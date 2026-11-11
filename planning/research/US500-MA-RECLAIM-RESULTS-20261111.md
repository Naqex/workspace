# R123: nhiều lệnh hơn nhưng không giữ được lợi nhuận khi tăng chi phí

11/11/2026. [Protocol trước kết quả](US500-MA-RECLAIM-PROTOCOL-20261111.md),
[đăng ký G2 screen riêng](US500-MA-RECLAIM-COST-SCREEN-REGISTRATION-20261111.json),
[lý do tách hai stage](US500-MA-RECLAIM-COST-SCREEN-AMENDMENT-20261111.md).

## Kết quả dễ đọc

Luật BUY: xu hướng SMA20>SMA80, giá đóng xuống MA20, rồi nến M15 sau đóng trở
lại trên MA20 cộng0,10armATR. SELL đối xứng. Không cần vượt armbarhigh/low.
Setup10:00–14:00NY,confirm≤15:00,exit15:31hoặc mất hướng/SL;1attempt/ngày.
Risk≤25USD trên mỗi annualbook10.000USD, không risk thật owner đã chọn.

| Năm | Số lệnh mỗi cost | Net chuẩn | Net chi phí cao |
|---|---:|---:|---:|
|2022|58|−117,60USD|−158,29USD|
|2023|50|+65,98USD|−58,09USD|
|2024|57|+56,45USD|−90,65USD|
|**Tổng mô tả3sổ năm**|**165**|**+4,83USD**|**−307,03USD**|

Annualreset10k mỗi năm; tổng không là account liên tục/CAGR. Chuẩn/stress dùng
pairedBidAsk embeddedspread, commission0 scenario, adverse extra slip.25/.75point
mỗi fill. Nativestop/gap/quantity giữ declaredmodel, không exact targetFTMO feed.

**Không giữ exactrecipe để tiến tới challenge/kiểm định sâu.** Chuẩn gần hòa,
stress âm cả3năm, số lệnh khoảng1/tuần vẫn thấp hơn dải3–8/tuần mới đề xuất cho
mục tiêu nguồn thu chính. Đây là research-priority decision trong assumptions,
không chứng minh cả họ pullback hoặcUS500 không có edge.

## So với phép đo trước

FP02 có396setup/93arm-extreme confirmations. Giữ đúng timestamp/side của396
setups đó, R123/FP05 đổi sang closed-MA reclaim cho165confirm(58/50/57).
Trong396setup mới:165confirm,222expiry,8trendcancel,1gapcancel. Không rearm để
ép count, không xóa losers hoặc gọi93→165 là profit improvement.

Attempt đầu `us500-ma-reclaim-v1` đã dừng đúng priorityfloor200:165signals,
0financialbooks. Attempt này giữ nguyên. Sau đó **trước PnL mới**, đã đăng ký
riêng một G2 exploratorycostscreen qua binding originalmanifest/result hashes.
Lý do: trước đây đã đề xuất50–100screening,200–500deepreview; chặn mọi phép kiểm
chi phí vì chưa200 là trộn hai stage. `frequency_eligible=false` vẫn giữ,
không hạ floor hoặc gọi originalattempt là pass. Adaptive stage decision sau
khi biết count được ghi rõ, không gọi là preregistered từ trước count165.

## BUY/SELL và chi phí

| Tổng3sổ năm | Số lệnh | Chuẩn | Chi phí cao |
|---|---:|---:|---:|
|BUY|88|−12,88USD|−123,10USD|
|SELL|77|+17,71USD|−183,93USD|

Thấy SELL chuẩn dương không cho phép bỏ BUY để gọi bản mới đã kiểm định.
Mean observed net chuẩn khoảng0,03USD/lệnh, stress khoảng−1,86USD/lệnh;
không coi samplemean là expectedfutureedge hoặc chỉ tăngsize để kiếm thu nhập.
Chi phí thay entryfill→stop/quantity và có thể exitreason, nên không lấy
stress−reference làm phí cộng thêm trên cùng lot/path. Không claim profit
nếu bỏ phí; parent storedfills vẫn phản ánh costs đã khóa.

## Những gì đã kiểm

