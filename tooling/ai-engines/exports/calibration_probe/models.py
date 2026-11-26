"""Core exception and data models for FTMO-Demo calibration probe."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SafetyLockError(RuntimeError):
    """Raised whenever any of the 6 fail-closed safety invariants is violated."""


class RedactedCredentials:
    """In-memory credential container that strictly redacts passwords on formatting."""

    __slots__ = ("login", "server", "terminal_path", "_password")

    def __init__(self, *, login: int, password: str, server: str, terminal_path: Path) -> None:
        self.login = int(login)
        self._password = str(password)
        self.server = str(server)
        self.terminal_path = Path(terminal_path)

    def secret_password(self) -> str:
        return self._password

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "login": self.login,
            "server": self.server,
            "terminal_path": str(self.terminal_path),
            "password": "***REDACTED***",
        }

    def __repr__(self) -> str:
        return (
            f"RedactedCredentials(login={self.login}, server={self.server!r}, "
            f"terminal_path={str(self.terminal_path)!r}, password='***REDACTED***')"
        )

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(frozen=True)
class PlannedCalibrationTrade:
    seq: int
    symbol: str
    side: str
    volume: float
    sl_units: float
    hold_sec: int
    gap_sec: int
