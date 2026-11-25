"""Permanent fast Layer-1 OPSEC & Private-Vault Boundary Guard (unittest + pytest compatible).

Runs under both `pytest` and GitHub Actions `quant_test_suite.py --group complete --tier all`
(which discovers `unittest.TestCase` subclasses automatically).

Fails immediately if any tracked Layer-1 code, skill, playbook, or active research document
re-introduces:
  - Tracked files under `private_vault/`
  - Real private LAN host IP (`192.168.1.28`) or real Tailscale IP (`100.72.*`)
  - Concrete private LAN/CGNAT IPs in non-test Layer-1 code/docs (excluding RFC 6598 CIDR literal)
  - Concrete Heroku deadman app names (`naqex-deadman-*`)
  - Concrete Telegram alert bot handle
  - Hardcoded local Windows user profile paths (`C:\\Users\\<name>`)
  - Live API keys, GitHub/OpenAI/Google tokens, Postgres password DSNs, or real webhook/bot secrets
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
ORDER_SEND_COUNT = 0

_TEXT_EXTS = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".ps1", ".sh",
    ".mq5", ".mqh", ".set", ".ini", ".toml", ".cfg", ".js", ".ts", ".html", ".css",
}

# Build sensitive patterns dynamically so this guard never trips Gitleaks or self-matches.
_REAL_LAN_HOST_RE = re.compile(r"\b192\.168\.1\.28\b")
_ANY_LAN_IP_RE = re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b")
_REAL_TAILSCALE_RE = re.compile(r"\b100\.72\.\d{1,3}\.\d{1,3}\b")
_ANY_CGNAT_TS_RE = re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_HEROKU_APP_RE = re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")
_TG_BOT_HANDLE_RE = re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")
_WIN_USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_REAL_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GITHUB_TOKEN", re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{30,}|" + "github_pat_" + r"[A-Za-z0-9_]{30,})\b")),
    ("OPENAI_KEY", re.compile(r"\b" + "sk-" + r"(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\b" + "AIza" + r"[0-9A-Za-z_-]{35}\b")),
    ("TELEGRAM_BOT_TOKEN", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{33,}\b")),
    ("DISCORD_WEBHOOK", re.compile(r"https?://(?:discord\.com|discordapp\.com)/api/webhooks/\d{15,}/[A-Za-z0-9_-]{50,}")),
    ("POSTGRES_CRED_DSN", re.compile(r"postgres(?:ql)?://[^\s:/@<]+:[^\s/@<]{6,}@[^\s/<]+")),
)


def _git_tracked_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def _iter_layer1_guarded_files(tracked: list[str]) -> list[tuple[str, Path]]:
    """Return tracked Layer-1 code/docs/skills guarded by permanent OPSEC CI checks."""
    out: list[tuple[str, Path]] = []
    for rel in tracked:
        if rel.startswith(("projects/", "private_vault/", ".runtime/")):
            continue
        if rel == "tooling/ai-engines/tests/test_layer1_opsec_guard.py":
            continue
        in_scope = (
            rel.startswith(("tooling/ai-engines/", ".agents/", "knowledge/"))
            or rel == "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
            or (rel.startswith("planning/research/") and "/" not in rel[len("planning/research/"):] and rel.endswith(".md"))
        )
        if not in_scope:
            continue
        p = ROOT / rel
        if not p.is_file():
            continue
        if p.suffix.lower() not in _TEXT_EXTS and p.name not in ("Procfile", "Makefile"):
            continue
        if p.stat().st_size > 1_500_000:
            continue
        out.append((rel, p))
    return out


def _line_no(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


class Layer1OpsecGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tracked = _git_tracked_files()
        cls.guarded = _iter_layer1_guarded_files(cls.tracked)
        cls.contents: list[tuple[str, bool, str]] = [
            (rel, ("/tests/" in rel or Path(rel).name.startswith("test_")), path.read_text(encoding="utf-8", errors="replace"))
            for rel, path in cls.guarded
        ]

    def test_private_vault_is_never_tracked_and_gitignored(self) -> None:
        pv_tracked = [f for f in self.tracked if f.startswith("private_vault/") or "/private_vault/" in f]
        self.assertEqual(pv_tracked, [], f"Layer-2 private_vault files must NEVER be tracked in Layer-1: {pv_tracked}")
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/private_vault/", gi, ".gitignore must ignore /private_vault/")

    def test_zero_real_private_ips_heroku_apps_or_telegram_handle(self) -> None:
        violations: list[str] = []
        tg_needle = "naqex_" + "guard_bot"
        hk_needle = "naqex-" + "deadman-"
        for rel, is_test, text in self.contents:
            if "192.168." in text:
                m = _REAL_LAN_HOST_RE.search(text)
                if m:
                    violations.append(f"REAL_LAN_IP {rel}:{_line_no(text, m.start())}")
                elif not is_test:
                    m_lan = _ANY_LAN_IP_RE.search(text)
                    if m_lan:
                        violations.append(f"LAN_IP {rel}:{_line_no(text, m_lan.start())}")
            if "100." in text:
                m = _REAL_TAILSCALE_RE.search(text)
                if m:
                    violations.append(f"REAL_TAILSCALE_IP {rel}:{_line_no(text, m.start())}")
                elif not is_test:
                    for m_ts in _ANY_CGNAT_TS_RE.finditer(text):
                        if text[m_ts.start():m_ts.end() + 3] == "100.64.0.0/10":
                            continue
                        violations.append(f"CGNAT_TS_IP {rel}:{_line_no(text, m_ts.start())}")
                        break
            low = text.lower()
            if hk_needle in low:
                m = _HEROKU_APP_RE.search(text)
                if m:
                    violations.append(f"HEROKU_APP {rel}:{_line_no(text, m.start())}")
            if tg_needle in low:
                m = _TG_BOT_HANDLE_RE.search(text)
                if m:
                    violations.append(f"TG_BOT_HANDLE {rel}:{_line_no(text, m.start())}")
        self.assertEqual(violations, [], "OPSEC leaks detected:\n" + "\n".join(violations[:25]))

    def test_zero_hardcoded_local_windows_user_paths(self) -> None:
        violations: list[str] = []
        for rel, _is_test, text in self.contents:
            if "users" not in text.lower():
                continue
            m = _WIN_USER_PATH_RE.search(text)
            if m:
                violations.append(f"WIN_USER_PATH {rel}:{_line_no(text, m.start())}")
        self.assertEqual(violations, [], "Hardcoded user profile paths detected:\n" + "\n".join(violations[:25]))

    def test_zero_live_secrets_tokens_or_credential_dsns(self) -> None:
        violations: list[str] = []
        needles = (
            ("GITHUB_TOKEN", ("ghp_", "github_pat_"), _REAL_SECRET_PATTERNS[0][1]),
            ("OPENAI_KEY", ("sk-",), _REAL_SECRET_PATTERNS[1][1]),
            ("GOOGLE_API_KEY", ("AIza",), _REAL_SECRET_PATTERNS[2][1]),
            ("TELEGRAM_BOT_TOKEN", (":AA", ":AB", ":AC", ":AD", ":AE", ":AF"), _REAL_SECRET_PATTERNS[3][1]),
            ("DISCORD_WEBHOOK", ("/api/webhooks/",), _REAL_SECRET_PATTERNS[4][1]),
            ("POSTGRES_CRED_DSN", ("postgres://", "postgresql://"), _REAL_SECRET_PATTERNS[5][1]),
        )
        for rel, _is_test, text in self.contents:
            for tag, keys, rx in needles:
                if any(k in text for k in keys):
                    m = rx.search(text)
                    if m:
                        violations.append(f"{tag} {rel}:{_line_no(text, m.start())}")
        self.assertEqual(violations, [], "Secret/token leaks detected:\n" + "\n".join(violations[:25]))

    def test_guard_patterns_catch_synthetic_leaks_and_allow_placeholders(self) -> None:
        self.assertIsNotNone(_REAL_LAN_HOST_RE.search("rdp " + "192.168." + "1.28"))
        self.assertIsNotNone(_REAL_TAILSCALE_RE.search("ts " + "100.72." + "70.18"))
        self.assertIsNotNone(_HEROKU_APP_RE.search("app " + "naqex-" + "deadman-eu"))
        self.assertIsNotNone(_TG_BOT_HANDLE_RE.search("@" + "naqex_" + "guard_bot"))
        self.assertIsNotNone(_WIN_USER_PATH_RE.search("C:" + "\\Users\\" + "Alice\\Desktop"))
        for safe in ("<LAN_IP>", "<TAILSCALE_IP>", "<HEROKU_DEADMAN_APP>", "<TELEGRAM_GUARD_BOT>", "100.64.0.0/10", "C:\\Users\\<USER>\\file"):
            self.assertIsNone(_REAL_LAN_HOST_RE.search(safe))
            self.assertIsNone(_REAL_TAILSCALE_RE.search(safe))
            self.assertIsNone(_HEROKU_APP_RE.search(safe))
            self.assertIsNone(_TG_BOT_HANDLE_RE.search(safe))
            self.assertIsNone(_WIN_USER_PATH_RE.search(safe))

    def test_read_only_invariant(self) -> None:
        self.assertEqual(ORDER_SEND_COUNT, 0)
        self.assertGreater(len(self.guarded), 100, "Expected Layer-1 OPSEC guard to scan > 100 tracked files")


if __name__ == "__main__":
    unittest.main()
