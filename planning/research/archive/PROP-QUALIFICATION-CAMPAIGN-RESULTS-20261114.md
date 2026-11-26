# Kết quả chiến dịch exit → sleeves → vòng đời quỹ

**Kết luận: đã hoàn tất chiến dịch, nhưng chưa đủ cơ sở để mua Challenge.** Không exit mới hoặc sleeve nào vượt cổng Development. Hệ thống cuối giữ A gốc; chính sách vốn mới giúp qua vòng 1 nhiều hơn, vẫn không hoàn tất hai vòng hoặc tạo payout.

Owner: task `229f6d76-e9a1-4f58-bcf4-c1545bea757b`. Ngày 14/11/2026. PR78 đã merge `3307fae`; baseline/result vẫn bất biến. Protocol khóa tại `95e3709`; quyết định Development và code tại `2e713c1`, trước mở kết quả mới năm 2024. 2025–2026 không được giải mã. Không broker, mua challenge, gọi model hay sửa VI Dubber.

## 1. Trước và sau — 36 mốc xuất phát tháng

Mỗi hàng dùng cùng 36 ngày bắt đầu từ 01/2022 đến 12/2024, kết thúc trước 01/01/2025. Mốc muộn có thời gian theo dõi ngắn hơn; các cửa sổ chồng lấn, không là 36 thử nghiệm độc lập. Các tỷ lệ là kết quả quan sát, không phải xác suất thắng tương lai. SYM = swap −40/−40; ASYM = proxy −45/−5 USD/lot/rollover.

| Hệ thống / risk | Phí | Qua vòng 1 | Qua cả hai | Trung vị vòng 1* | Vi phạm | Worst daily | Worst static | Peak DD | Payout |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Anchor0 / fixed 0.30% | SYM | 0/36 | 0/36 | Chưa có | 0 | 0.799% | 5.271% | 6.653% | 0 / $0.00 |
| Anchor0 / fixed 0.40% | SYM | 2/36 | 0/36 | 12.82 tháng | 0 | 1.071% | 7.234% | 8.874% | 0 / $0.00 |
| Frozen A0 / .50% → .35% → .25% | SYM | 8/36 | 0/36 | 11.31 tháng | 0 | 1.335% | 9.321% | 12.728% | 0 / $0.00 |
| Anchor0 / fixed 0.30% | ASYM | 0/36 | 0/36 | Chưa có | 0 | 0.731% | 4.895% | 6.268% | 0 / $0.00 |
| Anchor0 / fixed 0.40% | ASYM | 5/36 | 0/36 | 15.67 tháng | 0 | 0.979% | 7.083% | 8.356% | 0 / $0.00 |
| Frozen A0 / .50% → .35% → .25% | ASYM | 13/36 | 0/36 | 10.64 tháng | 0 | 1.221% | 8.899% | 11.849% | 0 / $0.00 |

*Trung vị chỉ tính các mốc đã đạt, không suy ra thời gian của 36 mốc còn lại. Không có trung vị hoàn tất cả hai vòng vì chưa có trường hợp hoàn tất.

Risk mới cố định trước kết quả: vòng 1 0,50%, vòng 2 0,35%, funded 0,25%; giảm risk lệnh mới xuống 0,25% khi lỗ thực hiện trong ngày >1,8% hoặc equity dưới 95,5% vốn đầu. Vị thế cũ giữ size cũ. Có cổng dự trữ rủi ro chung theo SL, phí và funding; không chọn risk bằng cách thử nhiều mức trên kết quả.

Worst static 9,32% để lại chỉ khoảng 0,68 điểm phần trăm trước giới hạn 10%; “không vi phạm trong mẫu” không đồng nghĩa đủ an toàn. Peak DD là sụt giảm từ đỉnh, khác static loss tính dưới vốn đầu. Daily 5% là ranh giới cấm, không là ngân sách cần dùng hết.

## 2. Kinh tế tín hiệu không được cải thiện bởi tăng size

Bảng dùng đúng $150 rủi ro danh nghĩa mỗi lệnh để tách thay đổi tín hiệu khỏi đi vốn. Trước/sau giống nhau vì mọi biến thể bị loại. Return (%) = Net R × 0,30%; 1R = $150, không phải toàn bộ số dư tài khoản.

