# Phễu EURUSD B0 và mức sẵn sàng của vàng intraday

**Quyết định: NO-GO cho việc chạy EURUSD B1 ở thời điểm này. Đề xuất hủy lượt
thử B1 chưa dùng, giữ ngân sách; chuyển sang duyệt card XAUUSD A0 trước khi chạy.**
Đây là quyết định phân bổ nghiên cứu, không chứng minh EURUSD không thể có edge.

PR71 đã merge vào `main` tại `7d29ce4`; nhánh `codex/eurusd-b0-study` đã xóa
local/remote sau ancestry và remote-tip checks. B0 được owner gác với hai nhãn
`CADENCE_OR_SAMPLE_SHORTFALL` + `DATA_PATH_INCOMPLETE`. Trạng thái quỹ vẫn là
`PROP_UNMEASURED`, không phải đã đo và vi phạm quỹ.

[Protocol audit](EURUSD-FUNNEL-AUDIT-PROTOCOL-20261113.md) ·
[JSON, input/code hashes và quality census](EURUSD-FUNNEL-AUDIT-RESULTS-20261113.json) ·
[Card XAUUSD Intraday B0/A0 chờ duyệt](XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md).

## 1. Sửa mẫu số: 455 vùng không có tín hiệu, không phải 450

Một vùng/ngày có thể tạo nhiều lần thử. Trên Development 2022–2023:

- 517 vùng hợp lệ →279 vùng có ít nhất một setup đúng bias/breakout →175 vùng
  chạm lại vùng theo luật →62 vùng có ít nhất một xác nhận →24 vùng có lệnh vào.
- 62 vùng có xác nhận tạo **67 sự kiện tín hiệu**. Vì vậy không lấy517−67 để
  tính số ngày bị loại: đúng là 517−62=**455 vùng, tương đương88,01%**.
- 67 tín hiệu gồm43 bị chặn phí và 24 được nhận.43 tín hiệu bị chặn nằm trên39 ngày;
  một ngày trong số đó có tín hiệu khác được nhận. Do đó 38 vùng xác nhận
  không có lệnh vì phí, không phải43 vùng.

Bảng dưới phân loại mỗi vùng theo tầng xa nhất thực tế đã đạt. Một ngày có
nhiều lần thử vẫn chỉ xuất hiện một lần trong bảng này.

| Tầng dừng của vùng |2022|2023|Tổng|
|---|---:|---:|---:|
|Có phá vùng theo giá, nhưng không khớp H1 bias ban đầu|103|98|201|
|Không có geometric breakout theo biên ATR của B0|20|17|37|
|Có setup đúng hướng, không chạm retest trong4 bar/trước11:00London|50|51|101|
|H1 bias đổi trong lúc chờ retest|0|3|3|
|Có retest được nhận, nhưng không lần nào đủ nến xác nhận|55|58|113|
|Có ít nhất một tín hiệu xác nhận trước phí|30|32|62|
|**Tổng vùng hợp lệ**|**258**|**259**|**517**|

201 vùng bị chặn ở bias gồm:69 chỉ gặp bias neutral/unavailable;61 chỉ gặp
breakout ngược bias;71 gặp cả hai kiểu.37 vùng chưa phá giá được tách riêng,
không gán nhầm thành lỗi bộ lọc bias.3 vùng đổi bias được tách khỏi101 vùng
hết hạn không retest. Không suy ra “giá chạy thẳng có lời”: chưa đo điều đó.
Kiểm sâu các bar breakout bị chặn cho thấy371 bar năm2022 và 313 bar năm2023
có H1 thực sự neutral theo rule; **không có ngày nào trong nhóm no-setup này
bị thiếu H1 đã admit**. Không gán nhầm neutral thành feedgap.

## 2. Cấp setup: vì sao số lần rớt lớn hơn số ngày?

| Kết cục của từng setup đã lưu |2022|2023|Tổng|
|---|---:|---:|---:|
|Không chạm lại trong4nến|68|61|129|
|Không chạm lại trước cutoff11:00London|68|83|151|
|Bias đổi khi chờ|0|3|3|
|Chạm lại nhưng nến xác nhận không đạt|94|100|194|
|Chạm lại và đủ xác nhận|31|36|67|
|**Tổng setup đúng bias+breakout**|**261**|**283**|**544**|

