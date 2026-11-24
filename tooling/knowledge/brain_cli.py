"""Naqex Knowledge Brain CLI: Local-First Markdown Source-of-Truth + Disposable SQLite FTS5 & Hybrid Vector Index.

Zero daemon, zero external API keys, Vietnamese diacritic-aware FTS5 (`unicode61 remove_diacritics 2`)
fused via Reciprocal Rank Fusion (RRF) with char/word TF-IDF cosine similarity and Evergreen preservation.

Usage:
  python -X utf8 tooling/knowledge/brain_cli.py index
  python -X utf8 tooling/knowledge/brain_cli.py query "thi quy calmar holdout" --top 8
  python -X utf8 tooling/knowledge/brain_cli.py owner-brief
  python -X utf8 tooling/knowledge/brain_cli.py log-curiosity --topic "AI" --question "..." --takeaway "..."
  python -X utf8 tooling/knowledge/brain_cli.py log-decision --decision "..." --reason "..." --revisit "..."
  python -X utf8 tooling/knowledge/brain_cli.py audit-data
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.parse import unquote

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BRAIN_DIR = ROOT / ".runtime/knowledge"
DB_PATH = BRAIN_DIR / "brain.sqlite3"
VEC_PATH = BRAIN_DIR / "brain_vec.npz"

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LEADING_SECTION_NUM_RE = re.compile(r"^(?:[0-9]+(?:\.[0-9]+)*\.?|[a-z]\.)\s+")
HEADING_STOPWORDS = frozenset({
    "va", "cua", "cho", "voi", "cac", "trong", "khi", "tu", "den", "la", "tai",
    "the", "and", "for", "of", "in", "on", "to", "vs", "with", "from", "by",
})
QUERY_STOPWORDS = HEADING_STOPWORDS | frozenset({
    "lam", "sao", "de", "do", "bi", "chi", "nao", "nhung", "nhu", "the", "thi",
    "co", "khong", "duoc", "nen", "can", "phai", "neu", "mot", "nhieu", "it",
    "gi", "bao", "nhieu", "cung", "luc", "truoc", "sau", "ve", "vao", "ra",
    "len", "xuong", "nay", "kia", "day", "roi", "ma", "hay", "hoac", "nhung",
    "se", "da", "dang", "con", "hon", "nhat", "rat", "qua", "tai", "sao",
    "what", "how", "why", "when", "where", "which", "who", "does", "should",
    "can", "could", "would", "this", "that", "these", "those", "about", "into",
    "are", "was", "were", "have", "has", "had", "not", "but", "all", "any",
})
TOKEN_RE = re.compile(r"[0-9a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\u4E00-\u9FFF\u0400-\u04FF_]{2,}")
VEC_DIM = 512  # Compact hashed feature space (zero-pickle float32 matrix -> < 5 MB, < 10 ms dot product)


def _strip_accents(text: str) -> str:
    # Normalize Vietnamese & Latin diacritics while keeping CJK & Cyrillic intact
    nk = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in nk if unicodedata.category(ch) != "Mn")


def _hash_vector(text: str) -> np.ndarray:
    """Deterministic multilingual hashed word + char-3gram TF vector (L2-normalized, zero external models)."""
    norm = _strip_accents(text)
    tokens = TOKEN_RE.findall(norm)
    vec = np.zeros(VEC_DIM, dtype=np.float32)
    counts: Counter[str] = Counter()
    for tok in tokens:
        counts[f"w:{tok}"] += 1
        if len(tok) >= 4:
            for i in range(len(tok) - 2):
                counts[f"c:{tok[i:i+3]}"] += 1
    for feat, cnt in counts.items():
        h = int.from_bytes(hashlib.blake2b(feat.encode("utf-8"), digest_size=4).digest(), "little")
        idx = h % VEC_DIM
        sign = 1.0 if ((h >> 16) & 1) else -1.0
        vec[idx] += sign * (1.0 + math.log(cnt))
    norm_val = float(np.linalg.norm(vec))
    if norm_val > 1e-9:
        vec /= norm_val
    return vec


def iter_knowledge_docs(*, include_archive: bool = False) -> list[tuple[str, Path, str, bool]]:
    """Discover all maintained Markdown sources across the workspace with clear domain & evergreen flags."""
    found: dict[str, tuple[Path, str, bool]] = {}

    def _add(p: Path, domain: str, evergreen: bool) -> None:
        if not p.is_file() or p.suffix.lower() != ".md" or p.stat().st_size > 1_000_000:
            return
        rel = p.relative_to(ROOT).as_posix()
        found[rel] = (p, domain, evergreen)

    # 1. Owner profile, curiosity journal, decisions, synthesized topics & playbooks
    for p in sorted((ROOT / "knowledge/owner").glob("*.md")):
        is_ev = p.name != "CURIOSITY-LOG.md"
        _add(p, "owner", is_ev)
    for p in sorted((ROOT / "knowledge/topics").glob("*.md")):
        _add(p, "knowledge", True)
    pb_dir = ROOT / "knowledge/playbooks"
    if pb_dir.is_dir():
        for p in sorted(pb_dir.glob("*.md")):
            _add(p, "knowledge", True)
    _add(ROOT / "knowledge/README.md", "knowledge", True)

    # 2. Workspace routing, lifecycle & morning briefings
    for name in ("planning/CURRENT-CONTEXT.md", "planning/CONTEXT-LIFECYCLE.md", "README.md"):
        _add(ROOT / name, "workspace", True)
    for p in sorted((ROOT / "planning").glob("MORNING-BRIEFING*.md")):
        _add(p, "workspace", False)

    # 3. Trading research reports (excluding archive index unless requested)
    pr = ROOT / "planning/research"
    if pr.is_dir():
        for p in sorted(pr.glob("*.md")):
            if not include_archive and p.name.startswith("ARCHIVE-INDEX"):
                continue
            _add(p, "trading_research", False)

    # 4. Architecture, workflow & search docs
    for folder in ("docs/development", "tooling/search", "tooling/ai-engines"):
        d = ROOT / folder
        if d.is_dir():
            for p in sorted(d.glob("*.md")):
                _add(p, "docs", True)

    # 5. Repo skills
    sk_dir = ROOT / ".agents/skills"
    if sk_dir.is_dir():
        for p in sorted(sk_dir.rglob("SKILL.md")):
            _add(p, "skill", True)
        for p in sorted(sk_dir.rglob("references/*.md")):
            _add(p, "skill", True)

    return [(rel, p, dom, ev) for rel, (p, dom, ev) in sorted(found.items())]


def chunk_markdown(text: str, rel_path: str) -> list[dict]:
    """Split Markdown by heading boundaries so retrieved snippets keep intact structure & line numbers."""
    lines = text.splitlines()
    chunks = []
    cur_heading = Path(rel_path).stem
    cur_lines: list[str] = []
    cur_start = 1

    def _flush(end_line: int) -> None:
        body = "\n".join(cur_lines).strip()
        if not body:
            return
        # Cap oversized single sections cleanly into ~1,800-char sub-chunks
        if len(body) <= 2000:
            chunks.append({"heading": cur_heading, "line_start": cur_start, "line_end": end_line, "body": body})
        else:
            step = 1800
            for off in range(0, len(body), step):
                part = body[off:off + step].strip()
                if part:
                    chunks.append({"heading": cur_heading, "line_start": cur_start, "line_end": end_line, "body": part})

    for idx, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            _flush(idx - 1)
            cur_heading = m.group(2).strip()
            cur_lines = [line]
            cur_start = idx
        else:
            cur_lines.append(line)
    _flush(len(lines))
    return chunks


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            chunk_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            heading TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            body TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            heading, body, content='chunks', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, heading, body) VALUES (new.id, new.heading, new.body);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, heading, body) VALUES('delete', old.id, old.heading, old.body);
        END;
    """)