| Năm | Phí | Lệnh | Net R trước = sau | Return | Equity DD (R) | Peak DD | Static loss | Worst daily | Net bỏ top 3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | SYM | 103 | +4.050 | +1.215% | 16.617 | 4.985% | 1.112% | 0.686% | -17.142R |
| 2023 | SYM | 107 | +13.795 | +4.138% | 22.177 | 6.653% | 3.202% | 0.799% | -10.369R |
| 2024 | SYM | 98 | +1.845 | +0.554% | 13.233 | 3.970% | 3.486% | 0.623% | -11.995R |
| 2022 | ASYM | 103 | +5.901 | +1.770% | 15.975 | 4.792% | 1.112% | 0.698% | -15.490R |
| 2023 | ASYM | 107 | +16.462 | +4.939% | 20.893 | 6.268% | 2.818% | 0.731% | -8.052R |
| 2024 | ASYM | 98 | +2.645 | +0.793% | 12.977 | 3.893% | 3.409% | 0.624% | -11.155R |

ASYM trung bình chỉ **8.336R/năm**, vẫn thấp hơn mục tiêu 25–40R/năm; equity DD năm 2023 khoảng 20,9R, cũng vượt đích 12–15R. Bỏ ba lệnh thắng lớn nhất thì cả ba năm đều âm. Đây là phép đo độ tập trung; không tự bác trend-following chỉ vì lợi nhuận tập trung, nhưng chưa đủ biên an toàn cho mục tiêu thu nhập chính.

## 3. Phase 1 — giải phẫu giveback và ba exit

| Ngưỡng MFE ngày 1, sau phí | Đã đạt / 210 | Sau đó đóng âm (SYM / ASYM) | Mất ≥50% lãi đỉnh (SYM / ASYM) |
|---|---:|---:|---:|
| ≥1R | 67 | 23 / 22 | 31 / 30 |
| ≥1.5R | 36 | 6 / 6 | 11 / 11 |
| ≥2R | 22 | 4 / 4 | 6 / 6 |
| ≥3R | 7 | 0 / 0 | 1 / 1 |

Các nhóm ngưỡng lồng nhau, không cộng thành số lệnh riêng.

| Năm | Thanh lý trước rollover đầu | Phần thay đổi sau đó SYM | Phần thay đổi sau đó ASYM |
|---|---:|---:|---:|
| 2022 | +5.839R | -1.789R | +0.062R |
| 2023 | -1.870R | +15.665R | +18.332R |

Đây là chênh lệch giữa các điểm thanh lý trên đường giữ lệnh thực, không phải chứng minh nhân quả cho “ngày 2”. Các lệnh đã SL/đóng sớm giữ đúng điểm đóng; giá trước 22UTC có thể cũ qua giờ bảo trì. Không biến carried mark thành giá mới có thể khớp.

| Exit | Phí | Net R 2022 / 2023 | Equity DD R 2022 / 2023 | Bỏ top 3 R 2022 / 2023 | Quyết định |
|---|---|---:|---:|---:|---|
| A0 | SYM | +4.050 / +13.795 | 16.617 / 22.177 | -17.142 / -10.369 | Giữ baseline |
| A0 | ASYM | +5.901 / +16.462 | 15.975 / 20.893 | -15.490 / -8.052 | Giữ baseline |
| E1 | SYM | +16.691 / +2.401 | 9.269 / 19.031 | -4.502 / -18.706 | Không đạt cổng cải thiện cả hai năm |
| E1 | ASYM | +17.032 / +2.865 | 9.269 / 19.063 | -4.359 / -18.615 | Không đạt cổng cải thiện cả hai năm |
| E2 | SYM | +1.769 / -1.064 | 13.427 / 20.483 | -18.951 / -16.486 | Không đạt cổng cải thiện cả hai năm |
| E2 | ASYM | +2.644 / +9.921 | 13.370 / 19.521 | -18.263 / -11.854 | Không đạt cổng cải thiện cả hai năm |
| E3 | SYM | N/A | N/A | N/A | 76/210 mốc 21:30 không có giá mới; không chọn |
| E3 | ASYM | N/A | N/A | N/A | 76/210 mốc 21:30 không có giá mới; không chọn |

E1 đóng 20:30 nếu chưa lãi ròng 1,5R; lệnh được giữ có stop dự phòng chi phí. E2 kích hoạt bảo vệ tại 1,5R rồi dùng nến H1 đóng qua SMA20 để thoát, không đặt trần TP. E3 dùng đệm phí carry lúc 21:30. E3 có 76 quyết định rơi trong giờ nghỉ thị trường: các đường parent giữ trong artifact chỉ phục vụ chẩn đoán, không được cộng thành kết quả E3 hợp lệ. Không đổi giờ E3 để cứu kết quả. Stop bảo vệ vẫn có thể lỗ khi gap/trượt giá.