544 setup không phải544 ngày. Trong261 lần chạm đầu tiên,194 không đạt trigger:
**60 chỉ không đạt màu/thân nến** (đã reclaim đúng phía biên),134 không đạt cả
reclaim lẫn màu nến;0 chỉ không đạt reclaim. Các số này tái dựng đúng priority
của B0: cutoff →data availability →bias →first touch →confirmation →expiry.
Mọi counter và 67 timestamp tín hiệu đều khớp artifact B0 gốc; không tạo lệnh mới.

## 3. 43 tín hiệu bị bộ lọc phí loại

| Nhóm |SL tự nhiên trung vị bị loại|Ngưỡng SL cần thiết trung vị|Khoảng ngưỡng theo spread|
|---|---:|---:|---:|
|2022:18 tín hiệu|6,95 pip|9,80 pip|8,20–11,40 pip|
|2023:25 tín hiệu|5,40 pip|8,20 pip|7,30–10,70 pip|
|**Gộp43 tín hiệu**|**6,00 pip**|**9,00 pip**|**7,30–11,40 pip**|

Không có một SL tối thiểu chung cho mọi quote. Ngưỡng thay đổi theo entryspread,
phí 9 USD/lot, ngân sách150 USD và lotfloor. Với d là stopdistance theo đơn vị
0,00001 và s là entryspread cùng đơn vị, native sizing cho số bước0,01 lot:

`steps=floor(15000/(d+10)); plannedF_cents=steps×(s+9)≤1800`.

Trong d+10 đã có 9 USD/lot phí và 1grid dự phòng. Kiểm lại43 rejects bằng bất
đẳng thức này đều khớp. Ví dụ spread0,1 pip cần SL từ 7,3 pip; spread0,2 pip cần
từ 8,2 pip trong đúng model/lotfloor này. Đây là toán giải thích lý do bỏ lệnh,
**không phải đề xuất nới SL tự nhiên** hoặc sửa cap12%.

## 4. Go / No-Go B1: điều gì được và chưa được chứng minh?

Thay đổi nhỏ dễ nghĩ tới nhất là bỏ điều kiện màu nến, giữ reclaim. Trên
**cohort setup đã lưu**, nó chỉ mở thêm60 sự kiện. Ngay cả giả định rất ưu ái
rằng cả 60 đều qua phí và vẫn giữ 24 fills cũ, chỉ có 84cơ hội trong2 năm, tức
42/năm — chưa tới60–80. Đây là phép đếm sức chứa của cohort cố định, **không
phải backtest hoặc upperbound của toàn bộ đường B1**: lệnh mới có thể thay
occupancy/eligibility và tạo đường sự kiện khác.

Bỏ retest hoặc bỏ H1 bias có thể mở rộng cơ hội về mặt hình học, nhưng chưa
có bằng chứng cùng lúc nâng expectancy, SL phù hợp và cadence sau phí.
Vào ngay breakout còn cần một SL không dựa vào nến retest tương lai, nên
không thể xem đó là thay một dòng rồi kế thừa kết quả B0. Không chạy các
phương án này hoặc đo markout để chọn thắng trong lượt audit.

Do đó **chưa có một thay đổi đơn lẻ được dữ liệu hiện tại bảo vệ cho cả hai
mục tiêu**: đủ tần suất và biên lợi nhuận cao hơn rõ rệt. Khuyến nghị hủy quyền
thử EURUSD B1 chưa dùng; trạng thái là `retirement_recommended`, chờ quyết định
owner, không tự dùng ngân sách đó để thêm các bản vàng. B0 vẫn giữ làm evidence.

Điều này không chứng minh biên độ toàn thị trường EURUSD luôn quá hẹp hoặc mọi
chiến lược EURUSD đều thất bại. Cũng chưa có ablation xác định riêng capF/R
đã gây toàn bộ cải thiện gross so Catalogue13: bộ luật, sample và period khác
nhau. Giá trị đã thấy của framework là admission/đơn vị/log minh bạch; alpha
vẫn phải được kiểm riêng. Không dùng2024 để chọn hoặc cứu thiết kế B1.

## 5. XAUUSD M1: kiểm07:00–21:00UTC,2022–2024

Tái sử dụng timestamp cache đã sealed của nguồn M1 Bid, kiểm raw SHA và đối
chiếu **toàn bộ 1.063.493timestamp2022–2024 với CSV gốc**, khớp từng dòng.
Không decode OHLC/Ask để nghiên cứu giá; hash chỉ đọc bytes của file đã admit
kết thúc2024. Phần này là chất lượng dữ liệu vàng được owner giao, không phải mở EURUSD2024.

