# EURUSD B0: có kết quả dương có điều kiện, nhưng quá ít cơ hội

**Quyết định: chưa đề xuất challenge; chưa dùng B1 hoặc chuyển XAUUSD.**
Đã chạy đúng một bộ luật B0 trên Development 2022–2023 và historical validation 2024.
Chỉ có **30 lệnh trong 3 năm**. Lợi nhuận stress theo mô hình quan sát là 899,44 USD,
nhưng 96,15% đến từ 2023; một lệnh 2023 có đường giá thiếu gần 55 phút. Đây chưa
phải lợi thế được chứng minh hoặc kết quả FTMO đã kiểm đầy đủ.

PR70 đã merge vào main tại `0a8542ba092e454aff2fe11f6d77675400c9df2c`;
nhánh `codex/prop-target-envelope` đã xóa local/remote. Triển khai và phép đo
được checkpoint ở `d33d917`; không thay pin/runtime Trader hoặc WIP của VI Dubber.

## Phạm vi cần hiểu trước khi đọc bảng

- [Protocol đã khóa](EURUSD-B0-PROTOCOL-20261113.md),
  [registration/source pins](EURUSD-B0-REGISTRATION-20261113.json),
  [JSON kết quả và đối soát](EURUSD-B0-RESULTS-20261113.json).
- Mỗi sổ năm bắt đầu 50.000 USD, ngân sách R0 = 150 USD/lệnh (0,30%), không lãi kép.
  H1/M15/ATR nối liên tục từ 01/11/2021; không khởi tạo lại chỉ báo theo năm.
- Hai kịch bản có **cùng trades/lots/SL/TP**: sizing và admission cùng dành
  reserve stress. Phí chuẩn 5 USD/lot/cả vòng; stress 9 USD gồm 5 USD commission
  và 4 USD slippage. Gross đã chứa spread Bid/Ask; không trừ spread lần hai.
- Toàn bộ bảng là **conditional economic diagnostic**, trước admission lịch
  known-at news và lịch phiên/rollover của tài khoản đích theo ngày. B0 đầy đủ giữ
  `BLOCKED_BY_CALENDAR`, net/cadence đạt quỹ=N/A, `PROP_UNMEASURED`.
  Swap bằng 0 chỉ thuộc kịch bản rollover khai báo lúc 21:00 UTC và đã thấy giá đóng;
  chưa xác nhận cost/session lịch sử của tài khoản FTMO đích.
- 2024 đã được nghiên cứu trước đây, không phải dữ liệu hoàn toàn chưa từng xem.
  Giá 2025–2026 **không được mở**.

## 1. Phễu: cơ hội mất ở đâu?

| Năm | Ngày trong tuần | Zone hợp lệ | Bias+breakout | Chạm đầu tiên | Xác nhận trước phí | Bỏ vì phí | Tỷ lệ bỏ vì phí | Lệnh vào BUY/SELL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|2022|260|258|261|125|31|18|58,06%|13:9/4|
|2023|260|259|283|136|36|25|69,44%|11:7/4|
|2024|262|260|262|109|28|22|78,57%|6:2/4|
|Tổng|782|777|806|370|95|65|68,42%|30:18/12|

806 setup đối soát đủ với first touch/expiry/cutoff/bias/gap cancellations;
370 lần chạm = 275 lần không xác nhận + 95 lần xác nhận; 95 = 65 bị loại vì phí
và 30 lệnh vào. Không có cơ hội nào bị loại sau xác nhận vì lot tối thiểu,
margin, SL không hợp lệ hoặc thiếu giá vào. Zone thiếu 2/1/2 ngày theo năm;
nến tín hiệu thiếu 1/1/4; có một setup chờ bị hủy do thiếu nến năm 2024.

**Nút thắt có hai tầng:** ngay trước phí chỉ có 28–36 xác nhận/năm; sau phí
còn 6–13 lệnh. Vì vậy sửa commission hoặc tăng risk đơn thuần chưa giải quyết
được độ thưa của bộ luật hiện tại. Giới hạn 2 lệnh/ngày chưa hề chạm: thực tế
tối đa 1 lệnh/ngày. Nguyên nhân không nằm ở giới hạn lệnh/ngày hoặc lot tối thiểu.

