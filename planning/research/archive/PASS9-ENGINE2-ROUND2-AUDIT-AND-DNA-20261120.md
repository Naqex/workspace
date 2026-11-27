# Pass 9 · Audit MQL5 Round 2 và DNA cho Engine #2

**0/6 hồ sơ được chọn cho Clean-Room Pass 10.** Năm hồ sơ bị cờ
thêm vị thế bất lợi theo giá fill. ALocalLevels còn thiếu bằng chứng
để giải thích các lần tăng lot và có lợi nhuận tập trung.

[Protocol](PASS9-ENGINE2-ROUND2-AUDIT-PROTOCOL-20261120.md) khóa tại 011d163.

## 1. Leaderboard Round 2

Đọc đủ sáu CSV mới, đối soát 5.131 dòng thành **3.304 lệnh đóng**,
1.809 dòng pending và 18 dòng nạp/rút hoặc balance. Tách tám file
Pass 3 theo ID/SHA. Dùng lại hai parser MQL5 history/positions hiện có.
Profit Currency lấy từ snapshot công khai đã gắn hash tại Pass 8.
MomentumDW là **EUR**, GTP là **CHF**, bốn hồ sơ còn lại là **USD**.
Phần cash gốc giữ nguyên đơn vị, phần repricing FTMO dùng USD.

| Hồ sơ | Lệnh | Nhồi bất lợi / cặp | Đỉnh vị thế cũ bất lợi | Tăng lot net đầy đủ | Tăng lot gross proxy | SL hiện / trống | Phán quyết |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ROEN S Gold | 834 | 4 / 6 | 2 | 0/17 | 0/698 | 831 / 3 | REJECTED_HIDDEN_GRID_OR_MARTINGALE |
| NU4 | 314 | 175 / 279 | 5 | 0/45 | 0/61 | 0 / 314 | REJECTED_HIDDEN_GRID_OR_MARTINGALE |
| MomentumDW | 599 | 12 / 12 | 1 | 0/147 | 0/582 | 599 / 0 | REJECTED_HIDDEN_GRID_OR_MARTINGALE |
| AxtralIAIndex | 937 | 60 / 65 | 2 | 0/0 | 1/845 | 0 / 937 | REJECTED_HIDDEN_GRID_OR_MARTINGALE |
| GTP | 421 | 40 / 103 | 8 | 8/97 | 22/320 | 421 / 0 | REJECTED_HIDDEN_GRID_OR_MARTINGALE |
| ALocalLevels | 199 | 0 / 0 | 0 | 0/0 | 19/173 | 0 / 199 | INSUFFICIENT_DATA_UNKNOWN |

Định nghĩa nhồi của Pass 3 được giữ để so sánh. Lệnh mới cùng mã
và chiều có giá xấu hơn vị thế cũ đang mở. Đây là proxy ở giá fill,
không có giá thanh lý và không quy kết chủ ý. Các lần mở cùng timestamp
không đủ bằng chứng để xác định thứ tự nhồi. SL hiển thị có thể đã dời.
Trường trống không chứng minh lệnh được mở mà thiếu hard SL.

**Hiệu quả anti-grid công khai.** Tỷ lệ hồ sơ không có cờ nhồi là
**1/6 (16,7%)** so với **1/8 (12,5%)** ở Pass 3, chênh khoảng
**4,2 điểm phần trăm**. Hai mẻ nhỏ và được lấy mẫu có chủ đích,
chưa đủ kết luận bộ lọc cải thiện ổn định. Tỷ lệ đủ bằng chứng
chuyển giao ở Round 2 là **0/6**.

- **NU4** có 175 lần thêm bất lợi, tối đa 5 vị thế cũ và lot ghi nhận
  từ 0,03 đến 0,36. Phí stress đưa toàn bộ 314 lệnh NZDUSD về âm.
