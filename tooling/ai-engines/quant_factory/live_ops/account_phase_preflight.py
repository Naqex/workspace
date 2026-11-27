"""Account-Bound Preflight Guard, Eval-vs-Funded Lock, MarketWatch Parity & Multi-Account Compliance.

Mũi 3 Live-Ops Lane OPS-2 fail-closed pre-launch validator (`validate_account_deployment`).

HARD SAFETY & IMMUTABILITY INVARIANTS (`[ARCH-02]` / `G02` / `G11`):
  - Pure offline read-only validator: `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - NEVER imports `MetaTrader5`, NEVER initiates SSH/network connections, NEVER mutates presets/EAs.
  - ZERO bare `assert` statements (`[ARCH-02]`).
  - Strict 2-Layer OPSEC: zero real account logins, private IPs, or credentials.
  - Fail-closed: missing, malformed, non-finite, or mismatched parameters ALWAYS yield `REJECT`.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Literal

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0

PREFLIGHT_SCHEMA: Final[str] = "naqex-account-phase-preflight-v1"

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]

DEFAULT_SPEC_CANDIDATE_PATHS: Final[tuple[Path, ...]] = (
    AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json",
    AI_ENGINES_DIR / "configs" / "ftmo_specs_28.json",
    WORKSPACE_ROOT / "planning" / "research" / "ftmo_specs_28.json",
    WORKSPACE_ROOT / "planning" / "research" / "FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json",
)

Severity = Literal["REJECT", "RED", "AMBER", "INFO"]
Verdict = Literal["PASS", "PASS_WITH_AMBER", "PASS_WITH_RED", "REJECT"]
AlertLevel = Literal["GREEN", "AMBER", "RED", "REJECT"]
InactivityStatus = Literal["GREEN", "AMBER", "RED", "EXPIRED", "NOT_PROVIDED", "INVALID"]

# MT5 ENUM_ACCOUNT_TRADE_MODE canonical map
_TRADE_MODE_ALIASES: Final[dict[str | int, str]] = {
    0: "DEMO",
    1: "CONTEST",
    2: "REAL",
    "0": "DEMO",
    "1": "CONTEST",
    "2": "REAL",
    "DEMO": "DEMO",
    "ACCOUNT_TRADE_MODE_DEMO": "DEMO",
    "REAL": "REAL",
    "LIVE": "REAL",
    "ACCOUNT_TRADE_MODE_REAL": "REAL",
    "CONTEST": "CONTEST",
    "ACCOUNT_TRADE_MODE_CONTEST": "CONTEST",
}

# MT5 ENUM_SYMBOL_TRADE_MODE canonical map (only FULL=4 permits unrestricted open+close)
_SYMBOL_TRADE_MODE_ALIASES: Final[dict[str | int, str]] = {
    0: "DISABLED",
    1: "LONGONLY",
    2: "SHORTONLY",
    3: "CLOSEONLY",
    4: "FULL",
    "0": "DISABLED",
    "1": "LONGONLY",
    "2": "SHORTONLY",
    "3": "CLOSEONLY",
    "4": "FULL",
    "DISABLED": "DISABLED",
    "SYMBOL_TRADE_MODE_DISABLED": "DISABLED",
    "LONGONLY": "LONGONLY",
    "SYMBOL_TRADE_MODE_LONGONLY": "LONGONLY",
    "SHORTONLY": "SHORTONLY",
    "SYMBOL_TRADE_MODE_SHORTONLY": "SHORTONLY",
    "CLOSEONLY": "CLOSEONLY",
    "SYMBOL_TRADE_MODE_CLOSEONLY": "CLOSEONLY",
    "FULL": "FULL",
    "SYMBOL_TRADE_MODE_FULL": "FULL",
}

# Canonical firm asset-class leverage table (FX account base leverage + per-class effective leverage)
FIRM_LEVERAGE_PROFILES: Final[dict[str, dict[str, int]]] = {
    "FTMO_SWING": {
        "ACCOUNT": 30,
        "FX": 30,
        "INDICES": 15,
        "METALS": 9,
        "OIL": 10,
        "CRYPTO": 1,
    },
    "FTMO_STANDARD": {
        "ACCOUNT": 100,
        "FX": 100,
        "INDICES": 50,
        "METALS": 30,
        "OIL": 30,
        "CRYPTO": 3,
    },
    "THE5ERS_HS_5K": {
        "ACCOUNT": 100,
        "FX": 100,
        "INDICES": 20,
        "METALS": 33,
        "OIL": 33,
        "CRYPTO": 2,
    },
    "IC_FUNDED": {
        "ACCOUNT": 50,
        "FX": 50,
        "INDICES": 20,
        "METALS": 20,
        "OIL": 20,
        "CRYPTO": 2,
    },
}

_FIRM_PROFILE_ALIASES: Final[dict[str, str]] = {
    "FTMO_SWING": "FTMO_SWING",
    "FTMO SWING": "FTMO_SWING",
    "FTMO_SWING_10K": "FTMO_SWING",
    "FTMO_SWING_25K": "FTMO_SWING",
    "FTMO_2STEP_SWING": "FTMO_SWING",
    "FTMO_STANDARD": "FTMO_STANDARD",
    "FTMO STANDARD": "FTMO_STANDARD",
    "FTMO_STD": "FTMO_STANDARD",
    "FTMO_STANDARD_10K": "FTMO_STANDARD",
    "FTMO_STANDARD_25K": "FTMO_STANDARD",
    "FTMO_STANDARD_50K": "FTMO_STANDARD",
    "FTMO_STANDARD_100K": "FTMO_STANDARD",
    "FTMO_STANDARD_200K": "FTMO_STANDARD",
    "FTMO_2STEP_STANDARD": "FTMO_STANDARD",
    "THE5ERS_HS_5K": "THE5ERS_HS_5K",
    "THE5ERS HS 5K": "THE5ERS_HS_5K",
    "THE5ERS_HIGH_STAKES_5K": "THE5ERS_HS_5K",
    "THE5ERS_HS_5K_CLASSIC": "THE5ERS_HS_5K",
    "THE5ERS_HS_5K_NEW": "THE5ERS_HS_5K",
    "THE5ERS_HIGH_STAKES": "THE5ERS_HS_5K",
    "IC_FUNDED": "IC_FUNDED",
    "IC_FUNDED_2STEP_5K": "IC_FUNDED",
    "IC_FUNDED_2STEP_10K": "IC_FUNDED",
}

_ISO_FX_CURRENCIES: Final[frozenset[str]] = frozenset(
    {
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CHF",
        "CAD",
        "AUD",
        "NZD",
        "SGD",
        "NOK",
        "SEK",
        "PLN",
        "CZK",
        "MXN",
        "ZAR",
        "TRY",
        "HKD",
        "CNH",
    }
)

_INDEX_ROOTS: Final[frozenset[str]] = frozenset(
    {
        "US100",
        "NAS100",
        "USTEC",
        "NDX",
        "US500",
        "SPX",
        "SP500",
        "US30",
        "DJ30",
        "WS30",
        "GER40",
        "DE40",
        "DAX",
        "UK100",
        "FTSE",
        "JP225",
        "NIKKEI",
        "FRA40",
        "EU50",
        "AUS200",
        "HK50",
    }
)

_METAL_ROOTS: Final[frozenset[str]] = frozenset(
    {"XAUUSD", "XAUEUR", "XAGUSD", "XPTUSD", "XPDUSD", "GOLD", "SILVER"}
)

_OIL_ROOTS: Final[frozenset[str]] = frozenset(
    {"USOIL", "UKOIL", "WTI", "BRENT", "XTIUSD", "XBRUSD", "NATGAS"}
)

_CRYPTO_ROOTS: Final[frozenset[str]] = frozenset(
    {"BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "LTCUSD", "ADAUSD", "BNBUSD", "BCHUSD", "DOGUSD"}
)

# Canonical FTMO broker suffix map for cash CFD indices & oil
DEFAULT_FTMO_BROKER_SUFFIX_MAP: Final[dict[str, str]] = {
    "US100": "US100.cash",
    "US500": "US500.cash",
    "US30": "US30.cash",
    "GER40": "GER40.cash",
    "UK100": "UK100.cash",
    "JP225": "JP225.cash",
    "USOIL": "USOIL.cash",
    "UKOIL": "UKOIL.cash",
}

def _fx_spec(symbol: str, digits: int) -> dict[str, Any]:
    return {
        "broker_symbol": symbol,
        "digits": digits,
        "contract_size": 100000.0,
        "stops_level": 0,
        "asset_class": "FX",
    }


# Built-in 28-symbol FTMO reference contract specs (verified against FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json)
DEFAULT_FTMO_SPECS_28: Final[dict[str, dict[str, Any]]] = {
    # 17 FX pairs
    "EURUSD": _fx_spec("EURUSD", 5),
    "GBPUSD": _fx_spec("GBPUSD", 5),
    "USDJPY": _fx_spec("USDJPY", 3),
    "USDCHF": _fx_spec("USDCHF", 5),
    "USDCAD": _fx_spec("USDCAD", 5),
    "AUDUSD": _fx_spec("AUDUSD", 5),
    "NZDUSD": _fx_spec("NZDUSD", 5),
    "EURGBP": _fx_spec("EURGBP", 5),
    "EURJPY": _fx_spec("EURJPY", 3),
    "EURCHF": _fx_spec("EURCHF", 5),
    "EURAUD": _fx_spec("EURAUD", 5),
    "EURCAD": _fx_spec("EURCAD", 5),
    "GBPJPY": _fx_spec("GBPJPY", 3),
    "GBPAUD": _fx_spec("GBPAUD", 5),
    "AUDJPY": _fx_spec("AUDJPY", 3),
    "CADJPY": _fx_spec("CADJPY", 3),
    "NZDJPY": _fx_spec("NZDJPY", 3),
    # 6 Cash Indices
    "US100.cash": {
        "broker_symbol": "US100.cash",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    "US500.cash": {
        "broker_symbol": "US500.cash",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    "US30.cash": {
        "broker_symbol": "US30.cash",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    "GER40.cash": {
        "broker_symbol": "GER40.cash",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    "UK100.cash": {
        "broker_symbol": "UK100.cash",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    "JP225.cash": {
        "broker_symbol": "JP225.cash",
        "digits": 2,
        "contract_size": 10.0,
        "stops_level": 0,
        "asset_class": "INDICES",
    },
    # 2 Metals
    "XAUUSD": {
        "broker_symbol": "XAUUSD",
        "digits": 2,
        "contract_size": 100.0,
        "stops_level": 0,
        "asset_class": "METALS",
    },
    "XAGUSD": {
        "broker_symbol": "XAGUSD",
        "digits": 3,
        "contract_size": 5000.0,
        "stops_level": 0,
        "asset_class": "METALS",
    },
    # 2 Oil / Energies
    "USOIL.cash": {
        "broker_symbol": "USOIL.cash",
        "digits": 3,
        "contract_size": 100.0,
        "stops_level": 0,
        "asset_class": "OIL",
    },
    "UKOIL.cash": {
        "broker_symbol": "UKOIL.cash",
        "digits": 3,
        "contract_size": 100.0,
        "stops_level": 0,
        "asset_class": "OIL",
    },
    # 1 Crypto
    "BTCUSD": {
        "broker_symbol": "BTCUSD",
        "digits": 2,
        "contract_size": 1.0,
        "stops_level": 0,
        "asset_class": "CRYPTO",
    },
}

_EVAL_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[_\-\s])(EVAL|P1|P2|PHASE1|PHASE2|SPRINT|CHALLENGE|VERIFY|VERIFICATION)(?:$|[_\-\s])",
    re.IGNORECASE,
)
_FUNDED_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[_\-\s])(FUNDED|LIVE_FUNDED)(?:$|[_\-\s])",
    re.IGNORECASE,
)
_SUFFIX_STRIP_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\.(?:cash|raw|pro|ecn|std|m|i|c|a|b)|_(?:cash|sb|raw|pro|ecn))$",
    re.IGNORECASE,
)

INACTIVITY_AMBER_DAYS: Final[int] = 21
INACTIVITY_RED_DAYS: Final[int] = 27
INACTIVITY_HARD_LIMIT_DAYS: Final[int] = 30
DEFAULT_FUNDED_MAX_RISK_MULT: Final[float] = 1.25
DEFAULT_FUNDED_MAX_AMBER_DD_PCT: Final[float] = 4.0
DEFAULT_FUNDED_MAX_RED_DD_PCT: Final[float] = 6.5
DEFAULT_BEST_DAY_WARN_RATIO: Final[float] = 0.45


@dataclass(frozen=True, slots=True)
class PreflightFinding:
    code: str
    severity: Severity
    check_area: str
    message: str
    expected: Any = None
    actual: Any = None
    subject: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreflightReport:
    schema: str
    passed: bool
    can_launch: bool
    verdict: Verdict
    alert_level: AlertLevel
    firm_profile: str
    account_phase: str
    inactivity_status: InactivityStatus
    best_day_share: float | None
    findings: tuple[PreflightFinding, ...]
    reject_codes: tuple[str, ...]
    red_codes: tuple[str, ...]
    amber_codes: tuple[str, ...]
    checked_symbols: tuple[str, ...]
    order_send_capable: bool = ORDER_SEND_CAPABLE
    order_send_count: int = ORDER_SEND_COUNT

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "passed": self.passed,
            "can_launch": self.can_launch,
            "verdict": self.verdict,
            "alert_level": self.alert_level,
            "firm_profile": self.firm_profile,
            "account_phase": self.account_phase,
            "inactivity_status": self.inactivity_status,
            "best_day_share": self.best_day_share,
            "findings": [f.to_dict() for f in self.findings],
            "reject_codes": list(self.reject_codes),
            "red_codes": list(self.red_codes),
            "amber_codes": list(self.amber_codes),
            "checked_symbols": list(self.checked_symbols),
            "order_send_capable": self.order_send_capable,
            "order_send_count": self.order_send_count,
        }


def _is_strict_int(value: Any) -> bool:
    return type(value) is int


def _to_finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    if not math.isfinite(out):
        return None
    return out


def _parse_bool_strict(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low == "true":
            return True
        if low == "false":
            return False
    return None


def _parse_mql_scalar(raw: str) -> Any:
    # MT5 Strategy Tester .set files can contain `value||start||step||stop||opt`
    val = raw.split("||", 1)[0].strip()
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        if "." in val or "e" in low:
            parsed = float(val)
            return parsed if math.isfinite(parsed) else val
        return int(val)
    except ValueError:
        return val


def parse_mt5_set_file(path: Path | str) -> dict[str, Any]:
    """Parse an MT5 `.set` preset file (UTF-8 / UTF-8-BOM / UTF-16LE) into a typed dictionary."""
    p = Path(path)
    raw = p.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="replace")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig", errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace")
    out: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        out[key.strip()] = _parse_mql_scalar(val)
    return out


def normalize_trade_mode(mode: str | int | None) -> str | None:
    if mode is None or isinstance(mode, bool):
        return None
    if isinstance(mode, int):
        return _TRADE_MODE_ALIASES.get(mode)
    if isinstance(mode, str):
        return _TRADE_MODE_ALIASES.get(mode.strip().upper())
    return None


def normalize_symbol_trade_mode(mode: str | int | None) -> str | None:
    if mode is None or isinstance(mode, bool):
        return None
    if isinstance(mode, int):
        return _SYMBOL_TRADE_MODE_ALIASES.get(mode)
    if isinstance(mode, str):
        return _SYMBOL_TRADE_MODE_ALIASES.get(mode.strip().upper())
    return None


def normalize_firm_profile(firm_profile: str | None) -> str | None:
    if not isinstance(firm_profile, str) or not firm_profile.strip():
        return None
    key = re.sub(r"[\s\-]+", "_", firm_profile.strip().upper())
    if key in FIRM_LEVERAGE_PROFILES:
        return key
    if key in _FIRM_PROFILE_ALIASES:
        return _FIRM_PROFILE_ALIASES[key]
    space_key = re.sub(r"\s+", " ", firm_profile.strip().upper())
    return _FIRM_PROFILE_ALIASES.get(space_key)


def normalize_account_phase(phase: str | None) -> str | None:
    if not isinstance(phase, str) or not phase.strip():
        return None
    up = re.sub(r"[\s\-]+", "_", phase.strip().upper())
    if up in ("EVAL", "P1", "P2", "PHASE1", "PHASE2", "CHALLENGE", "VERIFICATION", "VERIFY", "SPRINT"):
        return "EVAL"
    if up in ("FUNDED", "LIVE_FUNDED", "FTMO_ACCOUNT", "FUNDED_LIVE"):
        return "FUNDED"
    return None


def canonical_symbol_root(symbol: str) -> str:
    """Strip common broker suffixes (`.cash`, `.raw`, `.m`, etc.) and uppercase."""
    cleaned = _SUFFIX_STRIP_RE.sub("", symbol.strip())
    return cleaned.upper()


def classify_symbol_asset_class(symbol: str) -> str:
    root = canonical_symbol_root(symbol)
    if root in _INDEX_ROOTS:
        return "INDICES"
    if root in _METAL_ROOTS:
        return "METALS"
    if root in _OIL_ROOTS:
        return "OIL"
    if root in _CRYPTO_ROOTS:
        return "CRYPTO"
    if len(root) == 6 and root[:3] in _ISO_FX_CURRENCIES and root[3:] in _ISO_FX_CURRENCIES and root[:3] != root[3:]:
        return "FX"
    return "UNKNOWN"


def _normalize_single_spec(sym: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    cs = raw.get("contract_size")
    if cs is None:
        cs = raw.get("trade_contract_size")
    stops = raw.get("stops_level")
    if stops is None:
        stops = raw.get("trade_stops_level", 0)
    broker_sym = str(raw.get("broker_symbol") or raw.get("symbol") or sym)
    asset_class = str(raw.get("asset_class") or classify_symbol_asset_class(broker_sym)).upper()
    return {
        "broker_symbol": broker_sym,
        "digits": raw.get("digits"),
        "contract_size": cs,
        "stops_level": stops,
        "point": raw.get("point"),
        "asset_class": asset_class,
    }


def load_symbol_specs(specs_path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Load symbol contract specs from `ftmo_specs_28.json` / FTMO snapshot or built-in 28-symbol baseline."""
    chosen_path: Path | None = None
    if specs_path is not None:
        chosen_path = Path(specs_path)
        if not chosen_path.is_file():
            raise FileNotFoundError(f"Expected symbol specs file not found: {chosen_path}")
    else:
        for candidate in DEFAULT_SPEC_CANDIDATE_PATHS:
            if candidate.is_file():
                chosen_path = candidate
                break

    merged: dict[str, dict[str, Any]] = {k: dict(v) for k, v in DEFAULT_FTMO_SPECS_28.items()}
    if chosen_path is None:
        return merged

    raw_doc = json.loads(chosen_path.read_text(encoding="utf-8"))
    if not isinstance(raw_doc, dict):
        raise ValueError(f"Malformed specs JSON (expected object): {chosen_path}")

    # Support FTMO live snapshot schema (`fx_metals_indices_specs` + `core_live`)
    if "fx_metals_indices_specs" in raw_doc or "core_live" in raw_doc:
        for section in ("fx_metals_indices_specs", "core_live"):
            sec_data = raw_doc.get(section)
            if isinstance(sec_data, Mapping):
                for sym, entry in sec_data.items():
                    if isinstance(entry, Mapping):
                        norm = _normalize_single_spec(str(sym), entry)
                        existing = dict(merged.get(str(sym), {}))
                        existing.update({k: v for k, v in norm.items() if v is not None})
                        merged[str(sym)] = existing
        return merged

    # Support `{"symbols": {...}}` or flat `{sym: {...}}` (`ftmo_specs_28.json`)
    sym_table = raw_doc.get("symbols") if isinstance(raw_doc.get("symbols"), Mapping) else raw_doc
    if isinstance(sym_table, Mapping):
        for sym, entry in sym_table.items():
            if isinstance(entry, Mapping):
                merged[str(sym)] = _normalize_single_spec(str(sym), entry)
    return merged


