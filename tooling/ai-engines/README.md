# Engine jobs in native Paperclip

The optional [Hermes reviewer](hermes.md) uses its official SDK in another native
process worker. Keep TradingAgents, RD-Agent and Quant Lab in their current roles;
Hermes reviews evidence and maintains its own research notes.

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
research worker paused until its registered data/runtime preflight passes. Timer heartbeats are disabled; assignment and
explicit wake can run the analysis worker. Each job uses isolated cache/memory,
one debate round and one risk round, bounded tool rounds, no SDK retries and a
15-minute native process deadline. No shared memory crosses independent jobs.
No daily spending/run limit is enforced by this wrapper; concurrency and timeout
are not a budget cap.

## RD-Agent boundary

On 02 November 2026 the owner authorized
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

The registered `crypto-momentum-3d-v1` workflow subsequently completed as
[NAQ-6](http://127.0.0.1:17860/NAQ/issues/NAQ-6): fixed historical BTC/ETH daily
snapshot, one Gemini candidate, RD-Agent factor checks and Quant Lab prefix
walk-forward/cost stress. Native cancellation was separately verified without
a provider call. The research worker is now idle with timer heartbeats off.
This adapter runs a fixed formula verification workflow, not unrestricted
RD-Agent hypothesis search or the full `fin_factor/fin_model` loop. Its source remains pinned under
`projects/integrations/rd-agent`; do not install its broad dependencies into the
TradingAgents venv. Numeric strategy validation remains owned by Quant Lab.

### Registered research task

Assign this description to **Chuyên viên nghiên cứu**:

````text
```naqex-engine
{"version":1,"engine":"rd-agent","experiment":"crypto-momentum-3d-v1"}
```
````

The task cannot supply a path, command, provider, alternative formula or model.
The registered [contract](rd-factor-pilot/market-contract.json) fixes assets,
window, formula and costs before each run. To add a different research question,
review a new contract before exposing it to the worker; do not tune on the
published OOS results. Reassigning a new task starts another provider attempt;
there is no automatic retry, strategy promotion or budget cap in this wrapper.

Operator setup (not task input): prepare a **new** snapshot directory using the
existing public-data client; no account/key is needed for data:

```powershell
projects/integrations/TradingAgents/.venv/Scripts/python.exe tooling/ai-engines/rd_research.py prepare --directory <new-absolute-snapshot-directory>
```

After reviewing quality/source/cutoff, add `rd_agent` to the existing private
settings, alongside the original five fields:

```json
{
  "dataset_manifest": "<absolute snapshot directory>/manifest.json",
  "manifest_sha256": "<verified manifest SHA256>",
  "image_id": "sha256:<verified immutable locally built Docker image ID>"
}
```

Copy that object under `rd_agent`; no credential belongs in it. Source/imports
use the existing clean Quant Lab checkout; numerical libraries already exist in
the TradingAgents venv, with no new package installation. Each dispatch verifies
snapshot hashes and quality again, then makes one Gemini request. The isolated
Linux controller runs the bounded candidate; Quant Lab compares its exact
factor to an independent oracle and replays the equivalent trusted signal on
chronological prefixes. Public historical snapshots are not guaranteed revision
vintages and are not a sealed final holdout. The last partial fold is reported
as unused, not silently included.

The WSL guardian holds an exclusive runtime lease, refuses an already-active
Docker daemon, and revokes work on EOF/stale heartbeat. Cancellation removes
only containers with its job label and stops services it started. It never uses
`wsl --shutdown`; do not terminate the distro while another job owns it. On a
hard kill, inspect native run status and both Windows/Linux receipts before
retrying; never infer success from an artifact folder alone.

Successful research jobs publish **Kết quả nghiên cứu** and **Dữ liệu và kiểm
chứng** as native documents; failure leaves artifacts and blocks the task. The
numeric evidence contains cash/buy-hold baselines, full metrics, hashes, model
route and source versions. Successful workflow completion does not mean the
strategy qualified for demo or live. Historical NAQ-6 is a successful workflow
with an unqualified candidate; do not rerun it simply to obtain a better result.

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
