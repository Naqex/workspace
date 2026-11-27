# Naqex Reusable Antigravity Workflows (`tooling/workflows/`)

Reusable Python orchestration scripts for the Antigravity `run_workflow` tool (using native primitives: `phase`, `agent`, `parallel`, `pipeline`, `call_tool`, `log`, `args`, and `WORKSPACES`).

## Hard Invariants & Mode-A Safety Rules

Every script in this folder enforces fail-closed invariants (explicit `if ...: raise`, zero bare `assert`s):

- **Zero live execution & zero spend:** `spend_vnd = 0`, `OrderSend = 0`, `MT5_PROCS = 0` on PC Dev, zero broker/VPS mutations.
- **Holdout `2025+` SEALED:** `holdout_cutoff_utc = "2025-01-01T00:00:00Z"` and `holdout_rows_analysed = 0` across all Dev research/audit sweeps.
- **PC Dev `MODE_A_OWNER_ACTIVE` discipline:**
  - NEVER run `pytest -n auto` (cap workers at `-n 2` or single-process).
  - NEVER run `uv run` in the root `TradingWorkspace` repo — always invoke `.runtime/quant-audit-v24/Scripts/{python,ruff,ty,pytest}.exe`.
  - Keep `AGENTS.md` immutable (`10,901 B`, `+0 B`) and never run `git commit` / `git push` from read-only workflow scripts.
- **OPSEC & hygiene:** zero raw LAN/Tailscale IPs, zero hardcoded local Windows profile paths (`C:\Users\<USER>` placeholders only), zero live tokens/webhooks, zero bare currency symbols in Markdown prose (`USD`/`VND` only), LF-only (`\n`).

## Available Workflows

| Script | Purpose | Safety Profile |
|---|---|---|
| `audit_19_gates.py` | Read-only 19-gate adversarial siege audit covering all 19 Mandatory Gates of Total Offensive #2 v2.5 (5 CI scripts, `strategy-intel` 4/4 guards, `quant_core` 41/41, `<X13_WORKER>` receipt, OPSEC, Gitleaks, immutables, budgets). | Read-only (`workspace="inherit"`), `OrderSend=0`, `Holdout=0`. |
| `pareto_strategy_sweep.py` | Multi-agent Dev-only (`<= 2024-12-31`) strategy Pareto frontier & 7-angle adversarial red-team audit template enforcing Law-15 balanced reporting (`Đậu + Rớt + Chờ = 100%`). | Dev-only (`<= 2024-12-31`), `holdout_rows_analysed=0`, `OrderSend=0`. |

## Invocation via `run_workflow`

Invoke either script by passing its absolute `ScriptPath` and optional JSON `Args`:

```json
{
  "ScriptPath": "d:/ANNAM/TradingWorkspace/tooling/workflows/audit_19_gates.py",
  "Description": "Run Total Offensive #2 v2.5 read-only 19-gate adversarial audit",
  "Args": {
    "mode": "MODE_A_OWNER_ACTIVE",
    "max_workers": 2,
    "run_x13_probe": true,
    "run_gitleaks": true,
    "strategy_intel_dir": "D:/ANNAM/strategy-intel"
  }
}
```

```json
{
  "ScriptPath": "d:/ANNAM/TradingWorkspace/tooling/workflows/pareto_strategy_sweep.py",
  "Description": "Run Dev-only (<= 2024-12-31) Pareto strategy sweep and red-team audit",
  "Args": {
    "dev_cutoff_utc": "2024-12-31",
    "target_max_shock_dd_pct": 4.5,
    "max_workers": 2,
    "model_tier": "flash"
  }
}
```

## Static Checking Note (`top-level await`)

Antigravity `run_workflow` scripts execute with top-level `await` and runtime-injected symbols (`agent`, `parallel`, `pipeline`, `phase`, `call_tool`, `log`, `args`, `WORKSPACES`). Because standard `ast.parse()` and Ruff reject top-level `await`:

- `pyproject.toml` lists `"tooling/workflows"` in `[tool.ruff].extend-exclude`.
- `tooling/check_architecture.py` excludes `tooling/workflows/` from standard AST scans.
- Syntax-validate workflow scripts offline with Python's top-level await compiler flag:

```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe -c "import ast, pathlib; [compile(p.read_text('utf-8'), str(p), 'exec', ast.PyCF_ALLOW_TOP_LEVEL_AWAIT) for p in pathlib.Path('tooling/workflows').glob('*.py')]; print('OK')"
```
