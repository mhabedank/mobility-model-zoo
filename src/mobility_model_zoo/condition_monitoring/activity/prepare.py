"""Input preparation of pace-cnn: raw 6-axis IMU stream -> int8 model windows (feature 021, FR-021).

This is the host reference of the input contract on the model card. It turns a continuous stream of
accelerometer (g, 1 g = 9.80665 m/s^2) and gyroscope (rad/s) readings at 50 Hz into the model's
int8 input windows of 128 samples x 9 channels with 50 % overlap:

1. a causal median filter over 3 samples, per axis;
2. a causal 3rd-order Butterworth low-pass at 20 Hz, per axis (noise filter);
3. gravity separation of the acceleration with a causal 3rd-order Butterworth low-pass at 0.3 Hz:
   body acceleration = total acceleration - gravity;
4. channels in the order body_acc xyz, body_gyro xyz, total_acc xyz;
5. per-channel normalisation with the training-subject constants of uci-har-v1;
6. int8 quantisation with the model's input scale and zero point.

Steps 1-3 follow the dataset documentation (README.txt, features_info.txt; Anguita et al., ESANN 2013).
The median length, the order of the gravity filter and causal filtering are not stated there; the
owner fixed them on 2026-10-20 (research R11). The filters are second-order sections written out
in numpy, the same arithmetic a device implementation runs, and their coefficients go to the
release's `config.json`. Filter state starts at the steady state of the first sample, so there is
no start-up step from zero.

    from mobility_model_zoo.condition_monitoring.activity.prepare import Preparer
    prep = Preparer(mean, std, input_scale, input_zp)     # from config.json
    windows = prep.push(acc_g, gyro_rad_s)                # int8, shape (k, 1152), may be empty

The fidelity check (`fidelity_report`) compares the gravity separation with the dataset's own body
acceleration. It is informative only and never changes a parameter.
"""

from __future__ import annotations

import math

import numpy as np

RATE_HZ = 50
WINDOW = 128
STEP = 64  # 50 % overlap
MEDIAN = 3
NOISE_LOWPASS = {"order": 3, "cutoff_hz": 20.0}
GRAVITY_LOWPASS = {"order": 3, "cutoff_hz": 0.3}
CHANNELS = [
    "body_acc_x",
    "body_acc_y",
    "body_acc_z",
    "body_gyro_x",
    "body_gyro_y",
    "body_gyro_z",
    "total_acc_x",
    "total_acc_y",
    "total_acc_z",
]
UNITS = {"acc": "g (1 g = 9.80665 m/s^2)", "gyro": "rad/s"}


# ---- filter design (numpy only) ------------------------------------------------------------------


def butter_lowpass_sos(order: int, cutoff_hz: float, rate_hz: float) -> np.ndarray:
    """Digital Butterworth low-pass as second-order sections `[b0, b1, b2, 1, a1, a2]`, designed
    with the bilinear transform and a pre-warped cut-off; DC gain 1."""
    wc = 2 * rate_hz * math.tan(math.pi * cutoff_hz / rate_hz)  # pre-warped analog cut-off
    k = 2 * rate_hz
    poles = [
        wc
        * complex(
            math.cos(math.pi * (2 * i + order + 1) / (2 * order)),
            math.sin(math.pi * (2 * i + order + 1) / (2 * order)),
        )
        for i in range(order)
    ]
    zpoles = [(k + p) / (k - p) for p in poles]  # bilinear transform; zeros all at z = -1
    sections = []
    upper = sorted((z for z in zpoles if z.imag > 1e-12), key=lambda z: abs(z))
    for z in upper:  # conjugate pairs
        a1, a2 = -2 * z.real, abs(z) ** 2
        g = (1 + a1 + a2) / 4  # DC gain 1: b = g * (1, 2, 1)
        sections.append([g, 2 * g, g, 1.0, a1, a2])
    for z in (z for z in zpoles if abs(z.imag) <= 1e-12):  # a real pole (odd order)
        a1 = -z.real
        g = (1 + a1) / 2  # b = g * (1, 1)
        sections.append([g, g, 0.0, 1.0, a1, 0.0])
    return np.asarray(sections, np.float64)


