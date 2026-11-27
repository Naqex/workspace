# G1 correction: full-year consumer đã đọc nhầm pilot quarters

Separate raw/Fraction economic reviewer dừng `signal_confirmation_state` trong
attempt `index-paperwindow-components-v2`, trước công nhận kết quả. US500 có
124/126 planned thay vì inherited247/250: không là hành vi strategy đã đăng ký.

Root cause tái hiện từ source reviewer: loader US500 hard-code `[1,3]` từ pilot
Jan/Jul, được mang sang full-year review. Q2/Q4 không load nên late predictor
bị đánh dấu canonical absent; 37.016 side-minutes bị gọi nhầm coverage extension.
Tick intake/native/integer field checks/quote locators không đổi; NASDAQ loader
đã đọc full-year và không có lỗi quarter này. Economic raw reviewer tự chọn
quotes và xác nhận late price từ raw nên phát hiện missing-signal mask.

**Invalidated phạm vi US500 và full-batch verdict của attempt đó.** Giữ nguyên
source reviewv1, economic rows/summary/result/review-failure và mọi pins;
NASDAQ outcomes chưa được full review công nhận trong attempt bị dừng. Không
đổi parent negatives, rule, clock, delay, expiry, phí, target hoặc holdout.

## Cách sửa được khóa trước affected rerun

1. Full-year source loader phải nhận proofhash/year/side, yêu cầu đủ4quarters và
   8side output seals; bind từng canonical file vào existing frozen proof/receipt,
   kiểm census/clock/duplicate/year. Không dùng file tồn tại làm admission hoặc
   im lặng lọc quarter thiếu. Test missing/duplicate/tamper/wrongscope trước use.
2. Source reviewv2 output mới, reuse exact1.996raw/native seals và mọi tick-field/
   locator checks đúng. Recompute **chỉ US500 Q2/Q4 canonical comparison/late
   confirmation**, giữ unaffected reports bytes exact. Full-year canonical load
   bằng helper có quarter guard; source1 vẫn frozen và supersession được ghi.
3. Trước PnL: assert fullquarter coverage và late-confirmation coverage theo mỗi
   asset/year, đối chiếu regular-day census; known missing predictor giữ nguyên.
   Gate98% đã có trong economic protocol, kiểm sớm ở source boundary; không nới.
4. Corrected economic attempt mới, same componentv2/protocol/risk/costs; rerun
   affected US500 và kiểm NASDAQ rows/summary exact so attempt cũ nếu có reuse.
   Separate raw-selection/Fraction reviewer toàn corrected outcomes trước verdict.

Không source fetch, original raw/canonical migration hoặc xóa attempt lỗi. Đây
là source-consumer correctness fix, không speedup hay strategy retuning.
Source intake1.996hours vẫn terminal; chỉ cần kiểm lại phần đã sửa, không chờ
thêm một lượt thu dài. Hoàn tất phải báo trước/sau signal census và affected
results, phần invariant/reuse và remaining gaps ngoài C1/C2.