- **GTP** có 40 lần thêm, tối đa 8 vị thế cũ bất lợi. Tăng lot gấp
  tới 4 lần sau hai lệnh thua ròng trong 8/97 chuỗi đủ dữ liệu.
  So được 2 cặp USD risk theo SL hiển thị, cả hai dưới 1,5 lần.
  Cờ loại dựa vào các lần nhồi lặp. Chưa xác minh martingale theo risk.
- **ROEN S Gold** có 4 lần thêm bất lợi dù 824/834 lệnh dùng 0,10
  lot. Giữ cờ intake theo chuẩn Pass 3. Quy mô lặp thấp hơn NU4/GTP.
- **MomentumDW** có 12 lần thêm bất lợi, tất cả 599 lệnh dùng 0,01
  lot. CSV có 301 lệnh USDJPY (50,3%) và 27 AUDCAD. Tỷ trọng này
  khác thứ tự mã thấy trên Distribution công khai và giảm giá trị
  của giả thuyết bổ trợ bằng AUDCAD.
- **AxtralIAIndex** có 60 lần thêm bất lợi và 937/937 lệnh là mã hợp
  đồng ngoài rổ 13. Một lần tăng lot gross 2×, thiếu cột SL để xét risk.
- **ALocalLevels** không thấy thêm bất lợi. Có 19/173 lần tăng lot
  sau hai lệnh thua gross, đỉnh 7×. Mẫu đủ phí để xét net là 0.
  Thiếu SL ở định dạng positions, vì vậy chưa phân biệt được fixed-risk
  với tăng risk sau thua và giữ INSUFFICIENT_DATA_UNKNOWN.

## 2. Chi phí, giữ lệnh và mã FTMO

Giữ giá fill và spread nguồn. Thay phí bằng spec đã khóa 36f1535 và
8fd77ef. Swap theo lần qua 17:00 New York, đúng dấu và ngày 3×.
Dùng tỷ giá đích từ snapshot bị khóa khi thiếu giá quy đổi cùng cặp.
Khoảng dưới là độ nhạy giữa giả định UTC và Europe/Helsinki.
Standard giữ nguyên fills lịch sử để so phí. Lệnh qua cuối tuần
cần exit khác nếu chạy funded Standard. Margin đỉnh chỉ xét phần
định giá được và giữ lot gốc trong CSV.

| Hồ sơ | Lệnh tính tiền / tổng | Swing stress USD | Standard stress USD | Swap Swing USD | Có qua thứ Bảy (toàn log) | Margin đỉnh 10k Swing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ROEN S Gold | 829 / 834 | +6.909,12 → +6.959,19 | +6.904,49 → +6.954,78 | -987,85 → -937,78 | 29–29 | 105,00% |
| NU4 | 314 / 314 | -71,45 → -69,14 | -72,52 → -70,07 | -145,52 → -143,21 | 150–150 | 14,23% |
| MomentumDW | 572 / 599 | +19,88 → +19,97 | +20,27 → +20,38 | +4,34 → +4,42 | 94–94 | 1,62% |
| AxtralIAIndex | 0 / 937 | — | — | — | 49–51 | — |
| GTP | 421 / 421 | +3.735,49 → +3.737,65 | +3.734,84 → +3.737,00 | -137,73 → -135,57 | 49–49 | 103,57% |
| ALocalLevels | 185 / 199 | +68,15 → +68,88 | +68,33 → +68,88 | -0,73 → 0,00 | 0–0 | 6,97% |

Swap NU4 Swing gồm **192–196 lần 3×**. MomentumDW có **91–93 lần
3×** trong phần đủ spec. ROEN có 2 lệnh thuộc rổ nhưng thời điểm
mở/đóng trùng nên bỏ khỏi repricing. Bảng JSON giữ từng mã, commission,
slippage, swap và phần trăm margin của 10k/25k Swing, 50k Standard.
Giá trị >100% margin của ROEN và GTP ở sổ 10k cho thấy không thể sao
y lot trong những cụm lệnh đó dưới spec đang xét.

