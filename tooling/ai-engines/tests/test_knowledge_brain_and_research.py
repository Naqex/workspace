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