## 4. Phase 2 — ba sleeve, không dùng slot thứ tư

| Sleeve | Năm | Tín hiệu / đủ giá | SL trung vị | Phí/SL | Qua cổng 12% | Net markout SYM / ASYM | Ma sát trung bình |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | 2022 | 57 / 57 | 7.99 USD/oz | 9.65% | 66.7% | +0.259 / +0.259 USD/oz | 0.801 USD/oz |
| S1 | 2023 | 70 / 70 | 8.28 USD/oz | 9.24% | 65.7% | +1.970 / +1.970 USD/oz | 0.799 USD/oz |
| S2 | 2022 | 40 / 40 | 8.66 USD/oz | 8.91% | 70.0% | -1.819 / -1.440 USD/oz | 0.794 USD/oz |
| S2 | 2023 | 37 / 37 | 6.10 USD/oz | 12.24% | 51.4% | +3.587 / +3.975 USD/oz | 0.760 USD/oz |
| S3 | 2022 | 86 / 86 | 46.20 pip | 2.81% | 100.0% | -8.978 / -8.978 pip | 1.300 pip |
| S3 | 2023 | 94 / 94 | 30.70 pip | 3.91% | 100.0% | -8.479 / -8.479 pip | 1.232 pip |

- **S1:** H1 hồi rồi vượt nến trước theo H4, 12–16UTC, đóng 20:30. Năm 2022 dương +0,259 USD/oz nhưng nhỏ hơn ma sát 0,801: không qua Stage-0 đã khóa.
- **S2:** H1 inside-bar rồi breakout theo H4, giữ 48h/chặn nghỉ lễ. Âm năm 2022; năm 2023 chỉ 37 tín hiệu và tỷ lệ quy mô 12,24% vượt ngưỡng 12% đã chọn.
- **S3:** EURUSD H1 phá vùng Á theo H4, giữ 24h/chặn lịch. Quy mô SL phù hợp, nhưng âm cả hai năm. Dùng phí 9 USD/lot/vòng và swap stress −40 USD/lot/rollover cả hai chiều; đây là kịch bản bảo thủ được đăng ký, không biểu phí lịch sử FTMO đã xác minh.

**Không sleeve nào được sang Stage-1**, nên không viết SL-active/đo tương quan hay ghép portfolio để cứu chúng. Tương quan là N/A, không giả bằng 0. Không chạy US500 hoặc dùng slot thứ tư chỉ để vét ngân sách. Không có portfolio đa nhánh đủ điều kiện trong chiến dịch này.

## 5. Sổ 36 mốc tháng — chính sách vốn mới