def index_brain(*, force: bool = False, include_archive: bool = False) -> dict:
    """Incrementally index all workspace Markdown knowledge using SHA-256 change detection."""
    t0 = time.perf_counter()
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    existing = {row[0]: row[1] for row in conn.execute("SELECT path, sha256 FROM files")}
    docs = iter_knowledge_docs(include_archive=include_archive)
    current_paths = {rel for rel, *_ in docs}

    removed = 0
    for old_path in set(existing) - current_paths:
        conn.execute("DELETE FROM chunks WHERE path = ?", (old_path,))
        conn.execute("DELETE FROM files WHERE path = ?", (old_path,))
        removed += 1

    updated = 0
    unchanged = 0
    for rel, p, domain, evergreen in docs:
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if existing.get(rel) == digest and not force:
            unchanged += 1
            continue
        text = raw.decode("utf-8", errors="replace")
        chunks = chunk_markdown(text, rel)
        mtime = p.stat().st_mtime
        conn.execute("DELETE FROM chunks WHERE path = ?", (rel,))
        for ch in chunks:
            conn.execute(
                "INSERT INTO chunks(path, heading, line_start, line_end, domain, evergreen, updated_ts, body) VALUES (?,?,?,?,?,?,?,?)",
                (rel, ch["heading"], ch["line_start"], ch["line_end"], domain, int(evergreen), mtime, ch["body"]),
            )
        conn.execute(
            "INSERT OR REPLACE INTO files(path, sha256, domain, evergreen, updated_ts, chunk_count) VALUES (?,?,?,?,?,?)",
            (rel, digest, domain, int(evergreen), mtime, len(chunks)),
        )
        updated += 1
    conn.commit()

    # Rebuild compact zero-pickle vector matrix only if index changed or vector file missing
    total_chunks = int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    if updated > 0 or removed > 0 or not VEC_PATH.exists():
        rows = conn.execute("SELECT id, heading, body FROM chunks ORDER BY id").fetchall()
        ids = np.array([r[0] for r in rows], dtype=np.int64)
        vecs = np.vstack([_hash_vector(f"{r[1]}\n{r[2]}") for r in rows]) if rows else np.empty((0, VEC_DIM), dtype=np.float32)
        np.savez(VEC_PATH, ids=ids, vecs=vecs)
    conn.close()

    return {
        "db_path": str(DB_PATH.relative_to(ROOT).as_posix()),
        "files_total": len(docs),
        "files_updated": updated,
        "files_unchanged": unchanged,
        "files_removed": removed,
        "chunks_total": total_chunks,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
    }


