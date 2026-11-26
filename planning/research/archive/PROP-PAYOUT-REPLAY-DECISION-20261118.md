# Vốn 50.000 USD — có nên dành thêm lượt replay để đi tới payout?

**Chưa có nhánh đủ cơ sở cho một lượt replay tài khoản mới.** F4 là nhánh
dương ổn định hơn trong ba nhánh hiện tại, nhưng đã nằm trong BASE_GUARD
và chỉ đóng góp hàng trăm USD mỗi năm. V23 đã thử bỏ F3. V26 đã thử
đổi trọng số. Phương án chưa thử là thay đúng F3 bằng R043 ở risk
125 USD, và phép định cỡ cho thấy mức đóng góp còn giảm. Giữ
BASE_GUARD ở `NOT_QUALIFIED`.
[Tiêu chí khóa trước tại `956d682`](PROP-PAYOUT-REPLAY-ADMISSION-20261118.md)

## 1. Tiền và số lệnh ở từng lớp

Tất cả khoảng tính mới là 2018–2023. **USD/năm** là tổng trong sáu năm
chia sáu. **R/lệnh** là tiền ròng chia risk định mức từng lệnh.
Sổ 150 USD đóng vai trò tham chiếu kinh tế. Sổ account có sizing riêng
và khả năng từ chối lệnh. PRIMARY và STRICT dùng cùng phí. STRICT
giả định đường giá bất lợi khi gặp khoảng trống.
[V19](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.md)

| Nhánh | Tín hiệu có trong sổ tham chiếu | USD/năm PRIMARY / STRICT ở $150 | Net R/lệnh PRIMARY / STRICT | Sổ Funded độc lập PRIMARY / STRICT, số lệnh nhận | Net USD/năm trong sổ Funded PRIMARY / STRICT | Net R/lệnh Funded PRIMARY / STRICT |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD F5 | 194 | +629,78 / −14,33 | +0,130 / −0,003 | 194 / 151 | +794,46 / −258,59 | +0,131 / −0,067 |
| Gold F3 | 63 | −242,53 / −288,13 | −0,154 / −0,183 | 63 / 47 | −307,34 / −195,29 | −0,156 / −0,220 |
| Gold F4 | 83 | +209,06 / +103,64 | +0,101 / +0,050 | 83 / 62 | +269,40 / +138,47 | +0,104 / +0,062 |
| **Tổng** | **340** | **+596,31 / −198,82** | | **340 / 260** | **+756,52 / −315,41** | |

Risk Funded hiện hành là 187,50 USD, giảm xuống tới 75 USD trong
STRICT. 80 tín hiệu Funded STRICT bị guard dự phóng lỗ từ chối.
Trong **61 cửa sổ Challenge đủ 12 tháng**, số lượt xuất hiện của F5 /
F3 / F4 là 1.987 / 646 / 854. PRIMARY khớp 1.984 / 640 / 850, còn
STRICT khớp 1.982 / 643 / 852. Đây là lượt xuất hiện qua các cửa sổ
chồng lấn. Trong riêng pha 1, R/lệnh PRIMARY / STRICT lần lượt là
F5 +0,095 / −0,055, F3 −0,195 / −0,203, F4 +0,103 / +0,070.
Risk yêu cầu theo pha là 300 / 262,50 / 187,50 USD. F5/F4 có đóng
góp trong sổ hiện tại, nên một phương án giữ nguyên hai nhánh có
**0 lợi nhuận cộng thêm** từ việc chỉ đếm lại chúng.

### Độ phân tán và lệnh lớn

| Nhánh | USD cụm 2018–20 / 2021–23 (PRIMARY) | USD cụm 2018–20 / 2021–23 (STRICT) | Năm dương (P/S) | Lệnh vướng đường giá | Bỏ top 10 của cả danh mục Development, USD P/S |
|---|---:|---:|---:|---:|---:|
| F5 | +1.019,77 / +2.758,90 | +857,41 / −943,38 | 4/6 · 2/6 | 18 | −1.564,40 / −4.767,84 |
| F3 | −372,30 / −1.082,87 | −372,30 / −1.356,46 | 0/6 · 0/6 | 2 | −1.455,17 / −1.728,76 |
| F4 | +753,33 / +501,03 | +416,34 / +205,49 | 4/6 · 4/6 | 5 | +243,27 / −389,26 |

