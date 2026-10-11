"""Detectors of the can-ids-v1 harness: picket-forest, shortcut controls and baselines (research R5).

Every detector has the same interface and is trained and scored the same way (constitution VIII):
`fit(train, val)` sees training captures and validation captures (never test captures);
`score(caps)` returns one float score per frame, higher = more likely an attack. Thresholds and
alarm rules are chosen by the harness on validation scores.

A capture is a dict with `id`, `family`, `y` (labels), `ts` (seconds), `X` (the 13 streaming
features of `forest_features`), `can_id` (uint16) and `data` (uint8, n x 8).
"""

from __future__ import annotations

import pickle
import time
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from mobility_model_zoo.security.can_ids import forest
from mobility_model_zoo.security.can_ids.forest_features import FEATURE_NAMES

SEED = 0
BENIGN_KEEP = 0.1
TIMING = ["dt_id_ms", "dt_ratio", "dt_bus_ms", "bus_dt_ewma_ms"]


def subsample(caps: list[dict], key: str = "X", seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """All attack frames and 10 % of benign frames (same rule for every supervised detector)."""
    rng = np.random.default_rng(seed)
    xs, ys = [], []
    for c in caps:
        keep = (c["y"] == 1) | (rng.random(c["y"].size) < BENIGN_KEEP)
        xs.append(c[key][keep] if key != "orig" else orig_features(c)[keep])
        ys.append(c["y"][keep])
    return np.concatenate(xs), np.concatenate(ys)


def orig_features(c: dict) -> np.ndarray:
    """Frame features of the original can-train-and-test benchmark: timestamp, ID, data bytes.

    The absolute timestamp is a known shortcut feature; it is kept because the original used it."""
    return np.column_stack([c["ts"], c["can_id"].astype(np.float64), c["data"].astype(np.float64)])


@dataclass
class Detector:
    name: str
    kind: str  # model | control | baseline
    description: str
    model: object = None
    info: dict = field(default_factory=dict)

    def fit(self, train: list[dict], val: list[dict]) -> None:
        raise NotImplementedError

    def score(self, caps: list[dict]) -> list[np.ndarray]:
        raise NotImplementedError

    def size_bytes(self) -> int:
        """Cost proxy for the Pareto table: size of the pickled model."""
        return len(pickle.dumps(self.model)) if self.model is not None else 0

    def timed_score(self, caps: list[dict]) -> tuple[list[np.ndarray], float]:
        """Scores plus host time per frame in µs (Python, labelled as such in the report)."""
        t0 = time.perf_counter()
        out = self.score(caps)
        n = sum(len(c["y"]) for c in caps)
        return out, (time.perf_counter() - t0) / max(n, 1) * 1e6


# ---- forests ---------------------------------------------------------------------------------


class Forest(Detector):
    """picket-forest recipe on a feature subset; hyperparameters chosen on validation (F1)."""

    def __init__(self, name, kind, description, features, shuffle=False, grid=None):
        super().__init__(name, kind, description)
        self.idx = forest.cols(features)
        self.shuffle = shuffle
        self.grid = grid or forest.GRID

    def fit(self, train, val):
        if self.shuffle:
            self._fit_shuffled(train)
            return
        x, y = subsample(train)
        yv = np.concatenate([c["y"] for c in val])
        best = None
        for hp in self.grid:
            clf = forest.fit(x[:, self.idx], y, hp)
            sv = np.concatenate(forest.predict(clf, val, self.idx))
            f1 = _f1_at_best(yv, sv)
            if best is None or f1 > best[0]:
                best = (f1, hp, clf)
        _, self.info["hyperparameters"], self.model = best
        self.info["tree_nodes"] = int(sum(e.tree_.node_count for e in self.model.estimators_))

    SHUFFLE_SEEDS = 5

    def _fit_shuffled(self, train):
        """Leakage control: labels permuted across all training frames *before* the label-dependent
        subsampling, so neither labels nor frame selection carry information. The probabilities of
        five such forests are averaged; a single random model can land on any value for a
        homogeneous cluster of test frames, the average cannot. Fixed hyperparameters."""
        y_all = np.concatenate([c["y"] for c in train])
        bounds = np.cumsum([0, *(len(c["y"]) for c in train)])
        hp = self.grid[-1]
        self.model = []
        for seed in range(self.SHUFFLE_SEEDS):
            y_perm = np.random.default_rng(seed).permutation(y_all)
            shuffled = [
                {**c, "y": y_perm[a:b]} for c, a, b in zip(train, bounds[:-1], bounds[1:], strict=True)
            ]
            x, y = subsample(shuffled, seed=seed)
            self.model.append(forest.fit(x[:, self.idx], y, hp))
        self.info["hyperparameters"] = hp
        self.info["tree_nodes"] = int(sum(e.tree_.node_count for m in self.model for e in m.estimators_))

    def score(self, caps):
        if isinstance(self.model, list):
            # Probabilities, not hard votes: with random labels, hard majority votes are biased by
            # the local frame density (dense regions vote with the global majority), which would
            # look like signal. Averaged leaf probabilities are not.
            return [
                np.mean([m.predict_proba(c["X"][:, self.idx])[:, 1] for m in self.model], axis=0).astype(
                    np.float32
                )
                for c in caps
            ]
        return forest.predict(self.model, caps, self.idx)


def _f1_at_best(y, s) -> float:
    if not 0 < y.sum() < y.size:
        return 0.0
    thr = forest.best_threshold(y, s)
    p = s >= thr
    tp = float(((p == 1) & (y == 1)).sum())
    return 2 * tp / max(float(p.sum() + y.sum()), 1.0)


def _lookup(ids: np.ndarray, table: dict, default: float) -> np.ndarray:
    """Vectorised per-ID lookup: table {id: value} -> value per frame (default for unknown IDs)."""
    keys = np.fromiter(table.keys(), dtype=np.int64, count=len(table))
    vals = np.fromiter(table.values(), dtype=np.float64, count=len(table))
    order = np.argsort(keys)
    keys, vals = keys[order], vals[order]
    ids = ids.astype(np.int64)
    pos = np.clip(np.searchsorted(keys, ids), 0, max(len(keys) - 1, 0))
    found = (keys.size > 0) & (keys[pos] == ids) if keys.size else np.zeros(ids.size, bool)
    return np.where(found, vals[pos] if keys.size else default, default)


# ---- controls --------------------------------------------------------------------------------


class IdLookup(Detector):
    def fit(self, train, val):
        hits, total = defaultdict(int), defaultdict(int)
        for c in train:
            ids, y = c["can_id"], c["y"]
            for i in np.unique(ids):
                m = ids == i
                hits[int(i)] += int(y[m].sum())
                total[int(i)] += int(m.sum())
        all_y = np.concatenate([c["y"] for c in train])
        self.model = {"rate": {i: hits[i] / total[i] for i in total}, "default": float(all_y.mean())}

    def score(self, caps):
        rate, default = self.model["rate"], self.model["default"]
        return [_lookup(c["can_id"], rate, default).astype(np.float32) for c in caps]


# ---- baselines -------------------------------------------------------------------------------


def _intervals(c: dict) -> np.ndarray:
    """Time since the previous frame of the same ID (s); NaN for the first frame of an ID."""
    ids, ts = c["can_id"], c["ts"]
    out = np.full(ids.size, np.nan)
    order = np.lexsort((ts, ids))
    same = np.r_[False, ids[order][1:] == ids[order][:-1]]
    d = np.r_[np.nan, np.diff(ts[order])]
    out[order] = np.where(same, d, np.nan)
    return out


class MeanInterval(Detector):
    """Blevins et al. 2021 "Mean": benign mean interval per ID; short intervals score high."""

    def fit(self, train, val):
        sums, counts = defaultdict(float), defaultdict(int)
        for c in train:
            dt, ids = _intervals(c), c["can_id"]
            ok = (c["y"] == 0) & ~np.isnan(dt)
            for i in np.unique(ids[ok]):
                m = ok & (ids == i)
                sums[int(i)] += float(dt[m].sum())
                counts[int(i)] += int(m.sum())
        self.model = {i: sums[i] / counts[i] for i in counts}

    def score(self, caps):
        out = []
        for c in caps:
            dt, ids = _intervals(c), c["can_id"]
            mean = _lookup(ids, self.model, np.nan)
            s = np.where(np.isnan(mean), 1.0, 1.0 - np.clip(dt / mean, 0, 1))
            out.append(np.nan_to_num(s, nan=0.0).astype(np.float32))
        return out


class Binning(Detector):
    """Blevins et al. 2021 "Binning": per-ID histogram of benign intervals; rare bins score high."""

    BINS = np.r_[0, np.geomspace(1e-4, 10, 40), np.inf]

    def fit(self, train, val):
        hist = defaultdict(lambda: np.zeros(len(self.BINS) - 1))
        for c in train:
            dt, ids = _intervals(c), c["can_id"]
            ok = (c["y"] == 0) & ~np.isnan(dt)
            for i in np.unique(ids[ok]):
                m = ok & (ids == i)
                hist[int(i)] += np.histogram(dt[m], self.BINS)[0]
        self.model = {i: h / h.sum() for i, h in hist.items() if h.sum()}

    def score(self, caps):
        known = sorted(self.model)
        row = {i: r for r, i in enumerate(known)}
        mat = np.array([self.model[i] for i in known]) if known else np.zeros((0, len(self.BINS) - 1))
        out = []
        for c in caps:
            dt, ids = _intervals(c), c["can_id"]
            r = _lookup(ids, row, -1).astype(np.int64)
            b = np.clip(np.digitize(np.nan_to_num(dt, nan=1e9), self.BINS) - 1, 0, len(self.BINS) - 2)
            s = np.ones(ids.size, np.float32)  # unknown ID
            ok = r >= 0
            s[ok] = 1.0 - mat[r[ok], b[ok]]
            s[ok & np.isnan(dt)] = 0.0  # first frame of a known ID
            out.append(s)
        return out


class CanLogic(Detector):
    """can-logic-style rules (Lampe & Meng): unknown ID, three repeats of one ID, too-short interval."""

    def fit(self, train, val):
        mins = defaultdict(lambda: np.inf)
        for c in train:
            dt, ids = _intervals(c), c["can_id"]
            ok = (c["y"] == 0) & ~np.isnan(dt)
            for i in np.unique(ids[ok]):
                mins[int(i)] = min(mins[int(i)], float(dt[ok & (ids == i)].min()))
        self.model = {
            "whitelist": {int(i) for c in train for i in np.unique(c["can_id"][c["y"] == 0])},
            "min_interval": dict(mins),
        }

    def score(self, caps):
        wl, mins = self.model["whitelist"], self.model["min_interval"]
        known = {i: 1.0 for i in wl}
        out = []
        for c in caps:
            ids, dt = c["can_id"], _intervals(c)
            unknown = _lookup(ids, known, 0.0) == 0.0
            rep = np.r_[False, False, (ids[2:] == ids[1:-1]) & (ids[1:-1] == ids[:-2])]
            lim = _lookup(ids, mins, np.inf) * 0.5
            short = ~np.isnan(dt) & (dt < lim)
            out.append((unknown | rep | short).astype(np.float32))
        return out


class IsoForest(Detector):
    def fit(self, train, val):
        from sklearn.ensemble import IsolationForest

        x = np.concatenate([c["X"][c["y"] == 0] for c in train])
        rng = np.random.default_rng(SEED)
        x = x[rng.choice(len(x), min(len(x), 200_000), replace=False)]
        self.model = IsolationForest(n_estimators=100, random_state=SEED, n_jobs=-1).fit(x)

    def score(self, caps):
        return [(-self.model.score_samples(c["X"])).astype(np.float32) for c in caps]


class Original(Detector):
    """A model of the original can-train-and-test benchmark on its frame features."""

    def __init__(self, name, description, factory):
        super().__init__(name, "baseline", description)
        self.factory = factory

    def fit(self, train, val):
        x, y = subsample(train, key="orig")
        self.model = self.factory().fit(x, y)

    def score(self, caps):
        out = []
        for c in caps:
            x = orig_features(c)
            m = self.model
            s = m.predict_proba(x)[:, 1] if hasattr(m, "predict_proba") else m.decision_function(x)
            out.append(np.asarray(s, dtype=np.float32))
        return out


def _orig(kind: str):
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    return {
        "dt": lambda: DecisionTreeClassifier(random_state=SEED),
        "rf": lambda: RandomForestClassifier(random_state=SEED, n_jobs=-1),
        "et": lambda: ExtraTreesClassifier(random_state=SEED, n_jobs=-1),
        "gnb": GaussianNB,
        "logreg": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "mlp": lambda: make_pipeline(StandardScaler(), MLPClassifier(random_state=SEED, max_iter=50)),
    }[kind]


# ---- registry --------------------------------------------------------------------------------

NO_ID = [f for f in FEATURE_NAMES if f != "can_id"]


def registry() -> dict[str, Detector]:
    def make(cls, name, kind, desc):
        d = cls(name, kind, desc)
        return d

    regs: dict[str, Detector] = {
        "picket-forest": Forest(
            "picket-forest", "model", "random forest on 12 streaming features without the CAN ID", NO_ID
        ),
        "ctrl-id-lookup": make(
            IdLookup, "ctrl-id-lookup", "control", "attack rate per CAN ID learned on training data"
        ),
        "ctrl-timing-only": Forest(
            "ctrl-timing-only", "control", "picket-forest recipe on the 4 timing features", TIMING
        ),
        "ctrl-forest-with-id": Forest(
            "ctrl-forest-with-id",
            "control",
            "picket-forest recipe including the raw CAN ID",
            FEATURE_NAMES,
        ),
        "ctrl-shuffled": Forest(
            "ctrl-shuffled",
            "control",
            "picket-forest recipe with shuffled training labels",
            NO_ID,
            shuffle=True,
        ),
        "bl-mean-interval": make(
            MeanInterval,
            "bl-mean-interval",
            "baseline",
            "Blevins et al. 2021 mean interval per ID, benign-only",
        ),
        "bl-binning": make(
            Binning, "bl-binning", "baseline", "Blevins et al. 2021 interval binning per ID, benign-only"
        ),
        "bl-can-logic": make(
            CanLogic, "bl-can-logic", "baseline", "rules: unknown ID, three repeats, too-short interval"
        ),
        "bl-isolation-forest": make(
            IsoForest,
            "bl-isolation-forest",
            "baseline",
            "Isolation Forest on the 13 features, benign-only",
        ),
    }
    for k, desc in (
        ("dt", "decision tree"),
        ("rf", "random forest"),
        ("et", "extra trees"),
        ("gnb", "Gaussian naive Bayes"),
        ("logreg", "logistic regression"),
        ("mlp", "multi-layer perceptron"),
    ):
        regs[f"bl-orig-{k}"] = Original(
            f"bl-orig-{k}", f"original benchmark {desc} on timestamp, ID and data bytes", _orig(k)
        )
    return regs


def make_capture(df, cid: str, family: str) -> dict:
    """Frames (columns ts in s, can_id, dlc, b0..b7, label) -> a harness capture."""
    from mobility_model_zoo.security.can_ids.forest_features import extract

    return {
        "id": cid,
        "family": family,
        "y": df["label"].to_numpy(np.uint8),
        "ts": df["ts"].to_numpy(np.float64),
        "X": extract(df),
        "can_id": df["can_id"].to_numpy(np.uint16),
        "dlc": df["dlc"].to_numpy(np.uint8),
        "data": df[[f"b{i}" for i in range(8)]].to_numpy(np.uint8),
    }
