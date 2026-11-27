# V2 — chẩn đoán năm 2024, quét Atlas và giảm rủi ro tài khoản

**Đã hoàn tất chiến dịch; chưa đủ cơ sở để mua Challenge.** Năm 2024 yếu vì SELL mất phần lớn lợi nhuận BUY. Hai cách giảm carry không vượt đủ cổng lựa chọn. Trong 112 cấu hình Atlas, không có nhánh bổ sung đủ điều kiện. Hệ thống cuối giữ A gốc; risk thấp hơn giúp giảm lỗ dưới vốn đầu, đồng thời làm chậm tiến độ thi quỹ.

Đây là kết quả kiểm định offline, không phải cam kết lợi nhuận hoặc quyền giao dịch. `prop_qualified=false`; chưa có trường hợp hoàn tất hai vòng hay nhận payout trong mô phỏng.

Owner task `a2f3990c-8de8-4680-b5e0-87b2dc438462`, ngày 14/11/2026. PR #79 đã merge tại `a42fb9f`; nhánh cũ đã xóa. Giữ nguyên WIP VI Dubber; không gọi broker, model hoặc nhà cung cấp trả phí. Không giải mã giá năm 2025–2026.

## 1. So sánh PR #78 → PR #79 → V2

Mỗi hàng dùng 36 mốc bắt đầu tháng, từ tháng 1/2022 đến tháng 12/2024, kết thúc trước 01/01/2025. Các cửa sổ chồng lấn và có thời gian theo dõi khác nhau; số cửa sổ qua vòng không phải xác suất pass trong tương lai.

| Phiên bản / risk | Phí | Qua vòng 1 | Qua cả hai | Trung vị vòng 1* | Lỗ ngày lớn nhất | Lỗ dưới vốn đầu | Sụt từ đỉnh | Vi phạm | Payout / USD trader |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PR78 / 0.30% fixed | SYM | 0/36 | 0/36 | N/A | 0.799% | 5.271% | 6.653% | 0 | 0 / $0.00 |
| PR78 / 0.40% fixed | SYM | 2/36 | 0/36 | 12.82 tháng | 1.071% | 7.234% | 8.874% | 0 | 0 / $0.00 |
| PR79 | SYM | 8/36 | 0/36 | 11.31 tháng | 1.335% | 9.321% | 12.728% | 0 | 0 / $0.00 |
| V2 | SYM | 2/36 | 0/36 | 12.82 tháng | 1.071% | 6.157% | 8.969% | 0 | 0 / $0.00 |
| PR78 / 0.30% fixed | ASYM | 0/36 | 0/36 | N/A | 0.731% | 4.895% | 6.268% | 0 | 0 / $0.00 |
| PR78 / 0.40% fixed | ASYM | 5/36 | 0/36 | 15.67 tháng | 0.979% | 7.083% | 8.356% | 0 | 0 / $0.00 |
| PR79 | ASYM | 13/36 | 0/36 | 10.64 tháng | 1.221% | 8.899% | 11.849% | 0 | 0 / $0.00 |
| V2 | ASYM | 5/36 | 0/36 | 15.67 tháng | 0.979% | 6.083% | 8.356% | 0 | 0 / $0.00 |

SYM = swap Gold −40/−40; ASYM = proxy −45/−5 USD/lot/rollover. *Trung vị chỉ tính các cửa sổ đã qua vòng 1. Chưa có trung vị hoàn tất hai vòng vì chưa cửa sổ nào đạt. Một tài khoản liên tục từ 01/01/2022 chính là cửa sổ tháng đầu tiên, không phải quan sát độc lập thứ 37.

**Đánh đổi chính:** mức lỗ dưới vốn đầu lớn nhất giảm từ 9,321% xuống 6,157% ở SYM, từ 8,899% xuống 6,083% ở ASYM. Số cửa sổ qua vòng 1 giảm từ 8 xuống 2 ở SYM, từ 13 xuống 5 ở ASYM. Giảm risk không tạo thêm lợi thế tín hiệu. Sụt giảm từ đỉnh vẫn có thể lớn hơn 7%; đó là thước đo khác với lỗ dưới vốn đầu.

## 2. Vì sao 13 tài khoản cũ kẹt ở vòng 2?

| Bắt đầu | Qua vòng 1 | Đỉnh equity vòng 2 | Đỉnh balance vòng 2 | Đỉnh khi đã đóng hết | Còn thiếu đến 5% từ đỉnh flat | Thiếu, R tham chiếu $175 | Balance cuối |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022-01-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2022-02-01 | 2023-10-04 | 4.034% | 3.118% | 3.118% | 1.882 điểm % | 5.378R | $50,887.27 |
| 2022-07-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2022-08-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2022-10-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2022-11-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2022-12-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-01-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-02-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-03-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-07-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-08-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |
| 2023-09-01 | 2023-10-20 | 1.477% | 0.767% | 0.767% | 4.233 điểm % | 12.094R | $49,609.11 |

**13/13 dừng vì hết dữ liệu (`TIME_CENSORED_AT_DATASET_END`); 0/13 vi phạm drawdown.** Lãi equity cao nhất nằm trong khoảng +1,477% đến +4,034%; lãi cao nhất khi đã đóng hết vị thế là +0,767% đến +3,118%. Trường hợp gần nhất vẫn thiếu 1,882 điểm phần trăm, tức khoảng $941,18 hoặc 5,38R tham chiếu $175.

