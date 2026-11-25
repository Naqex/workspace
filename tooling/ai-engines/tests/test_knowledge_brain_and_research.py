"""Deterministic unit & integration tests for Naqex Knowledge Brain & Multi-Source Research CLIs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli
import research_cli

RESEARCH_PY = ROOT / ".runtime/research-tools/Scripts/python.exe"


def test_brain_strip_accents_and_chunking():
    assert brain_cli._strip_accents("Giao dịch định lượng quỹ FTMO") == "giao dich dinh luong quy ftmo"
    sample = "# Heading 1\nIntro line\n## Section A\nBody A with Calmar 1.75\n### Sub B\nBody B\n"
    chunks = brain_cli.chunk_markdown(sample, "test.md")
    assert len(chunks) == 3
    assert chunks[0]["heading"] == "Heading 1"
    assert chunks[1]["heading"] == "Section A"
    assert chunks[2]["heading"] == "Sub B"


def test_brain_hash_embed_multilingual_similarity():
    v_en = brain_cli._hash_vector("volatility targeting portfolio drawdown")
    v_en2 = brain_cli._hash_vector("portfolio drawdown control via volatility targeting")
    v_other = brain_cli._hash_vector("banana chocolate pancake recipe")
    assert float(v_en @ v_en2) > float(v_en @ v_other)
    # Vietnamese diacritic-insensitive match
    v_vi1 = brain_cli._hash_vector("chiến lược thi quỹ FTMO")
    v_vi2 = brain_cli._hash_vector("chien luoc thi quy ftmo")
    assert float(v_vi1 @ v_vi2) > 0.99
    # CJK & Cyrillic token support
    v_cn = brain_cli._hash_vector("量化交易 波动率目标")
    v_ru = brain_cli._hash_vector("алготрейдинг портфель")
    assert float(v_cn @ v_cn) > 0.99
    assert float(v_ru @ v_ru) > 0.99


def test_brain_index_and_hybrid_query_isolated(tmp_path, monkeypatch):
    # Create mini vault in tmp_path
    (tmp_path / "knowledge/owner").mkdir(parents=True)
    (tmp_path / "knowledge/topics").mkdir(parents=True)
    (tmp_path / "knowledge/owner/PROFILE.md").write_text(
        "---\ndoc_type: evergreen\ndomain: owner\n---\n# Hồ sơ Owner\nMục tiêu là One-Person Quant Pod với Sharpe 2.0 và kỷ luật quản trị rủi ro.\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/owner/CURIOSITY-LOG.md").write_text(
        "# Curiosity Log\n\n## 2026-11-23\n- **[Quant]** *Test question?*\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/owner/DECISIONS-JOURNAL.md").write_text(
        "# Decisions\n\n| Ngày | Quyết định | Lý do | Revisit |\n|---|---|---|---|\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/topics/sample.md").write_text(
        "---\ndoc_type: evergreen\n---\n# AI Research Workflow\nDùng SQLite FTS5 không dấu và RRF hybrid search.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", tmp_path / ".runtime/knowledge")
    monkeypatch.setattr(brain_cli, "DB_PATH", tmp_path / ".runtime/knowledge/brain.sqlite3")
    monkeypatch.setattr(brain_cli, "VEC_PATH", tmp_path / ".runtime/knowledge/brain_vec.npz")

    res1 = brain_cli.index_brain()
    assert res1["files_total"] == 4
    assert res1["files_updated"] == 4
    assert res1["chunks_total"] >= 4

    # Incremental second run must skip unchanged files
    res2 = brain_cli.index_brain()
    assert res2["files_updated"] == 0
    assert res2["files_unchanged"] == 4

    # Vietnamese diacritic-insensitive query must hit PROFILE.md
    q = brain_cli.query_brain("muc tieu quant pod quan tri rui ro", domain="owner", top_k=3)
    assert q["hits"]
    assert q["hits"][0]["path"] == "knowledge/owner/PROFILE.md"
    assert q["hits"][0]["evergreen"] is True

    # Logging curiosity + decision appends and incrementally re-indexes
    lc = brain_cli.log_curiosity("AI", "Cách tối ưu memory?", "Markdown + SQLite FTS5", "test")
    assert lc["index"]["files_updated"] == 1
    ld = brain_cli.log_decision("Chọn SQLite FTS5", "Nhẹ, không daemon", "Khi > 5000 file")
    assert ld["index"]["files_updated"] == 1
    brief = brain_cli.owner_brief()
    assert "Cách tối ưu memory?" in brief
    assert "Chọn SQLite FTS5" in brief


def test_research_trust_tier_and_local_markdown_capture(tmp_path, monkeypatch):
    assert research_cli.classify_trust_tier("https://arxiv.org/abs/2304.04676") == "T1_PRIMARY_OFFICIAL"
    assert research_cli.classify_trust_tier("https://habr.com/ru/articles/762342/") == "T2_TECHNICAL_COMMUNITY"
    assert research_cli.classify_trust_tier("https://zhihu.com/question/12345") == "T2_TECHNICAL_COMMUNITY"
    assert research_cli.classify_trust_tier("https://www.reddit.com/r/algotrading/comments/xyz") == "T3_FORUM_EXPERIENCE"
    assert research_cli.classify_trust_tier("https://example.org/blog") == "T3_GENERAL_WEB"

    # End-to-end local HTML conversion + provenance frontmatter via research-tools runtime (if installed)
    sample_html = tmp_path / "sample_note.html"
    sample_html.write_text("<html><body><h1>Quant Note</h1><p>Volatility brake keeps drawdown low.</p></body></html>", encoding="utf-8")
    if RESEARCH_PY.exists():
        p = subprocess.run(
            [str(RESEARCH_PY), "-X", "utf8", str(ROOT / "tooling/knowledge/research_cli.py"), "fetch", str(sample_html), "--mode", "autonomous", "--question", "test", "--stdout"],
            capture_output=True, text=True, timeout=30,
        )
        assert p.returncode == 0, p.stderr
        assert "untrusted_external_data: true" in p.stdout
        assert "trust_tier: T1_LOCAL_ARTIFACT" in p.stdout
        assert "Volatility brake keeps drawdown low." in p.stdout


def test_workspace_brain_index_and_owner_profile_ready():
    assert (ROOT / "knowledge/owner/PROFILE.md").is_file()
    assert (ROOT / "knowledge/owner/CURIOSITY-LOG.md").is_file()
    assert (ROOT / "knowledge/owner/DECISIONS-JOURNAL.md").is_file()
    assert (ROOT / ".agents/skills/research-and-memory-ops/SKILL.md").is_file()
    if brain_cli.DB_PATH.exists() and brain_cli.VEC_PATH.exists():
        q = brain_cli.query_brain("thi quy ftmo holdout", top_k=3)
        assert q["hits"]
        assert q["elapsed_ms"] < 500.0


def test_brain_private_first_override_and_clean_public_fallback(tmp_path, monkeypatch):
    # Setup Layer-1 public stubs only (no private_vault yet -> clean CI/public clone behavior)
    pub_owner = tmp_path / "knowledge/owner"
    pub_owner.mkdir(parents=True)
    (tmp_path / "knowledge/topics").mkdir(parents=True)
    (pub_owner / "PROFILE.md").write_text(
        "---\ndoc_type: evergreen\ndomain: owner\n---\n# Public Stub Profile\nPublic fallback sentinel alpha.\n",
        encoding="utf-8",
    )
    (pub_owner / "CURIOSITY-LOG.md").write_text(
        "# Curiosity Stub\n\n## 2026-11-25\n- **[Public]** *Public curiosity stub?*\n",
        encoding="utf-8",
    )
    (pub_owner / "DECISIONS-JOURNAL.md").write_text(
        "# Decisions Stub\n\n| Ngày | Quyết định | Lý do | Revisit |\n|---|---|---|---|\n| `2026-11-25` | Public stub decision | Template | Never |\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/topics/guide.md").write_text(
        "---\ndoc_type: evergreen\n---\n# Shared Topic\nGeneral public guide.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", tmp_path / ".runtime/knowledge")
    monkeypatch.setattr(brain_cli, "DB_PATH", tmp_path / ".runtime/knowledge/brain.sqlite3")
    monkeypatch.setattr(brain_cli, "VEC_PATH", tmp_path / ".runtime/knowledge/brain_vec.npz")

    # 1. Clean public fallback
    assert brain_cli.resolve_owner_file("PROFILE.md") == pub_owner / "PROFILE.md"
    idx_pub = brain_cli.index_brain()
    assert idx_pub["files_total"] == 4
    q_pub = brain_cli.query_brain("Public fallback sentinel alpha", domain="owner", top_k=3)
    assert q_pub["hits"] and q_pub["hits"][0]["path"] == "knowledge/owner/PROFILE.md"
    brief_pub = brain_cli.owner_brief()
    assert "knowledge/owner" in brief_pub
    assert "Public fallback sentinel alpha" in brief_pub
    assert brain_cli.audit_data()["owner_source"] == "knowledge/owner"

    # 2. Mount Layer-2 private_vault/owner -> Private-First override must supersede public stubs
    priv_owner = tmp_path / "private_vault/owner"
    priv_owner.mkdir(parents=True)
    (priv_owner / "PROFILE.md").write_text(
        "---\ndoc_type: evergreen\ndomain: owner\n---\n# Private Real Profile\nPrivate vault sentinel omega drawdown rules.\n",
        encoding="utf-8",
    )
    (priv_owner / "CURIOSITY-LOG.md").write_text(
        "# Private Curiosity\n\n## 2026-11-25\n- **[Private]** *Private real question?*\n",
        encoding="utf-8",
    )
    (priv_owner / "DECISIONS-JOURNAL.md").write_text(
        "# Private Decisions\n\n| Ngày | Quyết định | Lý do | Revisit |\n|---|---|---|---|\n| `2026-11-25` | Private real decision | Vault | Q1 |\n",
        encoding="utf-8",
    )

    assert brain_cli.resolve_owner_file("PROFILE.md") == priv_owner / "PROFILE.md"
    idx_priv = brain_cli.index_brain()
    assert idx_priv["files_total"] == 4
    assert idx_priv["files_removed"] == 3  # Replaced 3 public stubs with 3 private owner files
    assert idx_priv["files_updated"] == 3

    q_priv = brain_cli.query_brain("Private vault sentinel omega", domain="owner", top_k=5)
    assert q_priv["hits"]
    assert q_priv["hits"][0]["path"] == "private_vault/owner/PROFILE.md"
    assert q_priv["hits"][0]["evergreen"] is True
    # Public stub must NOT duplicate in index once private override is active
    assert all(not h["path"].startswith("knowledge/owner/") for h in q_priv["hits"])

    brief_priv = brain_cli.owner_brief()
    assert "private_vault/owner" in brief_priv
    assert "Private vault sentinel omega" in brief_priv
    assert "Public fallback sentinel alpha" not in brief_priv
    assert brain_cli.audit_data()["owner_source"] == "private_vault/owner"

    # Writes must target private_vault/owner and leave Layer-1 public stubs untouched
    pub_cur_before = (pub_owner / "CURIOSITY-LOG.md").read_text(encoding="utf-8")
    pub_dec_before = (pub_owner / "DECISIONS-JOURNAL.md").read_text(encoding="utf-8")
    lc = brain_cli.log_curiosity("Vault", "Does private write stay private?", "Yes, Layer-2 only")
    ld = brain_cli.log_decision("Use Layer-2 Private Vault", "Zero personal leak to Layer-1", "Annual")
    assert lc["logged_to"] == "private_vault/owner/CURIOSITY-LOG.md"
    assert ld["logged_to"] == "private_vault/owner/DECISIONS-JOURNAL.md"
    assert (pub_owner / "CURIOSITY-LOG.md").read_text(encoding="utf-8") == pub_cur_before
    assert (pub_owner / "DECISIONS-JOURNAL.md").read_text(encoding="utf-8") == pub_dec_before
    assert "Does private write stay private?" in (priv_owner / "CURIOSITY-LOG.md").read_text(encoding="utf-8")
    assert "Use Layer-2 Private Vault" in (priv_owner / "DECISIONS-JOURNAL.md").read_text(encoding="utf-8")


def test_xerj_private_first_owner_resolution(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("xerj_pf", ROOT / "tooling/search/xerj.py")
    xerj = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(xerj)

    # Strict scope checks: private_vault/owner/*.md is research-only; ops/presets/holdout stay excluded
    assert xerj.allowed(Path("private_vault/owner/PROFILE.md"), research=True) is True
    assert xerj.allowed(Path("private_vault/owner/PROFILE.md"), research=False) is False
    assert xerj.allowed(Path("private_vault/owner/PROFILE.md"), product=True, research=True) is False
    assert xerj.allowed(Path("private_vault/ops/naqex-node1-topology.md"), research=True) is False
    assert xerj.allowed(Path("private_vault/owner/holdout-notes.md"), research=True) is False
    assert xerj.allowed(Path("private_vault/owner/sub/nested.md"), research=True) is False

    # Setup tiny git repo to verify source_files() public fallback -> private-first override
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    pub_owner = tmp_path / "knowledge/owner"
    pub_owner.mkdir(parents=True)
    (pub_owner / "PROFILE.md").write_text("# Public Stub\n", encoding="utf-8")
    (tmp_path / "knowledge/topics").mkdir(parents=True)
    (tmp_path / "knowledge/topics/topic.md").write_text("# Shared Topic\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "knowledge"], check=True, capture_output=True)

    monkeypatch.setattr(xerj, "ROOT", tmp_path)
    pub_rels = [rel.as_posix() for rel, _ in xerj.source_files(research=True)]
    assert "knowledge/owner/PROFILE.md" in pub_rels
    assert "knowledge/topics/topic.md" in pub_rels

    # Add private_vault/owner/PROFILE.md (untracked/gitignored in Layer-1)
    priv_owner = tmp_path / "private_vault/owner"
    priv_owner.mkdir(parents=True)
    (priv_owner / "PROFILE.md").write_text("# Private Profile\n", encoding="utf-8")
    (tmp_path / "private_vault/ops").mkdir(parents=True)
    (tmp_path / "private_vault/ops/naqex-node1-topology.md").write_text("# OPSEC\n", encoding="utf-8")

    priv_rels = [rel.as_posix() for rel, _ in xerj.source_files(research=True)]
    assert "private_vault/owner/PROFILE.md" in priv_rels
    assert "knowledge/owner/PROFILE.md" not in priv_rels  # Overridden by Private-First
    assert "knowledge/topics/topic.md" in priv_rels
    assert all(not r.startswith("private_vault/ops/") for r in priv_rels)
    # Default codegraph mode (research=False) must NOT include private_vault
    default_rels = [rel.as_posix() for rel, _ in xerj.source_files(research=False)]
    assert all(not r.startswith("private_vault/") for r in default_rels)
