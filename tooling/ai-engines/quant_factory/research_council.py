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

import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.holdout_guard import enforce_pre_holdout_dates  # noqa: E402
from quant_core.metrics import compute_pbo_cscv, deflated_sharpe_ratio_empirical  # noqa: E402

from quant_factory.eval_pipeline import benjamini_hochberg  # noqa: E402


@dataclass(frozen=True)
class KillCriteria:
    max_bh_q: float = 0.10
    min_dsr: float = 0.50
    min_cluster_b_sharpe: float = 0.40
    min_cost_breakeven_mult: float = 2.00
    max_corr_vs_incumbent: float = 0.25
    max_tail_corr_vs_incumbent: float = 0.40
    min_trades_cluster_b: int = 30
    max_pbo: float = 0.50
    require_incumbent: bool = False
    require_robustness_gate: bool = False


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
    robustness_report: dict | None = None
    cluster_b_dates: tuple[str, ...] | list[str] | None = None
    incumbent_dates: tuple[str, ...] | list[str] | None = None
    pbo_returns_matrix: np.ndarray | None = None
    pbo_n_slices: int = 16
    pbo_value: float | None = None
    trial_sharpes: tuple[float, ...] | list[float] | np.ndarray | None = None
    sr_trials_var: float | None = None
    trial_sharpes_are_annualized: bool = True


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


def _align_and_compute_corr_and_tail_corr(
    cand: np.ndarray,
    inc: np.ndarray | None,
    *,
    cand_dates: tuple[str, ...] | list[str] | None = None,
    inc_dates: tuple[str, ...] | list[str] | None = None,
    tail_pct: float = 0.05,
) -> dict[str, Any]:
    """Strictly align candidate vs incumbent daily returns (NEVER blindly slice mismatched arrays!)."""
    if inc is None:
        return {
            "skipped": True,
            "alignment_ok": True,
            "aligned_n": 0,
            "corr_all": 0.0,
            "corr_tail": 0.0,
            "detail": "INCUMBENT_NOT_PROVIDED",
        }
    a = np.asarray(cand, dtype=np.float64)
    b = np.asarray(inc, dtype=np.float64)

    if cand_dates is not None or inc_dates is not None:
        if cand_dates is None or inc_dates is None:
            return {
                "skipped": False,
                "alignment_ok": False,
                "aligned_n": 0,
                "corr_all": 1.0,
                "corr_tail": 1.0,
                "detail": "DATE_ALIGNMENT_INCOMPLETE: supply both cluster_b_dates and incumbent_dates",
            }
        if len(cand_dates) != len(a) or len(inc_dates) != len(b):
            return {
                "skipped": False,
                "alignment_ok": False,
                "aligned_n": 0,
                "corr_all": 1.0,
                "corr_tail": 1.0,
                "detail": (
                    f"DATE_LENGTH_MISMATCH: cand={len(a)}/dates={len(cand_dates)}, "
                    f"inc={len(b)}/dates={len(inc_dates)}"
                ),
            }
        enforce_pre_holdout_dates(cand_dates, context="research_council.G4.cluster_b_dates")
        enforce_pre_holdout_dates(inc_dates, context="research_council.G4.incumbent_dates")
        c_map = {str(d): float(v) for d, v in zip(cand_dates, a, strict=True)}
        i_map = {str(d): float(v) for d, v in zip(inc_dates, b, strict=True)}
        common = sorted(set(c_map) & set(i_map))
        if len(common) < 20:
            return {
                "skipped": False,
                "alignment_ok": False,
                "aligned_n": len(common),
                "corr_all": 1.0,
                "corr_tail": 1.0,
                "detail": f"INSUFFICIENT_DATE_OVERLAP: {len(common)} < 20 common dates",
            }
        a_al = np.array([c_map[d] for d in common], dtype=np.float64)
        b_al = np.array([i_map[d] for d in common], dtype=np.float64)
    else:
        if len(a) != len(b):
            return {
                "skipped": False,
                "alignment_ok": False,
                "aligned_n": 0,
                "corr_all": 1.0,
                "corr_tail": 1.0,
                "detail": (
                    f"UNALIGNED_LENGTH_MISMATCH: cand={len(a)} != inc={len(b)} "
                    "(provide cluster_b_dates & incumbent_dates for exact date alignment)"
                ),
            }
        if len(a) < 20:
            return {
                "skipped": False,
                "alignment_ok": False,
                "aligned_n": int(len(a)),
                "corr_all": 1.0,
                "corr_tail": 1.0,
                "detail": f"INSUFFICIENT_SAMPLES: n={len(a)} < 20",
            }
        a_al, b_al = a, b

    if not (np.all(np.isfinite(a_al)) and np.all(np.isfinite(b_al))):
        return {
            "skipped": False,
            "alignment_ok": False,
            "aligned_n": int(len(a_al)),
            "corr_all": 1.0,
            "corr_tail": 1.0,
            "detail": "NON_FINITE_RETURNS_IN_G4",
        }
    if float(np.std(a_al)) <= 1e-12 or float(np.std(b_al)) <= 1e-12:
        return {
            "skipped": False,
            "alignment_ok": True,
            "aligned_n": int(len(a_al)),
            "corr_all": 0.0,
            "corr_tail": 0.0,
            "detail": "OK_ZERO_VARIANCE",
        }
    corr_all = float(np.corrcoef(a_al, b_al)[0, 1])
    if not math.isfinite(corr_all):
        corr_all = 0.0
    cutoff = float(np.quantile(b_al, tail_pct))
    mask = b_al <= cutoff
    if int(mask.sum()) >= 5 and float(np.std(a_al[mask])) > 1e-12 and float(np.std(b_al[mask])) > 1e-12:
        corr_tail = float(np.corrcoef(a_al[mask], b_al[mask])[0, 1])
        if not math.isfinite(corr_tail):
            corr_tail = 0.0
    else:
        corr_tail = 0.0
    return {
        "skipped": False,
        "alignment_ok": True,
        "aligned_n": int(len(a_al)),
        "corr_all": round(corr_all, 4),
        "corr_tail": round(corr_tail, 4),
        "detail": "OK",
    }


