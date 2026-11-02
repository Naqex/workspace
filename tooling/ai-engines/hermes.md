# Hermes research reviewer

Hermes is an optional worker, not a replacement for Paperclip, native workers,
RD-Agent or Quant Lab. Paperclip owns dispatch, concurrency, cancellation and task
history. Hermes uses its official `AIAgent` SDK in a native `process` adapter.
It reviews supplied evidence; it does not execute generated code or trade.

## Why the SDK

The pinned release's `hermes chat` auto-starts a detached local gateway. Its
profile works through `hermes_local`, but stopping that CLI alone does not prove
the daemon's work stopped. The SDK keeps the actual agent in Paperclip's child
process. No Hermes daemon, listener, scheduler, MCP or global Codex integration is
needed. A scoped Paperclip fix makes an explicit Hermes profile test its actual
provider instead of depending on host `python3`/`~/.hermes` discovery; that CLI
adapter is not the active worker path.

## Rebuild the local core

Source is the gitlink at `projects/integrations/hermes-agent` (MIT); this pilot
adopted release v0.22.5. Do not update it implicitly. Read its AGENTS/PM policy
before installing. The core uses Python 3.14 through upstream PM; no broad `all`
extra or upstream setup script is required for this worker. With an existing
Python that can bootstrap PM, from the Hermes checkout:

```powershell
$env:HERMES_HOME = 'D:/ANNAM/TradingWorkspace/.runtime/hermes/research'
$env:HERMES_RUNTIME_DIR = 'D:/ANNAM/TradingWorkspace/.runtime/hermes/tools'
python -c "from pm import sync_venv; sync_venv([], explicit=True)"
```

Use the existing gateway settings; the helper validates its project endpoint and
model catalog. From workspace root:

```powershell
projects/integrations/TradingAgents/.venv/Scripts/python.exe tooling/ai-engines/hermes_setup.py --company <company-id> --reports-to <existing-leader-id>
```

This prepares the ignored profile and prints the proposed worker. Add `--apply`
to create it when authorized. It refuses to replace an existing Hermes worker or
its owner settings. PM's `facts.json` supplies the selected interpreter; the SDK
loads from the pinned source checkout. No raw pip mutation of that venv.

Profile/config/plugin/session database/memory stay under `.runtime/hermes/`.
The setup helper copies the project plugin there and binds its helper import to
this workspace. Reprepare the profile after changing that plugin, with the worker
idle. The active worker reads the internal gateway key from its existing managed
config at job time, not Paperclip settings, task text or a second `.env`.

## Give it a task

Assign a 100–20,000 character description to **Chuyên viên phản biện**. Include
the evidence, its provenance, question and expected output. The bounded pilot
[dossier](hermes-pilot.md) demonstrates the format. This worker currently cannot
fetch arbitrary websites or source files; put the required excerpt in the task.
For the [linked spot workflow](README.md#a-linked-crypto-spot-workflow), the wrapper
instead resolves its typed `naqex-review` dependency through the native API,
verifies its run/receipt/document hashes, and supplies the bounded numeric dossier.
Task text still cannot provide arbitrary artifact paths or source commands.

Only `research_publish`, `memory` and `session_search` are exposed. Progressive
tool discovery is off so the inventory is explicit and checked before inference.
No terminal/files/code/delegation/cron/broker tools. This is a capability limit,
not an OS security sandbox. Memory is provisional research context, not an
accepted strategy, a sealed holdout or a global instruction store. It is separate
from Codex and other workers; skills are not promoted automatically.

The report tool attaches a native document; the worker marks the issue done only
after the model turn completes and attachment succeeds. Artifact directories are
unique per native run. Failure or hard cancellation preserves available evidence;
a remaining `running` receipt is interrupted/unknown, not success. No wrapper
retry, alternate provider, automation or trading authority is enabled. Main API
attempts are bounded by upstream configuration (six iterations, 180s agent budget,
240s process deadline); this is not a money budget or guarantee that remote
provider computation can be undone after cancellation.

Evidence/benchmark and remaining limits extend the existing
[integration receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md).
Remove/pause this worker through native Paperclip to disable it; retain its
reports and profile until the owner chooses to delete them. Existing engines
continue independently.
