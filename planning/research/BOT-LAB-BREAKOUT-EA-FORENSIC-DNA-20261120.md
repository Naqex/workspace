# Bot Lab · DNA từ log Live Account Breakout EA · Pass 4

**Bằng chứng mạnh nhất là lệnh Stop đặt theo lịch, phần lớn thoát ở giờ
cố định và USDJPY có rủi ro tiền tới SL hiển thị gần 100 USD/lệnh.**
Cả hai chiều sinh lời trong mẫu. Ưu tiên một phép thử Stage‑0 độc lập
trên USDJPY ở Pass 5. XAUUSD mới có 166 lệnh và quan sát từ cuối tháng
3/2026. Cả hai mã giữ trạng thái `PROP_UNMEASURED`.

## Phạm vi và đồng hồ nguồn

Nguồn duy nhất là `2283078.history.csv`, SHA256
`90ec2dbbab27388a5db8cdf39a552dc1ae637897ccde059a7467e5382da18c00`.
Đối soát 1.781 dòng gồm **776 lệnh đóng, 1.002 lệnh Stop có ghi hủy và
3 giao dịch vốn**. Lệnh đầu mở **13/01/2025 08:04:52**, lệnh cuối đóng
**18/11/2026 18:55:00**, theo giờ CSV. Tập trước 01/01/2025 có 0 lệnh,
tập sau mốc có 776, không lệnh vắt qua mốc. Toàn bộ gắn
`bar_path_skipped_holdout_lock`. Hai cột commission/swap trống ở 776/776.
`Profit` của nguồn được báo là gross. Net nguồn và tỷ trọng swap thực
nhận còn unknown.