def _compute_corr_and_tail_corr(
    cand: np.ndarray,
    inc: np.ndarray | None,
    tail_pct: float = 0.05,
    *,
    cand_dates: tuple[str, ...] | list[str] | None = None,
    inc_dates: tuple[str, ...] | list[str] | None = None,
) -> tuple[float, float]:
    res = _align_and_compute_corr_and_tail_corr(
        cand, inc, cand_dates=cand_dates, inc_dates=inc_dates, tail_pct=tail_pct
    )
    return float(res["corr_all"]), float(res["corr_tail"])


def _evaluate_g2_empirical_dsr(
    ret_b: np.ndarray,
    *,
    eff_n_trials: int,
    annualization_days: float,
    ledger_sharpes: list[float],
    ledger_supplied: bool,
    cand_in_ledger: bool,
    evidence: EvidenceBundle,
    eff_strict: bool,
) -> dict[str, Any]:
    """Evaluate Gate 2 DSR strictly via `quant_core.metrics.deflated_sharpe_ratio_empirical`."""
    r = np.asarray(ret_b, dtype=np.float64)
    r = r[np.isfinite(r)]
    ann_days = max(1, int(round(float(annualization_days))))
    m = max(1, int(eff_n_trials))

    if r.size < 3 or float(np.std(r, ddof=1)) <= 1e-15:
        return {
            "sr_ann": 0.0,
            "psr_gt0": 0.5,
            "dsr": 0.0,
            "sr_trials_var": 0.0,
            "expected_max_sr_ann": 0.0,
            "n_trials": m,
            "dsr_mode": "degenerate_zero_var",
            "empirical_variance_used": False,
            "g2_hard_fail": False,
        }

    psr_res = deflated_sharpe_ratio_empirical(r, n_trials=1, annualization_days=ann_days)
    cand_sr_ann = float(psr_res.observed_sr_annualized)
    psr_gt0 = float(psr_res.dsr)

    # Priority 1: Authoritative cross-sectional trial Sharpes from ExperimentLedger (DuckDB)
    dsr_res = None
    dsr_mode = ""
    empirical_used = False

    if ledger_supplied and ledger_sharpes:
        eff_sh = list(ledger_sharpes)
        if not cand_in_ledger:
            eff_sh.append(cand_sr_ann)
        if len(eff_sh) >= 2:
            dsr_res = deflated_sharpe_ratio_empirical(
                r,
                trial_sharpes=eff_sh,
                n_trials=max(m, len(eff_sh)),
                annualization_days=ann_days,
                sharpes_are_annualized=True,
            )
            dsr_mode = "empirical_ledger_sharpes"
            empirical_used = True

    # Priority 2: Explicit empirical trial_sharpes supplied in EvidenceBundle
    if dsr_res is None and evidence.trial_sharpes is not None:
        raw_ts = np.asarray(evidence.trial_sharpes, dtype=np.float64)
        if raw_ts.ndim == 1:
            fin_ts = raw_ts[np.isfinite(raw_ts)]
            if fin_ts.size >= 2 or m <= 1:
                dsr_res = deflated_sharpe_ratio_empirical(
                    r,
                    trial_sharpes=fin_ts,
                    n_trials=max(m, int(fin_ts.size)),
                    annualization_days=ann_days,
                    sharpes_are_annualized=bool(evidence.trial_sharpes_are_annualized),
                )
                dsr_mode = "empirical_trial_sharpes"
                empirical_used = True

    # Priority 3: Explicit empirical sr_trials_var supplied in EvidenceBundle
    if dsr_res is None and evidence.sr_trials_var is not None:
        dsr_res = deflated_sharpe_ratio_empirical(
            r,
            sr_trials_var=float(evidence.sr_trials_var),
            n_trials=m,
            annualization_days=ann_days,
            sharpes_are_annualized=bool(evidence.trial_sharpes_are_annualized),
        )
        dsr_mode = "empirical_sr_trials_var"
        empirical_used = True

    # Priority 4: Single-trial evaluation (M == 1 -> sr_star == 0, no variance required)
    if dsr_res is None and m <= 1:
        dsr_res = psr_res
        dsr_mode = "empirical_single_trial"
        empirical_used = True

    # Priority 5: Derive empirical cross-sectional Sharpes from 2D pbo_returns_matrix (for M > 1)
    if dsr_res is None and evidence.pbo_returns_matrix is not None:
        pmat = np.asarray(evidence.pbo_returns_matrix, dtype=np.float64)
        if pmat.ndim == 2 and pmat.shape[0] >= 3 and pmat.shape[1] >= 2 and bool(np.all(np.isfinite(pmat))):
            col_sd = np.std(pmat, axis=0, ddof=1)
            safe_sd = np.where(col_sd > 1e-15, col_sd, 1.0)
            col_sr_ann = np.where(
                col_sd > 1e-15,
                (np.mean(pmat, axis=0) / safe_sd) * math.sqrt(float(ann_days)),
                0.0,
            )
            dsr_res = deflated_sharpe_ratio_empirical(
                r,
                trial_sharpes=col_sr_ann,
                n_trials=max(m, int(col_sr_ann.size)),
                annualization_days=ann_days,
                sharpes_are_annualized=True,
            )
            dsr_mode = "empirical_pbo_matrix"
            empirical_used = True

    # Priority 6: Missing empirical variance for M > 1 -> fail closed when strict;
    # explicit variance fallback only in non-strict legacy mode
    if dsr_res is None:
        if eff_strict:
            return {
                "sr_ann": round(cand_sr_ann, 3),
                "psr_gt0": round(psr_gt0, 4),
                "dsr": 0.0,
                "sr_trials_var": 0.0,
                "expected_max_sr_ann": 0.0,
                "n_trials": m,
                "dsr_mode": "missing_empirical_variance_fail_closed",
                "empirical_variance_used": False,
                "g2_hard_fail": True,
            }
        dsr_res = deflated_sharpe_ratio_empirical(
            r,
            sr_trials_var=1.0 / float(max(1, r.size - 1)),
            n_trials=m,
            annualization_days=ann_days,
            sharpes_are_annualized=False,
        )
        dsr_mode = "legacy_non_strict_var_fallback"
        empirical_used = False

    return {
        "sr_ann": round(float(dsr_res.observed_sr_annualized), 3),
        "psr_gt0": round(psr_gt0, 4),
        "dsr": round(float(dsr_res.dsr), 4),
        "sr_trials_var": round(float(dsr_res.sr_trials_var), 8),
        "expected_max_sr_ann": round(float(dsr_res.expected_max_sr) * math.sqrt(float(ann_days)), 3),
        "n_trials": int(dsr_res.n_trials),
        "dsr_mode": dsr_mode,
        "empirical_variance_used": empirical_used,
        "g2_hard_fail": False,
    }


