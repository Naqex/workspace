"""Naqex Harness Engineering Architecture Gate ([ARCH-01..07]).

Every violation prints in the canonical agent-actionable format:
  [ARCH-XX] <file>:<line> | <issue> | REMEDIATION: <exact fix instruction>

Rules:
  [ARCH-01] Top-level `scipy` import in hot-path modules (`quant_factory/__init__.py`,
            `quant_factory/data_store.py`, `quant_factory/eval_pipeline.py`,
            `quant_factory/prop_engine.py`, `quant_core/*`).
  [ARCH-02] Python `assert` guarding Holdout/cutoff (`STOP`/`2025`/`HOLDOUT`/`holdout`)
            in `quant_core/`, `quant_factory/`, `hot_m1_cache.py`, `pass27*`, `pass24*`,
            `whitebox_discovery.py` (stripped under `python -O`).
  [ARCH-03] New loose `.py` files at `tooling/ai-engines/` root not in the maintained
            baseline allowlist.
  [ARCH-04] Orphan repo skills (`in_deg == 0 and out_deg == 0`) in `.agents/skills/*/SKILL.md`
            outside the explicit domain-standalone whitelist.
  [ARCH-05] Context/index byte bloat: `planning/research/README.md <= 15_000 B`
            (advisory warning by default; hard failure with `--strict`) and
            `planning/CURRENT-CONTEXT.md <= 12_000 B` (always hard failure).
  [ARCH-06] Mixed percent / fraction unit suffix bounds on `tooling/ai-engines/configs/ssot/*.json`
            (`_frac` finite numeric in [0, 1], `_pct` finite numeric in [0, 100]).
  [ARCH-07] Copyleft / Commons-Clause import ban (`backtesting`, `backtrader`, `vectorbt`)
            across Naqex core packages (`quant_core`, `quant_factory`, `ops_cloud`).
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HOT_PATH_SCIPY_FILES: tuple[str, ...] = (
    "tooling/ai-engines/quant_factory/__init__.py",
    "tooling/ai-engines/quant_factory/data_store.py",
    "tooling/ai-engines/quant_factory/eval_pipeline.py",
    "tooling/ai-engines/quant_factory/prop_engine.py",
)

ORPHAN_SKILL_WHITELIST: frozenset[str] = frozenset(
    {
        "chart-guided-tutoring",
        "reverse-engineering",
    }
)

BANNED_COPYLEFT_ROOTS: frozenset[str] = frozenset(
    {
        "backtesting",
        "backtrader",
        "vectorbt",
    }
)

README_MAX_BYTES = 15_000
CURRENT_CONTEXT_MAX_BYTES = 12_000

_HOLDOUT_ASSERT_RE = re.compile(r"\b(?:STOP|HOLDOUT|holdout_rows|cutoff_day)\b|2025|holdout", re.IGNORECASE)

# Baseline allowlist of existing loose root `.py` files in `tooling/ai-engines/` (233 files, tightened post-L9).
# Shrinking this list as files migrate to `legacy/` or `experiments/` only tightens the rule.
ROOT_AI_ENGINES_PY_ALLOWLIST: frozenset[str] = frozenset(
    {
        "abnormal_day_component.py",
        "abnormal_day_feature.py",
        "bot_breakout_forensic.py",
        "bot_live_auditor.py",
        "bot_live_leaderboard.py",
        "candle_source_provenance.py",
        "cash_rsi_signal_oracle.py",
        "dukascopy_bi5.py",
        "ecb_conference_source.py",
        "eia_release_dates.py",
        "engine_worker.py",
        "equity_calendar_component.py",
        "eurusd_b0.py",
        "eurusd_b0_source.py",
        "eurusd_funnel_audit.py",
        "eurusd_post_fomc_component.py",
        "evidence_compaction.py",
        "explicit_m1_view.py",
        "fixing_clock_probe.py",
        "fomc_price_component.py",
        "forex_discovery_report.py",
        "forex_ml_study.py",
        "forex_research.py",
        "forex_screen_diagnostics.py",
        "forex_study_batch.py",
        "forex_time_fit.py",
        "forex_uncertainty.py",
        "forex_wrapper_attribution.py",
        "ftmo_connection.py",
        "ftmo_free_trial_adapter.py",
        "ftmo_spread_sessions.py",
        "ftmo_trial_runner.py",
        "fx_pair_formation.py",
        "gold_continuous_b1.py",
        "gold_continuous_ledger.py",
        "gold_intraday_quality.py",
        "gold_ml_sl_labels.py",
        "gold_session_component.py",
        "golden_event_parity.py",
        "h4_sma_signal_oracle.py",
        "hermes_worker.py",
        "hierarchical_attribution.py",
        "hot_m1_cache.py",
        "inbox_intake_scanner.py",
        "independent_ledger_auditor.py",
        "index_cash_close_tick_component.py",
        "index_close_momentum.py",
        "index_consensus_component.py",
        "index_daily_reversion.py",
        "index_m1_book.py",
        "index_noise_study.py",
        "index_overnight_reversal_component.py",
        "index_preclose_reversion.py",
        "index_rest_of_day_component.py",
        "index_tick_review.py",
        "index_time_series_momentum.py",
        "intraday_shock_component.py",
        "japan_us_cash_reaction_component.py",
        "local_session_probe.py",
        "metals_pair_formation.py",
        "monthly_trend_component.py",
        "mq5_whitebox_exporter.py",
        "multiasset_monthly_input.py",
        "nasdaq_cash_calendar.py",
        "nasdaq_cash_reversion_component.py",
        "nasdaq_h4_study.py",
        "nasdaq_intraday_momentum_component.py",
        "nasdaq_noise14.py",
        "nasdaq_opening5_bounds.py",
        "nasdaq_opening5_orb.py",
        "nasdaq_overnight_reversal_component.py",
        "native_ftmo_asym_forensics.py",
        "native_ftmo_asym_pivot.py",
        "native_ftmo_monfri_screen.py",
        "native_ftmo_monfri_seal.py",
        "native_ftmo_swing.py",
        "ny_fx_gap_scenarios.py",
        "ny_fx_latency.py",
        "ny_fx_reversal.py",
        "options_expiry_component.py",
        "paperclip_setup.py",
        "paperclip_strategy_skills.py",
        "pass10_institutional_flow.py",
        "pass11_gbpusd_m1.py",
        "pass11_portfolio.py",
        "pass12_us500_ny_orb.py",
        "pass12_usdjpy_forensic.py",
        "pass13_fx_sweep.py",
        "pass13_intel_cleanroom.py",
        "pass13_us500_explicit.py",
        "pass14_intel_top15_batch.py",
        "pass15_ftmo_native_engine2.py",
        "pass16_dual_track.py",
        "pass17_usdjpy_forensic_cross.py",
        "pass18_opensource_non_usdjpy.py",
        "pass19_us500_supertrend_yencross.py",
        "pass20_pos_swap_carry_3engine.py",
        "pass22_gbpusd_volhigh_3engine.py",
        "pass23_ftmo_lifecycle_sim.py",
        "pass23_xau_indices_discovery.py",
        "pass24_mtf_new_archetypes.py",
        "pass25_new_assets_engine56.py",
        "pass26_cross_asset_rs.py",
        "pass27_portfolio_m1_phase_audit.py",
        "pass28_final_discovery_rednews_frontier.py",
        "pass5_usdjpy_tokyo.py",
        "pass6_breakout_execution.py",
        "pass7_fx_scout.py",
        "pass7b_qdm_m1.py",
        "pass7b_usdjpy_equity.py",
        "pass7b_usdjpy_research.py",
        "pass8_mql5_public.py",
        "pass8_usdjpy_gaps.py",
        "pass9_bot_round2.py",
        "pre_ecb_path_risk.py",
        "pre_ecb_session_risk.py",
        "prepare_xau_intraday_views.py",
        "prop_atlas_core.py",
        "prop_atlas_policy.py",
        "prop_atlas_report.py",
        "prop_atlas_scan.py",
        "prop_atlas_source.py",
        "prop_atlas_uncertainty.py",
        "prop_campaign_accounts.py",
        "prop_campaign_exits.py",
        "prop_campaign_report.py",
        "prop_campaign_review.py",
        "prop_campaign_source.py",
        "prop_cocore_audit.py",
        "prop_cocore_v4.py",
        "prop_portfolio_accounts.py",
        "prop_portfolio_common.py",
        "prop_portfolio_policy.py",
        "prop_portfolio_regime.py",
        "prop_portfolio_review.py",
        "prop_portfolio_scan.py",
        "prop_portfolio_sources.py",
        "prop_portfolio_ticks.py",
        "prop_v10_signals.py",
        "prop_v10_source.py",
        "prop_v11_campaign.py",
        "prop_v12_campaign.py",
        "prop_v12_signals.py",
        "prop_v14_campaign.py",
        "prop_v14_paths.py",
        "prop_v14_source.py",
        "prop_v15_common.py",
        "prop_v16_common.py",
        "prop_v17_common.py",
        "prop_v18_common.py",
        "prop_v19_common.py",
        "prop_v20_common.py",
        "prop_v5_account.py",
        "prop_v5_common.py",
        "prop_v5_data.py",
        "prop_v5_replay.py",
        "prop_v6_account.py",
        "prop_v6_common.py",
        "prop_v6_data.py",
        "prop_v6_paths.py",
        "prop_v6_replay.py",
        "prop_v6_review.py",
        "prop_v6_signals.py",
        "prop_v7_accounts.py",
        "prop_v7_common.py",
        "prop_v7_paths.py",
        "prop_v7_review.py",
        "prop_v8_calendar_correction.py",
        "prop_v8_campaign.py",
        "prop_v8_common.py",
        "prop_v8_review.py",
        "prop_v8_signals.py",
        "prop_v8_source.py",
        "prop_v9.py",
        "prop_v9_eurusd.py",
        "quant_test_suite.py",
        "quote_bar_oracle.py",
        "rd_research.py",
        "relative_equity_component.py",
        "research_consumption.py",
        "research_input_admission.py",
        "research_inventory.py",
        "review_index_noise.py",
        "review_us500_m15_opening.py",
        "review_us500_multiframe.py",
        "review_us500_strategy_fit.py",
        "round_level_component.py",
        "round_level_feature.py",
        "run_eurusd_b0.py",
        "run_gold_continuous_b2.py",
        "run_prop_campaign.py",
        "run_us500_channel_history.py",
        "run_us500_m15_opening_screen.py",
        "run_us500_ma_reclaim.py",
        "run_us500_multiframe.py",
        "run_us500_recent_screen.py",
        "seal_gbpjpy_m1.py",
        "sealed_m1_review.py",
        "selective_win_diagnosis.py",
        "shadow_night.py",
        "shadow_reconcile.py",
        "shadow_sessions.py",
        "shadow_watch.py",
        "spot_workflow.py",
        "strategy_evidence.py",
        "studio_observation.py",
        "studio_workflows.py",
        "system_doctor.py",
        "us500_continuation_diagnostics.py",
        "us500_euopen_component.py",
        "us500_fomc_momentum_component.py",
        "us500_frequency_audit.py",
        "us500_inventory_condition.py",
        "us500_m15_opening_screen.py",
        "us500_ma_reclaim.py",
        "us500_multiframe.py",
        "us500_opportunities.py",
        "us500_recent_setups.py",
        "us500_same_clock.py",
        "us500_year_source.py",
        "weekend_gap_component.py",
        "whitebox_discovery.py",
        "wti_session_source.py",
        "xau_a_validation.py",
        "xau_a_validation_source.py",
        "xau_h1_execution.py",
        "xau_h1_execution_prepare.py",
        "xau_h1_execution_review.py",
        "xau_h1_stage0_scan.py",
        "xau_h1_stage0_source.py",
        "xau_intraday_b0.py",
        "xau_intraday_source.py",
        "xau_scale_horizon_audit.py",
    }
)


@dataclass(frozen=True)
class ArchViolation:
    rule: str
    file: str
    line: int
    issue: str
    remediation: str
    severity: str = "error"  # "error" | "warning"

    def format_line(self) -> str:
        prefix = f"[{self.rule}]"
        sev = " (ADVISORY)" if self.severity == "warning" else ""
        return f"{prefix} {self.file}:{self.line} | {self.issue}{sev} | REMEDIATION: {self.remediation}"


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_python(path: Path, *, required_substrings: tuple[str, ...] = ()) -> tuple[str, ast.Module | None]:
    src = path.read_text(encoding="utf-8", errors="replace")
    if required_substrings and not any(tok in src for tok in required_substrings):
        return src, None
    try:
        return src, ast.parse(src, filename=str(path))
    except SyntaxError:
        return src, None


def _is_type_checking_guard(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def _iter_module_level_stmts(stmts: list[ast.stmt]) -> list[ast.stmt]:
    """Yield statements executed at module import time (including class bodies; excluding def/TYPE_CHECKING)."""
    out: list[ast.stmt] = []
    for stmt in stmts:
        out.append(stmt)
        if isinstance(stmt, ast.ClassDef):
            out.extend(_iter_module_level_stmts(stmt.body))
        elif isinstance(stmt, ast.If):
            if _is_type_checking_guard(stmt.test):
                out.extend(_iter_module_level_stmts(stmt.orelse))
            else:
                out.extend(_iter_module_level_stmts(stmt.body))
                out.extend(_iter_module_level_stmts(stmt.orelse))
        elif isinstance(stmt, (ast.With, ast.AsyncWith, ast.For, ast.AsyncFor)):
            out.extend(_iter_module_level_stmts(stmt.body))
            out.extend(_iter_module_level_stmts(getattr(stmt, "orelse", [])))
        elif isinstance(stmt, ast.Try):
            out.extend(_iter_module_level_stmts(stmt.body))
            for handler in stmt.handlers:
                out.extend(_iter_module_level_stmts(handler.body))
            out.extend(_iter_module_level_stmts(stmt.orelse))
            out.extend(_iter_module_level_stmts(stmt.finalbody))
    return out


def check_arch_01_hot_path_scipy(root: Path) -> list[ArchViolation]:
    """[ARCH-01] Ban top-level `scipy` imports in hot-path modules."""
    targets: list[Path] = []
    for rel in HOT_PATH_SCIPY_FILES:
        p = root / rel
        if p.is_file():
            targets.append(p)
    qc_dir = root / "tooling/ai-engines/quant_core"
    if qc_dir.is_dir():
        targets.extend(sorted(qc_dir.rglob("*.py")))

    remediation = (
        "Replace top-level scipy import with stdlib statistics.NormalDist() "
        "(use .inv_cdf instead of .ppf) or move scipy import inside the specific function that uses it."
    )
    violations: list[ArchViolation] = []
    seen: set[Path] = set()
    for path in targets:
        rp = path.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        _, tree = _parse_python(path, required_substrings=("scipy",))
        if tree is None:
            continue
        for stmt in _iter_module_level_stmts(tree.body):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.name == "scipy" or alias.name.startswith("scipy."):
                        violations.append(
                            ArchViolation(
                                rule="ARCH-01",
                                file=_rel(path, root),
                                line=stmt.lineno,
                                issue=f"Top-level scipy import ('import {alias.name}') in hot-path module",
                                remediation=remediation,
                            )
                        )
            elif isinstance(stmt, ast.ImportFrom):
                mod = stmt.module or ""
                if mod == "scipy" or mod.startswith("scipy."):
                    violations.append(
                        ArchViolation(
                            rule="ARCH-01",
                            file=_rel(path, root),
                            line=stmt.lineno,
                            issue=f"Top-level scipy import ('from {mod} import ...') in hot-path module",
                            remediation=remediation,
                        )
                    )
    return violations


def check_arch_02_holdout_asserts(root: Path) -> list[ArchViolation]:
    """[ARCH-02] Ban Python `assert` guarding Holdout/cutoff (`STOP`/`2025`/`HOLDOUT`/`holdout`)."""
    ai_dir = root / "tooling/ai-engines"
    targets: list[Path] = []
    for sub in ("quant_core", "quant_factory"):
        d = ai_dir / sub
        if d.is_dir():
            targets.extend(sorted(d.rglob("*.py")))
    for fixed in ("hot_m1_cache.py", "whitebox_discovery.py"):
        p = ai_dir / fixed
        if p.is_file():
            targets.append(p)
    if ai_dir.is_dir():
        targets.extend(sorted(ai_dir.glob("pass27*.py")))
        targets.extend(sorted(ai_dir.glob("pass24*.py")))

    remediation = (
        "Replace Python 'assert' (disabled under 'python -O') with an explicit fail-closed check: "
        "'if <violated_condition>: raise HoldoutLockError(...)'."
    )
    violations: list[ArchViolation] = []
    seen: set[Path] = set()
    for path in targets:
        rp = path.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        src = path.read_text(encoding="utf-8", errors="replace")
        if "assert" not in src or not _HOLDOUT_ASSERT_RE.search(src):
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue
        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            start_ln = max(1, node.lineno)
            end_ln = getattr(node, "end_lineno", start_ln) or start_ln
            seg = "\n".join(lines[start_ln - 1 : end_ln])
            if not seg:
                try:
                    seg = ast.unparse(node)
                except Exception:
                    seg = ""
            if _HOLDOUT_ASSERT_RE.search(seg):
                snippet = " ".join(seg.strip().split())
                if len(snippet) > 96:
                    snippet = snippet[:93] + "..."
                violations.append(
                    ArchViolation(
                        rule="ARCH-02",
                        file=_rel(path, root),
                        line=node.lineno,
                        issue=f"Holdout/cutoff guard uses Python assert ({snippet})",
                        remediation=remediation,
                    )
                )
    return violations


def check_arch_03_root_loose_py(
    root: Path,
    *,
    allowlist: frozenset[str] = ROOT_AI_ENGINES_PY_ALLOWLIST,
) -> list[ArchViolation]:
    """[ARCH-03] Block new loose `.py` files added at `tooling/ai-engines/` root."""
    ai_dir = root / "tooling/ai-engines"
    if not ai_dir.is_dir():
        return []
    remediation = (
        "Move this module out of tooling/ai-engines/ root into quant_core/, quant_factory/, "
        "ops_cloud/, or experiments/ (do not introduce new loose root .py scripts)."
    )
    violations: list[ArchViolation] = []
    for path in sorted(ai_dir.glob("*.py")):
        if not path.is_file():
            continue
        if path.name not in allowlist:
            violations.append(
                ArchViolation(
                    rule="ARCH-03",
                    file=_rel(path, root),
                    line=1,
                    issue=f"New loose root Python file '{path.name}' not in tooling/ai-engines/ baseline allowlist",
                    remediation=remediation,
                )
            )
    return violations


def check_arch_04_orphan_skills(
    root: Path,
    *,
    whitelist: frozenset[str] = ORPHAN_SKILL_WHITELIST,
) -> list[ArchViolation]:
    """[ARCH-04] Detect orphan repo skills (`in_deg == 0 and out_deg == 0`) outside standalone whitelist."""
    skills_dir = root / ".agents/skills"
    if not skills_dir.is_dir():
        return []
    skill_names = sorted(
        entry.name for entry in skills_dir.iterdir() if entry.is_dir() and (entry / "SKILL.md").is_file()
    )
    if len(skill_names) <= 1:
        return []

    out_edges: dict[str, set[str]] = {name: set() for name in skill_names}
    in_deg: dict[str, int] = {name: 0 for name in skill_names}
    patterns = {name: re.compile(r"(?<![a-z0-9-])" + re.escape(name) + r"(?![a-z0-9-])") for name in skill_names}

    for src_skill in skill_names:
        text = (skills_dir / src_skill / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        for dst_skill in skill_names:
            if dst_skill == src_skill:
                continue
            if patterns[dst_skill].search(text):
                out_edges[src_skill].add(dst_skill)
                in_deg[dst_skill] += 1

    remediation = (
        "Wire this skill into the Naqex skill handoff graph by referencing upstream/downstream "
        "skills in SKILL.md (or justify standalone status in ORPHAN_SKILL_WHITELIST)."
    )
    violations: list[ArchViolation] = []
    for skill in skill_names:
        if skill in whitelist:
            continue
        if in_deg[skill] == 0 and len(out_edges[skill]) == 0:
            skill_md = skills_dir / skill / "SKILL.md"
            violations.append(
                ArchViolation(
                    rule="ARCH-04",
                    file=_rel(skill_md, root),
                    line=1,
                    issue=f"Orphan repo skill '{skill}' has in_deg=0 and out_deg=0",
                    remediation=remediation,
                )
            )
    return violations


def check_arch_05_byte_bloat(root: Path, *, strict: bool = False) -> list[ArchViolation]:
    """[ARCH-05] Enforce byte budgets on `planning/research/README.md` (<=15KB) & `CURRENT-CONTEXT.md` (<=12KB)."""
    violations: list[ArchViolation] = []
    readme = root / "planning/research/README.md"
    if readme.is_file():
        size = readme.stat().st_size
        if size > README_MAX_BYTES:
            violations.append(
                ArchViolation(
                    rule="ARCH-05",
                    file=_rel(readme, root),
                    line=1,
                    issue=f"planning/research/README.md size {size:,} B exceeds {README_MAX_BYTES:,} B budget",
                    remediation=(
                        "Archive superseded research rows into planning/research/ARCHIVE-INDEX-*.md "
                        "and compact planning/research/README.md to <= 15,000 B."
                    ),
                    severity="error" if strict else "warning",
                )
            )

    ctx = root / "planning/CURRENT-CONTEXT.md"
    if ctx.is_file():
        size = ctx.stat().st_size
        if size > CURRENT_CONTEXT_MAX_BYTES:
            violations.append(
                ArchViolation(
                    rule="ARCH-05",
                    file=_rel(ctx, root),
                    line=1,
                    issue=f"planning/CURRENT-CONTEXT.md size {size:,} B exceeds {CURRENT_CONTEXT_MAX_BYTES:,} B budget",
                    remediation=(
                        "Compact stale sections of planning/CURRENT-CONTEXT.md into planning/archive/ "
                        "so CURRENT-CONTEXT.md stays <= 12,000 B."
                    ),
                    severity="error",
                )
            )
    return violations


def _find_json_key_line(lines: list[str], key: str) -> int:
    needle = f'"{key}"'
    for idx, line in enumerate(lines, start=1):
        if needle in line:
            return idx
    return 1


def check_arch_06_ssot_unit_suffixes(root: Path) -> list[ArchViolation]:
    """[ARCH-06] Enforce `_frac` in [0, 1] and `_pct` in [0, 100] on `tooling/ai-engines/configs/ssot/*.json`."""
    ssot_dir = root / "tooling/ai-engines/configs/ssot"
    if not ssot_dir.is_dir():
        return []

    remediation = (
        "Normalize SSOT JSON unit suffixes: '_frac' values must be finite numbers in [0.0, 1.0] "
        "and '_pct' values must be finite numbers in [0.0, 100.0] (never bool/NaN/Inf)."
    )
    violations: list[ArchViolation] = []

    def _validate_scalar(
        val: Any,
        suffix: str,
        key_path: str,
        key_name: str,
        rel_file: str,
        lines: list[str],
    ) -> None:
        if val is None:
            return
        line_no = _find_json_key_line(lines, key_name)
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            violations.append(
                ArchViolation(
                    rule="ARCH-06",
                    file=rel_file,
                    line=line_no,
                    issue=f"Key '{key_path}' has non-numeric/bool value {val!r}",
                    remediation=remediation,
                )
            )
        elif not math.isfinite(float(val)):
            violations.append(
                ArchViolation(
                    rule="ARCH-06",
                    file=rel_file,
                    line=line_no,
                    issue=f"Key '{key_path}' has non-finite value {val!r}",
                    remediation=remediation,
                )
            )
        elif suffix == "_frac" and not (0.0 <= float(val) <= 1.0):
            violations.append(
                ArchViolation(
                    rule="ARCH-06",
                    file=rel_file,
                    line=line_no,
                    issue=f"Fraction key '{key_path}'={val!r} out of [0, 1] range (mixed percent?)",
                    remediation=remediation,
                )
            )
        elif suffix == "_pct" and not (0.0 <= float(val) <= 100.0):
            violations.append(
                ArchViolation(
                    rule="ARCH-06",
                    file=rel_file,
                    line=line_no,
                    issue=f"Percent key '{key_path}'={val!r} out of [0, 100] range",
                    remediation=remediation,
                )
            )

    def _walk(
        node: Any,
        path_parts: list[str],
        rel_file: str,
        lines: list[str],
        inherited_suffix: str | None = None,
    ) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key_path = ".".join([*path_parts, str(k)])
                if k.endswith("_frac"):
                    eff_suffix: str | None = "_frac"
                elif k.endswith("_pct"):
                    eff_suffix = "_pct"
                else:
                    eff_suffix = inherited_suffix

                if isinstance(v, (dict, list)):
                    _walk(v, [*path_parts, str(k)], rel_file, lines, inherited_suffix=eff_suffix)
                elif eff_suffix is not None:
                    _validate_scalar(v, eff_suffix, key_path, str(k), rel_file, lines)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                item_path = ".".join([*path_parts, f"[{idx}]"])
                if isinstance(item, (dict, list)):
                    _walk(item, [*path_parts, f"[{idx}]"], rel_file, lines, inherited_suffix=inherited_suffix)
                elif inherited_suffix is not None:
                    parent_key = path_parts[-1] if path_parts else ""
                    _validate_scalar(item, inherited_suffix, item_path, parent_key, rel_file, lines)

    for json_path in sorted(ssot_dir.rglob("*.json")):
        if not json_path.is_file():
            continue
        rel_file = _rel(json_path, root)
        raw_text = json_path.read_text(encoding="utf-8", errors="replace")
        lines = raw_text.splitlines()
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            violations.append(
                ArchViolation(
                    rule="ARCH-06",
                    file=rel_file,
                    line=exc.lineno or 1,
                    issue=f"Invalid JSON syntax in SSOT config: {exc.msg}",
                    remediation="Fix JSON syntax so Pydantic v2 SSOT schema validation can load this file.",
                )
            )
            continue
        _walk(data, [], rel_file, lines)
    return violations


def check_arch_07_copyleft_imports(root: Path) -> list[ArchViolation]:
    """[ARCH-07] Ban copyleft/Commons-Clause imports (`backtesting`, `backtrader`, `vectorbt`) in core packages."""
    ai_dir = root / "tooling/ai-engines"
    remediation = (
        "Remove banned copyleft/Commons-Clause dependency ('backtesting'/'backtrader'/'vectorbt') "
        "and use Naqex MIT/BSD core (quant_core, NumPy, Numba, NautilusTrader)."
    )
    violations: list[ArchViolation] = []
    for pkg in ("quant_core", "quant_factory", "ops_cloud"):
        pkg_dir = ai_dir / pkg
        if not pkg_dir.is_dir():
            continue
        for path in sorted(pkg_dir.rglob("*.py")):
            _, tree = _parse_python(path, required_substrings=tuple(BANNED_COPYLEFT_ROOTS))
            if tree is None:
                continue
            rel_file = _rel(path, root)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in BANNED_COPYLEFT_ROOTS:
                            violations.append(
                                ArchViolation(
                                    rule="ARCH-07",
                                    file=rel_file,
                                    line=node.lineno,
                                    issue=f"Banned copyleft/Commons-Clause import '{alias.name}' in {pkg}",
                                    remediation=remediation,
                                )
                            )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    if top in BANNED_COPYLEFT_ROOTS:
                        violations.append(
                            ArchViolation(
                                rule="ARCH-07",
                                file=rel_file,
                                line=node.lineno,
                                issue=f"Banned copyleft/Commons-Clause import 'from {node.module}' in {pkg}",
                                remediation=remediation,
                            )
                        )
                elif isinstance(node, ast.Call):
                    fn_name = ""
                    if isinstance(node.func, ast.Name):
                        fn_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        fn_name = node.func.attr
                    if fn_name in ("import_module", "__import__"):
                        mod_arg: ast.expr | None = node.args[0] if node.args else None
                        if mod_arg is None:
                            for kw in node.keywords:
                                if kw.arg == "name":
                                    mod_arg = kw.value
                                    break
                        if isinstance(mod_arg, ast.Constant) and isinstance(mod_arg.value, str):
                            top = mod_arg.value.split(".")[0]
                            if top in BANNED_COPYLEFT_ROOTS:
                                violations.append(
                                    ArchViolation(
                                        rule="ARCH-07",
                                        file=rel_file,
                                        line=node.lineno,
                                        issue=f"Banned dynamic copyleft import '{mod_arg.value}' in {pkg}",
                                        remediation=remediation,
                                    )
                                )
    return violations


def run_architecture_audit(root: Path = ROOT, *, strict: bool = False) -> dict[str, Any]:
    """Run all 7 Harness Engineering architecture rules [ARCH-01..07]."""
    resolved = root.resolve()
    all_findings: list[ArchViolation] = []
    all_findings.extend(check_arch_01_hot_path_scipy(resolved))
    all_findings.extend(check_arch_02_holdout_asserts(resolved))
    all_findings.extend(check_arch_03_root_loose_py(resolved))
    all_findings.extend(check_arch_04_orphan_skills(resolved))
    all_findings.extend(check_arch_05_byte_bloat(resolved, strict=strict))
    all_findings.extend(check_arch_06_ssot_unit_suffixes(resolved))
    all_findings.extend(check_arch_07_copyleft_imports(resolved))

    errors = [v for v in all_findings if v.severity == "error"]
    warnings = [v for v in all_findings if v.severity == "warning"]
    by_rule: dict[str, int] = {f"ARCH-0{i}": 0 for i in range(1, 8)}
    for v in all_findings:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1

    return {
        "root": str(resolved).replace("\\", "/"),
        "strict": strict,
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "by_rule": by_rule,
        "errors": [asdict(v) for v in errors],
        "warnings": [asdict(v) for v in warnings],
        "formatted": [v.format_line() for v in all_findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Naqex Harness Engineering Architecture Gate ([ARCH-01..07]).")
    parser.add_argument("--root", type=Path, default=ROOT, help="Workspace root directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote advisory warnings (e.g. planning/research/README.md > 15KB) to hard errors",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit structured JSON report")
    args = parser.parse_args(argv)

    report = run_architecture_audit(args.root, strict=args.strict)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for line in report["formatted"]:
            print(line)
        status = "PASS" if report["passed"] else "FAIL"
        print(
            f"Architecture audit ({'STRICT' if args.strict else 'DEFAULT'}): {status} — "
            f"{report['error_count']} errors, {report['warning_count']} advisory warnings."
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
