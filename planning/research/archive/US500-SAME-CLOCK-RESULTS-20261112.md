# TC01 cùng giờ qua các ngày: đủ cơ hội, không qua cost/control screen

12/11/2026. **Đã kiểm xong một giả thuyết mới; gác exact TC01.**
673 cơ hội/753phiên lịch, khoảng4,47/5phiên, nhưng endpoint net âm cả ba năm
ở cả hai chi phí. Giữ US500/M15/intraday; chưa có challenge candidate.
[Protocol](US500-SAME-CLOCK-PROTOCOL-20261112.md) +source/tests freeze tại
`df26bf1` trước numerical outcomes. Không thêm grid hoặc chuyển reverse-score.

## Hiểu cách thử

Tại10:00NewYork, xem20phiên thường trước đó: khoảng10:01–10:31 thường tăng
hay giảm theo arithmeticmean BidOpenreturn? Mean dương→BUY,âm→SELL,0→đứng
ngoài; component đọc mức vào10:01 và mức ra10:31. Giả thuyết là dòng giao dịch
định kỳ có thể để lại chuyển động lặp theo giờ; không phải đợi cú phá kênh.

[Heston/Korajczyk/Sadka](https://arxiv.org/pdf/1005.3535) là primary source về
periodicity của **cross-sectional cổ phiếu**, chưa chứng minh áp dụng cho
time-series một CFD chỉ số. TC01 là adaptation do project đặt ra, không
paper replication hoặc bot đã được tác giả chứng minh. Đã phân biệt transfer
gap này trước kết quả. Không importcode/data từ paper.

## Kết quả — đơn vị phải hiểu đúng

Đây là **tổng điểm giá của component cố định1đơn vị**, khai báo giả định1USD
trên1point, không vốn10.000USD/risk0,25%, không native order hoặc chiến lược
có SL. Có thể đọc−538,96point là−538,96USD trong unit giả định này, nhưng
không so trực tiếp với netR120 vốn10k/lot sizing. Hai costs là phương án thay
thế trên cùng673signals, không1.346cơ hội độc lập.

| Năm | Cơ hội | Net reference, point/unit | Net stress, point/unit |
|---|---:|---:|---:|
|2022|230|−538,960|−768,960|
|2023|228|−126,516|−354,516|
|2024|215|−196,926|−411,926|
|**Tổng**|**673**|**−862,402**|**−1.535,402**|

Entry BUYask/SELLbid và exitngượcside, spreadembedded; adverseextra slippage
0,25/0,75point mỗi chiều; commission0 declaredscenario, chưa account FTMO fee.
Endpoints đủ cho673/673, không loại trade thiếu endpoint để làm đẹp net.
**Hai unique holdingwindows có missingM1 bên trong** (1năm2023,1năm2024);
không cản phép trừ endpoint đã có, nhưng SL/DD/firstcrossingpath vẫn chưa
biết trong hai windows. Không suy endpoint known thành full trading path known.

| Bridge của673cohort, point/unit | Giá trị |
|---|---:|
| Chuyển động theo hướng TC01 ở midpoint-of-minute-opens benchmark |−208,272|
| Embedded spread debit |−317,630|
| BidAsk gross, đã gồm spread |−525,902|
| Extra slippage reference |−336,500|
| Reference net |−862,402|
| Extra slippage stress |−1.009,500|
| Stress net |−1.535,402|

Midbenchmark chỉ để đối soát arithmetic, không observed synchronous quote
hoặc executablefill. Không trừ spread/slippage lần hai. Tổng midprice movement
đã âm trước mọi debit, nên chưa có bằng chứng đây chỉ là một edge bị phí cao
ăn hết.2023/24 có midbenchmark dương riêng (+102,7695/+18,8700), nhưng âm sau
spread/declaredslip; không chọn hai năm đó rồi gọi winner/OOS hoặc tune giờ.

| Constant direction control, cùng673planned windows | Reference | Stress |
|---|---:|---:|
| Luôn BUY |−977,867|−1.650,867|
| Luôn SELL |−330,393|−1.003,393|
| TC01 chọn theo20ngày trước |−862,402|−1.535,402|

TC01 tốt hơn BUYcontrol nhưng kém SELLcontrol và vẫn âm. Đây là matchedcohort
counterfactual controls, không randomized causality hoặc quyền chuyểnSELL-only.
Frozen next-stage heuristic không đạt cả totalstress>0,>=2positiveyears và
beatbothcontrols. Không dùng PnLnegatives của1recipe để bác bỏ mọi seasonal
flow, toàn OHLCV hoặc tất cả cách tradingUS500.

## Tần suất và lý do đứng ngoài

| Năm | Phiên lịch | Warmup | Phiên ngắn | Chặn do historical endpoint thiếu | Signal | Tuần không signal /tổng |
|---|---:|---:|---:|---:|---:|---:|
|2022|251|20|1|0|230|4/52|
|2023|250|20|2|0|228|4/52|
|2024|252|20|3|14|215|7/53|
|Tổng|753|60|6|14|673|15/157|

Tổng mỗi dòng khớp calendar.14ngày chặn2024 là hệ quả causal giữNone trong
window20ngày, không lấy last20valid để âm thầm thay recipe. Cold annualstarts
làm60ngày warmup trong ba sổ, không gọi thành ngày thị trường không cơ hội.
Quarter/month/weeklydistributions gồm0 giữ trong cadenceartifacts. Floor
>=200total/>=50annual đã qua trước component reader; không chứng nhận edge.

## Kiểm chứng và thời gian

-8focusedtests trước run: cả2side/warmup, zero, historygap, current/future
  target không đổi signal đầu, entryavailability tách signal, freshminute,
  halfday/annualreset, BidAsk/slippage/unknown và prioritycontrol guard.
-Primary producer dùng Fraction; reviewer riêng không import signal/endpoint
  implementation, dùng Decimal80 và direct-index20priorregularsessions.
  **673/673timestamps/directions** khớp, NYclock10:00/DST/date khớp.
-4.038componentrows (673×3recipes×2costs) đối chiếu sourceendpoint Bid/Ask,
  projectedfills/slip, mid/spreadbridge, unknown/interiorgap và annual/totals.
  Input/source/runtime/protocol hashes kiểm lại; source cùng frozenadmission
  loader, không independentfeed hoặc rawBI5 decoderreview mới.
-3actualrow mutations net/side/entrytime đều bị chặn trong bộ nhớ. Giữ
  `review.json`, reviewer snapshot/hash; đây là same-agent separate arithmetic.
-Workspace contracts đạt9guides/8pinnedsubmodules; catalogue legacyfields được
  so với`df26bf1` giữ nguyên toàn bộ. Supplement/annualreport/local links khớp
  numericalartifact; không writerlock còn lại.

| Lát | Actual wall | Đánh giá kỹ thuật |
|---|---:|---|
| Producer:load/sourcevalidation/cadence/component/write/pinguards |15,025s|3năm;loadmỗi năm một lần dùng chungstage|
| Separate signal/point-cost/source review |14,850s|Cố ý đọc lại admittedsource để đối chiếu|
| Research/code/tests/report/Git toàn task |Chưa đo riêng|Không nhận cả task chỉ mất30s|

Không materialbug mới, không lặp financialbacktest hoặc tối ưu GPU/Rust.
Tái dùng sourceproof/calendar/cadence/atomicwriter/runtime cũ; chỉ thêm module
signal/component, runner và8tests. Không cần framework hoặc skill mới.
Savedyearfiles giữ checkpoint; runner chưa cung cấp CLIresume giữa năm,
không gọi việc giữ checkpoint là đã kiểm resume. Không có failure attempt.

## Quyết định và đường đi tiếp

`park_exact_component`: không đưa TC01 tới nativeSL/account/prop qualification,
không mở2025/26 hoặc đổi lookback/slot/side để cứu từ outcome vừa thấy. G0
đăng ký trước; G1causal/arithmetic có evidence trongscope; G2chỉ endpoint/cost
scenario; G3edge chưa có,G4–G6không được cấp bởi study này.

Bài học cụ thể: hướng theo cùnggiờ20ngày trước này không cho grossaggregate
dương, và spread/slippage làm kết quả yếu hơn. Tần suất cao đã giải được
về count, nhưng chất lượng dự báo vẫn là nút thắt. Không có evidence cần
thêm engine/performance layer. Vòng sau ưu tiên source/mechanism admission
có thông tin mới trước code/search tiếp, thay vì tăng trialcount bằng grid.
Chưa dispatch hoặc chọn market/data/account mới.

Catalogue123/88/53historical giữ; thêm1relatedcomponentstudyTC01 +2constant
controls trong supplement, không độc lậpedge hoặc accountpolicy.2022–24 đã
consumeddevelopment; không đổi status các negatives/holdout/authority cũ.

Private campaign: `execution-v1/us500-same-clock-v1/` cómanifest/pins/source
snapshot,input/admission3năm,cadence-gate/perdayevents,18annualrecipe-cost
files,result/review/status/events/PROGRESS. PrimaryresultSHA:
`a7decd548d69304f0e8d11f27beb562003f76ad6ab6cdce5a3428c3b53eaa8c8`.
Tổng18files không18independentstrategies.0native/accountsimulation,0newGET,
0broker/modelcalls; không còn job nền. Progresspanel open trảqueued, nên
không tuyên bố owner đã nhìn thấy tab; file/log đã tồn tại và completed.
