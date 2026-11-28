"""Total Offensive #5 Dev-only (<= 2024-12-31) closed-loop alpha factory & compute modules.

Hard invariants:
  - HOLDOUT_CUTOFF_DATE = "2024-12-31" (Holdout 2025+ SEALED, holdout_rows_analysed = 0)
  - ORDER_SEND_CAPABLE = False (OrderSend = 0, offline research/audit only)
  - DEV_PC_REQUIRED_MODE = "MODE_A_OWNER_ACTIVE" (2-3 cores BelowNormal 0x4000, 0% GPU)
  - X13_WORKER_POLICY = "FULL_PERFORMANCE" (all cores, AC-only, silent fallback to PC Dev Mode A)
"""

from __future__ import annotations

HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
DEV_CUTOFF_SEC: int = 1_735_689_600  # Exclusive upper bound: 2025-01-01T00:00:00Z
ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
DEV_PC_REQUIRED_MODE: str = "MODE_A_OWNER_ACTIVE"
X13_WORKER_POLICY: str = "FULL_PERFORMANCE"

__all__ = [
    "DEV_CUTOFF_SEC",
    "DEV_PC_REQUIRED_MODE",
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "X13_WORKER_POLICY",
]
