# Pass 10 · Sàng lọc Stage‑0 cho Engine #2

**Giữ GBPUSD London ORB để xác minh ở M1 Bid/Ask.** Đây là nhánh duy
nhất qua Stage‑0 và vẫn dương sau lát SL ở cả hai cụm. Ghép thử với
USDJPY rút ngắn thời gian dưới đỉnh nhưng làm drawdown tiền đóng sâu
hơn. Chưa đủ bằng chứng để nhận thành Engine #2 đã kiểm định.

Development 2018–2024 đã có exposure. A 2018–2020, B 2021–2024.
[Protocol trước outcome](PASS10-ENGINE2-INSTITUTIONAL-FLOW-STAGE0-PROTOCOL-20261120.md)
ở `99b3051`. Target cost là Standard `36f1535` và Swing `8fd77ef`.

## 1. Chống trùng lặp và nguồn US500 intraday

| Nhánh | Đã có | Delta của Pass 10 |
| --- | --- | --- |
| London ORB FX | [R016/R017 và Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md), [Discovery7](ORB-DISCOVERY7-20261108.md), [Pass 7](PASS7-USDJPY-FULL-M1-EQUITY-AND-FX-SCOUT-20261120.md) | First-touch OCO hộp London 1 giờ, markout trước SL, đối chứng Fade và phí snapshot. Các bản London cũ chờ H1 close và dùng SL 1,5 ATR. Pass 7 dùng hộp Tokyo 3 giờ. |
| NY ORB US500 | [R094/R095](US500-M15-OPENING-SCREEN-PROTOCOL-20261111.md), [R094 afternoon](PROP-US500-R094-AFTERNOON-RESULTS-20261119.md), [multiframe](US500-MULTITIMEFRAME-DRAFT-20261111.md) | Hộp cash 60 phút, first-touch OCO và hard flat 15:55 NY. R094/R095 dùng hộp 15 phút và xác nhận close M15. |
| TOM US500 | [R025](US500-TURN-OF-MONTH-COMPONENT-PROTOCOL-20261108.md) và [source correction](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md) | Mua một vị thế từ D1 open cuối tháng tới D1 close ngày cash thứ ba, tính swap có dấu. R025 tách từng ngày cash và overnight. |

Inventory đã rà R016/R017, R025, R094/R095 và lineage liên quan.
Không thấy recipe exact đã chạy dưới snapshot `36f1535`, nên không
gắn `ALREADY_EXHAUSTED`. Kết luận chỉ áp dụng cho các cấu hình đã khóa.

