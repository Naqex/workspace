"""Unit tests for Harness Engineering architecture rules [ARCH-01..07], worktree_ctl, and naqex_cli."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLING_DIR = Path(__file__).resolve().parents[1]
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

import check_architecture as arch  # noqa: E402
import naqex_cli  # noqa: E402
import worktree_ctl  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _make_clean_repo(root: Path) -> None:
    """Create a minimal synthetic workspace that satisfies all 7 rules [ARCH-01..07]."""
    _write(root / "tooling/ai-engines/quant_factory/__init__.py", "__all__ = []\n")
    _write(root / "tooling/ai-engines/quant_factory/data_store.py", "from pathlib import Path\n")
    _write(
        root / "tooling/ai-engines/quant_factory/eval_pipeline.py",
        "from statistics import NormalDist\n_N = NormalDist(0.0, 1.0)\n",
    )
    _write(root / "tooling/ai-engines/quant_factory/prop_engine.py", "import numpy as np\n")
    _write(
        root / "tooling/ai-engines/quant_core/metrics.py",
        (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    import scipy\n"
            "def lazy_helper():\n"
            "    import scipy.optimize  # lazy function-local import is allowed\n"
            "    return scipy.optimize\n"
        ),
    )
    _write(
        root / "tooling/ai-engines/hot_m1_cache.py",
        (
            "class HoldoutLockError(ValueError):\n"
            "    pass\n"
            "def guard(ts, STOP):\n"
            "    if ts >= STOP:\n"
            "        raise HoldoutLockError('sealed')\n"
        ),
    )
    _write(root / "tooling/ai-engines/ops_cloud/node_ctl.py", "import json\n")
    _write(
        root / ".agents/skills/strategy-research/SKILL.md",
        "---\nname: strategy-research\n---\nHands off to strategy-qualification.\n",
    )
    _write(
        root / ".agents/skills/strategy-qualification/SKILL.md",
        "---\nname: strategy-qualification\n---\nReceives evidence from strategy-research.\n",
    )
    _write(
        root / ".agents/skills/chart-guided-tutoring/SKILL.md",
        "---\nname: chart-guided-tutoring\n---\nDomain-standalone education skill.\n",
    )
    _write(
        root / ".agents/skills/reverse-engineering/SKILL.md",
        "---\nname: reverse-engineering\n---\nDomain-standalone security skill.\n",
    )
    _write(root / "planning/research/README.md", "# Research Index\nCompact clean index.\n")
    _write(root / "planning/CURRENT-CONTEXT.md", "# Current Context\nCompact state.\n")
    _write(
        root / "tooling/ai-engines/configs/ssot/firms_catalog.json",
        json.dumps(
            {
                "ftmo_std_10k": {
                    "p1_target_frac": 0.10,
                    "daily_dd_frac": 0.05,
                    "risk_per_trade_pct": 0.16,
                    "profit_split_pct": 80.0,
                    "factor_caps_frac": {
                        "per_symbol_frac": 0.0175,
                        "total_open_account_frac": 0.03,
                    },
                }
            },
            indent=2,
        ),
    )


class CheckArchitectureRuleTests(unittest.TestCase):
    def test_clean_repo_passes_all_7_rules_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            report = arch.run_architecture_audit(root, strict=True)
            self.assertTrue(report["passed"], f"Expected clean repo to pass: {report['formatted']}")
            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["warning_count"], 0)
            self.assertEqual(sum(report["by_rule"].values()), 0)

    def test_arch_01_catches_top_level_scipy_and_allows_lazy_import(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            # Clean fixture already contains function-local lazy import and TYPE_CHECKING import -> must pass
            self.assertEqual(arch.check_arch_01_hot_path_scipy(root), [])

            # Inject top-level scipy import into hot-path module (including class body executed at import time)
            _write(
                root / "tooling/ai-engines/quant_factory/eval_pipeline.py",
                "from scipy.stats import norm\nx = norm.cdf(0.0)\n",
            )
            _write(
                root / "tooling/ai-engines/quant_core/bad_mod.py",
                "import scipy\n",
            )
            _write(
                root / "tooling/ai-engines/quant_core/bad_cls.py",
                "class SneakyImport:\n    import scipy.stats\n",
            )
            hits = arch.check_arch_01_hot_path_scipy(root)
            self.assertEqual(len(hits), 3)
            for h in hits:
                line = h.format_line()
                self.assertTrue(line.startswith("[ARCH-01] "))
                self.assertIn("| REMEDIATION:", line)

    def test_arch_02_catches_holdout_assert_and_allows_explicit_raise(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            self.assertEqual(arch.check_arch_02_holdout_asserts(root), [])

            _write(
                root / "tooling/ai-engines/pass27_sample.py",
                "def run(stamps, STOP):\n    assert int(stamps[-1]) < STOP, 'HOLDOUT'\n",
            )
            _write(
                root / "tooling/ai-engines/quant_factory/sample_lab.py",
                "def check(days):\n    assert max(days) < '2025-01-01'\n",
            )
            hits = arch.check_arch_02_holdout_asserts(root)
            self.assertEqual(len(hits), 2)
            for h in hits:
                line = h.format_line()
                self.assertTrue(line.startswith("[ARCH-02] "))
                self.assertIn("HoldoutLockError", line)

    def test_arch_03_catches_new_loose_root_py_and_allows_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            # hot_m1_cache.py is in baseline allowlist -> clean
            self.assertEqual(arch.check_arch_03_root_loose_py(root), [])

            # Migrated legacy/test filenames must no longer be allowlisted
            for retired in ("test_forex_ml_study.py", "bot_live_evidence.py", "hermes_setup.py"):
                self.assertNotIn(retired, arch.ROOT_AI_ENGINES_PY_ALLOWLIST)

            # Live workspace allowlist must stay tight (zero stale entries for removed/migrated files)
            actual_root_py = {p.name for p in (arch.ROOT / "tooling/ai-engines").glob("*.py") if p.is_file()}
            stale_entries = arch.ROOT_AI_ENGINES_PY_ALLOWLIST - actual_root_py
            self.assertEqual(
                stale_entries,
                frozenset(),
                f"Stale ARCH-03 allowlist entries: {sorted(stale_entries)[:10]}",
            )
            self.assertEqual(len(arch.ROOT_AI_ENGINES_PY_ALLOWLIST), 233)

            _write(root / "tooling/ai-engines/brand_new_unregistered_script.py", "x = 1\n")
            _write(root / "tooling/ai-engines/bot_live_evidence.py", "x = 2\n")
            hits = arch.check_arch_03_root_loose_py(root)
            self.assertEqual(len(hits), 2)
            for hit in hits:
                line = hit.format_line()
                self.assertTrue(line.startswith("[ARCH-03] tooling/ai-engines/"))
                self.assertIn("| REMEDIATION:", line)

    def test_arch_04_catches_orphan_skill_and_respects_standalone_whitelist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            # chart-guided-tutoring & reverse-engineering are whitelisted -> 0 hits
            self.assertEqual(arch.check_arch_04_orphan_skills(root), [])

            _write(
                root / ".agents/skills/lone-orphan-skill/SKILL.md",
                "---\nname: lone-orphan-skill\n---\nNo links anywhere.\n",
            )
            hits = arch.check_arch_04_orphan_skills(root)
            self.assertEqual(len(hits), 1)
            line = hits[0].format_line()
            self.assertTrue(line.startswith("[ARCH-04] .agents/skills/lone-orphan-skill/SKILL.md:1 |"))
            self.assertIn("| REMEDIATION:", line)

    def test_arch_05_enforces_readme_advisory_vs_strict_and_context_hard_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            self.assertEqual(arch.check_arch_05_byte_bloat(root, strict=True), [])

            # Oversized README -> warning in default mode, error in strict mode
            _write(root / "planning/research/README.md", "A" * 16_000)
            default_rep = arch.run_architecture_audit(root, strict=False)
            self.assertTrue(default_rep["passed"])
            self.assertEqual(default_rep["warning_count"], 1)
            self.assertEqual(default_rep["error_count"], 0)
            self.assertTrue(default_rep["formatted"][0].startswith("[ARCH-05] "))

            strict_rep = arch.run_architecture_audit(root, strict=True)
            self.assertFalse(strict_rep["passed"])
            self.assertEqual(strict_rep["error_count"], 1)

            # Oversized CURRENT-CONTEXT -> hard error even in default mode
            _write(root / "planning/CURRENT-CONTEXT.md", "B" * 13_000)
            ctx_rep = arch.run_architecture_audit(root, strict=False)
            self.assertFalse(ctx_rep["passed"])
            self.assertEqual(ctx_rep["error_count"], 1)
            self.assertEqual(ctx_rep["warning_count"], 1)

    def test_arch_06_catches_mixed_frac_and_pct_suffix_violations(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            self.assertEqual(arch.check_arch_06_ssot_unit_suffixes(root), [])

            _write(
                root / "tooling/ai-engines/configs/ssot/broken.json",
                json.dumps(
                    {
                        "tier": {
                            "max_dd_frac": 10.0,  # > 1.0 mixed percent!
                            "profit_split_pct": 120.0,  # > 100.0
                            "flag_frac": True,  # bool disguised as int
                            "factor_caps_frac": {"bad_usd_cap": 2.5},  # > 1.0 inside *_frac container
                        }
                    },
                    indent=2,
                ),
            )
            hits = arch.check_arch_06_ssot_unit_suffixes(root)
            self.assertEqual(len(hits), 4)
            for h in hits:
                line = h.format_line()
                self.assertTrue(line.startswith("[ARCH-06] "))
                self.assertIn("| REMEDIATION:", line)

    def test_arch_07_catches_banned_copyleft_imports_across_core_packages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_clean_repo(root)
            self.assertEqual(arch.check_arch_07_copyleft_imports(root), [])

            _write(root / "tooling/ai-engines/quant_core/bad_bt.py", "import backtrader as bt\n")
            _write(root / "tooling/ai-engines/quant_factory/bad_vbt.py", "from vectorbt.portfolio import Portfolio\n")
            _write(
                root / "tooling/ai-engines/ops_cloud/bad_dyn.py",
                (
                    "import importlib\n"
                    "mod = importlib.import_module('backtesting')\n"
                    "kw_mod = importlib.import_module(name='vectorbt')\n"
                    "kw_bi = __import__(name='backtrader')\n"
                ),
            )
            hits = arch.check_arch_07_copyleft_imports(root)
            self.assertEqual(len(hits), 5)
            for h in hits:
                line = h.format_line()
                self.assertTrue(line.startswith("[ARCH-07] "))
                self.assertIn("| REMEDIATION:", line)


class WorktreeAndCliSafetyTests(unittest.TestCase):
    def test_worktree_ctl_rejects_traversal_and_protects_external_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError):
                worktree_ctl.validate_worktree_name("../escape")
            with self.assertRaises(ValueError):
                worktree_ctl.validate_worktree_name("nested/name")
            self.assertEqual(worktree_ctl.validate_worktree_name("lane-l2_test"), "lane-l2_test")

            self.assertTrue(worktree_ctl.is_managed_worktree(root / ".worktrees/sub-a", root))
            self.assertFalse(worktree_ctl.is_managed_worktree(root / ".worktrees", root))
            self.assertFalse(worktree_ctl.is_managed_worktree(root.parent / "external-wt", root))

            wt_a = (root / ".worktrees/lane-a").as_posix()
            porcelain = (
                f"worktree {root.as_posix()}\nHEAD 1111111111111111111111111111111111111111\nbranch refs/heads/main\n\n"
                f"worktree {wt_a}\nHEAD 2222222222222222222222222222222222222222\ndetached\n\n"
                "worktree E:/ghws\nHEAD 3333333333333333333333333333333333333333\ndetached\n"
            )
            recs = worktree_ctl.parse_worktree_porcelain(porcelain, root)
            scopes = {r.scope for r in recs}
            self.assertEqual(scopes, {"primary", "managed", "external"})

            # LF guard fails closed when .gitattributes is missing
            self.assertTrue(worktree_ctl.verify_gitattributes_lf_guard(root))
            _write(root / ".gitattributes", "\n".join(worktree_ctl.REQUIRED_LF_RULES) + "\n")
            self.assertEqual(worktree_ctl.verify_gitattributes_lf_guard(root), [])

    def test_naqex_cli_builds_expected_subcommands(self) -> None:
        parser = naqex_cli.make_parser()
        for argv, needle in (
            (["doctor", "--mode", "fast"], "system_doctor.py"),
            (["test-fast"], "pytest"),
            (["test-full"], "not local_cache"),
            (["audit-arch", "--strict"], "check_architecture.py"),
            (["brain-index"], "brain_cli.py"),
            (["worktree", "list"], "worktree_ctl.py"),
            (["opsec"], "test_layer1_opsec_guard.py"),
            (["ruff", "check"], "ruff"),
        ):
            args, extra = parser.parse_known_args(argv)
            cmd = naqex_cli.build_command(args, extra)
            self.assertTrue(any(needle in part for part in cmd), f"Missing {needle!r} in {cmd}")

        # Regression test: `test-fast --workers 2` must NOT split `-o cache_dir=...`
        args_w2, extra_w2 = parser.parse_known_args(["test-fast", "--workers", "2"])
        cmd_w2 = naqex_cli.build_command(args_w2, extra_w2)
        o_idx = cmd_w2.index("-o")
        self.assertTrue(cmd_w2[o_idx + 1].startswith("cache_dir="), f"-o detached from cache_dir: {cmd_w2}")
        self.assertIn("-n", cmd_w2[:o_idx])
        self.assertIn("2", cmd_w2[:o_idx])

    def test_worktree_ctl_prune_skips_locked_and_resolves_relative_gitdir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Fake minimal git-common-dir layout via monkeypatching _run_git and list_worktrees
            admin = root / ".git/worktrees"
            locked_entry = admin / "locked-lane"
            locked_entry.mkdir(parents=True)
            (locked_entry / "gitdir").write_text("../../../.worktrees/locked-lane/.git\n", encoding="utf-8")
            (locked_entry / "locked").write_text("in use\n", encoding="utf-8")

            stale_entry = admin / "stale-lane"
            stale_entry.mkdir(parents=True)
            (stale_entry / "gitdir").write_text("../../../.worktrees/stale-lane/.git\n", encoding="utf-8")

            ext_entry = admin / "ext-lane"
            ext_entry.mkdir(parents=True)
            (ext_entry / "gitdir").write_text("E:/ghws/.git\n", encoding="utf-8")

            fake_proc = subprocess.CompletedProcess(args=["git"], returncode=0, stdout=str(root / ".git"), stderr="")
            with (
                mock.patch.object(worktree_ctl, "_run_git", return_value=fake_proc),
                mock.patch.object(worktree_ctl, "list_worktrees", return_value=[]),
            ):
                res = worktree_ctl.prune_managed_worktrees(root=root, dry_run=False)

            self.assertEqual(res["locked_managed_skipped"], ["locked-lane"])
            self.assertEqual(res["pruned_managed_entries"], ["stale-lane"])
            protected = res["external_worktrees_protected"]
            self.assertIsInstance(protected, list)
            assert isinstance(protected, list)
            self.assertIn("E:/ghws", protected)
            self.assertTrue(locked_entry.exists(), "Locked managed worktree admin entry must NOT be deleted")
            self.assertFalse(stale_entry.exists(), "Unlocked stale managed worktree admin entry should be pruned")
            self.assertTrue(ext_entry.exists(), "External worktree admin entry must NEVER be deleted")


if __name__ == "__main__":
    unittest.main()
