# WTI chênh lệch kỳ hạn · kiểm khả năng đưa vào sổ CFD

**Gác trước backtest · `DATA_PATH_INCOMPLETE` / `PROP_UNMEASURED`.**
Trong mỗi cụm ba năm chỉ có tối đa 35 cửa sổ tháng trọn vẹn. Với
risk danh nghĩa 150 USD/lệnh, cần **+85,71 USD ròng/lệnh (+0,571R)**
để góp 1.000 USD/năm, ngay cả khi đủ cả 35 lệnh và lệnh nào cũng dùng đủ
risk. Kho đã có nguồn tín hiệu và Bid H1 proxy, còn thiếu chứng từ định
giá vị thế qua kỳ đổi hợp đồng và phí qua đêm của đúng CFD đích.

## Một giả thuyết, một khung thời gian

Xét dấu `F1 − F4` ở settlement NYMEX đầu tiên của tháng: BUY khi
tháng gần đắt hơn tháng xa (backwardation), SELL khi ngược lại
(contango), bỏ khi bằng nhau. Dấu chênh lệch theo USD/thùng giữ
được nghĩa khi một settlement âm. Dùng settlement đã có từ phiên
trước, điểm vào sớm nhất 11:00 New York ở phiên kế tiếp và điểm
đánh giá 11:00 New York ở phiên settlement đầu tiên tháng sau.
Một vị thế tối đa cho mỗi cửa sổ, không đếm nến/ngày giữ như lệnh mới.
Giờ này là quy ước sàng lọc, trước khi chạy còn cần lịch khả dụng của
CFD đúng phiên và mốc settlement đã được phát hành. Đối chứng dự kiến
giữ BUY tại cùng cửa sổ và số thùng tuyệt đối, chịu cùng mô hình phí
theo chiều. Đo phần hơn đối chứng để kiểm liệu dấu đường cong có ích
so với chỉ nắm cùng lượng dầu trong cùng đoạn thời gian.