def _resolve_spec_for_symbol(
    symbol: str,
    expected_specs: Mapping[str, Mapping[str, Any]],
    broker_suffix_map: Mapping[str, str],
) -> tuple[str | None, dict[str, Any] | None]:
    """Return `(expected_broker_symbol, spec)` for a requested/canonical/broker symbol."""
    if symbol in expected_specs:
        spec = _normalize_single_spec(symbol, expected_specs[symbol])
        return spec["broker_symbol"], spec

    root = canonical_symbol_root(symbol)
    mapped_broker = broker_suffix_map.get(root) or broker_suffix_map.get(symbol)
    if mapped_broker and mapped_broker in expected_specs:
        spec = _normalize_single_spec(mapped_broker, expected_specs[mapped_broker])
        return mapped_broker, spec

    # Fallback lookup by canonical root across expected_specs keys
    for spec_sym, raw in expected_specs.items():
        if canonical_symbol_root(spec_sym) == root:
            spec = _normalize_single_spec(spec_sym, raw)
            return spec["broker_symbol"], spec

    return None, None


def check_account_binding(
    *,
    expected_login: int,
    actual_login: int | None,
    expected_trade_mode: str | int,
    actual_trade_mode: str | int | None,
    expected_server: str | None = None,
    actual_server: str | None = None,
    trade_allowed: bool | None = None,
    trade_expert: bool | None = None,
) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []

    if not _is_strict_int(expected_login) or expected_login <= 0:
        findings.append(
            PreflightFinding(
                code="INVALID_EXPECTED_LOGIN",
                severity="REJECT",
                check_area="account_binding",
                message="expected_login must be a positive integer.",
                expected="positive int",
                actual=expected_login,
            )
        )
    if not _is_strict_int(actual_login) or (actual_login is not None and actual_login <= 0):
        findings.append(
            PreflightFinding(
                code="INVALID_ACTUAL_LOGIN",
                severity="REJECT",
                check_area="account_binding",
                message="actual_login is missing or not a positive integer (fail-closed).",
                expected=expected_login,
                actual=actual_login,
            )
        )
    elif _is_strict_int(expected_login) and expected_login > 0 and actual_login != expected_login:
        findings.append(
            PreflightFinding(
                code="ACCOUNT_LOGIN_MISMATCH",
                severity="REJECT",
                check_area="account_binding",
                message=f"Connected account login {actual_login} does not match expected login {expected_login}.",
                expected=expected_login,
                actual=actual_login,
            )
        )

    norm_exp_mode = normalize_trade_mode(expected_trade_mode)
    norm_act_mode = normalize_trade_mode(actual_trade_mode)
    if norm_exp_mode not in ("DEMO", "REAL"):
        findings.append(
            PreflightFinding(
                code="INVALID_EXPECTED_TRADE_MODE",
                severity="REJECT",
                check_area="account_binding",
                message="expected_trade_mode must be DEMO or REAL.",
                expected="DEMO | REAL",
                actual=expected_trade_mode,
            )
        )
    if norm_act_mode not in ("DEMO", "REAL"):
        findings.append(
            PreflightFinding(
                code="INVALID_ACTUAL_TRADE_MODE",
                severity="REJECT",
                check_area="account_binding",
                message=f"Observed account trade mode '{actual_trade_mode}' is unsupported or missing (fail-closed).",
                expected=norm_exp_mode,
                actual=actual_trade_mode,
            )
        )
    elif norm_exp_mode in ("DEMO", "REAL") and norm_act_mode != norm_exp_mode:
        findings.append(
            PreflightFinding(
                code="ACCOUNT_TRADE_MODE_MISMATCH",
                severity="REJECT",
                check_area="account_binding",
                message=f"Account trade mode mismatch: expected {norm_exp_mode}, got {norm_act_mode}.",
                expected=norm_exp_mode,
                actual=norm_act_mode,
            )
        )

    if expected_server is not None:
        exp_srv = str(expected_server).strip()
        act_srv = "" if actual_server is None else str(actual_server).strip()
        if not exp_srv or not act_srv or act_srv.lower() != exp_srv.lower():
            findings.append(
                PreflightFinding(
                    code="ACCOUNT_SERVER_MISMATCH",
                    severity="REJECT",
                    check_area="account_binding",
                    message=f"Broker server mismatch: expected '{exp_srv}', got '{act_srv or '<missing>'}'.",
                    expected=exp_srv,
                    actual=act_srv or None,
                )
            )

    if trade_allowed is False:
        findings.append(
            PreflightFinding(
                code="ACCOUNT_TRADING_DISABLED",
                severity="REJECT",
                check_area="account_binding",
                message="ACCOUNT_TRADE_ALLOWED is False on target account.",
                expected=True,
                actual=False,
            )
        )
    if trade_expert is False:
        findings.append(
            PreflightFinding(
                code="ACCOUNT_EXPERT_TRADING_DISABLED",
                severity="REJECT",
                check_area="account_binding",
                message="ACCOUNT_TRADE_EXPERT (Algo Trading) is False on target account.",
                expected=True,
                actual=False,
            )
        )

    return findings


