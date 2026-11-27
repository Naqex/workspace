# ORB 5 phút không lọc RVOL trên KO, TWTR và SPY

**Quyết định · Gác ngân sách cho kỳ xác nhận mới.** KO lỗ trong cả hai
thứ tự nội nến. TWTR chỉ dương nhẹ ở một thứ tự. Sổ chung KO + TWTR
lỗ ở mọi kịch bản và trượt cả bốn tiêu chí đã khóa trước khi tính PnL.

Phép thử dùng cùng giai đoạn 07–12/2022 và cùng luật của
[TSLA tại b6b9c91](PROP-TSLA-2022H2-CASH-PATH-RESULTS-20261118.md).
KO và TWTR kiểm tra chuyển mã, SPY là đối chứng thị trường. TSLA đã
được chọn sau khi xem kết quả trước, nên dùng lại toàn bộ 103 lệnh
để đối chiếu. Đây là nến giao dịch cổ phiếu cash, chưa có bid/ask,
thứ tự tick, giá khớp CFD hay xác nhận danh mục FTMO năm 2022.
Phép thử không mở giá 2024–2026.

## Phễu và chất lượng đường giá

| Mã | Phiên nguồn | Phiên chấm | Phẳng / không phá | BUY / SELL | Nến vào chạm cả entry và SL / thoát đổi theo thứ tự | Gap entry / gap qua SL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| KO | 127 | 111 | 6 / 12 | 42 / 51 | 7 / 5 | 4 / 0 |
| TWTR | 83 | 65 | 1 / 7 | 34 / 23 | 4 / 4 | 3 / 1 |
| SPY | 127 | 111 | 0 / 12 | 50 / 49 | 4 / 4 | 2 / 0 |
| TSLA | 127 | 111 | — | 48 / 55 | 20 / 19 | 2 / 0 |

TWTR dừng tại phiên cash cuối 27/10. Bốn ngày thiếu phút là 06/07,
09/08, 26/08 và 04/10, lần lượt thiếu 1, 1, 1 và 209 phút. Ngày
06/07 đồng thời thuộc 15 phiên lịch đầu dành cho warm-up nên chỉ đếm
một lần trong phễu. KO và SPY đủ phút trong mọi phiên, kể cả phiên
rút ngắn 25/11 chỉ dùng cho lịch sử. ATR và volume dùng nến ngày
chính thức đã đối chiếu đủ lịch. Giữ gap ex-dividend của KO và SPY
trong True Range, tiền cổ tức bằng 0 do đóng ngay trong ngày.
Ledger TSLA gốc đã quy đổi split 3:1 kể từ ngày có hiệu lực.

Giữ nguyên ATR14 từ các phiên đã đóng, cả hai chiều, SL bằng 0,1
lần ATR, cổ phiếu nguyên, trần 150 USD risk danh nghĩa mỗi entry,
margin 1:1 trên sổ 50.000 USD và thoát muộn nhất tại Open 15:59 ET.

## Sổ riêng theo phí và cách đi của giá trong nến

OHLC và OLHC đặt đỉnh/đáy theo hai thứ tự cố định. Kịch bản **bất lợi**
giữ nguyên thứ tự và định giá stop nội nến bằng cực trị bất lợi, trong
khi gap qua stop dùng giá mở cửa thực tế của phút. TSLA dùng stress
bất lợi theo từng lệnh đúng như artifact gốc. Mỗi cột phí ghi
**Net USD / Mean Net R**. Tháng dương và phép bỏ lệnh thắng lớn tính
theo phí notional.