EIA xác định F1 là kỳ giao sớm nhất, F4 là ba tháng giao sau F1.
Chuỗi theo thứ tự kỳ hạn tự đổi hợp đồng khi kỳ gần hết hạn. Bredin,
O'Sullivan và Spencer (2021) tìm thông tin dự báo ở kỳ giữ 1, 4, 8
tháng với mô hình đường cong trên futures. Fernández-Pérez, Fuertes
và Miffre (2021) đo phần bù trên danh mục long-short nhiều hợp đồng
năng lượng. Hai kết quả tạo cơ sở kiểm giả thuyết nhưng không đưa ra
kỳ vọng PnL cho chỉ dấu F1 − F4 trên một CFD. Chọn một tháng vì đây
là kỳ ngắn nhất bài đầu kiểm, không rút xuống intraday để tăng số mẫu.
[EIA](https://www.eia.gov/dnav/pet/tbldefs/pet_pri_fut_tbldef2.asp) ·
[Bredin và cộng sự](https://doi.org/10.1016/j.eneco.2021.105350) ·
[Fernández-Pérez và cộng sự](https://openaccess.city.ac.uk/27563/).

Kiểm chỉ mục, catalogue và lịch sử commit chưa thấy exact rule này.
R082/R083 đo tiếp diễn WTI quanh sự kiện trong ngày. Nhánh WTI → USD/CAD
dùng giá dầu để dự báo FX. Cả ba đã có biên bản riêng.
[R082](WTI-WEDNESDAY-COMPONENT-RESULTS-20261109.md) ·
[R083](WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md) ·
[WTI → USD/CAD](PROP-OIL-CAD-STAGE0-RESULTS-20261118.md).

## Nguồn hiện có và phần còn thiếu

| Thành phần | Kiểm được | Giới hạn |
| --- | --- | --- |
| Settlement F1–F4 | EIA định danh giá NYMEX theo tháng giao và thông lệ settlement 14:30 ET | Dùng làm predictor theo phiên đã biết. Chênh lệch giá hai tháng giao không đi vào cash tài khoản |
| Giá CFD proxy 2018–2023 | Kho từng dùng cho USD/CAD có 72 tệp tháng Bid H1, 35.400 nến H1 gốc và các lát Ask M1 rời rạc | Cache tháng này có 0/72 tệp Ask H1. Thiếu spread và giá khớp đích cho cả vòng giao dịch |
| Đổi tháng trên `LIGHT.CMD/USD` | Dukascopy mô tả đổi giá tham chiếu khi nghỉ phiên và ghi debit/credit tiền mặt tương ứng | Chưa có chuỗi lịch, kỳ hợp đồng và khoản debit/credit lịch sử đủ 2018–2023 tại đúng giờ đổi của CFD đích |
| FTMO `USOIL.cash` | Thông báo năm 2023 xác minh mã có lịch phiên riêng và nhắc swap có thể đổi | Chưa xác minh đủ Bid/Ask, rollover, swap BUY/SELL theo ngày, quy đổi lot và hạn chế đặt lệnh của đúng tài khoản qua cả sáu năm |

Nguồn: [CFD Adjustment Calendar của Dukascopy](https://www.dukascopy.com/swiss/english/marketwatch/calendars/cfd-price-adjustment-calendar/) ·
[FTMO tháng 2/2023](https://ftmo.com/en/blog/trading-updates/trading-update-16-feb-2023/) ·
[Đối soát cache gốc](PROP-OIL-CAD-STAGE0-RESULTS-20261118.md).

**Tháng 4/2020 là case bắt buộc nếu mở lại.** F1 ngày 20/04
settle −37,63 USD/thùng. Dukascopy chặn tăng exposure từ 21/04
và gỡ close-only ngày 30/04. Vị thế mở trước đó không bị bắt buộc
đóng theo thông báo này, nhưng khả năng thoát và giá vẫn phải được
kiểm. Giữ giá âm đúng dấu, không tính log, không dùng chênh hai hợp
đồng làm lãi, không giả định một trong hai sự kiện cũng diễn ra y
hệt trên FTMO. Gap giữa hợp đồng là dòng điều chỉnh. Gap giá thực
cùng hợp đồng vẫn là rủi ro của vị thế.
[EIA về tháng 4/2020](https://www.eia.gov/Todayinenergy/detail.php?id=43875) ·
[Dukascopy hạn chế tăng exposure](https://www.dukascopy.com/europe/hu/about/ournews/temporary-restrictions-on-light-cmd-usd-exposure-increase/) ·
[Dukascopy gỡ hạn chế](https://www.dukascopy.com/europe/spanish/about/ournews/light-cmd-trading-resumed).

## Quy mô so với mục tiêu 1.000 USD/năm

| Cụm | Trần cửa sổ tháng trọn | Net yêu cầu mỗi vị thế | USD/năm nếu chỉ đạt +0,25R/vị thế | Net thực / lỗ đuôi thực |
| --- | ---: | ---: | ---: | --- |
| 2018–2020 | 35 | 85,71 USD / 0,571R | 437,50 USD | Chưa đo |
| 2021–2023 | 35 | 85,71 USD / 0,571R | 437,50 USD | Chưa đo |

Có 71 cửa sổ liền nhau trên 72 tháng, gồm một cửa sổ bắc qua
ranh giới hai cụm. Đây là số cửa sổ không chồng vị thế tối đa,
chưa suy được 35 quan sát độc lập thống kê trong một chế độ dầu
kéo dài. Ở 10 lệnh/năm, mức cần là +100 USD/lệnh hay +0,667R.
Nếu mức dừng cấu trúc đúng bằng 5 hoặc 10 USD/thùng, risk 150 USD
chỉ chứa tối đa 30 hoặc 15 thùng trước giới hạn lot/margin. Với
35 lệnh/cụm, đó là yêu cầu +2,86 hoặc +5,71 USD/thùng ròng.
Các số này là độ nhạy sizing, chưa phải mức SL hay lot quan sát.

Để đo điểm hòa vốn cần tách: biến động giá CFD, điều chỉnh tiền khi
đổi tháng, spread, commission, slippage, và swap qua đêm theo chiều.
Gọi `G` là gross bình quân USD mỗi lệnh sau trung hòa bước nhảy đổi
tháng, trước ma sát. Tổng drag bình quân để hòa vốn tối đa là `G`.
Để đạt 1.000 USD/năm trong từng cụm, drag tối đa là
`G − 85,71 USD/lệnh` ở độ phủ lý tưởng. Chưa có `G` đáng tin
từ đường giá đích nên cả hai ngưỡng tính theo USD thực đều chưa đo.
Kể cả quy mô đủ, vẫn phải đo lỗ đuôi từ đường giữ lệnh và gap thật.

BASE PRIMARY trước đó qua hai vòng trong 12 tháng ở 0/61 cửa sổ.
Góp thêm 1.000 USD/năm ở risk hiện hành là tiêu chí sàng vai trò,
không phải cam kết sẽ cải thiện tỷ lệ pass. Với cadence thấp và
phần kinh tế chưa định giá được, gác hướng này ở cửa kiểm nguồn,
giữ `BASE_GUARD` tại `NOT_QUALIFIED`.
[Đối chứng BASE](PROP-PAYOUT-REPLAY-DECISION-20261118.md).

## Kiểm chứng

Chạy kiểm cache-only trên sáu tệp H1 từ 2018 đến 2023. Kiểm thứ tự,
độ phân giải giờ, ranh giới thời gian, số tệp mỗi phía và đối chiếu
35.400 timestamp với receipt cũ. Hai phép tính độc lập xác nhận
71 cửa sổ liền nhau, 35/cụm và yêu cầu 4/7 R/lệnh. Bảng đầu ra là
kiểm nguồn và tính ngược mục tiêu, chưa chạy PnL hoặc replay chung.
Tập giá 2024–2026 nằm ngoài đầu vào phân tích.

Script, SHA256 sáu tệp H1 và artifact nén nằm trong
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-wti-curve-admission-20261118/`.
`admission.json.zst` đã kiểm giải nén, SHA256
`e5aa4411027bc38d9ae4b674eea3c8219a35ed5420c5c75fdf86d777bda30c10`.