def _extract_preset_param(preset: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in preset and preset[key] is not None:
            return preset[key]
    return None


def infer_preset_phase(
    preset: Mapping[str, Any],
    *,
    explicit_preset_phase: str | None = None,
    preset_name: str | None = None,
) -> str | None:
    if explicit_preset_phase is not None:
        return normalize_account_phase(explicit_preset_phase)
    raw_phase = _extract_preset_param(preset, "phase", "preset_phase", "account_phase")
    if isinstance(raw_phase, str):
        norm = normalize_account_phase(raw_phase)
        if norm is not None:
            return norm

    sku = str(_extract_preset_param(preset, "InpContractSku", "contract_sku", "sku") or "")
    label = f"{sku} {preset_name or ''}".strip()
    if label:
        if _EVAL_TOKEN_RE.search(label):
            return "EVAL"
        if _FUNDED_TOKEN_RE.search(label):
            return "FUNDED"

    target = _to_finite_float(_extract_preset_param(preset, "InpTargetProfitPct", "target_profit_pct"))
    if target is not None:
        return "EVAL" if target > 0.0 else "FUNDED"
    return None


def _is_sprint_preset(preset: Mapping[str, Any], *, preset_name: str | None = None) -> bool:
    sku = str(_extract_preset_param(preset, "InpContractSku", "contract_sku", "sku") or "")
    label = f"{sku} {preset_name or ''}".upper()
    if "SPRINT" in label:
        return True
    mult = _to_finite_float(_extract_preset_param(preset, "risk_mult", "InpBasePhaseMult", "base_phase_mult"))
    return mult is not None and mult >= 2.0


def check_eval_vs_funded_lock(
    *,
    account_phase: str,
    preset: Mapping[str, Any],
    explicit_preset_phase: str | None = None,
    preset_name: str | None = None,
    max_funded_risk_mult: float = DEFAULT_FUNDED_MAX_RISK_MULT,
    strict_funded_1x: bool = False,
    max_funded_amber_dd_pct: float = DEFAULT_FUNDED_MAX_AMBER_DD_PCT,
    max_funded_red_dd_pct: float = DEFAULT_FUNDED_MAX_RED_DD_PCT,
) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    norm_acct_phase = normalize_account_phase(account_phase)
    if norm_acct_phase is None:
        findings.append(
            PreflightFinding(
                code="UNKNOWN_ACCOUNT_PHASE",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=f"Unsupported account_phase '{account_phase}' (must be EVAL/P1/P2 or FUNDED).",
                expected="EVAL | FUNDED",
                actual=account_phase,
            )
        )
        return findings

    risk_mult = _to_finite_float(_extract_preset_param(preset, "risk_mult", "InpBasePhaseMult", "base_phase_mult"))
    if risk_mult is None or risk_mult <= 0.0:
        findings.append(
            PreflightFinding(
                code="INVALID_RISK_MULT",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message="Preset risk_mult / InpBasePhaseMult is missing, non-finite, or <= 0 (fail-closed).",
                expected="> 0.0",
                actual=_extract_preset_param(preset, "risk_mult", "InpBasePhaseMult", "base_phase_mult"),
            )
        )

    amber_dd_pct = _to_finite_float(_extract_preset_param(preset, "amber_dd_pct", "InpAmberDdPct"))
    if amber_dd_pct is None or amber_dd_pct <= 0.0:
        findings.append(
            PreflightFinding(
                code="INVALID_AMBER_DD_PCT",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message="Preset amber_dd_pct / InpAmberDdPct is missing, non-finite, or <= 0 (fail-closed).",
                expected="> 0.0",
                actual=_extract_preset_param(preset, "amber_dd_pct", "InpAmberDdPct"),
            )
        )

    raw_red = _extract_preset_param(preset, "red_dd_pct", "InpRedDdPct")
    red_dd_pct = _to_finite_float(raw_red) if raw_red is not None else None
    if raw_red is not None and (red_dd_pct is None or red_dd_pct <= 0.0):
        findings.append(
            PreflightFinding(
                code="INVALID_RED_DD_PCT",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message="Preset red_dd_pct / InpRedDdPct is non-finite or <= 0.",
                expected="> 0.0",
                actual=raw_red,
            )
        )
    elif amber_dd_pct is not None and red_dd_pct is not None and red_dd_pct <= amber_dd_pct:
        findings.append(
            PreflightFinding(
                code="INVALID_BRAKE_ORDERING",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=f"red_dd_pct ({red_dd_pct}%) must be strictly greater than amber_dd_pct ({amber_dd_pct}%).",
                expected=f"> {amber_dd_pct}",
                actual=red_dd_pct,
            )
        )

    inferred_phase = infer_preset_phase(preset, explicit_preset_phase=explicit_preset_phase, preset_name=preset_name)
    raw_explicit_phase = (
        explicit_preset_phase
        if explicit_preset_phase is not None
        else _extract_preset_param(preset, "phase", "preset_phase")
    )
    if raw_explicit_phase is not None and normalize_account_phase(str(raw_explicit_phase)) is None:
        findings.append(
            PreflightFinding(
                code="UNKNOWN_PRESET_PHASE",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=f"Unrecognized preset phase '{raw_explicit_phase}' (fail-closed).",
                expected="EVAL | FUNDED",
                actual=raw_explicit_phase,
            )
        )

    if not isinstance(strict_funded_1x, bool):
        findings.append(
            PreflightFinding(
                code="INVALID_STRICT_FUNDED_FLAG",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message="strict_funded_1x must be a boolean (fail-closed).",
                expected="bool",
                actual=strict_funded_1x,
            )
        )

    cap_mult = _to_finite_float(max_funded_risk_mult)
    if cap_mult is None or cap_mult <= 0.0 or cap_mult > DEFAULT_FUNDED_MAX_RISK_MULT + 1e-9:
        findings.append(
            PreflightFinding(
                code="INVALID_FUNDED_RISK_MULT_CAP",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=(
                    f"max_funded_risk_mult must be finite in (0, {DEFAULT_FUNDED_MAX_RISK_MULT:.2f}] "
                    f"(fail-closed), got {max_funded_risk_mult!r}."
                ),
                expected=f"(0.0, {DEFAULT_FUNDED_MAX_RISK_MULT:.2f}]",
                actual=max_funded_risk_mult,
            )
        )
        effective_max_mult = 1.0 if strict_funded_1x is True else DEFAULT_FUNDED_MAX_RISK_MULT
    else:
        effective_max_mult = 1.0 if strict_funded_1x is True else min(cap_mult, DEFAULT_FUNDED_MAX_RISK_MULT)

    cap_amber = _to_finite_float(max_funded_amber_dd_pct)
    if cap_amber is None or cap_amber <= 0.0 or cap_amber > DEFAULT_FUNDED_MAX_AMBER_DD_PCT + 1e-9:
        findings.append(
            PreflightFinding(
                code="INVALID_FUNDED_AMBER_DD_CAP",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=(
                    f"max_funded_amber_dd_pct must be finite in (0, {DEFAULT_FUNDED_MAX_AMBER_DD_PCT:.2f}] "
                    f"(fail-closed), got {max_funded_amber_dd_pct!r}."
                ),
                expected=f"(0.0, {DEFAULT_FUNDED_MAX_AMBER_DD_PCT:.2f}]",
                actual=max_funded_amber_dd_pct,
            )
        )
        effective_max_amber = DEFAULT_FUNDED_MAX_AMBER_DD_PCT
    else:
        effective_max_amber = cap_amber

    cap_red = _to_finite_float(max_funded_red_dd_pct)
    if cap_red is None or cap_red <= 0.0 or cap_red > DEFAULT_FUNDED_MAX_RED_DD_PCT + 1e-9:
        findings.append(
            PreflightFinding(
                code="INVALID_FUNDED_RED_DD_CAP",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=(
                    f"max_funded_red_dd_pct must be finite in (0, {DEFAULT_FUNDED_MAX_RED_DD_PCT:.2f}] "
                    f"(fail-closed), got {max_funded_red_dd_pct!r}."
                ),
                expected=f"(0.0, {DEFAULT_FUNDED_MAX_RED_DD_PCT:.2f}]",
                actual=max_funded_red_dd_pct,
            )
        )
        effective_max_red = DEFAULT_FUNDED_MAX_RED_DD_PCT
    else:
        effective_max_red = cap_red

    if (
        cap_amber is not None
        and cap_red is not None
        and cap_amber > 0.0
        and cap_red > 0.0
        and cap_red <= cap_amber
    ):
        findings.append(
            PreflightFinding(
                code="INVALID_FUNDED_DD_CAP_ORDERING",
                severity="REJECT",
                check_area="eval_vs_funded_lock",
                message=(
                    f"max_funded_red_dd_pct ({cap_red:.2f}%) must be strictly greater than "
                    f"max_funded_amber_dd_pct ({cap_amber:.2f}%)."
                ),
                expected=f"> {cap_amber:.2f}",
                actual=cap_red,
            )
        )

    if norm_acct_phase == "FUNDED":
        if inferred_phase == "EVAL":
            findings.append(
                PreflightFinding(
                    code="EVAL_PRESET_ON_FUNDED_ACCOUNT",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message="HARD REJECT: Eval/Sprint preset cannot be attached to a FUNDED account.",
                    expected="FUNDED",
                    actual="EVAL",
                )
            )
        elif inferred_phase is None:
            findings.append(
                PreflightFinding(
                    code="UNDETERMINED_PRESET_PHASE_ON_FUNDED",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message="Preset phase could not be verified as FUNDED (fail-closed on FUNDED account).",
                    expected="FUNDED",
                    actual=None,
                )
            )

        if risk_mult is not None and risk_mult > effective_max_mult + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_RISK_MULT_EXCEEDED",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"HARD REJECT: risk_mult={risk_mult:.2f}x exceeds FUNDED ceiling "
                        f"{effective_max_mult:.2f}x (1.0x Safe / 1.25x max)."
                    ),
                    expected=f"<= {effective_max_mult:.2f}",
                    actual=risk_mult,
                )
            )
        elif risk_mult is not None and risk_mult > 1.0 + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_ELEVATED_MULT_ABOVE_1X",
                    severity="INFO",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"FUNDED risk_mult={risk_mult:.2f}x is within the 1.25x ceiling "
                        "but above the conservative 1.00x Safe baseline."
                    ),
                    expected=1.0,
                    actual=risk_mult,
                )
            )

        pl_mult = _to_finite_float(_extract_preset_param(preset, "InpProfitLockMult", "profit_lock_mult"))
        if pl_mult is not None and pl_mult > effective_max_mult + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_PROFIT_LOCK_MULT_EXCEEDED",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"HARD REJECT: profit_lock_mult={pl_mult:.2f}x exceeds FUNDED ceiling "
                        f"{effective_max_mult:.2f}x."
                    ),
                    expected=f"<= {effective_max_mult:.2f}",
                    actual=pl_mult,
                )
            )

        if amber_dd_pct is not None and amber_dd_pct > effective_max_amber + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_AMBER_DD_TOO_LOOSE",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"HARD REJECT: amber_dd_pct={amber_dd_pct:.2f}% exceeds FUNDED ceiling "
                        f"{effective_max_amber:.2f}%."
                    ),
                    expected=f"<= {effective_max_amber:.2f}",
                    actual=amber_dd_pct,
                )
            )

        if red_dd_pct is not None and red_dd_pct > effective_max_red + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_RED_DD_TOO_LOOSE",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"HARD REJECT: red_dd_pct={red_dd_pct:.2f}% exceeds FUNDED tight Red ceiling "
                        f"{effective_max_red:.2f}%."
                    ),
                    expected=f"<= {effective_max_red:.2f}",
                    actual=red_dd_pct,
                )
            )

        target_pct = _to_finite_float(_extract_preset_param(preset, "InpTargetProfitPct", "target_profit_pct"))
        if target_pct is not None and target_pct > 0.0:
            findings.append(
                PreflightFinding(
                    code="EVAL_TARGET_ON_FUNDED_ACCOUNT",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=(
                        f"HARD REJECT: InpTargetProfitPct={target_pct:.2f}% (> 0) indicates an Eval preset "
                        "attached to a FUNDED account."
                    ),
                    expected=0.0,
                    actual=target_pct,
                )
            )

        kill_daily = _to_finite_float(_extract_preset_param(preset, "InpKillDailyDdPct", "kill_daily_dd_pct"))
        if kill_daily is not None and kill_daily > 3.5 + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_KILL_DAILY_DD_TOO_LOOSE",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=f"HARD REJECT: kill_daily_dd_pct={kill_daily:.2f}% exceeds FUNDED safe ceiling 3.50%.",
                    expected="<= 3.50",
                    actual=kill_daily,
                )
            )

        kill_static = _to_finite_float(_extract_preset_param(preset, "InpKillStaticDdPct", "kill_static_dd_pct"))
        if kill_static is not None and kill_static > 8.0 + 1e-9:
            findings.append(
                PreflightFinding(
                    code="FUNDED_KILL_STATIC_DD_TOO_LOOSE",
                    severity="REJECT",
                    check_area="eval_vs_funded_lock",
                    message=f"HARD REJECT: kill_static_dd_pct={kill_static:.2f}% exceeds FUNDED safe ceiling 8.00%.",
                    expected="<= 8.00",
                    actual=kill_static,
                )
            )

    return findings