| Bắt đầu | SYM vòng 1 | SYM vòng cuối / balance | ASYM vòng 1 | ASYM vòng cuối / balance |
|---|---|---:|---|---:|
| 2022-01-01 | 2023-10-20 | 2 / $48,746.44 | 2023-10-20 | 2 / $49,609.11 |
| 2022-02-01 | 2023-10-20 | 2 / $48,746.44 | 2023-10-04 | 2 / $50,887.27 |
| 2022-03-01 | Chưa đạt | 1 / $47,529.61 | Chưa đạt | 1 / $48,315.55 |
| 2022-04-01 | Chưa đạt | 1 / $47,650.23 | Chưa đạt | 1 / $47,572.27 |
| 2022-05-01 | Chưa đạt | 1 / $47,646.05 | Chưa đạt | 1 / $47,758.71 |
| 2022-06-01 | Chưa đạt | 1 / $47,730.93 | Chưa đạt | 1 / $53,466.10 |
| 2022-07-01 | 2023-10-20 | 2 / $48,746.44 | 2023-10-20 | 2 / $49,609.11 |
| 2022-08-01 | Chưa đạt | 1 / $52,906.47 | 2023-10-20 | 2 / $49,609.11 |
| 2022-09-01 | Chưa đạt | 1 / $47,641.36 | Chưa đạt | 1 / $47,769.76 |
| 2022-10-01 | 2023-11-10 | 2 / $48,443.61 | 2023-10-20 | 2 / $49,609.11 |
| 2022-11-01 | Chưa đạt | 1 / $52,915.48 | 2023-10-20 | 2 / $49,609.11 |
| 2022-12-01 | Chưa đạt | 1 / $52,930.56 | 2023-10-20 | 2 / $49,609.11 |
| 2023-01-01 | Chưa đạt | 1 / $52,960.27 | 2023-10-20 | 2 / $49,609.11 |
| 2023-02-01 | 2023-11-10 | 2 / $48,443.61 | 2023-10-20 | 2 / $49,609.11 |
| 2023-03-01 | Chưa đạt | 1 / $53,010.21 | 2023-10-20 | 2 / $49,609.11 |
| 2023-04-01 | Chưa đạt | 1 / $48,799.52 | Chưa đạt | 1 / $50,486.82 |
| 2023-05-01 | Chưa đạt | 1 / $48,786.19 | Chưa đạt | 1 / $50,493.48 |
| 2023-06-01 | Chưa đạt | 1 / $52,761.81 | Chưa đạt | 1 / $53,426.38 |
| 2023-07-01 | 2023-10-20 | 2 / $48,746.44 | 2023-10-20 | 2 / $49,609.11 |
| 2023-08-01 | 2023-10-20 | 2 / $48,746.44 | 2023-10-20 | 2 / $49,609.11 |
| 2023-09-01 | 2023-11-10 | 2 / $48,443.61 | 2023-10-20 | 2 / $49,609.11 |
| 2023-10-01 | Chưa đạt | 1 / $51,112.21 | Chưa đạt | 1 / $51,435.31 |
| 2023-11-01 | Chưa đạt | 1 / $48,196.75 | Chưa đạt | 1 / $48,912.67 |
| 2023-12-01 | Chưa đạt | 1 / $47,626.84 | Chưa đạt | 1 / $48,280.36 |
| 2024-01-01 | Chưa đạt | 1 / $48,801.32 | Chưa đạt | 1 / $48,274.12 |
| 2024-02-01 | Chưa đạt | 1 / $51,737.94 | Chưa đạt | 1 / $51,875.24 |
| 2024-03-01 | Chưa đạt | 1 / $53,089.72 | Chưa đạt | 1 / $53,225.47 |
| 2024-04-01 | Chưa đạt | 1 / $50,630.29 | Chưa đạt | 1 / $51,044.65 |
| 2024-05-01 | Chưa đạt | 1 / $51,049.76 | Chưa đạt | 1 / $51,191.66 |
| 2024-06-01 | Chưa đạt | 1 / $50,520.85 | Chưa đạt | 1 / $50,512.88 |
| 2024-07-01 | Chưa đạt | 1 / $51,960.74 | Chưa đạt | 1 / $52,067.99 |
| 2024-08-01 | Chưa đạt | 1 / $50,642.56 | Chưa đạt | 1 / $51,008.82 |
| 2024-09-01 | Chưa đạt | 1 / $51,951.50 | Chưa đạt | 1 / $52,035.35 |
| 2024-10-01 | Chưa đạt | 1 / $51,642.55 | Chưa đạt | 1 / $51,729.70 |
| 2024-11-01 | Chưa đạt | 1 / $52,925.89 | Chưa đạt | 1 / $52,986.49 |
| 2024-12-01 | Chưa đạt | 1 / $50,675.17 | Chưa đạt | 1 / $50,725.77 |

Cả 72 trường hợp kết thúc do hết lịch sử quan sát, không phải bị xóa vì thua. Không tự retry/reset khi lỗ, không nối các sổ năm độc lập, không mang vị thế cũ sang tài khoản mới.

## 6. Payout, chi phí và khoảng trống thực thi

Reward proxy: chỉ tài khoản funded, flat, đã đủ 30 ngày từ lệnh funded đầu/chu kỳ trước và lãi đóng ≥20 USD mới xét. Trừ 100% lãi khỏi tài khoản; 80% quyền nhận của trader, 20% của firm. Không rút 80% rồi xóa thêm 20% không hạch toán; không bơm vốn vào tài khoản đang lỗ. Không có tài khoản funded nên funded policy/payout chỉ được kiểm bằng fixture, chưa có đường thực nghiệm. Không có tiền thật nhận về, chưa trừ phí mua/retry Challenge hay chi phí vận hành khỏi thu nhập.

FAQ FTMO kiểm ngày 14/11/2026 cho phép yêu cầu từ ngày 14, account flat, min20USD bank/card (50USD crypto), mức chia thông thường 2-Step80%. Mô hình giữ mốc 30 ngày bảo thủ hơn, nhưng bỏ qua chờ xét duyệt/chi trả và giả định reset/new cycle tức thời. Nguồn: https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/

