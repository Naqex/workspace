"""Unified Experiment Ledger combining `tooling/run_registry/store.py` (SQLite hash chain) + DuckDB.

Stores every research trial atomically in:
  1. Tamper-evident append-only `SQLiteRunRegistry` (SHA-256 hash chain + idempotency key).
  2. Local file `.runtime/experiments/experiments.duckdb` (`duckdb 2.0.1`, zero server) for `<0.1s`
     SQL analytics (`get_cumulative_trial_count`, `get_family_p_values`, cross-family comparisons).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import threading
import weakref
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tooling.run_registry.store import (  # noqa: E402
    JournalCorruptionError,
    Provenance,
    RunEvent,
    RunRecord,
    SQLiteRunRegistry,
    utc_now,
)

DEFAULT_EXPERIMENTS_DIR: Path = REPO_ROOT / ".runtime" / "experiments"
DEFAULT_DUCKDB_PATH: Path = DEFAULT_EXPERIMENTS_DIR / "experiments.duckdb"
DEFAULT_REGISTRY_PATH: Path = DEFAULT_EXPERIMENTS_DIR / "run_registry.sqlite3"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
_READONLY_SQL_START_RE = re.compile(r"^\s*(?:SELECT|WITH|EXPLAIN|DESCRIBE|SHOW)\b", re.IGNORECASE)
_FORBIDDEN_SQL_WRITE_RE = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|COPY|CALL|LOAD|INSTALL|EXPORT|IMPORT|MERGE|SET|PRAGMA)\b",
    re.IGNORECASE,
)


def _close_con_box(box: list[duckdb.DuckDBPyConnection | None]) -> None:
    con = box[0]
    box[0] = None
    if con is not None:
        try:
            con.close()
        except Exception:
            pass


_LEDGER_COLS: tuple[str, ...] = (
    "run_id",
    "git_sha",
    "data_sha",
    "strategy_id",
    "family_id",
    "sharpe",
    "dsr",
    "pbo",
    "spa_p",
    "npv_usd",
    "p_le_zero",
    "p_value",
    "created_utc",
)
_FLOAT_COLS: frozenset[str] = frozenset({"sharpe", "dsr", "pbo", "spa_p", "npv_usd", "p_le_zero", "p_value"})


def _column_matches(col: str, duck_val: Any, expected_val: Any) -> bool:
    if col in _FLOAT_COLS:
        if duck_val is None and expected_val is None:
            return True
        if duck_val is None or expected_val is None:
            return False
        dv = float(duck_val)
        ev = float(expected_val)
        return math.isfinite(dv) and math.isfinite(ev) and math.isclose(dv, ev, rel_tol=1e-12, abs_tol=1e-12)
    return str(duck_val) == str(expected_val)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS experiments (
    run_id VARCHAR PRIMARY KEY,
    git_sha VARCHAR NOT NULL,
    data_sha VARCHAR NOT NULL,
    strategy_id VARCHAR NOT NULL,
    family_id VARCHAR NOT NULL,
    sharpe DOUBLE,
    dsr DOUBLE,
    pbo DOUBLE,
    spa_p DOUBLE,
    npv_usd DOUBLE,
    p_le_zero DOUBLE,
    p_value DOUBLE NOT NULL,
    created_utc VARCHAR NOT NULL
);
"""


def _require_text(val: Any, name: str) -> str:
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return val.strip()


