# Kiểm tần suất US500 trước khi đầu tư thêm vào backtest

11/11/2026. Owner đồng ý tiếp sau [batch 27 cấu hình](US500-MULTIFRAME-RESULTS-20261111.md)
và trao đổi về cỡ mẫu. Mục tiêu: xác định tầng nào làm tín hiệu quá thưa, sửa
thứ tự nghiên cứu để kiểm tần suất trước mô phỏng tài chính lớn. Không coi nhiều
lệnh là edge, không ép bot vào lệnh hoặc thay risk để đạt chỉ tiêu.

## Phạm vi khóa trước số đếm mới

- Chỉ 2022–2024 exposed development, accepted paired M1/cash calendars và proof
  hashes của parent. Không fetch, broker, model, 2025+ hoặc raw decode mới.
- Dùng saved decisions R098 (A/20–80/k.10) và R120 (A/40–160/k.10) để đối
  chiếu lịch sử, không chọn MA theo PnL. R120 chỉ là ca chẩn đoán đã có.
- 5 phép đo tín hiệu cố định bên dưới, cùng MA20/80, ATR14 và k=.10. Đây là
  thử nghiệm thiết kế liên quan cùng họ, không 5 edge độc lập. FP01–FP04 phải
  được giữ trong trial history dù không chạy PnL; chưa là account-policy versions.

| Probe | Warmup/eligibility | Setup | Giờ arm New York | Hạn xác nhận |
|---|---|---|---|---|
| FP00 | Parent common161M15 + H1ready | Đóng qua MA nhanh | 10:00–10:45 | min(arm+60m,11:00) |
| FP01 | Đủ MA80 hiện tại/trước, không cần H1 ở lane A | Như FP00 | Như FP00 | Như FP00 |
| FP02 | Như FP01 | Như FP00 | 10:00–14:00 | min(arm+60m,15:00) |
| FP03 | Như FP01 | Chạm hoặc xuyên MA bằng biên nến | 10:00–10:45 | Như FP00 |
| FP04 | Như FP01 | Như FP03 | 10:00–14:00 | min(arm+60m,15:00) |

Lý do trước đo: common warmup cần để so công bằng 27 cấu hình, nhưng một bot A
20/80 không cần H1 hay MA160 không dùng. Restrict đầu phiên là giả thuyết thêm;
pullback theo xu hướng cũng có thể xuất hiện trong phiên cash. Chạm MA bằng
wick là một định nghĩa pullback rõ, ít hẹp hơn bắt buộc close xuyên MA. Các
điều chỉnh này kiểm cơ hội theo cơ chế; không chọn vì subgroup có lời.

BUY: fast>slow ở hai M15 đã đóng, close trước>fast trước. FP00–02 cần close
hiện tại<=fast; FP03–04 chỉ cần low hiện tại<=fast. SELL đối xứng, dùng high.
Đây là reach-or-cross, không bắt buộc close hồi phục hay gán nhãn OB/FVG.
Freeze armhigh/low, ATR và expiry. Confirm ở M15 sau strict beyond L±.10ATR;
M15 direction cancellation trước confirm, final expiry bar vẫn được kiểm.
Một arm attempt/ngày kể cả expiry/cancel; không rearm/position add-on.

Các probe chỉ đếm **confirmed signals**, chưa native fills/trades. Exact
next-minute paired-open availability báo riêng, không chuyển sang fill muộn.
Không SL/PnL/price-path-after-entry/cost optimization. Calendar short day vẫn
không trade; M15 gaps reset readiness và block ngày theo causal prefix. Không
xóa ngày khi thấy dữ liệu thiếu ở tương lai. Không coi 753 phiên đều eligible.

## Đầu ra và kiểm đúng

Đếm riêng scheduled/normal days; arm slots -> short/blocked/missing bar/not
ready/attempt consumed -> trend/previous-side/pullback/ATR -> arm -> confirm/
expiry/cancel. Buckets ở mỗi tầng không chồng lấp và phải reconcile. Ghi cả
bar counts và unique days để không cộng nhiều nến thành nhiều cơ hội độc lập.
Unique days của các reason có thể chồng nhau ở thời điểm khác nhau trong ngày;
chỉ các bar-reason buckets cùng tầng mới được cộng thành arm_slots.
Mỗi attempt giữ closed-bar snapshots, cancellation/threshold events và giờ.

FP00 confirm/arm timestamps/sides phải khớp saved R098 và parent Policy replay
trên cùng prepared snapshots. R120 cũng replay để xác nhận 87arm/15confirm
không do reporter. Các fixture kiểm BUY/SELL/touch/equality, own warmup,
late-session clock, gaps, expiry, one attempt và invariance trước sửa future data.
Source/protocol/test/input pins, snapshots, progress, deadline600s, CANCEL,
O_EXCL writer lock, failure receipt và timers như parent. Không sửa source khi chạy.

## Quyết định được phép từ đợt này

Mốc 50–100 lệnh screening và 200–500 lệnh review là planning heuristic, không
chứng nhận của FTMO hoặc statistical minimum. Tần suất mục tiêu 2–5 lệnh/tuần
là ưu tiên thiết kế của campaign, không quota vào lệnh. Giữ cả ý tưởng thưa;
không kết luận không có edge chỉ vì thiếu mẫu.

**Chỉ FP04 là thiết kế chính định trước cho bước native tiếp theo**; các probe
còn lại giúp giải thích, không chọn bản đông lệnh/lời nhất. Chỉ cân nhắc đăng ký
native financial screen riêng nếu FP04 có >=200 exact-fill-available signals
tổng ba năm và >=50 ở mỗi năm, không lỗi material. Đây là research-priority
floor (có thể vẫn dưới mục tiêu2–5/tuần), không economic pass. Nếu chưa đủ,
dừng batch tài chính mới và báo thiết kế vẫn quá thưa; không nới tiếp tự động.

Nếu được thử native tiếp: phải freeze protocol/code/tests mới trước PnL;
new intraday exit15:30 decision/15:31 fill cần native clock/SL tests. Giữ
declared10k/25USD risk, max1position và costs/reference stress; không tự dùng
noon exit với late entry. Chưa chạy bước này chỉ vì probe có nhiều tín hiệu.
