"""Periodic Prop Firm Terms & Black Friday Promo Drift Radar (OrderSend = 0).

Compares observed official/fixture prop firm rules and seasonal promotions
against Naqex SSOT catalogs:
  - `tooling/ai-engines/configs/ssot/firms_catalog.json`
  - `tooling/ai-engines/configs/prop_pricing_catalog.json`

Tracks BOTH Black Friday 2026 operational deadlines:
  1. `bf_bill_lock`: `2026-11-30T16:00:00+07:00` (`10:00 CET`, 0 VND lock window)
  2. `bf_14day_payment_cutoff`: `2026-12-14T16:00:00+07:00` (14-day unpaid invoice
     cutoff — explicitly flagged `NOT_DISCLOSED_REQUIRES_SUPPORT_CONFIRMATION`)

Hard safety & supply-chain invariants (enforced under `python -O`, zero bare `assert`):
  - `ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0`, `SPEND_VND = 0`
  - Every external finding is tagged `untrusted_external_data: true` with `trust_tier`
  - Read-only public HTTPS GET only in `--live` mode (NEVER logins, NEVER bypasses
    CAPTCHA/anti-bot, NEVER submits forms or places orders)
  - `--offline` mode performs zero network calls (100% CI safe)
  - `--dry-run` computes and prints the report without writing disk state
  - Persists sanitized output atomically to `.runtime/automation/prop_terms_radar_latest.json`
"""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

SCHEMA_VERSION: str = "naqex-prop-terms-radar-v1"
ORDER_SEND_COUNT: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0
SPEND_VND: int = 0
UNTRUSTED_EXTERNAL_DATA: bool = True

ICT_TZ = timezone(timedelta(hours=7))
CET_TZ = timezone(timedelta(hours=1))

DEADLINE_BF_BILL_LOCK_ISO: str = "2026-11-30T16:00:00+07:00"
DEADLINE_BF_14DAY_CUTOFF_ISO: str = "2026-12-14T16:00:00+07:00"

INTERMEDIATE_GATES: tuple[dict[str, str], ...] = (
    {
        "id": "holdout_v2_lock",
        "label": "Holdout v2 Prospective Lock",
        "timestamp": "2026-12-01T00:00:00Z",
    },
    {
        "id": "nfp",
        "label": "US Non-Farm Payrolls (NFP)",
        "timestamp": "2026-12-04T20:30:00+07:00",
    },
    {
        "id": "ftmo_free_trial_end",
        "label": "FTMO Free Trial 14d Window End",
        "timestamp": "2026-12-08T23:59:59+07:00",
    },
    {
        "id": "cpi",
        "label": "US Consumer Price Index (CPI)",
        "timestamp": "2026-12-10T20:30:00+07:00",
    },
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIRMS_CATALOG = REPO_ROOT / "tooling" / "ai-engines" / "configs" / "ssot" / "firms_catalog.json"
DEFAULT_PRICING_CATALOG = REPO_ROOT / "tooling" / "ai-engines" / "configs" / "prop_pricing_catalog.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / ".runtime" / "automation" / "prop_terms_radar_latest.json"

READ_ONLY_USER_AGENT: str = "NaqexPropTermsRadar/1.0 (https://github.com/naqex; read-only)"

TIER1_OFFICIAL_DOMAINS: tuple[str, ...] = (
    "ftmo.com",
    "the5ers.com",
    "icfunded.com",
    "e8markets.com",
)
TIER2_TECHNICAL_DOMAINS: tuple[str, ...] = (
    "fxstreet.com",
    "quantpedia.com",
    "mql5.com",
)
TIER3_FORUM_DOMAINS: tuple[str, ...] = (
    "reddit.com",
    "forexfactory.com",
    "trustpilot.com",
    "hocvientrader.com",
)

LIVE_PUBLIC_PROBE_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "firm_id": "ftmo",
        "label": "FTMO Black Friday",
        "url": "https://ftmo.com/en/black-friday/",
        "keywords": ("black friday", "30%", "20%", "10:00", "cet", "november 30"),
    },
    {
        "firm_id": "ftmo",
        "label": "FTMO Terms and Conditions",
        "url": "https://ftmo.com/en/terms-and-conditions/",
        "keywords": ("proforma invoice", "14 days", "withdraw", "cancel"),
    },
    {
        "firm_id": "ftmo",
        "label": "FTMO News FAQ",
        "url": "https://ftmo.com/en/faq/can-i-trade-news/",
        "keywords": ("2 minutes", "restricted", "swing", "standard"),
    },
    {
        "firm_id": "the5ers",
        "label": "The5ers High Stakes",
        "url": "https://the5ers.com/high-stakes/",
        "keywords": ("high stakes", "5k", "25k", "black friday", "10%", "2 minutes"),
    },
    {
        "firm_id": "the5ers",
        "label": "The5ers Terms",
        "url": "https://the5ers.com/terms-and-conditions/",
        "keywords": ("proforma", "3.5%", "expert advisor", "forbidden"),
    },
    {
        "firm_id": "ic_funded",
        "label": "IC Funded Home",
        "url": "https://icfunded.com/",
        "keywords": ("black friday", "blackic45", "5,000", "10,000", "25,000"),
    },
    {
        "firm_id": "ic_funded",
        "label": "IC Funded Terms",
        "url": "https://icfunded.com/terms-and-conditions/",
        "keywords": ("3 minutes", "inconsistent trading", "copy trading", "third payout"),
    },
)

_FORBIDDEN_URL_PATH_FRAGMENTS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/logout",
    "/checkout/submit",
    "/order/create",
    "/payment/confirm",
    "/api/order",
)

_ANTIBOT_MARKERS: tuple[str, ...] = (
    "just a moment...",
    "cf-chl-",
    "cf-turnstile",
    "challenge-platform",
    "enable javascript and cookies",
    "verify you are human",
    "g-recaptcha",
    "hcaptcha",
    "turnstile",
    "attention required! | cloudflare",
)

_TRUST_TIER_RANK: dict[str, int] = {
    "T1_PRIMARY_OFFICIAL": 1,
    "T2_TECHNICAL_COMMUNITY": 2,
    "T3_FORUM_EXPERIENCE": 3,
    "T3_GENERAL_WEB": 4,
}

_FORBIDDEN_HOST_SUFFIXES: tuple[str, ...] = (
    ".localhost",
    ".local",
    ".internal",
    ".localdomain",
)

_NUMERIC_LABEL_RE = re.compile(r"^(?:0x[0-9a-f]+|0o[0-7]+|[0-9]+)$")

_WIN_USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/]"
    r"(?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_SECRET_TOKEN_RE = re.compile(
    r"(?:\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,})\b)"
)
_PRIVATE_IP_RE = re.compile(
    r"(?<![0-9.])(?!100\.64\.0\.0/10(?![0-9]))"
    r"(?:192\.168\.\d{1,3}\.\d{1,3}|"
    r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![0-9.])"
)