def _validate_opt_float(
    val: Any,
    name: str,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be a finite float or None, got {type(val).__name__}")
    out = float(val)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite, got {val!r}")
    if lo is not None and out < lo:
        raise ValueError(f"{name}={out} must be >= {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}={out} must be <= {hi}")
    return out


def _safe_reg_id(raw: str, *, prefix: str = "exp", max_len: int = 120) -> str:
    cleaned = _SAFE_ID_RE.sub("_", raw.strip()).strip("_.:-")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"{prefix}-{cleaned}" if cleaned else f"{prefix}-0"
    return cleaned[:max_len]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    run_id: str
    git_sha: str
    data_sha: str
    strategy_id: str
    family_id: str
    p_value: float
    sharpe: float | None = None
    dsr: float | None = None
    pbo: float | None = None
    spa_p: float | None = None
    npv_usd: float | None = None
    p_le_zero: float | None = None
    created_utc: str = ""


class ExperimentLedger:
    """Dual-backed experiment ledger: SQLiteRunRegistry hash chain + local DuckDB SQL store."""

    def __init__(
        self,
        duckdb_path: str | Path = DEFAULT_DUCKDB_PATH,
        registry_path: str | Path | None = None,
    ) -> None:
        self.duckdb_path = Path(duckdb_path)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path = (
            Path(registry_path) if registry_path is not None else self.duckdb_path.with_name("run_registry.sqlite3")
        )
        self.registry = SQLiteRunRegistry(self.registry_path)
        self._lock = threading.RLock()
        self._con_box: list[duckdb.DuckDBPyConnection | None] = [None]
        self._finalizer = weakref.finalize(self, _close_con_box, self._con_box)
        with self._connect() as con:
            con.execute(_SCHEMA_SQL)

    def close(self) -> None:
        """Close the cached DuckDB connection cleanly (idempotent)."""
        with self._lock:
            _close_con_box(self._con_box)

    def __enter__(self) -> ExperimentLedger:
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    @contextmanager
    def _connect(self, *, read_only: bool = False) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Borrow a reusable in-process DuckDB connection (avoids ~30 ms cold file-open per query).

        Uses DuckDB's default read-write DatabaseInstance configuration so same-process external
        `duckdb.connect(path)` calls share the instance seamlessly without configuration conflicts.
        """
        _ = read_only
        with self._lock:
            con = self._con_box[0]
            if con is None:
                con = duckdb.connect(str(self.duckdb_path))
                self._con_box[0] = con
            yield con

    def record_experiment(
        self,
        *,
        run_id: str,
        git_sha: str,
        data_sha: str,
        strategy_id: str,
        family_id: str,
        p_value: float,
        sharpe: float | None = None,
        dsr: float | None = None,
        pbo: float | None = None,
        spa_p: float | None = None,
        npv_usd: float | None = None,
        p_le_zero: float | None = None,
        created_utc: str | None = None,
    ) -> dict[str, Any]:
        """Atomically record a trial into `SQLiteRunRegistry` (hash-chained) and DuckDB."""
        rid = _require_text(run_id, "run_id")
        gsha = _require_text(git_sha, "git_sha")
        dsha = _require_text(data_sha, "data_sha")
        sid = _require_text(strategy_id, "strategy_id")
        fid = _require_text(family_id, "family_id")
        pval = _validate_opt_float(p_value, "p_value", lo=0.0, hi=1.0)
        if pval is None:
            raise ValueError("p_value is required")

        sh = _validate_opt_float(sharpe, "sharpe")
        dsr_v = _validate_opt_float(dsr, "dsr", lo=0.0, hi=1.0)
        pbo_v = _validate_opt_float(pbo, "pbo", lo=0.0, hi=1.0)
        spa_v = _validate_opt_float(spa_p, "spa_p", lo=0.0, hi=1.0)
        npv_v = _validate_opt_float(npv_usd, "npv_usd")
        ple0_v = _validate_opt_float(p_le_zero, "p_le_zero", lo=0.0, hi=1.0)
        ts_utc = created_utc or utc_now()

        payload = {
            "run_id": rid,
            "git_sha": gsha,
            "data_sha": dsha,
            "strategy_id": sid,
            "family_id": fid,
            "sharpe": sh,
            "dsr": dsr_v,
            "pbo": pbo_v,
            "spa_p": spa_v,
            "npv_usd": npv_v,
            "p_le_zero": ple0_v,
            "p_value": pval,
            "created_utc": ts_utc,
        }
        config_sha = _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        input_sha = dsha if _SHA256_RE.fullmatch(dsha) else _sha256_text(dsha)
        prov = Provenance(
            code_revision=gsha,
            config_sha256=config_sha,
            input_sha256=input_sha,
            source_refs=(f"family:{fid}", f"strategy:{sid}"),
        )
        run_rec = RunRecord(
            run_id=rid,
            attempt_no=1,
            fence_token=f"ledger-{rid}",
            project_id="quant_factory",
            run_kind="experiment_trial",
            mode="research",
            correlation_id=_safe_reg_id(f"fam-{fid}", prefix="fam"),
            provenance=prov,
            created_at_utc=ts_utc,
        )
        registered = self.registry.register_run(run_rec)
        event: RunEvent = self.registry.append(
            RunEvent.create(
                event_type="experiment.recorded",
                run=registered,
                idempotency_key=_safe_reg_id(f"exp-{rid}", prefix="exp"),
                event_id=_safe_reg_id(f"evt-{rid}", prefix="evt"),
                occurred_at_utc=ts_utc,
                payload=payload,
            )
        )

        with self._connect() as con:
            existing = con.execute("SELECT run_id FROM experiments WHERE run_id = ?", [rid]).fetchone()
            if existing is None:
                con.execute(
                    """
                    INSERT INTO experiments (
                        run_id, git_sha, data_sha, strategy_id, family_id,
                        sharpe, dsr, pbo, spa_p, npv_usd, p_le_zero, p_value, created_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [rid, gsha, dsha, sid, fid, sh, dsr_v, pbo_v, spa_v, npv_v, ple0_v, pval, ts_utc],
                )

        return {
            **payload,
            "registry_sequence": event.sequence,
            "registry_event_hash": event.event_hash,
        }

    def get_cumulative_trial_count(self, family_id: str) -> int:
        """Return exact cumulative count of recorded trials `M` for `family_id` (<0.1s SQL)."""
        fid = _require_text(family_id, "family_id")
        with self._connect(read_only=True) as con:
            row = con.execute("SELECT COUNT(*) FROM experiments WHERE family_id = ?", [fid]).fetchone()
        return int(row[0]) if row is not None else 0

    def get_family_p_values(self, family_id: str) -> list[float]:
        """Return chronologically ordered raw p-values for all recorded trials in `family_id`."""
        fid = _require_text(family_id, "family_id")
        with self._connect(read_only=True) as con:
            rows = con.execute(
                "SELECT p_value FROM experiments WHERE family_id = ? ORDER BY created_utc ASC, run_id ASC",
                [fid],
            ).fetchall()
        return [float(r[0]) for r in rows]

    def has_strategy(self, family_id: str, strategy_id: str) -> bool:
        """Check whether `(family_id, strategy_id)` has already been logged in the ledger."""
        fid = _require_text(family_id, "family_id")
        sid = _require_text(strategy_id, "strategy_id")
        with self._connect(read_only=True) as con:
            row = con.execute(
                "SELECT COUNT(*) FROM experiments WHERE family_id = ? AND strategy_id = ?",
                [fid, sid],
            ).fetchone()
        return bool(row is not None and int(row[0]) > 0)

    def query_family(self, family_id: str) -> list[dict[str, Any]]:
        """Return all trial records for `family_id` ordered chronologically."""
        fid = _require_text(family_id, "family_id")
        cols = (
            "run_id",
            "git_sha",
            "data_sha",
            "strategy_id",
            "family_id",
            "sharpe",
            "dsr",
            "pbo",
            "spa_p",
            "npv_usd",
            "p_le_zero",
            "p_value",
            "created_utc",
        )
        with self._connect(read_only=True) as con:
            rows = con.execute(
                f"SELECT {', '.join(cols)} FROM experiments WHERE family_id = ? ORDER BY created_utc ASC, run_id ASC",
                [fid],
            ).fetchall()
        return [dict(zip(cols, row, strict=True)) for row in rows]

    def query_sql(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        """Execute a read-only parameterized SQL query against the local DuckDB file."""
        stmt = _require_text(sql, "sql")
        stripped = stmt.rstrip().rstrip(";").strip()
        if ";" in stripped or not _READONLY_SQL_START_RE.match(stripped) or _FORBIDDEN_SQL_WRITE_RE.search(stripped):
            raise ValueError("query_sql only permits single read-only SELECT/WITH queries")
        with self._connect(read_only=True) as con:
            return list(con.execute(stripped, list(params)).fetchall())

    def verify_integrity(self) -> dict[str, Any]:
        """Verify BOTH SQLite hash-chain integrity AND full column-level DuckDB vs SQLite parity."""
        events = self.registry.replay()
        expected_by_run_id: dict[str, dict[str, Any]] = {}
        for ev in events:
            if ev.event_type != "experiment.recorded":
                continue
            payload = dict(ev.payload)
            rid = str(ev.run_id)
            if str(payload.get("run_id")) != rid:
                raise JournalCorruptionError(
                    f"LEDGER_PAYLOAD_RUN_ID_MISMATCH: event.run_id={rid!r} != payload.run_id={payload.get('run_id')!r}"
                )
            if rid in expected_by_run_id:
                prev = expected_by_run_id[rid]
                for col in _LEDGER_COLS:
                    if not _column_matches(col, payload.get(col), prev.get(col)):
                        raise JournalCorruptionError(f"LEDGER_DUPLICATE_CONFLICT: run_id={rid!r} column={col!r}")
            else:
                expected_by_run_id[rid] = payload

        col_sql = ", ".join(_LEDGER_COLS)
        with self._connect(read_only=True) as con:
            duck_rows = con.execute(f"SELECT {col_sql} FROM experiments").fetchall()

        duck_by_run_id = {str(row[0]): dict(zip(_LEDGER_COLS, row, strict=True)) for row in duck_rows}
        reg_run_ids = set(expected_by_run_id)
        duck_run_ids = set(duck_by_run_id)

        missing_in_duck = sorted(reg_run_ids - duck_run_ids)
        extra_in_duck = sorted(duck_run_ids - reg_run_ids)
        if missing_in_duck or extra_in_duck:
            raise JournalCorruptionError(
                f"LEDGER_PARITY_MISMATCH: missing_in_duckdb={missing_in_duck[:5]}, "
                f"unregistered_in_duckdb={extra_in_duck[:5]}"
            )

        for rid, exp_payload in expected_by_run_id.items():
            duck_row = duck_by_run_id[rid]
            for col in _LEDGER_COLS:
                dv = duck_row[col]
                ev_val = exp_payload.get(col)
                if not _column_matches(col, dv, ev_val):
                    raise JournalCorruptionError(
                        f"LEDGER_CONTENT_TAMPERED: run_id={rid!r} column={col!r} "
                        f"duckdb={dv!r} != sqlite_chain={ev_val!r}"
                    )

        return {
            "verified": True,
            "registry_events": len(events),
            "experiments_count": len(duck_run_ids),
            "duckdb_path": str(self.duckdb_path),
            "registry_path": str(self.registry_path),
        }


__all__ = [
    "DEFAULT_DUCKDB_PATH",
    "DEFAULT_EXPERIMENTS_DIR",
    "DEFAULT_REGISTRY_PATH",
    "ExperimentLedger",
    "ExperimentRecord",
]