Equity là balance cộng lãi/lỗ đang mở. Balance cao nhất có thể vẫn còn vị thế; chỉ mức khi đã đóng hết mới phù hợp điều kiện pass. Risk thực tế có lúc giảm về $125 nên $175 chỉ là đơn vị quy đổi. Hết dữ liệu chưa chứng minh chiến lược sẽ không bao giờ pass, cũng không chứng minh thêm vài tháng chắc chắn pass. Tập 2025–2026 tiếp tục đóng.

## 3. Năm 2024: BUY kiếm tiền, SELL làm mất phần lớn

Cùng risk danh nghĩa $150/lệnh, 1R = $150. Gross đã trừ spread, chưa trừ commission, slippage và swap.

| Năm | Chiều | Lệnh | Gross R | Commission R | Slippage R | Swap R | Net nếu bỏ financing* | Net R trong mô hình |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | BUY | 54 | +3.388 | 0.119 | 1.869 | -2.433 | +1.400 | -1.033 |
| 2022 | SELL | 49 | +9.189 | 0.115 | 1.837 | -0.303 | +7.237 | +6.934 |
| 2023 | BUY | 57 | +8.766 | 0.179 | 2.600 | -3.129 | +5.987 | +2.858 |
| 2023 | SELL | 50 | +16.635 | 0.164 | 2.437 | -0.431 | +14.035 | +13.604 |
| 2024 | BUY | 61 | +18.920 | 0.153 | 1.867 | -2.211 | +16.900 | +14.689 |
| 2024 | SELL | 37 | -10.662 | 0.091 | 1.141 | -0.149 | -11.895 | -12.044 |

*Bỏ financing chỉ để giải thích phần đóng góp chi phí, không phải kịch bản được dùng để lựa chọn. **BUY 2024 +14,689R; SELL −12,044R.** Swap BUY 2024 là −2,211R, còn nhỏ hơn −3,129R của năm 2023. Vì vậy, giả thuyết “BUY bị carry kéo hỏng năm 2024” không khớp bằng chứng. Không chuyển sang BUY-only dựa trên năm 2024 đã biết.

Con số SELL 2022 khoảng +11,19R ở PR #77 là trước hiệu chỉnh lịch nghỉ. Baseline PR #78/#79 hiện dùng +6,934R; riêng đóng sớm ngày 04/07/2022 đã làm thay đổi khoảng 4,25R. Không trộn hai phiên bản lịch khi so sánh.

## 4. Hai cách giảm carry: giữ A gốc

CA1: BUY đóng lúc 20:30 UTC cùng ngày; SELL giữ quy tắc cũ. CA2: BUY đóng lúc 20:30 UTC thứ Tư nếu lãi ròng thanh lý chưa đạt 1,5R. Cả hai giữ nguyên tín hiệu vào và SL, chỉ thử trên Development 2022–2023.

| Cấu hình | Phí | Net R 2022 / 2023 | Equity DD (R) 2022 / 2023 | Quyết định |
|---|---|---:|---:|---|
| A0 | SYM | +4.050 / +13.795 | 16.617 / 22.177 | Giữ baseline |
| A0 | ASYM | +5.901 / +16.462 | 15.975 / 20.893 | Giữ baseline |
| CA1 | SYM | +2.753 / +3.618 | 14.854 / 17.506 | Không đạt đủ cổng |
| CA1 | ASYM | +4.874 / +6.632 | 14.478 / 16.330 | Không đạt đủ cổng |
| CA2 | SYM | +8.188 / +11.686 | 16.341 / 18.366 | Không đạt đủ cổng |
| CA2 | ASYM | +10.157 / +14.566 | 15.975 / 17.164 | Không đạt đủ cổng |

CA1 xóa được swap BUY bằng cách đóng lệnh thật, nhưng cũng mất phần giá đi tiếp sau 20:30. Net BUY giảm còn khoảng −2,06R / −6,97R ở 2022/2023, kém A gốc. CA2 cải thiện tỷ lệ lợi nhuận/drawdown, nhưng Net R năm 2023 thấp hơn A gốc trong cả hai mô hình phí. CA2 có đánh đổi hữu ích, song không đạt yêu cầu đã khóa: cả Net R và Net R/DD phải tăng ở từng năm, từng mô hình. Không đổi cổng sau kết quả.

Đây là hai lượt thử mới được phê duyệt trong V2, không phải hồi tố sửa kết quả E3 của V1. Mốc quyết định cần quote trong 60 giây; thiếu thì ghi unknown, không lấy nến giờ tiếp theo làm giá khớp.

## 5. Atlas: 112 cấu hình, không có sleeve đủ điều kiện

Danh mục đã đăng ký: 5 tài sản × 12 cấu hình quét rồi quay lại vùng (sweep) = 60; 4 tài sản ngoài Gold × 12 cấu hình phá vùng đi tiếp = 48; Gold có thêm 4 cấu hình BUY momentum. Tổng 112 cấu hình. Mỗi nhóm vùng dùng phiên Á 00:00–06:00 UTC hoặc ngày giao dịch trước; cửa sổ London 08:00–11:00 / New York 13:00–16:00 UTC; giữ đến 20:30 cùng ngày, +24h hoặc +48h có chặn lịch. Không thêm công thức sau khi thấy kết quả.

