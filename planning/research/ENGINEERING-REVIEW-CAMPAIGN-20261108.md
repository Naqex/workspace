# Hậu kiểm campaign: đúng kết quả, giảm việc lặp, giữ tiến độ

**C1 chưa đạt; C2 còn giới hạn.** Chưa có strategy đủ bằng chứng để khuyên mua
challenge. [Campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) giữ hai tiêu chí;
report này giữ phát hiện engineering và cách tiếp tục, không thay authority.

## Những gì đã kiểm và sửa

| Lát | Phát hiện | Hành động và bằng chứng | Còn thiếu |
|---|---|---|---|
| Native execution | Asia→London2023 dừng gần cuối reference: cash checkpoint sau quyết định che canonical entry checkpoint | Trader `f8879b32`: giữ decision và kiểm cùng pending operation qua cash event; thực tế Dec2023 442.341 ticks/accounting/roundtrip đạt | Annual recovery bằng source mới đang chạy; chưa công nhận full-year fix |
| Validation performance | Mỗi validation quét lại cả history để tìm entry/exit source; pilot lại validate typed execution vừa được validate | `edbd1e5f` index chỉ trong một pass; `043656a2` reuse đúng local typed result rồi vẫn kiểm limits/risk/pilot constraints trước observer commit | Không dùng persistent validation cache, không suy speedup cả năm |
| Process/source ownership | Bản sửa isolated không thể dùng runner mặc định trỏ D: và reviewer lại import source D: | Workspace `f781550`: explicit `--source-root`, chặn đổi source sau model import, reviewer theo cùng root; test subprocess thật và negative case đạt | Runtime sản phẩm D: vẫn source cũ `78a8397f`, không rollout khi worker còn chạy |
| Metadata | JSON cha còn text Compression/recovery cũ và cap1 khác protocol2workers | Giữ file cha; [recovery](H1-ASIA-RECOVERY-20261108.md)/JSON mới ghi đúng lineage, source, cap1 và deadline. Workspace `758613b` chặn worker/deadline/parallel vượt registration trước preparation/dispatch;5negative cases đạt | Không tự parse free-text protocol để làm authority; old runtime giữ code đã load, không retroactively nhận guard mới |
| Preparation | Recoveryv2 tạo xong quality/tick cache nhưng fail trước simulation vì H1 warmup cache source mới chưa có | `758613b` chuẩn bị/dedup H1 warmup trước worker. Test thực3quotes→2H1hours cho2jobs và load trước dispatch; recoveryv3 reuse quality/tick cache trong7,4s thay vì tạo lại594s | V3 mới đang chạy; counter dict của callback cũ chỉ ảnh hưởng telemetry lúc prep, đã sửa cho lượt sau và có regression |
| Trial history | Catalogue chưa ghi 6 gold policies dù outcomes đã có | Catalogue đồng bộ47records/34versions:24native FX+4MLcoarse+6metalcoarse; giữ2controls và toàn bộ negatives | Không coi34versions là34alpha độc lập; chưa có selection-adjusted proof |
| Skill | Có workflow hậu kiểm phù hợp, không cần skill mới trùng vai trò | Cập nhật reference của engineering-retrospective: source isolation, metadata inheritance và cash/decision regression | Manual workflow walkthrough; chưa independent model forward-test hoặc native package republish |

## Thời gian theo phạm vi thực sự đã đo

| Phần | Baseline | Bản mới/actual | Phạm vi |
|---|---:|---:|---|
| 6 flat advance windows, state có6.832 ledger events/1.022 ticks |8,89–9,02s|Indexed3,33–3,38s; thêm single-validation1,66–1,84s|Initial/final serialized SHA exact; không observer/calendar và không cả năm |
| Gold H4 long history |Chưa có A/B tương đương|117,19s wall/111,22s CPU|180rows,15annualbooks,2costs,2sizes; coarse indicative |
| Gold H1 intraday |Chưa có A/B tương đương|102,21s wall/100,86s CPU|90rows,15annualbooks,2costs; coarse indicative |
| Đọc lại3 sealed native reference states bằng current validator |Không rerun mô phỏng|0,37–0,38s/state|6.957–7.031events/state; whole-history validation/canonical roundtrip exact |
| Native annual batches |Đang chạy bằng nguồn cũ|Chưa có final wall/CPU|Không chuyển latency microbenchmark thành dự báo5× cho cả batch |
| Recovery Asia2023 |Attempt cũ lỗi ở27.223.813ticks/reference;v2prep594s rồi fail cacheH1 trước simulation|V3 reuse quality/tick7,4s rồi chuẩn bị riêng H1warmup; đọc PROGRESS|Không CLI resume giữa scenario; chưa có completed seal để reuse |
| Research/code/review toàn campaign |Không đo active time từ đầu|Unknown|Không suy từ timestamps commit hoặc cộng các khoảng chạy song song |