Top 10 lấy từ sổ PRIMARY Development rồi giữ cùng danh tính ở STRICT.
F5 chiếm tám lệnh, F4 chiếm hai. F5 dao động từ −673,20 đến +2.239,59 USD
theo năm PRIMARY, F4 từ −331,32 đến +603,76 USD. F4 dương hai cụm
dưới STRICT, nhưng cả hai nhánh còn phụ thuộc đuôi thắng hoặc đường
giá, và F4 chỉ có 6–21 tín hiệu/năm. Đây là phép cắt đuôi mô tả,
không dùng để sửa công thức.
[Đối chiếu đường giá](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md)

## 2. Lợi nhuận, thời gian đến funded và tiền rút

Dưới đây là hai sổ được chạy từ khi vẫn phải thi, cùng các sổ đã
Funded ngay từ đầu. Tất cả là mô phỏng. Cột DD ngày và lỗ static là
mức xấu nhất của 72 sổ Challenge chạy đến cutoff chung, nên bao
gồm thời đoạn sau tháng 12. Tỷ lệ lịch sử có cửa sổ chồng nhau.

| Development | Vòng 1 / hai vòng, trong 12 tháng | DD ngày / lỗ dưới vốn đầu | Đến Funded / có payout trước cutoff, 72 mốc | Payout/năm trên sổ đã Funded | Năm có payout / tháng trắng |
|---|---:|---:|---:|---:|---:|
| BASE PRIMARY | 6/61 · 0/61 | 1,359% / 6,383% | 6 / 6 | 631,26 USD | 5/6 · 57/72 |
| BASE phí +50% | 4/61 · 0/61 | 1,342% / 7,723% | 0 / 0 | 341,66 USD | 3/6 · 62/72 |
| BASE STRICT | 3/61 · 0/61 | 1,344% / 8,400% | 0 / 0 | 304,16 USD | 2/6 · 63/72 |
| V23 bỏ F3 PRIMARY | 6/61 · 0/61 | 1,876% / 4,675% | 6 / 6 | 877,13 USD | 6/6 · 52/72 |
| V23 bỏ F3 phí +50% | 4/61 · 0/61 | 1,905% / 5,162% | 6 / 6 | 690,35 USD | 5/6 · 55/72 |
| V23 bỏ F3 STRICT | 3/61 · 0/61 | 1,359% / 8,400% | 0 / 0 | 328,45 USD | 3/6 · 62/72 |

Trong nhóm mô phỏng PRIMARY đã tới được Funded, trung vị đến Funded /
payout đầu lần lượt **68,51 / 69,12 tháng** ở BASE và **56,37 / 61,20
tháng** khi bỏ F3. Sáu cửa sổ hoàn thành mỗi bản đều bắt đầu sớm
và dùng lại nhiều năm dữ liệu. Trong 61 cửa sổ đủ một năm, **0
tài khoản nhận payout** ở mỗi chế độ. V23 đưa payout giả định lên
thêm 245,87 USD/năm nếu đã Funded và giảm một số dạng DD, nhưng
không tăng số cửa sổ hoàn tất hai vòng sau 12 tháng. Đây là giá trị
chẩn đoán của việc bỏ F3, chưa có cơ sở tuyên bố tỷ lệ thành công
tương lai. Tiền rút thật đã xác nhận trong hồ sơ bằng 0.
[V23](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.md)

## 3. Bảng quyết định

| Phương án | Bằng chứng ở risk đã đo | Quyết định |
|---|---|---|
| F5/F4 đang dùng | F4 có edge hẹp ở cả hai kịch bản. F5 âm dưới STRICT. | Giữ nhãn đối chứng, không cộng lại vào portfolio. |
| V23 bỏ F3 | Tăng +9,70R, tương đương +242,53 USD/năm ở sổ $150. Cùng 0/61 qua cả hai vòng. | Đã có replay. Giữ làm đối chứng về loại trừ nhánh. |
| V26 P80_ISO_EXACT | Tăng +2,53R trên 340 lệnh Dev, khoảng **+63,17 USD/năm**. Equity DD giảm 12,2065R → 12,1885R. Risk mở 312,80 → 257,52 USD. V26 đã hoàn thành phép replay riêng và giữ BASE. | Dùng kết quả đã có. |
| Thay F3 bằng R043 nguyên bản | R043 có 98 khớp trong sổ năm riêng, 96 đóng, hai vị thế cuối sổ. 12–21 lệnh đóng mỗi năm. Ở $125, stress cho **−425,27 USD/năm** theo equity cuối năm và **−0,277R/lệnh đóng**. Giảm swap về reference cho −151,56 USD/năm và −0,146R/lệnh. | **Không replay.** Phiên bản đã khóa hụt cổng cả hai kịch bản. |
| Gold sweep London DAY của V8 | 107 tín hiệu, 44 qua cap ở 2022–2023. Ở $150, **+1.894,58 USD/năm** trên hai năm đó, +0,574R/lệnh đã lọc. Giữ 45,1% / 37,5%, tỷ lệ ma sát/stop trung vị 15,82% / 16,92%. | Có số đo dương đáng lưu. Cổng quy mô và giữ mẫu đã trượt, chưa có đóng góp sau ghép. |

