"""Pure prepared-input admission gates; stdout consumers own optional evidence writes."""

import hashlib
import json
import math
import subprocess
from pathlib import Path

from quant_core.cost_gates import exceeds_friction_cap


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def toxicity_scale(profile, *, friction=None, median_stop=None, retention=None):
    reasons = []
    findings = profile.get("findings", [])
    if findings:
        reasons.extend(sorted({f["flag"] for f in findings}))
    if (
        profile.get("format") in (".ex4", ".ex5", ".dll", ".pyc")
        or profile.get("logic_recovery") == "UNAVAILABLE_FROM_STRINGS"
    ):
        reasons.append("BINARY_LOGIC_UNVERIFIED")
    if (
        friction is None
        or isinstance(friction, bool)
        or not math.isfinite(friction)
        or median_stop is None
        or isinstance(median_stop, bool)
        or not math.isfinite(median_stop)
        or retention is None
        or isinstance(retention, bool)
        or not math.isfinite(retention)
    ):
        reasons.append("SCALE_EVIDENCE_REQUIRED")
    elif friction < 0 or median_stop <= 0 or not 0 <= retention <= 1:
        reasons.append("INVALID_SCALE_INPUT")
    else:
        if exceeds_friction_cap(friction, median_stop, 25):
            reasons.append("FRICTION_FRAGILITY_SCALPER")
        elif exceeds_friction_cap(friction, median_stop, 12):
            reasons.append("STAGE0_FRICTION_SCALE_FAIL")
        if retention < 0.5:
            reasons.append("RETENTION_BELOW_HALF")
    return dict(
        gate=1,
        passed=not reasons,
        reasons=reasons,
        profile_sha256=content_hash(profile),
        full_logic_qualification=False,
        artifact_writes=0,
    )


def development_gate(candidate, baseline, *, inputs_sha256, recipe_sha256):
    reasons = []
    required = ("net_R", "equity_R_DD", "static_R_loss", "worst_daily_R", "max_open_risk_USD")
    for key in required:
        if any(
            isinstance(r.get(key), bool) or not isinstance(r.get(key), (int, float)) or not math.isfinite(r[key])
            for r in (candidate, baseline)
        ):
            reasons.append("MISSING_OR_NONFINITE_" + key)
        elif key != "net_R" and any(r[key] < 0 for r in (candidate, baseline)):
            reasons.append("NEGATIVE_RISK_METRIC_" + key)
    if not reasons:
        if candidate["net_R"] <= baseline["net_R"] + 1e-8:
            reasons.append("NET_NOT_HIGHER")
        if candidate["equity_R_DD"] >= baseline["equity_R_DD"] - 1e-8:
            reasons.append("EQUITY_DD_NOT_LOWER")
        for key in ("static_R_loss", "worst_daily_R", "max_open_risk_USD"):
            if candidate[key] > baseline[key] + 1e-8:
                reasons.append(key.upper() + "_INCREASED")
    for item in (candidate, baseline):
        clusters = item.get("cluster_R", [])
        if len(clusters) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in clusters
        ):
            reasons.append("DUAL_CLUSTER_FAIL")
        if item.get("development_years") != [2018, 2023]:
            reasons.append("DEVELOPMENT_SCOPE_REQUIRED")
        if item.get("SL_active_validated") is not True or item.get("signal_contract_status") != "CAUSAL_FROZEN":
            reasons.append("CAUSAL_SL_ACTIVE_EVIDENCE_REQUIRED")
    value = dict(
        schema="ResearchGate2-v1",
        gate=2,
        passed=not reasons,
        reasons=reasons,
        candidate=candidate,
        baseline=baseline,
        inputs_sha256=inputs_sha256,
        recipe_sha256=recipe_sha256,
    )
    return dict(value, evidence_sha256=content_hash(value))


def require_gate3(decision, freeze_path, *, observed_inputs_sha256, observed_recipe_sha256, repository):
    root = Path(repository).resolve()
    path = Path(freeze_path).resolve()
    relative = path.relative_to(root).as_posix()
    freeze = json.loads(path.read_text())
    committed = json.loads(subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + relative]))
    if committed != freeze:
        raise ValueError("COMMITTED_FREEZE_REQUIRED")
    for name, digest in freeze.get("source_pins", {}).items():
        with (root / name).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != digest:
                raise ValueError("FROZEN_SOURCE_CHANGED")
    payload = {k: v for k, v in decision.items() if k != "evidence_sha256"}
    if not freeze.get("source_pins") or freeze.get("decision_sha256") != content_hash(decision):
        raise ValueError("COMMITTED_DECISION_BINDING_REQUIRED")
    if decision.get("schema") != "ResearchGate2-v1" or decision.get("evidence_sha256") != content_hash(payload):
        raise ValueError("INVALID_GATE2_EVIDENCE")
    repeated = development_gate(
        decision["candidate"],
        decision["baseline"],
        inputs_sha256=observed_inputs_sha256,
        recipe_sha256=observed_recipe_sha256,
    )
    if repeated != decision or not repeated["passed"]:
        raise ValueError("DEVELOPMENT_GATE_NOT_SATISFIED")
    return dict(eligible_for_replay=True, not_broker_authority=True)
