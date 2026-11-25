# EURUSD PreECB R056 | Phần lợi nhuận còn lại sau chia lot và stop

19/11/2026 · **Gác PreECB R056 cho mục tiêu payout.** Giữ cấu hình và lot
đã khóa, hai cụm Development cho **39,89 và 56,26 USD/năm** dưới mô hình
phí của BASE. Tương đương **0,399% và 0,563%/năm** trên sổ tham chiếu
10.000 USD. Hai cụm đều hụt mức 2%/năm (200 USD ở sổ gốc hoặc 1.000 USD
ở sổ 50.000 USD). Kết quả gác của ATR parent, R056, R057/R058 và lần
thử thoát 14:15 được giữ. BASE_GUARD vẫn `NOT_QUALIFIED`.

## Phép so dùng đúng cùng cơ hội

PreECB bán EURUSD vào **02:00 New York** và thoát **14:00 Berlin** mỗi
ngày trong tuần nếu đủ điều kiện nguồn. Tên PreECB dùng để gọi cửa sổ
theo giờ, dù ngày đó có lịch ECB hay không. R056 đặt stop theo 2 lần
RMS của biến động 20 phiên đã hoàn tất. Lot làm tròn xuống 0,01 theo
rủi ro tối đa **25 USD/lệnh** trên sổ 10k với leverage giả định 1:30.
Lượt này giữ risk, cơ chế stop và sizing. Mức 150 USD của BASE chỉ
thuộc sổ BASE, dùng để tham chiếu các vị thế đã có.

Dùng lại 1.209 lệnh của sổ R056 niêm phong năm 2018–2022. Năm 2023
nối từ cash 11.078,12 USD, trạng thái flat và 20 ngày dự kiến gần nhất
năm 2022. Cùng engine đã khóa, 256 lệnh đóng và 4 ngày bỏ qua vì
thiếu lịch sử. Cash cuối 2023 đạt 11.126,98 USD theo phí R056 gốc.
Sáu file nguồn giá năm 2018–2023 được xác minh SHA256 với cache H1,
gồm đối chiếu thời gian, sequence, Bid/Ask của các điểm vào và thoát
theo giờ với hồ sơ giá cũ.

So sánh ba cách trên 1.460/1.465 ngày có đủ điểm giá và các giờ H1:

1. **R056 có SL.** Giữ nguyên lệnh, giá thoát và lot.
2. **R056 giữ theo giờ.** Cùng entry và lot, dùng Ask đầu phút thoát
   dự kiến cho phép tính độ nhạy. Tách phần ảnh hưởng của stop và thời
   điểm thoát trên cùng lệnh.
3. **SELL ở phiên liền sau.** Từ 14:00 Berlin, giữ thêm đúng số giờ
   dự kiến của PreECB trong cùng ngày. Cùng lot EUR, dự kiến 5–7 giờ
   tùy tuần đổi giờ. Giá vào Bid và thoát Ask đều yêu cầu có quote
   trong phút đầu. Đo độ nhạy theo giờ khi giữ nguyên hướng SELL.

Hai cửa sổ dùng cùng EUR lot-giờ (199,03 / 188,75 theo hai cụm),
notional quy đổi sang USD lệch dưới 0,02%. Thời gian giữ bình quân
khoảng 6 giờ 4–5 phút, chênh dưới một giây giữa hai cửa sổ trong mỗi
cụm. Đối chứng dùng cùng cặp và hướng. Yếu tố USD chung, lịch tin và
dòng giao dịch từng phiên chưa được nhận diện riêng bằng phép so này.
Phân rã hai năm của ATR parent và hồ sơ MAE trước đây là nghiên cứu
kế thừa. [PreECB dài hạn](PRE-ECB-LONG-PRICE-RESULTS-20261108.md) ·
[Attribution ATR](PRE-ECB-WRAPPER-ATTRIBUTION-RESULTS-20261108.md) ·
[Đường giá ATR](PRE-ECB-PATH-RISK-RESULTS-20261108.md) ·
[R056](PRE-ECB-SESSION-RISK-RESULTS-20261108.md).

### Phí, phiên và lịch tin

R056 stress tính 5 USD/lot commission và 4 USD/lot trượt giá vòng
lệnh, swap SELL 20 USD/lot mỗi đơn vị rollover. BASE `SYM_FLAT` dùng
7 USD/lot commission, 2 USD/lot trượt giá, swap 40 USD/lot. Hai mô hình
cùng 9 USD/lot trước làm tròn, cùng spread nằm sẵn trong Bid/Ask.
BASE làm tròn commission từng phía, tạo chênh lệch nhỏ. Phần chênh
còn lại đến từ lệnh giữ quá giờ phải chịu swap. Mức commission Forex
FTMO công bố là 5 USD/lot/vòng, khớp phần commission gốc của R056.
Spread, trượt và swap trong bảng vẫn là dữ liệu hoặc giả định nghiên cứu.
[Thông báo commission FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/).

