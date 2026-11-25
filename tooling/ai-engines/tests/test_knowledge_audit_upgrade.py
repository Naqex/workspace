"""Unit & workspace-integrity tests for upgraded `brain_cli.audit_data()` (broken Markdown links & near-duplicate topic headings)."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli


def test_detects_broken_relative_links_and_ignores_valid_or_code_fences(tmp_path: Path, monkeypatch):
    (tmp_path / "knowledge/topics").mkdir(parents=True)
    (tmp_path / "knowledge/inbox").mkdir(parents=True)
    (tmp_path / "planning/research").mkdir(parents=True)

    (tmp_path / "planning/research/EXISTING.md").write_text("# Valid Target\n", encoding="utf-8")
    (tmp_path / "knowledge/topics/target.md").write_text("# Target Topic\n", encoding="utf-8")

    # Inbox broken links must be ignored (raw untrusted web captures)
    (tmp_path / "knowledge/inbox/raw_capture.md").write_text(
        "[Scraped Relative](./does-not-exist-in-inbox.md)\n",
        encoding="utf-8",
    )

    (tmp_path / "knowledge/topics/sample.md").write_text(
        "\n".join([
            "---",
            "doc_type: evergreen",
            "---",
            "# Sample Guide",
            "Valid local link: [Target](target.md#section-1)",
            "Valid parent link: [Existing](../../planning/research/EXISTING.md)",
            "External link: [Docs](https://example.com/missing-page)",
            "Pure anchor: [Jump](#sample-guide)",
            "Inline code link ignored: `[Fake](missing-inline.md)`",
            "```markdown",
            "[Fenced Fake](missing-in-fence.md)",
            "```",
            "Actual broken link 1: [Ghost Local](ghost-topic.md#anchor)",
            "Actual broken link 2: [Ghost Research](../../planning/research/NO_SUCH_REPORT.md)",
        ]) + "\n",
        encoding="utf-8",
    )

    broken = brain_cli.find_broken_knowledge_links(tmp_path)
    assert len(broken) == 2
    targets = {item["target"] for item in broken}
    assert targets == {"ghost-topic.md#anchor", "../../planning/research/NO_SUCH_REPORT.md"}
    assert all(item["file"] == "knowledge/topics/sample.md" for item in broken)

    # Also verify full audit_data() wiring via monkeypatched ROOT
    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", tmp_path / ".runtime/knowledge")
    monkeypatch.setattr(brain_cli, "DB_PATH", tmp_path / ".runtime/knowledge/brain.sqlite3")
    monkeypatch.setattr(brain_cli, "VEC_PATH", tmp_path / ".runtime/knowledge/brain_vec.npz")
    audit = brain_cli.audit_data()
    assert audit["broken_knowledge_links_count"] == 2
    assert len(audit["broken_knowledge_links"]) == 2


def test_detects_near_duplicate_topic_headings_diacritic_aware(tmp_path: Path, monkeypatch):
    (tmp_path / "knowledge/topics").mkdir(parents=True)

    (tmp_path / "knowledge/topics/topic_a.md").write_text(
        "\n".join([
            "---",
            "doc_type: evergreen",
            "---",
            "# Quản trị Rủi ro Drawdown Prop Firm",
            "## 1. Chiến lược Khớp lệnh Rollover MT5",
            "## 2. Phân bổ Vốn Cá nhân Độc lập",
        ]) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge/topics/topic_b.md").write_text(
        "\n".join([
            "---",
            "doc_type: evergreen",
            "---",
            "# Quan tri rui ro drawdown prop firm",
            "## 3. Chiến lược Khớp lệnh Rollover MT5 Thực tế",
            "## 4. Vi cấu trúc Funding Rate Crypto Perpetual",
        ]) + "\n",
        encoding="utf-8",
    )

    dups = brain_cli.find_near_duplicate_topic_headings(tmp_path)
    assert len(dups) == 2
    assert dups[0]["similarity"] == 1.0
    assert dups[0]["file_a"] == "knowledge/topics/topic_a.md"
    assert dups[0]["file_b"] == "knowledge/topics/topic_b.md"
    assert dups[1]["similarity"] >= 0.70

    # Ensure unrelated headings were NOT flagged
    flagged_headings = {d["heading_a"] for d in dups} | {d["heading_b"] for d in dups}
    assert "4. Vi cấu trúc Funding Rate Crypto Perpetual" not in flagged_headings

    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", tmp_path / ".runtime/knowledge")
    monkeypatch.setattr(brain_cli, "DB_PATH", tmp_path / ".runtime/knowledge/brain.sqlite3")
    monkeypatch.setattr(brain_cli, "VEC_PATH", tmp_path / ".runtime/knowledge/brain_vec.npz")
    audit = brain_cli.audit_data()
    assert audit["near_duplicate_topic_headings_count"] == 2


def test_real_workspace_knowledge_vault_zero_broken_links_and_clean_prose():
    """Verify the actual workspace knowledge vault passes link, duplicate-heading, frontmatter & no-bare-dollar checks."""
    broken = brain_cli.find_broken_knowledge_links(ROOT)
    assert broken == [], f"Broken relative Markdown links in knowledge/: {broken}"

    dups = brain_cli.find_near_duplicate_topic_headings(ROOT)
    assert dups == [], f"Near-duplicate topic headings in knowledge/topics/: {dups}"

    expected_topics = [
        "knowledge/topics/mt5-live-execution-gaps-and-tca.md",
        "knowledge/topics/capital-scaling-prop-to-own-book.md",
        "knowledge/topics/market-microstructure-and-economic-edge-handbook.md",
        "knowledge/topics/trading-psychology-and-profit-giveback-playbook.md",
        "knowledge/topics/ai-quant-engineering-frontier-2026.md",
        "knowledge/topics/alpha-hypothesis-ledger.md",
    ]
    bare_dollar_pair_re = re.compile(r"\$[^$\n]+\$")
    for rel in expected_topics:
        p = ROOT / rel
        assert p.is_file(), f"Missing expected evergreen topic: {rel}"
        txt = p.read_text(encoding="utf-8")
        assert txt.startswith("---\ndoc_type: evergreen\n"), f"Missing evergreen frontmatter in {rel}"
        # Ensure zero bare `$` pairs in prose (and zero bare `$` currency symbols in prose)
        for line_no, line in brain_cli._iter_non_code_lines(txt):
            cleaned = brain_cli.INLINE_CODE_RE.sub("", line)
            assert not bare_dollar_pair_re.search(cleaned), f"Bare dollar pair in {rel}:{line_no}: {line}"
            assert "$" not in cleaned, f"Bare '$' in prose {rel}:{line_no}: {line}"

    # Verify M7.1 read-only storage audit report exists and has zero bare `$` pairs in prose
    audit_doc = ROOT / "planning/research/STORAGE-HYGIENE-AUDIT-20261124.md"
    assert audit_doc.is_file()
    audit_txt = audit_doc.read_text(encoding="utf-8")
    assert "READ_ONLY_AUDIT_PENDING_OWNER_APPROVAL" in audit_txt
    assert "deletions_performed: 0" in audit_txt
    for line_no, line in brain_cli._iter_non_code_lines(audit_txt):
        cleaned = brain_cli.INLINE_CODE_RE.sub("", line)
        assert "$" not in cleaned, f"Bare '$' in prose STORAGE-HYGIENE-AUDIT:{line_no}: {line}"
