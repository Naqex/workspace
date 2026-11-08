# R019: đã code và kiểm, chưa có lợi thế để ưu tiên challenge

Thực hiện [protocol](PRIOR-DAY-RETEST-PROTOCOL-20261108.md), commit `47407d1`;
`73e62ff` làm rõ warmup toàn bộ Nov–Dec trước outcomes. Native implementation
ở Trader `83731fc8`. **Không đạt stage1, chưa mở full-history batch.**

## Cách hiểu đơn giản

Bản cũ vào ngay sau khi giá đóng cửa vượt đỉnh/đáy ngày trước. Bản mới chờ
tối đa ba giờ để giá quay lại chạm mức đó, rồi đóng cửa giữ phía breakout.
Nếu quay ngược, mất nến hoặc hết giờ thì hủy; chỉ một lần thử/ngày.

Retest làm ít lệnh hơn nhưng **không cải thiện kết quả ở hai năm đã thử**.
Đây là giả thuyết riêng của project, không phải recipe đã được NYFed chứng
minh hoặc một paper replication. Không chỉnh thời hạn chờ/SL sau outcome.

## Kết quả paired2019/2022

Mỗi năm bắt đầu lại10.000USD, planned25USD/lệnh (0,25%initial), minstep0,01,
SL1,5ATR14, không fixedTP, một position. Giữ chi phí parent: BidAsk observed,
commission2,50USD/lot/side, slip0/0,00002 mỗi side, declared funding. Hai năm
đã consumed; **không cleanOOS hoặc account liên tục**.

| Năm | Rule | Phí chuẩn, USD | Phí cao, USD | Lệnh đóng / mỗi cost |
|---|---|---:|---:|---:|
| 2019 | Breakout cũ R015 | +240,85 | +114,80 | 166 |
| 2019 | Retest mới R019 | +27,26 | **−5,16** | 50 |
| 2022 | Breakout cũ R015 | +43,45 | −3,96 | 170 |
| 2022 | Retest mới R019 | **−450,56** | **−452,64** | 52 |

R019 có156/157arm attempts năm2019/2022, nhưng chỉ50/52entries — khoảng một
lệnh/tuần, không phải cam kết tần suất tương lai. 2019 có25SL/25strategy-exit;
2022 có37SL/15strategy-exit, mỗi cost. Strategy-exit không tự là lệnh thắng.
Tất cả8books kết thúc flat, không pending; funding thực ghi0 do các vị thế
đã đóng trước các funding events. Không bỏ swap khỏi cost model để tạo số0.

Gate đã khóa là net>0 ở cả4year-cost cases và≥30closed trades/case; counts
đạt nhưng net không đạt. Năm2019stress gần0; năm2022 âm rõ trong mô hình H1.
Không dùng dấu gần0 để hard-reject cả family. Exact recipe không được ưu tiên
stage2; H1 approximation chưa thể thay full-tick/prop qualification.

## Hành vi code và luồng state/data

Reuse `IntradayH1Candidate`, native ATR/size/next-quote/coarse cost core; không
engine hay UI mới. Thêm opt-in candidate và4optional state fields: armed side,
level, time và attempt day. Pending retest chỉ thuộc R019, expiry từ armed time;
không tạo một state store khác. Old candidates buộc fields mới empty.

Closed H1 source → cập nhật prior-day range/ATR → arm → confirm/cancel → queued
intent → first observed quote sau decision trong coarse model → stop/exit/cash.
Source gaps hủy pending arm. Missing quote sau intent giữ actual late fill,
không tự giả fill tại giờ mong muốn. Native tick path vẫn cần kiểm riêng vì
decision delivery/next-tick và stop first-crossing khác H1 approximation.

## C2: đã kiểm gì, chưa kiểm gì?