| Tài sản | Cấu hình | Lượt tín hiệu thô (1) | ASYM dương cả hai năm (2) | Đủ endpoint | Thiếu endpoint | Qua Stage-0 |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | 16 | 2521 | 3 | 16 | 0 | 0 |
| EURUSD | 24 | 3396 | 0 | 24 | 0 | 0 |
| US500 | 24 | 1869 | 6 | 0 | 24 | 0 |
| GBPUSD | 24 | 3891 | 1 | 24 | 0 | 0 |
| AUDUSD | 24 | 3270 | 1 | 20 | 4 | 0 |

**84 cấu hình có đủ endpoint nhưng không vượt toàn bộ cổng; 28 cấu hình còn thiếu endpoint nên chưa kết luận được toàn mẫu.** Không gọi cả 112 cấu hình là thua lỗ kinh tế. (1) 14.947 lượt có trùng tín hiệu giữa các thời gian giữ, không phải 14.947 lệnh độc lập. (2) Mean dương trên phần có giá chỉ là chẩn đoán nếu còn missing. Đủ endpoint cũng chưa chứng minh đủ đường SL.

USDJPY chưa có nguồn H1/M1 liên tục đủ năm được chấp nhận, chỉ có một số ngày Tokyo fixing. Vì vậy USDJPY bị chặn ở mức sẵn sàng dữ liệu, không phải một ứng viên đã đo và thua.

Cổng Stage-0 yêu cầu từng năm có ít nhất 40 tín hiệu, đủ giá/SL hợp lệ, ma sát trung vị/SL trung vị ≤15%, ít nhất 60% tín hiệu tự nhiên đạt ma sát/SL ≤15%; mean markout ròng phải dương và không nhỏ hơn mean ma sát thực thi trong cả hai mô hình phí. Chỉ ứng viên qua Stage-0 mới chạy Natural SL, kiểm tra ≥6R/năm và tương quan lãi/lỗ ngày <0,30 với A_Core. Không có ứng viên qua Stage-0 nên **Stage-1 và correlation là N/A**, không phải correlation bằng 0.

Các trường hợp đáng chú ý, chỉ để giải thích kết quả:

- Gold sweep vùng ngày trước, phiên London, giữ 48h: mean ASYM +3,861 / +4,181 USD/oz, nhưng chỉ 45,1% / 39,3% tín hiệu đạt cổng ma sát/SL. Không được nới SL hoặc lọc mất phần lớn tín hiệu để cứu.
- Gold BUY momentum phiên New York có mean dương cả hai năm, nhưng chỉ 20–32 tín hiệu/năm với impulse và 29–32 với two-bar. Một số năm mean ròng còn nhỏ hơn ma sát. Chưa đủ số mẫu và tần suất đã yêu cầu.
- EURUSD không cấu hình nào dương cả hai năm trong mô hình hiện tại. GBPUSD và AUDUSD mỗi tài sản có một cấu hình mean dương cả hai năm, nhưng biên độ chưa vượt đủ cổng sau phí.

### Nguồn dữ liệu và phí

Gold dùng spread quan sát được, commission 0,0007% notional/side, slippage 0,20 USD/oz/side; swap SYM −40/−40 hoặc ASYM −45/−5 USD/lot/rollover, mốc 22:00 UTC và thứ Tư ×3. FX giữ commission + slippage $5 + $4/lot mỗi vòng và swap bảo thủ −$40/lot/rollover hai chiều; đây là proxy, chưa xác minh swap FTMO thực tế. US500 giữ commission legacy $1/lot/vòng, slippage 0,75 point/side, funding $2/lot/ngày lịch; thiếu mô hình cổ tức đích nên cấu hình qua đêm không được chọn.

Đã rà 693 giờ endpoint Gold, gồm 128 giờ tái dùng và 565 giờ bổ sung; sửa một bản M1 làm việc trước khi tính PnL, giữ nguyên bản gốc. Chặn việc dùng ngày chỉ có 12 nến H1 làm D1 hoàn chỉnh: loại 4 lượt tín hiệu trước Stage-0, không đổi 112 công thức.

Lần chạy nguồn đầu được giữ tại `component-attempt-1/`. Sau đó bổ sung đúng 1.105 giờ endpoint còn thiếu: US500 224, GBPUSD 451, AUDUSD 430. Không đổi tín hiệu, phí hoặc thời gian giữ. Vẫn còn 28 cấu hình thiếu endpoint; không điền giá, loại mẫu hoặc tiếp tục tải để ép vượt cổng. H1/M1 proxy không đồng nghĩa tick khớp lệnh thực; bổ sung tick endpoint không biến toàn bộ đường giá thành tick đã kiểm chứng.

### Độ bất định khi thử nhiều cấu hình

JSON công khai giữ toàn bộ khoảng bootstrap: 50.000 lần lấy mẫu theo khối 5 ngày có tín hiệu, khoảng 95% thông thường và khoảng hiệu chỉnh Bonferroni trên 112 cấu hình cho từng năm/mô hình phí. Đây là chẩn đoán độ bất định; không phải bảo đảm ý nghĩa thống kê cho mọi cách nhìn. Thiếu endpoint thì không xuất khoảng tin cậy toàn mẫu.

