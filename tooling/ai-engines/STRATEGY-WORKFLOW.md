# Workflow chiến lược

[AI plan](../../planning/trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md) giữ scope;
[receipt](../../planning/checkpoints/ai-integrations-20261031/RECEIPT.md) giữ
bằng chứng. Paperclip own task/run/report; không thêm tracker/UI riêng.

| Chặng | Skill/tool | Bàn giao |
|---|---|---|
| Ý tưởng/spec | [strategy-research](../../.agents/skills/strategy-research/SKILL.md), research index | Candidate/version, hypothesis, nguồn/license/unknowns |
| Rule/data/risk | Profile/spec/QDM/validator hiện có | Program/phase, source date, cost/risk/consumed map |
| Code/check/run | Opt-in runner/tests/preflight | Manifest/quality/results/receipt/decisions |
| Qualification | [strategy-qualification](../../.agents/skills/strategy-qualification/SKILL.md), `strategy_evidence.py inspect` | Correctness/edge/prop/operations/authority và next stage |
| Shadow/demo/operate | [Studio](../../.agents/skills/studio-operations/SKILL.md), runtime/grant/lifecycle | Binding/quote/risk/reconciliation/recovery |
| Context/skills | [evidence continuity](../../.agents/skills/evidence-continuity/SKILL.md), [maintenance](../../docs/development/SKILL-MAINTENANCE.md) | Locator/revision/delta, không copy ledger/raw logs |

Không cần agent/task riêng mỗi hàng. Fixed process worker không tự nhận câu hỏi
mới từ Markdown; coding agent chạy study riêng, lead delegate theo capability.

## Preflight cùng runner

Từ `projects/trader/foundation_v2`, Python `.venv` đã có:

```powershell
& .venv/Scripts/python.exe scripts/forex_h4_pilot.py --input-dir <input-root> --input-manifest <pinned-inputs.json> --output-dir <new-preflight-dir> --candidate <registered-id> --research-protocol <protocol.md> --preflight-only
```

Giữ account-spec/hash nếu có như [runner guide](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md).
Output mới chặn hai writer cùng attempt, không chứng minh dedup mọi job ở các
output khác nhau. Preflight kiểm contract/hash/coverage/warmup và account fields
được hỗ trợ; không simulation/orders/OOS mới. Nó đọc development để kiểm data
nên phải ghi consumption. Output chỉ manifest/quality/receipt, không results.
Run thật dùng output khác; không lặp preflight bên ngoài khi runner đã thực hiện
cùng checks và inputs không đổi. Không sửa hash để ép input đạt.

## Dossier từ artifact

```powershell
python -X utf8 tooling/ai-engines/strategy_evidence.py inspect --run-dir <completed-study-dir>
```

`--verify-inputs` hash CSV khi cần integrity check; `--source-root <foundation_v2>`
so source hiện tại. Drift không xóa evidence lịch sử, chỉ hạn chế tái hiện.
Tool kiểm invariants/bindings, không thay core accounting, statistical review
hoặc chứng thực nguồn artifact. Không overwrite run hoặc sửa ledger để tự pass.
Development dossier luôn `promotion_authorized:false`, kể cả PnL dương.
Không tính maxDD từ minimum equity rời rạc; giữ open PnL và coverage rõ.

## Risk và concurrency

Source audit05/11: Trader `api-rust/src/automation_grants.rs::create_grant` khóa
workspace/server/login, chặn execution owner trùng; transaction giữ attempts/
reservations, unknown không release. Research/observation có thể song song;
nhiều strategy cùng account phải qua cùng owner/budget, không nhân grants.
Đây là source-confirmed boundary, không là portfolio allocator/correlation
model hoặc runtime acceptance hôm nay. Không thêm engine risk cạnh tranh.

## Skill consumers

`paperclip_strategy_skills.py` preview/bundle source và sync qua native API;
mặc định không ghi app. Attach research/qualification cho native lead phù hợp,
không gắn process worker/đổi permission của họ. Không start service hoặc gọi
model chỉ để test instruction. Runtime unavailable thì giữ bundle/receipt,
resume publish qua API, không ghi trực tiếp DB. Xem [operations](OPERATIONS.md).