Mẫu số là weekday windows, mỗi ngày840 phút; **có giữ ngày nghỉ chưa xác minh**.
Một gap ở đây là chuỗi thiếu **hơn15 phút M1 liên tiếp**; đã kiểm riêng trường
hợp15/16 phút. Với cách thường dùng là interbar spacing>15 phút, không có gap
nội phiên dài như vậy trong các ngày có nến; cách đó không phát hiện ngày trống.

| Năm |Ngày trong tuần|Ngày có missingrun>15 phút|Trống cả khung|Thiếu ở biên khung, ngày còn dữ liệu|Gap giữa phiên>15 phút|Tỷ lệ phút có bản ghi|
|---|---:|---:|---:|---:|---:|---:|
|2022|260|10|2|8|0|98,72%|
|2023|260|11|3|8|0|98,26%|
|2024|262|12|3|9|0|98,36%|
|**Tổng**|**782**|**33**|**8**|**25**|**0**|—|

33 ngày đều là trống cả ngày hoặc thiếu cuối khung giờ. Nhiều ngày trùng dịp
nghỉ Mỹ/cuối năm, nhưng chưa bind lịch đóng cửa đúng provider/account/date.
Vì vậy **không gọi33 ngày là 33lỗi feed**, và 98,x% là coverage của lưới giờ đã
đặt, không phải tỷ lệ dữ liệu đủ trên mọi giờ thị trường thực sự mở.

M1 Bid đủ để chuẩn bị feature/count-only sau khi card được duyệt, nhưng chưa
chứng nhận execution: còn missingminutes nhỏ, timestamp/source semantics,
observedAsk/tick, ambiguitySLTP và datedcalendar/news. Không dùng0gap>15 phút
làm dấu pass toàn bộ đường vốn. Chưa có tín hiệu vàng, netPnL hoặc backtest mới.

## 6. Card hướng A và những sửa cần giữ

[Đặc tả A0 riêng](XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md) đề xuất H1 SMA20 bias →
M15 pullback/reclaim quanhSMA20±0,20ATR →SL tự nhiên ±0,10ATR →TP2Rprice;
entry09:00–16:00UTC, giữ tối đa 120 phút, flat chậm nhất18UTC hoặc sớm hơn theo
calendar/news. Một baseline, không grid; **chờ owner duyệt trước mọi strategy run**.

- Không chuyển tỷ lệ phí 6,4% của R043 multiday sang vàng intraday. Đóng sớm thay
  cả returns/trades; không cộng lại swap8.950 USD cũ vào alpha mới.
- Không hard-code rollover22UTC. [FTMO12/11/2026](https://ftmo.com/en/blog/trading-updates/trading-update-12-nov-2026/)
  dùng GMT+2 và có lịch metals đóng sớm; không phải lịch historical2022–2024.
- [Biểu phí công bố25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
  là 0,0007%notional/side với metals; phải capture đúng account trước dispatch,
  không lấy fixed5 USD/lot cũ làm phí vàng FTMO. Reference/stress đề xuất nằm
  trong card; stress slip0,20 USD/oz/side tương đương40 USD/lot/cảvòng khiC=100 oz.
- NativeMetalMarket cũ dùng commission cố định theo lot. Nếu dùng notionalfee
  cần chứng minh accounting hai phía/known-atreserve bằng fixtures trước PnL;
  chưa có adapter A0 hoặc chứng nhận native hỗ trợ đầy đủ card này.

## Evidence, thời gian, giới hạn

Audit EURUSD chỉ dùng sealed2022–2023 và warmup2021 cho initialization; không
đọc EURUSD2024 hoặc giá 2025–2026. Dùng code indicators trùng frozen B0, kiểm
rawhash và trường hợp LF/CRLF; không sửa baseline/raw/result. Privateaudit giữ
từng zone/setup/rejectedintent, input/code hashes và event/status.

- 8fixtures mới đạt: đếm trùngzone, biaspriority, lotfloor threshold, khóa2024,
  gap15/16 phút, empty/boundarywindows. Counterparity đầy đủ 544setups/67 signals.
- Audit đếm EURUSD: khoảng0,27s; Kiểm timestamp vàng:2,61s, chưa
  gồm lần kiểm lại CSV và thời gian research/code/Git. Không gọi đây là thời
  gian end-to-end toàn task hoặc benchmark nhanh hơn backtest.
- Same-agent/same-feed review, không independent feed/reviewer. Không broker,
  providerprice fetch, PnL mới, B1, backtest vàng hoặc freshholdout.

Privatebase:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`:
`eurusd-b0-funnel-audit-20261113/attempt-1` và
`xauusd-intraday-readiness-20261113/attempt-1`. Nguyên trạng oldB0 giữ ở parent.