**Quy đổi chính có bằng chứng từ broker**. Snapshot MQL5 đúng Signal ID
ghi server MT4 `Headway-Real`. Headway công bố chuyển UTC+3 sang UTC+2 vào
26/10/2025 khi châu Âu hết DST. Dùng lịch `Europe/Helsinki` cho phép
quy đổi lịch sử, với `UTC` là đối chứng. Trạng thái
`BROKER_SCHEDULE_CORROBORATED` nghĩa là quy đổi được tài liệu broker
ủng hộ. CSV thiếu offset theo dòng và không có lệnh trước 2025 để kiểm
offset theo giá. [MQL5 Signal](https://www.mql5.com/en/signals/2283078) ·
[Định danh server MT4](https://help.headway-online.care/hc/en-us/articles/11876815463837-Can-t-find-the-Broker-or-Server-on-Meta-Trader) ·
[Thông báo DST của Headway](https://hw.online/company-news/metatrader-server-time-changes-due-to-the-wintertime-shift/).

| Quan sát | USDJPY | XAUUSD |
| --- | --- | --- |
| Thứ Hai sớm nhất, đặt pending / khớp | 05:01:00 / 05:01:01 | 06:00:00 / 06:05:45 |
| Thứ Sáu đóng muộn nhất trong CSV | 18:00:02 | 18:55:01 |
| Chủ Nhật có lệnh mở | 0 | 0 |
| Cụm đặt pending / cụm đóng | 05:01 / 18:00 | 06:05 / 18:55 |
| Quy về UTC mùa đông | 03:01 / 16:00 | 04:05 / 16:55 |
| Quy về UTC mùa hè | 02:01 / 15:00 | 03:05 / 15:55 |

Các mốc trên là hành vi của hệ thống nên cách xa biên mở/đóng của thị
trường. Hai giả định giờ đều hợp với lệnh quan sát nếu chỉ xét cuối tuần.
Trong cửa sổ ±14 ngày quanh các lần đổi DST của châu Âu và New York,
USDJPY giữ mode 05:01/18:00 xuyên 8/8 lần kiểm. XAUUSD giữ 06:05/18:55
quanh hai lần đổi giờ cuối tháng 10 và đầu tháng 11/2026 có đủ hai phía.
Điều này cho thấy lịch hoạt động bám giờ nguồn. Quy đổi UTC ưu tiên
lịch broker vì log riêng không đủ suy ra offset.

## Báo cáo theo thời gian và chiều

Net stress mô hình giữ nguyên giá khớp và lot trong CSV, thay commission
bằng spec đã khóa và thêm 0,20 pip/side USDJPY, 0,20 USD/oz/side XAUUSD.
Lịch 17:00 New York cho 0 lần rollover ở cả hai giả định giờ. Kết quả
giống giữa hai spec trên cohort này. Gross nguồn **+11.091,42 USD**,
net cơ sở mô hình **+9.870,47 USD**, net stress **+9.115,81 USD**.
Các số USD này giữ lot lịch sử và chưa chuẩn hóa theo quy mô tài khoản.

| Quý đóng lệnh | Lệnh | Gross USD | Net stress USD |
| --- | ---: | ---: | ---: |
| 2025 Q1 | 68 | +437,69 | +302,39 |
| 2025 Q2 | 73 | +2.463,75 | +2.334,53 |
| 2025 Q3 | 91 | +2.389,72 | +2.133,01 |
| 2025 Q4 | 80 | +467,39 | +256,64 |
| 2026 Q1 | 92 | −1.263,50 | −1.497,77 |
| 2026 Q2 | 151 | −480,71 | −940,73 |
| 2026 Q3 | 146 | +5.653,26 | +5.280,96 |
| 2026 Q4 tới 18/11 | 75 | +1.423,82 | +1.246,79 |

**16/23 tháng và 6/8 quý dương dưới stress.** Hai tháng tốt nhất
(07/2026 và 05/2025) cộng **+3.978,68 USD**, bằng 30,5% tổng các tháng
dương. Bỏ cả hai vẫn còn **+5.137,13 USD**. Mức tập trung lớn hơn ở cấp
quý. 2026 Q3 tạo 57,9% net stress toàn kỳ và trước đó có hai quý âm liên
tiếp. USDJPY dương 15/23 tháng, XAUUSD dương 8/9 tháng, với tháng đầu và
cuối của Vàng chỉ có dữ liệu một phần. JSON có toàn bộ bảng tháng.

| Mã · chiều | Lệnh | Win rate gross | Gross nguồn USD | Net stress mô hình USD |
| --- | ---: | ---: | ---: | ---: |
| USDJPY BUY | 318 | 48,7% | +3.807,77 | +2.842,03 |
| USDJPY SELL | 292 | 42,1% | +4.606,02 | +3.752,72 |
| XAUUSD BUY | 75 | 61,3% | +1.673,64 | +1.602,72 |
| XAUUSD SELL | 91 | 56,0% | +1.003,99 | +918,35 |

USDJPY quan sát ở đây đánh hai chiều với số lệnh gần cân bằng. SELL có
win rate thấp hơn và đóng góp stress lớn hơn trong mẫu. Giữ cả hai chiều
cho giả thuyết tiếp theo. [Đối chứng USDJPY ASYM_B](BOTTLENECK2-ASYMMETRIC-PIVOT-20261119.md).

## DNA vào và thoát lệnh

| Thước đo | USDJPY | XAUUSD |
| --- | ---: | ---: |
| Lệnh đóng | 610 | 166 |
| Pending Stop có ghi hủy | 824 | 178 |
| Cụm đặt pending chính | 534/824 tại 05:01 | 157/178 tại 06:05 |
| Ngày có pending hủy / thấy cả hai chiều hủy | 482 / 9 | 166 / 8 |
| Pending hủy trong 5 giây đầu mốc đóng | 349 | 10 |
| Khớp đúng giây 00 tại mốc giờ tròn | 2/610 | 0/166 |
| Khớp đúng giây 00 tại mốc M15 | 4/610 | 0/166 |
| Cụm giờ khớp lớn nhất theo CSV | 05:xx, 205/610 | 06:xx, 78/166 |
| Entry T2 / T3 / T4 / T5 / T6 | 113 / 124 / 127 / 127 / 119 | 33 / 34 / 37 / 31 / 31 |

USDJPY khớp ở phút 01 nhiều nhất (63 lệnh), XAUUSD ở phút 05 (13 lệnh).
Theo quy đổi Headway, USDJPY khớp nhiều nhất tại 02:xx và 03:xx UTC
(132 và 119). XAUUSD tập trung tại 03:xx và 05:xx UTC (69 và 29).
Phân bố đủ 60 phút, 24 giờ và hai giả định clock nằm trong JSON.
Cụm đặt lệnh hủy cùng với thời điểm khớp rải giữa nến cho thấy cơ chế
pending Stop có cơ sở mạnh. Log chưa nối được từng lệnh đóng với ticket
pending gốc, chưa xác định được nguồn level hoặc cặp OCO.

| Cơ chế thoát theo log | USDJPY | XAUUSD |
| --- | ---: | ---: |
| SL tổng, gồm gần đúng và tag lệch | 186 (30,5%) | 42 (25,3%) |
| ↳ `HIT_EXACT_SL` trong một tick | 111 (18,2%) | 14 (8,4%) |
| ↳ Tag `[sl]` lệch hơn một tick | 75 (12,3%) | 28 (16,9%) |
| `HIT_EXACT_TP` | 0 | 2 (1,2%) |
| `BREAKEVEN_OR_TRAILING_STOP` | 0 | 0 |
| `TIME_OR_SIGNAL_EXIT` | 424 (69,5%) | 122 (73,5%) |
| ↳ Trong 5 giây đầu mốc đóng | 418 tại 18:00 | 119 tại 18:55 |

Mốc gần đúng dùng một tick, 0,001 JPY hoặc 0,01 USD/oz. Tách các lệnh
có tag stop nhưng khớp lệch để giữ nguyên nguyên nhân quan sát. Không
có SL hiển thị ở hòa vốn hoặc phía có lãi. File không ghi lịch sử sửa
stop nên trailing ở phía còn lỗ vẫn chưa biết. Sáu lệnh USDJPY và
ba lệnh Vàng thuộc nhóm time/signal đóng ngoài cụm chính. Hai lệnh
Vàng chạm TP có gross −0,14 USD và 0 USD. USDJPY thiếu TP 610/610.
Vàng có TP 3/166 với khoảng cách 0 / 0,07 / 1.240,02 USD/oz và tỷ số
TP/SL 0 / 0,00143 / 25,30×. Chưa có bằng chứng về một TP cố định.

| Quy mô | USDJPY | XAUUSD |
| --- | ---: | ---: |
| SL hiển thị P10 / P25 / median / P75 / P90 / max | 23,38 / 33,00 / 45,70 / 62,90 / 85,30 / 181,20 pip | 40,38 / 41,29 / 43,39 / 45,92 / 47,49 / 106,85 USD/oz |
| Gross / rủi ro theo SL hiển thị P10 / median / P90 | −1,01 / −0,10 / +1,65 | −1,01 / +0,22 / +1,38 |
| Giữ P10 / P25 / median / P75 / P90 / max | 1,60 / 4,48 / 8,56 / 11,79 / 12,90 / 12,98 giờ | 3,16 / 7,88 / 10,15 / 12,37 / 12,80 / 13,00 giờ |
| 0 đêm / 1 đêm / 2+ đêm | 610 / 0 / 0 | 166 / 0 / 0 |
| Qua cuối tuần | 0 | 0 |

Đếm đêm theo ngày trong CSV và theo rollover New York sau cả hai cách
quy đổi. **Selective Win Diagnosis** có 375 lệnh gross dương (278 USDJPY,
97 Vàng), tất cả thuộc nhóm time/signal, trong đó 367 thoát ngay mốc
đóng. Cả 375 giữ nhãn path unknown và 0 lệnh đủ điều kiện MAE/MFE. Net theo
từng lệnh nguồn và tỷ trọng swap thực nhận chưa xác minh. Swap trong mô
hình là 0 do không cắt rollover.

## Sizing, đồng thời và DD

| Thước đo | USDJPY | XAUUSD | Ghép hai mã |
| --- | ---: | ---: | ---: |
| Vị thế đồng thời tối đa | 2 | 2 | 3 |
| Đồng thời cùng mã cùng chiều tối đa | 1 | 1 | 1 |
| Khoảng cách nhỏ nhất hai lần mở cùng mã | 268 giây | 27 giây | — |
| Stop-risk tiền P10 / median / P90 | 98,78 / 100,21 / 102,72 USD | 81,05 / 87,58 / 96,26 USD | — |
| Stop-risk / gross balance P10 / median / P90 | 0,87 / 0,96 / 1,19% | 0,69 / 0,84 / 0,97% | — |
| Tương quan balance mở với stop-risk | +0,076 | −0,034 | — |
| Top 2 / 5 / 10 trong pool lệnh gross dương | 7,0 / 13,6 / 21,5% | 7,6 / 16,0 / 27,6% | 5,8 / 11,1 / 17,6% |
| Chuỗi thua gross dài nhất | 8 | 6 | 8 |
| Peak-to-valley gross cash, loại nạp rút | 2.697,51 USD | 366,30 USD | 2.360,11 USD |
| Peak-to-valley theo SL hiển thị | 26,50R proxy | 4,43R proxy | 23,23R proxy |

Tại USDJPY, median stop-risk qua ba giai đoạn vốn lần lượt **100,08 /
100,25 / 100,06 USD** dù có hai lần rút tiền. Bằng chứng nghiêng về số
tiền rủi ro gần cố định trong phạm vi quan sát. Vàng có median 90,42 USD
trước lần rút vốn thứ hai và 83,80 USD sau đó. Chưa chứng minh fixed
fractional ở cả hai mã. Stop-risk dùng giá SL hiện trong export và balance
dựng từ nạp/rút cộng gross đã đóng. Có các lần chồng hai vị thế ngược chiều
cùng mã, vì vậy một vị thế mỗi mã là ràng buộc được chọn cho bản độc lập,
khác với độ đồng thời quan sát. Khoảng cách nhỏ nhất không đủ suy ra cooldown.

| Closed-only, chưa gồm float | USDJPY 0,50% / 0,75% | XAUUSD 0,50% / 0,75% | Ghép 0,50% / 0,75% |
| --- | ---: | ---: | ---: |
| Worst daily từ balance đầu ngày mô hình | 1,23 / 1,85% | 0,53 / 0,80% | 1,53 / 2,30% |
| Worst static dưới vốn ban đầu | 0,23 / 0,35% | 0,52 / 0,78% | 0,23 / 0,35% |
| Peak-to-valley | 13,25 / 19,88% | 2,22 / 3,33% | 11,62 / 17,42% |

Đây là phép nhân R proxy tại mức risk cố định trên vốn ban đầu, cùng
phí nguồn còn thiếu và cùng lệnh đã đóng. “Closed-only” gom cash tại
cùng timestamp và dùng reset Prague theo từng giả định clock. Equity DD,
R theo stop gốc và margin đều unknown. Ngưỡng static **10%** so với vốn
đầu tài khoản. Các số peak-to-valley hai chữ số phản ánh mức trả lại lãi
từ đỉnh và không tự chỉ ra vi phạm static. Daily **5%** cần cả floating
equity và phí. [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/).

Tương quan gross khi hai mã cùng tồn tại 30/03–18/11/2026 là **−0,017**
theo 168 ngày có giao dịch ở ít nhất một mã và **−0,016** theo 34 tuần.
Riêng 160 ngày cả hai cùng có lệnh, tương quan **−0,020**. Mẫu ngắn,
chưa xác minh tương quan lỗ nổi hoặc tail risk.

**Khả năng chuyển giao theo profile.** Holding trong ngày phù hợp để
kiểm thử ở cả Swing 10k/25k (80%) và Standard 50k–200k (20%). Swing 1:30
cần kiểm margin tại đúng stop, lot step và số vị thế. Mọi tier Standard
vẫn cần kiểm lịch nghỉ >2h và news của funded theo mã, nhất là phiên
đóng sớm. Quy tắc >2h của FTMO có ngoại lệ cho Swing và hai vòng đánh giá.
Chưa có mô phỏng sizing cho Standard 50k–200k. [Luật giữ lệnh FTMO](https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

## Pass 5 · Đề xuất một giả thuyết độc lập

**USDJPY phá hộp Tokyo rồi giữ tiếp diễn trong ngày.** Giả thuyết cho rằng
khi giá thoát vùng tích lũy đầu phiên Tokyo, mất cân bằng lệnh có thể kéo
giá đi thêm theo hướng phá đến phiên Âu. Chọn giờ theo phiên thị trường
để độc lập với mốc 05:01 và 18:00 từ broker nguồn. Dùng cùng quy tắc cho
cả BUY và SELL. XAUUSD để ngoài phép thử đầu tiên.

| Tầng | Quy tắc đề xuất khóa trước khi chạy |
| --- | --- |
| Bias / zone | Trung tính hai chiều. Hộp lấy high/low từ ba nến H1 đã đóng trong 09:00–12:00 Asia/Tokyo. Dùng mid để dựng hộp và ghi rõ UTC. |
| Trigger / entry | Sau khi hộp đóng, xét lần phá đầu tiên lên trên high hoặc xuống dưới low một tick bằng side quote có thể khớp. Xét tới London open 08:00 Europe/London, tối đa một tín hiệu/ngày, bỏ cạnh còn lại sau sự kiện đầu tiên. Nếu chỉ có M1 và hai cạnh cùng chạm trong nến thì ghi thiếu thứ tự, không chọn fill. |
| Stage‑0 | Chỉ đo markout net stress ở **+4h** sau entry. Đối chứng vào hướng ngược trên cùng sự kiện và horizon bằng bid/ask tương ứng, cùng chi phí. Ghi số ngày không phá, missing, spread và giờ giao dịch. Không áp SL, TP hay sizing ở Stage‑0. |
| Scale | Natural SL tham chiếu cạnh đối diện của hộp, chưa kích hoạt trong Stage‑0. Tỷ lệ median stress friction / median stop ≤12%. Ít nhất 50% tín hiệu tự nhiên đạt giới hạn 12%. Dùng spread từ bid/ask, commission snapshot, stress 0,20 pip/side và không trừ spread lần hai. |
| Cửa qua | Development 2018–2024, báo riêng cụm 2018–2020 và 2021–2024. Mean markout sau stress phải dương qua từng năm, ít nhất bằng ma sát stress trung bình và hơn đối chứng ở cả hai cụm. Đề xuất sàn 40 tín hiệu/năm cho độ phủ cơ bản. Nếu thiếu nguồn, ghi trạng thái dữ liệu. Nếu fail, dừng recipe và ghi kết quả. |
| Chỉ thiết kế nếu Stage‑0 qua | Một vị thế mỗi mã, stop cạnh hộp, không TP cứng. Đóng chậm nhất 16:00 Europe/London hoặc 60 phút trước kỳ nghỉ >2h đã xác minh, tùy mốc nào đến trước. Hủy pending khi hết cửa entry. Trước replay vốn đăng ký risk 0,50% và 0,75%, lot làm tròn xuống, margin theo tier và equity Prague. Không thử trailing/BE trong lượt đầu. |

Đầu vào cần khóa cho Pass 5 gồm nguồn bid/ask và coverage, lịch phiên,
lịch nghỉ theo symbol, các mốc gap/no-fill, ngưỡng chi phí và commit
runner. Đối soát bằng một timeline tính tay cho đầu hộp, first-touch,
spread và exit +4h trước khi tổng hợp cả kỳ. Dữ liệu 2018–2024 đã có
exposure qua nhiều lượt nghiên cứu. Số liệu của Pass 5 dùng để sàng lọc
giả thuyết trên Development, với giá từ 2025 vẫn niêm phong.

Các điểm nguồn chưa biết gồm cách chọn ngày đặt lệnh, khoảng dựng
range, direction bias, biến động/news filter, trigger order ID, spread
lúc khớp và SL trước mọi sửa đổi. Chúng không được suy diễn thành rule
sao chép. Phép thử trên đây đủ cụ thể để bác bỏ nhanh cơ chế độc lập.
**Đề xuất mở Stage‑0 USDJPY ở Pass 5, chờ kết quả trước khi viết bot SL/TP
hoàn chỉnh hay mở XAUUSD.**

## Kiểm chứng

Đã kiểm 80 test, 0 skip. Test mới đối soát SL lệch tick, đồng thời khi
đóng/mở cùng timestamp, static và peak-to-valley, parser export thật và
canh gác không gọi market store. Đã đối soát 776 phân loại từng dòng
trong biên nhận riêng. 0 file nến/tick local mở, 0 backtest, `OrderSend = 0`.
MT5 chưa mở. Khóa holdout, pin Trader và WIP VI Dubber giữ nguyên.

[JSON đối soát](BOT-LAB-BREAKOUT-EA-FORENSIC-DNA-20261120.json) ·
[SHA256](BOT-LAB-BREAKOUT-EA-FORENSIC-DNA-20261120.sha256).
`research_inventory.py --key bot-lab-breakout-pass4-20261120` tra
manifest riêng. Báo cáo và checksum dùng byte LF chuẩn Git.
