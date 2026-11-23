"""Institutional 2-Role Research Council: Proposer -> Skeptical Red-Team Critic (M2.3).

Enforces fail-closed scientific discipline for every new Naqex alpha hypothesis:
  1. `Proposer` submits a typed `HypothesisCard` (economic rationale, counterparty mechanism,
     causal invariants, and pre-registered hard kill criteria).
  2. `SkepticalRedTeamCritic` audits empirical Development evidence strictly on Cluster A -> blind Cluster B
     (`holdout_rows_analysed == 0`) through 6 automated gates:
       - Gate 0: Holdout seal & hypothesis completeness (economic rationale + kill criteria)
       - Gate 1: Benjamini-Hochberg FDR multiple-testing correction (`q <= max_bh_q`)
       - Gate 2: Bailey-Lopez de Prado Deflated Sharpe Ratio (`DSR >= min_dsr`) & OOS Sharpe floor
       - Gate 3: Cost Stress Survival (`2.0x` net positive & breakeven multiple >= `min_cost_breakeven_mult`)
       - Gate 4: Orthogonality & Worst-5% Tail Correlation vs incumbent portfolio
       - Gate 5: Cluster B sample size & Cluster A -> Cluster B sign consistency
  3. Outputs a deterministic JSON verdict (`APPROVE_FOR_INCUBATION`, `CONDITIONAL_RETEST`, or `REJECT_KILLED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio


@dataclass(frozen=True)
class KillCriteria:
    max_bh_q: float = 0.10
    min_dsr: float = 0.50
    min_cluster_b_sharpe: float = 0.40
    min_cost_breakeven_mult: float = 2.00
    max_corr_vs_incumbent: float = 0.25
    max_tail_corr_vs_incumbent: float = 0.40
    min_trades_cluster_b: int = 30


@dataclass(frozen=True)
class HypothesisCard:
    hypothesis_id: str
    title: str
    asset_universe: tuple[str, ...]
    timeframe: str
    counterparty_mechanism: str
    economic_rationale: str
    causal_invariants: tuple[str, ...]
    n_trials_cumulative: int
    kill_criteria: KillCriteria = field(default_factory=KillCriteria)
    proposer_role: str = "Quant_Proposer_v1"

    def validate(self) -> list[str]:
        errors = []
        if not self.hypothesis_id.strip():
            errors.append("Missing hypothesis_id")
        if len(self.economic_rationale.strip()) < 30:
            errors.append("economic_rationale too short (< 30 chars): must explain who loses to pay us")
        if not self.counterparty_mechanism.strip():
            errors.append("Missing counterparty_mechanism")
        if not self.asset_universe:
            errors.append("asset_universe cannot be empty")
        if not self.causal_invariants:
            errors.append("causal_invariants must list explicit look-ahead & financing checks")
        if self.n_trials_cumulative < 1:
            errors.append("n_trials_cumulative must be >= 1")
        return errors

    def to_dict(self) -> dict:
        d = asdict(self)
        d["asset_universe"] = list(self.asset_universe)
        d["causal_invariants"] = list(self.causal_invariants)
        return d


@dataclass(frozen=True)
class EvidenceBundle:
    cluster_a_returns: np.ndarray
    cluster_b_returns: np.ndarray
    p_value_raw: float
    family_p_values: tuple[float, ...]
    candidate_index_in_family: int
    cost_1x_net: float
    cost_2x_net: float
    n_trades_cluster_b: int
    incumbent_daily_returns: np.ndarray | None = None
    annualization_days: float = 252.0
    holdout_rows_analysed: int = 0


def propose_hypothesis(
    *,
    hypothesis_id: str,
    title: str,
    asset_universe: list[str] | tuple[str, ...],
    timeframe: str,
    counterparty_mechanism: str,
    economic_rationale: str,
    causal_invariants: list[str] | tuple[str, ...],
    n_trials_cumulative: int,
    kill_criteria: KillCriteria | None = None,
) -> HypothesisCard:
    """Role 1 (Proposer): construct and pre-validate a typed HypothesisCard."""
    card = HypothesisCard(
        hypothesis_id=hypothesis_id,
        title=title,
        asset_universe=tuple(asset_universe),
        timeframe=timeframe,
        counterparty_mechanism=counterparty_mechanism,
        economic_rationale=economic_rationale,
        causal_invariants=tuple(causal_invariants),
        n_trials_cumulative=int(n_trials_cumulative),
        kill_criteria=kill_criteria or KillCriteria(),
    )
    return card


def _compute_corr_and_tail_corr(cand: np.ndarray, inc: np.ndarray | None, tail_pct: float = 0.05) -> tuple[float, float]:
    if inc is None:
        return 0.0, 0.0
    a = np.asarray(cand, dtype=np.float64)
    b = np.asarray(inc, dtype=np.float64)
    n = min(len(a), len(b))
    if n < 20:
        return 0.0, 0.0
    a, b = a[:n], b[:n]
    if float(np.std(a)) <= 1e-12 or float(np.std(b)) <= 1e-12:
        return 0.0, 0.0
    corr_all = float(np.corrcoef(a, b)[0, 1])
    if not math.isfinite(corr_all):
        corr_all = 0.0
    cutoff = float(np.quantile(b, tail_pct))
    mask = b <= cutoff
    if int(mask.sum()) >= 5 and float(np.std(a[mask])) > 1e-12 and float(np.std(b[mask])) > 1e-12:
        corr_tail = float(np.corrcoef(a[mask], b[mask])[0, 1])
        if not math.isfinite(corr_tail):
            corr_tail = 0.0
    else:
        corr_tail = 0.0
    return round(corr_all, 4), round(corr_tail, 4)


def critique_proposal(card: HypothesisCard, evidence: EvidenceBundle) -> dict:
    """Role 2 (Skeptical Red-Team Critic): audit proposal through 6 automated fail-closed gates."""
    kc = card.kill_criteria
    card_errors = card.validate()

    # Gate 0: Holdout seal + card integrity
    g0_pass = (int(evidence.holdout_rows_analysed) == 0) and (len(card_errors) == 0)
    g0_reasons = list(card_errors)
    if int(evidence.holdout_rows_analysed) != 0:
        g0_reasons.append(f"HOLDOUT_CONTAMINATION: holdout_rows_analysed={evidence.holdout_rows_analysed} != 0")

    # Gate 1: BH-FDR multiple-testing adjustment
    fam_p = list(evidence.family_p_values) if evidence.family_p_values else [float(evidence.p_value_raw)]
    q_vals = benjamini_hochberg(fam_p)
    idx = min(max(0, int(evidence.candidate_index_in_family)), len(q_vals) - 1)
    bh_q = float(q_vals[idx])
    g1_pass = bh_q <= kc.max_bh_q

    # Gate 2: Deflated Sharpe Ratio (DSR) + Cluster B Sharpe floor
    ret_a = np.asarray(evidence.cluster_a_returns, dtype=np.float64)
    ret_b = np.asarray(evidence.cluster_b_returns, dtype=np.float64)
    dsr_b = deflated_sharpe_ratio(ret_b, n_trials=card.n_trials_cumulative, annualization=evidence.annualization_days)
    g2_pass = (dsr_b["dsr"] >= kc.min_dsr) and (dsr_b["sr_ann"] >= kc.min_cluster_b_sharpe)

    # Gate 3: Cost Stress Survival (exact breakeven cost multiple)
    cost_drag_1x = float(evidence.cost_1x_net) - float(evidence.cost_2x_net)
    if cost_drag_1x > 1e-9:
        breakeven_mult = 1.0 + float(evidence.cost_1x_net) / cost_drag_1x
    else:
        breakeven_mult = 99.0 if float(evidence.cost_1x_net) > 0 else 0.0
    g3_pass = (float(evidence.cost_2x_net) > 0.0) and (breakeven_mult >= kc.min_cost_breakeven_mult)

    # Gate 4: Orthogonality & Worst-5% Tail Correlation vs Incumbent
    corr_all, corr_tail = _compute_corr_and_tail_corr(ret_b, evidence.incumbent_daily_returns, tail_pct=0.05)
    g4_pass = (abs(corr_all) <= kc.max_corr_vs_incumbent) and (corr_tail <= kc.max_tail_corr_vs_incumbent)

    # Gate 5: Sample Size & Cluster A -> Cluster B Sign Consistency
    mean_a = float(np.mean(ret_a)) if len(ret_a) else 0.0
    mean_b = float(np.mean(ret_b)) if len(ret_b) else 0.0
    g5_pass = (int(evidence.n_trades_cluster_b) >= kc.min_trades_cluster_b) and (mean_a > 0.0) and (mean_b > 0.0)

    gates = {
        "G0_seal_and_card": {"passed": g0_pass, "detail": "OK" if g0_pass else "; ".join(g0_reasons)},
        "G1_bh_fdr": {"passed": g1_pass, "p_raw": round(float(evidence.p_value_raw), 5), "bh_q": round(bh_q, 5), "threshold": kc.max_bh_q, "m_family": len(fam_p)},
        "G2_dsr_and_sharpe": {"passed": g2_pass, "sr_ann_b": dsr_b["sr_ann"], "dsr_b": dsr_b["dsr"], "psr_gt0": dsr_b["psr_gt0"], "n_trials": card.n_trials_cumulative, "min_dsr": kc.min_dsr, "min_sr": kc.min_cluster_b_sharpe},
        "G3_cost_stress": {"passed": g3_pass, "cost_1x_net": round(float(evidence.cost_1x_net), 4), "cost_2x_net": round(float(evidence.cost_2x_net), 4), "breakeven_mult": round(breakeven_mult, 2), "min_be": kc.min_cost_breakeven_mult},
        "G4_orthogonality": {"passed": g4_pass, "corr_all": corr_all, "corr_tail_5pct": corr_tail, "max_corr": kc.max_corr_vs_incumbent, "max_tail": kc.max_tail_corr_vs_incumbent},
        "G5_sample_and_sign": {"passed": g5_pass, "n_trades_b": int(evidence.n_trades_cluster_b), "min_trades_b": kc.min_trades_cluster_b, "mean_a_pos": mean_a > 0.0, "mean_b_pos": mean_b > 0.0},
    }

    failed = [k for k, v in gates.items() if not v["passed"]]
    objections = []
    if not g0_pass:
        objections.append(f"BLOCKER G0: {gates['G0_seal_and_card']['detail']}")
    if not g1_pass:
        objections.append(f"BH-FDR fail: q={bh_q:.4f} > {kc.max_bh_q} (m={len(fam_p)})")
    if not g2_pass:
        objections.append(f"DSR/Sharpe fail: DSR={dsr_b['dsr']:.3f} (min {kc.min_dsr}), SR_B={dsr_b['sr_ann']:.2f} (min {kc.min_cluster_b_sharpe})")
    if not g3_pass:
        objections.append(f"Cost fragility: net@2x={evidence.cost_2x_net:.4f}, breakeven={breakeven_mult:.2f}x < {kc.min_cost_breakeven_mult:.2f}x")
    if not g4_pass:
        objections.append(f"Redundant alpha: corr_all={corr_all:.3f}, tail_corr={corr_tail:.3f} exceeds orthogonality budget")
    if not g5_pass:
        objections.append(f"Sample/sign fail: n_trades_B={evidence.n_trades_cluster_b}, mean_A={mean_a:.6f}, mean_B={mean_b:.6f}")

    # Hard fail-closed decision rule
    hard_kill_gates = {"G0_seal_and_card", "G1_bh_fdr", "G3_cost_stress", "G5_sample_and_sign"}
    if not failed:
        verdict = "APPROVE_FOR_INCUBATION"
    elif (set(failed) & hard_kill_gates) or len(failed) >= 2:
        verdict = "REJECT_KILLED"
    else:
        # Only 1 soft gate failed (e.g., marginal DSR or borderline correlation while FDR + Cost + Sign passed)
        verdict = "CONDITIONAL_RETEST"

    payload = {
        "schema": "naqex-research-council-verdict-v1",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "critic_role": "Skeptical_RedTeam_Critic_v1",
        "hypothesis": card.to_dict(),
        "gates": gates,
        "failed_gates": failed,
        "critic_objections": objections,
        "verdict": verdict,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    payload["verdict_sha256"] = hashlib.sha256(canonical).hexdigest()[:16]
    return payload
