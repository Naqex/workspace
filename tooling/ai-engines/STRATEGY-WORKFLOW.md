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

Khung/checklist theo stage ở
[validation gates](../../.agents/skills/strategy-qualification/references/validation-gates.md),
căn cứ và current gaps ở [framework audit](../../planning/research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
Protocol/data/source hashes và exit0 không tự chứng minh preregistration timing,
causality, OOS hoặc prop fit. Dossier `review_checks` tách mechanical checks khỏi
phần chưa được tool đánh giá; dùng bảng gate/evidence trong mọi đề xuất đổi stage.

## Preflight cùng runner

Trước đổi window, dùng `research_consumption.py --root <explicit-root>` (lặp
`--root` khi cần) `--output <new-audit.json>` để inventory bounded JSON metadata.
Không mở CSV, không đi theo directory links ra ngoài root, không xuất PnL/quotes;
vẫn parse toàn JSON trong size limit. Output ghi coverage gaps và phân biệt
planned registration với executed-run metadata. Absence không chứng minh unseen,
record có dates cũng không tự chứng minh đã xem giá. Owner history chưa rõ thì
ghi unverified. [Protocol hiện hành](../../planning/research/PROP-HISTORICAL-ROBUSTNESS-20261105.md)
giữ nhãn/cutoff/tiêu chí/pins của bài kế tiếp. Runner đã có opt-in registration
support và synthetic integration evidence theo receipt; chưa có market run mới.
Không đổi dates để vượt guard2022 hoặc tự gọi registration là quyền holdout.

Để chạy registration đã hỗ trợ, thêm `--study-registration <registration.json>
--study-registration-sha256 <registered-hash>` cùng candidate/input/protocol/spec.
Batch job config dùng `study_registration` và `study_registration_sha256` để
forward đúng pair đó; trước dispatch kiểm pin/role/candidate. Dossier nhận schema
historical riêng, giữ exposure unverified và không auto-promote. File registration
freeze cũ không sửa để cập nhật trạng thái; receipt/implementation binding giữ delta.

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

### Batch development hữu hạn trên Windows

`forex_study_batch.py --config <registered-config.json> --output-dir <batch-dir>
--max-workers 3 --worker-seconds 1800 --deadline-seconds 5400` chạy bằng Python
venv Trader đã có. Config giữ từng candidate/input manifest/protocol/hash/spec
và tick count đã đăng ký, không nhận command/provider/broker tùy ý. Đọc lại
protocol cho phép deadline/concurrency trước chạy; các số trên là trần của
đợt Q1 hiện tại, không phải ETA hoặc default nghiên cứu chung.

Candidate đầu chạy một mình trước; sau khi kiểm kết quả mới mở đủ số slot.
Supervisor dùng lại Windows JobObject của runtime với stdin gate, interpreter
thật và import paths của venv: child không làm nghiên cứu trước khi thuộc job.
Cancel/timeout/crash đóng cả cây; `CANCEL` trong batch-dir dừng việc chưa xong.
Không cần terminal MT5, Paperclip service hoặc model cho batch offline này.

`progress.json`/`PROGRESS.md` cập nhật5giây từ worker receipt và terminal riêng.
Exit0 chỉ được `completed_verified` sau dossier/accounting/bindings check.
Chạy lại đúng config/output sẽ kiểm và reuse **job đã hoàn tất**, không chạy lại
chúng. Job chưa xong/lỗi cần attempt mới có chủ đích; giữ thư mục cũ, không tự
retry/overwrite hoặc gọi đây là resume giữa mô phỏng. Lock còn sau crash phải
đối soát process và artifacts trước xử lý, không tự xóa để chạy đè.
`--reuse-from <older-batch-dir>` cho một attempt mới kiểm và tham chiếu các job
đã hoàn tất của batch cũ; các job cũ failed/partial không được reuse. Result
locator từng hàng ở `progress.json` có thể trỏ về batch cũ; không copy hoặc ghi
đè artifacts đó. Supervisor failure có source frames và terminal riêng; projection
cũ còn `running` phải đối soát, không tự kết luận worker còn sống.

Job config có thể đặt `reuse_scenarios_from` thành đường dẫn `replay` của attempt
đã dừng để CLI kiểm và dùng lại scenario có completed seal. Output luôn mới;
không tự retry failed job và không sửa raw attempt cũ. Thiếu seal hoặc mismatch
là lỗi rõ ràng, không âm thầm tính lại toàn bộ. Đây là scenario-boundary reuse,
chưa phải restore giữa simulation. Legacy outputs và source-version drift cần
review riêng, không tự công nhận tương đương. Xem
[contract runner](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md#reuse-a-completed-scenario-after-interruption).

## Dossier từ artifact

Status/log/failure conventions: [observability](OBSERVABILITY.md).
`strategy_evidence.py status --run-dir <attempt>` đọc progress và last-update age,
không xác minh process sống hoặc tự restart job.

```powershell
python -X utf8 tooling/ai-engines/strategy_evidence.py inspect --run-dir <completed-study-dir>
```

`--verify-inputs` hash CSV khi cần integrity check; `--source-root <foundation_v2>`
so source hiện tại. Drift không xóa evidence lịch sử, chỉ hạn chế tái hiện.
Tool kiểm invariants/bindings, không thay core accounting, statistical review
hoặc chứng thực nguồn artifact. Không overwrite run hoặc sửa ledger để tự pass.
Development dossier luôn `promotion_authorized:false`, kể cả PnL dương.
Historical-robustness dossier cũng giữ false và không tự thành clean OOS.
Reuse completed job/scenario cần khớp Python/Pydantic/Decimal binding ngoài
source/input/protocol/cost. Environment cũ chưa ghi thì không tự suy tương đương.
Không tính maxDD từ minimum equity rời rạc; giữ open PnL và coverage rõ.

## Risk và concurrency

Trước ưu tiên candidate cho prop, dùng
[time-fit research](../../planning/research/PROP-FIRM-FIT-20261102.md#thời-gian-challenge-và-độ-phù-hợp-chiến-lược--kiểm-lại-05112026)
để pin deadline/activation/inactivity, minimum trading/profitable days, hold/news,
phase reset và payout riêng theo program/version. Đăng ký horizons kinh tế và
time-to-target trước outcome; báo chưa đạt trong observation hoặc unknown khi
thiếu coverage, không ngoại suy tuyến tính/tăng lot/thêm lệnh cho đủ ngày.
Đây là yêu cầu thiết kế/review bài kế tiếp, **chưa là full lifecycle code guard**;
loss-floor evaluator hiện có không chứng minh pass hai phase hoặc time-to-payout.

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
