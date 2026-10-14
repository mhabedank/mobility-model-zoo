"""Processing and content checks of website images (feature 016, research R3 to R5).

Crop around the focal point, encode WebP derivatives that carry the IPTC "trained algorithmic
media" marker, enforce the byte caps, detect faces (YuNet) and readable text (RapidOCR), and
compare regenerated images by perceptual hash (I5). Everything here needs the `images` extra and is
imported lazily by `zoo site images`; `zoo site build` never touches it.
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.errors import UsageError
from mobility_model_zoo.site.images import BYTE_CAPS, IPTC_MARKER, WIDTHS

INSTALL = "the images extra is missing: uv sync --extra release --extra images"
QUALITY, MIN_QUALITY = 72, 60
FACE_SCORE, FACE_MIN_HEIGHT = 0.5, 16
TEXT_CONFIDENCE, TEXT_MIN_CHARS = 0.7, 2
PHASH_MAX_BITS = 4
# opencv_zoo's YuNet face detector (MIT), pinned by content hash; fetched once into the cache.
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
CACHE = Path.home() / ".cache" / "mobility-model-zoo" / "yunet"


class MissingExtra(UsageError):
    pass


def _pil():
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise MissingExtra(INSTALL) from e
    return Image


# ---- crop and encode ---------------------------------------------------------------------------
def crop_box(
    width: int, height: int, aspect: str, focal: tuple[float, float]
) -> tuple[int, int, int, int]:
    """The largest box of the aspect ratio inside the image, centred on the focal point and clamped
    to the edges, so the focal point stays visible at every width (FR-006)."""
    aw, ah = (16, 9) if aspect == "16:9" else (3, 2)
    if width * ah > height * aw:  # too wide: full height
        cw, ch = round(height * aw / ah), height
    else:
        cw, ch = width, round(width * ah / aw)
    cx, cy = focal[0] * width, focal[1] * height
    left = min(max(round(cx - cw / 2), 0), width - cw)
    top = min(max(round(cy - ch / 2), 0), height - ch)
    return left, top, left + cw, top + ch


def xmp_packet(model: str, series: str) -> bytes:
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
        f"<Iptc4xmpExt:DigitalSourceType>{IPTC_MARKER}</Iptc4xmpExt:DigitalSourceType>"
        f"<xmp:CreatorTool>mobility-model-zoo imagery, series {series}, model {model}</xmp:CreatorTool>"
        '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode()


def encode(img: Any, width: int, xmp: bytes) -> bytes:
    """One WebP derivative within its byte cap; quality drops from 72 to 60 if needed."""
    scaled = img.resize((width, round(width * img.height / img.width)), _pil().Resampling.LANCZOS)
    for quality in range(QUALITY, MIN_QUALITY - 1, -4):
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=quality, method=6, xmp=xmp)
        data = buf.getvalue()
        if len(data) <= BYTE_CAPS[width]:
            return data
    raise UsageError(
        f"the {width} px derivative stays above {BYTE_CAPS[width]} bytes even at quality {MIN_QUALITY}"
    )


def derivatives(
    png: Path, aspect: str, focal: tuple[float, float], model: str, series: str
) -> dict[int, bytes]:
    Image = _pil()
    with Image.open(png) as img:
        img = img.convert("RGB")
        cropped = img.crop(crop_box(img.width, img.height, aspect, focal))
        xmp = xmp_packet(model, series)
        return {w: encode(cropped, w, xmp) for w in WIDTHS}


def has_marker(path: Path) -> bool:
    """Whether a derivative carries the IPTC marker (check I3); reads the XMP chunk of the WebP."""
    Image = _pil()
    with Image.open(path) as img:
        xmp = img.info.get("xmp") or b""
    return IPTC_MARKER.encode() in xmp


# ---- content checks (I4) -----------------------------------------------------------------------
def _yunet_model() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "face_detection_yunet_2023mar.onnx"
    if not path.exists():
        with urllib.request.urlopen(YUNET_URL, timeout=60) as r:  # noqa: S310 - pinned by hash below
            path.write_bytes(r.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not YUNET_SHA256:
        print(f"warning: YuNet model is not pinned yet; downloaded sha256 {digest}", file=sys.stderr)
    elif digest != YUNET_SHA256:
        path.unlink()
        raise UsageError(f"YuNet model hash {digest} differs from the pinned {YUNET_SHA256}")
    return path


def faces(png: Path) -> dict[str, Any]:
    """Detections of identifiable size; `pass` is False if any (FR-009)."""
    try:
        import cv2
    except ImportError as e:  # pragma: no cover
        raise MissingExtra(INSTALL) from e
    import numpy as np

    img = cv2.imread(str(png))
    if img is None:
        raise UsageError(f"{png} is not an image")
    det = cv2.FaceDetectorYN.create(str(_yunet_model()), "", (320, 320), FACE_SCORE, 0.3, 5000)
    hits: list[dict[str, float]] = []
    below = 0
    views = [img]
    h, w = img.shape[:2]
    for half in (img[:, : w // 2], img[:, w // 2 :]):  # 2x upscaled halves catch small faces
        views.append(cv2.resize(half, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    for scale, view in zip((1, 2, 2), views, strict=True):
        det.setInputSize((view.shape[1], view.shape[0]))
        _, found = det.detect(view)
        for row in np.asarray(found if found is not None else []).reshape(-1, 15):
            height = float(row[3]) / scale
            score = float(row[14])
            if score >= FACE_SCORE and height >= FACE_MIN_HEIGHT:
                hits.append({"score": round(score, 3), "height_px": round(height, 1)})
            else:
                below += 1
    return {"pass": not hits, "hits": hits, "below_threshold": below}


def text(png: Path) -> dict[str, Any]:
    """OCR tokens with confidence ≥ 0.7 and at least two alphanumerics; any means fail (FR-009)."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:  # pragma: no cover
        raise MissingExtra(INSTALL) from e
    result, _ = RapidOCR()(str(png))
    tokens = []
    for _box, word, score in result or []:
        alnum = sum(ch.isalnum() for ch in word)
        if float(score) >= TEXT_CONFIDENCE and alnum >= TEXT_MIN_CHARS:
            tokens.append({"text": word, "score": round(float(score), 3)})
    return {"pass": not tokens, "tokens": tokens}


def tool_versions() -> dict[str, str]:
    from importlib import metadata

    out = {}
    for pkg in ("pillow", "opencv-python-headless", "rapidocr-onnxruntime", "onnxruntime"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    out["yunet_sha256"] = YUNET_SHA256
    return out


# ---- perceptual hash (I5) ----------------------------------------------------------------------
def phash(path: Path) -> int:
    """64-bit pHash: 32x32 grey, DCT, top-left 8x8 against the median."""
    import numpy as np

    Image = _pil()
    with Image.open(path) as img:
        grey = np.asarray(img.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    n = 32
    k = np.arange(n)
    dct = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    coeffs = dct @ grey @ dct.T
    low = coeffs[:8, :8].flatten()
    median = np.median(low[1:])
    bits = 0
    for i, v in enumerate(low):
        if v > median:
            bits |= 1 << i
    return bits


def phash_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
