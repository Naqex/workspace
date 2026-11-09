# R084 USDJPY Tokyo: bản mua chính không đạt, có hướng cần kiểm tiếp

09/11/2026. [Protocol](USDJPY-TOKYO-COMPONENT-PROTOCOL-20261109.md) đã commit
`615ebc5` trước thu giá mới; [method](TOKYO-FIX-METHOD-ADMISSION-20261109.md)
và [pilot](USDJPY-TOKYO-SOURCE-RESULTS-20261109.md). Đây là own adaptation
trong họ R020/R021, không replication paper, independent edge hoặc clean OOS.

## Quyết định dễ hiểu

**Bản chính mua USDJPY 09:26→09:54 Tokyo không qua chi phí cao ở cả hai năm.**
Không thay lịch phụ hoặc chiều bán thành winner sau khi thấy kết quả.
Tuy vậy, giữ hai phát hiện có ích: bản lịch phụ mua trước fix dương và phép
đối chứng bán sau fix dương. Chúng chỉ cho lý do đăng ký kiểm thêm, chưa đủ
SL/account/prop/forward hoặc đề xuất challenge. Goal C1/C2 vẫn mở.

Đơn vị dưới đây là **100.000 USD notional cố định cho mỗi lượt**, không vốn
account 10.000 USD, %return, mức risk hoặc lot đề xuất. Lời/lỗ đã quy về USD
tại exit mid; đây là approximation, không broker conversion certificate.

| Quy tắc / lịch | Số lượt 2019 / 2022 | Net chuẩn 2019 / 2022 (USD) | Net cao 2019 / 2022 (USD) | Vai trò / quyết định |
|---|---:|---:|---:|---|
| Mua trước fix, chỉ ngày danh nghĩa là ngày làm việc | 49 / 46 | +54,67 / −2,79 | −125,18 / −142,93 | Primary: không đạt |
| Mua trước fix, chuyển ngày nghỉ về ngày làm việc trước | 69 / 70 | +631,64 / +837,59 | +378,34 / +623,61 | Sensitivity: follow-up flag, không promote primary |
| Bán trước fix, lịch chính | 49 / 46 | −781,53 / −952,80 | −961,39 / −1.092,93 | Opposite control: không cứu bản mua |
| Bán sau fix 09:56→10:24, lịch chính | 49 / 46 | +267,22 / +1.430,15 | +87,33 / +1.289,95 | Diagnostic control: có lý do đăng ký temporal extension mới |
| Bán sau fix, lịch phụ | 69 / 70 | +407,68 / +2.233,47 | +154,33 / +2.019,37 | Không tự nâng thành bản chính |
| Bán trước fix, lịch phụ | 69 / 70 | −1.663,98 / −2.288,36 | −1.917,27 / −2.502,35 | Control âm |
| Không giao dịch, cả hai lịch | 0 / 0 | 0 / 0 | 0 / 0 | Null, vẫn giữ diagnostics chất lượng nguồn |

Phí: spread từ Ask/Bid, commission 5 USD/100k roundtrip; chuẩn slip0, cao
thêm0,4pip roundtrip. Không actual targetbrokerfees hoặc observed slippage.
SumUSD và sumpips được đối soát riêng từng row. Ví dụ mua chính năm2022 net
chuẩn −2,79USD nhưng +14,83pip: conversion từng ngày khác nhau; không đổi
aggregatepip bằng FXrate trung bình để ép hai dấu phải giống nhau.

## Tại sao bản chính không đạt và bản bán chưa đủ thuyết phục?

| Năm, mua chính | Gross trước spread/phí USD | Spread | Commission | Slip stress | Net stress |
|---|---:|---:|---:|---:|---:|
| 2019 | +418,10 | 118,43 | 245,00 | 179,86 | −125,18 |
| 2022 | +475,00 | 247,79 | 230,00 | 140,14 | −142,93 |

Cả hai gross dương nhưng không đủ trả tổng chi phí đã đăng ký. Không giảm
commission/slippage hoặc sửa cửa giờ để cứu kết quả. Lịch phụ khác cohort,
không chứng minh mọi doanh nghiệp chuyển thanh toán về ngày trước.

Bán sau fix lịch chính năm2019 chỉ +1,78USD trung bình mỗi lượt sau stress;
median −10,55USD,22/49lượt dương. Năm2022 trung bình +28,04USD, median
+36,46USD,30/46lượt dương. Top5lượt dương chiếm60,79%/40,47% **tổng đóng góp
dương** từng năm (không lấy net PnL làm mẫu số). Có phụ thuộc ít lượt và khác
biệt giai đoạn: cần lịch sử rộng hơn, không chọn chỉ năm đẹp hoặc tự suy
profit component thành xác suất pass quỹ. Các giá trị này chưa có protectiveSL.

