# Engine jobs in native Paperclip

Paperclip owns task assignment, run concurrency, process timeout/cancellation and
task history. The native `process` adapter calls `engine_worker.py`. The wrapper
accepts a bounded request and uses upstream TradingAgentsGraph and its report
exporter. It does not patch an upstream engine or use a general shell tool from a
task. Studio continues to embed native Paperclip UI.

## One analysis

In Paperclip, create a task assigned to **Chuyên viên phân tích**. Use a title
such as **Phân tích BTC — kỹ thuật và tin tức** and put this block in its
description (adjust the date before running):

````text
```naqex-engine
{
  "version": 1,
  "engine": "tradingagents",
  "symbol": "BTC-USD",
  "as_of": "2026-11-01",
  "asset_type": "crypto",
  "analysts": ["market", "news"]
}
```
````

Supported asset types: `crypto`, `stock`. Analysts: `market`, `news`, `social`,
and `fundamentals` for stocks only. Forex/MT5 is not connected through this
adapter. The requested date and upstream provenance are retained; this is a
market analysis, not an independently validated strategy or an execution signal.

Successful jobs attach a native Markdown document to the task and mark the task
done. A failure leaves the task blocked with an actionable document. Each attempt
has a separate document and artifact directory; it never overwrites earlier
attempts. Interrupted calls are not resumed automatically. Native process
cancellation stops work; receipts may retain `running` after a hard kill, which
means interrupted/unknown, not success. Check the Paperclip run before retrying.
Duplicate dispatches of the same run leave its existing task and receipt untouched.
The task description is the request: conversational follow-ups do not replace its
typed block. Edit that block or create a new task for a different analysis.

## Settings and setup

Private operator settings live outside Git, normally
`.runtime/ai-engines/settings.json`. They contain only model IDs and paths:

```json
{
  "version": 1,
  "artifact_root": "E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs",
  "gateway_config": "<absolute path to existing project managed.yaml>",
  "quick_model": "<existing Gemini model ID>",
  "deep_model": "<existing Gemini model ID>"
}
```

Credentials are read from the existing project gateway config at job time, not
copied into this file, Paperclip adapter config or task text. The endpoint must
match the project port registry. Host provider credentials, tracing and upstream
config environment variables are removed. Current expired Opus5.5 routes are
rejected. Renewing that route requires reviewing this explicit local guard.

Use the existing TradingAgents venv; do not install this wrapper as another app.
Preview provisioning first, then use `--apply` when authorized:

```powershell
projects/integrations/TradingAgents/.venv/Scripts/python.exe tooling/ai-engines/paperclip_setup.py --company <company-id> --settings <private-settings>
```

The setup helper creates only missing workers, never replaces an owner-created
agent or chooses another company. New workers start paused in this Paperclip pin;
resume the analysis worker in native UI after checking the model/gateway. Keep the
research worker paused. Timer heartbeats are disabled; assignment and
explicit wake can run the analysis worker. Each job uses isolated cache/memory,
one debate round and one risk round, bounded tool rounds, no SDK retries and a
15-minute native process deadline. No shared memory crosses independent jobs.
No daily spending/run limit is enforced by this wrapper; concurrency and timeout
are not a budget cap.

## RD-Agent boundary

The research worker remains **paused**. On 02 November 2026 the owner authorized
runtime installation. WSL2 distro `NaqexResearch` now has Ubuntu 24.04, Docker
Engine and RD-Agent 1.0.0 built from the existing gitlink. Package/CLI, Docker
SDK and container smoke passed; Docker autostart, Windows drive automount and
Windows interop are disabled in this dedicated distro. See the
[runtime guide](rd-agent-runtime.md) for ownership, commands and evidence.

An operator-triggered [synthetic factor pilot](rd-factor-pilot/README.md) passed
on 02 November: one Gemini-generated candidate, real upstream FactorFBWorkspace
and five evaluators, independent oracle, causal invariance and failure controls.
Generated code ran in a bounded offline container. This is not the full finance
loop, a real-data backtest, strategy qualification or native Paperclip dispatch.

Next gate: real-data adapter with point-in-time provenance, bounded finance-loop
contract and native dispatch/cancellation qualification. The current adapter
still refuses RD-Agent jobs. Its source remains pinned under
`projects/integrations/rd-agent`; do not install its broad dependencies into the
TradingAgents venv. Numeric strategy validation remains owned by Quant Lab.

## Verification

```powershell
projects/integrations/TradingAgents/.venv/Scripts/python.exe -m unittest discover -s tooling/ai-engines/tests -v
```

Acceptance/receipts extend the existing
[AI integration checkpoint](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
Source setup, a real Paperclip dispatch, actual model success and strategy
validation are separate results.

The first real job is [NAQ-4](http://127.0.0.1:17860/NAQ/issues/NAQ-4),
using requested route `gemini-3.8-flash-high`. This identifies the gateway route,
not independent proof of the provider's underlying model. Open the report link in
the task conversation to read the native document. Model narratives, prices and
arithmetic still need independent checks; requested dates alone do not prove
point-in-time data or a completed daily candle.