def _extract_query_tokens(query: str) -> list[str]:
    """Extract informative, deduplicated bilingual query tokens (filtering VI+EN filler stopwords)."""
    raw_toks = [t for t in TOKEN_RE.findall(_strip_accents(query)) if len(t) >= 2]
    filtered = [t for t in raw_toks if t not in QUERY_STOPWORDS]
    chosen = filtered if filtered else raw_toks
    # Deduplicate preserving order, preferring informative domain tokens (digits/uppercase/longer words)
    seen: set[str] = set()
    uniq: list[str] = []
    for t in chosen:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    # Prioritize tokens containing digits or length >= 4 so domain terms (ftmo, the5ers, ibkr, us100, 500, cex) never get truncated
    uniq.sort(key=lambda t: (not any(ch.isdigit() for ch in t), len(t) < 4))
    return uniq[:18]


def rerank_hits_typesafe(
    query: str,
    hits: list[dict],
    *,
    top_k: int = 8,
    model: str = "jev-1.14.0",
    no_match_threshold: float = 0.30,
    transport=None,
) -> dict:
    """Rerank a Stage-1 shortlist using ONE batched TypeSafe (`jev-1.14.0`) request.

    Follows TypeSafe `rerank_typesafe` + `classifying_rag_passages` + companion Noul pattern:
      - One companion Noul (`has_relevant_doc`) detects absent/off-topic queries (`< 0.30 -> no_match`).
      - One per-candidate relevance Noul (`rel_doc_i`) scores every passage in parallel.
      - One Choice (`best_doc`) selects the single best passage for Top-1 boost.
    Raises `TypeSafeUnavailableError` / `TypeSafeAPIError` fail-closed if API fails.
    """
    if not hits:
        return {
            "enabled": True,
            "model": model,
            "has_relevant_doc_noul": 0.0,
            "no_match": True,
            "best_choice": None,
            "hits": [],
            "latency_ms": 0.0,
            "est_cost_usd": 0.0,
        }
    import sys as _sys
    qf_dir = ROOT / "tooling/ai-engines/quant_factory"
    if str(qf_dir) not in _sys.path:
        _sys.path.insert(0, str(qf_dir))
    import typesafe_client as ts  # noqa: WPS433

    shortlist = hits[:12]
    cand_map: dict[str, dict[str, str]] = {}
    choice_criteria: dict[str, str] = {}
    questions: dict[str, dict] = {
        "has_relevant_doc": {
            "type": "noul",
            "instructions": "Does at least one passage in `candidates` directly contain factual information that answers `user_query`?",
            "criteria": {
                "true": "One or more passages in `candidates` directly address the exact topic asked in `user_query`.",
                "false": "All passages in `candidates` are about unrelated topics and do not answer `user_query`.",
            },
        },
    }
    for idx, h in enumerate(shortlist, start=1):
        cid = f"doc_{idx}"
        cand_map[cid] = {
            "path": h["path"],
            "heading": h["heading"],
            "snippet": str(h.get("snippet", ""))[:500],
        }
        choice_criteria[cid] = f"Candidate `{cid}` ({h['path']} — {h['heading']}) best answers `user_query`."
        questions[f"rel_{cid}"] = {
            "type": "noul",
            "instructions": f"Does candidate `{cid}` in `candidates` directly answer or provide key facts for `user_query`?",
            "criteria": {
                "true": f"Candidate `{cid}` directly addresses the specific topic in `user_query`.",
                "false": f"Candidate `{cid}` is tangential or unrelated to `user_query`.",
            },
        }
    questions["best_doc"] = {
        "type": "choice",
        "instructions": "Which single candidate in `candidates` best answers `user_query`?",
        "criteria": choice_criteria,
    }

    res = ts.call_system_one(
        {"user_query": query, "candidates": cand_map},
        questions,
        model=model,
        transport=transport,
    )
    answers = res["answers"]
    has_rel = ts.extract_noul(answers, "has_relevant_doc")
    best_cid = (answers.get("best_doc") or {}).get("choice")
    best_conf = (answers.get("best_doc") or {}).get("confidence")
    no_match = has_rel < no_match_threshold

    reranked: list[dict] = []
    for idx, h in enumerate(shortlist, start=1):
        cid = f"doc_{idx}"
        rel_p = ts.extract_noul(answers, f"rel_{cid}")
        is_best = (cid == best_cid) and (not no_match)
        # Rank strictly by calibrated relevance probability (with small tie-break for Choice #1 & Stage-1 RRF)
        combined = round(rel_p + (0.08 if is_best else 0.0) + 0.02 * float(h["score"]), 5)
        item = dict(h)
        item["stage1_score"] = h["score"]
        item["typesafe_relevance_noul"] = round(rel_p, 4)
        item["typesafe_is_best_choice"] = is_best
        item["score"] = combined
        reranked.append(item)
    reranked.sort(key=lambda x: -x["score"])

    return {
        "enabled": True,
        "model": res["model"],
        "has_relevant_doc_noul": round(has_rel, 4),
        "no_match": no_match,
        "best_choice": best_cid,
        "best_choice_confidence": round(float(best_conf), 4) if best_conf is not None else None,
        "latency_ms": res["latency_ms"],
        "usage": res["usage"],
        "est_cost_usd": res["est_cost_usd"],
        "hits": [] if no_match else reranked[:top_k],
        "rejected_shortlist_count": len(reranked) if no_match else 0,
    }


