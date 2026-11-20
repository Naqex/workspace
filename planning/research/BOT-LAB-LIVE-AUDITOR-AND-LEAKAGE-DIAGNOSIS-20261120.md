# Bot Lab · kiểm toán trade log và chẩn đoán entry/exit

**Rổ Swing âm ngay ở phép đo giá thô, đồng thời có trả lại lợi nhuận sau entry.** Giữ xuyên tuần làm xấu kết quả trên đối chứng đã khóa. Chỉ đổi trailing stop chưa có đủ cơ sở cứu danh mục. Performance CSV chạy qua pipeline trên 199 dòng, với 0 dòng có đủ dữ liệu mô phỏng vốn FTMO.

## 1. Tách vấn đề entry, thời gian giữ và exit

Đọc lại sổ Development đã seal của [8fd77ef](SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.md) và [USDJPY de62a92](BOTTLENECK2-ASYMMETRIC-PIVOT-20261119.md). Có 2.500 dòng qua sáu khung xem (rổ và sleeve có thể chứa cùng lệnh). BASE_GUARD dùng tape SYM 2018–2023. Các nhóm còn lại dùng 2018–2024. MAE, MFE theo R gốc của từng lệnh. R/năm theo sổ sizing hoặc tape tham chiếu tương ứng.

**MAE** là lỗ nổi xấu nhất, **MFE** là lời nổi tốt nhất theo đường đi quan sát. MFE dưới đây đã ròng phí. MFE ≤ 0R nghĩa là chưa có đỉnh lời dương sau phí trong phần đường đã đo. Capture là net thực nhận chia cho MFE. Mọi đỉnh đều được biết sau entry.

| Nhóm | Có path / tổng | MAE / MFE toàn mẫu | MAE / MFE thắng | MAE / MFE thua | MFE 0R | Lệnh thua từng dương | Capture winner | Net R/năm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Swing 10k equal-risk | 839/839 | 1,00 / 0,58 | 0,05 / 4,72 | 1,00 / 0,22 | 276/839 | 370/646 | 37,5% | −25,02 |
| Trend D1 | 688/688 | 1,00 / 0,69 | 0,05 / 4,76 | 1,00 / 0,27 | 213/688 | 322/535 | 33,8% | −23,83 |
| Carry + Trend D1 | 433/433 | 0,99 / 0,60 | 0,03 / 4,82 | 1,00 / 0,16 | 149/433 | 180/329 | 43,1% | −5,43 |
| US500 Dip D1 | 34/34 | 0,75 / 0,25 | 0,05 / 1,04 | 1,02 / 0,00 | 12/34 | 6/18 | 85,7% | −0,43 |
| USDJPY ASYM_B | 166/166 | 0,96 / 0,61 | 0,09 / 2,55 | 1,00 / 0,20 | 34/166 | 70/104 | 77,7% | 8,69 |
| BASE_GUARD Dev | 315/340 | 0,45 / 0,35 | 0,23 / 0,85 | 0,79 / 0,15 | 42/315 | 137/179 | 65,8% | 4,03 |

| Nhóm | Markout thô gross / net (R) | Năm net dương | Giữ lâu hơn so với Friday open, Δ gross / net ghép (R) |
| --- | --- | --- | --- |
| Swing 10k equal-risk | −48,51 / −268,97 | 1/7 | −523,79 / −756,16 |
| Trend D1 | −12,66 / −219,70 | 0/7 | −438,52 / −675,08 |
| Carry + Trend D1 | −39,95 / −50,82 | 2/7 | −80,79 / −75,43 |
| US500 Dip D1 | 4,10 / 1,54 | 4/7 | −4,49 / −5,65 |
| USDJPY ASYM_B | 81,06 / 68,55 | 3/7 | Chưa có cặp tương ứng |
| BASE_GUARD Dev | Chưa có cùng chuẩn | — | Chưa có cặp tương ứng |

