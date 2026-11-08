# Rest-of-day → cuối phiên: đăng ký hai price components trước outcomes

Tiếp [method admission](INDEX-REST-OF-DAY-METHOD-20261109.md), không sửa hoặc
cứu R074/R075 opening reversal, R051/R064 first-half momentum. Cùng momentum
family/selection history, không hai independent discoveries hoặc paper replication.
Không chạy lại các account books đã gác để tìm winner.

## Hai câu hỏi và nguồn

R076 `us500-restofday-last30-price-component-v1`, R077
`nasdaq-restofday-last30-price-component-v1`. Cả hai là primary đã khóa cho
riêng asset; không cộng USD/unit giữa hai thị trường thành portfolio lợi nhuận.
Development 2019/2022, đã consumed; prior expected cashsession trước năm từ
2018/2021. Own holdout 2025+ không mở.

- US500: exact source-only views/proof SHA của
  [R075 protocol](US500-OVERNIGHT-REVERSAL-PROTOCOL-20261109.md), source receipt
  `us500-overnight-source-admission-v2/result.json` SHA
  `d5a2c23310729dab1a456cc66aa0d16e5cce5e65fbc014aa8caac5e5d3b12190`.
  Current guarded reader đối chiếu receipt qua
  `us500-overnight-reversal-component-v1/source-reader-hardening-review-v1.json`;
  code snapshot cũ là owner cho old pins, không repin theo code mới.
- NASDAQ: `nasdaq-m1-history-v2/result.json` SHA
  `3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`, review SHA
  `8b0bced9723138d52242552a66ed74c33f5a43d8d3013288b515d2db7c4b9703`;
  original 8 books/calendar seals, warmup Nov–Dec2018/2021. Không source fetch.

Giữ raw/explicit-side/canonical/calendar checks và lineage đã có. Không chạy
lại toàn bộ price transformation không đổi. Source/code/proof đổi phải có
receipt scope riêng, không lấy SHA match thay source correctness hoặc OOS.

## Tín hiệu, timing và common comparison mask

Regular cashdays 09:30–16:00 New York; halfday skip theo calendar trước outcome.
Previous close là BidClose phút cuối **đúng previous expected cashsession**,
kể cả halfday, không last available quote. Current predictor là 15:29 BidClose,
known muộn nhất 15:30. So với previous close: cao hơn BUY, thấp hơn SELL,
bằng nhau no trade. Không threshold, ATR readiness/SL, gamma/volume/news filters.
Price signal chỉ đặt câu hỏi về rROD, không đo hoặc suy ra actual gamma exposure.

Để đối chiếu predictor công bằng, cả previous close, 09:59 BidClose và 15:29
BidClose phải có paired sides/clock/grid hợp lệ và không crossed ở field dùng.
Đây là quality mask biết trước entry; không dùng current full-day completeness,
closing return hoặc outcome. Thiếu/crossed bất kỳ predictor ghi unavailable,
không thay bằng 0. 09:59 field chỉ làm benchmark/readiness, không đổi chiều
primary. Explicit common-mask adaptation khác paper không có CFD quality gaps.

Decision 15:30 → entry M1Open 15:31; exit decision 15:58 → M1Open 15:59.
Interval proxy, không executable tick đúng timestamp. Không TP/SL, exit tại
gap-touch hoặc forceclose cuối mẫu. Holding window là 28 phút; missing/crossed
endpoint vẫn planned/unresolved, không next quote/zero PnL. Internal M1 gaps
giữ census, không dùng hindsight để xóa entry hoặc chứng nhận equity path.

## Economics và controls

Một hypothetical unit =1USD/price unit; chưa lot, risk 0,25%, sizing/margin,
account equity hoặc prop drawdown. BUY Ask→Bid; SELL Bid→Ask. Hai declared
cost scenarios của mỗi asset giữ riêng, observed spread/slip 0,25/0,75 mỗi side,
commission 0; US500 dùng existing zero-commission scenario, NASDAQ helper như
R074. Không historical target-broker fee/fill proof. Same-day planned funding0.

Mỗi planned primary day cùng endpoints: primary rROD, opposite rROD, always
long, always short, **first-half control** sign(09:59 Close−previous Close).
First-half bằng0 thì control không exposure, costs=None/net0, không fake fill.
Hai costs/null giữ cùng census; controls không automatic promotion nếu primary
fail. Không so với old ATR/account PnL vì khác mask/SL/sizing.

Retain **từng asset** chỉ khi mỗi năm: ≥100 planned primary signals,
≥98% regular days đủ cả predictors, ≥98% planned days resolved endpoints,
stress primary known sum>0 và > cả always-long/always-short/first-half control
trên cùng resolved mask. Phần threshold là triage chọn workload, có thể bỏ sót
edge nhỏ; không statistical proof hoặc xác suất pass. Báo unknowns, sample/
concentration, net và paired deltas; không chọn winrate/RR đẹp để thay gate.

Fail → gác exact primary, không flip/tune threshold/clock/fees/asset/window cứu
outcome. Survivors mới đáng đăng ký một wrapper/risk design với target costs,
selection-aware/OOS, prop equity/time-fit, prospective reconciliation và owner
handover. Không gọi positive component hoặc control là challenge-qualified.

## Implementation/review trước new outcomes

Reuse calendar/predictor/cost/summary primitives cho hai rule consumers; default
opening components phải giữ nguyên qua focused tests và actual R074/R075
row+summary equality. Đây là compatibility evidence, không rerun research cũ.
New tests: late-vs-firsthalf signs đối nghịch, known-at/latency, previous holiday/
halfday/DST, no future mutation, missing/crossed predictors/endpoints, flat
primary/control, currency rounding và mixed candidate/market/authority guards.

Separate Fraction reviewer dựng toàn bộ signals/endpoints/cost fields/controls/
census/gate, source bindings và mutations; synthetic review trước economic run.
Cùng agent/provider nhưng implementation khác; không independent human/model
signoff. Giữ original/code/protocol/input snapshots, mọi failures và verdicts.

Private output mới `execution-v1/index-restofday-components-v1`, một writer,
PID/progress/events/CANCEL, producer/reviewer deadline180s riêng. Đọc mỗi input
một lần trong phase cần, ghi prep/compute/hash/report/review wall+CPU. Không
runtime/broker/provider/account/paid service/global config/raw migration/xóa data.
