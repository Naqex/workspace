# R061: source đúng trong scope, SMA pilot chưa được giữ

Theo [frozen protocol](NASDAQ100-H4-SMA-PROTOCOL-20261108.md), commits
`d2eb1b1`/`e63077d` trước outcome. 4books đã terminal và separate-Fraction
review đạt trong coarse H1scope. **Không giữ exactrecipe cho qualification
ở lượt này; chưa có challenge candidate.** Không loại cả NASDAQ/SMA family.

## Kết quả dễ đọc

Mỗi year bắt đầu10.000USD, plannedstop25USD/lệnh; financing/slip declared,
không target broker terms. Thay đổi equity gồm mark vị thế mở, không forceclose.

| Developmentyear | Reference netUSD | Stress netUSD | Closed trades /cost | Cuối mẫu |
|---|---:|---:|---:|---|
|2019|+340,47|+240,59|7|1BUY mở, floating+150,97/+146,42USD|
|2022|−35,51|−77,36|14|Flat|

2019balance+189,50/+94,17USD, financing91,17/179,83USD;2022financing39,93/
80,58USD. Hai costs không là samples độc lập. Stress2019≈+2,41%,2022≈−0,77%
trên vốn10k; không đủ để suy days-to-target hoặc xác suất pass/payout.
Year2019mark31/12/2019 22UTC, year2022mark30/12/2022 22UTC; không giả quote
cuối lịch. Funding vẫn theo calendar tới endexclusive như protocol.

Frozen retention cần cả2stressyears dương và>=20closedtrades/year: không đạt
cả hai. Ngưỡng20 là filter riêng pilot, không chuẩn thống kê chung; kết quả
íttrades chủ yếu nói evidence hạn chế, không chứng minh strategy không cóedge.
Không tăng risk/giảmfees hoặc retune SMA/SL để cứu exactversion.

## C1/C2: đã biết gì, còn thiếu gì?

| Lát | Bằng chứng/kết luận |
|---|---|
| G0 registration/trials | One recipe×2years×2costs, source exposure/dates/known-at giữ rõ; không cleanOOS |
| G1 source/signal | 13focusedfixtures trước numeric; pilot/historyreview từ đợt trước; separateFraction tự dựng5.124H4decisions,42closedtradechecks/4books khớp |
| G2 model/accounting | Exact cents/quantity/stops/cash/float/funding/events khớp; ATR/difference Fraction vs Decimal28 tolerance<1e−21. 5mutations price/time/missingdecision/funding/falseauthority reject |
| Missing-path realism | 171gap events/cost2019,119/cost2022 khi holding; 2019 có unobservedfinaltail. Closures/unknownfeedgaps, không tự chứng nhận outage. Stops/funding trong gap là modeldependent, không actual first-crossing proof |
| Economics | Không đạt frozenfilter;20trades threshold không tạo statisticalcertificate. Không gọi registeredfilterfail là bác bỏ toànfamily |
| G3/G4/G5 | Chưa cleanOOS, targetcontract/dividend/swaps/tickpath/prop/time-fit/prospective; không claim challenge ready |
| G6 | Brokercalls0,modelcalls0,executionauthorityfalse; không account/provider/holdout mới |

Reviewer cùng agent/provider nhưng khác implementation/arithmetic, không
independenthuman/model/feed audit. H1Open là intervalproxy, không timestamp
khớp thực; không coi tốc độ này là speedup native replay cùng độ chính xác.

## Hậu kiểm kỹ thuật và dữ liệu

| Phần | Thực đo /vấn đề | Quyết định |
|---|---|---|
| Preflight v1 | PID16044 chặn nhầm reviewer-sourcehash với receipt;0numericbooks | Giữ failure/driver gốc, bind đúng2loại ởv2. Không đổi source/rules/costs |
| Fixture ban đầu | Crossednegative còn vi phạm OHLC trước guard đích | Sửa fixture giữ OHLC hợp lệ,13tests đạt trước PnL |
| Producer v2, bao gồm load/hash/preflight/4books |1,728swall/1,672sCPU; từngsimulate0,241–0,284s | Reuse8sealedbooks, không network/parse fulltick/history rerun |
| Fraction reviewer v2 |1,934swall;4books/5.124decisions/42trades/5mutations | Đủ coarse arithmetic scope, không thêmGPU/Rust/framework |
| Research/code/human time | Chưa có active timer | Không cộng3,66s thành toàn thời gian từý tưởng tới kết luận |
| Data contracts | Raw source → sealed source-only BidAsk books → pinned H4recipe/cost → result/review | Giữ source ID, UTC/ms/grid, roles/known-at/exposure, immutableattempts và schema/quality/hash; không migration/xóa |
| AX/retrieval | Catalogue61records/44researchversions, source+implementation+negatives có liên kết | Đọc numericalJSON bằng code; search chỉ tìm tài liệu. Không cần vectorDB/embeddingticks hoặc skill mới |

Không lỗi numerical/material mismatch trong scope kiểm. Module mới là
workspace offlineprototype `tooling/ai-engines/nasdaq_h4_study.py`, reuse
canonical ATR/protective/size/financial primitives. Product/runtime không đổi.
Giữ exact instrument identity, không đưa NASDAQ qua US500/XAUguards.

## Evidence và resume

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/nasdaq-h4-sma-v1`: preflightfailure, chưa numeric; không reuse
  như một completedrun hoặc overwrite.
- `execution-v1/nasdaq-h4-sma-v2`:4books,config/manifest/source-snapshot/
  preflight/result/review/progress/events. PID20328 terminal0, reviewerterminal0.
- `run-nasdaq-h4-sma-v2.py`, `review-nasdaq-h4-sma-v2.py`: frozen snapshots
  trong attempt. ResultSHA`4717afa18e3c9f97028213a9bc8ef22d4b74cc93159507128e0e2c922dc8cbaf`;
  manifestSHA`cdfb9ed744095cf8dc65b44aab4a93bcefb73395326c4b970a775a25f519e7e6`.
- Source/yearbooks và56rawbindings giữ ở historyattempt cũ; không tải lại.

Goal C1/C2 vẫn active. Lát tiếp phải là methodadmission của cơ chế có khả
năng áp dụng khác crossover dài ngày này: so mechanism/clock/data/cost/holding
và novelty với catalogue trước freeze tối đa1–2recipes. Không default nhân
biến thể Nasdaq/SMA hoặc grid20/80/ATR để Goal bận. Tick/targetcost/prop check
chỉ dành cho hypothesis đủ bằng chứng hoặc một phép kiểm bias được đăng ký,
không chạy annualticks cho version failfilter chỉ để có thêm batch.
