# V19 — đi vốn, khoảng trống dữ liệu và adapter Free Trial

**Chưa có nâng cấp CPPI hay “miễn nhiễm gap” đủ chứng cứ. Chưa mua Challenge.** Đã hoàn tất các phép đo, giữ cả kết quả âm; adapter chỉ đọc/shadow, chưa gửi lệnh broker.

PR #97/head `014e1eb` đạt 3CI, merge `beaabdd`. V19 đăng ký `f2c7dd8`, khóa lựa chọn Dev/code `9aaaf29` trước kết quả V19 trên 2024–13/10/2026. Nhánh `codex/asymmetric-recovery-and-mt5-v19`; PR #98 để mở. Exact-head CI và downloaded test IDs được đối soát sau push bằng receipt private.

## 1. Vì sao căn bậc hai không thắng?

V16 đã giữ risk cơ sở đến −5% rồi mới giảm; không có bậc giảm cơ sở ở −1% đến −3,5%. Hàm cushion mũ 0,35/0,50 giảm chậm hơn hàm tuyến tính nhưng vẫn giảm risk ở vùng mà V16 chưa giảm. Nó là hàm lõm theo cushion, không phải bảo đảm lồi/bảo toàn vốn tuyệt đối. Lãi tích lũy cũng là equity có thể mất; hai lệnh thua không bảo đảm chỉ mất “tiền nhà”.

Đăng ký tối đa sáu cấu hình. O2 bị loại ngay khi fit: trọng số mean-matched inverse-vol vượt [0,25;2] và tăng variance, không giải bài toán minimum variance toàn cục. Ba cấu hình đầu đi qua 1.752 sổ Dev/kiểm toán toàn bộ; hai O1 không cải thiện hai tiêu chí chính đã khóa. `BASE_GUARD` là bản đối chiếu tiếp, không được đổi tên thành một chiến lược CPPI thành công.

| Bản Dev | Hai vòng — xấu nhất | Thời gian quan sát TB tháng — xấu nhất | Static % | Daily % |
|---|---|---|---|---|
| BASE_GUARD | 0 | 36,51 | 8,3997 | 1,3587 |
| O1_G035 | 0 | 36,51 | 8,3933 | 1,3571 |
| O1_G050 | 0 | 36,51 | 8,3981 | 1,3571 |

Chỉ số thời gian Dev tính cả mốc chưa đạt bằng phần lịch sử còn quan sát được đến cuối 2023; mốc bắt đầu muộn có thời gian quan sát ngắn hơn. Chỉ dùng so cùng các mốc giữa profiles, không coi là thời gian kỳ vọng không bị kiểm duyệt.

O2: weights [2.3370352336521822, 8.094220472649914, 5.063994293720588]; unit-book variance 5.752,56 → 73.633,77. Không nới cap hoặc chọn lại gamma sau Validation.

Self-review phát hiện heuristic trên chưa giải đầy đủ objective minimum variance. Đã đăng ký [correction O2](V19-O2-CONSTRAINT-CORRECTION-20261116.md) ở `2d7bc94`, **sau khi baseline Validation đã exposed**, rồi chỉ fit lại trên Dev. Giữ cả bản sai/ineligible; không gọi correction là một thí nghiệm chưa từng thấy Validation.

Nghiệm covariance có ràng buộc: weights [0.6795318286445249, 0.25, 1.0921851359699877]; variance unit-book 5.752,56 → **3.190,71**, cùng sample mean. 27 active sets là cách giải một bài toán tối ưu lồi ba biến, không phải 27 strategy trials. Đây chưa là mức giảm DD hoặc lợi nhuận thật sau lot grid/account policy.

Ba profile O2 sửa đúng objective đi qua thêm **1752 full Dev ledgers**. Theo gate đã đăng ký, cần thắng hai metric chính và không làm worst DD xấu hơn; nếu chỉ tốt ở variance/payout tie-break thì vẫn giữ incumbent.

| O2 Dev sau correction | Hai vòng — xấu nhất | Thời gian quan sát TB tháng | Static % | Daily % |
|---|---|---|---|---|
| O2 | 0 | 36,51 | 7,9516 | 1,7319 |
| O1_G035_O2 | 0 | 36,51 | 8,3989 | 1,7162 |
| O1_G050_O2 | 0 | 36,51 | 8,3927 | 1,7162 |

O2 promotion gate: **False**; giữ bản `BASE_GUARD`. Không thay profile dựa trên kết quả 2024–2026.