| Năm | SL tự nhiên trung vị trước phí | SL trung vị của lệnh vào | SL trung bình trước phí → lệnh vào | R_price trung vị |
|---|---:|---:|---:|---:|
|2022|8,40 pip|12,30 pip|10,19→14,41 pip|138,00 USD|
|2023|6,00 pip|10,50 pip|7,14→10,77 pip|136,50 USD|
|2024|6,05 pip|8,95 pip|6,36→10,22 pip|134,66 USD|

Các SL hẹp bị bỏ theo cap; **không có SL nào được kéo rộng để qua cap**.
R_price nhỏ hơn R0 vì còn phí, dự phòng và làm tròn lot. Giữ cả lệnh thua và
tháng không có lệnh trong thống kê.

## 2. Unit economics: đã vượt được ma sát chưa?

| Năm / cost | Lệnh | Gross sau spread USD/lot | Commission+slip USD/lot | Conditional net USD | Mean netR0/lệnh | Annual netR0 |
|---|---:|---:|---:|---:|---:|---:|
|2022 chuẩn|13|10,57|5,00|+78,05|+0,0400|+0,5203|
|2022 stress|13|10,57|9,00|+22,01|+0,0113|+0,1467|
|2023 chuẩn*|11|69,18|5,00|+922,32|+0,5590|+6,1488|
|2023 stress*|11|69,18|9,00|+864,84|+0,5241|+5,7656|
|2024 chuẩn|6|10,47|5,00|+46,83|+0,0520|+0,3122|
|2024 stress|6|10,47|9,00|+12,59|+0,0140|+0,0839|

*2023 có khoảng trống khi giữ lệnh, không phải exactfull pathnet. Các năm khác cũng còn gate
news/target calendar; tất cả là mô hình quan sát có điều kiện.

GrossUSD/lot tính=sumgross/sumlots, không trung bình từng ratio hoặc chỉ winners.
Tổng30 lệnh:36,94 lots; gross1.231,90 USD, commission184,70 USD, stressslip147,76 USD;
net chuẩn1.047,20 USD, net stress899,44 USD=5,9963 R0. Đây là cộng ba sổ reset,
không CAGR/continuousaccount/payout.

So Catalogue13historical0,69–8,19 USD/lot, B0 có gross mẫu cao hơn; tuy nhiên
2022/2024 chỉ hơn9 USD stress fee khoảng1,5 USD/lot. Period/rules/sample khác,
không là một A/Btest hoặc bằng chứng edge độc lập.2023 đóng góp96,15%net stress;
không chọn riêng năm/side tốt để sửa verdict.

| Năm | Netstress BUY / số lệnh | Netstress SELL / số lệnh | Tháng không lệnh | Tháng có lệnh |
|---|---:|---:|---:|---:|
|2022|−148,77/9|+170,78/4|4|8|
|2023*|+588,91/7|+275,93/4|4|8|
|2024|−194,30/2|+206,89/4|9|3|

SELL dương trong mẫu nhỏ **không cấp quyền chạy SELL-only**; đó là trial mới.

## 3. Friction: cap dự kiến khác phí thực tế

| Năm / cost | PlannedstressF/R0 median (dùng chung) | RealizedF/R0 median | P90 | Max |
|---|---:|---:|---:|---:|
|2022 chuẩn|10,40%|6,88%|7,52%|8,10%|
|2022 stress|10,40%|9,71%|11,47%|11,70%|
|2023 chuẩn*|10,40%|6,50%|7,50%|8,40%|
|2023 stress*|10,40%|9,97%|11,50%|12,13%|
|2024 chuẩn|10,56%|6,76%|7,33%|7,65%|
|2024 stress|10,56%|10,72%|11,75%|12,03%|

Mọi intent được nhận đều có plannedstress≤12%; có1lệnh 2023 và1lệnh 2024
realizedstress vượt12% do spreadexit không biết trước. Không loại hai lệnh
đó. Reserve dùng entryspread, không nhìn trộm exitspread. Mid→spread→TP limit
executiondrag→explicitcost được đối soát; TP không được hưởng priceimprovement.