- **Swing 10k.** 37,5% capture áp dụng cho 193 winner. Trong 646 lệnh thua, 276 chưa từng có MFE ròng dương và 370 từng dương rồi đóng âm. Sổ có SL ghi gross −62,79R, phí vào–ra 16,92R và swap −95,43R toàn kỳ. Markout thô của 3.192 endpoint âm cả trước phí. Dời mốc thoát sang Friday D1 open giúp −25,02 thành −10,07R/năm. Δ net ghép cặp và hiệu suất hai sổ có mẫu số khác nhau do lệnh chồng lấn và slot. Bằng chứng chỉ ra thiếu lợi thế ở chân trời đã thử và có giveback. Chưa thể chia khoản lỗ theo tỷ lệ nhân quả.
- **Trend, Carry, Index.** Trend thô âm sau phí 7/7 năm. Carry thô dương 2/7 năm, swap thô dương 3,22R nhưng gross thô −39,95R. Index có +1,54R markout thô sau phí trên 35 intent và cadence thấp. Giữ qua Friday open mất thêm 5,65R net trên cặp Index.
- **USDJPY.** Sổ đóng có +8,69R/năm và winner capture 77,7%. Markout thô dương tổng +68,55R sau phí nhưng chỉ dương 3/7 năm. Chưa chứng minh lợi thế bền theo thời gian hoặc tác động của một exit mới.
- **BASE_GUARD.** Tape Dev tham chiếu +4,03R/năm. Có path cho 315/340 lệnh, gồm 179 lệnh thua với 137 từng dương. Winner capture 65,8%. M1 OLHC dùng trình tự mô phỏng trong nến và thiếu 25 đường đủ tin cậy. Thiếu phép đo raw và exit đối chứng trên cùng tập lệnh để quy giveback thành edge có thể cứu.

## 2. Benchmark trên Performance CSV có sẵn

Hai bản CSV (thường và _all) cho cùng 199 dòng sau chuẩn hóa, tính một lần. Nguồn là nhật ký do người giao dịch ghi từ 14/11/2025 đến 10/07/2026. Lượt này chỉ đọc CSV được chỉ định. Giá Holdout vẫn niêm phong. Không có xác nhận fills từ broker.

23 cột gốc gồm `Name`, `Trade Date`, `Trade Recap`, `Learning`, `Pair`, `Po3 Range`, `Strategy`, `Setup`, `Macro`, `Hợp lưu GB`, `Follow your plan`, `bias`, `Market Condition`, `Entry`, `Entry TF`, `R:R`, `R:R Potential`, `WR`, `Position`, `Day`, `Month`, `STime Entry`, `News`. Các trường có giá trị cho bộ audit gồm Pair, Position, Trade Date, WR và R:R. Trong Trade Date có 116 dòng tới phút theo GMT+7, 83 dòng chỉ tới ngày. Cột R:R Potential để riêng khỏi R tự ghi.

| Mã nguồn quy về | Số dòng | Thắng / thua / hòa | Win rate | R tự ghi |
| --- | --- | --- | --- | --- |
| USTEC | 144 | 77 / 61 / 6 | 53,5% | 313,90 |
| XAUUSD | 28 | 10 / 16 / 2 | 35,7% | 15,65 |
| GER40 | 7 | 3 / 4 / 0 | 42,9% | 4,96 |
| GBPJPY | 7 | 5 / 2 / 0 | 71,4% | 10,83 |
| EURUSD | 6 | 2 / 3 / 1 | 33,3% | 3,31 |
| US500.cash | 3 | 2 / 1 / 0 | 66,7% | 8,54 |
| GBPUSD | 3 | 3 / 0 / 0 | 100,0% | 6,99 |
| DẦU | 1 | 0 / 1 / 0 | 0,0% | −0,90 |
| Tổng | 199 | 102 / 88 / 9 | 51,3% | 363,28 |

R trung bình tự ghi là **1,826R/lệnh**, với 0 dòng lệch dấu giữa WR và R:R. Top 2/5/10 chiếm 18,7% / 26,3% / 35,3% pool R dương. Tháng cao nhất chiếm 30,4% theo ngày journal. Chưa thấy cờ concentration theo ngưỡng chẩn đoán. USTEC có 144/199 dòng và chưa có spec trong hai snapshot đã khóa.

