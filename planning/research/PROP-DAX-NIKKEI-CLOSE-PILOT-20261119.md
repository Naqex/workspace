# Động lượng 30 phút cuối phiên DAX và Nikkei 225

Đã có [hậu kiểm CFD Nhật 2019/2022](PROP-JPN-CLOSE-PROXY-RESULTS-20261119.md).
Nguồn bám sát benchmark quanh giờ đóng cửa. Lệnh định giá được âm
sau spread ở cả hai năm. Kết quả pilot gốc bên dưới được giữ.

**Gác DAX sau mẫu kiểm chi phí.** Đủ giá hai chiều ở cả 12 ngày mẫu.
Cụm 2021–2023 chỉ giữ **1/6** cơ hội khi ma sát phải nằm trong 12% stop
tự nhiên. Cụm 2018–2020 giữ **3/6**. **Nikkei 225 dừng ở bước xác minh
nguồn và hợp đồng.** Chưa chạy phép đo lợi nhuận hoặc tài khoản cho cả hai.

## Luật và phạm vi đã khóa

Đo một lần mỗi phiên tiền mặt: lấy dấu của Bid Close từ phút cuối phiên
liền trước tới nến phút đã đóng ngay trước nửa giờ cuối. Dương lấy BUY,
âm lấy SELL. Dùng giá mở Bid/Ask của phút kế tiếp sau một phút đệm,
rồi thoát ở giá mở phút cuối trước giờ đóng hoặc ở stop nếu bị chạm.
Stop BUY là đáy Bid, stop SELL là đỉnh Ask của 30 nến đã đóng ngay trước
khi quyết định. Luật không đặt TP và không kéo giãn stop để qua phí.