Private evidence root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.
`retained-ledger-optimization-v1/` giữ raw A/B; `entry-checkpoint-diagnostic-v3-fixed/result.json`
giữ regression thật; `h1-survivor-tick/recovery-v2-historical-state-compatibility.json`
giữ đọc lại3states. Three single-pass samples chưa ABBA đầy đủ; chỉ gọi là
observed latency range, không benchmark whole-product/annual được chứng nhận.

## Kiểm chứng lần tiếp tục này

- Focused product suite: `test_forex_pilot_entry.py`, `test_forex_pilot_risk.py`,
  `test_forex_financing.py`, `test_forex_horizons.py`, `test_forex_prop_candidates.py`,
  `test_replay_tick_execution.py`:77tests+66subtests đạt. Scope là timing/risk/
  accounting và retained-state guards, không edge.
- Workspace batch/evidence suite đầu:32tests+9subtests đạt, isolated-source fixture
  đầu thiếu dependency module nên một test mới lỗi. Sửa fixture copy package
  thực; hai source-selection tests đạt. Không lỗi numerical engine, không xóa
  failure để gọi lần đầu xanh. Sau H1/cache/cap changes:35tests+9subtests đạt;
 5new cap cases ban đầu dùng sai expectation return-code thay vì exception,
 sửa fixture expectation và5/5đạt; telemetry regression thêm1test đạt. Tổng
 36test cases/14subtests đã kiểm qua các lượt, không rerun unrelated suite.
- Skill environment audit:0errors/0warnings; active combined22.412bytes,
  project10.133/65.536bytes, reserve55.403bytes. Validator skill đạt bằng bundled
  Python; Python nghiên cứu thiếuPyYAML nên không cài dependency vào engine chỉ
  để chạy validator. Scoped skill links0errors.

## C1/C2 và thứ tự tiếp tục

| Gate | Hiện trạng | Bước tiếp |
|---|---|---|
| G0: protocol/trials | Có freeze/pins/trialhistory; metadata defect của parent đã ghi; execution cap có guard mới | Giữ history, không sửa registration đã dùng; legacy outcomes không được tự nâng cấp acceptance |
| G1: timing/state | Có synthetic negatives, actual failure regression và sealed-state compatibility | Chờ annual recovery; kiểm integrity/cash/horizons của đúng source |
| G2: realism | Native EURUSD có observed Bid/Ask; metal chỉ indicative M1Bid+declaredAsk; costs/spec là declared/current counterfactual | Không suy live fills hoặc historical broker realism; phải đối chiếu khi đi forward |
| G3: edge | Hai survivors coarse conditional95%interval đều chứa0, đã selection trên2023/2024 | Chưa đủ edge. Không mở holdout chỉ để kiếm một lần pass; chọn câu hỏi/hypothesis tiếp bằng lý do đã lưu |
| G4: prop/time-fit | Đang chạy tick paths3/6/12m, chưa final kết quả cả4candidate-year jobs | Review target/DD/phase/first-breach trước quyết định; không tăngrisk cứu kết quả |
| G5/G6: forward/quyền | System-demo trước đây không là strategy forward; chưa đủ C1 | Chỉ frozen qualified survivor mới đề xuất shadow/demo và gate tương ứng |

Xác nhận lại nguồn hiện hành08/11: [QuantConnect research guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide)
nhấn mạnh hypothesis/OOS/trial history; số backtests không chứng minh edge.
[FTMO EA/strategy FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/)
yêu cầu thực thi theo điều kiện thị trường và lưu ý same-EA/allocation; cho phép
EA không đồng nghĩa một bot đã được challenge-approved. Đây là refresh phương
pháp/permission context, không thay terms snapshot của registrations.

Theo dõi đúng ba locator đang hoạt động:
`h1-survivor-tick/batch-2023-v1/PROGRESS.md`, `batch-2024-v1/PROGRESS.md`,
`batch-asia-2023-recovery-v3/PROGRESS.md`. V2 giữ failure trước simulation; V3
giữ nguyên economic/source registrationv2, chỉ sửa supervisor preparation. Chỉ nhận completed_verified sau
dossier/seals/accounting. Nếu không còn ứng viên đủ economics, kết luận chưa
tìm được và chuyển hypothesis; không bảo đảm sẽ có winner sau một số vòng.