## Kiểm dữ liệu, số học và thời gian

| Lát | Bằng chứng đã kiểm | Giới hạn |
|---|---|---|
| Lịch | CSV official38holidays; generator và calendar oracle độc lập bằng businessday enumeration/bisect khớp toàn bộ mapping;49/46primary,69/70sensitivity,139uniondates | Declared bank calendar, chưa PIT/all-bank payment/fix publication proof |
| Golden Week/Christmas | 05/05/2019 và30/04 cùng về26/04, dedup;25/12 loại trước shift; không sourceyear ngoài registration | Không thêm EOM31, không điều chỉnh theo quotes |
| Nguồn | 278rawday-sides;380.638native bars/379.924explicit bars,714padding không coi là observed quote; full1.899.620OHLCV field comparisons Fraction/native | Same provider, M1 sideOpen/Close chưa jointtick/exactfill |
| Holding roles | Tất cả139days có đủ29minutes×2sides cho cả prefix vàpostfix; không missing/crossed Open/Close; không drop ngày sau kết quả | Không suy bound extrema/jointmid path hoặc broker stop fills |
| Financial | 32books,18.720field cash-oracle checks, midpoint producer so side-fill arithmetic oracle; gross/spread/fees/slip/USD/pips/strictN/A/null/counts | Books overlap/costs/controls, không32 independent edges |
| Preflight | 13synthetic/calendar checks;10mutations bị executable validator từ chối trước thu giá mới | Cùng agent, không independent reviewer/feed |
| Final mutations | Thêmnativeprice/time,JPYgrid,actualcash: tổng14rejections | Không chứng nhận toàn bộ trading engine |
| Source | 116,915s wall /7,767s CPU;278day-side accesses gồm4cachehits,274new fetches,0failure | Không source retry/WAF/auth; max300s |
| Bind/preflight | 1,873s wall trong consumer | Không research/code/Git time |
| Fullsource review/newroles | 25,708s wall | Chỉ workload đã đo |
| Compute+financialreview/mutations | 0,610s wall | Không benchmark speedup với batch khác |
| Tổng consumer | 28,191s wall /27,375s CPU;0network/broker/model calls | Source+consumer khoảng145,106s; không gồm thời gian thiết kế/code/Git |

Consumer chạy với network-denied socketguard; không2025+/holdout, broker,
model/provider trả phí hoặc permission mở mới. Pin protocol/code/config/raw/
seals/snapshots trước/sau; không sửa raw hoặc kết quả pilot cũ.

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/jpy-tokyo-preflight-v1/`, `jpy-tokyo-calendar-v1/`,
`jpy-tokyo-source-v1/`, `jpy-tokyo-component-v1/`. Source/component đã terminal
`completed_reviewed`, không còn job của R084. RowsSHA
`589ba6eac298f342a796bee9e28ed6c615e6466c0d752aadcec5fed34ede41f2`;
reviewerSHA `a02fe99cd215ecea9e54a8d7abfe52cbdb3dbc0f694081a6e8f3305f86718897`.

## Hậu kiểm và bước tiếp

| Điểm | Quyết định |
|---|---|
| Correctness | Không phát hiện lỗi material trong scope; giữ gate false của primary và true riêng của sensitivity |
| Performance | Numeric/review dưới30s, source dưới2phút; reuse4pilotraw. Chưa có lý do thêm GPU/Rust/parallel fetch hoặc giảm checks |
| Workflow/skills | Kế thừa audit gần nhất, một branch/PR cho đợt; không thêm issue/skill/framework. Context route tới kết quả mới, archive cũ giữ |
| Selection | Bán sau fix chỉ là control đã thấy kết quả; nếu kiểm tiếp phải ghi selection và freeze protocol mới trước outcomes ở năm khác |

Ưu tiên đăng ký **temporal extension bán sau fix**, cùng slot/fees/calendar
chính, thêm lịch phụ riêng; rộng giai đoạn trước thiết kế SL/risk. Giữ2019/2022
là discovery/exposed, không gọi lại là OOS. Không loại cả fixing family, không
retune prefix BUY, không mua/cài EA. Catalogue84records/58policy-modelversions/
25native/9controls; thêm component liên quan R021, không account policy mới.
