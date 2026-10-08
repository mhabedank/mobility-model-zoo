"""hum-fan features and metrics (no TensorFlow needed)."""

import struct

import numpy as np
import pytest

from mobility_model_zoo.condition_monitoring.sound_anomaly.features import log_mel, read_wav
from mobility_model_zoo.condition_monitoring.sound_anomaly.train import roc_auc, windows


def test_roc_auc_and_partial_auc():
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    assert roc_auc(np.arange(8.0), y) == 1.0
    assert roc_auc(-np.arange(8.0), y) == 0.0
    assert roc_auc(np.ones(8), y) == 0.5  # ties
    assert abs(roc_auc(np.array([0, 1, 2, 5, 3, 4, 6, 7.0]), y) - 14 / 16) < 1e-9
    assert roc_auc(np.arange(8.0), y, max_fpr=0.1) == 1.0


def test_log_mel_shape():
    x = np.sin(np.linspace(0, 2000 * np.pi, 16000)).astype(np.float32)
    assert log_mel(x).shape == (49, 40)


def test_windows_stack_context():
    lm = np.arange(311 * 40, dtype=np.float32).reshape(311, 40)
    w = windows(lm)
    assert w.shape == (307, 200)
    assert np.array_equal(w[1], lm[1:6].reshape(-1))
    assert windows(lm, stride=8).shape == (39, 200)


def _wav_bytes(pcm: np.ndarray, n_ch: int, bits: int, extensible: bool) -> bytes:
    width = bits // 8
    if width == 3:
        v = pcm.astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3]
        data = v.tobytes()
    else:
        data = pcm.astype("<i2" if width == 2 else "<i4").tobytes()
    if extensible:  # WAVE_FORMAT_EXTENSIBLE with PCM sub-format GUID
        fmt = struct.pack(
            "<HHIIHHHHI", 0xFFFE, n_ch, 16000, 16000 * n_ch * width, n_ch * width, bits, 22, bits, 0
        )
        fmt += struct.pack("<H", 1) + b"\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"
    else:
        fmt = struct.pack("<HHIIHH", 1, n_ch, 16000, 16000 * n_ch * width, n_ch * width, bits)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"LIST" + struct.pack("<I", 3) + b"abc\x00"
    chunks += b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


@pytest.mark.parametrize("bits,extensible", [(16, False), (16, True), (24, True), (32, False)])
def test_read_wav_formats(tmp_path, bits, extensible):
    full = 1 << (bits - 1)
    ch0 = np.array([0, full // 2, -full // 2, -full], dtype=np.int64)
    pcm = np.stack([ch0, -ch0 // 2], axis=1).reshape(-1)  # 2 channels, interleaved
    p = tmp_path / "x.wav"
    p.write_bytes(_wav_bytes(pcm, 2, bits, extensible))
    assert np.allclose(read_wav(p, length=0, channel=0), [0, 0.5, -0.5, -1.0], atol=1e-6)
    assert np.allclose(read_wav(p, length=0), [0, 0.125, -0.125, -0.25], atol=1e-6)  # mean
    assert read_wav(p, length=6, channel=1).shape == (6,)