def check_asset_class_leverage(
    *,
    firm_profile: str,
    account_leverage: int | float | None,
    asset_class_leverages: Mapping[str, int | float] | None = None,
    expected_leverage_by_class: Mapping[str, int | float] | None = None,
    leverage_rel_tol: float = 0.02,
) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    parsed_tol = _to_finite_float(leverage_rel_tol)
    if parsed_tol is None or parsed_tol < 0.0 or parsed_tol > 1.0:
        findings.append(
            PreflightFinding(
                code="INVALID_LEVERAGE_REL_TOL",
                severity="REJECT",
                check_area="leverage",
                message=f"leverage_rel_tol must be finite in [0.0, 1.0] (fail-closed), got {leverage_rel_tol!r}.",
                expected="[0.0, 1.0]",
                actual=leverage_rel_tol,
            )
        )
        eff_lev_tol = 0.02
    else:
        eff_lev_tol = parsed_tol

    norm_firm = normalize_firm_profile(firm_profile)
    if norm_firm is None:
        findings.append(
            PreflightFinding(
                code="UNKNOWN_FIRM_PROFILE",
                severity="REJECT",
                check_area="leverage",
                message=f"Unknown firm_profile '{firm_profile}' (cannot verify leverage fail-closed).",
                expected=sorted(FIRM_LEVERAGE_PROFILES.keys()),
                actual=firm_profile,
            )
        )
        return findings

    expected_map: dict[str, float] = {k: float(v) for k, v in FIRM_LEVERAGE_PROFILES[norm_firm].items()}
    if expected_leverage_by_class is not None:
        for k, v in expected_leverage_by_class.items():
            fv = _to_finite_float(v)
            if fv is None or fv <= 0.0:
                findings.append(
                    PreflightFinding(
                        code="INVALID_EXPECTED_LEVERAGE_OVERRIDE",
                        severity="REJECT",
                        check_area="leverage",
                        message=f"Invalid expected leverage override for class '{k}': {v}.",
                        expected="> 0",
                        actual=v,
                        subject=str(k).upper(),
                    )
                )
                return findings
            expected_map[str(k).strip().upper()] = fv

    exp_acct_lev = expected_map.get("ACCOUNT", expected_map["FX"])
    act_acct_lev = _to_finite_float(account_leverage)
    if act_acct_lev is None or act_acct_lev <= 0.0:
        findings.append(
            PreflightFinding(
                code="MISSING_ACCOUNT_LEVERAGE",
                severity="REJECT",
                check_area="leverage",
                message="Account leverage (ACCOUNT_LEVERAGE) is missing or <= 0 (fail-closed).",
                expected=exp_acct_lev,
                actual=account_leverage,
            )
        )
    elif abs(act_acct_lev - exp_acct_lev) / max(1.0, exp_acct_lev) > eff_lev_tol:
        findings.append(
            PreflightFinding(
                code="ACCOUNT_LEVERAGE_MISMATCH",
                severity="REJECT",
                check_area="leverage",
                message=(
                    f"{norm_firm} expects account leverage 1:{exp_acct_lev:g}, "
                    f"but observed 1:{act_acct_lev:g} (possible Swing vs Standard mismatch)."
                ),
                expected=exp_acct_lev,
                actual=act_acct_lev,
                subject="ACCOUNT",
            )
        )

    if asset_class_leverages is not None:
        for raw_cls, raw_obs in asset_class_leverages.items():
            cls_key = str(raw_cls).strip().upper()
            if cls_key not in expected_map:
                findings.append(
                    PreflightFinding(
                        code="UNKNOWN_ASSET_CLASS_LEVERAGE",
                        severity="REJECT",
                        check_area="leverage",
                        message=f"Unknown asset class '{raw_cls}' in asset_class_leverages.",
                        expected=sorted(k for k in expected_map if k != "ACCOUNT"),
                        actual=raw_cls,
                        subject=cls_key,
                    )
                )
                continue
            obs_val = _to_finite_float(raw_obs)
            exp_val = expected_map[cls_key]
            if obs_val is None or obs_val <= 0.0:
                findings.append(
                    PreflightFinding(
                        code="INVALID_ASSET_CLASS_LEVERAGE",
                        severity="REJECT",
                        check_area="leverage",
                        message=f"Asset class '{cls_key}' leverage is invalid/non-positive: {raw_obs}.",
                        expected=exp_val,
                        actual=raw_obs,
                        subject=cls_key,
                    )
                )
            elif abs(obs_val - exp_val) / max(1.0, exp_val) > eff_lev_tol:
                findings.append(
                    PreflightFinding(
                        code="ASSET_CLASS_LEVERAGE_MISMATCH",
                        severity="REJECT",
                        check_area="leverage",
                        message=(
                            f"{norm_firm} {cls_key} expects leverage 1:{exp_val:g}, "
                            f"but observed 1:{obs_val:g}."
                        ),
                        expected=exp_val,
                        actual=obs_val,
                        subject=cls_key,
                    )
                )

    return findings