DAX lấy mốc bắt đầu đấu giá đóng cửa Xetra **17:30 giờ Berlin**, trước
đấu giá. Các mốc quyết định/vào/thoát là **17:00 / 17:01 / 17:29**.
Dùng timezone Berlin để giữ DST. Nikkei lấy giờ tiền mặt Tokyo
**15:00 JST** trong 2018–2023, tương ứng **14:30 / 14:31 / 14:59**.
JPX chỉ kéo dài đến 15:30 từ 05/11/2024. Ngày nghỉ và đóng sớm
thuộc lịch từng sàn. Mẫu đã đặt vào thứ Tư thứ ba của tháng 1 và 7, cùng
phiên liền trước để tính tín hiệu. Không có phiên đóng sớm cuối năm
trong mẫu này. Lịch 2018–2023 cho toàn bộ ngày chưa được nạp vào runner.
[Lịch Xetra](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours/trading-calendar) ·
[Lịch đấu giá Xetra](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/Xetra/continuous-trading-with-auctions/auctionschedule) ·
[Giờ JPX qua các thời kỳ](https://www.jpx.co.jp/english/equities/trading/domestic/tvdivq0000006blj-att/tradinghours_eg.pdf).

Đây là phép chuyển giả thuyết của Baltussen, Da, Lammers và Martens sang
CFD dùng giờ tiền mặt. Bảng futures của bài dùng DAX 09:00–17:30
và Nikkei SGX 08:00–14:00 theo đồng hồ thị trường đó. Phụ lục chỉ số
tiền mặt dùng Nikkei 09:00–15:00. Lịch sử bài đến 01/05/2020, nên cụm
2018–2020 có kỳ thời gian trùng, dù dữ liệu CFD khác nguồn. Bài chưa
trừ phí giao dịch. R076/R077 trên US500/Nasdaq là đối chứng âm đã
có và cùng họ tín hiệu. Không chạy lại chúng.
[Bài gốc](https://pure.eur.nl/ws/portalfiles/portal/58145484/1_s2.0_S0304405X21001598_main.pdf) ·
[Kết quả R076/R077](INDEX-REST-OF-DAY-RESULTS-20261109.md).

## Nguồn và hợp đồng

| Thị trường | Xác minh được | Phần thiếu cho phép đo |
|---|---|---|
| DAX → GER40.cash | KID của Dukascopy nối DEU.IDX/EUR với DAX. Feed CFD này dùng futures gần hạn làm tham chiếu, có basis so với cash và so với FTMO. QDM có mục Germany 30 cũ, nguồn hiện hành ghi Germany 40. Không thấy cache DAX lịch sử trong các kho kiểm. Dùng 48 file ngày × chiều từ endpoint công khai, đủ 24 ngày gồm ngày làm tín hiệu và ngày liền trước. | Khớp tick, biểu phí riêng từng tài khoản, min/step lot và giờ CFD lịch sử chưa xác minh. Các file mới đủ cho mẫu quy mô, chưa đủ cho sáu năm. |
| Nikkei 225 → JP225.cash | Tìm thấy 485 ngày có cặp file Bid/Ask theo metadata cache của Japan200+, gồm 241 ngày năm 2019 và 244 ngày năm 2022. Tài liệu Dukascopy đặt tên Japan 200+ trong bảng sản phẩm, Japan 225+ trong lịch phiên. Nikkei có định nghĩa chỉ số 225 cổ phiếu riêng. | Chưa có căn cứ xác nhận chuỗi giá trong cache bám đúng hợp đồng Nikkei cần kiểm. Chuỗi cũng chỉ có hai năm. Không suy từ tên QDM `JAPAN 225` ra danh mục cấu thành hay benchmark. Chưa định giá hay thay proxy khác. |

FTMO công bố miễn commission cho chỉ số. Thông báo 2022 cho biết
GER40.cash và JP225.cash chuyển từ 10 xuống 1 hợp đồng/lot từ
10/10/2022. JP225.cash lại tăng lên 10 từ 07/07/2025. Vì vậy phép
tính dưới đây dùng **đơn vị hợp đồng tham chiếu**, với 1 đơn vị DAX
= 1 EUR cho một điểm chỉ số ở kịch bản đích. Không dùng một multiplier
cho mọi năm hoặc lấy quy ước tick Dukascopy làm định nghĩa MT5.
FTMO từng công bố đòn bẩy nhóm bao gồm GER40 là 1:50 Standard và 1:15
Swing. Bảng chi tiết hiện hành tải không thành công trong trình duyệt,
nên sizing/margin ở đây vẫn là phép tính theo giả định đã ghi.
[Dukascopy KID](https://www.dukascopy.com/media/pdf/swiss/KID/KID%20-%20CFD%20on%20Stock%20Index.pdf) ·
[Dukascopy bảng chỉ số](https://www.dukascopy.com/europe/english/cfd/range-of-markets/cfd-indices/) ·
[Dukascopy lịch phiên](https://www.dukascopy.com/wiki/en/manuals/jforex4-desktop/trading-sessions/) ·
[Nikkei mô tả chỉ số](https://indexes.nikkei.co.jp/en/nkave/index/profile?cid=1) ·
[FTMO phí chỉ số](https://ftmo.com/en/blog/zero-commissions-on-indices/) ·
[FTMO đổi lot 2022](https://ftmo.com/de/blog/trading-update-06-10-2022/) ·
[FTMO đổi lot JP225 năm 2025](https://ftmo.com/en/blog/trading-updates/trading-update-26-jun-2025/) ·
[FTMO tham chiếu đòn bẩy](https://ftmo.com/en/blog/a-few-answers-to-your-questions/).

## DAX: mẫu trước khi mở phép đo lợi nhuận

Spread là giá Ask trừ Bid quan sát ở phút vào. Cộng thêm trượt giá
stress **0,75 điểm mỗi chiều** như R076/R077. Đây là stress đặt trước,
chưa có số đo slippage live của GER40. Tính cổng phí từ giá vào, cùng
phí mặc định khi đóng trong ngày. Khoảng cách SL lấy từ giá vào phía
có thể thực thi nên đã phản ánh bên spread dùng để vào. Không dùng
spread lúc thoát để quyết định có vào.

| Cụm | Đủ toàn bộ phút cần dùng | Hướng BUY / SELL | SL trung vị (điểm) | Spread vào / thoát trung vị | Ma sát stress tại entry trung vị | Qua phí / giữ được sau kiểm risk tĩnh |
|---|---:|---:|---:|---:|---:|---:|
| 2018–2020 | 6/6 | 3 / 3 | 15,61 | 1,042 / 1,041 | 2,542 | 3 / 3 |
| 2021–2023 | 6/6 | 4 / 2 | 14,28 | 1,392 / 1,252 | 2,892 | 1 / 1 |

Ở mức ma sát trung vị, cần SL khoảng **21,18 / 24,10 điểm** để đạt
12%. Hai cụm có (median(friction/SL)) lần lượt **18,28% / 19,26%**.
Bốn ngày qua cổng tập trung vào 2019 (2), 2020 (1) và 2021 (1).
Mẫu 12 ngày đủ để áp điểm dừng đã khóa của pilot, còn tần suất mỗi năm
trên toàn lịch, lợi nhuận, đóng góp theo nước và tương quan vẫn chưa đo.

**Kiểm sức chứa tĩnh.** Dùng các lệnh đã nhận trong các sổ BASE mở
tháng 1 mỗi năm, cả PRIMARY và STRICT. Trong 12 ngày, 4 có lệnh BASE
cùng ngày UTC. Một khung 28 phút chồng EURUSD F5, ngày 21/07/2021,
với 298,41 USD risk stop đang dành. Bốn tín hiệu qua phí vẫn nằm trong
trần chung **1.000 USD** khi cấp tối đa 187,50 USD ở phép đo tham chiếu
Funded. Quy đổi EURUSD bằng close nến Ask đã biết trước lúc vào. Dùng
bước giả định 0,1 đơn vị hợp đồng và làm tròn xuống. Margin DAX riêng
khoảng **1.570–2.255 USD Standard**, **5.233–7.516 USD Swing**. Hôm
chồng F5, tổng ký quỹ tham chiếu là **3.987,92 / 13.293,07 USD**,
và tổng khoản dự phòng stop biểu kiến là **484,81 USD**. Phép kiểm
dùng vốn tĩnh và các entry BASE đã lưu, chưa đo DD, free margin thực
hoặc admission sau khi lệnh mới làm đổi đường vốn. Risk theo pha của
BASE giữ nguyên.

## Quyết định

DAX trượt gate pilot **giữ ít nhất 50% ở mỗi cụm**. Dừng trước khi mở
thêm nguồn hoặc tính PnL toàn kỳ. Phép so BUY cùng cơ hội và cùng chi
phí đã khóa, chưa kích hoạt vì gate quy mô trượt. Nikkei mang trạng
thái `SOURCE_REVIEW_REQUIRED`. **USD/năm và R/lệnh chưa đo**,
nên chưa thể so định lượng với mốc 1.000 hay bậc 5.000–7.500 USD.
Hai phiên có giờ khác nhau chỉ tạo hai dịp theo lịch. Chưa có hai dòng
lệnh thực nhận để cộng hoặc tính mức phụ thuộc. Giữ BASE_GUARD,
`NOT_QUALIFIED`. Không replay tài khoản, không đọc giá 2024–2026,
không mua dữ liệu và không kết nối broker.

## Bằng chứng

`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-de-jp-close-momentum-20261119/`.
Đã đối chiếu SHA của 48 file raw và 48 export, kiểm **60.192** bản
ghi một phút ở hai phía bằng decoder delta có sẵn. Chỉ dùng nến có thật
trong phản hồi nguồn. Đã kiểm lại 12 quyết định qua phí bằng phép
nhân chéo Decimal, hai ledger BASE theo SHA của audit, kiểm vốn/margin
và giải nén receipt. Nhật chỉ đọc tên và năm của tệp cache.

| Artifact | SHA256 |
|---|---|
| `registration.json` | `cc025c7435ab06c475a9010b82e35364b80fbe698d13c3e6bb6b79d766f3f929` |
| `acquisition.json` | `7914305f552f10ffdf3960299561202cf17149bcd7c8fe3b4663a73e489731b1` |
| `pilot-admission.py` | `4202b63e14626290c1a22d251ac6521cd86ede2304045d7c838d4320cff6055f` |
| `pilot-admission.json.zst` | `a0deeabb48770fb525ba4e8d2bd9217099d3ec297bd687db41cb2c67ec7340f3` |