# Verified offline snapshot compiled from 2026-11-27 external research (T1 primary +
# clearly separated T2/T3 signals). Used by `--offline` for 100% CI-safe execution.
DEFAULT_OFFLINE_SNAPSHOT: dict[str, Any] = {
    "snapshot_id": "prop-terms-radar-snapshot-20261127",
    "fetched_utc": "2026-11-27T06:44:00Z",
    "untrusted_external_data": True,
    "firms": {
        "ftmo": {
            "trust_tier": "T1_PRIMARY_OFFICIAL",
            "source_urls": [
                "https://ftmo.com/en/black-friday/",
                "https://ftmo.com/en/terms-and-conditions/",
                "https://ftmo.com/en/faq/can-i-trade-news/",
                "https://ftmo.com/en/faq/how-can-i-pay-for-the-ftmo-challenge/",
                "https://ftmo.com/en/faq/how-do-i-withdraw-my-reward/",
                "https://ftmo.com/en/forbidden-trading-practices/",
            ],
            "vietnam_eligible": True,
            "ea_allowed": True,
            "third_party_ea_shared_cap_risk": True,
            "requires_ea_written_clearance": False,
            "server_msg_daily_cap": 2000,
            "max_open_orders": 200,
            "black_friday_2026": {
                "active": True,
                "cutoff_cet_primary": "2026-11-30T10:00:00+01:00",
                "cutoff_ict_primary": "2026-11-30T16:00:00+07:00",
                "cutoff_cet_alt_t3": "2026-11-30T10:30:00+01:00",
                "cutoff_discrepancy_detected": True,
                "discount_pct_by_tier": {
                    "ftmo_2step_standard:10K": 30.0,
                    "ftmo_2step_standard:25K": 20.0,
                    "ftmo_2step_standard:50K": 20.0,
                    "ftmo_2step_standard:100K": 20.0,
                    "ftmo_2step_standard:200K": 20.0,
                    "ftmo_2step_swing:10K": 0.0,
                    "ftmo_2step_swing:25K": 0.0,
                },
                "trust_tier": "T1_PRIMARY_OFFICIAL",
            },
            "unpaid_invoice_14d_policy": {
                "contractual_price_lock_after_promo": "NOT_DISCLOSED",
                "gtc_clause": ("Clause 3.4 (Proforma Invoice for bank transfer; right to cancel if unpaid on time)"),
                "proforma_methods": ["bank_wire"],
                "instant_timeout_methods": [
                    "card",
                    "apple_pay",
                    "google_pay",
                    "paypal",
                    "revolut_pay",
                    "crypto",
                    "skrill",
                ],
                "eu_paid_withdrawal_right_days": 14,
                "eu_withdrawal_void_on_first_trade": True,
                "community_vn_pending_bill_observation_days": 14,
                "community_trust_tier": "T3_FORUM_EXPERIENCE",
                "requires_support_confirmation": True,
            },
            "programs": {
                "ftmo_2step_standard": {
                    "news_restricted_eval": False,
                    "news_restricted_funded": True,
                    "news_window_sec": 120,
                    "news_includes_sl_tp_triggers": True,
                    "qualitative_consistency_rule": False,
                    "best_day_cap_pct": None,
                    "min_payout_usd_wire_card": 20.0,
                    "min_payout_usd_crypto": 50.0,
                    "profit_split_pct": 80.0,
                    "fee_refund_milestone": "FIRST_PAYOUT",
                    "tiers": {
                        "10K": {"orig_usd": 98.61, "promo_usd": 68.70, "promo_pct": 30.0},
                        "25K": {"orig_usd": 277.01, "promo_usd": 220.50, "promo_pct": 20.0},
                    },
                },
            },
        },
        "the5ers": {
            "trust_tier": "T1_PRIMARY_OFFICIAL",
            "source_urls": [
                "https://the5ers.com/high-stakes/",
                "https://the5ers.com/terms-and-conditions/",
                "https://the5ers.com/faqs/",
            ],
            "vietnam_eligible": True,
            "ea_allowed": True,
            "own_source_code_required": True,
            "requires_ea_written_clearance": True,
            "black_friday_2026": {
                "active": True,
                "discount_pct": 10.0,
                "promo_code": None,
                "cutoff_iso": "NOT_DISCLOSED",
                "trust_tier": "T3_GENERAL_WEB",
                "notes": ("Reported 10% sitewide BF 2026 on T2/T3 trackers; not yet verified on live T1 checkout."),
            },
            "unpaid_invoice_14d_policy": {
                "contractual_price_lock_after_promo": "NOT_DISCLOSED",
                "gtc_clause": "Proforma invoice for bank transfer; right to cancel if unpaid on time",
                "proforma_methods": ["bank_wire"],
                "instant_timeout_methods": ["card", "crypto"],
                "requires_support_confirmation": True,
            },
            "retired_tiers": ["20K", "60K"],
            "observed_extra_tiers": ["2.5K"],
            "programs": {
                "the5ers_high_stakes_classic": {
                    "news_restricted_eval": True,
                    "news_restricted_funded": True,
                    "news_window_sec": 120,
                    "news_breach_penalty": "SOFT_BREACH_PROFIT_DEDUCTED_LOSS_KEPT",
                    "qualitative_consistency_rule": False,
                    "min_profitable_days": 3,
                    "profitable_day_threshold_pct": 0.5,
                    "min_payout_usd": 150.0,
                    "withdrawal_fee_pct": 3.5,
                    "profit_split_pct": 80.0,
                    "fee_refund_milestone": "10PCT_HUB_P1_20PCT_HUB_P2_70PCT_CASH_FIRST_PAYOUT",
                    "tiers": {
                        "5K": {
                            "orig_usd": 39.0,
                            "promo_usd": 35.10,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "10K": {
                            "orig_usd": 78.0,
                            "promo_usd": 70.20,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "25K": {
                            "orig_usd": 195.0,
                            "promo_usd": 175.50,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                    },
                },
                "the5ers_high_stakes_new": {
                    "news_restricted_eval": True,
                    "news_restricted_funded": True,
                    "news_window_sec": 120,
                    "qualitative_consistency_rule": False,
                    "min_profitable_days": 3,
                    "profitable_day_threshold_pct": 0.5,
                    "min_payout_usd": 150.0,
                    "withdrawal_fee_pct": 3.5,
                    "profit_split_pct": 80.0,
                    "tiers": {
                        "5K": {
                            "orig_usd": 35.0,
                            "promo_usd": 31.50,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "10K": {
                            "orig_usd": 69.0,
                            "promo_usd": 62.10,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "25K": {
                            "orig_usd": 176.0,
                            "promo_usd": 158.40,
                            "promo_pct": 10.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                    },
                },
            },
        },
        "ic_funded": {
            "trust_tier": "T1_PRIMARY_OFFICIAL",
            "source_urls": [
                "https://icfunded.com/",
                "https://icfunded.com/terms-and-conditions/",
            ],
            "vietnam_eligible": True,
            "ea_allowed": True,
            "own_source_code_required": True,
            "requires_ea_written_clearance": False,
            "server_msg_daily_cap": 3000,
            "black_friday_2026": {
                "active": True,
                "discount_pct": 45.0,
                "promo_code": "BLACKIC45",
                "cutoff_iso": "2026-11-30T23:59:59Z",
                "cutoff_exact_verified": False,
                "trust_tier": "T3_GENERAL_WEB",
                "notes": (
                    "Code BLACKIC45 (-45% through Nov 30, 2026) seen on T3 coupon aggregators/YouTube only; "
                    "verify on live icfunded.com checkout before relying."
                ),
            },
            "programs": {
                "ic_funded_2step_pro": {
                    "news_restricted_eval": False,
                    "news_restricted_funded": True,
                    "news_window_sec": 180,
                    "news_window_instant_sec": 600,
                    "qualitative_consistency_rule": True,
                    "consistency_clause": (
                        "Terms Section 12 (Inconsistent Trading: lot size, strategy, "
                        "frequency, risk exposure across eval vs funded)"
                    ),
                    "profit_split_start_range_pct": [75.0, 80.0],
                    "profit_split_pct": 80.0,
                    "fee_refund_milestone": "THIRD_PAYOUT",
                    "tiers": {
                        "5K": {
                            "orig_usd": 74.0,
                            "promo_usd": 40.70,
                            "promo_pct": 45.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "10K": {
                            "orig_usd": 125.0,
                            "promo_usd": 68.75,
                            "promo_pct": 45.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                        "25K": {
                            "orig_usd": 249.0,
                            "promo_usd": 136.95,
                            "promo_pct": 45.0,
                            "promo_trust_tier": "T3_GENERAL_WEB",
                        },
                    },
                },
            },
        },
    },
}


def enforce_read_only_invariants() -> None:
    """Fail-closed invariant check safe under `python -O` (no bare `assert`)."""
    if ORDER_SEND_COUNT != 0:
        raise RuntimeError(f"Hard invariant violated: ORDER_SEND_COUNT={ORDER_SEND_COUNT}")
    if HOLDOUT_ROWS_ANALYSED != 0:
        raise RuntimeError(f"Hard invariant violated: HOLDOUT_ROWS_ANALYSED={HOLDOUT_ROWS_ANALYSED}")
    if SPEND_VND != 0:
        raise RuntimeError(f"Hard invariant violated: SPEND_VND={SPEND_VND}")
    if not UNTRUSTED_EXTERNAL_DATA:
        raise RuntimeError("Hard invariant violated: UNTRUSTED_EXTERNAL_DATA must remain True")


def parse_iso_utc(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Timestamp must be a non-empty ISO-8601 string")
    cleaned = raw.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_utc(dt: datetime | None = None) -> str:
    """Format an aware UTC datetime as canonical ISO-8601 `...Z`."""
    cur = (dt or datetime.now(UTC)).astimezone(UTC)
    return cur.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_trust_tier(url: str) -> str:
    """Classify a URL by strict domain-boundary matching (prevents spoofing)."""
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return "T3_GENERAL_WEB"

    def _matches(domains: tuple[str, ...]) -> bool:
        return any(host == d or host.endswith("." + d) for d in domains)

    if _matches(TIER1_OFFICIAL_DOMAINS):
        return "T1_PRIMARY_OFFICIAL"
    if _matches(TIER2_TECHNICAL_DOMAINS):
        return "T2_TECHNICAL_COMMUNITY"
    if _matches(TIER3_FORUM_DOMAINS):
        return "T3_FORUM_EXPERIENCE"
    return "T3_GENERAL_WEB"


def resolve_capped_trust_tier(
    source_urls: Sequence[str],
    declared_tier: str | None = None,
) -> str:
    """Compute weakest (strictest) trust tier across ALL URLs; never allow self-declared elevation."""
    cleaned_urls = [str(u).strip() for u in source_urls if isinstance(u, str) and str(u).strip()]
    if not cleaned_urls:
        url_tier = "T3_GENERAL_WEB"
    else:
        url_tier = max(
            (classify_trust_tier(u) for u in cleaned_urls),
            key=lambda tier: _TRUST_TIER_RANK.get(tier, 4),
        )
    if not declared_tier:
        return url_tier
    decl = str(declared_tier).strip()
    if decl not in _TRUST_TIER_RANK:
        return "T3_GENERAL_WEB"
    return max((url_tier, decl), key=lambda tier: _TRUST_TIER_RANK[tier])


def validate_public_read_only_url(url: str) -> str:
    """Validate that a target URL is public HTTPS and never points to internal/login/order endpoints."""
    cleaned = str(url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Only https:// public URLs are allowed, got: {cleaned!r}")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in URL are strictly prohibited")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host == "localhost" or any(host.endswith(sfx) for sfx in _FORBIDDEN_HOST_SUFFIXES):
        raise ValueError(f"Local/internal host is prohibited: {host!r}")
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        addr = None
    if addr is not None:
        if not addr.is_global or addr.is_private or addr.is_loopback or addr.is_unspecified:
            raise ValueError(f"Non-global/private/loopback IP host is prohibited: {host!r}")
    else:
        if "." not in host:
            raise ValueError(f"Single-label/numeric-integer host is prohibited: {host!r}")
        labels = host.split(".")
        if all(_NUMERIC_LABEL_RE.fullmatch(lbl) is not None for lbl in labels):
            raise ValueError(f"Obfuscated/non-canonical numeric IP host is prohibited: {host!r}")
    path_low = (parsed.path or "").lower()
    for frag in _FORBIDDEN_URL_PATH_FRAGMENTS:
        if frag in path_low:
            raise ValueError(f"Interactive login/checkout URL blocked by supply-chain guard: {cleaned!r}")
    return cleaned


def sanitize_opsec_text(raw: Any) -> str:
    """Scrub local Windows profile paths, private IPs, and secret tokens."""
    out = str(raw or "")
    out = _SECRET_TOKEN_RE.sub("<REDACTED_SECRET>", out)
    out = _WIN_USER_PATH_RE.sub("<USER_HOME>", out)
    out = _PRIVATE_IP_RE.sub("<REDACTED_IP>", out)
    return out


def sanitize_payload(obj: Any) -> Any:
    """Recursively sanitize all string values inside a JSON-serializable payload."""
    if isinstance(obj, str):
        return sanitize_opsec_text(obj)
    if isinstance(obj, dict):
        return {str(k): sanitize_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_payload(v) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_payload(v) for v in obj]
    return obj


def load_json_file(
    path: Path | str,
    *,
    expected_schema_key: str | None = None,
    expected_schema: str | None = None,
) -> dict[str, Any]:
    """Load and validate a JSON object from disk."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Required JSON file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {p}")
    if expected_schema_key and expected_schema:
        actual = data.get(expected_schema_key)
        if actual != expected_schema:
            raise ValueError(f"Invalid {expected_schema_key} in {p}: expected {expected_schema!r}, got {actual!r}")
    return data


def atomic_write_json(path: Path | str, payload: Mapping[str, Any]) -> Path:
    """Atomically write LF-only UTF-8 JSON to disk via temp file + fsync + replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(sanitize_payload(dict(payload)), indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return target


def evaluate_deadlines(
    now_utc: datetime | None = None,
    *,
    bill_lock_iso: str = DEADLINE_BF_BILL_LOCK_ISO,
    cutoff_14d_iso: str = DEADLINE_BF_14DAY_CUTOFF_ISO,
) -> dict[str, Any]:
    """Evaluate BOTH Black Friday 2026 deadlines and intermediate macro gates."""
    enforce_read_only_invariants()
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    lock_dt = parse_iso_utc(bill_lock_iso)
    cutoff_dt = parse_iso_utc(cutoff_14d_iso)

    if cutoff_dt <= lock_dt:
        raise ValueError(f"14-day payment cutoff ({cutoff_14d_iso}) must be strictly after bill lock ({bill_lock_iso})")

    lock_rem_sec = (lock_dt - now).total_seconds()
    lock_rem_hours = round(lock_rem_sec / 3600.0, 2)
    if lock_rem_sec <= 0:
        lock_status = "EXPIRED"
    elif lock_rem_hours <= 24.0:
        lock_status = "URGENT_WINDOW"
    else:
        lock_status = "UPCOMING"

    cutoff_rem_sec = (cutoff_dt - now).total_seconds()
    cutoff_rem_hours = round(cutoff_rem_sec / 3600.0, 2)
    if now < lock_dt:
        cutoff_status = "PRE_LOCK_WINDOW"
    elif cutoff_rem_sec <= 0:
        cutoff_status = "EXPIRED"
    elif cutoff_rem_hours <= 24.0:
        cutoff_status = "URGENT_PAYMENT_WINDOW"
    else:
        cutoff_status = "ACTIVE_HOLD_WINDOW"

    gates_status: list[dict[str, Any]] = []
    for gate in INTERMEDIATE_GATES:
        g_dt = parse_iso_utc(gate["timestamp"])
        g_rem_h = round((g_dt - now).total_seconds() / 3600.0, 2)
        gates_status.append(
            {
                "id": gate["id"],
                "label": gate["label"],
                "timestamp_utc": format_utc(g_dt),
                "timestamp_ict": g_dt.astimezone(ICT_TZ).isoformat(),
                "hours_remaining": g_rem_h,
                "status": "PASSED" if g_rem_h <= 0 else "UPCOMING",
            }
        )

    return {
        "checked_utc": format_utc(now),
        "checked_ict": now.astimezone(ICT_TZ).isoformat(),
        "bf_bill_lock": {
            "id": "bf_bill_lock",
            "label": "FTMO Black Friday Bill Lock Cutoff (0 VND)",
            "timestamp_ict": lock_dt.astimezone(ICT_TZ).isoformat(),
            "timestamp_cet": lock_dt.astimezone(CET_TZ).isoformat(),
            "timestamp_utc": format_utc(lock_dt),
            "hours_remaining": lock_rem_hours,
            "days_remaining": round(lock_rem_hours / 24.0, 2),
            "status": lock_status,
            "spend_vnd_required": 0,
            "cutoff_discrepancy_note": (
                "Primary consensus cutoff is 2026-11-30 10:00 CET (16:00 ICT); one T3 source cites "
                "10:30 CET. Fail-closed to earlier 10:00 CET and verify live timer before 15:00 ICT."
            ),
        },
        "bf_14day_payment_cutoff": {
            "id": "bf_14day_payment_cutoff",
            "label": "14-Day Unpaid Invoice Cutoff (Conditional — Support Confirmation Required)",
            "timestamp_ict": cutoff_dt.astimezone(ICT_TZ).isoformat(),
            "timestamp_cet": cutoff_dt.astimezone(CET_TZ).isoformat(),
            "timestamp_utc": format_utc(cutoff_dt),
            "hours_remaining": cutoff_rem_hours,
            "days_remaining": round(cutoff_rem_hours / 24.0, 2),
            "hold_span_days": round((cutoff_dt - lock_dt).total_seconds() / 86400.0, 2),
            "status": cutoff_status,
            "contractual_price_lock_status": "NOT_DISCLOSED_REQUIRES_SUPPORT_CONFIRMATION",
            "ftmo_gtc_clause": (
                "Clause 3.4: Bank transfer issues proforma invoice with stated due date; "
                "FTMO entitled to cancel unpaid orders."
            ),
            "the5ers_gtc_clause": (
                "Bank transfer issues proforma invoice; right to cancel if unpaid on time; no BF lock guarantee."
            ),
            "proforma_methods": ["bank_wire"],
            "instant_timeout_methods": [
                "card",
                "apple_pay",
                "google_pay",
                "paypal",
                "revolut_pay",
                "crypto",
                "skrill",
            ],
            "vn_bank_wire_warning": (
                "Outbound SWIFT wire from Vietnam incurs ~15-40 USD bank/intermediary fees, "
                "erasing ~30 USD BF savings on FTMO 10K."
            ),
        },
        "intermediate_macro_gates": gates_status,
    }


def _close_float(a: Any, b: Any, tol: float = 1e-4) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    if not (math.isfinite(float(a)) and math.isfinite(float(b))):
        return False
    return abs(float(a) - float(b)) <= tol


def _extract_tier_key(contract: Mapping[str, Any]) -> str:
    cap = float(contract.get("capital_usd", 0.0))
    if cap >= 1000.0 and abs(cap % 1000.0) < 1e-6:
        return f"{int(round(cap / 1000.0))}K"
    return f"{cap / 1000.0:g}K"


def check_cross_catalog_parity(
    firms_catalog: Mapping[str, Any],
    pricing_catalog: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Verify internal consistency between `firms_catalog.json` and `prop_pricing_catalog.json`."""
    drifts: list[dict[str, Any]] = []
    pricing_firms = pricing_catalog.get("firms", {})
    contracts = firms_catalog.get("contracts", {})

    for cid, contract in contracts.items():
        firm_id = str(contract.get("firm_id", ""))
        prog_id = str(contract.get("program_id", ""))
        tier_key = _extract_tier_key(contract)

        p_firm = pricing_firms.get(firm_id)
        if not isinstance(p_firm, Mapping):
            drifts.append(
                {
                    "drift_id": f"CROSS_MISSING_FIRM_{cid}",
                    "scope": "cross_catalog",
                    "firm_id": firm_id,
                    "contract_id": cid,
                    "severity": "HIGH",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "firm_id",
                    "ssot_firms_value": firm_id,
                    "ssot_pricing_value": None,
                    "message": f"Firm {firm_id!r} present in firms_catalog but missing in prop_pricing_catalog.",
                }
            )
            continue

        p_prog = p_firm.get("programs", {}).get(prog_id)
        if not isinstance(p_prog, Mapping):
            drifts.append(
                {
                    "drift_id": f"CROSS_MISSING_PROGRAM_{cid}",
                    "scope": "cross_catalog",
                    "firm_id": firm_id,
                    "contract_id": cid,
                    "severity": "HIGH",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "program_id",
                    "ssot_firms_value": prog_id,
                    "ssot_pricing_value": None,
                    "message": (f"Program {prog_id!r} present in firms_catalog but missing in prop_pricing_catalog."),
                }
            )
            continue

        p_tier = p_prog.get("tiers", {}).get(tier_key)
        if not isinstance(p_tier, Mapping):
            drifts.append(
                {
                    "drift_id": f"CROSS_MISSING_TIER_{cid}",
                    "scope": "cross_catalog",
                    "firm_id": firm_id,
                    "contract_id": cid,
                    "severity": "HIGH",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "tier",
                    "ssot_firms_value": tier_key,
                    "ssot_pricing_value": None,
                    "message": f"Tier {tier_key!r} for {prog_id!r} missing in prop_pricing_catalog.",
                }
            )
            continue

        p1_pct = round(float(contract.get("p1_target_frac", 0.0)) * 100.0, 4)
        p2_pct = round(float(contract.get("p2_target_frac", 0.0)) * 100.0, 4)
        dd_daily = round(float(contract.get("daily_loss_limit_frac", 0.0)) * 100.0, 4)
        dd_max = round(float(contract.get("static_loss_limit_frac", 0.0)) * 100.0, 4)
        split_pct = round(float(contract.get("payout_split_frac", 0.0)) * 100.0, 4)

        comparisons: tuple[tuple[str, Any, Any, str], ...] = (
            ("available_vn", contract.get("available_vn"), p_tier.get("available_vn"), "HIGH"),
            ("fee_orig_usd", contract.get("fee_orig_usd"), p_tier.get("orig_usd"), "HIGH"),
            ("fee_promo_usd", contract.get("fee_promo_usd"), p_tier.get("active_promo_usd"), "HIGH"),
            ("p1_target_pct", p1_pct, p_prog.get("p1_target_pct"), "HIGH"),
            ("p2_target_pct", p2_pct, p_prog.get("p2_target_pct"), "HIGH"),
            ("dd_daily_pct", dd_daily, p_tier.get("dd_daily_pct"), "CRITICAL"),
            ("dd_max_pct", dd_max, p_tier.get("dd_max_pct"), "CRITICAL"),
            (
                "news_restricted_eval",
                contract.get("news_restricted_eval"),
                p_prog.get("news_restricted_eval"),
                "HIGH",
            ),
            (
                "news_restricted_funded",
                contract.get("news_restricted_funded"),
                p_prog.get("news_restricted_funded"),
                "HIGH",
            ),
            ("news_window_sec", contract.get("news_window_sec"), p_prog.get("news_window_sec"), "HIGH"),
            ("min_payout_usd", contract.get("min_payout_usd"), p_prog.get("min_payout_usd"), "MEDIUM"),
            ("profit_split_pct", split_pct, p_prog.get("profit_split_pct"), "MEDIUM"),
        )
        for field_name, val_f, val_p, sev in comparisons:
            if isinstance(val_f, bool) or isinstance(val_p, bool):
                same = val_f is val_p
            elif isinstance(val_f, (int, float)) or isinstance(val_p, (int, float)) or val_f is None or val_p is None:
                same = _close_float(val_f, val_p, tol=1e-2)
            else:
                same = val_f == val_p
            if not same:
                drifts.append(
                    {
                        "drift_id": f"CROSS_{cid}_{field_name}".upper(),
                        "scope": "cross_catalog",
                        "firm_id": firm_id,
                        "contract_id": cid,
                        "severity": sev,
                        "trust_tier": "T1_LOCAL_SSOT",
                        "field": field_name,
                        "ssot_firms_value": val_f,
                        "ssot_pricing_value": val_p,
                        "message": (
                            f"SSOT mismatch on {cid}.{field_name}: "
                            f"firms_catalog={val_f!r} vs prop_pricing_catalog={val_p!r}."
                        ),
                    }
                )

    return drifts


def check_catalog_staleness(
    firms_catalog: Mapping[str, Any],
    pricing_catalog: Mapping[str, Any],
    now_utc: datetime,
) -> list[dict[str, Any]]:
    """Check catalog freshness and guard against invalid future timestamps."""
    drifts: list[dict[str, Any]] = []
    checks = (
        ("firms_catalog", firms_catalog.get("updated_utc"), float(firms_catalog.get("staleness_max_cal_days", 7))),
        (
            "prop_pricing_catalog",
            pricing_catalog.get("updated_utc"),
            float(pricing_catalog.get("staleness_max_days", 7)),
        ),
    )
    for label, raw_ts, max_days in checks:
        if not isinstance(raw_ts, str) or not raw_ts.strip():
            drifts.append(
                {
                    "drift_id": f"STALE_MISSING_TS_{label}".upper(),
                    "scope": "staleness",
                    "firm_id": "all",
                    "severity": "HIGH",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "updated_utc",
                    "ssot_value": None,
                    "observed_value": format_utc(now_utc),
                    "message": f"{label} is missing updated_utc.",
                }
            )
            continue
        ts_dt = parse_iso_utc(raw_ts)
        age_days = (now_utc - ts_dt).total_seconds() / 86400.0
        if age_days < -1.0:
            drifts.append(
                {
                    "drift_id": f"FUTURE_TS_{label}".upper(),
                    "scope": "staleness",
                    "firm_id": "all",
                    "severity": "HIGH",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "updated_utc",
                    "ssot_value": raw_ts,
                    "observed_value": format_utc(now_utc),
                    "message": f"{label}.updated_utc ({raw_ts}) is in the future by {abs(age_days):.2f} days.",
                }
            )
        elif age_days > max_days:
            drifts.append(
                {
                    "drift_id": f"STALE_{label}".upper(),
                    "scope": "staleness",
                    "firm_id": "all",
                    "severity": "MEDIUM",
                    "trust_tier": "T1_LOCAL_SSOT",
                    "field": "updated_utc",
                    "ssot_value": raw_ts,
                    "observed_value": f"age={age_days:.2f}d > max={max_days:.1f}d",
                    "message": f"{label} is stale ({age_days:.2f}d > {max_days:.1f}d max).",
                }
            )
    return drifts


def detect_external_drift(
    firms_catalog: Mapping[str, Any],
    pricing_catalog: Mapping[str, Any],
    observed_snapshot: Mapping[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Compare observed external firm rules & promos against both SSOT catalogs."""
    enforce_read_only_invariants()
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    if observed_snapshot.get("untrusted_external_data") is not True:
        raise ValueError("observed_snapshot must explicitly declare untrusted_external_data: true")

    drifts: list[dict[str, Any]] = []
    drifts.extend(check_cross_catalog_parity(firms_catalog, pricing_catalog))
    drifts.extend(check_catalog_staleness(firms_catalog, pricing_catalog, now))

    ssot_firms = pricing_catalog.get("firms", {})
    obs_firms = observed_snapshot.get("firms", {})
    firm_summaries: dict[str, Any] = {}

    for firm_id, obs_firm in obs_firms.items():
        if not isinstance(obs_firm, Mapping):
            continue
        ssot_firm = ssot_firms.get(firm_id)
        source_urls = list(obs_firm.get("source_urls", []))
        declared_firm_tier = obs_firm.get("trust_tier")
        trust_tier = resolve_capped_trust_tier(
            source_urls,
            str(declared_firm_tier) if declared_firm_tier is not None else None,
        )
        firm_drift_count_before = len(drifts)

        if not isinstance(ssot_firm, Mapping):
            drifts.append(
                {
                    "drift_id": f"EXT_UNKNOWN_FIRM_{firm_id}".upper(),
                    "scope": "external_rules",
                    "firm_id": firm_id,
                    "severity": "MEDIUM",
                    "trust_tier": trust_tier,
                    "untrusted_external_data": True,
                    "field": "firm_id",
                    "ssot_value": None,
                    "observed_value": firm_id,
                    "source_urls": source_urls,
                    "message": f"Observed firm {firm_id!r} not present in prop_pricing_catalog.",
                }
            )
            continue

        # 1. Vietnam eligibility & EA policy checks
        if "vietnam_eligible" in obs_firm and obs_firm["vietnam_eligible"] is not ssot_firm.get("vietnam_eligible"):
            drifts.append(
                {
                    "drift_id": f"EXT_{firm_id}_VIETNAM_ELIGIBLE".upper(),
                    "scope": "external_rules",
                    "firm_id": firm_id,
                    "severity": "CRITICAL",
                    "trust_tier": trust_tier,
                    "untrusted_external_data": True,
                    "field": "vietnam_eligible",
                    "ssot_value": ssot_firm.get("vietnam_eligible"),
                    "observed_value": obs_firm["vietnam_eligible"],
                    "source_urls": source_urls,
                    "message": (
                        f"{firm_id} Vietnam eligibility changed: "
                        f"SSOT={ssot_firm.get('vietnam_eligible')} vs observed={obs_firm['vietnam_eligible']}."
                    ),
                }
            )

        ssot_ea = ssot_firm.get("ea_policy", {})
        if "ea_allowed" in obs_firm and obs_firm["ea_allowed"] is not ssot_ea.get("allowed"):
            drifts.append(
                {
                    "drift_id": f"EXT_{firm_id}_EA_ALLOWED".upper(),
                    "scope": "external_rules",
                    "firm_id": firm_id,
                    "severity": "CRITICAL",
                    "trust_tier": trust_tier,
                    "untrusted_external_data": True,
                    "field": "ea_policy.allowed",
                    "ssot_value": ssot_ea.get("allowed"),
                    "observed_value": obs_firm["ea_allowed"],
                    "source_urls": source_urls,
                    "message": (
                        f"{firm_id} EA allowance changed: "
                        f"SSOT={ssot_ea.get('allowed')} vs observed={obs_firm['ea_allowed']}."
                    ),
                }
            )

        if "server_msg_daily_cap" in obs_firm and obs_firm["server_msg_daily_cap"] != ssot_ea.get(
            "server_msg_daily_cap"
        ):
            drifts.append(
                {
                    "drift_id": f"EXT_{firm_id}_SERVER_MSG_CAP".upper(),
                    "scope": "external_rules",
                    "firm_id": firm_id,
                    "severity": "MEDIUM",
                    "trust_tier": trust_tier,
                    "untrusted_external_data": True,
                    "field": "ea_policy.server_msg_daily_cap",
                    "ssot_value": ssot_ea.get("server_msg_daily_cap"),
                    "observed_value": obs_firm["server_msg_daily_cap"],
                    "source_urls": source_urls,
                    "message": (
                        f"{firm_id} server message cap changed: "
                        f"SSOT={ssot_ea.get('server_msg_daily_cap')} vs observed={obs_firm['server_msg_daily_cap']}."
                    ),
                }
            )

        # 2. Black Friday cutoff discrepancy & unpaid invoice contractual gap
        bf = obs_firm.get("black_friday_2026", {})
        if isinstance(bf, Mapping) and bf.get("cutoff_discrepancy_detected"):
            drifts.append(
                {
                    "drift_id": f"EXT_{firm_id}_BF_CUTOFF_DISCREPANCY".upper(),
                    "scope": "black_friday",
                    "firm_id": firm_id,
                    "severity": "MEDIUM",
                    "trust_tier": "T3_GENERAL_WEB",
                    "untrusted_external_data": True,
                    "field": "black_friday_2026.cutoff_cet",
                    "ssot_value": bf.get("cutoff_cet_primary"),
                    "observed_value": bf.get("cutoff_cet_alt_t3"),
                    "source_urls": source_urls,
                    "message": (
                        f"{firm_id} BF cutoff discrepancy: primary={bf.get('cutoff_cet_primary')} vs "
                        f"alt T3={bf.get('cutoff_cet_alt_t3')} (keep conservative earlier cutoff)."
                    ),
                }
            )

        inv_pol = obs_firm.get("unpaid_invoice_14d_policy", {})
        if isinstance(inv_pol, Mapping) and inv_pol.get("contractual_price_lock_after_promo") == "NOT_DISCLOSED":
            drifts.append(
                {
                    "drift_id": f"EXT_{firm_id}_14D_INVOICE_LOCK_UNVERIFIED".upper(),
                    "scope": "black_friday_invoice",
                    "firm_id": firm_id,
                    "severity": "HIGH",
                    "trust_tier": trust_tier,
                    "untrusted_external_data": True,
                    "field": "unpaid_invoice_14d_policy.contractual_price_lock_after_promo",
                    "ssot_value": "MILESTONE_2026-12-14T16:00:00+07:00",
                    "observed_value": "NOT_DISCLOSED",
                    "source_urls": source_urls,
                    "message": (
                        f"{firm_id} official T&Cs do NOT disclose a contractual 14-day Black Friday price lock "
                        "on unpaid orders; direct support confirmation required."
                    ),
                }
            )

        # 3. Extra tiers observed (e.g. The5ers 2.5K)
        extra_tiers = obs_firm.get("observed_extra_tiers", [])
        if isinstance(extra_tiers, list) and extra_tiers:
            first_prog = next(iter(ssot_firm.get("programs", {}).values()), {})
            ssot_tier_keys = set(first_prog.get("tiers", {}).keys()) if isinstance(first_prog, Mapping) else set()
            missing_in_ssot = [t for t in extra_tiers if t not in ssot_tier_keys]
            if missing_in_ssot:
                drifts.append(
                    {
                        "drift_id": f"EXT_{firm_id}_EXTRA_TIERS".upper(),
                        "scope": "catalog_coverage",
                        "firm_id": firm_id,
                        "severity": "LOW",
                        "trust_tier": "T3_GENERAL_WEB",
                        "untrusted_external_data": True,
                        "field": "tiers",
                        "ssot_value": sorted(ssot_tier_keys),
                        "observed_value": missing_in_ssot,
                        "source_urls": source_urls,
                        "message": (
                            f"{firm_id} has additional tier(s) {missing_in_ssot} reported externally "
                            "not yet listed in SSOT."
                        ),
                    }
                )

        # 4. Program-level & tier-level comparisons
        obs_progs = obs_firm.get("programs", {})
        ssot_progs = ssot_firm.get("programs", {})
        for prog_id, obs_prog in obs_progs.items():
            if not isinstance(obs_prog, Mapping):
                continue
            ssot_prog = ssot_progs.get(prog_id)
            if not isinstance(ssot_prog, Mapping):
                drifts.append(
                    {
                        "drift_id": f"EXT_{firm_id}_{prog_id}_MISSING".upper(),
                        "scope": "external_rules",
                        "firm_id": firm_id,
                        "program_id": prog_id,
                        "severity": "MEDIUM",
                        "trust_tier": trust_tier,
                        "untrusted_external_data": True,
                        "field": "program_id",
                        "ssot_value": None,
                        "observed_value": prog_id,
                        "source_urls": source_urls,
                        "message": f"Program {prog_id!r} observed for {firm_id} is missing in SSOT.",
                    }
                )
                continue

            # News window & restrictions
            for news_key in ("news_restricted_eval", "news_restricted_funded"):
                if news_key in obs_prog and obs_prog[news_key] is not ssot_prog.get(news_key):
                    drifts.append(
                        {
                            "drift_id": f"EXT_{prog_id}_{news_key}".upper(),
                            "scope": "external_rules",
                            "firm_id": firm_id,
                            "program_id": prog_id,
                            "severity": "CRITICAL",
                            "trust_tier": trust_tier,
                            "untrusted_external_data": True,
                            "field": news_key,
                            "ssot_value": ssot_prog.get(news_key),
                            "observed_value": obs_prog[news_key],
                            "source_urls": source_urls,
                            "message": (
                                f"{prog_id}.{news_key} changed: "
                                f"SSOT={ssot_prog.get(news_key)} vs observed={obs_prog[news_key]}."
                            ),
                        }
                    )

            if "news_window_sec" in obs_prog and not _close_float(
                obs_prog["news_window_sec"],
                ssot_prog.get("news_window_sec"),
                tol=0.5,
            ):
                drifts.append(
                    {
                        "drift_id": f"EXT_{prog_id}_NEWS_WINDOW_SEC".upper(),
                        "scope": "external_rules",
                        "firm_id": firm_id,
                        "program_id": prog_id,
                        "severity": "HIGH",
                        "trust_tier": trust_tier,
                        "untrusted_external_data": True,
                        "field": "news_window_sec",
                        "ssot_value": ssot_prog.get("news_window_sec"),
                        "observed_value": obs_prog["news_window_sec"],
                        "source_urls": source_urls,
                        "message": (
                            f"{prog_id} funded news window differs: "
                            f"SSOT={ssot_prog.get('news_window_sec')}s vs observed={obs_prog['news_window_sec']}s."
                        ),
                    }
                )

            # Qualitative consistency rule gap
            if (
                obs_prog.get("qualitative_consistency_rule") is True
                and ssot_prog.get("best_day_cap_pct") is None
                and ssot_prog.get("daily_profit_cap_pct") is None
                and not ssot_prog.get("qualitative_consistency_rule")
            ):
                clause = obs_prog.get("consistency_clause", "T&Cs")
                drifts.append(
                    {
                        "drift_id": f"EXT_{prog_id}_QUALITATIVE_CONSISTENCY".upper(),
                        "scope": "external_rules",
                        "firm_id": firm_id,
                        "program_id": prog_id,
                        "severity": "HIGH",
                        "trust_tier": trust_tier,
                        "untrusted_external_data": True,
                        "field": "qualitative_consistency_rule",
                        "ssot_value": False,
                        "observed_value": True,
                        "source_urls": source_urls,
                        "message": (
                            f"{prog_id} enforces qualitative consistency ({clause}) not explicitly flagged "
                            "in SSOT — avoid aggressive lot step-down (4x -> 1x) without support clearance."
                        ),
                    }
                )

            # Min payout channel nuance (e.g., FTMO 20 USD wire/card vs 50 USD crypto)
            if "min_payout_usd_wire_card" in obs_prog and not _close_float(
                obs_prog["min_payout_usd_wire_card"],
                ssot_prog.get("min_payout_usd"),
                tol=0.01,
            ):
                drifts.append(
                    {
                        "drift_id": f"EXT_{prog_id}_MIN_PAYOUT_CHANNEL".upper(),
                        "scope": "external_rules",
                        "firm_id": firm_id,
                        "program_id": prog_id,
                        "severity": "MEDIUM",
                        "trust_tier": trust_tier,
                        "untrusted_external_data": True,
                        "field": "min_payout_usd",
                        "ssot_value": ssot_prog.get("min_payout_usd"),
                        "observed_value": {
                            "wire_card_usd": obs_prog["min_payout_usd_wire_card"],
                            "crypto_usd": obs_prog.get("min_payout_usd_crypto"),
                        },
                        "source_urls": source_urls,
                        "message": (
                            f"{prog_id} min_payout_usd is channel-dependent: "
                            f"wire/card={obs_prog['min_payout_usd_wire_card']} USD, "
                            f"crypto={obs_prog.get('min_payout_usd_crypto')} USD "
                            f"(SSOT models {ssot_prog.get('min_payout_usd')} USD)."
                        ),
                    }
                )

            # Profit split range check (e.g., IC Funded 75-80% start)
            split_range = obs_prog.get("profit_split_start_range_pct")
            if (
                isinstance(split_range, list)
                and split_range
                and min(split_range) < float(ssot_prog.get("profit_split_pct", 0.0))
            ):
                drifts.append(
                    {
                        "drift_id": f"EXT_{prog_id}_PROFIT_SPLIT_START".upper(),
                        "scope": "external_rules",
                        "firm_id": firm_id,
                        "program_id": prog_id,
                        "severity": "LOW",
                        "trust_tier": trust_tier,
                        "untrusted_external_data": True,
                        "field": "profit_split_pct",
                        "ssot_value": ssot_prog.get("profit_split_pct"),
                        "observed_value": split_range,
                        "source_urls": source_urls,
                        "message": (
                            f"{prog_id} official pages mention starting profit split range {split_range}% "
                            f"vs SSOT {ssot_prog.get('profit_split_pct')}% — verify selected tier at checkout."
                        ),
                    }
                )

            # Tier pricing & Black Friday promo diffs
            obs_tiers = obs_prog.get("tiers", {})
            ssot_tiers = ssot_prog.get("tiers", {})
            for tier_key, obs_tier in obs_tiers.items():
                if not isinstance(obs_tier, Mapping):
                    continue
                ssot_tier = ssot_tiers.get(tier_key)
                if not isinstance(ssot_tier, Mapping):
                    continue
                if "orig_usd" in obs_tier and not _close_float(
                    obs_tier["orig_usd"],
                    ssot_tier.get("orig_usd"),
                    tol=0.05,
                ):
                    drifts.append(
                        {
                            "drift_id": f"EXT_{prog_id}_{tier_key}_ORIG_USD".upper(),
                            "scope": "pricing",
                            "firm_id": firm_id,
                            "program_id": prog_id,
                            "tier": tier_key,
                            "severity": "HIGH",
                            "trust_tier": trust_tier,
                            "untrusted_external_data": True,
                            "field": "orig_usd",
                            "ssot_value": ssot_tier.get("orig_usd"),
                            "observed_value": obs_tier["orig_usd"],
                            "source_urls": source_urls,
                            "message": (
                                f"{prog_id} {tier_key} list price changed: "
                                f"SSOT={ssot_tier.get('orig_usd')} USD vs observed={obs_tier['orig_usd']} USD."
                            ),
                        }
                    )
                if "promo_usd" in obs_tier and not _close_float(
                    obs_tier["promo_usd"],
                    ssot_tier.get("active_promo_usd"),
                    tol=0.05,
                ):
                    promo_urls = obs_tier.get("source_urls") or source_urls
                    raw_promo_tier = obs_tier.get("promo_trust_tier") or trust_tier
                    promo_tier = resolve_capped_trust_tier(
                        promo_urls if isinstance(promo_urls, list) else source_urls,
                        str(raw_promo_tier),
                    )
                    # Promo tier can never exceed the firm's verified trust tier either.
                    promo_tier = max(
                        (promo_tier, trust_tier),
                        key=lambda tier: _TRUST_TIER_RANK.get(tier, 4),
                    )
                    is_t1 = promo_tier == "T1_PRIMARY_OFFICIAL"
                    drifts.append(
                        {
                            "drift_id": f"EXT_{prog_id}_{tier_key}_PROMO_USD".upper(),
                            "scope": "black_friday_promo",
                            "firm_id": firm_id,
                            "program_id": prog_id,
                            "tier": tier_key,
                            "severity": "HIGH" if is_t1 else "MEDIUM",
                            "trust_tier": promo_tier,
                            "untrusted_external_data": True,
                            "requires_checkout_verification": not is_t1,
                            "field": "active_promo_usd",
                            "ssot_value": ssot_tier.get("active_promo_usd"),
                            "observed_value": obs_tier["promo_usd"],
                            "observed_promo_pct": obs_tier.get("promo_pct"),
                            "source_urls": source_urls,
                            "message": (
                                f"{prog_id} {tier_key} promo price differs ({promo_tier}): "
                                f"SSOT={ssot_tier.get('active_promo_usd')} USD vs "
                                f"observed={obs_tier['promo_usd']} USD (-{obs_tier.get('promo_pct', 0)}%)."
                            ),
                        }
                    )

        bf_declared_tier = bf.get("trust_tier") if isinstance(bf, Mapping) else None
        bf_capped_tier = (
            resolve_capped_trust_tier(source_urls, str(bf_declared_tier)) if bf_declared_tier is not None else "UNKNOWN"
        )
        firm_summaries[firm_id] = {
            "trust_tier": trust_tier,
            "vietnam_eligible": obs_firm.get("vietnam_eligible"),
            "ea_allowed": obs_firm.get("ea_allowed"),
            "black_friday_active": bool(bf.get("active")) if isinstance(bf, Mapping) else False,
            "black_friday_trust_tier": bf_capped_tier,
            "drift_count": len(drifts) - firm_drift_count_before,
            "source_urls": source_urls,
        }

    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for d in drifts:
        sev = str(d.get("severity", "LOW")).upper()
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    if sev_counts["CRITICAL"] > 0:
        overall_status = "CRITICAL_DRIFT"
    elif sev_counts["HIGH"] > 0:
        overall_status = "DRIFT_DETECTED_ACTION_REQUIRED"
    elif sev_counts["MEDIUM"] > 0 or sev_counts["LOW"] > 0:
        overall_status = "ADVISORY_DRIFT"
    else:
        overall_status = "ALIGNED"

    return {
        "overall_status": overall_status,
        "total_drifts": len(drifts),
        "severity_counts": sev_counts,
        "firms": firm_summaries,
        "drifts": drifts,
    }


def _strip_html(raw_html: str) -> str:
    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


class _SafeReadOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validates every HTTP 3xx redirect target against the SSRF/supply-chain URL guard."""

    max_redirections = 5

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        resolved = urljoin(req.full_url, newurl)
        safe_target = validate_public_read_only_url(resolved)
        return super().redirect_request(req, fp, code, msg, headers, safe_target)


def fetch_public_url(
    url: str,
    timeout: float = 10.0,
    *,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, str]:
    """Read-only GET fetch with redirect SSRF validation and clean HTTPError status capture."""
    safe_url = validate_public_read_only_url(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": READ_ONLY_USER_AGENT}, method="GET")
    active_opener = opener or urllib.request.build_opener(_SafeReadOnlyRedirectHandler())
    try:
        with active_opener.open(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 200))
            body = resp.read(512_000).decode("utf-8", errors="replace")
            return status, body
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            raw = exc.read(512_000)
            if isinstance(raw, bytes):
                body = raw.decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return int(exc.code), body


def probe_live_public_urls(
    targets: tuple[dict[str, Any], ...] = LIVE_PUBLIC_PROBE_TARGETS,
    *,
    timeout_sec: float = 10.0,
    fetch_fn: Callable[[str, float], tuple[int, str]] | None = None,
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    """Bounded read-only public HTTPS probe. NEVER logins or bypasses CAPTCHA/anti-bot."""
    enforce_read_only_invariants()
    fetched_ts = format_utc(now_utc)
    results: list[dict[str, Any]] = []

    fetcher = fetch_fn or fetch_public_url

    for item in targets:
        raw_url = str(item["url"])
        safe_url = validate_public_read_only_url(raw_url)
        tier = classify_trust_tier(safe_url)
        record: dict[str, Any] = {
            "firm_id": str(item.get("firm_id", "unknown")),
            "label": str(item.get("label", safe_url)),
            "url": safe_url,
            "trust_tier": tier,
            "fetched_utc": fetched_ts,
            "untrusted_external_data": True,
            "http_status": None,
            "probe_status": "UNREACHABLE_OR_TIMEOUT",
            "matched_keywords": [],
            "error": None,
        }
        try:
            status_code, raw_body = fetcher(safe_url, timeout_sec)
            record["http_status"] = int(status_code)
            raw_low = raw_body.lower()
            text = _strip_html(raw_body)
            low = text.lower()
            has_antibot = any((m in raw_low) or (m in low) for m in _ANTIBOT_MARKERS)
            if status_code in (403, 429, 503) or has_antibot:
                record["probe_status"] = "ANTI_BOT_BLOCKED_STOPPED"
                record["error"] = "Anti-bot/CAPTCHA gate encountered; stopped immediately per supply-chain guard."
            elif 200 <= status_code < 300:
                record["probe_status"] = "OK_PUBLIC_TEXT"
                kws = item.get("keywords", ())
                record["matched_keywords"] = [str(k) for k in kws if str(k).lower() in low]
            else:
                record["probe_status"] = "HTTP_ERROR"
                record["error"] = f"HTTP {status_code}"
        except Exception as exc:
            record["probe_status"] = "UNREACHABLE_OR_TIMEOUT"
            record["error"] = sanitize_opsec_text(f"{type(exc).__name__}: {exc}")
        results.append(record)

    return results


def run_radar(
    *,
    mode: str = "offline",
    dry_run: bool = False,
    firms_catalog_path: Path | str = DEFAULT_FIRMS_CATALOG,
    pricing_catalog_path: Path | str = DEFAULT_PRICING_CATALOG,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    snapshot_path: Path | str | None = None,
    snapshot_override: Mapping[str, Any] | None = None,
    now_utc: datetime | None = None,
    fetch_fn: Callable[[str, float], tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """Execute the prop terms & Black Friday radar and optionally persist latest JSON."""
    enforce_read_only_invariants()
    if mode not in ("offline", "live"):
        raise ValueError(f"Unsupported mode {mode!r}; expected 'offline' or 'live'")

    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    firms_cat = load_json_file(
        firms_catalog_path,
        expected_schema_key="schema_version",
        expected_schema="naqex-ssot-firms-catalog-v1",
    )
    pricing_cat = load_json_file(
        pricing_catalog_path,
        expected_schema_key="schema",
        expected_schema="naqex-prop-pricing-catalog-v1",
    )

    if snapshot_override is not None:
        snapshot = dict(snapshot_override)
    elif snapshot_path is not None:
        snapshot = load_json_file(snapshot_path)
    else:
        snapshot = DEFAULT_OFFLINE_SNAPSHOT

    deadlines = evaluate_deadlines(now_utc=now)
    drift_report = detect_external_drift(firms_cat, pricing_cat, snapshot, now_utc=now)
    live_probes: list[dict[str, Any]] = []
    if mode == "live":
        live_probes = probe_live_public_urls(fetch_fn=fetch_fn, now_utc=now)

    report: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_utc": format_utc(now),
        "mode": mode,
        "dry_run": bool(dry_run),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "spend_vnd": SPEND_VND,
        "untrusted_external_data": UNTRUSTED_EXTERNAL_DATA,
        "snapshot_id": snapshot.get("snapshot_id", "custom"),
        "snapshot_fetched_utc": snapshot.get("fetched_utc", format_utc(now)),
        "deadlines": deadlines,
        "drift_summary": {
            "overall_status": drift_report["overall_status"],
            "total_drifts": drift_report["total_drifts"],
            "severity_counts": drift_report["severity_counts"],
        },
        "firms": drift_report["firms"],
        "drifts": drift_report["drifts"],
        "live_probes": live_probes,
        "output_written": False,
    }

    if not dry_run:
        payload_to_write = {**report, "output_written": True}
        atomic_write_json(output_path, payload_to_write)
        report["output_written"] = True

    return sanitize_payload(report)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Naqex Prop Terms & Black Friday Drift Radar (read-only, OrderSend=0)."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--offline",
        action="store_true",
        help="Run 100%% offline against verified snapshot/fixture (default).",
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Also run bounded read-only public HTTPS probes on official T1 domains.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute report without writing `.runtime/automation/prop_terms_radar_latest.json`.",
    )
    parser.add_argument(
        "--firms-catalog",
        default=str(DEFAULT_FIRMS_CATALOG),
        help="Path to SSOT firms_catalog.json.",
    )
    parser.add_argument(
        "--pricing-catalog",
        default=str(DEFAULT_PRICING_CATALOG),
        help="Path to SSOT prop_pricing_catalog.json.",
    )
    parser.add_argument(
        "--snapshot",
        default=None,
        help="Optional JSON snapshot file to compare against SSOT.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output JSON path for latest radar state.",
    )
    parser.add_argument(
        "--now-utc",
        default=None,
        help="Override UTC clock (ISO-8601) for deterministic testing.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print full JSON report to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    enforce_read_only_invariants()
    args = _build_parser().parse_args(argv)
    mode = "live" if args.live else "offline"
    now_dt = parse_iso_utc(args.now_utc) if args.now_utc else None

    report = run_radar(
        mode=mode,
        dry_run=bool(args.dry_run),
        firms_catalog_path=args.firms_catalog,
        pricing_catalog_path=args.pricing_catalog,
        output_path=args.out,
        snapshot_path=args.snapshot,
        now_utc=now_dt,
    )

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        dl = report["deadlines"]
        ds = report["drift_summary"]
        print(
            f"[prop_terms_radar] mode={report['mode']} dry_run={report['dry_run']} "
            f"status={ds['overall_status']} drifts={ds['total_drifts']} "
            f"order_send={report['order_send_count']} spend_vnd={report['spend_vnd']}"
        )
        print(
            f"  BF Bill Lock ({dl['bf_bill_lock']['timestamp_ict']}): "
            f"{dl['bf_bill_lock']['status']} ({dl['bf_bill_lock']['hours_remaining']}h)"
        )
        print(
            f"  BF 14d Cutoff ({dl['bf_14day_payment_cutoff']['timestamp_ict']}): "
            f"{dl['bf_14day_payment_cutoff']['status']} ({dl['bf_14day_payment_cutoff']['hours_remaining']}h) "
            f"[{dl['bf_14day_payment_cutoff']['contractual_price_lock_status']}]"
        )
        for d in report["drifts"]:
            print(f"  - [{d['severity']}][{d['trust_tier']}] {d['drift_id']}: {d['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
