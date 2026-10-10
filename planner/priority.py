"""Step 1: score every dealer 0-100 by business priority."""
import pandas as pd

DEFAULT_WEIGHTS = {
    "target_gap": 0.35,
    "pending_issues": 0.25,
    "days_since_visit": 0.25,
    "dealer_size": 0.15,
}
ISSUES_CAP = 5
DAYS_CAP = 30
HIGH_THRESHOLD = 40
MEDIUM_THRESHOLD = 30


def normalise_weights(weights: dict) -> dict:
    """Scale weights so they sum to 1 (sliders don't have to add up exactly)."""
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("At least one priority weight must be above zero.")
    return {k: v / total for k, v in weights.items()}


def tier(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def score_dealers(df: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Return a copy of df with factor columns, priority_score and priority_tier."""
    w = normalise_weights({**DEFAULT_WEIGHTS, **(weights or {})})
    out = df.copy()

    target = out["monthly_target_lakh"].astype(float)
    achieved = out["achieved_lakh"].astype(float)
    # 0 if already at or above target.
    gap = ((target - achieved) / target.where(target > 0)).fillna(0).clip(0, 1)
    issues = out["pending_issues"].clip(0, ISSUES_CAP) / ISSUES_CAP
    days = out["days_since_last_visit"].clip(0, DAYS_CAP) / DAYS_CAP
    max_target = target.max()
    size = target / max_target if max_target > 0 else target * 0

    out["f_target_gap"] = gap.round(3)
    out["f_pending_issues"] = issues.round(3)
    out["f_days_since_visit"] = days.round(3)
    out["f_dealer_size"] = size.round(3)
    out["priority_score"] = (
        100
        * (
            w["target_gap"] * gap
            + w["pending_issues"] * issues
            + w["days_since_visit"] * days
            + w["dealer_size"] * size
        )
    ).round(1)
    out["priority_tier"] = out["priority_score"].apply(tier)
    return out
