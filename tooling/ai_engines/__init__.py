"""Module entrypoints for the existing historical ai-engines directory."""
from pathlib import Path
import sys

_implementation = str(Path(__file__).resolve().parent.parent / "ai-engines")
__path__.append(_implementation)
if _implementation not in sys.path:
    sys.path.insert(0, _implementation)