Ngoài rổ 13 có AUDCAD, AUDNZD, NZDCAD, GBPAUD, EURCAD, GBPCAD và
CADCHF trong log. FTMO CFD công khai các cặp FX này. Snapshot account
đã niêm phong thiếu spec tương ứng, nên chưa định giá. Mã như NQ_Z,
GC_J và RTY_H dùng quy cách theo tháng hợp đồng. Các gốc NQ, GC, NG,
HG, SI, 6J, 6E, YM, RTY và ES có tên trong chương trình FTMO Futures
riêng. US2000.cash và CORN.c là các mã CFD liên quan về underlying.
Chưa bind chính hợp đồng nguồn, không gán phí hoặc tính như CFD 13 mã.
[FTMO CFD Symbols](https://ftmo.com/en/symbols) ·
[FTMO Futures](https://ftmo.com/en/futures/faq/which-instruments-can-i-trade-with-ftmo-futures/) ·
[FTMO Trading Update](https://ftmo.com/en/blog/trading-updates/trading-update-12-nov-2026/) ·
[Giữ lệnh Swing và Standard](https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

## 3. Forensic DNA từ log

Có **669 lệnh đóng trước 2025 theo giờ nguồn** và **2.635 lệnh ở mốc
2025 trở đi**. UTC và Helsinki chỉ là hai phương án so độ nhạy.
Không có xác nhận timezone từ nguồn CSV. Giá giờ cuối tuần được ghi
theo hai mô hình, không gán timezone từ một điểm cuối tuần.
Tất cả các phép đo dùng log. Thiếu ứng viên sạch có đường giá hợp lệ
để làm MAE/MFE hoặc Selective Win Diagnosis trong Pass 9.

| Hồ sơ | BUY / SELL | Entry đúng giờ H1 | Giữ median / P90 / max (giờ) | Pending hủy thấy được | SL/TP sát giá · trailing/BE · audit khác |
| --- | ---: | ---: | ---: | ---: | --- |
| ROEN S Gold | 695 / 139 | 11 | 1,3 / 19,2 / 303,2 | 555 | SL 477, TP 112, trail/BE 233, tag lệch 0, time/signal 9, unknown 3 |
| NU4 | 161 / 153 | 23 | 63,7 / 269,0 / 701,9 | 0 | SL 0, TP 0, trail/BE 0, tag lệch 0, time/signal 0, unknown 314 |
| MomentumDW | 507 / 92 | 307 | 10,0 / 82,6 / 413,8 | 0 | SL 87, TP 2, trail/BE 134, tag lệch 120, time/signal 229, unknown 27 |
| AxtralIAIndex | 701 / 236 | 5 | 2,7 / 26,7 / 791,2 | 0 | SL 0, TP 0, trail/BE 0, tag lệch 0, time/signal 0, unknown 937 |
| GTP | 221 / 200 | 3 | 6,2 / 55,0 / 121,3 | 1254 | SL 11, TP 6, trail/BE 211, tag lệch 188, time/signal 5, unknown 0 |
| ALocalLevels | 110 / 89 | 0 | 2,5 / 8,2 / 18,7 | 0 | SL 0, TP 0, trail/BE 0, tag lệch 0, time/signal 0, unknown 199 |

Entry đúng giờ có thể đến từ clock hoặc điều kiện nến, không xác định
được loại lệnh đã khớp từ riêng timestamp. Pending hủy là hàng log có
tag hủy, không gán cho fill. Khoảng SL/TP trong JSON phân theo mã và đơn
vị giá nguồn. Nhãn exit time/signal là phần dư sau các tag và khớp giá.

| Hồ sơ | Cash proxy theo tiền nguồn | Tháng dương | Quý dương | Bỏ hai tháng tốt nhất | Bỏ Top 5 lệnh | DD đóng tiền nguồn | Chuỗi thua tối đa |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ROEN S Gold | +10.746,48 USD | 43/65 | 17/23 | +7.543,97 | +7.203,18 | 1.091,05 | 20 |
| NU4 | -12,19 USD | 24/28 | 6/10 | -198,90 | -342,94 | 589,29 | 11 |
| MomentumDW | +60,51 EUR | 16/25 | 5/9 | +17,69 | -15,74 | 53,89 | 12 |
| AxtralIAIndex | +80.410,25 USD | 12/24 | 4/9 | +14.320,25 | +11.371,25 | 100.909,00 | 11 |
| GTP | +3.303,74 CHF | 14/21 | 7/8 | +1.752,61 | +2.722,39 | 1.081,40 | 13 |
| ALocalLevels | +35,35 USD | 10/21 | 6/8 | -67,80 | -131,07 | 84,22 | 23 |

Cash proxy cộng phí và swap quan sát được, ô trống giả định bằng 0.
JSON tách riêng net ở các hàng đủ phí. DD đóng cộng các lần tất toán
cùng timestamp, chuỗi thua dùng thứ tự dòng khi timestamp trùng.
DD proxy R dùng rủi ro ở SL hiển thị khi SL nằm phía bảo vệ, đổi tiền
nguồn sang USD cùng đơn vị. Hình học này dễ bị phóng đại khi stop đã
dời sát entry. True initial R và floating DD vẫn unknown.

### ALocalLevels · đối chiếu bổ trợ trước khi quyết định

199 lệnh từ 26/03/2025 đến 16/11/2026, toàn bộ log-only.
96 EURUSD, 38 USDJPY, 24 GBPUSD. Không có entry đúng giây đóng H1.
Giữ median 2,48 giờ, P90 8,21 giờ. Từ 0 đến 3 lệnh qua rollover
theo hai giả định clock và 0 lệnh qua thứ Bảy. Có thể phù hợp về
khung giữ của cả Swing lẫn Standard. SL, kiểu vào/thoát và quy tắc
phần manual chưa biết. Win/loss cash proxy là khoảng 2,95×, nhưng
bỏ hai tháng tốt nhất từ +35,35 xuống −67,80 USD. Swing stress có
185 lệnh đủ spec, khoảng +68,15–68,88 USD. Bỏ Top 5 còn
−93,01 đến −92,02 USD.

Tương quan Pearson với riêng chân USDJPY của log Live Account
Breakout EA gần 0 theo ngày cùng có lệnh (−0,006 đến +0,003,
139–140 ngày), và −0,071 theo 66 tuần cùng hoạt động. Khi log
tham chiếu âm, Pearson theo ngày khoảng −0,106 đến −0,099
(205 ngày), nhưng dương +0,227 theo 37 tuần âm. Log tham chiếu
có khả năng khác cách thực thi Tokyo-box Pass 7B. Không có giao
nhau trước 2025 để đo với chính đường replay Pass 7B.

## 4. Quyết định Pass 10

**Không đăng ký giả thuyết Clean-Room từ Round 2.** ALocalLevels là
hồ sơ cần thêm initial SL và lịch sử lệnh để phân biệt fixed-risk với
tăng risk, đồng thời khoản lãi hiện tại phụ thuộc vài lệnh thắng.
Các mẫu còn lại bị chặn ở cửa hành vi.

Ưu tiên nguồn ý tưởng định lượng có quy tắc hoặc mã nguồn công khai
để xây Engine #2 khác cơ chế Tokyo-box. Giữ 95 hồ sơ MQL5 chưa chấm
làm nguồn bổ sung khi tiếp cận public hợp lệ và có thể lấy CSV đúng
quyền. Khi có cơ chế mới, khóa rule và nguồn trước khi đo Stage-0
2018–2024. Lượt này không chạy Stage-0 hay backtest.

66 bài kiểm thử Bot Lab, exit forensics, Pass 8 và inventory đạt, 0 skip.
Full quant suite `--group complete --tier all --workers 4` đạt 1.490 bài, 0 skip, trong 52,32 giây.
SHA256 của báo cáo và JSON dùng blob Git với xuống dòng LF.
Giữ SHA holdout, 0 giá Development/holdout được mở trong phân tích này.
OrderSend = 0. Pin Trader và WIP VI Dubber giữ nguyên.