| Cấu hình Gold (ASYM) | Năm | Mean USD/oz | Khoảng bootstrap 95% | Khoảng Bonferroni 112* |
|---|---:|---:|---:|---:|
| XAUUSD.SWEEP.PREVDAY.LONDON.48H | 2022 | +3.861 | [-0.471; +8.335] | [-3.507; +11.803] |
| XAUUSD.SWEEP.PREVDAY.LONDON.48H | 2023 | +4.181 | [-1.419; +9.756] | [-5.630; +13.599] |
| XAUUSD.IMPULSE.D1H4.NY.DAY | 2022 | +3.122 | [-4.439; +9.620] | [-9.171; +12.817] |
| XAUUSD.IMPULSE.D1H4.NY.DAY | 2023 | +0.713 | [-2.804; +4.715] | [-4.635; +8.067] |
| XAUUSD.TWOBAR.D1H4.NY.DAY | 2022 | +0.726 | [-3.932; +5.089] | [-7.271; +7.654] |
| XAUUSD.TWOBAR.D1H4.NY.DAY | 2023 | +2.039 | [-0.383; +4.617] | [-2.116; +6.739] |

*Khoảng hiệu chỉnh chỉ áp dụng trong từng năm/mô hình; không là một bảo đảm toàn cục cho cả 448 cách nhìn. Bảng minh họa sau khi đo không được dùng để chọn lại sleeve.

## 6. Risk Policy v2: an toàn hơn, chậm hơn

Vòng 1 và 2 dùng 0,40% ($200/lệnh trên sổ $50.000); funded dùng 0,25%. Khi equity xuống dưới $48.750, risk lệnh mới tối đa 0,30%; dưới $47.750 tối đa 0,18%. Từ vốn đầu đến −2,5% vẫn giữ risk theo phase. Funded không tự tăng từ 0,25% lên 0,30%. Giữ giới hạn 0,25% sau khi lỗ đã thực hiện trong ngày vượt 1,8%, reset theo Prague. Risk phục hồi khi equity phục hồi; không thay size vị thế đang mở.

Cổng dự trữ nội bộ từ chối toàn bộ lệnh mới nếu SL và chi phí dự kiến của các vị thế có thể làm equity chạm $46.500 (−7%). **Cổng này từ chối 0 lệnh trong lần chạy**, nên không được gán mức giảm drawdown quan sát được cho nó. Khác biệt kết quả đến từ risk theo phase thấp hơn và bậc giảm risk; chưa tách đóng góp riêng của từng phần bằng thử nghiệm ablation.

| Phí | Tổng lượt vào trên 36 cửa sổ* | Bị chặn bởi cổng 7% | Số lượt risk $200 / $150 / $125 / $90 |
|---|---:|---:|---|
| SYM | 5667 | 0 | 4154 / 1005 / 0 / 508 |
| ASYM | 5667 | 0 | 4405 / 901 / 0 / 361 |

*Là lượt vào của các tài khoản mô phỏng chồng lấn, không phải số lệnh thị trường độc lập. Risk 0,18% không bảo đảm không cháy: phí, gap, nhiều vị thế và thay đổi risk khiến số R còn chịu được không cố định.

**Điểm cần sửa trước khi dùng cổng dự trữ ngoài nghiên cứu:** helper kế thừa đang dự trữ funding đến thời điểm thoát thực tế đã biết, thay vì hạn giữ lệnh đã biết lúc vào. Đây là lỗi tính nhân quả của cổng, không phải bằng chứng cổng đã sẵn sàng vận hành. Đã đối chiếu lại toàn bộ 11.334 lượt vào bằng hạn giữ lệnh khóa trước, gồm mọi vị thế đang mở: 2.109 phép dự trữ mỗi mô hình thay đổi, nhưng vẫn 0 lệnh bị chặn. Equity dự trữ thấp nhất còn $46.766,78 / $46.809,90, trên $46.500. Vì vậy lỗi này không làm đổi đường lệnh/kết quả quan sát. Không sửa chính sách đã khóa hoặc tuyên bố helper hiện tại là pretrade causal.

### Tài khoản liên tục từ 01/01/2022

| Phí | Phase cuối | Balance cuối phase | Lượt vào | Lỗ ngày lớn nhất | Lỗ dưới vốn đầu |
|---|---:|---:|---:|---:|---:|
| SYM | 1 | $53,794.84 | 308 | 1.071% | 2.592% |
| ASYM | 2 | $48,471.97 | 308 | 0.979% | 5.644% |

Balance là số dư của phase đang chạy; khi qua vòng thi, sổ phase mới bắt đầu lại $50.000. Lợi nhuận vòng thi không phải tiền payout.

Reward proxy giữ quy tắc 30 ngày, đã đóng hết vị thế và lãi đóng ≥$20; trừ 100% lợi nhuận khỏi account, chia trader 80% / firm 20%. Không bơm tiền, tự retry hoặc xóa lỗ bằng reset. Trong dữ liệu chưa có funded case, nên phần funded/reward chỉ được kiểm bằng fixtures. Chưa tính phí mua/retry Challenge và chi phí vận hành; không có payout thật.

## 7. Kinh tế A gốc không thay đổi

