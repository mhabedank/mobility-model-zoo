"""Input preparation host reference of pace-cnn (feature 021, T012; FR-021, research R11)."""

import subprocess
import sys

import numpy as np
import pytest

from mobility_model_zoo.condition_monitoring.activity import prepare as pp
from mobility_model_zoo.condition_monitoring.activity.train import SIGNALS
from mobility_model_zoo.edge.int8.quant import quantize

MEAN = np.linspace(-0.1, 0.1, 9).astype(np.float32)
STD = np.linspace(0.2, 0.5, 9).astype(np.float32)
SCALE, ZP = 0.05, -3


def _stream(n=700, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / pp.RATE_HZ
    acc = np.stack([np.sin(2 * np.pi * 1.8 * t), np.cos(2 * np.pi * 0.9 * t), 1 + 0 * t], 1)
    acc = acc * 0.3 + rng.normal(0, 0.02, (n, 3))
    gyro = rng.normal(0, 0.4, (n, 3))
    return acc, gyro


def test_windows_are_int8_128_by_9_with_half_overlap():
    acc, gyro = _stream()
    w = pp.prepare_stream(acc, gyro, MEAN, STD, SCALE, ZP)
    assert w.dtype == np.int8 and w.shape == ((700 - 128) // 64 + 1, 1152)
    rows = w.reshape(len(w), 128, 9)
    assert np.array_equal(rows[0][64:], rows[1][:64])


def test_channel_order_is_the_models():
    assert pp.CHANNELS == SIGNALS
    acc, gyro = _stream(200)
    ch = pp.Preparer(MEAN, STD, SCALE, ZP).channels(acc, gyro)
    total, body = ch[:, 6:9], ch[:, 0:3]
    gravity = total - body
    assert np.abs(gravity[-50:, 2] - 0.3).max() < 0.05  # the constant z component is gravity


def test_quantisation_uses_the_models_scale_and_zero_point():
    acc, gyro = _stream(128)
    prep = pp.Preparer(MEAN, STD, SCALE, ZP)
    ch = pp.Preparer(MEAN, STD, SCALE, ZP).channels(acc, gyro).astype(np.float32)
    want = quantize(((ch - MEAN) / STD).reshape(-1), SCALE, ZP)
    assert np.array_equal(prep.push(acc, gyro)[0], want)


def test_chunked_stream_equals_whole_stream():
    acc, gyro = _stream()
    whole = pp.prepare_stream(acc, gyro, MEAN, STD, SCALE, ZP)
    prep = pp.Preparer(MEAN, STD, SCALE, ZP)
    parts = [prep.push(acc[i : i + 37], gyro[i : i + 37]) for i in range(0, len(acc), 37)]
    assert np.array_equal(np.concatenate(parts), whole)


def test_module_needs_numpy_only():
    code = (
        "import sys; import mobility_model_zoo.condition_monitoring.activity.prepare; "
        "print('scipy' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


@pytest.mark.parametrize(("order", "cutoff"), [(3, 20.0), (3, 0.3)])
def test_filters_match_scipy(order, cutoff):
    signal = pytest.importorskip("scipy.signal")
    rng = np.random.default_rng(1)
    x = rng.normal(size=(400, 2)) + 1.0
    ours = pp.sos_filter(pp.butter_lowpass_sos(order, cutoff, pp.RATE_HZ), x)
    sos = signal.butter(order, cutoff, fs=pp.RATE_HZ, output="sos")
    zi = signal.sosfilt_zi(sos)[:, :, None] * x[0][None, None, :]
    ref, _ = signal.sosfilt(sos, x, axis=0, zi=zi)
    assert np.allclose(ours, ref, rtol=1e-9, atol=1e-9)


def test_dc_gain_is_one():
    for spec in (pp.NOISE_LOWPASS, pp.GRAVITY_LOWPASS):
        sos = pp.butter_lowpass_sos(spec["order"], spec["cutoff_hz"], pp.RATE_HZ)
        y = pp.sos_filter(sos, np.full((10, 1), 2.5))
        assert np.allclose(y, 2.5)


def test_fidelity_reports_rmse_and_correlation_per_axis():
    rng = np.random.default_rng(3)
    n = 2000
    t = np.arange(n) / pp.RATE_HZ
    total = np.stack([np.sin(2 * np.pi * 1.5 * t) * 0.3 + g for g in (0.1, -0.2, 0.95)], 1)
    total += rng.normal(0, 0.01, total.shape)
    body = total - pp.sos_filter(pp.GRAVITY_SOS, total)
    stream = np.zeros((n, 9))
    stream[:, 0:3], stream[:, 6:9] = body, total
    windows = np.stack([stream[i : i + 128] for i in range(0, n - 128 + 1, 64)])
    rep = pp.fidelity_report(windows)
    assert rep["recordings"] == 1
    assert set(rep["axes"]) == {"x", "y", "z"}
    for a in rep["axes"].values():
        assert a["rmse_g"] < 1e-9 and a["correlation"] > 0.999999