Bốn lần thiếu thoát đúng giờ vào 25/12 các năm 2018/2019/2020/2023.
Sổ R056 giữ các lệnh này tới báo giá đầu tiếp theo và tính carry.
Đối chứng thiếu thêm một điểm giá ngày 23/11/2023. Giữ cả năm lệnh
trong sổ có SL. Mẫu so chung loại chúng khỏi cả ba cột.
Thời gian giữ dự kiến của hai cửa sổ kết thúc trước 22:00 UTC.

Đối chiếu 16 giờ công bố FOMC đã niêm phong trong 2019/2022. Mẫu R056
có lệnh cả 16 ngày và 0 lần thoát trong ±2 phút. Đối chứng giữ đến mốc
công bố ở 16/16 và thoát sát giờ trong 12/16. Vì vậy, phép đổi giờ giữ
được phơi nhiễm SELL tương đương nhưng khác nguy cơ tin tức. Kiểm này
chưa phủ lịch ECB, số liệu USD khác hoặc mọi ngày nghỉ và giờ tài khoản
đích. FAQ FTMO áp hạn chế thực thi quanh tin được chỉ định với Funded
Standard, gồm cả SL/TP. Challenge, Verification và Swing được miễn
hạn chế đó. Chưa đánh giá tương thích Funded Standard cho cả hai cửa sổ.
[Nguồn lịch FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) ·
[Quy định tin tức FTMO](https://ftmo.com/en/faq/can-i-trade-news/).

## Kết quả

Mỗi ô tiền là **USD/năm** bình quân của cụm ba năm. 1R = 25 USD.
Phép so dùng sổ một nhánh với khối lượng đã khớp theo mô hình H1.

| Cụm | Lệnh R056 / mẫu so chung | R056 phí gốc | R056 phí BASE | Có SL, mẫu chung | Đến giờ, mẫu chung | SELL phiên liền sau |
|---|---:|---:|---:|---:|---:|---:|
| 2018–2020 | 709 / 706 | +43,70 | **+39,89** | +46,29 | +67,62 | −206,56 |
| 2021–2023 | 756 / 754 | +57,74 | **+56,26** | +57,11 | +76,10 | −162,04 |

| Cụm | Mean R/lệnh toàn sổ có SL | Mean R/lệnh mẫu chung có SL / đến giờ / đối chứng | Lot trung vị / khoảng | Risk dự tính trung vị |
|---|---:|---:|---|---:|
| 2018–2020 | +0,00675 | +0,00787 / +0,01149 / −0,03511 | 0,04 / 0,01–0,11 | 22,48 USD |
| 2021–2023 | +0,00893 | +0,00909 / +0,01211 / −0,02579 | 0,04 / 0,02–0,10 | 21,88 USD |

| Năm | Lệnh | R056 USD theo phí gốc / BASE | Đến giờ / phiên liền sau trên mẫu chung, phí BASE |
|---|---:|---:|---:|
| 2018 | 236 | +277,60 / +275,61 | +277,99 / −24,98 |
| 2019 | 236 | +52,98 / +45,87 | +106,32 / −305,10 |
| 2020 | 237 | −199,47 / −201,81 | −181,45 / −289,60 |
| 2021 | 240 | +45,48 / +44,41 | +27,70 / −199,11 |
| 2022 | 260 | +78,89 / +77,74 | +134,33 / −173,85 |
| 2023 | 256 | +48,86 / +46,64 | +66,26 / −113,17 |

### Mất tiền ở đâu?

- **Quy mô lot.** Từ tổng pip cố định đã công bố, trung bình
  296,73 / 208,33 pip sau stress mỗi năm. Để quy ra 1.000 USD/năm
  cần 0,337 / 0,480 lot cố định tại 10 USD/pip/lot, trước tác động
  của stop và giới hạn tài khoản. Đây là đơn vị so quy mô. R056 có
  lot trung vị 0,04 vì stop và ngân sách 25 USD. Ngay cả số tiền giữ
  tới giờ trên lot thực dùng cũng chỉ 67,62 / 76,10 USD/năm.
  [Thành phần giá 2010–2022](PRE-ECB-LONG-PRICE-RESULTS-20261108.md) ·
  [Số liệu 2023](PRE-ECB-RECENT-PRICE-RESULTS-20261108.md).
- **Cách chia lot giữa ngày và stop.** Trên mẫu chung 3 năm đầu,
  chia đều cùng tổng lot cho 415,19 USD theo giờ, chia lot đúng sổ
  giảm 208,70 USD, làm tròn phí BASE bớt 3,63 USD, stop/thoát thực
  bớt 63,99 USD. Cụm sau lần lượt 192,48 USD, tăng 39,24 USD do
  trọng số lot, bớt 3,43 USD do làm tròn và bớt 56,96 USD do stop.
  Phần stop bớt khoảng 19–21 USD/năm, còn ảnh hưởng của trọng số
  lot đổi dấu giữa hai cụm. Lot chia đều là phép chuẩn hóa hậu kiểm.
- **Hướng USD và giờ.** Cùng SELL ở phiên kế lỗ cả hai cụm. Chênh
  lệch theo giờ trước và sau 14:00 Berlin là +274,18 / +238,14
  USD/năm ở cùng notional. Khoảng chênh này là đối chứng theo phiên,
  và phần lỗ của đối chứng không được ghi thành đóng góp của R056.

## Drawdown, lệnh lớn và chồng danh mục

| Cụm | Cash DD R056 (USD, % sổ 10k) | Sụt giảm H1 từ đỉnh cash trước đó (USD) | Mark mở bất lợi nhất (USD), có SL / giữ giờ / phiên sau | PnL R056 bỏ 10 lệnh thắng lớn nhất (USD/cụm) |
|---|---:|---:|---:|---:|
| 2018–2020 | 272,14 · 2,72% | 286,75 | −25,00 / −61,05 / −70,30 | −223,04 |
| 2021–2023 | 157,24 · 1,57% | 162,73 | −24,90 / −57,76 / −71,32 | −231,52 |

Mười lệnh thắng góp 342,71 / 400,31 USD trong khi toàn sổ chỉ lãi
119,67 / 168,79 USD theo cụm. Mark mở tính bằng Ask cao nhất quan
sát được trước thoát, dùng giá thoát mô phỏng ở nến có SL và
không lấy giá cả nến sau mốc thoát theo giờ. Khoảng trống H1 còn
ảnh hưởng bốn lệnh giữ qua lễ. Cash quy swap về lúc quyết toán
lệnh. Các chỉ số này chưa đo floating tick, trượt khi xuyên stop,
Prague reset, max equity DD hay vi phạm của tài khoản quỹ.

Với V19 Development PRIMARY OLHC, chồng thời gian trên 52/709 và
64/756 lệnh theo đường có SL, gồm 43 và 49 lệnh chồng EURUSD F5.
Nếu giữ đủ đến giờ dự kiến, số lệnh chồng F5 là 32 và 37, trong đó
22 và 18 cùng SELL. Đây là số lần chồng khoảng giữ lệnh theo sổ.
Chưa tính lại mức risk còn trống/bù margin, netting hoặc lợi nhuận
tăng thêm trên tài khoản chung. Khối lượng gốc thấp và kết quả mỏng
ngay trước khi xét ràng buộc chung.

## Quyết định và bằng chứng

Giữ R056 ở trạng thái gác. Với luật đã khóa, lợi nhuận còn lại thấp
hơn mốc 2% ở cả hai cụm ngay trên sổ gốc 10k. Kết quả giữ theo giờ
cũng còn xa mốc và có khoản lỗ giữa đường lớn hơn 2R. Phép so này
khép nhu cầu tìm thêm dữ liệu tick để ưu tiên R056 cho payout.
Dữ liệu giá 2024–2026 vẫn đóng.

Bộ tính số nguyên độc lập kiểm 1.465 lệnh, 1.460 mẫu chung, phí,
cash DD và chồng BASE. Bộ kiểm 2023 tính lại 256 lot, stop, điểm
thoát H1 và 4 lần thiếu lịch sử. Mã R056 hiện tại khớp snapshot
sau chuẩn hóa xuống dòng và các dependency khớp hash gốc.
11 kiểm thử tập trung bằng unittest đạt. Kiểm raw SHA256 và dùng
cache H1 sáu năm mất khoảng 70 giây trong lượt này.

Bằng chứng tại
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-pre-ecb-development-attribution-20261119/`.

| File | SHA256 |
|---|---|
| `registration.md` | `bd5e3c2e98495a3178b9040f18cf13626db7e13b133ef70856142cf07c460a09` |
| `r056-attribution.json.zst` | `2b6adeb3683f6e2b2ae558df1864ea24cce167a0c6414eca3456b14e1e452198` |
| `verification.json` | `a67cf098da8234c0603d821398ed41fa9df404ae883f5499e0d7a612ffa3753e` |
| `continuation-review.json` | `d8a32378c99f50c75df611b3a7b0a10c7b9766e53cb0fb80d60657e0ee745d32` |