def _normalize_marketwatch_snapshots(
    market_watch_symbols: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(market_watch_symbols, Mapping):
        for sym, payload in market_watch_symbols.items():
            entry = dict(payload) if isinstance(payload, Mapping) else {}
            entry.setdefault("symbol", str(sym))
            out[str(sym)] = entry
    else:
        for item in market_watch_symbols:
            if not isinstance(item, Mapping):
                continue
            sym = str(item.get("symbol") or item.get("name") or "").strip()
            if sym:
                entry = dict(item)
                entry["symbol"] = sym
                out[sym] = entry
    return out


def check_marketwatch_contract_parity(
    *,
    market_watch_symbols: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None,
    required_symbols: Sequence[str] | None = None,
    expected_specs: Mapping[str, Mapping[str, Any]] | None = None,
    specs_path: Path | str | None = None,
    broker_suffix_map: Mapping[str, str] | None = None,
    preset: Mapping[str, Any] | None = None,
    firm_profile: str | None = None,
    max_allowed_stops_level: int | None = None,
    contract_size_rel_tol: float = 1e-6,
    leverage_rel_tol: float = 0.02,
    require_market_watch: bool = True,
) -> tuple[list[PreflightFinding], list[str]]:
    findings: list[PreflightFinding] = []
    checked: list[str] = []

    parsed_cs_tol = _to_finite_float(contract_size_rel_tol)
    if parsed_cs_tol is None or parsed_cs_tol < 0.0 or parsed_cs_tol > 1.0:
        findings.append(
            PreflightFinding(
                code="INVALID_CONTRACT_SIZE_REL_TOL",
                severity="REJECT",
                check_area="marketwatch_parity",
                message=(
                    f"contract_size_rel_tol must be finite in [0.0, 1.0] (fail-closed), "
                    f"got {contract_size_rel_tol!r}."
                ),
                expected="[0.0, 1.0]",
                actual=contract_size_rel_tol,
            )
        )
        eff_cs_tol = 1e-6
    else:
        eff_cs_tol = parsed_cs_tol

    parsed_mw_lev_tol = _to_finite_float(leverage_rel_tol)
    if parsed_mw_lev_tol is None or parsed_mw_lev_tol < 0.0 or parsed_mw_lev_tol > 1.0:
        findings.append(
            PreflightFinding(
                code="INVALID_LEVERAGE_REL_TOL",
                severity="REJECT",
                check_area="marketwatch_parity",
                message=f"leverage_rel_tol must be finite in [0.0, 1.0] (fail-closed), got {leverage_rel_tol!r}.",
                expected="[0.0, 1.0]",
                actual=leverage_rel_tol,
            )
        )
        eff_mw_lev_tol = 0.02
    else:
        eff_mw_lev_tol = parsed_mw_lev_tol

    eff_max_stops: int | None = max_allowed_stops_level
    if max_allowed_stops_level is not None and (
        not _is_strict_int(max_allowed_stops_level) or max_allowed_stops_level < 0
    ):
        findings.append(
            PreflightFinding(
                code="INVALID_MAX_ALLOWED_STOPS_LEVEL",
                severity="REJECT",
                check_area="marketwatch_parity",
                message=(
                    f"max_allowed_stops_level must be a non-negative strict int (fail-closed), "
                    f"got {max_allowed_stops_level!r}."
                ),
                expected="int >= 0",
                actual=max_allowed_stops_level,
            )
        )
        eff_max_stops = 0

    if market_watch_symbols is None:
        if require_market_watch or required_symbols:
            findings.append(
                PreflightFinding(
                    code="MISSING_MARKETWATCH_SNAPSHOT",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message="MarketWatch symbol snapshot is missing (fail-closed).",
                    expected="non-empty symbol snapshot",
                    actual=None,
                )
            )
        return findings, checked

    mw_map = _normalize_marketwatch_snapshots(market_watch_symbols)
    if not mw_map:
        findings.append(
            PreflightFinding(
                code="EMPTY_MARKETWATCH_SNAPSHOT",
                severity="REJECT",
                check_area="marketwatch_parity",
                message="MarketWatch symbol snapshot is empty (fail-closed).",
                expected=">= 1 symbol",
                actual=0,
            )
        )
        return findings, checked

    specs = (
        {str(k): _normalize_single_spec(str(k), v) for k, v in expected_specs.items()}
        if expected_specs is not None
        else load_symbol_specs(specs_path)
    )
    suffix_map = dict(DEFAULT_FTMO_BROKER_SUFFIX_MAP)
    if broker_suffix_map is not None:
        suffix_map.update({str(k).upper(): str(v) for k, v in broker_suffix_map.items()})

    # Validate preset InpSym* broker suffix mappings when provided
    if preset is not None:
        for pkey, pval in preset.items():
            if not (isinstance(pkey, str) and pkey.startswith("InpSym") and isinstance(pval, str) and pval.strip()):
                continue
            declared_sym = pval.strip()
            root = canonical_symbol_root(declared_sym)
            expected_broker = suffix_map.get(root)
            if expected_broker is not None and declared_sym != expected_broker:
                findings.append(
                    PreflightFinding(
                        code="SYMBOL_SUFFIX_MISMATCH",
                        severity="REJECT",
                        check_area="marketwatch_parity",
                        message=(
                            f"Preset {pkey}='{declared_sym}' does not match expected broker symbol '{expected_broker}'."
                        ),
                        expected=expected_broker,
                        actual=declared_sym,
                        subject=pkey,
                    )
                )

    mw_by_root: dict[str, tuple[str, dict[str, Any]]] = {
        canonical_symbol_root(k): (k, v) for k, v in mw_map.items()
    }
    norm_firm = normalize_firm_profile(firm_profile) if firm_profile else None
    firm_lev_table = FIRM_LEVERAGE_PROFILES.get(norm_firm) if norm_firm else None

    targets = list(required_symbols) if required_symbols is not None else list(mw_map.keys())
    if not targets:
        findings.append(
            PreflightFinding(
                code="EMPTY_REQUIRED_SYMBOLS",
                severity="REJECT",
                check_area="marketwatch_parity",
                message="required_symbols cannot be an empty sequence (fail-closed).",
                expected=">= 1 symbol",
                actual=0,
            )
        )
        return findings, checked

    for req_sym in targets:
        expected_broker_sym, spec = _resolve_spec_for_symbol(req_sym, specs, suffix_map)
        if spec is None or expected_broker_sym is None:
            findings.append(
                PreflightFinding(
                    code="UNKNOWN_SYMBOL_SPEC",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=f"No expected contract specification found for symbol '{req_sym}' (fail-closed).",
                    expected="symbol present in expected_specs",
                    actual=req_sym,
                    subject=req_sym,
                )
            )
            continue

        snap_key: str | None = None
        snap: dict[str, Any] | None = None
        if expected_broker_sym in mw_map:
            snap_key = expected_broker_sym
            snap = mw_map[expected_broker_sym]
        elif req_sym in mw_map:
            snap_key = req_sym
            snap = mw_map[req_sym]
        else:
            root_hit = mw_by_root.get(canonical_symbol_root(expected_broker_sym))
            if root_hit is not None:
                snap_key, snap = root_hit

        if snap is None or snap_key is None:
            findings.append(
                PreflightFinding(
                    code="SYMBOL_MISSING_FROM_MARKETWATCH",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=f"Required symbol '{expected_broker_sym}' is absent from MarketWatch snapshot.",
                    expected=expected_broker_sym,
                    actual=None,
                    subject=expected_broker_sym,
                )
            )
            continue

        checked.append(snap_key)

        # Broker suffix parity (e.g. US100 vs US100.cash)
        if snap_key != expected_broker_sym:
            findings.append(
                PreflightFinding(
                    code="SYMBOL_SUFFIX_MISMATCH",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=(
                        f"Broker symbol name mismatch for '{req_sym}': expected '{expected_broker_sym}', "
                        f"observed '{snap_key}'."
                    ),
                    expected=expected_broker_sym,
                    actual=snap_key,
                    subject=req_sym,
                )
            )

        # MarketWatch visibility / selection check
        for vis_key in ("in_market_watch", "visible", "select"):
            if vis_key in snap and snap[vis_key] is False:
                findings.append(
                    PreflightFinding(
                        code="SYMBOL_NOT_IN_MARKETWATCH",
                        severity="REJECT",
                        check_area="marketwatch_parity",
                        message=f"Symbol '{snap_key}' is not enabled/visible in MarketWatch ({vis_key}=False).",
                        expected=True,
                        actual=False,
                        subject=snap_key,
                    )
                )
                break

        # Trade mode MUST be FULL
        raw_tmode = snap.get("trade_mode")
        norm_tmode = normalize_symbol_trade_mode(raw_tmode)
        if norm_tmode != "FULL":
            findings.append(
                PreflightFinding(
                    code="SYMBOL_TRADE_MODE_NOT_FULL",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=(
                        f"Symbol '{snap_key}' trade_mode is '{norm_tmode or raw_tmode}' "
                        "(must be SYMBOL_TRADE_MODE_FULL)."
                    ),
                    expected="FULL",
                    actual=norm_tmode or raw_tmode,
                    subject=snap_key,
                )
            )

        # Digits parity
        exp_digits = spec.get("digits")
        act_digits = snap.get("digits")
        if not _is_strict_int(exp_digits) or not _is_strict_int(act_digits) or act_digits != exp_digits:
            findings.append(
                PreflightFinding(
                    code="SYMBOL_DIGITS_MISMATCH",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=f"Symbol '{snap_key}' digits mismatch: expected {exp_digits}, got {act_digits}.",
                    expected=exp_digits,
                    actual=act_digits,
                    subject=snap_key,
                )
            )

        # Optional point consistency with digits
        if "point" in snap and snap["point"] is not None and _is_strict_int(exp_digits):
            obs_pt = _to_finite_float(snap["point"])
            exp_pt = 10.0 ** (-int(exp_digits))
            if obs_pt is None or abs(obs_pt - exp_pt) > 1e-12:
                findings.append(
                    PreflightFinding(
                        code="SYMBOL_POINT_MISMATCH",
                        severity="REJECT",
                        check_area="marketwatch_parity",
                        message=f"Symbol '{snap_key}' point mismatch: expected {exp_pt}, got {snap['point']}.",
                        expected=exp_pt,
                        actual=snap["point"],
                        subject=snap_key,
                    )
                )

        # Contract size parity
        exp_cs = _to_finite_float(spec.get("contract_size"))
        raw_act_cs = snap.get("contract_size")
        if raw_act_cs is None:
            raw_act_cs = snap.get("trade_contract_size")
        act_cs = _to_finite_float(raw_act_cs)
        if (
            exp_cs is None
            or exp_cs <= 0.0
            or act_cs is None
            or act_cs <= 0.0
            or abs(act_cs - exp_cs) / max(1.0, abs(exp_cs)) > eff_cs_tol
        ):
            findings.append(
                PreflightFinding(
                    code="SYMBOL_CONTRACT_SIZE_MISMATCH",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=(
                        f"Symbol '{snap_key}' contract_size mismatch: expected {exp_cs}, got {raw_act_cs}."
                    ),
                    expected=exp_cs,
                    actual=raw_act_cs,
                    subject=snap_key,
                )
            )

        # Stops level check
        raw_act_stops = snap.get("stops_level")
        if raw_act_stops is None:
            raw_act_stops = snap.get("trade_stops_level")
        exp_stops = spec.get("stops_level", 0)
        stops_ceiling = eff_max_stops if eff_max_stops is not None else exp_stops
        if not _is_strict_int(raw_act_stops) or raw_act_stops < 0:
            findings.append(
                PreflightFinding(
                    code="SYMBOL_STOPS_LEVEL_INVALID",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=f"Symbol '{snap_key}' stops_level is missing or negative: {raw_act_stops}.",
                    expected=f"0..{stops_ceiling}",
                    actual=raw_act_stops,
                    subject=snap_key,
                )
            )
        elif _is_strict_int(stops_ceiling) and raw_act_stops > stops_ceiling:
            findings.append(
                PreflightFinding(
                    code="SYMBOL_STOPS_LEVEL_EXCEEDED",
                    severity="REJECT",
                    check_area="marketwatch_parity",
                    message=(
                        f"Symbol '{snap_key}' stops_level={raw_act_stops} exceeds allowed ceiling {stops_ceiling}."
                    ),
                    expected=f"<= {stops_ceiling}",
                    actual=raw_act_stops,
                    subject=snap_key,
                )
            )

        # Optional per-symbol effective leverage check against firm asset-class profile
        if "effective_leverage" in snap and snap["effective_leverage"] is not None and firm_lev_table is not None:
            sym_cls = spec.get("asset_class") or classify_symbol_asset_class(snap_key)
            if sym_cls in firm_lev_table:
                exp_sym_lev = float(firm_lev_table[sym_cls])
                obs_sym_lev = _to_finite_float(snap["effective_leverage"])
                if (
                    obs_sym_lev is None
                    or obs_sym_lev <= 0.0
                    or abs(obs_sym_lev - exp_sym_lev) / max(1.0, exp_sym_lev) > eff_mw_lev_tol
                ):
                    findings.append(
                        PreflightFinding(
                            code="SYMBOL_LEVERAGE_MISMATCH",
                            severity="REJECT",
                            check_area="leverage",
                            message=(
                                f"Symbol '{snap_key}' ({sym_cls}) effective leverage 1:{snap['effective_leverage']} "
                                f"does not match {norm_firm} expected 1:{exp_sym_lev:g}."
                            ),
                            expected=exp_sym_lev,
                            actual=snap["effective_leverage"],
                            subject=snap_key,
                        )
                    )

    return findings, checked


def _normalize_direction(direction: Any) -> str | None:
    if isinstance(direction, bool):
        return None
    if isinstance(direction, (int, float)):
        if direction > 0:
            return "BUY"
        if direction < 0:
            return "SELL"
        return None
    if isinstance(direction, str):
        up = direction.strip().upper()
        if up in ("BUY", "LONG", "+1", "1", "B"):
            return "BUY"
        if up in ("SELL", "SHORT", "-1", "S"):
            return "SELL"
    return None


def _normalize_firm_name(firm: Any) -> str:
    raw = str(firm or "").strip().upper()
    if raw.startswith("FTMO"):
        return "FTMO"
    if "5ERS" in raw or "THE5ERS" in raw:
        return "THE5ERS"
    if "IC_FUNDED" in raw or "ICFUNDED" in raw or "IC FUNDED" in raw:
        return "IC_FUNDED"
    return raw


def check_multi_account_compliance(
    *,
    active_eas: Sequence[Mapping[str, Any]] | None = None,
    active_signals: Sequence[Mapping[str, Any]] | None = None,
    days_since_last_trade: float | int | None = None,
    max_day_profit_usd: float | None = None,
    daily_profits_usd: Sequence[float] | None = None,
    total_profit_target_usd: float | None = None,
    is_sprint_mode: bool = False,
    best_day_warn_ratio: float = DEFAULT_BEST_DAY_WARN_RATIO,
    firm_consistency_cap_ratio: float | None = None,
    hedging_window_sec: int = 3600,
) -> tuple[list[PreflightFinding], InactivityStatus, float | None]:
    findings: list[PreflightFinding] = []

    parsed_warn_ratio = _to_finite_float(best_day_warn_ratio)
    if parsed_warn_ratio is None or parsed_warn_ratio <= 0.0 or parsed_warn_ratio > 1.0:
        findings.append(
            PreflightFinding(
                code="INVALID_BEST_DAY_WARN_RATIO",
                severity="REJECT",
                check_area="multi_account_compliance",
                message=(
                    f"best_day_warn_ratio must be finite in (0.0, 1.0] (fail-closed), "
                    f"got {best_day_warn_ratio!r}."
                ),
                expected="(0.0, 1.0]",
                actual=best_day_warn_ratio,
            )
        )
        eff_warn_ratio = DEFAULT_BEST_DAY_WARN_RATIO
    else:
        eff_warn_ratio = parsed_warn_ratio

    parsed_hedge_win = _to_finite_float(hedging_window_sec)
    if parsed_hedge_win is None or parsed_hedge_win < 0.0:
        findings.append(
            PreflightFinding(
                code="INVALID_HEDGING_WINDOW_SEC",
                severity="REJECT",
                check_area="multi_account_compliance",
                message=(
                    f"hedging_window_sec must be finite >= 0 (fail-closed), got {hedging_window_sec!r}."
                ),
                expected=">= 0",
                actual=hedging_window_sec,
            )
        )
        eff_hedge_win = 3600.0
    else:
        eff_hedge_win = parsed_hedge_win

    parsed_cons_cap: float | None = None
    if firm_consistency_cap_ratio is not None:
        cap_check = _to_finite_float(firm_consistency_cap_ratio)
        if cap_check is None or cap_check <= 0.0 or cap_check > 1.0:
            findings.append(
                PreflightFinding(
                    code="INVALID_CONSISTENCY_CAP",
                    severity="REJECT",
                    check_area="multi_account_compliance",
                    message=f"firm_consistency_cap_ratio must be in (0, 1], got {firm_consistency_cap_ratio}.",
                    expected="(0.0, 1.0]",
                    actual=firm_consistency_cap_ratio,
                )
            )
        else:
            parsed_cons_cap = cap_check

    # 1. Magic Number Collision & Range Overlap Guard
    if active_eas:
        seen_magics: dict[tuple[Any, int], str] = {}
        seen_ranges: list[tuple[Any, int, int, str]] = []
        for idx, ea in enumerate(active_eas):
            ea_id = str(ea.get("ea_id") or ea.get("name") or f"ea_{idx}")
            acct_key = ea.get("account_login", "__default__")

            magics_to_check: list[Any] = []
            if "magic" in ea and ea["magic"] is not None:
                magics_to_check.append(ea["magic"])
            if "magics" in ea and ea["magics"] is not None:
                magics_to_check.extend(list(ea["magics"]))

            for m in magics_to_check:
                if not _is_strict_int(m) or m <= 0:
                    findings.append(
                        PreflightFinding(
                            code="INVALID_MAGIC_NUMBER",
                            severity="REJECT",
                            check_area="multi_account_compliance",
                            message=f"EA '{ea_id}' declares invalid magic number: {m}.",
                            expected="positive int",
                            actual=m,
                            subject=ea_id,
                        )
                    )
                    continue
                k = (acct_key, m)
                if k in seen_magics:
                    findings.append(
                        PreflightFinding(
                            code="MAGIC_NUMBER_COLLISION",
                            severity="REJECT",
                            check_area="multi_account_compliance",
                            message=(
                                f"Magic number {m} collides between '{seen_magics[k]}' and '{ea_id}' "
                                f"on account {acct_key}."
                            ),
                            expected="unique magic per EA on account",
                            actual=m,
                            subject=ea_id,
                        )
                    )
                else:
                    seen_magics[k] = ea_id

            if "magic_range" in ea and ea["magic_range"] is not None:
                rng = ea["magic_range"]
                if (
                    isinstance(rng, Sequence)
                    and len(rng) == 2
                    and _is_strict_int(rng[0])
                    and _is_strict_int(rng[1])
                    and 0 < rng[0] <= rng[1]
                ):
                    lo, hi = int(rng[0]), int(rng[1])
                    for prev_acct, prev_lo, prev_hi, prev_id in seen_ranges:
                        if prev_acct == acct_key and not (hi < prev_lo or lo > prev_hi):
                            findings.append(
                                PreflightFinding(
                                    code="MAGIC_RANGE_OVERLAP",
                                    severity="REJECT",
                                    check_area="multi_account_compliance",
                                    message=(
                                        f"Magic range [{lo}, {hi}] of '{ea_id}' overlaps "
                                        f"[{prev_lo}, {prev_hi}] of '{prev_id}' on account {acct_key}."
                                    ),
                                    expected="disjoint magic ranges",
                                    actual=[lo, hi],
                                    subject=ea_id,
                                )
                            )
                    seen_ranges.append((acct_key, lo, hi, ea_id))
                else:
                    findings.append(
                        PreflightFinding(
                            code="INVALID_MAGIC_RANGE",
                            severity="REJECT",
                            check_area="multi_account_compliance",
                            message=f"EA '{ea_id}' has invalid magic_range: {rng}.",
                            expected="(min_int, max_int) with 0 < min <= max",
                            actual=rng,
                            subject=ea_id,
                        )
                    )

        # Cross-check individual magics falling inside another EA's magic_range on the same account
        for (acct_key, m), ea_id in seen_magics.items():
            for rng_acct, lo, hi, rng_ea_id in seen_ranges:
                if rng_acct == acct_key and rng_ea_id != ea_id and lo <= m <= hi:
                    findings.append(
                        PreflightFinding(
                            code="MAGIC_NUMBER_COLLISION",
                            severity="REJECT",
                            check_area="multi_account_compliance",
                            message=(
                                f"Magic number {m} of '{ea_id}' falls inside magic_range [{lo}, {hi}] "
                                f"owned by '{rng_ea_id}' on account {acct_key}."
                            ),
                            expected="disjoint magic assignment",
                            actual=m,
                            subject=ea_id,
                        )
                    )

    # 2. Group Hedging Guard (opposite direction, same canonical symbol, different accounts at same firm)
    if active_signals:
        normalized_sigs: list[dict[str, Any]] = []
        for idx, sig in enumerate(active_signals):
            firm = _normalize_firm_name(sig.get("firm") or sig.get("firm_profile"))
            acct = sig.get("account_login")
            sym = str(sig.get("symbol") or "").strip()
            direction = _normalize_direction(sig.get("direction") or sig.get("side"))
            ts = _to_finite_float(sig.get("timestamp_utc")) if sig.get("timestamp_utc") is not None else None
            if not firm or acct is None or not sym or direction is None:
                findings.append(
                    PreflightFinding(
                        code="INVALID_ACTIVE_SIGNAL_RECORD",
                        severity="REJECT",
                        check_area="multi_account_compliance",
                        message=f"active_signals[{idx}] is missing firm/account_login/symbol/direction (fail-closed).",
                        expected="firm, account_login, symbol, direction(BUY|SELL)",
                        actual=dict(sig),
                        subject=f"signal_{idx}",
                    )
                )
                continue
            normalized_sigs.append(
                {
                    "firm": firm,
                    "account_login": acct,
                    "symbol": sym,
                    "root": canonical_symbol_root(sym),
                    "direction": direction,
                    "ts": ts,
                }
            )

        reported_pairs: set[tuple[str, str, str, str]] = set()
        for i in range(len(normalized_sigs)):
            a = normalized_sigs[i]
            for j in range(i + 1, len(normalized_sigs)):
                b = normalized_sigs[j]
                if a["firm"] != b["firm"]:
                    continue
                if a["root"] != b["root"]:
                    continue
                if a["account_login"] == b["account_login"]:
                    continue
                if a["direction"] == b["direction"]:
                    continue
                if a["ts"] is not None and b["ts"] is not None:
                    if abs(a["ts"] - b["ts"]) > eff_hedge_win:
                        continue
                pair_key = (
                    a["firm"],
                    a["root"],
                    str(min(str(a["account_login"]), str(b["account_login"]))),
                    str(max(str(a["account_login"]), str(b["account_login"]))),
                )
                if pair_key in reported_pairs:
                    continue
                reported_pairs.add(pair_key)
                findings.append(
                    PreflightFinding(
                        code="GROUP_HEDGING_CONFLICT",
                        severity="REJECT",
                        check_area="multi_account_compliance",
                        message=(
                            f"GROUP HEDGING RISK on {a['firm']} {a['root']}: account {a['account_login']} "
                            f"({a['direction']} {a['symbol']}) opposes account {b['account_login']} "
                            f"({b['direction']} {b['symbol']})."
                        ),
                        expected="no opposite-direction same-symbol signals across same-firm accounts",
                        actual={
                            "firm": a["firm"],
                            "symbol_root": a["root"],
                            "accounts": [a["account_login"], b["account_login"]],
                            "directions": [a["direction"], b["direction"]],
                        },
                        subject=a["root"],
                    )
                )

    # 3. Inactivity Rule Guard (21d AMBER / 27d RED / >=30d EXPIRED REJECT)
    inactivity_status: InactivityStatus = "NOT_PROVIDED"
    if days_since_last_trade is not None:
        days_val = _to_finite_float(days_since_last_trade)
        if days_val is None or days_val < 0.0:
            inactivity_status = "INVALID"
            findings.append(
                PreflightFinding(
                    code="INVALID_INACTIVITY_DAYS",
                    severity="REJECT",
                    check_area="multi_account_compliance",
                    message=f"days_since_last_trade must be a finite non-negative number, got {days_since_last_trade}.",
                    expected=">= 0",
                    actual=days_since_last_trade,
                )
            )
        elif days_val >= float(INACTIVITY_HARD_LIMIT_DAYS):
            inactivity_status = "EXPIRED"
            findings.append(
                PreflightFinding(
                    code="INACTIVITY_LIMIT_BREACHED",
                    severity="REJECT",
                    check_area="multi_account_compliance",
                    message=(
                        f"Account inactivity ({days_val:g}d) reached/exceeded the 30-day prop firm expiration limit."
                    ),
                    expected=f"< {INACTIVITY_HARD_LIMIT_DAYS}",
                    actual=days_val,
                )
            )
        elif days_val >= float(INACTIVITY_RED_DAYS):
            inactivity_status = "RED"
            findings.append(
                PreflightFinding(
                    code="INACTIVITY_RED_ALERT",
                    severity="RED",
                    check_area="multi_account_compliance",
                    message=(
                        f"RED INACTIVITY ALERT: {days_val:g} days since last trade "
                        f"(>= {INACTIVITY_RED_DAYS}d toward 30-day prop expiration limit)."
                    ),
                    expected=f"< {INACTIVITY_RED_DAYS}",
                    actual=days_val,
                )
            )
        elif days_val >= float(INACTIVITY_AMBER_DAYS):
            inactivity_status = "AMBER"
            findings.append(
                PreflightFinding(
                    code="INACTIVITY_AMBER_WARNING",
                    severity="AMBER",
                    check_area="multi_account_compliance",
                    message=(
                        f"AMBER INACTIVITY WARNING: {days_val:g} days since last trade "
                        f"(>= {INACTIVITY_AMBER_DAYS}d toward 30-day limit)."
                    ),
                    expected=f"< {INACTIVITY_AMBER_DAYS}",
                    actual=days_val,
                )
            )
        else:
            inactivity_status = "GREEN"

    # 4. Best-Day Share Guard (`max_day_profit / total_profit_target > 0.45` warning under Sprint)
    best_day_share: float | None = None
    resolved_max_day: float | None = None
    if daily_profits_usd is not None:
        parsed_days: list[float] = []
        for idx, val in enumerate(daily_profits_usd):
            fv = _to_finite_float(val)
            if fv is None:
                findings.append(
                    PreflightFinding(
                        code="INVALID_DAILY_PROFIT_ENTRY",
                        severity="REJECT",
                        check_area="multi_account_compliance",
                        message=f"daily_profits_usd[{idx}] is non-finite or invalid: {val}.",
                        expected="finite number",
                        actual=val,
                    )
                )
                return findings, inactivity_status, None
            parsed_days.append(fv)
        resolved_max_day = max(0.0, max(parsed_days)) if parsed_days else 0.0

    if max_day_profit_usd is not None:
        fv = _to_finite_float(max_day_profit_usd)
        if fv is None:
            findings.append(
                PreflightFinding(
                    code="INVALID_MAX_DAY_PROFIT",
                    severity="REJECT",
                    check_area="multi_account_compliance",
                    message=f"max_day_profit_usd must be finite, got {max_day_profit_usd}.",
                    expected="finite number",
                    actual=max_day_profit_usd,
                )
            )
            return findings, inactivity_status, None
        resolved_max_day = max(0.0, fv)

    if resolved_max_day is not None and total_profit_target_usd is not None:
        target_val = _to_finite_float(total_profit_target_usd)
        if target_val is None or target_val <= 0.0:
            findings.append(
                PreflightFinding(
                    code="INVALID_PROFIT_TARGET",
                    severity="REJECT",
                    check_area="multi_account_compliance",
                    message=(
                        f"total_profit_target_usd must be > 0 when computing best-day share, "
                        f"got {total_profit_target_usd}."
                    ),
                    expected="> 0.0",
                    actual=total_profit_target_usd,
                )
            )
        else:
            best_day_share = round(resolved_max_day / target_val, 6)
            if parsed_cons_cap is not None and best_day_share > parsed_cons_cap + 1e-9:
                findings.append(
                    PreflightFinding(
                        code="BEST_DAY_CONSISTENCY_BREACH",
                        severity="REJECT",
                        check_area="multi_account_compliance",
                        message=(
                            f"Best-day share {best_day_share:.2%} exceeds firm hard consistency cap "
                            f"{parsed_cons_cap:.2%}."
                        ),
                        expected=f"<= {parsed_cons_cap:.2f}",
                        actual=best_day_share,
                    )
                )

            if is_sprint_mode and best_day_share > eff_warn_ratio + 1e-9:
                if best_day_share > 0.50 + 1e-9:
                    findings.append(
                        PreflightFinding(
                            code="BEST_DAY_SHARE_SPRINT_RED",
                            severity="RED",
                            check_area="multi_account_compliance",
                            message=(
                                f"RED BEST-DAY CONCENTRATION (Sprint): max single-day profit is "
                                f"{best_day_share:.1%} of target (> 50% review/consistency risk)."
                            ),
                            expected=f"<= {eff_warn_ratio:.2f}",
                            actual=best_day_share,
                        )
                    )
                else:
                    findings.append(
                        PreflightFinding(
                            code="BEST_DAY_SHARE_SPRINT_WARNING",
                            severity="AMBER",
                            check_area="multi_account_compliance",
                            message=(
                                f"AMBER BEST-DAY CONCENTRATION (Sprint): max single-day profit is "
                                f"{best_day_share:.1%} of target (> {eff_warn_ratio:.0%})."
                            ),
                            expected=f"<= {eff_warn_ratio:.2f}",
                            actual=best_day_share,
                        )
                    )

    return findings, inactivity_status, best_day_share


def check_primary_live_preset_flags(
    *,
    preset: Mapping[str, Any],
    is_primary_live_preset: bool = True,
) -> list[PreflightFinding]:
    """Enforce `B8`: `InpAllowManualHaltFile == true` and `InpWritePrimaryHeartbeat == true` on primary live presets."""
    if not is_primary_live_preset:
        return []

    findings: list[PreflightFinding] = []
    halt_flag = _parse_bool_strict(preset.get("InpAllowManualHaltFile"))
    if halt_flag is not True:
        findings.append(
            PreflightFinding(
                code="B8_MANUAL_HALT_FILE_DISABLED",
                severity="REJECT",
                check_area="preset_safety_b8",
                message=(
                    "B8 FAIL-CLOSED REJECT: Primary live preset MUST set InpAllowManualHaltFile=true "
                    "for emergency flat-halt capability."
                ),
                expected=True,
                actual=preset.get("InpAllowManualHaltFile"),
                subject="InpAllowManualHaltFile",
            )
        )

    hb_flag = _parse_bool_strict(preset.get("InpWritePrimaryHeartbeat"))
    if hb_flag is not True:
        findings.append(
            PreflightFinding(
                code="B8_PRIMARY_HEARTBEAT_DISABLED",
                severity="REJECT",
                check_area="preset_safety_b8",
                message=(
                    "B8 FAIL-CLOSED REJECT: Primary live preset MUST set InpWritePrimaryHeartbeat=true "
                    "for dead-man watchdog telemetry."
                ),
                expected=True,
                actual=preset.get("InpWritePrimaryHeartbeat"),
                subject="InpWritePrimaryHeartbeat",
            )
        )

    return findings


def validate_account_deployment(
    *,
    expected_login: int,
    actual_login: int | None,
    expected_trade_mode: str | int,
    actual_trade_mode: str | int | None,
    firm_profile: str,
    account_phase: str,
    preset: Mapping[str, Any] | Path | str,
    account_leverage: int | float | None = None,
    asset_class_leverages: Mapping[str, int | float] | None = None,
    market_watch_symbols: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    required_symbols: Sequence[str] | None = None,
    expected_specs: Mapping[str, Mapping[str, Any]] | None = None,
    specs_path: Path | str | None = None,
    broker_suffix_map: Mapping[str, str] | None = None,
    active_eas: Sequence[Mapping[str, Any]] | None = None,
    active_signals: Sequence[Mapping[str, Any]] | None = None,
    days_since_last_trade: float | int | None = None,
    max_day_profit_usd: float | None = None,
    daily_profits_usd: Sequence[float] | None = None,
    total_profit_target_usd: float | None = None,
    is_sprint_mode: bool | None = None,
    is_primary_live_preset: bool = True,
    expected_server: str | None = None,
    actual_server: str | None = None,
    trade_allowed: bool | None = None,
    trade_expert: bool | None = None,
    max_funded_risk_mult: float = DEFAULT_FUNDED_MAX_RISK_MULT,
    strict_funded_1x: bool = False,
    max_funded_amber_dd_pct: float = DEFAULT_FUNDED_MAX_AMBER_DD_PCT,
    max_funded_red_dd_pct: float = DEFAULT_FUNDED_MAX_RED_DD_PCT,
    max_allowed_stops_level: int | None = None,
    expected_leverage_by_class: Mapping[str, int | float] | None = None,
    firm_consistency_cap_ratio: float | None = None,
    best_day_warn_ratio: float = DEFAULT_BEST_DAY_WARN_RATIO,
    hedging_window_sec: int = 3600,
    preset_phase: str | None = None,
    preset_name: str | None = None,
    require_market_watch: bool = True,
) -> PreflightReport:
    """Fail-closed pre-launch validator across account binding, phase lock, leverage, MarketWatch, B8 & compliance."""
    findings: list[PreflightFinding] = []
    resolved_preset_name = preset_name
    preset_dict: dict[str, Any] = {}

    if isinstance(preset, (Path, str)):
        p = Path(preset)
        resolved_preset_name = resolved_preset_name or p.name
        if not p.is_file():
            findings.append(
                PreflightFinding(
                    code="PRESET_FILE_NOT_FOUND",
                    severity="REJECT",
                    check_area="preset_loading",
                    message=f"Preset file not found: {p}",
                    expected="existing .set file",
                    actual=str(p),
                )
            )
        else:
            preset_dict = parse_mt5_set_file(p)
    elif isinstance(preset, Mapping):
        preset_dict = dict(preset)
    else:
        findings.append(
            PreflightFinding(
                code="INVALID_PRESET_INPUT",
                severity="REJECT",
                check_area="preset_loading",
                message="preset must be a Mapping or Path to an MT5 .set file.",
                expected="Mapping | Path",
                actual=type(preset).__name__,
            )
        )

    findings.extend(
        check_account_binding(
            expected_login=expected_login,
            actual_login=actual_login,
            expected_trade_mode=expected_trade_mode,
            actual_trade_mode=actual_trade_mode,
            expected_server=expected_server,
            actual_server=actual_server,
            trade_allowed=trade_allowed,
            trade_expert=trade_expert,
        )
    )

    findings.extend(
        check_eval_vs_funded_lock(
            account_phase=account_phase,
            preset=preset_dict,
            explicit_preset_phase=preset_phase,
            preset_name=resolved_preset_name,
            max_funded_risk_mult=max_funded_risk_mult,
            strict_funded_1x=strict_funded_1x,
            max_funded_amber_dd_pct=max_funded_amber_dd_pct,
            max_funded_red_dd_pct=max_funded_red_dd_pct,
        )
    )

    findings.extend(
        check_primary_live_preset_flags(
            preset=preset_dict,
            is_primary_live_preset=is_primary_live_preset,
        )
    )

    findings.extend(
        check_asset_class_leverage(
            firm_profile=firm_profile,
            account_leverage=account_leverage,
            asset_class_leverages=asset_class_leverages,
            expected_leverage_by_class=expected_leverage_by_class,
        )
    )

    mw_findings, checked_symbols = check_marketwatch_contract_parity(
        market_watch_symbols=market_watch_symbols,
        required_symbols=required_symbols,
        expected_specs=expected_specs,
        specs_path=specs_path,
        broker_suffix_map=broker_suffix_map,
        preset=preset_dict,
        firm_profile=firm_profile,
        max_allowed_stops_level=max_allowed_stops_level,
        require_market_watch=require_market_watch,
    )
    findings.extend(mw_findings)

    norm_phase = normalize_account_phase(account_phase) or str(account_phase)
    effective_sprint = (
        is_sprint_mode
        if is_sprint_mode is not None
        else (norm_phase == "EVAL" and _is_sprint_preset(preset_dict, preset_name=resolved_preset_name))
    )

    comp_findings, inactivity_status, best_day_share = check_multi_account_compliance(
        active_eas=active_eas,
        active_signals=active_signals,
        days_since_last_trade=days_since_last_trade,
        max_day_profit_usd=max_day_profit_usd,
        daily_profits_usd=daily_profits_usd,
        total_profit_target_usd=total_profit_target_usd,
        is_sprint_mode=effective_sprint,
        best_day_warn_ratio=best_day_warn_ratio,
        firm_consistency_cap_ratio=firm_consistency_cap_ratio,
        hedging_window_sec=hedging_window_sec,
    )
    findings.extend(comp_findings)

    reject_codes = tuple(f.code for f in findings if f.severity == "REJECT")
    red_codes = tuple(f.code for f in findings if f.severity == "RED")
    amber_codes = tuple(f.code for f in findings if f.severity == "AMBER")

    if reject_codes:
        passed = False
        verdict: Verdict = "REJECT"
        alert_level: AlertLevel = "REJECT"
    elif red_codes:
        passed = True
        verdict = "PASS_WITH_RED"
        alert_level = "RED"
    elif amber_codes:
        passed = True
        verdict = "PASS_WITH_AMBER"
        alert_level = "AMBER"
    else:
        passed = True
        verdict = "PASS"
        alert_level = "GREEN"

    return PreflightReport(
        schema=PREFLIGHT_SCHEMA,
        passed=passed,
        can_launch=passed,
        verdict=verdict,
        alert_level=alert_level,
        firm_profile=normalize_firm_profile(firm_profile) or str(firm_profile),
        account_phase=norm_phase,
        inactivity_status=inactivity_status,
        best_day_share=best_day_share,
        findings=tuple(findings),
        reject_codes=reject_codes,
        red_codes=red_codes,
        amber_codes=amber_codes,
        checked_symbols=tuple(checked_symbols),
        order_send_capable=ORDER_SEND_CAPABLE,
        order_send_count=ORDER_SEND_COUNT,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed offline Account-Phase & MarketWatch preflight validator (ORDER_SEND_CAPABLE=False)."
    )
    parser.add_argument("--config-json", type=Path, required=True, help="Path to deployment preflight JSON payload.")
    parser.add_argument("--set-file", type=Path, default=None, help="Optional MT5 .set file overriding payload preset.")
    parser.add_argument("--specs-json", type=Path, default=None, help="Optional symbol specs JSON path.")
    args = parser.parse_args(argv)

    payload = json.loads(args.config_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config-json must contain a JSON object")
    if args.set_file is not None:
        payload["preset"] = args.set_file
    if args.specs_json is not None:
        payload["specs_path"] = args.specs_json

    report = validate_account_deployment(**payload)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