| Kiểm tra | Độ phủ / kết quả |
| --- | --- |
| Martingale | Unknown. 0/199 có lot hoặc close time. |
| Grid / averaging down | Unknown. Thiếu thời điểm đóng, giá fill và mark trong lúc giữ. |
| SL / lỗ đuôi | Unknown. Thiếu SL ở 199/199. Avg Loss / Avg Win theo R tự ghi là 0,229. |
| FTMO 5% / 10%, margin, Standard kỳ nghỉ | Unknown ở cả 8 kịch bản. 0 lệnh đủ dữ liệu để dựng equity. |
| Commission, swap, MAE/MFE và PnL USD | Unknown. 0/199 có giá mở/đóng, commission, swap hoặc PnL USD. |
| Winner taxonomy | 102 winner ở trạng thái UNCLASSIFIED_MISSING_EVIDENCE. |

## 3. Scorecard và quy trình nạp log

Module hỗ trợ CSV/HTML lịch sử theo cột tương thích Myfxbook, MQL5 Signals, Darwinex/cTrader và parser MT4/MT5 closed/deals. Layout kiểm theo fixture. Cờ lot dùng hai lệnh đã đóng thua trước entry. Cờ grid cần mark giá khi vị thế cũ còn mở. Trống stop là unknown. Sizing cần stop lúc mở có nguồn. Phân rã lệnh thua ghi gross, commission và swap. Nhãn winner dùng Selective Win Diagnosis, tách đường giá hậu nghiệm khỏi entry.

Profile Swing 10k/25k dùng 8fd77ef, Standard 10k/50k dùng 36f1535. Trọng tâm 80/20 và risk 0,50%/1,00% là thiết lập scorecard. Phí đích 5 USD/lot FX, 0 cho US500.cash, 0,0007% notional mỗi phía XAUUSD và swap snapshot. Spread đã nằm trong giá fill. Định giá lại giữ nguyên fills nhập, nên vẫn còn bất định về khớp lệnh bên FTMO.

FTMO 2-Step áp 5% theo balance tại 00:00 CE(S)T và 10% static theo vốn đầu. Quy tắc nghỉ >2 giờ áp cho funded Standard. Đường Bid M1 cộng Ask proxy chỉ dựng được các mốc quan sát. Cash flow và lệnh ngoài file còn thiếu nếu không có từ nguồn. [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/) · [FTMO policy giữ qua kỳ nghỉ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

Ưu tiên **một Myfxbook full-history CSV có giá, lot, timezone và chi phí**, kèm MT4/MT5 History cùng tài khoản và stop lúc mở để đối chiếu. [Myfxbook hướng dẫn export](https://www.myfxbook.com/help/knowledge-base/exporting-trading-history/).

[Lệnh CLI tại inbox](../../research/bot_reverse_lab/inbox/live_signals/README.md) · [Playbook](BOT-REVERSE-LAB-PLAYBOOK.md#scorecard-ftmo-từ-log-thực-chiến).

CLI kiểm trực tiếp trên file thật. 61 test liên quan PASS, 0 skip, gồm normalizer, stop unknown, martingale/grid, Daily Loss theo Prague, lỗ nổi khi lệnh đóng hòa, chặn giá holdout và audit cả thắng/thua. OrderSend = 0. Niêm phong từ 01/01/2025 giữ nguyên.

[JSON đối soát](BOT-LAB-LIVE-AUDITOR-AND-LEAKAGE-DIAGNOSIS-20261120.json) · [SHA256](BOT-LAB-LIVE-AUDITOR-AND-LEAKAGE-DIAGNOSIS-20261120.sha256).
Private manifest: bot-lab-live-20261120/manifest.json. SHA256: b4e2b66903266f97a34106a0afe6feb5465f82b1e4923c567508614b668772f4. Checksum báo cáo và JSON dùng byte LF chuẩn trong Git.