Các assumption giữ nguyên: Bid/Ask lịch sử Dukascopy/QDM; vàng100oz/lot, min/step0,01lot; commission0,0007%notional/side; slippage0,20USD/oz/side; rollover22UTC, thứ Tư×3; lịch Friday20:30/holiday đã khóa. Đây không phải snapshot đầy đủ của tài khoản đích. Floating/cash giữ convention Anchor0: fee vào ghi balance, funding đang mở nằm floating, một leg slip trong floating, hai leg slip quyết toán khi đóng; cổng reserve tính cả hai. Giá cũ ở Prague reset và giờ nghỉ vẫn là carried mark. Margin/leverage, execution latency, historical news restrictions, actual swaps và lịch/feed đích chưa xác minh đủ; không được gắn prop_qualified=true.

## 7. Kiểm chứng, lỗi phát hiện và tái hiện

- 147 tests hồi quy đạt, gồm21 fixtures mới về exit/protection, fill clock, scope dữ liệu, rounding, phase risk/throttle, reserve, collision, daily reset, target, payout và censoring.
- Oracle Fraction độc lập công thức: 2464 cost bridges ở risk125/150/175/250USD; 616 so khớp đường parent qua hai mô hình phí.
- 72 tài khoản được đối soát bằng sổ khác cách hạch toán: oracle ghi swap vào cash rồi phục hồi anchor thực hiện; so đúng cash, peak DD, static DD, daily loss và thời điểm breach. 21 terminal transitions đối chiếu primitive prop_session hiện có.
- Đây là đối soát tính toán do cùng người triển khai, không gọi là review độc lập bởi agent/người khác. Không gửi Astra.
- 108 giờ tick bổ sung được đối chiếu M1 trước outcome, không phát hiện mismatch. EURUSD half-hour endpoints được seek lại CSV gốc: đủ86/86 và94/94, không dùng giá đầu giờ thay20:30.
- Parity bắt lỗi horizon dùng decision thay observed entry: sửa đồng hồ, giữ outcome trước sửa trong `clock-correction-attempt`; không thay tín hiệu, SL, chi phí hoặc ngưỡng lựa chọn. Lỗi E3 thiếu quote được giữ trong `phase1-attempt1`; chặn chọn thay vì bịa giá.

Tái hiện bằng Python3.12.10, NumPy2.3.5 và dependencies của Trader đã pin. Nguồn local riêng không đẩy tick/CSV/cache lên GitHub. Các lệnh đã chạy:

```powershell
$env:PYTHONPATH="D:/ANNAM/TradingWorkspace/projects/trader/foundation_v2;D:/ANNAM/TradingWorkspace/tooling/ai-engines"
python tooling/ai-engines/run_prop_campaign.py phase1
python tooling/ai-engines/run_prop_campaign.py validation
python tooling/ai-engines/prop_campaign_review.py
python -m unittest discover -s tooling/ai-engines/tests -p test_prop_campaign.py
```

Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-qualification-campaign-20261114`. `registration.json`, `implementation-freeze.json`, `composition-freeze.json`, `validation-release.json`, source reviews, per-trade paths, `lifecycle-*.json`, `computational-parity.json` và JSON cạnh báo cáo giữ hashes/locators. Không chạy lại study chỉ để đọc báo cáo. Source/preparation và những lần sửa clock/coverage được giữ riêng; thay numeric input/code phải tạo attempt mới, không ghi đè receipt đã đóng.

## 8. Quyết định sau chiến dịch

**Gác Challenge với A hiện tại và không tăng risk thêm.** Nút thắt vẫn là tốc độ tích lũy lợi nhuận và độ bền ngoài các lệnh đuôi lớn; sizing không tạo edge hoặc thêm mẫu độc lập. Nếu mở đợt nghiên cứu mới, cần một cơ chế có lý do kinh tế khác, khóa cadence/cost/markout trước và chỉ tiếp tục sau Stage-0; không tiếp tục vặn ba exit hoặc ba sleeve vừa bị loại. Một nhánh có lợi nhuận trong mẫu là benchmark hữu ích, chưa là nguồn thu nhập chính đã được chứng minh.

Hậu kiểm engineering: giữ vectorized sufficient statistics vì đã khớp Anchor0 và oracle dòng tiền khác công thức; không tuyên bố speedup khi chưa có benchmark cùng workload. Lỗi clock và endpoint được sửa bằng guard/test; chưa có bằng chứng cần engine/framework mới. Không sửa skill thêm để lặp lại policy vốn đã có.
