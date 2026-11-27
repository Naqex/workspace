"""Two registered gates use only decision-known ratios, never labels or returns."""

import math

import numpy as np


def fit_thresholds(rows):
    if any(not 2018 <= r["year"] <= 2023 for r in rows):
        raise ValueError("Development-only threshold fit")
    result = {}
    for identity in sorted({r["id"] for r in rows if r["family"] in ("F3", "F4")}):
        values = [
            r["day_range_ATR"]
            for r in rows
            if r["id"] == identity and r["day_range_ATR"] is not None and math.isfinite(r["day_range_ATR"])
        ]
        result[identity] = float(np.quantile(values, 0.9, method="linear")) if values else None
    return result


def accept(row, gate, thresholds):
    if gate not in ("G_L3_A", "G_L3_B"):
        raise ValueError("Unregistered exhaustion gate")
    if row["family"] not in ("F3", "F4"):
        return True
    value = row["day_range_ATR"]
    limit = 0.9 if gate == "G_L3_A" else thresholds.get(row["id"])
    return bool(value is not None and math.isfinite(value) and limit is not None and value <= limit)


def resolution_cutoff(known_cutoff, *, step):
    if step not in (60000, 3600000):
        raise ValueError("Unregistered data resolution")
    return int(known_cutoff) // step * step
