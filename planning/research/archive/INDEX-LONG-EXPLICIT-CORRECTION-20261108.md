# Sửa nguồn cho long RSI/preclose và kiểm lại monthly admission

Đăng ký trước outcome của lượt sửa. Kế thừa [quarterly source correction](INDEX-EXPLICIT-QUARTERLY-PREFLIGHT-20261108.md)
và [kết quả hiện có](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md). Không chọn lại
chiến lược hoặc thay ngưỡng sau khi đã biết kết quả cũ. C1/C2 chưa hoàn tất.

## Vì sao cần sửa, giữ gì cố định?

Native decoder đã chèn carried-close bars. Sáu noise/firstlast books đã được
sửa; long RSI/preclose/monthly còn giữ expanded-view scenarios. Lượt này sửa
data semantics, không performance optimization hoặc trial tìm tham số mới.

- Tạo paired explicit views2013–2021 từ `us500-long-m1-v6/<year>` và cache raw
  do parent manifest dẫn tới. Năm2022–2024 reuse source views đã kiểm trong
  `us500-explicit-source-v1`, không tái tạo hoặc thay protocol/source pins cũ.
- Reuse codea2a3358: chỉ giữ nến source được liệt kê, giá/volume khớp parent,
  original order, pair intersection và unpaired journals. Giữ raw/old views,
  failures/availability records; thiếu raw hoặc binding không khớp thì dừng.
  Không tải quote mới hoặc khôi phục side bị parent bỏ trong lượt này.
- Source views giữ public data đã consumed; không gọi2013–2024 là cleanOOS.
  Không local2025+, broker/model/networkcalls, tài khoản/provider mới, trả phí.

## Chuẩn bị và kiểm

Hai data workers tối đa, mỗi năm deadline900s, controller3600s. Worker thuộc
Windows Job Object; output mới/lock/CANCEL/status/log/proof/source snapshots.
Worker/reader/source đang pin không bị sửa giữa job. Đối chiếu native decoder
Node trực tiếp trên **raw cache đã có**, network bị chặn; không gọi downloader
theo lịch đầy đủ vì parent V6 có requests unavailable được khai báo. Native
timestamps và Python source timestamps phải khớp, nến được giữ/unpaired phải
khớp toàn giá/volume/order. Same provider/cùng agent, không independent feed
hoặc independent human/model sign-off. Mỗi completed year được giữ nếu năm
khác lỗi; không restart tất cả hoặc thay hashes để reuse.

Reader bắt buộc explicit-source proof hiện có. Kiểm lại bindings2022–2024
trước reuse; source/producer đổi phải attempt mới, không sửa proof cũ.
Thời gian phân prepare/reader/native oracle/reuse/compute/review và unknown;
không cộng CPU/wall hoặc timings chạy chồng nhau thành thời gian end-to-end.

## Lượt numerical sau data gate

1. Exact RSI3+IBS R050 và preclose R052, annual2013–2024, mỗi năm10k/planned25USD,
   cùng legacy commission0,5USD/lot/side, slippage0,25/0,75 và funding1/2USD
   mỗi lot/calendar day. Không dùng commission0 mới để cứu kết quả; giữ nguyên
   entry/exit/SL/clock/lot/minimum/margin/endbook và null control.
2. So observed source inputs và signal plans/clock/fill availability trước.
   Giữ hoặc reuse book cũ **chỉ nếu entire input used + numerical functions +
   environment/cost bindings chứng minh không bị tác động**. Nếu input bị
   ảnh hưởng có thể đổi state sau đó, rerun whole affected annual book ở
   output mới rồi arithmetic/fill/funding/open-mark reviewer. Không xóa vài
   trade rồi sửa PnL. Max một numerical worker, controller1800s.
3. Tiêu chí long review cũ: totalnet dương cảcosts,≥8/12stressyears dương và
   cả4blocks2013–15/2016–18/2019–21/2022–24 stressnet>0. Giữ tất cả failures,
   nofillyears/partial/gaps không làm economic0. Đây là descriptive triage,
   không calibratedprobability, hard rejection cảfamily hoặcchallengeproof.
4. Monthly momentum và always-long benchmark: chạy `prepare` và `input_coverage`
   trên cùng2013warmup/2014–2024evaluation source-only views, giữ đủ13monthends
   và14completecashTR rules. Nếu admissionfail thì không mô phỏng portfolio;
   lưu new input observations/decisions/delta và giữ old numbers với nhãn
   expanded-view/unadmitted. Không xóa năm thiếu để chạy mẫu đẹp. Nếu đạt,
   đăng ký bước numerical continuous riêng trước chạy, không dùng positive
   admission để suy có edge hoặc tự mở holdout.

## Kết quả cần lưu

Source/data/runtime/protocol/hash/version và old/new locators; missing source/
padding/unpaired/coverage; before/afterdecisions/trades/funding/cash/open/gaps,
timings, bug/recovery/reuse và rule/source parity. Cập nhật kết luận cũ bằng
link, không overwrite frozen artifacts. Nhật ký ghi vì sao chọn giữ/bỏ/unknown,
remaining gaps và next action theo workflow. C1 vẫn cần native index/tick/prop,
targetcost và unseen/forward evidence; repair này tự nó không đạt C1 hoặcC2full.