def critique_proposal(
    card: HypothesisCard,
    evidence: EvidenceBundle,
    *,
    ledger: Any | None = None,
    family_id: str | None = None,
    require_incumbent: bool | None = None,
    require_robustness_gate: bool | None = None,
    strict_gates: bool | None = None,
) -> dict:
    """Role 2 (Skeptical Red-Team Critic): audit proposal through automated fail-closed gates.

    When `ledger` (`ExperimentLedger`) is supplied, cumulative trial count `M` and historical
    `family_p_values` are read authoritatively from DuckDB so callers cannot self-report `M=1`.
    When `strict_gates=True` (or `ledger is not None`, or explicit `require_*` flags),
    skipping Gate 4 (`incumbent_daily_returns=None`) or Gate 6 (`robustness_report=None`)
    fails closed (`REJECT_KILLED`) instead of returning `APPROVE_FOR_INCUBATION`.
    """
    kc = card.kill_criteria
    card_errors = card.validate()

    eff_strict = bool(strict_gates) if strict_gates is not None else (ledger is not None)
    need_incumbent = (
        bool(require_incumbent)
        if require_incumbent is not None
        else (eff_strict or bool(kc.require_incumbent))
    )
    need_robustness = (
        bool(require_robustness_gate)
        if require_robustness_gate is not None
        else (eff_strict or bool(kc.require_robustness_gate))
    )

    # Gate 0: Holdout seal + card integrity (unconditional date guard BEFORE Gate 4 early-return!)
    if evidence.cluster_b_dates is not None:
        enforce_pre_holdout_dates(evidence.cluster_b_dates, context="research_council.G0.cluster_b_dates")
    if evidence.incumbent_dates is not None:
        enforce_pre_holdout_dates(evidence.incumbent_dates, context="research_council.G0.incumbent_dates")

    g0_pass = (int(evidence.holdout_rows_analysed) == 0) and (len(card_errors) == 0)
    g0_reasons = list(card_errors)
    if int(evidence.holdout_rows_analysed) != 0:
        g0_reasons.append(f"HOLDOUT_CONTAMINATION: holdout_rows_analysed={evidence.holdout_rows_analysed} != 0")

    raw_p_candidate = float(evidence.p_value_raw)
    if not math.isfinite(raw_p_candidate) or not (0.0 <= raw_p_candidate <= 1.0):
        raise ValueError(f"Invalid p_value_raw: {evidence.p_value_raw!r}")

    # Authoritative cumulative M, family p-values & empirical Sharpes from ExperimentLedger when supplied
    eff_family_id = family_id or card.counterparty_mechanism or card.hypothesis_id
    eff_n_trials = int(card.n_trials_cumulative)
    ledger_sharpes: list[float] = []
    cand_in_ledger = False
    if ledger is not None:
        if hasattr(ledger, "verify_integrity"):
            ledger.verify_integrity()
        ledger_m = int(ledger.get_cumulative_trial_count(eff_family_id))
        if hasattr(ledger, "query_family"):
            fam_rows = list(ledger.query_family(eff_family_id))
            ledger_pvals = [float(r["p_value"]) for r in fam_rows]
            ledger_sharpes = [
                float(r["sharpe"])
                for r in fam_rows
                if r.get("sharpe") is not None
                and not isinstance(r.get("sharpe"), bool)
                and math.isfinite(float(r["sharpe"]))
            ]
            matching_indices = [
                i for i, r in enumerate(fam_rows) if str(r.get("strategy_id")) == str(card.hypothesis_id)
            ]
        else:
            ledger_pvals = [float(p) for p in ledger.get_family_p_values(eff_family_id)]
            matching_indices = []
        if matching_indices:
            # Use authoritative logged p-value for card.hypothesis_id (conservative max if logged >1x);
            # NEVER allow self-reported p_value_raw to steal another strategy's smaller p-value.
            cand_in_ledger = True
            fam_p = list(ledger_pvals)
            idx = max(matching_indices, key=lambda i: fam_p[i])
            cand_p_raw = float(fam_p[idx])
            eff_n_trials = max(eff_n_trials, ledger_m, len(fam_p))
        else:
            fam_p = [*ledger_pvals, raw_p_candidate]
            idx = len(fam_p) - 1
            cand_p_raw = raw_p_candidate
            eff_n_trials = max(eff_n_trials, ledger_m + 1, len(fam_p))
    else:
        fam_p = list(evidence.family_p_values) if evidence.family_p_values else [raw_p_candidate]
        idx = min(max(0, int(evidence.candidate_index_in_family)), len(fam_p) - 1)
        cand_p_raw = raw_p_candidate

    # Gate 1: BH-FDR multiple-testing adjustment
    q_vals = benjamini_hochberg(fam_p)
    bh_q = float(q_vals[idx])
    g1_pass = bh_q <= kc.max_bh_q

    # Gate 2: Empirical Deflated Sharpe Ratio (DSR) + Cluster B Sharpe floor (no silent 1/(T-1) proxy)
    ret_a = np.asarray(evidence.cluster_a_returns, dtype=np.float64)
    ret_b = np.asarray(evidence.cluster_b_returns, dtype=np.float64)
    dsr_b = _evaluate_g2_empirical_dsr(
        ret_b,
        eff_n_trials=eff_n_trials,
        annualization_days=evidence.annualization_days,
        ledger_sharpes=ledger_sharpes,
        ledger_supplied=ledger is not None,
        cand_in_ledger=cand_in_ledger,
        evidence=evidence,
        eff_strict=eff_strict,
    )
    g2_hard_fail = bool(dsr_b["g2_hard_fail"])
    g2_pass = (not g2_hard_fail) and (dsr_b["dsr"] >= kc.min_dsr) and (dsr_b["sr_ann"] >= kc.min_cluster_b_sharpe)

    # Gate 3: Cost Stress Survival (exact breakeven cost multiple)
    cost_drag_1x = float(evidence.cost_1x_net) - float(evidence.cost_2x_net)
    if cost_drag_1x > 1e-9:
        breakeven_mult = 1.0 + float(evidence.cost_1x_net) / cost_drag_1x
    else:
        breakeven_mult = 99.0 if float(evidence.cost_1x_net) > 0 else 0.0
    g3_pass = (float(evidence.cost_2x_net) > 0.0) and (breakeven_mult >= kc.min_cost_breakeven_mult)

    # Gate 4: Orthogonality & Worst-5% Tail Correlation vs Incumbent (strict alignment!)
    g4_info = _align_and_compute_corr_and_tail_corr(
        ret_b,
        evidence.incumbent_daily_returns,
        cand_dates=evidence.cluster_b_dates,
        inc_dates=evidence.incumbent_dates,
        tail_pct=0.05,
    )
    corr_all = float(g4_info["corr_all"])
    corr_tail = float(g4_info["corr_tail"])
    g4_hard_fail = False
    if g4_info["skipped"] and need_incumbent:
        g4_pass = False
        g4_hard_fail = True
        g4_detail = "SKIPPED_MISSING_INCUMBENT_FAIL_CLOSED"
    elif not g4_info["alignment_ok"]:
        g4_pass = False
        g4_hard_fail = True
        g4_detail = str(g4_info["detail"])
    else:
        g4_pass = (abs(corr_all) <= kc.max_corr_vs_incumbent) and (corr_tail <= kc.max_tail_corr_vs_incumbent)
        g4_detail = str(g4_info["detail"])

    # Gate 5: Sample Size & Cluster A -> Cluster B Sign Consistency
    mean_a = float(np.mean(ret_a)) if len(ret_a) else 0.0
    mean_b = float(np.mean(ret_b)) if len(ret_b) else 0.0
    g5_pass = (int(evidence.n_trades_cluster_b) >= kc.min_trades_cluster_b) and (mean_a > 0.0) and (mean_b > 0.0)

    gates: dict[str, Any] = {
        "G0_seal_and_card": {"passed": g0_pass, "detail": "OK" if g0_pass else "; ".join(g0_reasons)},
        "G1_bh_fdr": {
            "passed": g1_pass,
            "p_raw": round(cand_p_raw, 5),
            "bh_q": round(bh_q, 5),
            "threshold": kc.max_bh_q,
            "m_family": len(fam_p),
        },
        "G2_dsr_and_sharpe": {
            "passed": g2_pass,
            "sr_ann_b": dsr_b["sr_ann"],
            "dsr_b": dsr_b["dsr"],
            "psr_gt0": dsr_b["psr_gt0"],
            "n_trials": eff_n_trials,
            "min_dsr": kc.min_dsr,
            "min_sr": kc.min_cluster_b_sharpe,
            "dsr_mode": dsr_b["dsr_mode"],
            "empirical_variance_used": dsr_b["empirical_variance_used"],
            "sr_trials_var": dsr_b["sr_trials_var"],
            "expected_max_sr_ann": dsr_b["expected_max_sr_ann"],
        },
        "G3_cost_stress": {
            "passed": g3_pass,
            "cost_1x_net": round(float(evidence.cost_1x_net), 4),
            "cost_2x_net": round(float(evidence.cost_2x_net), 4),
            "breakeven_mult": round(breakeven_mult, 2),
            "min_be": kc.min_cost_breakeven_mult,
        },
        "G4_orthogonality": {
            "passed": g4_pass,
            "corr_all": corr_all,
            "corr_tail_5pct": corr_tail,
            "aligned_n": int(g4_info["aligned_n"]),
            "skipped": bool(g4_info["skipped"]),
            "detail": g4_detail,
            "max_corr": kc.max_corr_vs_incumbent,
            "max_tail": kc.max_tail_corr_vs_incumbent,
        },
        "G5_sample_and_sign": {
            "passed": g5_pass,
            "n_trades_b": int(evidence.n_trades_cluster_b),
            "min_trades_b": kc.min_trades_cluster_b,
            "mean_a_pos": mean_a > 0.0,
            "mean_b_pos": mean_b > 0.0,
        },
    }

    # Gate 6: 4-Pillar Robustness Gate (fail-closed when required and skipped!)
    g6_hard_fail = False
    if evidence.robustness_report is not None:
        rb = evidence.robustness_report
        g6_verdict = str(rb.get("verdict", "FAIL_FRAGILE"))
        g6_pass = bool(rb.get("passed", False)) and g6_verdict == "PASS_ROBUST"
        g6_hard_fail = g6_verdict == "FAIL_FRAGILE"
        gates["G6_robustness_gate"] = {
            "passed": g6_pass,
            "verdict": g6_verdict,
            "failed_pillars": list(rb.get("failed_pillars", [])),
            "ranking_score_worst_year_p10_r": rb.get("ranking_score_worst_year_p10_r"),
        }
    elif need_robustness:
        g6_hard_fail = True
        gates["G6_robustness_gate"] = {
            "passed": False,
            "verdict": "SKIPPED_MISSING_REPORT",
            "failed_pillars": ["MISSING_ROBUSTNESS_REPORT"],
            "ranking_score_worst_year_p10_r": None,
        }

    # Gate 7: CSCV Probability of Backtest Overfitting (PBO <= max_pbo, default 0.50) via quant_core.metrics
    g7_hard_fail = False
    if evidence.pbo_returns_matrix is not None:
        pbo_res = compute_pbo_cscv(evidence.pbo_returns_matrix, n_slices=int(evidence.pbo_n_slices))
        pbo_val = float(pbo_res.pbo)
        g7_pass = pbo_val <= float(kc.max_pbo)
        g7_hard_fail = not g7_pass
        gates["G7_pbo_cscv"] = {
            "passed": g7_pass,
            "pbo": round(pbo_val, 4),
            "max_pbo": float(kc.max_pbo),
            "is_overfit": bool(pbo_res.is_overfit),
            "n_slices": int(pbo_res.n_slices),
            "n_trials": int(pbo_res.n_trials),
            "n_combinations": int(pbo_res.n_combinations),
        }
    elif evidence.pbo_value is not None:
        if isinstance(evidence.pbo_value, bool) or not math.isfinite(float(evidence.pbo_value)):
            raise ValueError(f"Invalid pbo_value: {evidence.pbo_value!r}")
        pbo_val = float(evidence.pbo_value)
        if not (0.0 <= pbo_val <= 1.0):
            raise ValueError(f"pbo_value must be in [0, 1], got {pbo_val}")
        g7_pass = pbo_val <= float(kc.max_pbo)
        g7_hard_fail = not g7_pass
        gates["G7_pbo_cscv"] = {
            "passed": g7_pass,
            "pbo": round(pbo_val, 4),
            "max_pbo": float(kc.max_pbo),
            "is_overfit": bool(pbo_val > float(kc.max_pbo)),
        }

    failed = [k for k, v in gates.items() if not v["passed"]]
    objections = []
    if not g0_pass:
        objections.append(f"BLOCKER G0: {gates['G0_seal_and_card']['detail']}")
    if not g1_pass:
        objections.append(f"BH-FDR fail: q={bh_q:.4f} > {kc.max_bh_q} (m={len(fam_p)})")
    if not g2_pass:
        objections.append(
            f"DSR/Sharpe fail: DSR={dsr_b['dsr']:.3f} (min {kc.min_dsr}), "
            f"SR_B={dsr_b['sr_ann']:.2f} (min {kc.min_cluster_b_sharpe})"
        )
    if not g3_pass:
        objections.append(
            f"Cost fragility: net@2x={evidence.cost_2x_net:.4f}, "
            f"breakeven={breakeven_mult:.2f}x < {kc.min_cost_breakeven_mult:.2f}x"
        )
    if not g4_pass:
        objections.append(
            f"Gate 4 orthogonality fail ({g4_detail}): corr_all={corr_all:.3f}, tail_corr={corr_tail:.3f}"
        )
    if not g5_pass:
        objections.append(
            f"Sample/sign fail: n_trades_B={evidence.n_trades_cluster_b}, "
            f"mean_A={mean_a:.6f}, mean_B={mean_b:.6f}"
        )
    if "G6_robustness_gate" in failed:
        g6 = gates["G6_robustness_gate"]
        objections.append(f"Robustness gate fail ({g6['verdict']}): pillars={g6['failed_pillars']}")
    if "G7_pbo_cscv" in failed:
        g7 = gates["G7_pbo_cscv"]
        objections.append(f"PBO overfit fail: pbo={g7['pbo']:.4f} > {g7['max_pbo']:.2f}")

    # Hard fail-closed decision rule
    hard_kill_gates = {"G0_seal_and_card", "G1_bh_fdr", "G3_cost_stress", "G5_sample_and_sign"}
    if g2_hard_fail:
        hard_kill_gates.add("G2_dsr_and_sharpe")
    if g4_hard_fail:
        hard_kill_gates.add("G4_orthogonality")
    if g6_hard_fail:
        hard_kill_gates.add("G6_robustness_gate")
    if g7_hard_fail:
        hard_kill_gates.add("G7_pbo_cscv")
    if not failed:
        verdict = "APPROVE_FOR_INCUBATION"
    elif (set(failed) & hard_kill_gates) or len(failed) >= 2:
        verdict = "REJECT_KILLED"
    else:
        # Only 1 soft gate failed (e.g., marginal DSR, borderline corr, or asymmetry/year warning)
        verdict = "CONDITIONAL_RETEST"

    payload = {
        "schema": "naqex-research-council-verdict-v1",
        "evaluated_utc": datetime.now(UTC).isoformat(),
        "critic_role": "Skeptical_RedTeam_Critic_v1",
        "ledger_enforced": ledger is not None,
        "family_id": eff_family_id,
        "effective_n_trials": eff_n_trials,
        "hypothesis": card.to_dict(),
        "gates": gates,
        "failed_gates": failed,
        "critic_objections": objections,
        "verdict": verdict,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    payload["verdict_sha256"] = hashlib.sha256(canonical).hexdigest()[:16]
    return payload