Ở R043 nguyên bản, hai cụm stress lần lượt **−3.658,39 / +1.106,75
USD** theo equity cuối năm. Tổng 96 lệnh đóng trước swap đã âm
345,39 USD. Ba lệnh thắng lớn nhất cộng 2.758,72 USD, bỏ đi thì
tổng lệnh đóng giảm còn −6.080,51 USD. Sổ M1 riêng có lỗ ngày
quan sát cao nhất 246,30 USD và equity peak-to-trough 2.081,17 USD.
Đường M1 có phần thiếu. Sổ ghép cần một contract hỗ trợ R043 giữ
nhiều ngày, cùng lịch, swap và admission chung với hai nhánh Gold/FX.
Giá trị tăng thêm tĩnh khi thay F3 là **−182,75 USD/năm PRIMARY**
và **−137,15 USD/năm STRICT**. Hai phép đều hụt ngưỡng +1.000
USD/năm đã khóa. Những con số này chưa mô hình hóa sự trùng lệnh,
trần risk mở hoặc việc thay đổi các fill sau đó.
[R043 và phí](GOLD-R043-FINANCING-PATH-AUDIT-20261112.md) ·
[R043 M1](GOLD-M1-PATH-AND-EURUSD-POSTMORTEM-20261113.md) ·
[V26](BATCH-EXACT-ISO-V26-RESULTS-20261118.md) ·
[V8](PROP-GOLD-V8-RESULTS-20261115.md)

### Mức hợp lý để mở lại

Dùng **4.873,10 USD** từ phép độ nhạy đã hiệu chỉnh để hiểu độ lớn.
Thiếu hụt PRIMARY của sổ gốc vẫn là 4.929,17 USD ở nhóm chưa qua.
Mục tiêu đóng góp +1.000 USD/năm bằng khoảng 20,5% khoảng hụt đã
hiệu chỉnh. Với 40 **lệnh thực sự được nhận thêm** mỗi năm, cần
+25 USD/lệnh sau phí, tương đương +0,167R ở risk 150 USD hoặc
+0,083R ở 300 USD. Với 60 lệnh, con số tương ứng là +16,67 USD,
+0,111R hoặc +0,056R. Tự lấp cả khoảng hụt với 40 lệnh ở 300 USD
sẽ cần +0,406R/lệnh. Đây là phép định cỡ theo risk đã thấy, không
phải đề nghị chuyển sizing. Tìm phần cải thiện thêm **ở các cửa sổ
đang hụt**, giữ lợi thế qua cả hai cụm và kiểm guard trước khi dành
lượt cho 61 cửa sổ tài khoản.
[Thiếu hụt gốc](PROP-PHASE1-SHORTFALL-20261118.md) ·
[Đính chính độ nhạy](PROP-EUR-CLOCK-AND-TREASURY-AUCTION-RESULTS-20261118.md)

### Kiểm chứng

Đọc hóa đơn tiền và các sổ đã niêm phong. Đối chiếu sáu tập sổ
BASE/V23, 366 cửa sổ 12 tháng, mốc funded/payout, và cặp cụm R043
với SHA256. Kiểm lại tổng tham chiếu PRIMARY 3.577,86 USD và STRICT
−1.192,90 USD. Tính lại bảng chênh theo từng năm. Hồ sơ Zstandard
`payout-admission-v2-manifest.json` có SHA256
`e30552bd89c6f1ff75d7ee13810f83c9ab1ae96af132dd807eca65be5e214036`
tại `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-payout-admission-20261118/`.
Lượt này chỉ đọc sổ. Không chạy tín hiệu, replay mới hay đọc giá
2024–2026.
