"""Automated Prop-Firm Terms & Clause Drift Auditor powered by TypeSafe (`jev-1.14.0`).

Uses TypeSafe's `parallel_questions` pattern (1 batched System One request with 6 atomic
Noul questions over raw prop-firm Terms/FAQ text) + an explicit deterministic Truth Table
comparing observed clauses against Naqex's frozen Prop-Firm baseline (`FTMO Swing`,
`FTMO Standard`, `The5ers High Stakes`, `Topstep 50K`).

SAFETY & GOVERNANCE:
  - Pure read-only compliance auditor (`ORDER_SEND_CAPABLE = False`).
  - Opt-in API execution: uses `TYPESAFE_API_KEY` from env only when `--live` / live call
    is invoked; supports deterministic injected `transport` for 100% offline unit tests.
  - Fail-closed: API errors raise cleanly (NEVER coerced to "compliant"); uncertain Nouls
    (`0.30 < p < 0.70`) emit `UNCERTAIN_MANUAL_REVIEW` rather than silent pass.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

QF_DIR = Path(__file__).resolve().parent
if str(QF_DIR) not in sys.path:
    sys.path.insert(0, str(QF_DIR))

import typesafe_client as ts  # noqa: E402

ORDER_SEND_CAPABLE = False

# All question wording kept in one auditable module per `typesafe-ai` skill
PROP_TERMS_QUESTIONS: dict[str, dict[str, Any]] = {
    "allows_overnight_weekend": {
        "type": "noul",
        "instructions": "Does `policy_text` permit traders to hold open positions overnight and over the weekend?",
        "criteria": {
            "true": "Holding positions overnight and over weekends is explicitly allowed.",
            "false": "Positions must be closed daily or overnight/weekend holding is prohibited.",
        },
    },
    "restricts_news_window": {
        "type": "noul",
        "instructions": "Does `policy_text` prohibit or restrict opening, closing, or triggering SL/TP orders within a time window around high-impact macroeconomic news releases?",
        "criteria": {
            "true": "There is a ban or time-window restriction around red/high-impact news events.",
            "false": "Trading during macroeconomic news releases is permitted with no news-window restriction.",
        },
    },
    "bans_third_party_copy_ea": {
        "type": "noul",
        "instructions": "Does `policy_text` prohibit third-party commercial EAs, trade copiers, or cross-account copy trading?",
        "criteria": {
            "true": "Third-party commercial EAs, signal copiers, or cross-user copy trading is prohibited.",
            "false": "Third-party EAs and external copy trading are explicitly permitted.",
        },
    },
    "has_consistency_cap": {
        "type": "noul",
        "instructions": "Does `policy_text` enforce a maximum single-day profit share cap (such as no single day exceeding 50% or 40% of total profit target)?",
        "criteria": {
            "true": "A single day's profit cannot exceed a capped percentage of total target (consistency rule).",
            "false": "No single-day profit percentage cap applies (a minimum count of profitable days is not a cap).",
        },
    },
    "requires_custom_ea_approval": {
        "type": "noul",
        "instructions": "Does `policy_text` require traders to contact support or obtain explicit prior approval before running their own personal custom Expert Advisor?",
        "criteria": {
            "true": "Traders must notify support or receive approval before using custom personal EAs.",
            "false": "Personal custom EAs can be used without prior support approval, or custom EAs are completely banned.",
        },
    },
    "uses_trailing_intraday_dd": {
        "type": "noul",
        "instructions": "Does `policy_text` use an intraday trailing drawdown (trailing unrealized high-water mark intra-trade) rather than static balance or end-of-day drawdown?",
        "criteria": {
            "true": "Maximum loss limit trails intraday unrealized peak equity.",
            "false": "Drawdown is static from initial balance or trails only end-of-day (EOD) closed balance.",
        },
    },
}

# Known Naqex verified baselines (2026-11-24) — drift against these raises RULE_DRIFT_DETECTED
FIRM_BASELINES: dict[str, dict[str, bool]] = {
    "ftmo_swing": {
        "allows_overnight_weekend": True,
        "restricts_news_window": False,
        "bans_third_party_copy_ea": True,
        "has_consistency_cap": False,
        "requires_custom_ea_approval": False,
        "uses_trailing_intraday_dd": False,
    },
    "ftmo_standard": {
        "allows_overnight_weekend": False,
        "restricts_news_window": True,
        "bans_third_party_copy_ea": True,
        "has_consistency_cap": False,
        "requires_custom_ea_approval": False,
        "uses_trailing_intraday_dd": False,
    },
    "the5ers_high_stakes": {
        "allows_overnight_weekend": True,
        "restricts_news_window": True,
        "bans_third_party_copy_ea": True,
        "has_consistency_cap": False,
        "requires_custom_ea_approval": False,
        "uses_trailing_intraday_dd": False,
    },
    "topstep_50k": {
        "allows_overnight_weekend": False,
        "restricts_news_window": False,
        "bans_third_party_copy_ea": True,
        "has_consistency_cap": True,
        "requires_custom_ea_approval": False,
        "uses_trailing_intraday_dd": False,
    },
}


def audit_prop_terms_text(
    policy_text: str,
    *,
    firm_id: str | None = None,
    baseline: Mapping[str, bool] | None = None,
    yes_threshold: float = 0.70,
    no_threshold: float = 0.30,
    model: str = ts.DEFAULT_MODEL,
    transport: Callable[..., dict[str, Any]] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Audit prop-firm policy text with 1 batched TypeSafe call + deterministic drift Truth Table."""
    clean_text = str(policy_text or "").strip()
    if len(clean_text) < 20:
        raise ValueError("policy_text is too short (< 20 chars) for reliable clause auditing")

    expected = dict(baseline) if baseline is not None else dict(FIRM_BASELINES.get(str(firm_id or ""), {}))
    res = ts.call_system_one(
        {"policy_text": clean_text[:28_000]},
        PROP_TERMS_QUESTIONS,
        model=model,
        transport=transport,
        api_key=api_key,
    )
    answers = res["answers"]

    clauses: dict[str, dict[str, Any]] = {}
    drift_alerts: list[str] = []
    uncertain_fields: list[str] = []

    for qid in PROP_TERMS_QUESTIONS:
        prob = ts.extract_noul(answers, qid)
        label = ts.classify_noul(prob, yes_threshold=yes_threshold, no_threshold=no_threshold)
        exp_val = expected.get(qid)
        status = "OBSERVED"
        if label == "UNCERTAIN":
            status = "UNCERTAIN_MANUAL_REVIEW"
            uncertain_fields.append(qid)
        elif exp_val is not None:
            observed_bool = label == "YES"
            if observed_bool != bool(exp_val):
                status = "RULE_DRIFT_DETECTED"
                drift_alerts.append(f"{qid}: expected={exp_val} observed={observed_bool} (p={prob:.3f})")
            else:
                status = "MATCH"
        clauses[qid] = {
            "noul": round(prob, 4),
            "label": label,
            "baseline_expected": exp_val,
            "status": status,
        }

    # Explicit deterministic Truth Table for overall audit verdict
    if drift_alerts:
        verdict = "HALT_RULE_DRIFT_REVIEW"
    elif uncertain_fields:
        verdict = "MANUAL_REVIEW_UNCERTAIN"
    else:
        verdict = "PASS_MATCHES_BASELINE" if expected else "OBSERVED_NO_BASELINE"

    return {
        "schema": "naqex-prop-terms-audit-v1",
        "audited_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "firm_id": firm_id,
        "model": res["model"],
        "verdict": verdict,
        "drift_alerts": drift_alerts,
        "uncertain_fields": uncertain_fields,
        "clauses": clauses,
        "latency_ms": res["latency_ms"],
        "usage": res["usage"],
        "est_cost_usd": res["est_cost_usd"],
        "order_send_capable": ORDER_SEND_CAPABLE,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit Prop-Firm Terms/FAQ text for clause drift using TypeSafe jev-1.14.0.")
    ap.add_argument("--file", type=Path, required=True, help="Path to local Terms/FAQ text or Markdown snapshot.")
    ap.add_argument("--firm", choices=sorted(FIRM_BASELINES.keys()), default=None, help="Optional baseline firm ID.")
    ap.add_argument("--model", default=ts.DEFAULT_MODEL)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args(argv)

    text = args.file.read_text(encoding="utf-8", errors="ignore")
    report = audit_prop_terms_text(text, firm_id=args.firm, model=args.model)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload + "\n", encoding="utf-8", newline="\n")
    print(payload)
    return 0 if report["verdict"] in ("PASS_MATCHES_BASELINE", "OBSERVED_NO_BASELINE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
