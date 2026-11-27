"""Concurrency, incremental speed & schema auto-migration tests for `brain_cli.py` and `xerj.py` cleanup."""
from __future__ import annotations

import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli  # noqa: E402


def _setup_mini_vault(root: Path) -> None:
    (root / "knowledge/owner").mkdir(parents=True, exist_ok=True)
    (root / "knowledge/topics").mkdir(parents=True, exist_ok=True)
    (root / "knowledge/owner/PROFILE.md").write_text(
        "---\ndoc_type: evergreen\ndomain: owner\n---\n"
        "# Owner Profile\nTarget One-Person Quant Pod with strict drawdown control.\n",
        encoding="utf-8",
    )
    (root / "knowledge/owner/CURIOSITY-LOG.md").write_text(
        "# Curiosity Log\n\n## 2026-11-26\n- **[Quant]** *Initial question?*\n",
        encoding="utf-8",
    )
    (root / "knowledge/owner/DECISIONS-JOURNAL.md").write_text(
        "# Decisions\n\n| Ngày | Quyết định | Lý do | Revisit |\n|---|---|---|---|\n",
        encoding="utf-8",
    )
    for i in range(12):
        (root / f"knowledge/topics/topic_{i:02d}.md").write_text(
            f"---\ndoc_type: evergreen\n---\n# Topic {i}\n"
            f"Detailed quant research note number {i} on FTMO risk and Calmar.\n",
            encoding="utf-8",
        )


def test_brain_8_concurrent_threads_index_query_and_log_zero_corruption(tmp_path: Path, monkeypatch):
    _setup_mini_vault(tmp_path)
    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", tmp_path / ".runtime/knowledge")
    monkeypatch.setattr(brain_cli, "DB_PATH", tmp_path / ".runtime/knowledge/brain.sqlite3")
    monkeypatch.setattr(brain_cli, "VEC_PATH", tmp_path / ".runtime/knowledge/brain_vec.npz")

    # Initial seed index
    seed = brain_cli.index_brain()
    assert seed["files_total"] == 15
    assert brain_cli.VEC_PATH.is_file()

    def worker(tid: int) -> dict:
        if tid % 4 == 0:
            res_c = brain_cli.log_curiosity(f"T{tid}", f"Concurrent question {tid}?", f"Takeaway {tid}")
            q = brain_cli.query_brain(f"Concurrent question {tid}", top_k=5)
            return {"kind": "curiosity", "tid": tid, "indexed": res_c["index"]["chunks_total"], "hits": len(q["hits"])}
        if tid % 4 == 1:
            res_d = brain_cli.log_decision(f"Decision {tid}", f"Reason {tid}", "Q4")
            q = brain_cli.query_brain(f"Decision {tid}", top_k=5)
            return {"kind": "decision", "tid": tid, "indexed": res_d["index"]["chunks_total"], "hits": len(q["hits"])}
        if tid % 4 == 2:
            idx = brain_cli.index_brain()
            q = brain_cli.query_brain("FTMO risk Calmar", top_k=5)
            return {"kind": "index+query", "tid": tid, "chunks": idx["chunks_total"], "hits": len(q["hits"])}
        q1 = brain_cli.query_brain("One-Person Quant Pod drawdown", domain="owner", top_k=3)
        q2 = brain_cli.query_brain("quant research note", domain="knowledge", top_k=5)
        return {"kind": "query", "tid": tid, "h1": len(q1["hits"]), "h2": len(q2["hits"])}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(8)))

    assert len(results) == 8
    # Every logged curiosity & decision must survive without lost updates
    cur_txt = (tmp_path / "knowledge/owner/CURIOSITY-LOG.md").read_text(encoding="utf-8")
    dec_txt = (tmp_path / "knowledge/owner/DECISIONS-JOURNAL.md").read_text(encoding="utf-8")
    for tid in (0, 4):
        assert f"Concurrent question {tid}?" in cur_txt
    for tid in (1, 5):
        assert f"Decision {tid}" in dec_txt

    # SQLite DB must pass PRAGMA integrity_check and have valid vec_blob on every chunk
    conn = sqlite3.connect(str(brain_cli.DB_PATH))
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
        null_blobs = conn.execute("SELECT COUNT(*) FROM chunks WHERE vec_blob IS NULL").fetchone()[0]
        assert null_blobs == 0
        total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        assert total_chunks >= 15
    finally:
        conn.close()