| Mã | Đường giá | 0,0035 USD/cp mỗi chiều | 0,004% notional mỗi chiều | Lệnh thắng / tổng · tháng dương / tổng | Net USD bỏ top 1 / top 3 |
| --- | --- | ---: | ---: | ---: | ---: |
| KO | OHLC | -2.492,84 / -0,2978 | -2.330,33 / -0,2769 | 12/93 · 2/6 | -3.380,37 / -4.933,50 |
| KO | OLHC | -2.492,84 / -0,2978 | -2.330,33 / -0,2769 | 12/93 · 2/6 | -3.380,37 / -4.933,50 |
| KO | OHLC bất lợi | -4.470,44 / -0,5583 | -4.307,92 / -0,5374 | 12/93 · 2/6 | -5.357,96 / -6.911,09 |
| KO | OLHC bất lợi | -4.452,87 / -0,5539 | -4.290,35 / -0,5330 | 12/93 · 2/6 | -5.340,39 / -6.893,52 |
| TWTR | OHLC | -1.761,97 / -0,2072 | -1.549,43 / -0,1796 | 9/57 · 2/4 | -3.427,17 / -5.020,73 |
| TWTR | OLHC | -59,19 / 0,0002 | 153,28 / 0,0278 | 10/57 · 3/4 | -1.724,46 / -4.084,95 |
| TWTR | OHLC bất lợi | -3.910,15 / -0,4811 | -3.697,56 / -0,4534 | 9/57 · 2/4 | -5.575,30 / -7.168,86 |
| TWTR | OLHC bất lợi | -2.159,48 / -0,2678 | -1.946,97 / -0,2401 | 10/57 · 2/4 | -3.824,70 / -6.185,20 |
| SPY | OHLC | -1.125,74 / -0,1829 | -1.431,74 / -0,2170 | 14/99 · 3/6 | -2.835,39 / -4.266,71 |
| SPY | OLHC | -1.125,74 / -0,1829 | -1.431,74 / -0,2170 | 14/99 · 3/6 | -2.835,39 / -4.266,71 |
| SPY | OHLC bất lợi | -4.873,35 / -0,5687 | -5.179,35 / -0,6027 | 14/99 · 2/6 | -6.583,01 / -8.014,33 |
| SPY | OLHC bất lợi | -4.878,61 / -0,5702 | -5.184,61 / -0,6042 | 14/99 · 2/6 | -6.588,27 / -8.019,59 |
| TSLA | OHLC | 6.233,85 / 0,4042 | 6.067,81 / 0,3934 | 25/103 · 4/6 | 4.370,79 / 1.659,15 |
| TSLA | OLHC | 3.954,14 / 0,2561 | 3.788,01 / 0,2452 | 23/103 · 4/6 | 2.090,99 / -620,65 |
| TSLA | Bất lợi theo từng lệnh | 189,44 / 0,0113 | 23,33 / 0,0005 | 23/103 · 3/6 | -1.673,69 / -4.385,33 |

### Net theo tháng ở phí notional (USD)

| Mã / đường giá | 07 | 08 | 09 | 10 | 11 | 12 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| KO OHLC | -424,79 | 1.235,42 | -1.690,56 | 708,81 | -1.661,47 | -497,74 |
| KO OLHC | -424,79 | 1.235,42 | -1.690,56 | 708,81 | -1.661,47 | -497,74 |
| TWTR OHLC | 786,33 | 617,16 | -750,19 | -2.202,73 | — | — |
| TWTR OLHC | 786,33 | 617,16 | 952,52 | -2.202,73 | — | — |
| SPY OHLC | 135,40 | -581,12 | 724,77 | 262,73 | -886,81 | -1.086,71 |
| SPY OLHC | 135,40 | -581,12 | 724,77 | 262,73 | -886,81 | -1.086,71 |
| TSLA OHLC | 111,35 | -709,20 | 4.035,11 | 1.442,14 | -1.029,03 | 2.217,46 |
| TSLA OLHC | 111,35 | -709,20 | 3.016,60 | 1.442,14 | -1.029,03 | 956,16 |

## Sổ dùng chung KO + TWTR

Dùng 150 trigger, một balance 50.000 USD và margin 1:1. Trần risk
danh nghĩa 150 USD/lệnh và 800 USD đồng thời. Khi hai mã vào cùng
phút, KO đứng trước TWTR theo thứ tự chữ cái. Lệnh thoát trong
cùng phút chưa giải phóng vốn cho lệnh mới. Margin dùng tiền mặt
đã hiện thực hóa tối đa 50.000 USD, sau khi trừ margin và phí dự
phòng. Dự phòng hai chiều theo giá entry đã biết, phí thực hiện
trừ theo giá entry và exit khi settle. Mỗi tổ hợp phí/thứ tự có
một sổ riêng.