| Năm | Phí | Lệnh | Net R ở risk $150, trước = sau | Mean Net R/lệnh | Net R nếu bỏ top 3 lệnh |
|---|---|---:|---:|---:|---:|
| 2022 | SYM | 103 | +4.050 | +0.0393 | -17.142 |
| 2023 | SYM | 107 | +13.795 | +0.1289 | -10.369 |
| 2024 | SYM | 98 | +1.845 | +0.0188 | -11.995 |
| 2022 | ASYM | 103 | +5.901 | +0.0573 | -15.490 |
| 2023 | ASYM | 107 | +16.462 | +0.1538 | -8.052 |
| 2024 | ASYM | 98 | +2.645 | +0.0270 | -11.155 |

A_Core vẫn là A0 và chưa có sleeve, nên các sổ chiến lược risk cố định được tái dùng nguyên trạng từ PR #79. V2 chạy mới phần vòng đời với risk thay đổi trên tick; không gán việc thay size thành cải thiện alpha. Khi risk thay đổi, dùng USD/% tài khoản để so mục tiêu quỹ; tổng R là tổng net/risk đã cấp của từng lệnh.

## 8. Kiểm chứng, quy trình và giới hạn

- 176 tests hồi quy đạt, gồm 16 fixtures V2 về carry, thời điểm nến hoàn tất, ngân sách 112 cấu hình, bậc risk, reserve, lưới giá FX, bootstrap và kiểm tra tác động reserve theo deadline.
- Phase 0: 13 tài khoản vòng 2 và 6 sổ theo chiều khớp phép tính đối chiếu.
- Carry: 840 đường lệnh, 3360 phép đối chiếu chi phí ở risk $90 / $125 / $150 / $200.
- Atlas: 112 cấu hình và 28418 phép đối chiếu chi phí theo đơn vị khớp phép tính phân số chính xác.
- Vòng đời: 72 tài khoản khớp cash, equity, daily loss, drawdown và phase reset bằng một cách hạch toán khác: ghi funding vào cash thay vì giữ trong floating. Có đối chiếu ledger tại từng entry/exit; không reset theo năm mới.
- Cùng một implementer, dùng công thức tính khác. Đây là đối soát số học, không phải review độc lập bởi người/model khác. Không gửi Astra.
- Lỗi thiếu import ở bước freeze nguồn đã dừng trước PnL; không dùng output dang dở làm kết quả tài chính. Các lần nguồn thiếu và bản gốc được giữ; không lấp missing bằng giá tương lai.

### Thời điểm khóa quyết định

Protocol commit `6fcd3f3`, code trước Stage-0 `b3f64ea`, code trước replay Phase 3 `054d371`. Quyết định giữ A0/không sleeve và hash risk đã khóa trong private receipt trước khi chạy Phase 3:

- Freeze: `2026-11-14T14:30:16.270446+00:00`.
- Release Phase 3: `2026-11-14T14:30:16.910947+00:00`.
- Bản công khai nguyên byte: [PROP-ATLAS-V2-DECISION-20261114.json](PROP-ATLAS-V2-DECISION-20261114.json).

**Sai lệch quy trình:** protocol yêu cầu commit decision JSON trước Phase 3; thực tế JSON chỉ được khóa ở private receipt trước replay và được commit khi xuất báo cáo. Protocol/code đã commit trước, nhưng điều đó không thay thế yêu cầu commit quyết định. Không backdate, không sửa lại protocol và không coi receipt riêng là bằng chứng quyết định đã nằm trên Git từ trước. Không có lựa chọn lại core/sleeve/risk sau kết quả Phase 3.

Năm 2024 đã được xem ở các chiến dịch trước và Phase 0, chỉ gọi là Historical Validation. Reader Phase 1/2 chặn năm 2024; năm 2025–2026 không được mở. Không có clean OOS mới trong chiến dịch này.

Có 222 mốc reset Prague riêng biệt khi đang có vị thế; phép đo dùng quote gần nhất, tuổi quote tối đa khoảng 60,42 phút. Các mốc/tuổi quote còn nguyên trong ledger riêng; không coi chúng là fresh quote hoặc lấy kết quả daily loss làm chứng nhận thực thi trên feed FTMO.