Volatility drag ở đây là xấp xỉ `0,5 × variance` của **fractional daily account returns**, không phải 0,5 lần phương sai R rồi gọi là % vốn. Daily unit-book drag Dev: 0,00012%; đó chưa là mức giảm vốn thực tế của account engine.

## 2. Các lệnh vướng giá thiếu và guard có tác dụng gì?

32/494 lệnh qua 55 gap occurrences; 25 EURUSD/F5, 2 Gold/F3 và 5 Gold/F4. 50 khoảng thiếu 1 phút, 3 khoảng thiếu 2 phút, 2 khoảng thiếu 3 phút. Đóng trong ngày tránh swap/cuối tuần, không tự sửa việc nguồn thiếu vài phút giữa ngày.

Rà source D/E và các tick/M1/HTF exports đã có tìm được **0 quan sát mới trong gap**. Không bịa nến phẳng. M5/M15/H1 không tái tạo thứ tự chạm SL trong phút thiếu; proprietary/unproven archive formats vẫn chưa được chứng nhận.

Guard 30 phút trước entry loại 0 tín hiệu; có 2 timeout requests trên Full. Thoát ở quote đầu tiên sau timeout, không bán hồi tố ở nến cuối trước mất feed. Vẫn còn 32 nhãn source-uncertain. Stress là giả định excursion bất lợi ở vùng chưa biết, không phải chứng minh thị trường thực đã chạm SL hay flat haircut tùy ý.

## 3. Đối chiếu V16 với V19 trên 105 mốc lịch sử

Bảng dưới lấy OLHC; JSON giữ cả OHLC và full oracle của **mọi sổ**. Median chỉ tính cửa sổ hoàn tất; 105 mốc chồng lấn không là 105 bài thi độc lập.

| Bản / dữ liệu / phí | Vòng 1 | Hai vòng | Recent hai vòng | Median tháng | Daily % | Static % | Funded riêng USD |
|---|---|---|---|---|---|---|---|
| V16/PRIMARY/1× | 81 | 71 | 0/33 | 47,08 | 1,9630 | 6,3825 | 6.457,11 |
| V19/PRIMARY/1× | 80 | 71 | 0/33 | 48,06 | 2,0275 | 6,3825 | 6.471,13 |
| V16/PRIMARY/1.5× | 74 | 7 | 0/33 | 87,09 | 1,9248 | 7,7228 | 4.170,00 |
| V19/PRIMARY/1.5× | 74 | 15 | 0/33 | 40,93 | 2,0309 | 7,7228 | 4.184,00 |
| V16/STRICT/1× | 18 | 1 | 0/33 | 18,95 | 1,9628 | 8,3997 | 1.824,95 |
| V19/STRICT/1× | 14 | 0 | 0/33 | — | 1,9858 | 8,3997 | 1.824,95 |

Sổ tham chiếu risk 150 USD/lệnh đo kinh tế tín hiệu; khác account sizing/admission/harvest. R không là % lợi nhuận tài khoản. 2026 kết thúc ngày 13/10, chưa đủ năm.

| Bản / dữ liệu / phí | Net R tham chiếu | Net USD tham chiếu |
|---|---|---|
| V16/PRIMARY/1× | 42,30 | 6.345,52 |
| V16/PRIMARY/1.5× | 28,67 | 4.299,78 |
| V16/STRICT/1× | -5,05 | -757,11 |
| V19/PRIMARY/1× | 42,39 | 6.358,75 |
| V19/PRIMARY/1.5× | 28,75 | 4.313,01 |
| V19/STRICT/1× | -5,05 | -757,11 |

Tăng phí được tính lại trên actual lot/cash/reserve. Paths SL/P1 giữ nguyên; không giả vờ đã tái tạo mọi first crossing khi spread giãn. Không có modeled breach không chứng minh rủi ro ngoài thị trường bằng 0.

## 4. 5.000 chuỗi đường lệnh, không xáo PnL cuối ngày

Cùng seed/draws V18, mọi sleeve trong quý đi cùng nhau, giữ ordered excursions và account state/clock xuyên seams. 36 tháng, báo prefix 12/18/24; cả hai ordering, 3 cost/source cases cho từng V16/V19. **120.000 sổ Monte Carlo đều qua native cash bridge và full independent ledger/path oracle**; không chỉ lấy mẫu. Oracle cùng tác giả và feed, không phải reviewer độc lập.