- NativeNautilus1.231.0 quản events/orders/matching/positions/cash, reuse Cfd
  INDEX1USD/point/lot và shared execution. Chỉ thêm offline policy injection,
  legacy default giữ nguyên. Không cutover product/live hoặc broker calls.
- 6financialbooks+3null completed và execution/cash/closedbar signal/earliest
  confirmation/exit-clock review đạt.3null khôngorders/khôngPnL. Source seals
  và native-vs-frequency timestamp/side traces khớp cho9books.
- 165actualtrades ở mỗi cost,0riskreject/0openposition cuối/0unresolved heldpaths.
  Đây là complete observedM1 coverage, không exact intraminute tickpath hoặc
  đầy đủ daily/overall equity/news/closure/targetbroker compliance.
- 16R123/scopedregistration tests đạt;23parent tests và1CLI recovery test đạt
  sau thêm optional policy injection. Bao gồm wrong clock/signal mutation,
  dynamicclosedMA/frozenATR, equality/no samebar, lateexit, stops/gaps,
  missed exactexit→recovery vẫn unknown, futuregap sau stop không đổi knownpath.
- Mean/accounting net dùng independent Decimal cent rounding. Native2023reference
  lệch+0,01USD do nativeMoney halfcentfloat; đã đối soát từng position≤1cent và
  nativecash=sum nativeclosed events. Các sổ khác delta0. Không giấu bằng tolerance lớn.

Correctness là scoped same-agent/separate-code-path evidence, không independent
human/feed audit. Không mở2025+ hoặc xét statisticaledge/OOS/challengeauthority.

## Thời gian và bài học kỹ thuật

| Phase của costscreen | Wall |
|---|---:|
|Source validation/preparation3năm dùng chung|23,95s|
|Frequency/setup-trace parity|0,15s|
|Nativequote preparation|2,89s|
|9native simulations, gồm3null|58,14s|
|9reviews/artifactwrite|2,66s|
|**Toàn costscreen**|**88,02s**|
|Attempt frequency đầu, đã giữ riêng|43,26s|
|Code/research/kiểm/Git/report|Chưa đo riêng|

Không cộng overlap hoặc nói toàn task mất88s. Frequency attempt và costscreen
có nguồn/registration mới, không lấy43→88 làm speedup; source/preparation reuse
giữa các books trong cùng attempt. Không cần thêmGPU/Rust/engine hoặc skill mới.

Bài học quy trình: tách G1/G2 cheapscreen khỏi G3deepreview; sample/planning
floor không là tem edge. Đã giữ originalfloor/attempt và newstage registration
riêng. Không chỉnh chiến lược chỉ để đạt số lệnh tối thiểu. Giữ đồng thời
[phân tích cadence/thu nhập](DAYTRADING-INCOME-CADENCE-20261111.md) theo steering mới.

## Trạng thái và việc tiếp

R123 là một related ruleversion mới củaR004/R098/FP02, không edge độc lập;
FP05 frequencydesign cũng được lưu, không erase4frequencyprobes trước. Catalogue
123records/88policy-modelversions/53native. Không challenge candidate mới.
Không chạy lại version không đổi hoặc quét tiếp MA/SL/TP/giờ để cứu.

Bước sau cần admission một hypothesis có cơ chế và cadence hợp mục tiêu trước
khi triển khai, không chọn theo profit của vài subgroup. Thiếu equity/prop/
forward/ownerhandover vẫn là gate riêng nếu sau này có candidate qua screening.

Evidence private tại campaign `execution-v1/`:

- `us500-ma-reclaim-v1`: frozenfrequencyattempt165, priorityfalse,0books.
- `us500-ma-reclaim-cost-screen-v1`: manifest/snapshots,frequencygate,
  9books/reviews/metrics/seals,result/events/progress/timers.
- `final-artifact-audit.json` trong costscreen:9seals/trace/census/side sums/null.
- `income-cadence-scenarios.json`: planning math, không phải forecast từ R123.

Code/protocol trướccount commit`d13deeb`; scopedcostscreen commit`9a08df4`
trước financial outcomes. Không writer/job còn chạy; oldresults/negatives giữ.