| Đường giá | Phí | Lệnh nhận / giảm size / bỏ | Entry có vị thế đang giữ / cùng phút vào | Margin / risk đỉnh (USD) | Net USD / Mean R | Bỏ top 1 (USD) | Tháng dương |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OHLC | Theo cp | 125 / 107 / 25 | 2 / 0 | 49.990,44 / 151,17 | -5.003,36 / -0,3719 | -6.034,35 | 1/6 |
| OHLC | Notional | 127 / 105 / 23 | 4 / 2 | 49.995,41 / 151,36 | -4.732,34 / -0,3903 | -5.767,47 | 1/6 |
| OLHC | Theo cp | 128 / 98 / 22 | 6 / 2 | 49.992,84 / 152,72 | -3.367,91 / -0,2954 | -4.891,88 | 1/6 |
| OLHC | Notional | 129 / 93 / 21 | 7 / 3 | 49.995,41 / 152,72 | -3.084,54 / -0,2525 | -4.616,87 | 1/6 |
| OHLC bất lợi | Theo cp | 125 / 113 / 25 | 2 / 1 | 49.981,05 / 150,00 | -8.345,28 / -0,6652 | -9.364,09 | 0/6 |
| OHLC bất lợi | Notional | 125 / 113 / 25 | 2 / 1 | 49.981,05 / 150,00 | -8.093,13 / -0,6470 | -9.114,72 | 0/6 |
| OLHC bất lợi | Theo cp | 127 / 113 / 23 | 5 / 3 | 49.981,87 / 152,62 | -6.674,55 / -0,5713 | -8.175,00 | 0/6 |
| OLHC bất lợi | Notional | 127 / 112 / 23 | 5 / 1 | 49.981,87 / 152,72 | -6.414,05 / -0,5602 | -7.922,78 | 0/6 |

### Tiêu chí ưu tiên kỳ dữ liệu độc lập

| Tiêu chí khóa trước | Kết quả | Phán quyết |
| --- | --- | --- |
| Cả KO và TWTR dương sau phí notional ở cả OHLC và OLHC | KO −2.330,33 USD ở cả hai. TWTR −1.549,43 và +153,28 USD | Trượt |
| Sổ chung ít nhất +500 USD ở cả OHLC và OLHC | −4.732,34 và −3.084,54 USD | Trượt |
| Sổ chung còn ít nhất +500 USD sau khi bỏ lệnh thắng lớn nhất | −5.767,47 và −4.616,87 USD | Trượt |
| Kịch bản stop bất lợi hơn của sổ chung không âm | −8.093,13 USD | Trượt |

Dấu lãi của TWTR và dấu lỗ của danh mục là hai câu hỏi khác nhau.
TWTR ở OLHC còn +153,28 USD, nhưng bỏ lệnh thắng nhất thì còn
−1.724,46 USD. SPY cũng âm trong cả hai thứ tự. TSLA vẫn là quan
sát riêng trong giai đoạn đã dùng, với chỉ +23,33 USD dưới stress
bất lợi ở phí notional. Bằng chứng này không đủ để ưu tiên dữ liệu
mới hoặc nâng trạng thái `BASE_GUARD` khỏi `NOT_QUALIFIED`.

## Tái hiện và đối soát

Artifact private nằm trong `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-stock-orb-transfer-20261118/`.
Giữ `registration.md`, ghi chú preflight, `orb-transfer.py`, verifier,
manifest và bảng chi tiết đủ theo phí, tháng, lý do thoát và giờ khớp.
Dữ liệu gốc và ledger từng lệnh nằm ngoài Git.

- SHA256 protocol: `d156316b230ba40bef59eb2d3185b5248fad809f9a816967dcf0b867e9ba1103`.
- SHA256 ZIP: `3640e34b8de32d86a3e1fd83e68e99013e5c130f72ed3a93287a2b651b24f843`.
- SHA256 ledger Zstandard: `98100cc1e8f297d26b08681eec55cbcff00b740103b58a96b140ae30636ad163`.
- `python orb-transfer.py --preflight` kiểm lịch phiên và SHA256
  sáu CSV. `python orb-transfer.py` chạy 6/6 test của engine gốc
  và so round-trip nén. `python verify-orb-transfer.py` đối soát
  4.928 lượt lệnh theo phối hợp phí/đường giá và cả 8 sổ dùng chung
  bằng phép cộng cash và tái tính margin/risk tại từng entry.