## 4. Daily loss và floating drawdown

Tính trên **mọi observed tick lúc giữ lệnh**, không suy từ cashclose hoặc H1/M1
extrema. Dailyanchor là balance00:00Prague. SessionLondon cùng ngày Prague
và các vị thế đều flat trong ngày theo scenario; đã kiểm ánh xạ clock cho
toàn 2022–2024. Daily và peak-to-trough là hai số khác nhau.

| Năm stress | Max entries/ngày | WorstDailyLoss USD / %50k | Equity peakDD USD / R0 | Staticloss so vốn đầu | Path không có gap>60s |
|---|---:|---:|---:|---:|---:|
|2022|1|155,25 /0,3105%|716,37 /4,7758R|515,57 USD|13/13|
|2023*|1|149,80 /0,2996%|290,82 /1,9388R|280,32 USD|10/11|
|2024|1|149,31 /0,2986%|474,12 /3,1608R|254,55 USD|6/6|

Pooled observedstressDD716,37 USD=4,7758R; **không chứng nhận overall/DD quỹ**.
2023/toàn chiến dịch truepathDD chưa đủ dữ liệu. Có29/30 lệnh không gap>60s theo
policy; điều này không chứng minh feed giữ mọi tick hoặc không có giá ẩn.
JSON còn liquidationmarkedseries với cost reserve; peakDD của series này
không tự là upperbound của peakDD series equity vì peak cũng thay đổi.

**Gap ngày 25/09/2023:** từ 10:05:27.510 đến 11:00:00.177UTC, 54phút32,667 giây;
54 phút M1 hoàn toàn không có observations. Nativeprepared và CSV gốc khớp
toàn17.774 sessionticks của ngày đó: đây là gap đã có trong source, không
phải B0 làm rơi dữ liệu. LệnhSELL có observedmodelnet−45,90 USD stress;
SL/TP trong gap và eligibility sau hiddenexit vẫn unknown. Không drop lệnh,
không nội suy, không giả bound chỉ bằng thay−45,90. Boundedlocalcachelookup
chưa tìm được đường EURUSD đủ để khôi phục; không tải mới hoặc thay feed.

## 5. So với Prop Target Envelope

| Cửa | Kết quả | Quyết định |
|---|---|---|
|Giá/fees/timing/accounting|17 fixtures;60 scenario-trade cash/fill/cost checks|Đạt phạm vi đã kiểm, không full native-engine parity|
|Frictionplan≤12%|Đạt mọi nhận lệnh;2 lệnh stress thực tế vượtcap|Filter hoạt động; không bảo đảm chi phí tương lai|
|Cadence≥60/năm, ưu tiên120|6–13conditionalfills; trướcphí28–36confirmations|`CADENCE_OR_SAMPLE_SHORTFALL` trong diagnostic; strict funded cadence N/A|
|Kỳ vọng sau phí|Mẫu dương cả3 năm,30 lệnh; tập trung 2023|Chưa chứng minh edge; không gắnECONOMIC_FAIL nhưng cũng không alpha-pass|
|Path|1khoảng trống khi giữ lệnh;2023 chưa khôi phục|`DATA_PATH_INCOMPLETE` cho affectedpath và toàn chiến dịch claim|
|Tốc độ tích lũy R mục tiêu|Trung bình conditional≈2 R0/năm,2023≈5,77R|Còn rất xa25–40R designrange và50R/năm cho mục tiêu12tháng ở0,30%|
|Daily/overall/target/lifecycle|Chưa fullnews/calendar/accountreplay|`PROP_UNMEASURED`, không `PROP_VIOLATED`|
|OOS/payout|2024exposed;2025–26closed; không shadow/live|Chưa qualified hoặc income evidence|

Cadence strict không được suy thành upperbound từ cohort này: newsreject/
earlyexit có thể thay eligibility của lệnh sau. Đây là bằng chứng bộ luật
đang đo thưa, chưa là đã chạy đủ fundedpolicy.

