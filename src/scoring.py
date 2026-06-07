"""
UBI Driver Risk Scorer — scoring module.

Usage
-----
from src.scoring import score_driver

result = score_driver(
    features={
        "avg_speed": 26.0,
        "max_speed": 51.0,
        "harsh_braking_count": 0,
        "recklessness_score": 3.5,
        "trips_recorded": 10,
        "num_claims": 0,
    },
    days_safe=42,
)
"""

from __future__ import annotations

import joblib
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_MODEL_PATH = _HERE.parent / "models" / "risk_model.pkl"

# ---------------------------------------------------------------------------
# Reference upper bounds for normalising telematics features.
# Used only for worst-feature detection (tip selection), not for scoring.
# Values are the observed p99 across all 50 synthetic drivers.
# ---------------------------------------------------------------------------
_FEATURE_UPPER = {
    "avg_speed": 90.0,           # km/h
    "harsh_braking_count": 3.0,  # events per driver history
    "recklessness_score": 16.5,  # mean absolute bearing-change (degrees)
}

# ---------------------------------------------------------------------------
# Load model once at import time
# ---------------------------------------------------------------------------
_payload = joblib.load(_MODEL_PATH)
_model = _payload["model"]
_feature_cols: list[str] = _payload["feature_cols"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_driver(features: dict, days_safe: int) -> dict:
    """
    Score a single driver and return a full risk profile.

    Parameters
    ----------
    features : dict
        Must contain: avg_speed, max_speed, harsh_braking_count,
        recklessness_score, trips_recorded, num_claims.
    days_safe : int
        Consecutive days without harsh braking or high-speed events.

    Returns
    -------
    dict with keys:
        risk_score      int    0–100
        risk_label      str    e.g. "🟢 Low Risk"
        driver_level    str    e.g. "🥇 Gold"
        streak_message  str
        tip             str
    """
    X = pd.DataFrame([features])[_feature_cols]
    prob_high_risk = float(_model.predict_proba(X)[0, 1])
    risk_score = round(prob_high_risk * 100)

    risk_label, label_emoji = _risk_label(risk_score)

    return {
        "risk_score": risk_score,
        "risk_label": f"{label_emoji} {risk_label}",
        "driver_level": _driver_level(risk_score, risk_label, days_safe),
        "streak_message": _streak_message(days_safe),
        "tip": _tip(features, risk_label),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _risk_label(score: int) -> tuple[str, str]:
    if score <= 33:
        return "Low Risk", "🟢"
    if score <= 66:
        return "Medium Risk", "🟡"
    return "High Risk", "🔴"


def _driver_level(score: int, risk_label: str, days_safe: int) -> str:
    """
    Gamification tier.

    Tier      Requirement
    Diamond   90+ days safe  AND  Low Risk  AND  score < 20
    Gold      61-90 days safe  AND  Low Risk
    Silver    31-60 days safe  AND  Low or Medium Risk
    Bronze    everything else
    """
    is_low = risk_label == "Low Risk"
    is_low_or_medium = risk_label in ("Low Risk", "Medium Risk")

    if days_safe >= 90 and is_low and score < 20:
        return "💎 Diamond"
    if days_safe >= 61 and is_low:
        return "🥇 Gold"
    if days_safe >= 31 and is_low_or_medium:
        return "🥈 Silver"
    return "🥉 Bronze"


def _streak_message(days_safe: int) -> str:
    if days_safe == 0:
        return "Start your streak today — drive safe!"
    if days_safe >= 7:
        return f"🔥 {days_safe} day safe driving streak!"
    return f"{days_safe} days safe — keep it up!"


def _tip(features: dict, risk_label: str) -> str:
    if risk_label == "Low Risk":
        return "Great driving! You qualify for a rebate on your next renewal."

    # Normalise each problematic telematics feature to [0, 1] and surface the worst.
    penalties = {
        "avg_speed": features.get("avg_speed", 0) / _FEATURE_UPPER["avg_speed"],
        "harsh_braking_count": (
            features.get("harsh_braking_count", 0) / _FEATURE_UPPER["harsh_braking_count"]
        ),
        "recklessness_score": (
            features.get("recklessness_score", 0) / _FEATURE_UPPER["recklessness_score"]
        ),
    }
    worst = max(penalties, key=penalties.get)

    return {
        "avg_speed": (
            "Your average speed is high. "
            "Slowing down saves fuel and reduces accident risk."
        ),
        "harsh_braking_count": (
            "Frequent harsh braking detected. "
            "Anticipate stops earlier to drive smoother."
        ),
        "recklessness_score": (
            "Sharp direction changes detected. "
            "Smoother steering improves your score."
        ),
    }[worst]


# ---------------------------------------------------------------------------
# Quick demo — run with: python -m src.scoring  (from project root)
# ---------------------------------------------------------------------------

def _print_profile(row: "pd.Series", days_safe: int) -> None:
    features = row[_feature_cols].to_dict()
    result = score_driver(features, days_safe)

    bar_filled = "█" * (result["risk_score"] // 5)
    bar_empty  = "░" * (20 - result["risk_score"] // 5)

    print(f"  Driver       : {row['customer_id']}")
    print(f"  Risk Score   : {result['risk_score']:>3}/100  [{bar_filled}{bar_empty}]")
    print(f"  Risk Label   : {result['risk_label']}")
    print(f"  Driver Level : {result['driver_level']}")
    print(f"  Streak       : {result['streak_message']}")
    print(f"  Tip          : {result['tip']}")


if __name__ == "__main__":
    df = pd.read_csv(_HERE.parent / "data" / "features.csv")

    # Score every driver to identify one representative per risk tier
    df["score"] = (
        _model.predict_proba(df[_feature_cols])[:, 1] * 100
    ).round().astype(int)

    low_sample    = df[df["score"] <= 33].iloc[0]
    medium_sample = df[(df["score"] >= 34) & (df["score"] <= 66)].iloc[0]
    high_sample   = df[df["score"] >= 67].iloc[0]

    scenarios = [
        ("Low Risk Driver",    low_sample,    75),   # Gold tier: 61-90 days, low risk
        ("Medium Risk Driver", medium_sample, 45),   # Silver tier: 31-60 days, medium risk
        ("High Risk Driver",   high_sample,   5),    # Bronze tier: < 30 days
    ]

    print("=" * 60)
    print("  UBI Driver Risk Scorer — Sample Outputs")
    print("=" * 60)

    for label, row, days_safe in scenarios:
        print(f"\n── {label} (days_safe={days_safe}) ──")
        _print_profile(row, days_safe)

    print("\n" + "=" * 60)