def test_brain_auto_migrates_legacy_db_without_vec_blob(tmp_path: Path, monkeypatch):
    _setup_mini_vault(tmp_path)
    brain_dir = tmp_path / ".runtime/knowledge"
    brain_dir.mkdir(parents=True)
    db_path = brain_dir / "brain.sqlite3"
    vec_path = brain_dir / "brain_vec.npz"

    # Build a legacy v1 SQLite database WITHOUT vec_blob / mtime_ns / file_size
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE files (
            path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL, updated_ts REAL NOT NULL, chunk_count INTEGER NOT NULL
        );
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT NOT NULL, heading TEXT NOT NULL,
            line_start INTEGER NOT NULL, line_end INTEGER NOT NULL, domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL, updated_ts REAL NOT NULL, body TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            heading, body, content='chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, heading, body) VALUES (new.id, new.heading, new.body);
        END;
        CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, heading, body) VALUES('delete', old.id, old.heading, old.body);
        END;
    """)
    conn.execute(
        "INSERT INTO chunks(path, heading, line_start, line_end, domain, evergreen, updated_ts, body) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            "knowledge/owner/PROFILE.md", "Owner Profile", 1, 5,
            "owner", 1, 1700000000.0, "Legacy owner profile drawdown",
        ),
    )
    conn.commit()
    conn.close()
    np.savez(
        vec_path,
        ids=np.array([1], dtype=np.int64),
        vecs=np.vstack([brain_cli._hash_vector("Owner Profile\nLegacy owner profile drawdown")]),
    )

    monkeypatch.setattr(brain_cli, "ROOT", tmp_path)
    monkeypatch.setattr(brain_cli, "BRAIN_DIR", brain_dir)
    monkeypatch.setattr(brain_cli, "DB_PATH", db_path)
    monkeypatch.setattr(brain_cli, "VEC_PATH", vec_path)

    # Querying seamlessly triggers migration + backfill and shrinks legacy VEC_PATH to compat marker
    q = brain_cli.query_brain("One-Person Quant Pod drawdown", domain="owner", top_k=3)
    assert q["hits"]
    assert q["hits"][0]["path"] == "knowledge/owner/PROFILE.md"
    assert vec_path.is_file()
    assert vec_path.stat().st_size <= 4096

    conn2 = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in conn2.execute("PRAGMA table_info(chunks)").fetchall()}
        assert "vec_blob" in cols
        assert conn2.execute("SELECT COUNT(*) FROM chunks WHERE vec_blob IS NULL").fetchone()[0] == 0
    finally:
        conn2.close()


def test_xerj_node_cleans_up_run_dir_on_exit_and_failure(tmp_path: Path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("xerj_clean", ROOT / "tooling/search/xerj.py")
    assert spec is not None and spec.loader is not None
    xerj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(xerj)

    monkeypatch.setattr(xerj, "STATE", tmp_path / "search_state")
    monkeypatch.setattr(xerj, "verify_binary", lambda: None)

    class _DeadProc:
        pid = 99999

        def poll(self):
            return 1

        def terminate(self):
            pass

        def wait(self, timeout=5):
            return 1

    monkeypatch.setattr(xerj.subprocess, "Popen", lambda *a, **k: _DeadProc())
    try:
        with xerj.node(lock_timeout=0.5):
            pass
        raise AssertionError("Expected RuntimeError when fake search process exits immediately")
    except RuntimeError as exc:
        assert "Owned search node exited" in str(exc)

    # Zero leaked run-* directories remain!
    leaked = list((tmp_path / "search_state").glob("run-*"))
    assert leaked == [], f"Leaked run-* dirs: {leaked}"
