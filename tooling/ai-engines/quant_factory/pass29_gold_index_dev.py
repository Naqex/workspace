"""Backward-compatible re-export shim for `experiments/pass29_gold_index_dev.py`."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_AI_ENGINES_DIR = str(Path(__file__).resolve().parents[1])
if _AI_ENGINES_DIR not in sys.path:
    sys.path.insert(0, _AI_ENGINES_DIR)

if __name__ == "__main__":
    runpy.run_module("experiments.pass29_gold_index_dev", run_name="__main__")
else:
    import experiments.pass29_gold_index_dev as _impl

    sys.modules[__name__] = _impl
