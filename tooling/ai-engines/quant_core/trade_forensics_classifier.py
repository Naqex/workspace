"""Outcome geometry taxonomy; labels do not identify skill or trader intent."""
from collections import Counter
import math
import numpy as np

LABELS = dict(W1="TRUE_STRUCTURAL_WIN", W2="FRAGILE_OR_LUCKY_WIN",
              L1="STOP_HUNTED_RIGHT_DIRECTION", L2="ROUND_TRIP_GIVEBACK",
              L3="EXHAUSTION_OR_CHASING_TRAP", L4="CLEAN_EXPECTED_LOSS")


def classify(row):
    for key in ("net_R", "MFE_R", "MAE_R"):
        if not math.isfinite(row[key]):
            raise ValueError("nonfinite_forensic_metric")
    if row["MFE_R"] < 0 or row["MAE_R"] < 0:
        raise ValueError("excursion_magnitudes_must_be_nonnegative")
    mfe, mae = row["MFE_R"], row["MAE_R"]
    late = row.get("late_jump_share", 0) >= .8 and row.get("profitable_fraction", 1) <= .2
    geometry = mae < .6 or mfe >= 1.5 * mae
    flags = dict(near_death=mae >= .8, late_windfall=late,
                 open_path_unknown=bool(row.get("open_path_unknown")),
                 L1=row["reason"] == "SL" and row.get("post_MFE_R", 0) >= 1,
                 L2=mfe >= .8,
                 L3=row.get("family") in ("F3", "F4") and mfe < .25 and
                    row.get("day_range_ATR", 0) is not None and row.get("day_range_ATR", 0) > .9)
    if row["net_R"] > 0:
        label = "W2" if flags["near_death"] or late or flags["open_path_unknown"] or not geometry else "W1"
    else:
        label = next((k for k in ("L1", "L2", "L3") if flags[k]), "L4")
    unknown = (flags["open_path_unknown"] or
               row["net_R"] <= 0 and row["reason"] == "SL" and row.get("post_path_unknown", True) or
               row["net_R"] <= 0 and row.get("family") in ("F3", "F4") and row.get("day_range_ATR") is None)
    return dict(label=label, label_name=LABELS[label], flags=flags,
                provisional=bool(unknown), causal_skill_or_manipulation_identified=False,
                giveback_bucket="0.80–<1.00" if .8 <= mfe < 1 else "1.00–<1.50" if 1 <= mfe < 1.5 else ">=1.50" if mfe >= 1.5 else None)


def excursions(times, executable_prices, *, entry, exit_at, entry_price, natural_units,
               side, exit_price, cutoff, stop_reason):
    times, prices = np.asarray(times), np.asarray(executable_prices)
    if len(times) != len(prices) or not len(times) or np.any(np.diff(times) < 0):
        raise ValueError("forensic_path_order_or_shape")
    if side not in (-1, 1) or natural_units <= 0 or not entry <= exit_at <= cutoff:
        raise ValueError("forensic_path_scope")
    use = (times >= entry) & (times <= exit_at)
    moves = side * (prices[use].astype(float) - entry_price) / natural_units
    moves = np.r_[moves, side * (exit_price - entry_price) / natural_units]
    final = side * (exit_price - entry_price) / natural_units
    early = np.flatnonzero(use & (times <= exit_at - 15 * 60000))
    late_share = max(0., (final - side * (float(prices[early[-1]]) - entry_price) / natural_units) / final) if len(early) and final > 0 else 0.
    post = (times > exit_at) & (times <= cutoff)
    after = side * (prices[post].astype(float) - entry_price) / natural_units
    def passage(level):
        hits = np.flatnonzero(after >= level)
        return int(times[post][hits[0]]) if len(hits) else None
    return dict(MFE_R=max(0., float(moves.max())), MAE_R=max(0., float(-moves.min())),
                profitable_fraction=float(np.mean(moves > 0)), late_jump_share=float(late_share),
                post_MFE_R=max(0., float(after.max())) if len(after) and stop_reason == "SL" else 0.,
                post_1R_at=passage(1) if stop_reason == "SL" else None,
                post_2R_at=passage(2) if stop_reason == "SL" else None)


def summarize(rows):
    total = len(rows)
    groups = []
    for label, name in LABELS.items():
        use = [r for r in rows if r["label"] == label]
        groups.append(dict(label=label, name=name, count=len(use), pct=100*len(use)/total if total else None,
                           net_R=sum(r["net_R"] for r in use), provisional=sum(r["provisional"] for r in use)))
    return dict(trades=total, net_R=sum(r["net_R"] for r in rows), groups=groups,
                provisional=sum(r["provisional"] for r in rows),
                overlapping_loss_flags={k:dict(count=sum(r["net_R"] <= 0 and r["flags"][k] for r in rows),
                    loss_R=sum(-r["net_R"] for r in rows if r["net_R"] <= 0 and r["flags"][k])) for k in ("L1", "L2", "L3")},
                W1_share=sum(r["label"] == "W1" for r in rows)/total if total else 0.)


def concentration(rows):
    ordered = sorted((r for r in rows if r["net_R"] > 0), key=lambda r: (-r["net_R"], r["trade_key"]))
    total = sum(r["net_R"] for r in rows)
    return dict(total_net_R=total, without_top5=total-sum(r["net_R"] for r in ordered[:5]),
                without_top10=total-sum(r["net_R"] for r in ordered[:10]),
                top10=[{k:r[k] for k in ("trade_key", "net_R", "label")} for r in ordered[:10]],
                hypothetical_removal_not_an_executable_strategy=True)
