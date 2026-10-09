"""Synthetic CAN traffic for examples and tests (feature 007, T019)."""

import numpy as np
import pandas as pd
import pytest

from mobility_model_zoo.security.can_ids.metrics import attack_episodes
from mobility_model_zoo.security.can_ids.synth import ATTACKS, generate


@pytest.mark.parametrize("attack", ATTACKS)
def test_one_attack_episode_in_benign_traffic(attack):
    df = generate(attack, n_frames=2000, seed=3)
    assert len(df) == 2000
    assert list(df.columns[:3]) == ["ts", "can_id", "dlc"] and "label" in df
    assert np.all(np.diff(df["ts"].to_numpy()) >= 0)
    episodes = attack_episodes(df["ts"].to_numpy(), df["label"].to_numpy())
    assert len(episodes) == 1
    assert 0 < df["label"].sum() < len(df)


@pytest.mark.parametrize("attack", ATTACKS)
def test_deterministic_per_seed(attack):
    pd.testing.assert_frame_equal(generate(attack, seed=5), generate(attack, seed=5))
    assert not generate(attack, seed=5).equals(generate(attack, seed=6))


def test_unknown_attack_is_refused():
    with pytest.raises(ValueError, match="unknown attack"):
        generate("masquerade")
