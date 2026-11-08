# NASDAQ đầu phiên: exact overnight reversal không đạt

[Protocol](NASDAQ-OVERNIGHT-REVERSAL-PROTOCOL-20261109.md) `8af0a52` và
implementation `8005a14` được commit trước outcomes. R074 là own adaptation
của cơ chế overnight → first-half reversal, không paper replication. Cả hai
năm development đã consumed; không gọi dữ liệu này là clean OOS.

## Kết quả dễ đọc

Một hypothetical unit = 1 USD/price unit; **không phải PnL trên tài khoản
10.000 USD**, không lot hoặc risk 0,25%. Tín hiệu ngược gap overnight, vào
09:32 và ra 09:59 New York, Bid/Ask và hai costs như protocol.

| Năm | Planned / resolved | Primary phí chuẩn (USD/unit) | Primary phí cao (USD/unit) | Always long phí cao | Always short phí cao |
|---|---:|---:|---:|---:|---:|
| 2019 | 249 / 249 | −917,74 | −1.166,74 | −200,41 | −1.032,19 |
| 2022 | 250 / 250 | −2.109,71 | −2.359,71 | −1.257,11 | −114,56 |

Đủ predictor và cả hai endpoints trên toàn bộ 499 planned days; 4 halfdays
skip theo calendar. 503 cashday rows đều giữ. Một holding window năm 2019
thiếu M1 bên trong: component endpoints vẫn biết, nhưng **không biết full
equity path, SL hoặc prop drawdown**. Không xóa ngày đó để cải thiện PnL.

Primary âm cả hai stress years và không đạt control comparison. **Gác exact
recipe**, không thêm SL/account wrapper hoặc tune timing/threshold/side/cost
để cứu kết quả. Opposite-gap control stress −65,86 / +988,04 USD/unit, cũng
không qua two-year gate và không được promote từ control. Negative không
bác bỏ mọi opening reversal hoặc paper trên ETF/futures khác feed/latency.

## C2: đã kiểm gì, lỗi gì và giữ lại gì?

- 7 focused tests trước actual outcomes: BUY/SELL/flat, source clock/grid,
  missing/crossed predictors/endpoints, previous halfday/holiday, DST, future
  mutation, denominator/control/authority/holdout guards. Không full product test.
- Separate Fraction reviewer kiểm đủ 503 rows, signals/prior expected session,
  1.996 endpoint price fields và 3.992 cost-role cases (59.880 cost/metadata
  fields), summary/null/concentration/gate. Cost scenarios/roles là cùng 499
  market observations, không 3.992 trade độc lập.
- 7 mutations signal/time/quote/cost/net/missingday/authority bị từ chối.
  Same agent/provider, implementation số học khác; không independent human/model
  signoff, target broker ticks, account/SL/prop/OOS/forward/handover proof.
- Reviewer v1 thất bại ở `gross_quote`: đã làm tròn quote-unit PnL thành cents.
  Contract canonical giữ `gross_quote` raw; `gross_account/net_account` mới
  làm tròn cents. Actual 03/01/2019 control có 43,528 quote units, 43,53 USD
  gross account. Giữ v1 code/failure và original manifest; reviewer v2 sửa
  đúng contract, kiểm 12 synthetic cases gồm fractional BUY/SELL rồi review
  lại **artifacts đã có**, không rerun numeric hoặc thay economic assumptions.
  Thêm regression contract nhỏ trong repo; original source/code pins giữ nguyên.

## Thời gian và cải tiến có ích

| Phase | Wall | CPU | Hành động |
|---|---:|---:|---|
| Chuẩn bị nguồn hai năm | 4,173 s | Chưa đo riêng | Reuse 8 sealed books/calendar; không download |
| Compute hai năm | 0,135 s | 0,141 s | Không cần GPU, parallel workers hoặc Rust |
| Producer toàn lượt | 7,763 s | 7,719 s | Gồm preparation/compute/pins/output, không cộng lại hai dòng trên |
| Reviewer v2 đầy đủ | 5,280 s | 5,250 s | Reuse outcomes, kiểm riêng bằng Fraction |
| Research/code và sửa reviewer | Chưa đo tổng | Chưa đo | Không suy từ timestamps thành active time hoặc speedup |

V1 review đã fail terminal 1; producer và v2 review terminal 0. Không job nền
cần chờ. Khác workload của NYFX nên không gọi tỷ lệ thời gian là tối ưu cùng
semantics. Bài học correctness được giữ bằng regression/failure, không thêm
skill/framework/DB mới chỉ cho một case; skills hiện có đủ workflow.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
output `execution-v1/nasdaq-overnight-reversal-component-v1/` giữ config,
manifest/snapshots/rows/summary/result/review/events/progress/timings/failure.
V2 reviewer và synthetic preflight ở private root, code SHA trong review receipt.

- Result SHA256: `b8df0fbdad5373d30503f4ded51617e0a43e60847ed5514da7d2c6cf36219c71`.
- Review receipt SHA256: `6b115be452b00f5d1e0b34d34107f6aac64d33b017ea46226f2108eb1f0115ed`.
- Reviewer v2 SHA256: `4e6d624c2b0b567705b6e6da79933b83b5b96efeddc843651fe1030cc9af08b7`.

Catalogue 74 records / 58 policy-model versions / 25 native / 9 controls:
R074 là price component nên chưa thêm account-policy version. Goal C1/C2
active, chưa challenge candidate. Tiếp source/method admission cho US500 cùng
cơ chế vì gần S&P ETF/futures primary evidence hơn NASDAQ; nếu làm là transfer
trial có ghi selection history, không independent discovery hoặc cứu R074.
Khóa rules/costs/coverage/control trước new outcomes; không own holdout/broker.
