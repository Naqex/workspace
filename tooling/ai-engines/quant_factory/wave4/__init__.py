"""Total Offensive #4 Dev-only (<= 2024-12-31) quantitative & AI modules.

Hard invariants:
  - HOLDOUT_CUTOFF_DATE = "2024-12-31" (Holdout 2025+ SEALED, holdout_rows_analysed = 0)
  - ORDER_SEND_CAPABLE = False (OrderSend = 0, offline research/audit only)
  - MAX_OFFICIAL_API_USD_PER_MONTH = 5.0 (hard official API spend ceiling)
"""

from __future__ import annotations

HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
ORDER_SEND_CAPABLE: bool = False
MAX_OFFICIAL_API_USD_PER_MONTH: float = 5.0

__all__ = [
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "MAX_OFFICIAL_API_USD_PER_MONTH",
]