def steady_state(sos: np.ndarray, x0: np.ndarray) -> np.ndarray:
    """Transposed direct form II state of every section for a constant input `x0` (per channel),
    shape (sections, 2, channels)."""
    x0 = np.asarray(x0, np.float64)
    z = np.zeros((len(sos), 2, x0.size))
    u = x0
    for i, (b0, b1, b2, _, a1, a2) in enumerate(sos):
        y = u * (b0 + b1 + b2) / (1 + a1 + a2)
        z[i, 0] = y - b0 * u
        z[i, 1] = b2 * u - a2 * y
        u = y
    return z


def sos_step(sos: np.ndarray, z: np.ndarray, x: np.ndarray) -> np.ndarray:
    """One sample through the cascade (transposed direct form II); updates `z` in place."""
    u = x
    for i, (b0, b1, b2, _, a1, a2) in enumerate(sos):
        y = b0 * u + z[i, 0]
        z[i, 0] = b1 * u - a1 * y + z[i, 1]
        z[i, 1] = b2 * u - a2 * y
        u = y
    return u


def sos_filter(sos: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Filter a whole signal (n, channels) causally from the steady state of its first sample."""
    x = np.asarray(x, np.float64)
    z = steady_state(sos, x[0])
    return np.stack([sos_step(sos, z, row) for row in x])


NOISE_SOS = butter_lowpass_sos(NOISE_LOWPASS["order"], NOISE_LOWPASS["cutoff_hz"], RATE_HZ)
GRAVITY_SOS = butter_lowpass_sos(GRAVITY_LOWPASS["order"], GRAVITY_LOWPASS["cutoff_hz"], RATE_HZ)


# ---- streaming preparation ----------------------------------------------------------------------


class Preparer:
    """Streaming preparation: push raw samples in any chunk size, receive every completed window."""

    def __init__(self, mean, std, input_scale: float, input_zp: int):
        self.mean = np.asarray(mean, np.float32)
        self.std = np.asarray(std, np.float32)
        self.scale, self.zp = float(input_scale), int(input_zp)
        self._hist: np.ndarray | None = None  # last MEDIAN raw samples, (MEDIAN, 6)
        self._z_noise: np.ndarray | None = None
        self._z_gravity: np.ndarray | None = None
        self._buf: list[np.ndarray] = []  # prepared float channels since the last window start

    def channels(self, acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
        """Float channels (n, 9) in `CHANNELS` order, before normalisation."""
        raw = np.concatenate([np.asarray(acc, np.float64), np.asarray(gyro, np.float64)], axis=1)
        out = np.empty((len(raw), len(CHANNELS)))
        for t, sample in enumerate(raw):
            if self._hist is None:  # start: history and filter state from the first sample
                self._hist = np.repeat(sample[None], MEDIAN, axis=0)
                self._z_noise = steady_state(NOISE_SOS, sample)
                self._z_gravity = steady_state(GRAVITY_SOS, sample[:3])
            self._hist = np.concatenate([self._hist[1:], sample[None]])
            med = np.median(self._hist, axis=0)
            clean = sos_step(NOISE_SOS, self._z_noise, med)
            total, gyro_f = clean[:3], clean[3:]
            gravity = sos_step(GRAVITY_SOS, self._z_gravity, total)
            out[t] = np.concatenate([total - gravity, gyro_f, total])
        return out

    def push(self, acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
        """int8 windows (k, 128 * 9), row-major 128 x 9, for every window completed by this chunk."""
        from mobility_model_zoo.edge.int8.quant import quantize

        ready = []
        for row in self.channels(acc, gyro):
            self._buf.append(row)
            if len(self._buf) == WINDOW:
                win = np.asarray(self._buf, np.float32)
                norm = (win - self.mean) / self.std
                ready.append(quantize(norm.reshape(-1), self.scale, self.zp))
                self._buf = self._buf[STEP:]
        if not ready:
            return np.zeros((0, WINDOW * len(CHANNELS)), np.int8)
        return np.stack(ready).astype(np.int8)


def prepare_stream(acc, gyro, mean, std, input_scale: float, input_zp: int) -> np.ndarray:
    """All int8 windows of one continuous recording."""
    return Preparer(mean, std, input_scale, input_zp).push(acc, gyro)


def config_block() -> dict:
    """The `preparation` block of the release's config.json."""
    return {
        "rate_hz": RATE_HZ,
        "window": WINDOW,
        "step": STEP,
        "units": UNITS,
        "channels": CHANNELS,
        "steps": [
            {"op": "median", "length": MEDIAN, "causal": True, "on": "acc and gyro, per axis"},
            {
                "op": "butterworth_lowpass",
                **NOISE_LOWPASS,
                "on": "acc and gyro, per axis",
                "sos": NOISE_SOS.tolist(),
            },
            {
                "op": "gravity_separation",
                "lowpass": {"type": "butterworth", **GRAVITY_LOWPASS, "sos": GRAVITY_SOS.tolist()},
                "body_acc": "total_acc - lowpass(total_acc)",
            },
            {"op": "normalise", "rule": "(x - mean) / std per channel, training-subject constants"},
            {"op": "quantise", "rule": "round(x / input_scale) + input_zp, clipped to int8"},
        ],
        "filter_form": "second-order sections, transposed direct form II, causal; state starts at "
        "the steady state of the first sample",
        "chosen_by_the_zoo": [
            "median length 3",
            "gravity filter order 3",
            "causal filtering",
        ],
    }


# ---- fidelity check (informative) -----------------------------------------------------------------


def _segments(windows: np.ndarray) -> list[np.ndarray]:
    """Rebuild continuous recordings from 50 %-overlapping windows (n, 128): consecutive windows
    whose overlap matches exactly belong to one recording."""
    segments, current = [], [windows[0]]
    for prev, win in zip(windows[:-1], windows[1:], strict=True):
        if np.array_equal(prev[STEP:], win[:STEP]):
            current.append(win[STEP:])
        else:
            segments.append(np.concatenate(current))
            current = [win]
    segments.append(np.concatenate(current))
    return segments


def fidelity_report(train_x: np.ndarray, settle: int = WINDOW) -> dict:
    """Gravity separation of the dataset's total acceleration against the dataset's body
    acceleration, per axis, on the training subjects (windows (n, 128, 9) in dataset channel
    order). Informative: the result is reported and never used to change a filter parameter."""
    axes = {}
    n_segments = n_samples = 0
    for a, axis in enumerate("xyz"):
        total = _segments(train_x[:, :, 6 + a])
        body = _segments(train_x[:, :, a])
        got, want = [], []
        for t, b in zip(total, body, strict=True):
            if len(t) <= settle:
                continue
            sep = t - sos_filter(GRAVITY_SOS, t[:, None])[:, 0]
            got.append(sep[settle:])
            want.append(b[settle:])
        g, w = np.concatenate(got), np.concatenate(want)
        axes[axis] = {
            "rmse_g": float(np.sqrt(np.mean((g - w) ** 2))),
            "correlation": float(np.corrcoef(g, w)[0, 1]),
        }
        n_segments, n_samples = len(got), int(len(g))
    return {
        "method": "causal gravity separation (prepare.py) of total_acc vs the dataset's body_acc, "
        f"training subjects, continuous recordings rebuilt from the windows, first {settle} "
        "samples of each recording skipped",
        "recordings": n_segments,
        "samples_per_axis": n_samples,
        "axes": axes,
        "note": "informative; never changes a filter parameter (research R11)",
    }