| Bản / dữ liệu / phí (OLHC) | Hai vòng 12/18/24/36 % | Median khi đậu, tháng | Funded riêng: mean payout/năm USD |
|---|---|---|---|
| V16/PRIMARY/1× | 1,24/6,08/14,32/33,36 | 25,90 | 946,37 |
| V19/PRIMARY/1× | 1,38/6,20/14,50/33,56 | 25,88 | 946,41 |
| V16/PRIMARY/1.5× | 0,78/3,48/8,54/21,70 | 26,18 | 773,47 |
| V19/PRIMARY/1.5× | 0,86/3,64/8,86/21,98 | 26,02 | 773,32 |
| V16/STRICT/1× | 0,06/0,40/1,48/4,54 | 28,15 | 424,38 |
| V19/STRICT/1× | 0,08/0,52/1,56/4,58 | 28,05 | 424,38 |

Cột payout dùng một sổ **đã Funded ngay từ đầu** chạy song song; không phải thu nhập sau thời gian thi. Tiền rút sau khi thực sự vượt hai vòng được đo riêng trong thí nghiệm state ở mục 5. Đây là tần suất resampling lịch sử đã exposed, không là xác suất tương lai đã hiệu chỉnh. Payout là mô phỏng, gồm cả các đường 0 USD và chưa trừ phí mua/retry/thuế/vận hành. **Payout thực nhận = 0; lệnh broker đã gửi = 0.**

## 5. Bản đồ hồi vốn và chi phí cơ hội

Từ −5% vốn, cần +5,26% trên equity hiện tại để về bờ, hoặc +300% của **đệm còn 5%** để đạt target vòng 1 +10%. Hai mẫu số này khác nhau. Bảng dùng 256 common Dev-only paths/state trong 36 tháng; không chọn lại policy. Mỗi state giả định đang flat ở vòng 1, chưa có ngày giao dịch hợp lệ trước đó và anchor ngày bằng balance giả định lúc bắt đầu. Không chỉ nhìn equity rồi suy đây là dự báo đầy đủ cho một account thật đang có vị thế/lỗ trong ngày. Nhóm không đạt vẫn giữ trong mẫu và chi phí thời gian hạn chế ở 36 tháng.

| V19 state % | Buffer còn % | ROI buffer tới +10% % | Về bờ % | Median về bờ nếu đạt | Hai vòng % | Median đậu nếu đạt | Payout/tháng USD |
|---|---|---|---|---|---|---|---|
| 8 | 18 | 11,11 | 100,00 | 0,00 | 65,23 | 18,36 | 21,28 |
| 5 | 15 | 33,33 | 100,00 | 0,00 | 49,22 | 23,45 | 14,06 |
| 2 | 12 | 66,67 | 100,00 | 0,00 | 29,69 | 26,30 | 6,76 |
| 0 | 10 | 100,00 | 100,00 | 0,00 | 21,48 | 27,46 | 4,23 |
| -2 | 8 | 150,00 | 89,45 | 3,97 | 13,28 | 30,75 | 2,15 |
| -4 | 6 | 233,33 | 69,92 | 11,76 | 6,25 | 30,47 | 0,69 |
| -6 | 4 | 400,00 | 40,23 | 20,30 | 2,34 | 30,68 | 0,16 |
| -8 | 2 | 900,00 | 4,30 | 29,04 | 0,00 | — | 0,00 |

Payout/tháng dùng tiền mô phỏng thực sự rút **sau khi qua hai vòng**, chia toàn bộ 36 tháng và gồm zeros; không lấy thu nhập sổ Funded riêng gán cho tài khoản đang thi. Lượt đo bổ sung giữ nguyên mọi first-passage outcome và đối soát full ledger. JSON giữ bảng V16 bên cạnh, conditional mean, restricted mean và số không đạt.

Drag tham chiếu dưới đây dùng cùng phương sai USD/ngày của unit book risk cố định 150 USD, chia equity giả định từng state rồi lấy `0,5 × variance × 252`. Đây là phép đổi mẫu số để so quy mô; chưa đo drag của actual adaptive account tại từng state và không đưa các con số này vào chọn policy.

| State % | Drag log/năm tham chiếu % |
|---|---|
| 8 | 0,02486 |
| 5 | 0,02630 |
| 2 | 0,02787 |
| 0 | 0,02899 |
| -2 | 0,03019 |
| -4 | 0,03146 |
| -6 | 0,03281 |
| -8 | 0,03425 |