def query_brain(
    query: str,
    *,
    domain: str = "all",
    top_k: int = 8,
    rerank: str = "none",
    typesafe_model: str = "jev-1.14.0",
    typesafe_transport=None,
) -> dict:
    """Hybrid RRF retrieval combining SQLite FTS5 BM25 + Multilingual Hashed Vector Cosine + Evergreen Boost.

    Pass `rerank="typesafe"` (opt-in) to semantically rerank the Stage-1 Top-12 shortlist via
    TypeSafe `jev-1.14.0` with explicit `no_match` abstention. Default `rerank="none"` is 100% offline.
    """
    t0 = time.perf_counter()
    if not DB_PATH.exists() or not VEC_PATH.exists():
        index_brain()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. FTS5 BM25 search with VI+EN stopword removal so informative domain tokens never get truncated
    toks = _extract_query_tokens(query)
    fts_ranks: dict[int, int] = {}
    if toks:
        fts_expr = " OR ".join(f'"{t}"' for t in toks)
        sql = """
            SELECT c.id, bm25(chunks_fts, 2.0, 1.0) AS score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
        """
        params: list = [fts_expr]
        if domain != "all":
            sql += " AND c.domain = ?"
            params.append(domain)
        sql += " ORDER BY score LIMIT 80"
        for rank, row in enumerate(conn.execute(sql, params).fetchall(), start=1):
            fts_ranks[int(row["id"])] = rank

    # 2. Vector cosine similarity across all chunks (< 5 ms matrix-vector multiply)
    z = np.load(VEC_PATH, allow_pickle=False)
    ids = z["ids"]
    vecs = z["vecs"]
    vec_ranks: dict[int, int] = {}
    if len(ids) > 0:
        clean_q = " ".join(toks) if toks else query
        qv = _hash_vector(clean_q)
        sims = vecs @ qv
        order = np.argsort(-sims)[:80]
        if domain != "all":
            allowed_ids = {int(r[0]) for r in conn.execute("SELECT id FROM chunks WHERE domain = ?", (domain,))}
        else:
            allowed_ids = None
        rank_i = 0
        for idx in order:
            cid = int(ids[idx])
            if allowed_ids is not None and cid not in allowed_ids:
                continue
            if float(sims[idx]) <= 0.02:
                break
            rank_i += 1
            vec_ranks[cid] = rank_i
            if rank_i >= 60:
                break

    # 3. Reciprocal Rank Fusion (RRF) + Evergreen protection & mild temporal decay
    cand_ids = set(fts_ranks) | set(vec_ranks)
    if not cand_ids:
        conn.close()
        return {"query": query, "domain": domain, "rerank": rerank, "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1), "hits": []}

    placeholders = ",".join("?" for _ in cand_ids)
    meta_rows = {
        int(r["id"]): dict(r)
        for r in conn.execute(f"SELECT id, path, heading, line_start, line_end, domain, evergreen, updated_ts, body FROM chunks WHERE id IN ({placeholders})", tuple(cand_ids))
    }
    conn.close()

    now_ts = time.time()
    scored = []
    for cid in cand_ids:
        m = meta_rows[cid]
        rrf = 0.0
        if cid in fts_ranks:
            rrf += 1.35 / (35.0 + fts_ranks[cid])
        if cid in vec_ranks:
            rrf += 1.0 / (40.0 + vec_ranks[cid])
        if m["evergreen"]:
            rrf *= 1.15 if m["domain"] == "owner" else 1.08
        else:
            age_days = max(0.0, (now_ts - float(m["updated_ts"])) / 86400.0)
            rrf *= (0.80 + 0.20 * math.exp(-age_days / 180.0))
        snippet = re.sub(r"\s+", " ", m["body"]).strip()[:420]
        scored.append({
            "score": round(rrf, 5),
            "path": m["path"],
            "lines": f"L{m['line_start']}-L{m['line_end']}",
            "domain": m["domain"],
            "evergreen": bool(m["evergreen"]),
            "heading": m["heading"],
            "fts_rank": fts_ranks.get(cid),
            "vec_rank": vec_ranks.get(cid),
            "snippet": snippet,
        })
    scored.sort(key=lambda x: -x["score"])

    if rerank == "typesafe":
        rr = rerank_hits_typesafe(
            query,
            scored[:max(12, top_k * 2)],
            top_k=top_k,
            model=typesafe_model,
            transport=typesafe_transport,
        )
        return {
            "query": query,
            "domain": domain,
            "rerank": "typesafe",
            "no_match": rr["no_match"],
            "typesafe_rerank": {k: v for k, v in rr.items() if k != "hits"},
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
            "hits": rr["hits"],
        }

    return {
        "query": query,
        "domain": domain,
        "rerank": "none",
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        "hits": scored[:top_k],
    }


def owner_brief() -> str:
    prof = (ROOT / "knowledge/owner/PROFILE.md").read_text(encoding="utf-8")
    cur_lines = (ROOT / "knowledge/owner/CURIOSITY-LOG.md").read_text(encoding="utf-8").splitlines()
    recent_cur = [l for l in cur_lines if l.startswith("- **[")][-5:]
    dec_lines = (ROOT / "knowledge/owner/DECISIONS-JOURNAL.md").read_text(encoding="utf-8").splitlines()
    recent_dec = [l for l in dec_lines if l.startswith("| `202")][-5:]
    out = [
        "=== NAQEX OWNER BRIEF ===",
        prof.strip(),
        "\n--- Recent Curiosities (last 5) ---",
        *recent_cur,
        "\n--- Recent Strategic Decisions (last 5) ---",
        *recent_dec,
    ]
    return "\n".join(out)


def log_curiosity(topic: str, question: str, takeaway: str, source: str = "") -> dict:
    p = ROOT / "knowledge/owner/CURIOSITY-LOG.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = p.read_text(encoding="utf-8")
    day_hdr = f"## {today}"
    src_str = f" Nguồn: {source}." if source else ""
    entry = f"- **[{topic}]** *{question}*\n  - **Tóm tắt / Kết quả:** {takeaway}{src_str}\n"
    if day_hdr in text:
        new_text = text.rstrip() + "\n" + entry
    else:
        new_text = text.rstrip() + f"\n\n{day_hdr}\n\n" + entry
    p.write_text(new_text, encoding="utf-8", newline="\n")
    idx_res = index_brain()
    return {"logged_to": str(p.relative_to(ROOT).as_posix()), "date": today, "index": idx_res}


def log_decision(decision: str, reason: str, revisit: str) -> dict:
    p = ROOT / "knowledge/owner/DECISIONS-JOURNAL.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f"| `{today}` | {decision} | {reason} | {revisit} |\n"
    text = p.read_text(encoding="utf-8").rstrip() + "\n" + row
    p.write_text(text, encoding="utf-8", newline="\n")
    idx_res = index_brain()
    return {"logged_to": str(p.relative_to(ROOT).as_posix()), "date": today, "index": idx_res}


def _dir_size_and_count(path: Path) -> tuple[int, int]:
    """Fast recursive file size + count using os.scandir (reuses Windows FindNextFile metadata)."""
    total_bytes = 0
    count = 0
    stack = [str(path)]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            count += 1
                            total_bytes += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total_bytes, count


def _iter_non_code_lines(text: str):
    """Yield (line_no, line) skipping YAML frontmatter and fenced code blocks."""
    lines = text.splitlines()
    in_fence = False
    in_frontmatter = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if idx == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield idx, line


def _clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")].strip()
    else:
        # Drop optional Markdown title suffix e.g. path.md "Title"
        target = re.split(r'\s+(?=["\'])', target, maxsplit=1)[0].strip()
    return target


def find_broken_knowledge_links(root: Path | None = None) -> list[dict]:
    """Detect broken relative Markdown links inside maintained `knowledge/` docs (excluding gitignored `inbox/`)."""
    base = root if root is not None else ROOT
    kb_dir = base / "knowledge"
    if not kb_dir.is_dir():
        return []
    broken: list[dict] = []
    for md_file in sorted(kb_dir.rglob("*.md")):
        rel_parts = md_file.relative_to(kb_dir).parts
        if rel_parts and rel_parts[0] == "inbox":
            continue
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in _iter_non_code_lines(text):
            cleaned_line = INLINE_CODE_RE.sub("", line)
            for m in MD_LINK_RE.finditer(cleaned_line):
                raw_target = _clean_link_target(m.group(1))
                if not raw_target or raw_target.startswith("#"):
                    continue
                low = raw_target.lower()
                if low.startswith(("http://", "https://", "mailto:", "file://", "conversation://", "tel:", "data:")):
                    continue
                path_only = raw_target.split("#", 1)[0].split("?", 1)[0].strip()
                if not path_only:
                    continue
                path_only = unquote(path_only)
                resolved = (md_file.parent / path_only).resolve()
                if not resolved.exists():
                    broken.append({
                        "file": md_file.relative_to(base).as_posix(),
                        "line": line_no,
                        "target": raw_target,
                    })
    return broken


def _normalize_heading_tokens(heading: str) -> tuple[str, set[str]]:
    norm = _strip_accents(heading)
    norm = re.sub(r"[`*_~]", "", norm)
    norm = LEADING_SECTION_NUM_RE.sub("", norm).strip()
    norm = re.sub(r"\s+", " ", norm)
    raw_toks = TOKEN_RE.findall(norm)
    filtered = {t for t in raw_toks if t not in HEADING_STOPWORDS}
    toks = filtered if len(filtered) >= 2 else set(raw_toks)
    return norm, toks


def find_near_duplicate_topic_headings(
    root: Path | None = None,
    *,
    similarity_threshold: float = 0.70,
) -> list[dict]:
    """Detect exact or near-duplicate headings across `knowledge/topics/*.md` using diacritic-free token Jaccard & sequence similarity."""
    base = root if root is not None else ROOT
    topics_dir = base / "knowledge/topics"
    if not topics_dir.is_dir():
        return []

    records: list[tuple[str, int, str, str, set[str]]] = []
    for md_file in sorted(topics_dir.glob("*.md")):
        rel = md_file.relative_to(base).as_posix()
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in _iter_non_code_lines(text):
            m = HEADING_RE.match(line)
            if not m:
                continue
            heading_txt = m.group(2).strip()
            norm, toks = _normalize_heading_tokens(heading_txt)
            if not norm:
                continue
            records.append((rel, line_no, heading_txt, norm, toks))

    dups: list[dict] = []
    for i in range(len(records)):
        rel_a, line_a, h_a, norm_a, toks_a = records[i]
        for j in range(i + 1, len(records)):
            rel_b, line_b, h_b, norm_b, toks_b = records[j]
            sim = 0.0
            if norm_a == norm_b:
                sim = 1.0
            else:
                union = toks_a | toks_b
                jaccard = (len(toks_a & toks_b) / len(union)) if union else 0.0
                seq_ratio = (
                    SequenceMatcher(None, norm_a, norm_b).ratio()
                    if min(len(norm_a), len(norm_b)) >= 12
                    else 0.0
                )
                if jaccard >= similarity_threshold or seq_ratio >= 0.85:
                    sim = max(jaccard, seq_ratio)
            if sim >= similarity_threshold:
                dups.append({
                    "file_a": rel_a,
                    "line_a": line_a,
                    "heading_a": h_a,
                    "file_b": rel_b,
                    "line_b": line_b,
                    "heading_b": h_b,
                    "similarity": round(sim, 3),
                })
    dups.sort(key=lambda x: (-x["similarity"], x["file_a"], x["line_a"]))
    return dups


def audit_data() -> dict:
    """Read-only workspace data hygiene & knowledge index health audit."""
    rt = ROOT / ".runtime"
    empty_tmp_dirs = []
    heavy_rt_dirs = []
    if rt.is_dir():
        for d in sorted(rt.iterdir()):
            if not d.is_dir():
                continue
            total_b, f_count = _dir_size_and_count(d)
            sz_mb = total_b / (1024 * 1024)
            if f_count == 0 and any(tok in d.name.lower() for tok in ("tmp", "temp", "smoke", "dry", "quant-suite-")):
                empty_tmp_dirs.append(d.name)
            elif sz_mb >= 200.0:
                heavy_rt_dirs.append({"dir": d.name, "size_mb": round(sz_mb, 1), "files": f_count})
    heavy_rt_dirs.sort(key=lambda x: -x["size_mb"])

    pr_count = len(list((ROOT / "planning/research").glob("*"))) if (ROOT / "planning/research").is_dir() else 0
    kb_count = len(list((ROOT / "knowledge").rglob("*.md"))) if (ROOT / "knowledge").is_dir() else 0
    db_ok = DB_PATH.exists() and VEC_PATH.exists()
    db_kb = round((DB_PATH.stat().st_size + VEC_PATH.stat().st_size) / 1024.0, 1) if db_ok else 0.0
    broken_links = find_broken_knowledge_links(ROOT)
    near_dup_headings = find_near_duplicate_topic_headings(ROOT)
    return {
        "brain_index_ready": db_ok,
        "brain_index_kb": db_kb,
        "knowledge_md_files": kb_count,
        "planning_research_files": pr_count,
        "dead_empty_runtime_dirs": empty_tmp_dirs,
        "heavy_runtime_dirs_ge_200mb": heavy_rt_dirs,
        "broken_knowledge_links_count": len(broken_links),
        "broken_knowledge_links": broken_links,
        "near_duplicate_topic_headings_count": len(near_dup_headings),
        "near_duplicate_topic_headings": near_dup_headings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Knowledge Brain CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index")
    p_idx.add_argument("--force", action="store_true")
    p_idx.add_argument("--include-archive", action="store_true")

    p_q = sub.add_parser("query")
    p_q.add_argument("text")
    p_q.add_argument("--domain", default="all", choices=("all", "owner", "knowledge", "workspace", "trading_research", "docs", "skill"))
    p_q.add_argument("--top", type=int, default=8)
    p_q.add_argument("--rerank", default="none", choices=("none", "typesafe"), help="Optional Stage-2 semantic reranker (default: none/offline).")
    p_q.add_argument("--model", default="jev-1.14.0", help="Pinned TypeSafe model ID when --rerank typesafe.")
    p_q.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("owner-brief")

    p_cur = sub.add_parser("log-curiosity")
    p_cur.add_argument("--topic", required=True)
    p_cur.add_argument("--question", required=True)
    p_cur.add_argument("--takeaway", required=True)
    p_cur.add_argument("--source", default="")

    p_dec = sub.add_parser("log-decision")
    p_dec.add_argument("--decision", required=True)
    p_dec.add_argument("--reason", required=True)
    p_dec.add_argument("--revisit", required=True)

    sub.add_parser("audit-data")

    args = ap.parse_args()
    if args.cmd == "index":
        print(json.dumps(index_brain(force=args.force, include_archive=args.include_archive), indent=2, ensure_ascii=False))
    elif args.cmd == "query":
        res = query_brain(args.text, domain=args.domain, top_k=args.top, rerank=args.rerank, typesafe_model=args.model)
        if args.as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            extra = f", rerank={res.get('rerank', 'none')}"
            if res.get("no_match"):
                extra += ", NO_MATCH"
            print(f"Brain Query ({res['elapsed_ms']}ms, domain={res['domain']}{extra}): {res['query']}")
            if res.get("no_match"):
                rr = res.get("typesafe_rerank", {})
                print(f"  [NO MATCH] has_relevant_doc={rr.get('has_relevant_doc_noul')} (< 0.30) — rejected {rr.get('rejected_shortlist_count', 0)} unrelated candidates.")
            for i, h in enumerate(res["hits"], 1):
                tag = "EVERGREEN" if h["evergreen"] else "DATED"
                rel_s = f"|jev={h['typesafe_relevance_noul']:.2f}" if "typesafe_relevance_noul" in h else ""
                print(f"  {i}. [{h['domain']}|{tag}|score={h['score']:.4f}{rel_s}] {h['path']}#{h['lines']} — {h['heading']}")
                print(f"     {h['snippet'][:200]}")
    elif args.cmd == "owner-brief":
        print(owner_brief())
    elif args.cmd == "log-curiosity":
        print(json.dumps(log_curiosity(args.topic, args.question, args.takeaway, args.source), indent=2, ensure_ascii=False))
    elif args.cmd == "log-decision":
        print(json.dumps(log_decision(args.decision, args.reason, args.revisit), indent=2, ensure_ascii=False))
    elif args.cmd == "audit-data":
        print(json.dumps(audit_data(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