Các phần chưa xác minh đủ để vận hành: swap/spec/margin/leverage đích, lịch tin hạn chế lịch sử, calendar/feed và khớp lệnh của tài khoản đích, cổng reserve causal, forward chưa thấy và bàn giao vận hành. CI hoặc dữ liệu nguồn đạt không đồng nghĩa chiến lược đủ điều kiện giao dịch.

Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\prop-atlas-v2-20261114`. Protocol, source admission, các lần freeze, JSON theo cấu hình, bootstrap, bốn bảng parity và 72 ledger giữ đủ định vị/hash. Báo cáo JSON kèm theo công khai toàn bộ 112 kết quả và 448 hàng độ bất định; không upload raw tick/cache.

**Quyết định:** giữ A0 làm benchmark nghiên cứu; chưa dùng cấu hình này để mua Challenge hoặc dựa vào thu nhập chính. Nhánh bổ sung chưa vượt cổng nên chưa có portfolio mới. Nghiên cứu tiếp cần giả thuyết kinh tế mới hoặc giải quyết bất định phí/nguồn có thể làm đổi quyết định. Không mở thêm giờ, nới SL hay tăng risk chỉ để sửa kết quả của 112 cấu hình.

## Phụ lục — toàn bộ 112 cấu hình

Cột nguyên nhân giữ nguyên mã máy để đối chiếu JSON. `CADENCE_LT40`: ít tín hiệu; `DATA_ENDPOINT_INCOMPLETE`: thiếu giá; `MEDIAN_SCALE_GT15` / `SCALE_RETENTION_LT60`: không hợp quy mô phí/SL; `NET_NONPOSITIVE_*`: có năm mean không dương; `NET_LT_FRICTION_*`: mean dương nhưng chưa lớn hơn ma sát; `DIVIDEND_CARRY_TARGET_UNVERIFIED`: chưa xác minh carry/cổ tức của sản phẩm đích. Các nguyên nhân có thể trùng.

| Cấu hình | Tín hiệu 2022/23 | Có giá 2022/23 | Đạt phí/SL 15%, 2022/23 | Mean net ASYM 2022/23* | Nguyên nhân |
|---|---:|---:|---:|---:|---|
| XAUUSD.SWEEP.ASIA.LONDON.DAY | 125/109 | 125/109 | 36.8%/29.4% | -0.790/-0.529 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.ASIA.LONDON.24H | 125/109 | 125/109 | 36.8%/29.4% | -1.618/+0.037 | MEDIAN_SCALE_GT15, NET_LT_FRICTION_ASYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.ASIA.LONDON.48H | 125/109 | 125/109 | 36.8%/29.4% | -2.693/+0.158 | MEDIAN_SCALE_GT15, NET_LT_FRICTION_ASYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.ASIA.NY.DAY | 126/142 | 126/142 | 69.0%/71.8% | -1.837/-0.283 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.SWEEP.ASIA.NY.24H | 126/142 | 126/142 | 69.0%/71.8% | -1.476/-1.515 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.SWEEP.ASIA.NY.48H | 126/142 | 126/142 | 69.0%/71.8% | -2.463/-1.401 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.SWEEP.PREVDAY.LONDON.DAY | 51/56 | 51/56 | 45.1%/39.3% | +4.069/-1.136 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.PREVDAY.LONDON.24H | 51/56 | 51/56 | 45.1%/39.3% | +4.155/-0.297 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.PREVDAY.LONDON.48H | 51/56 | 51/56 | 45.1%/39.3% | +3.861/+4.181 | MEDIAN_SCALE_GT15, SCALE_RETENTION_LT60 |
| XAUUSD.SWEEP.PREVDAY.NY.DAY | 84/80 | 84/80 | 77.4%/80.0% | -1.400/-0.246 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.SWEEP.PREVDAY.NY.24H | 84/80 | 84/80 | 77.4%/80.0% | -2.120/-1.621 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.SWEEP.PREVDAY.NY.48H | 84/80 | 84/80 | 77.4%/80.0% | -2.053/-2.759 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.IMPULSE.D1H4.LONDON.DAY | 17/18 | 17/18 | 58.8%/77.8% | -4.619/-4.177 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| XAUUSD.IMPULSE.D1H4.NY.DAY | 20/32 | 20/32 | 95.0%/93.8% | +3.122/+0.713 | CADENCE_LT40, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT |
| XAUUSD.TWOBAR.D1H4.LONDON.DAY | 23/31 | 23/31 | 73.9%/61.3% | -2.453/-0.732 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| XAUUSD.TWOBAR.D1H4.NY.DAY | 29/32 | 29/32 | 93.1%/81.2% | +0.726/+2.039 | CADENCE_LT40, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT |
| EURUSD.SWEEP.ASIA.LONDON.DAY | 118/129 | 118/129 | 94.9%/96.1% | -1.670/+2.500 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.ASIA.LONDON.24H | 118/129 | 118/129 | 94.9%/96.1% | -12.170/-3.529 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.ASIA.LONDON.48H | 118/129 | 118/129 | 94.9%/96.1% | -5.549/-7.590 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.ASIA.NY.DAY | 104/91 | 104/91 | 99.0%/96.7% | -2.631/+0.845 | NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.ASIA.NY.24H | 104/91 | 104/91 | 99.0%/96.7% | -1.951/-7.532 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.ASIA.NY.48H | 104/91 | 104/91 | 99.0%/96.7% | -8.002/-19.873 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.LONDON.DAY | 66/71 | 66/71 | 98.5%/93.0% | -2.653/-5.808 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.LONDON.24H | 66/71 | 66/71 | 98.5%/93.0% | -5.909/-7.193 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.LONDON.48H | 66/71 | 66/71 | 98.5%/93.0% | -7.105/-4.046 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.NY.DAY | 81/82 | 81/82 | 98.8%/100.0% | -2.804/-0.382 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.NY.24H | 81/82 | 81/82 | 98.8%/100.0% | -12.112/-2.537 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.SWEEP.PREVDAY.NY.48H | 81/82 | 81/82 | 98.8%/100.0% | -7.885/-10.091 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.LONDON.DAY | 56/70 | 56/70 | 100.0%/100.0% | -0.302/-1.339 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.LONDON.24H | 56/70 | 56/70 | 100.0%/100.0% | -2.354/-6.719 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.LONDON.48H | 56/70 | 56/70 | 100.0%/100.0% | -17.079/-11.241 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.NY.DAY | 44/41 | 44/41 | 100.0%/100.0% | -12.743/-1.180 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.NY.24H | 44/41 | 44/41 | 100.0%/100.0% | -26.298/-8.756 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.ASIA.NY.48H | 44/41 | 44/41 | 100.0%/100.0% | -27.720/-16.537 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.LONDON.DAY | 42/40 | 42/40 | 100.0%/100.0% | -4.062/-8.353 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.LONDON.24H | 42/40 | 42/40 | 100.0%/100.0% | -11.279/-17.893 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.LONDON.48H | 42/40 | 42/40 | 100.0%/100.0% | -22.024/-35.378 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.NY.DAY | 45/52 | 45/52 | 100.0%/100.0% | -15.264/-2.669 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.NY.24H | 45/52 | 45/52 | 100.0%/100.0% | -27.591/-15.748 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| EURUSD.CONT.PREVDAY.NY.48H | 45/52 | 45/52 | 100.0%/100.0% | -31.044/-24.356 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| US500.SWEEP.ASIA.LONDON.DAY | 67/5 | 21/1 | 14.9%/0.0% | +13.681/-35.430 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.ASIA.LONDON.24H | 67/5 | 55/4 | 26.9%/0.0% | +11.750/+31.857 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, SCALE_RETENTION_LT60 |
| US500.SWEEP.ASIA.LONDON.48H | 67/5 | 48/3 | 23.9%/0.0% | +7.294/+39.862 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, SCALE_RETENTION_LT60 |
| US500.SWEEP.ASIA.NY.DAY | 79/5 | 19/2 | 15.2%/20.0% | +1.689/+24.566 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.ASIA.NY.24H | 79/5 | 63/5 | 55.7%/60.0% | +3.187/+13.079 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, SCALE_RETENTION_LT60 |
| US500.SWEEP.ASIA.NY.48H | 79/5 | 51/4 | 43.0%/40.0% | +13.712/+14.805 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.LONDON.DAY | 60/45 | 19/14 | 11.7%/0.0% | -16.022/-8.665 | DATA_ENDPOINT_INCOMPLETE, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.LONDON.24H | 60/45 | 48/35 | 30.0%/4.4% | -5.223/-4.532 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.LONDON.48H | 60/45 | 42/31 | 26.7%/4.4% | +1.308/-3.510 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.NY.DAY | 76/91 | 27/31 | 25.0%/17.6% | -17.428/-11.230 | DATA_ENDPOINT_INCOMPLETE, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.NY.24H | 76/91 | 63/77 | 55.3%/27.5% | -8.326/-9.558 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.SWEEP.PREVDAY.NY.48H | 76/91 | 55/64 | 46.1%/24.2% | +2.562/-11.248 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.ASIA.LONDON.DAY | 25/3 | 9/1 | 28.0%/33.3% | -15.975/-43.521 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.ASIA.LONDON.24H | 25/3 | 22/2 | 80.0%/66.7% | -27.593/-13.641 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| US500.CONT.ASIA.LONDON.48H | 25/3 | 18/2 | 64.0%/66.7% | -49.807/-31.027 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| US500.CONT.ASIA.NY.DAY | 40/1 | 12/0 | 30.0%/0.0% | -14.920/N/A | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.ASIA.NY.24H | 40/1 | 31/1 | 77.5%/0.0% | -32.209/-16.660 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.ASIA.NY.48H | 40/1 | 26/1 | 65.0%/0.0% | -21.776/-76.713 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.PREVDAY.LONDON.DAY | 27/2 | 5/0 | 18.5%/0.0% | -13.436/N/A | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.PREVDAY.LONDON.24H | 27/2 | 22/1 | 81.5%/50.0% | -20.639/+25.458 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.PREVDAY.LONDON.48H | 27/2 | 18/0 | 66.7%/0.0% | -63.347/N/A | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.PREVDAY.NY.DAY | 52/45 | 16/16 | 30.8%/35.6% | +8.696/+0.540 | DATA_ENDPOINT_INCOMPLETE, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, SCALE_RETENTION_LT60 |
| US500.CONT.PREVDAY.NY.24H | 52/45 | 46/37 | 88.5%/82.2% | -9.839/-0.574 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| US500.CONT.PREVDAY.NY.48H | 52/45 | 38/31 | 73.1%/68.9% | -23.667/-0.030 | DATA_ENDPOINT_INCOMPLETE, DIVIDEND_CARRY_TARGET_UNVERIFIED, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.LONDON.DAY | 147/153 | 147/153 | 96.6%/94.1% | -4.035/-0.097 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.LONDON.24H | 147/153 | 147/153 | 96.6%/94.1% | -8.135/-2.923 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.LONDON.48H | 147/153 | 147/153 | 96.6%/94.1% | -13.564/-7.791 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.NY.DAY | 120/114 | 120/114 | 98.3%/94.7% | +0.243/-3.251 | NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.NY.24H | 120/114 | 120/114 | 98.3%/94.7% | -16.703/-7.661 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.ASIA.NY.48H | 120/114 | 120/114 | 98.3%/94.7% | -12.976/-17.743 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.LONDON.DAY | 77/73 | 77/73 | 90.9%/91.8% | +3.774/-2.559 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.LONDON.24H | 77/73 | 77/73 | 90.9%/91.8% | -3.406/-0.405 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.LONDON.48H | 77/73 | 77/73 | 90.9%/91.8% | -1.082/-6.975 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.NY.DAY | 80/84 | 80/84 | 100.0%/91.7% | +2.691/+0.583 | NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.NY.24H | 80/84 | 80/84 | 100.0%/91.7% | -14.925/-3.106 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.SWEEP.PREVDAY.NY.48H | 80/84 | 80/84 | 100.0%/91.7% | -29.581/-2.983 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.LONDON.DAY | 73/81 | 73/81 | 100.0%/100.0% | +3.836/-7.311 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.LONDON.24H | 73/81 | 73/81 | 100.0%/100.0% | -7.840/-13.384 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.LONDON.48H | 73/81 | 73/81 | 100.0%/100.0% | -9.799/-20.732 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.NY.DAY | 53/46 | 53/46 | 100.0%/100.0% | -0.915/-3.457 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.NY.24H | 53/46 | 53/46 | 100.0%/100.0% | -9.858/-7.833 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.ASIA.NY.48H | 53/46 | 53/46 | 100.0%/100.0% | -1.547/-22.111 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.LONDON.DAY | 45/55 | 45/55 | 100.0%/100.0% | +10.973/-2.333 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.LONDON.24H | 45/55 | 45/55 | 100.0%/100.0% | -1.051/-12.473 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.LONDON.48H | 45/55 | 45/55 | 100.0%/100.0% | -11.582/-14.865 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.NY.DAY | 47/49 | 47/49 | 100.0%/100.0% | -10.094/-2.696 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.NY.24H | 47/49 | 47/49 | 100.0%/100.0% | -22.460/-8.522 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| GBPUSD.CONT.PREVDAY.NY.48H | 47/49 | 47/49 | 100.0%/100.0% | -26.053/-27.437 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.SWEEP.ASIA.LONDON.DAY | 107/117 | 107/117 | 60.7%/51.3% | -2.249/-2.701 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.ASIA.LONDON.24H | 107/117 | 107/117 | 60.7%/51.3% | -8.816/-6.462 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.ASIA.LONDON.48H | 107/117 | 107/117 | 60.7%/51.3% | -11.025/-10.097 | MEDIAN_SCALE_GT15, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.ASIA.NY.DAY | 113/120 | 112/119 | 77.0%/70.8% | -1.596/-1.354 | DATA_ENDPOINT_INCOMPLETE, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.SWEEP.ASIA.NY.24H | 113/120 | 113/120 | 77.9%/71.7% | -2.993/-8.749 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.SWEEP.ASIA.NY.48H | 113/120 | 113/120 | 77.9%/71.7% | -4.861/-15.902 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.SWEEP.PREVDAY.LONDON.DAY | 58/50 | 58/50 | 81.0%/56.0% | -5.988/-8.336 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.PREVDAY.LONDON.24H | 58/50 | 58/50 | 81.0%/56.0% | -11.269/-14.186 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.PREVDAY.LONDON.48H | 58/50 | 58/50 | 81.0%/56.0% | -16.272/-18.520 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT, SCALE_RETENTION_LT60 |
| AUDUSD.SWEEP.PREVDAY.NY.DAY | 79/67 | 78/66 | 89.9%/79.1% | +4.677/+1.967 | DATA_ENDPOINT_INCOMPLETE, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT |
| AUDUSD.SWEEP.PREVDAY.NY.24H | 79/67 | 79/67 | 91.1%/80.6% | -1.309/-5.709 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.SWEEP.PREVDAY.NY.48H | 79/67 | 79/67 | 91.1%/80.6% | -4.799/-18.222 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.LONDON.DAY | 60/53 | 60/53 | 100.0%/100.0% | -8.467/-6.581 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.LONDON.24H | 60/53 | 60/53 | 100.0%/100.0% | -19.258/-13.902 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.LONDON.48H | 60/53 | 60/53 | 100.0%/100.0% | -28.523/-19.368 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.NY.DAY | 62/51 | 61/51 | 98.4%/100.0% | +0.926/-9.296 | DATA_ENDPOINT_INCOMPLETE, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.NY.24H | 62/51 | 62/51 | 100.0%/100.0% | -7.171/-13.412 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.ASIA.NY.48H | 62/51 | 62/51 | 100.0%/100.0% | -15.021/-21.210 | NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.LONDON.DAY | 39/29 | 39/29 | 100.0%/100.0% | -11.008/+0.328 | CADENCE_LT40, NET_LT_FRICTION_ASYM_FLAT, NET_LT_FRICTION_SYM_FLAT, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.LONDON.24H | 39/29 | 39/29 | 100.0%/100.0% | -27.182/-8.124 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.LONDON.48H | 39/29 | 39/29 | 100.0%/100.0% | -44.172/-10.479 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.NY.DAY | 46/39 | 45/39 | 97.8%/100.0% | -6.131/-3.244 | CADENCE_LT40, DATA_ENDPOINT_INCOMPLETE, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.NY.24H | 46/39 | 46/39 | 100.0%/100.0% | -3.426/-4.751 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |
| AUDUSD.CONT.PREVDAY.NY.48H | 46/39 | 46/39 | 100.0%/100.0% | -7.272/-16.262 | CADENCE_LT40, NET_NONPOSITIVE_ASYM_FLAT, NET_NONPOSITIVE_SYM_FLAT |

*Đơn vị: Gold USD/oz; FX pip; US500 index point. Mean trên nhóm có giá chưa đầy đủ không phải kết quả đủ điều kiện của toàn mẫu. JSON giữ cả kết quả âm, thiếu giá và các cổng không đạt.