**NY ORB · `US500_INTRADAY_DATA_GAP_2018_2020`.** QDM CLI 125.2692
liệt kê template instrument `USA500.IDX_dukascopy` và `US500.cash_ftmo`,
nhưng 6 symbol trong kho hiện tại không có series US500. Native FTMO
H1 chỉ có **258 / 259 / 259** nến trong 2018 / 2019 / 2020, tất cả
ở 00:00 giờ server. Repo có hồ sơ M1 Bid/Ask từ kênh trực tiếp cũ,
ngoài bộ đầu vào QDM đã cho phép ở lượt này. Chỉ kiểm metadata QDM,
không export rỗng, không gọi update vì bản CLI không khóa được cận
trên cho tải mới. **0 lệnh NY ORB, PnL N/A.**
[Nguồn CFD](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/?lang=en) ·
[StrategyQuant về giới hạn update](https://strategyquant.com/forum/topic/qdmcli-exe-update-resume-ohne-uberschreiben/).

## 2. Stage‑0 · net stress

Các số cộng USD theo quy ước **1 lot mỗi cơ hội**. Đây là phép
đo kinh tế tín hiệu, không quy về vốn một tài khoản.

| Cấu hình chính / đối chứng | Số mẫu | A · USD | B · USD | Năm dương | Đối chứng A / B | Quyết định |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| London EURUSD · 17:00 London | 1.634 | −6.834,50 | +2.640,50 | 4/7 | Fade −7.265,50 / −21.220,50 USD | REJECTED_AT_STAGE0 |
| London GBPUSD · 17:00 London | 1.605 | +40.323,00 | +24.494,00 | 6/7 | Fade −61.731,00 / −54.446,00 USD | PROMOTE_TO_SL_SLICE |
| US500 NY ORB | — | — | — | — | — | US500_INTRADAY_DATA_GAP_2018_2020 |
| US500 TOM Swing | 83 | +37,42 | −235,56 | 2/7 | REST −4,20 / −0,44 bps/phiên | REJECTED_AT_STAGE0 |
| US500 TOM Standard · đối chứng Friday-flat | 83 | −354,91 | +93,20 | 2/7 | REST +0,02 / −0,44 bps/phiên | CONTROL_ONLY |

### London · các mốc cố định và phí

| Mã | Mốc | Mẫu | Breakout A / B (USD) | Fade A / B (USD) | Năm Breakout dương |
| --- | --- | ---: | --- | --- | ---: |
| EURUSD | +4h | 1.634 | −2.162,50 / −6.660,50 | −11.937,50 / −11.919,50 | 4/7 |
| EURUSD | +8h | 1.630 | −2.211,50 / +11.441,50 | −11.848,50 / −29.981,50 | 4/7 |
| EURUSD | 17:00 London | 1.634 | −6.834,50 / +2.640,50 | −7.265,50 / −21.220,50 | 4/7 |
| GBPUSD | +4h | 1.615 | +30.180,00 / +17.482,00 | −51.908,00 / −47.434,00 | 7/7 |
| GBPUSD | +8h | 1.601 | +34.238,00 / +28.380,00 | −55.518,00 / −58.332,00 | 6/7 |
| GBPUSD | 17:00 London | 1.605 | +40.323,00 / +24.494,00 | −61.731,00 / −54.446,00 | 6/7 |

Mốc 17:00 London là horizon chính đã khóa. GBPUSD còn
**+26.554 USD** sau khi bỏ hai năm tốt nhất. Net trung bình
**+40,38 USD/lot** so với **16 USD/lot** ma sát stress. Hộp trung vị
25,8 pip, phí 1,6 pip bằng **6,20%** hộp, 94,0% mẫu đạt trần
friction/SL 12%. EURUSD có hộp 18,3 pip, phí 1,0 pip bằng **5,46%**
hộp, 96,8% đạt trần 12%. Điểm loại EURUSD là edge sau phí ở Cụm A,
dù quy mô stop đủ lớn.

EURUSD/GBPUSD có 1.635/1.616 first-touch xác định được. Lần lượt
130/173 ngày bị bỏ vì nến first-touch chạm cả hai phía, 51/27 ngày
không chạm và 11/11 ngày thiếu hộp hoặc hộp phẳng. Tại 17:00 London
thiếu đường đủ giá 1/11 cơ hội. Tại +8h bỏ 3/1 cơ hội vì chạm
rollover, và 2/14 vì thiếu đường. H1 dùng Bid + spread snapshot.
Giờ trigger trong bar và spread thực lúc khớp cần M1/tick để xác minh.

### TOM · tác động của carry

Native D1 có nến cho **1.761/1.761** ngày cash trong lịch và định giá
83/83 cửa đủ trong Development. Hai cửa cắt biên mẫu bị loại. Có
1.173 cửa REST bốn phiên, chồng lấn. TOM Swing trước phí
**+521,38 USD/lot**, swap **−545,22 USD/lot**, spread và slippage
**−174,30 USD/lot**. Net còn **−198,14 USD/lot**. Có 63 rollover 3×.
Hai snapshot index áp 3× vào **thứ Sáu** theo spec đích. Cụm A TOM
**−0,13 bps/phiên** so REST **−4,20**. Cụm B TOM **−1,51** so
REST **−0,44**. Tỷ lệ phí trên 2×ATR14 qua cổng, nhưng cơ chế rớt kinh tế
và đối chứng. Kết quả không bao gồm lịch điều chỉnh dividend lịch sử.
Đây là native D1 session close proxy và chưa chứng minh dòng tiền.
[McConnell & Xu](https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf).

Đối chứng Standard sửa lỗi 5 cửa giữ qua cuối tuần khi thứ Sáu là
ngày nghỉ NYSE. Bản cũ có 58 cửa clamp, 5 rollover 3× và net
−210,67 USD/lot. Bản cuối có **63** cửa clamp, **0** rollover 3×
và net **−261,71 USD/lot**. Cả hai bản lưu riêng. TOM Swing và hai
nhánh London khớp nguyên kết quả sau hiệu chỉnh. Standard còn thiếu
quote sát giờ đóng và lịch news/closure đích để kiểm funded.

## 3. Lát SL và tính bổ trợ của GBPUSD

Chỉ chạy opposite-edge SL + flat 17:00 London. **828** lệnh thoát
qua SL hoặc gap, **777** hết phiên. Sizing 0,30% vốn danh nghĩa,
round down 0,01 lot, không có lệnh vướng min lot hoặc thiếu margin
khi xét từng lệnh. Margin đỉnh ước tính **1.344 USD** trên Swing 10k
và **3.405 USD** trên Swing 25k. Cash lũy kế mô hình theo sizing
này lần lượt **+4.993,90** và **+12.735,55 USD** trong bảy năm
trước kiểm tra dùng chung vốn.

| Năm/cụm | Lệnh GBPUSD | GBPUSD Stage‑0 net (USD/lot) | EURUSD Stage‑0 net (USD/lot) | GBPUSD SL net (R) | TOM Swing net (USD/lot) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2018 | 233 | +10.833,50 | +2.717,50 | +47,86 | −241,84 |
| 2019 | 208 | +9.473,50 | −4.240,00 | +4,68 | −84,63 |
| 2020 | 228 | +20.016,00 | −5.312,00 | +57,10 | +363,88 |
| 2021 | 232 | +4.411,50 | +1.745,00 | +10,83 | −114,42 |
| 2022 | 238 | +18.247,00 | +1.677,00 | +51,48 | −18,49 |
| 2023 | 231 | +3.641,50 | +2.160,50 | +13,96 | +70,98 |
| 2024 | 235 | −1.806,00 | −2.942,00 | −4,67 | −173,64 |
| A | 669 | +40.323,00 | −6.834,50 | +109,64 | +37,42 |
| B | 936 | +24.494,00 | +2.640,50 | +71,60 | −235,56 |

R dùng khoảng cách đến SL cấu trúc làm mẫu số, net đã trừ phí.
Tổng là **+181,24R trên 1.605 lệnh**, **+0,113R/lệnh**, 6/7 năm dương.
2024 âm cả raw và sau SL. Không đổi side, SL hoặc giờ để cứu năm đó.

### Cùng ngày bao phủ với USDJPY Pass 7B Stress_05

Tái dựng được 1.334 ngày USDJPY đủ đường bằng đồng hồ M1, đối soát
từng năm với receipt Pass 7B. GBPUSD có 1.805 ngày đánh giá được
gồm no-touch và dual-touch bỏ theo mô hình. Dùng **1.324 ngày giao**,
bỏ 8 cơ hội USDJPY và 428 cơ hội GBPUSD ngoài phần giao. Ngày có
coverage và không có lệnh dùng 0. Tuần ISO cộng các ngày được ghép.

| Điều kiện | Ngày hoặc tuần | Pearson | Cùng lỗ | GBPUSD lãi |
| --- | ---: | ---: | ---: | ---: |
| Ngày, toàn bộ phần giao | 1.324 | +0,052 | 380 | 454 |
| Ngày USDJPY lỗ | 663 | −0,012 | 380 | 214 |
| Tuần, toàn bộ phần giao | 342 | +0,063 | 83 | 157 |
| Tuần USDJPY lỗ | 164 | +0,012 | 83 | 81 |

GBPUSD đóng góp **+146,55 USD** trong 663 ngày USDJPY âm và
**+1.019,50 USD** trong 164 tuần USDJPY âm. Tương quan gần 0 cho thấy
có cơ hội đa dạng hóa. Hai nhánh vẫn cùng lỗ trong 57,3% số ngày
USDJPY thua.

| Cash trên ngày giao | Net USD | Max cash DD USD | Net / DD | Dưới đỉnh dài nhất |
| --- | ---: | ---: | ---: | ---: |
| USDJPY | +2.374,29 | 612,13 | 3,88 | 637 ngày / 20,93 tháng |
| GBPUSD | +2.570,64 | 890,43 | 2,89 | 627 ngày / 20,60 tháng |
| Cộng hai nhánh | +4.944,92 | 940,97 | 5,26 | 516 ngày / 16,95 tháng |

Underwater tiền đóng giảm **121 ngày (~3,98 tháng)** và Net/DD tăng
**35,5%**, đồng thời Max DD sâu thêm **328,84 USD (+53,7%)**.
Mỗi nhánh dùng cùng 30 USD rủi ro danh nghĩa trên sổ tham chiếu 10k,
nên hai nhánh có thể dùng tổng ngân sách danh nghĩa 60 USD khi cùng
mở. So sánh dùng cash đóng theo ngày và một cơ sở vốn cố định.
Mốc **21,12 tháng** gốc là floating của sổ USDJPY đầy đủ với sizing
theo số dư. So sánh cùng đơn vị trong bảng bắt đầu ở **20,93 tháng**;
chưa đo floating, Daily Loss hay margin đồng thời của danh mục mới.

## 4. Phán quyết Pass 11

Chỉ đưa **GBPUSD London ORB** sang bước xác minh execution trên giá
M1 Bid/Ask hoặc tick 2018–2024 bằng export QDM có cận trên đã kiểm.
Giữ luật nguyên bản. Đối chiếu đặc biệt 173 ngày H1 chạm hai cạnh,
giá gap/SL, spread giờ London và năm 2024. Nếu còn edge, dùng
đường vốn theo thời gian để so cùng **tổng ngân sách rủi ro** với
USDJPY solo, đo Daily/Overall loss và margin đồng thời rồi mới
đánh giá tiến độ Challenge. Hạ tầng QDM hiện có template GBPUSD
nhưng chưa có series GBPUSD trong kho symbol được kiểm. Holdout
chưa dùng cho bất kỳ quyết định nào ở Pass 10.

## 5. Kiểm chứng

Bộ quant đầy đủ đạt **1.496 bài, 0 skip, 0 fail**. Lần đầu
gặp WinError 32 lúc một test observer cũ dọn file Parquet tạm. Test đó
qua khi chạy riêng và toàn bộ suite qua khi chạy lại trong thư mục tạm
của job. Log hai lần được lưu để đối soát.

Đối chiếu được từng ledger giá/chi phí, timestamp đã sử dụng sớm hơn
01/01/2025 và SHA của nguồn, fee spec, lịch và ledger tham chiếu.
0 giá holdout, 0 OrderSend, pin Trader và WIP VI Dubber được giữ.
SHA256 của Markdown/JSON tính trên bytes blob Git (xuống dòng LF).
