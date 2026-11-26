# S&P 500 overnight → đầu phiên: transfer trial khóa trước outcomes

Tiếp [R074 NASDAQ review](NASDAQ-OVERNIGHT-REVERSAL-RESULTS-20261109.md), không
đổi verdict của R074 hoặc promote opposite control. Chọn US500 vì gần S&P ETF/
futures trong [Liu & Tse](https://www.sciencedirect.com/science/article/pii/S1059056016301563)
hơn NASDAQ; nguồn abstract/introduction và giới hạn full method giữ đúng
[method admission đã đọc](NASDAQ-OVERNIGHT-REVERSAL-PROTOCOL-20261109.md).
Đây là transfer sau khi đã biết NASDAQ âm, cùng family/selection history,
không independent discovery, paper replication hoặc clean OOS.

## Nguồn và câu hỏi

R075 `us500-overnight-first30-reversal-price-component-v1`. Development 2019/
2022; chỉ cần previous expected cashsession trước năm để có first overnight
gap. Reuse full source-only views đã review:

| Năm nguồn | Root dưới private `execution-v1/` | Source proof SHA256 |
|---|---|---|
| 2018 | `us500-long-explicit-source-v1/2018` | `1670fb10ccd76036f092b2dc9b959852130b27d695d3ebeae60856239b3c337c` |
| 2019 | `us500-long-explicit-source-v1/2019` | `657f2ec2542af0d76b4df5980e93791b7a0b16f8f915f2205c5aa6a170d86f59` |
| 2021 | `us500-long-explicit-source-v1/2021` | `caa6f2802d1d2c04a27028cb3f1da5ddbedf8bd9bda17096ebf077ea1969e9ce` |
| 2022 | `us500-explicit-source-v1/2022` | `7a41f021c86a04345ce2591b90efa72112792ef5479c16ff6d1167f7064dc840` |

2018/2021 chỉ lấy previous cash endpoint theo calendar, không tính PnL hoặc
thêm predictor từ các năm đó. Các năm đều đã consumed. Rebind proof/producer/
validator/raw input seals/calendar/canonical quarterly outputs bằng guards hiện
có; không nâng old expanded view thành source-only hoặc bỏ raw hash checks.
2022 calendar tại `tooling/ai-engines/fixtures/nyse-2022.json`; các năm khác
dùng frozen `us500-long-cash-calendar-v1/nyse-<year>.json`. So economic session
stamps với fixed cash proxy của component trước outcomes. Khác metadata không
cho phép sửa hashes; thiếu source endpoint vẫn giữ row.

## Exact rule, economics và gate

Giữ nguyên R074: gap = 09:30 BidOpen − đúng previous cash last M1 BidClose;
SELL nếu dương, BUY nếu âm, bằng 0 không trade. Regular 390-minute cashdays;
halfday skip theo calendar, prior halfday vẫn cung cấp close. Missing/crossed
predictor là unavailable, không zero. Decision 09:31 → M1Open 09:32; decision
thoát 09:58 → Open 09:59. Quote interval proxy không executable tick; không
TP gap-touch, SL/ATR/threshold/volume/news filter hoặc parameter grid.

Một hypothetical unit worth 1 USD/price unit, không lot/account risk/margin.
BUY Ask→Bid, SELL Bid→Ask; observed spread, slip 0,25/0,75 mỗi side, commission
0 qua existing `index_noise_study` zero-commission declared cost scenario.
Đó là scenario dùng cho nghiên cứu, **không historical broker cost proof năm
2019/2022**; public index-commission evidence đã có không chứng nhận quotes/
fills/latency hoặc target account. Không planned overnight funding.

Mọi expected cashday có row. Missing/crossed entry/exit vẫn planned/unresolved,
không next-quote/zero PnL. Giữ census 27 holding minutes, không filter entry
bằng future quality. No account equity/prop path claim từ endpoint component.

Primary, opposite-gap, always-long, always-short cùng mask/endpoints; 2 costs
và null không exposure. Retain chỉ khi **mỗi năm** ≥100 planned signals,
≥98% regular days có predictor, ≥98% planned days resolved, stress primary
known sum >0 và > cả always-long/always-short. Giữ concentration và unknowns;
gate là triage có thể bỏ sót edge nhỏ, không chứng minh statistical edge.
Controls không được promote nếu primary fail. Fail → gác exact recipe, không
tune clock/cost/side/threshold để rescue. Pass → đăng ký wrapper mới trước
outcomes, selection-aware robustness/OOS/prop/time-fit/prospective/handover
vẫn phải làm; chưa challenge-qualified hoặc execution authority.

## Reuse code, review và status

Hai consumer dùng chung pure component, explicit profile binds candidate,
source identity và market geometry. NASDAQ public API/default behavior phải
giữ nguyên qua focused regressions và actual 503-row/summary equality với
frozen R074; đây là kiểm source revision, không nghiên cứu lại R074.
Source observation helper chỉ thêm explicit source identity, default không đổi.

Trước new numeric: strict source admission; profile/mismatch/BUY/SELL/cost/
clock/missing/holdout tests; Fraction synthetic cases cả sub-cent raw quote vs
rounded account money. Separate reviewer dựng signal, endpoints, toàn cost
fields/census/control/gate, mutations. Cùng agent/provider nhưng cách tính
khác; chưa human/model độc lập. Giữ mọi failure/attempt/code pins cũ.

Output mới `execution-v1/us500-overnight-reversal-component-v1`, một writer,
PID/status/events/CANCEL/deadline 180 s, snapshots/config/manifest trước PnL;
review deadline 180 s riêng. Source admission riêng deadline 180 s, không PnL.
Đọc quarterly source một lần/year rồi chỉ giữ relevant cashday endpoints/path;
không download mới. Ghi prep/compute/review wall+CPU. Không sửa Trader/runtime,
skills/global config/raw hoặc mở own 2025+/broker/provider/account/payment.
