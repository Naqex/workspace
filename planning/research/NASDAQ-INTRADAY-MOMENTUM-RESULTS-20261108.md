# NASDAQ first→last-half: không đạt, không đảo tín hiệu để rescue

[Protocol](NASDAQ-INTRADAY-MOMENTUM-PROTOCOL-20261108.md) khóa trước outcomes,
implementation15303de, sourceM1 đã review. R064 là transfer của R051 sang
NASDAQ, không independent trial family hoặc paper replication. Đã terminal và
đối soát đầy đủ; chưa có candidate challenge.

Giá trị dưới đây là **USD trên một hypothetical unit**, không lot hoặc tài
khoản10k. Cả2years đủ endpoints, không unresolved trong window đã đăng ký.

| Năm | Signal days / cashdays | Primary phí chuẩn | Primary phí cao | Primary−alwayslong khi phí cao |
|---|---:|---:|---:|---:|
|2019|221/252|−260,64|−481,64|−70,44|
|2022|192/251|−1.777,99|−1.969,99|−1.116,10|

Alwayslong cùng mask cũng âm: stress−411,20/−853,89USD/unit, không được đổi
thành winner.4halfdays skip theo calendar;86regular days không đủ readiness
hoặc flatfirst-return, không bị chọn theo PnL.413signals/413resolved endpoints,
503cashdayrows đều giữ;0missingM1 trong413holdingwindows28minutes đã đo.
Không suy sourceM1 completeness thành executable ticks hoặc targetbrokerproof.

**Decision:** gác exactR064, không đổi side/clock/ATR/control/fees hoặc gọi
opposite-side counterfactual là ứng viên được kiểm định. Không là bác bỏ mọi
intraday momentum hoặc ORB. Không tốn longhistory/propwrapper cho bản này.

## C2 và engineering scope

- 9focusedtests trước history,6FOMChelper regressions;5wirefixtures Buy/Sell/
  missingentry/missingexit/halfday qua separate reviewer trước numeric.
- Pure parent Decimal signal đối chiếu Fraction oracle; timing firsthalf,
  previouscashclose/14pastTR và futuremutation giữ entry, không filter ngày
  hiện tại bằng phần cuối ngày chưa biết.6mutations sourcequote/side/time/
  missingrow/authority/hash đều reject.
- 503rows,1.652cost-rolecases và1.652sourceendpointpricechecks reviewed,
  cents rounding/gross/spread/slip/net và matchedcontrol summaries khớp.
  Supplemental `financial-field-crosscheck.json` kiểm24.780costfields bằng
  Fraction/7mutations,0,151s; reuse parent sourcebinding, không rerun simulator.
  Sameagent/provider, không independenthuman/model review. Không account/
  SL/sizing/prop/OOS/forward/handover hoặc brokerauthority.
- Sourceđọc1lần/year; numeric1,047/1,066s; prepare2,005/2,194s, totalproducer
  9,756s/CPU9,578s; reviewer9,992s. Không gọi đây là speedup so R063 vì khác
  workload. Chưa có bottleneck đáng thêm GPU/Rust/framework; giữ implementation.
- Helperobservation hỗ trợ M1 bằng durationexplicit, H1default/fields giữ như
  cũ qua regressions. OldFOMC artifacts/snapshots không đổi hoặc rebindcode mới.
  No source fetch/paidprovider/account/runtime/product changes.

Private `execution-v1/nasdaq-intraday-momentum-component-v1` dưới campaignroot
giữ pins/config/rows/summary/result/review/timings/status/events/snapshots.
ProducerPID23320 vàreviewer terminal0. ResultSHA
`41eb0114381bc21c8e90f9d594c9fdba74eb730640c591e56df515aa64edfaf8`;
reviewer sourceSHA
`1e4d401d7e65e7b63998a26a5cdecd45e189b9e0321ed39d2306f2d5faa13e72`.
Review receiptSHA
`c2965d148c33a4be4c92e25ec6c6e9caf78041fa8a73e7fe37a5a00fde042038`.
Không nhầm reviewer code hash với review receipt hash.

**Tiếp:** [QQQ first5minute ORB method admission](NASDAQ-OPENING5-ORB-METHOD-20261108.md),
một rule có primarymethod rõ và fixedstop khác R064, dùng sealedM1 hiện có.
Chưa chọn n/TP theo data và chưa economicoutcome mới. Goal C1/C2 active.