**Đề xuất sau dossier:** gác B0 khỏi danh sách challenge hiện tại. Chưa có
cơ sở tăng risk để chữa cadence hoặc coi DD thấp là quyền nâng risk. Nếu
owner xét B1, cần **một cơ chế tạo thêm cơ hội hợp lý trước phí**, đăng ký
trước và giữ budget; nới costcap/SL hay bỏ thua sau khi nhìn số không phù hợp.
Không tự dispatchB1 hoặc A/XAU. Dữ liệu/news gaps cần đúng admission nếu
sau này muốn nâng bất kỳ bản nào thành ứng viên quỹ.

## 6. Vận hành, thời gian và hậu kiểm kỹ thuật

Luồng: sealedBid/Askticks→nếnBid đã đóng→H1bias/zoneM15→breakout/retest→
naturalSL+stresscostadmission→native sizing→observed tickfill/SL/TP/time exit→
native accounting→read-only audit. Đây là researchadapter dùng native financial
primitives; chưa phải fullTrader/LEAN/Nautilus liveengine hoặc brokerreplay.

| Công đoạn | Wall đo được |
|---|---:|
|WarmupNov–Dec 2021,2.898.251 ticks|26,41s|
|Chuẩn bị 2022,36.946.763 ticks|199,98s|
|Chuẩn bị 2023,27.549.175 ticks|137,28s|
|Chuẩn bị 2024,20.687.149 ticks|96,14s|
|Tổng preparation gồm load/overhead|459,91s|
|Indicators liên tục|0,19s|
|Ba năm×hai costscenarios, execution/accounting/output|10,27s|
|Tổngfinancial job|470,61s=7phút50,61 giây|
|CPU processfinancial job|407,17s|

Đây không benchmark cùng workload với engine cũ, không claim tăng tốc Xlần.
Preparation chiếm97,72%wall; cache đãsealed có thể reuse sauhash/bindingcheck,
nhưng chưa đo wall của fullcache rerun. Không chạy lại tài chính để làm đẹp số.
Tổngthờigian suynghĩ/code/research/review/viếtbáocáo không được đo liên tục,
không cộng các khoảng chồng nhau rồi gọi end-to-end runtime.

| Hậu kiểm | Evidence / xử lý |
|---|---|
|Correctness|19.482 nến trong phiên khớp quotes;541.248 điểm định giá equity và60 scenario-trades khớp phép kiểm tiền nguyên cents. Đây là self-review trên cùng feed, không independent validation|
|Data quality|Gap54,54 phút phát hiện/đối chiếuCSV, giữ unknown và originalattempt; không rerun source mới|
|Reliability|Sửa second writer bị từ chối không được ghi failure vào active attempt;17 fixtures gồm race/ownershipcase. Thay đổi saufinancial run, không đổi numerical kernel|
|Evidence|Giữ reviewgốc; reviewer mới nhận explicitfrozensource và outputmới, không overwrite receipt; chặnPython-O làm tắtassertions|
|Performance|Reuse nativeprepared 2023/24 và viewcache; chưa cầnGPU/Rust/engine rewrite; hotspot hiện tại là source preparation|
|Skills|Workflow hiện có đã yêu cầu source gaps/closed holdout/cost/trace; không tạo skill trùng hoặc đổi globalconfig|

Numerical source hash giữ trong registration/private`source-attempt-1`; code checkpoint
`d33d917` trước post-run ownership/review hardening. Các correction này không đổi
signal/risk/cost/fills, không tiêu B1. Final review dùng frozen-source pins.

Private artifacts:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/eurusd-b0-20261113/`.
`attempt-1/result.json`, `review.json`, `review-final.json`,
`gap-20230925.json`, per year`*-details.json`/`*-funnel.json`, events/status và
`prepared-v1/*/seal.json` giữ numerical/provenance; raw prices không đưa lênGit.

Nguồn luật hiện hành đã đối chiếu: [FTMOnews](https://ftmo.com/faq/can-i-trade-news/)
và [symbolspec/sessions](https://ftmo.com/en/symbols/). Chúng không thay lịch
known-at 2022–24, biểu phí account hoặc datedsessioncalendar. Không có broker,
provider price fetch, tài khoản mới, B1, XAU hoặc truy cập giá 2025–2026 trong lượt này.