| Lát | Bằng chứng |
|---|---|
| Trước economic outcomes | 33focused tests +27subtests đạt; sau thêm retest state guards, 18tests +25subtests liên quan đạt |
| Fixtures mới | BUY/SELL, không same-bar retest, confirm bar1/bar3, expiry, equal-close invalidation, one-arm latch, gap/day/clock/stale range, state roundtrip/tamper, native next-quote entry/exit/SL/cash và missing confirmation/entry/exit |
| Legacy prefix parity | Frozen predecessor:19recipes×1.200candles =22.800signal/distance checks;760state snapshots,19restore cases,457synthetic entries; khớp, fields mới None |
| Source admission | 4annual raw/cache seals rehashed/loaded bằng native guard; 2019warmup1.016H1,2022warmup1.077H1, toàn bộ observed Nov–Dec năm trước |
| Separate economic review | 1.268decisions,876closed trades trên8books; state-machine/floatATR khác implementation, Fraction sizing/fees/cash; independent H1 earliest stop/strategy-exit audit khớp |
| Parent economic regression | Cả4parent books khớp exact historical trades/decisions/funding/open/pending/net/cash với catalogue13 cũ; không rerun624cases |
| Mutations | 5lỗi fee, fill, future decision, quantity và false authority bị reject |

Review cùng agent/provider, code paths khác; không independent human/model
audit hoặc nguồn độc lập. Giá SL giữa nến vẫn level/H1 gap, chưa actual first
crossing tick. ATR oracle float so sai khác<1e−13 về price distance; tài chính
dùng Fraction/cent rounding, không nới monetary tolerance. Chưa intrabar DD,
internal risk brakes/prop equity/time-fit, target contract, selection-aware
unseen/prospective forward hoặc owner handover. Correctness trong scope này
không là chứng nhận challenge. Không broker/network/model calls hoặc2025+.

## Hậu kiểm kỹ thuật và thời gian

| Phase thực đo | Wallseconds | Quyết định |
|---|---:|---|
| Pre-numeric legacy parity | 2,178 | Đủ cho synthetic scope, giữ receipt/source hash |
| Source load/rehash4years | 11,824 | Khoảng76%job; giữ integrity guards, chưa có lý do tối ưu khi job đủ ngắn |
| Toàn paired run | 15,477 | CPU15,203s;8books hoàn tất, không retry/failure |
| Independent review | 3,263 | Không rerun numeric; mọi field liên quan khớp |

Code/research preparation time chưa có timer riêng; các số trên **không là
toàn bộ thời gian từ ý tưởng đến kết luận**. PID27724/session85597 và reviewer
terminal0. Không còn numerical worker của lượt này để chờ. Không sửa source
đang pin giữa job; raw/frozen artifacts và lỗi/negatives cũ giữ nguyên.

Không correctness bug mới trong scope đã kiểm. Workflow preflight lần này đã
kiểm các nhánh missing-data trước PnL, không lặp thiếu sót của pilot R033.
Chưa cần GPU/Rust, service/index/RAG hoặc thêm skill; research/qualification/
evidence-continuity/retrospective hiện có đủ. Không xóa evidence để cleanup.

## Evidence, catalogue và hướng tiếp

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/prior-day-retest-v1` giữ8books/config/manifest/source-snapshot/
source-proofs/result/review/progress/events. Driver `run-prior-day-retest-v1.py`,
reviewer `check-prior-day-retest-v1.py` pin trước outcomes. Preflight riêng
`prior-day-retest-preflight-v1.json`/`check-prior-day-retest-legacy-v1.py`.
ResultSHA `bc382fbc13e2740ebb74a710c79b850d76f497e45ab1181fd700ef1de5dd40a4`;
reviewerSHA `7ef85fee2b2f78a6c74262981323bdd2609ffb1b54b6f8f998e9dc2a4d399d1f`.

R019 chuyển từ deferred sang **implemented, not retained under stage1**.
Catalogue vẫn60records, nay43research policy versions/25native offline rules;
không thêm recipeID cho hai costs, hai năm hoặc parent rerun. Không challenge
candidate. Goal C1/C2 active.

Lát tiếp: admission thị trường NASDAQ100 và một hypothesis có lý do chuyển
asset, trước numeric. Reuse existing public provider/cache helpers; kiểm
instrument identity, BidAsk/units/time/calendar, cost/funding geometry và
source fidelity trên fixture nhỏ trước full history. Không tự lấy assumptions
US500/gold gắn sang NASDAQ, thêm provider/account hoặc hạ phí cứu các bản cũ.