**O3 chưa xác định được ngưỡng reset tối ưu.** Không suy thời gian kỳ vọng vô hạn từ median của nhóm thắng, không coi restricted mean là expected time thật. Phí retry/điều kiện reset chưa biết; nhận định mua lại giúp nhanh hơn chưa có cơ sở. Không reset tài khoản, bỏ chuỗi thua hoặc mua Challenge trong V19.

## 6. Adapter, tốc độ và lưu trữ

[Adapter/runbook](FTMO-FREE-TRIAL-ADAPTER-V19-20261116.md): READ_ONLY mặc định hoặc SHADOW_PAPER, demo binding, raw spec/spread, Prague reset, news/session/stale guards, native V16 signals và frozen V19 sizing, expected-vs-external-fill logger. CLI/file bridge/native-gateway giả lập và 6 full-seed signal prefixes đã kiểm. SDK chưa có trong runtime kiểm thử; chưa attach MT5 thật. Native shadow cần seed, spec/lịch tin được xác minh; chưa là EA hoặc broker parity acceptance.

Full suite: **1216 PASS / 0 skip**, giữ đủ **1.153 V18 IDs**. Wall **15,580 giây**, target <22s: **đạt**. Bốn runtime groups chạy chồng có kiểm soát; không gọi là cùng workload nhanh hơn toàn máy.

Smoke cùng 78 IDs/assertions, 10 fresh processes và startup: **7/10 dưới 0,78s**, max **0,827s**, median **0,760s**. Target 10/10 dưới 0,78s: **chưa đạt**. Giữ mọi outliers; không retry lấy chuỗi đẹp. Profile và paired diagnostics được giữ; không chứng minh chính xác nguyên nhân ba lần chậm lịch sử chỉ từ timing V18.

Timing V18 cho thấy ba lần chậm hơn nhóm còn lại trung bình 80,2ms: 23,7ms ở import, 40,6ms ở phần thân test và 15,2ms ngoài suite. Dữ liệu cũ không có GC/syscall trace để quy toàn bộ chênh lệch cho một module hoặc disk I/O. Không đổi metric sang internal suite time để bỏ chi phí khởi động Python.

Tối ưu đã kiểm: bỏ thăm AST expression khi chỉ tìm ImportFrom (đối chiếu cùng các nested imports), bỏ sys.path trùng sau module loading; giữ oracle checking/fixture assertions. Hai worker smoke không thắng rõ nên không dùng. Oracle single-point bỏ NumPy array một phần tử sau 16 full-ledger parity checks; không bỏ quote/reset/exit clocks.

| Kho | Hiện tại GiB | Delta so V18 GiB | Delta files | Lỗi đọc |
|---|---|---|---|---|
| D | 197,23 | 0,002 | 166 | 2 |
| E | 216,53 | 1,523 | 512 | 0 |

Job V19 giữ **1,523GiB / 496 files**, chủ yếu JSON account/path packs và NPY quote arrays. Đây là evidence được giữ có chủ đích, gần toàn bộ mức tăng quan sát trên E. Không xóa dữ liệu mới hoặc chứng nhận toàn ổ không có rác. Snapshot logical/non-atomic không là physical freed bytes; hai lỗi đọc D thuộc VI Dubber và giữ nguyên.

## 7. Chốt bước tiếp

**Giữ research-only; chưa mua Challenge hoặc tự gửi lệnh Free Trial.** Ưu tiên thu dữ liệu đích có binding và kiểm continuity/spec/news cùng seed, rồi mới đánh giá execution gap. Không dùng sizing để biến nguồn thiếu hoặc alpha yếu thành đã qualified.

Đã đọc lại được các trang FTMO công khai về 2-Step, daily/static loss, giữ lệnh và tin; giữ riêng receipt mới và các lần TLS timeout cũ. Client Area, specification/phí/lịch tin của account đích vẫn chưa xác minh. Free Trial 14 ngày có mục tiêu riêng; mô phỏng hai vòng trong báo cáo không là kết quả Free Trial. MQL5 SDK docs đã lưu HTML/hash; API documentation không thay runtime verification. Giữ VI WIP, Trader pin và mọi nguồn/freezes/failed attempts. PR #98 mở, không merge tự động.

JSON: [ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json](ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json). Private job: `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\asymmetric-recovery-and-mt5-v19-20261116`. `ci-exact-head-reconciliation.json` và `completion-receipt.json` được ghi sau 3 CI đúng HEAD/downloaded test IDs; không sửa HEAD chỉ để tự đóng dấu.
