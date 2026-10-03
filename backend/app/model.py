"""XGBoost score on the same features the rules use.

The score can hold a clean booking. It cannot block one.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from joblib import dump, load
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.domain import FEATURE_NAMES

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "fraud_model.joblib"
META_PATH = DATA_DIR / "fraud_model.json"


def ensure_model() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return train_and_save()


def train_and_save(seed: int = 7) -> dict:
    x, y = _synthetic(seed)
    model = XGBClassifier(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.12,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=seed,
    )
    x_train, _, y_train, _ = train_test_split(x, y, test_size=0.2, random_state=seed, stratify=y)
    model.fit(x_train, y_train)

    normal = _row(weight_ratio=1.0, velocity_ratio=1.0)
    heavy = _row(weight_ratio=12.0, velocity_ratio=1.0)
    score_normal = float(model.predict_proba(normal)[0, 1])
    score_heavy = float(model.predict_proba(heavy)[0, 1])
    # Sit between a typical parcel and a carton far above the account median.
    threshold = round((score_normal + score_heavy) / 2, 4)
    if score_heavy <= score_normal:
        threshold = 0.65

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dump(model, MODEL_PATH)
    meta = {
        "algorithm": "xgboost",
        "features": FEATURE_NAMES,
        "threshold": threshold,
        "score_normal": round(score_normal, 4),
        "score_heavy": round(score_heavy, 4),
        "policy": "High score holds. High score never blocks. Thin history and card payments skip the model.",
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    return meta


def score_features(features: dict) -> float:
    meta = ensure_model()
    model = load(MODEL_PATH)
    row = np.array([[float(features.get(name, 0)) for name in FEATURE_NAMES]])
    probability = float(model.predict_proba(row)[0, 1])
    return round(probability, 4)


def hold_threshold() -> float:
    return float(ensure_model()["threshold"])


def _row(**overrides) -> np.ndarray:
    base = {name: 0.0 for name in FEATURE_NAMES}
    base["velocity_ratio"] = 1.0
    base["weight_ratio"] = 1.0
    base.update(overrides)
    return np.array([[base[name] for name in FEATURE_NAMES]])


def _synthetic(seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows = []
    labels = []

    def add(n, label, **flags):
        for _ in range(n):
            row = {name: 0.0 for name in FEATURE_NAMES}
            row["velocity_ratio"] = float(rng.normal(1.0, 0.25))
            row["weight_ratio"] = float(rng.normal(1.0, 0.3))
            for key, value in flags.items():
                row[key] = value
            # Label noise so the model is not a perfect copy of the rules.
            noisy = label if rng.random() > 0.08 else 1 - label
            rows.append([row[name] for name in FEATURE_NAMES])
            labels.append(noisy)

    add(400, 0)
    add(120, 1, account_closed=1)
    add(120, 1, inbound_deny_hit=1)
    add(140, 1, new_payer=1, origin_unseen=1)
    add(140, 1, origin_unseen=1, express_or_international=1, domestic_ground_history=1)
    add(100, 1, velocity_ratio=8)
    add(80, 0, card_payment=1, weight_ratio=2)
    add(80, 0, thin_history=1, weight_ratio=2)
    # Weight is not a rule. It is the gray case the model is allowed to rank.
    for _ in range(160):
        row = {name: 0.0 for name in FEATURE_NAMES}
        row["velocity_ratio"] = float(rng.normal(1.0, 0.2))
        row["weight_ratio"] = float(rng.uniform(4.0, 18.0))
        rows.append([row[name] for name in FEATURE_NAMES])
        labels.append(1 if rng.random() > 0.15 else 0)
    for _ in range(80):
        row = {name: 0.0 for name in FEATURE_NAMES}
        row["velocity_ratio"] = float(rng.normal(1.0, 0.2))
        row["weight_ratio"] = float(rng.uniform(0.4, 1.8))
        rows.append([row[name] for name in FEATURE_NAMES])
        labels.append(0)

    return np.array(rows), np.array(labels)
