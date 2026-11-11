# US500: đối chiếu M15, H1 và M5

11/11/2026. **DRAFT / chưa executable / chưa financial registration hoặc PnL.**
Owner đã đồng ý A/B/C trước, M1 sau; 7 mức đệm giữ nguyên. Đây là phần mở rộng
của [baseline v1](US500-M15-PULLBACK-BASELINE-DRAFT-20261111.md), không sửa file
v1 đã được probe/hash. Hướng chính vẫn US500/pullback/intraday/prop risk thấp.

## Phạm vi owner đã chọn

| Lane | Thiết kế | Phép so sánh |
|---|---|---|
| A | Luật M15 v1, xác nhận vào bằng M15 | Bản đối chiếu |
| B | A + bộ lọc bias H1 tại lúc arm | B−A đo việc thêm H1 |
| C | B nhưng xác nhận bằng nến M5 đã đóng | C−B đo entry clock |

Mỗi lane dùng k=0/0,05/0,10/0,15/0,20/0,25/0,30:21relatedconfigurations,
không21independentedges. Năm/cost/control làm tăng sốbooks, không tăng số
chiến lược độc lập. Chưa mở thêm M1, nhiều loại zone hoặc H1parameter grid.

Owner tự khai đã học H1bias/M15zone/M5hoặcM1entry, nhưng chưa rõ hoặc kết hợp
nhiều cách xác định zone. Không gọi bản này là faithful replication của một
phương pháp manual đã profitable. Zone baseline là [Low,High] nến M15 arm
đã định nghĩa ởv1; high/low confirmation anchors giữ nguyên, không tự coi đây
là supply-demand/OB/FVG đã được chứng minh. Không thêm width/retest parameter.

## Defaults cụ thể do agent chọn cho draft

Những mục sau làm thiết kế đủ rõ để triển khai; chưa phải thông số tối ưu
hoặc hiệu quả đã đo. Không cần thêm một vòng chọn các khác biệt nhỏ trước
coding; material findings phải được ghi thành delta/version trước PnL.

### H1 bias — một định nghĩa duy nhất

- Dựng H1 từ cùng admitted paired M1 cash-session source: các block đầy đủ
  09:30–10:30,10:30–11:30,…,14:30–15:30 America/New_York. Không biến nửa giờ
  15:30–16:00 thành một H1 đầy đủ. M15 vẫn tiêu thụ phần đó như v1.
- SMA20H1 lấy20Bidcloses của H1 đầy đủ, không reset đầu ngày; không tính từ
  H1 đang chạy. BiasBUY nếu closeH1>SMA20H1, SELL nếu<, NEUTRAL nếu bằng.
  Đây là bộ lọc thiên hướng vị trí giá, không chứng nhận một xu hướng chắc chắn.
- B/C xét bias tại lúc M15arm. Chỉ admit nếu bias cùng side; lưu snapshot
  H1close-time/source/value và freeze bias cho setup đó. Không dùng H1 đóng
  sau arm để hồi tố cứu/cancel setup; M15trend cancellation v1 vẫn có hiệu lực.
- Trước10:30 dùng H1 hoàn tất gần nhất của phiên NYSE trước nếu chưa có H1
  phiên hiện tại. Đây là lựa chọn carry-bias rõ ràng, có thể cũ sau overnight
  gap, chưa được xem tốt hơn việc chờ H1 mới. Chỉ nhận phiên hiện tại hoặc
  phiên NYSE liền trước; không carry qua missing expected H1/session.
- Sau một expected H1 thiếu, reset readiness của bộ lọc cho tới đủ20fullH1
  liên tiếp theo calendar; không lấp nến. Phiên nghỉ không tạo expected bar;
  phiên đóng sớm chỉ tạo các fullH1 hợp lệ. Không cần lấy giá tương lai để
  quyết định một H1 đang hình thành có đầy đủ hay không.

### So sánh cùng nền dữ liệu

A comparator trong study mới chỉ bắt đầu khi M15 v1 ready và H1SMA20 ready,
để không nhầm tác động warmup với tác động directionfilter. A vẫn không dùng
giá trị bias để chọn side. Đây là common-eligibility comparator của studyv2,
không sửa v1 hoặc giấu phần dates bị loại; báo readiness/gap/day counts riêng.

Tại một bar-close trùng thời điểm: công bố các bar đã hoàn tất/cập nhật
indicator trước; kiểm M15cancellation/expiry rồi mới xét confirmation. Không
cho M5 vừa kết thúc cùng nến M15arm kích hoạt entry ở chính arm timestamp.
Nếu thiếu M1 đã tới deadline khi flat thì giữ missing/blocked state, không
lấy full-day coverage tương lai để chọn ngày có lãi. Khi đang có vị thế,
missing path vẫn unresolved, không xóa ledger hoặc position.

### M5 entry trong C

- Sau M15arm đã đóng, xét từng M5 đầy đủ từ cùng3M1/BidOHLC, timestamp phải
  lớn hơn arm-time. BUYclose>L+k×A; SELLclose<L−k×A. Equality khôngconfirm.
- L/zone/A đều là snapshot M15arm; ATR/SL không chuyển sang M5. Các kiểm
  hướng M15 chỉ cập nhật khi M15 mới đóng, không đoán M15 chưa đóng từ M5.
- Hạn vẫn60phút sauarm và không quá11:00NY, không đổi thành4M5bars=20phút.
  Entry model vẫn exact next M1Open sau decision60giây và qua risk/cost check.
  Một arm/day và một position nhưv1, không tăng số lần thử vì entry nhỏ hơn.
- SL2×M15ATR, exit theo M15trend hoặc12:00/noon timing, capital/risk/fees/grid/
  source/unknown policy giữ nguyên giữa A/B/C. M1OHLC không là observed ticks;
  cần granularity tốt hơn ở survivor thì là data/execution admission riêng.

## Kiểm chứng trước khi chạy tài chính

1. Native policy A phải khớp các v1fixtures, tách indicator/economic changes
   khỏi việc thêm H1/M5. Dùng Nautilus thật; không chỉ gọi incumbentbook.
2. HTFclock/as-of tests: không dùng09:30–10:30H1 ở10:15; không dùng zone M15
   trước arm close; kiểm partialH1, carry-bias, overnightgap, readiness-reset.
3. Paired fixtures B/C: cùng arm/side/H1 snapshot, chỉ entryclock khác; cùng
   equality/expiry/risk/SL/exit tests. Test M5 và M15 trùng close cancellation
   trướcconfirmation; không cho shorterTF biết futurefullM15.
4. Pin protocol/code/source/calendar/spec, giữ R004 và v1 lineage. Only2022–24
   exposed;2025+reserved. Ghi mọi trial/negative/cancel, không sửa luật sauPnL.

Ví dụ thời gian, chưa phải dữ liệu thị trường: arm10:00; threshold cố định.
NếuM5close10:05vượtthreshold trong khi M15closeđầutiênvượtở10:15, C có thể
decision10:05/model-fill10:06; B decision10:15/model-fill10:16. Không chứng
minh C lời hơn: giá khớp, missed trades, stops và costs còn phải mô phỏng.

Kết quả cần signals→admissions→fills/unknown, paired opportunity IDs, net/R,
equityDD (tách modeled balanceDD), cost/R, days0trade, missed/delayed entries
và timers theo phase. M5 không tự tăng commission nếu giữ tradecount/quantity;
SLngắn hơn là thay đổi strategy riêng. Không biến3lane thành3data độc lập.

Source/load/indicator preparation được reuse; không mặc định M5 tốn3x hoặc
M1tốn15x totalwall. Chưa có benchmark multiTF. Skills hiện có đủ: strategy-
research/native-engines và qualification. Không tạo framework/skill mới,
broker/model call, holdout read hoặc job nền từ việc chốt thiết kế này.

## Điểm tiếp tục

Đã lưu quyết định A/B/C cùng defaults draft. **Tiếp native code và fixtures
causal/clock/orders trước financial batch21configs**, rồi đóng numerical
registration/manifest/census. Catalogue vẫn95records; chưa cấp trialID hoặc
claim economic outcome. Không yêu cầu owner chọn lại các thông số nhỏ đã
được giao agent thiết kế; nếu có material trade-off mới thì báo rõ.

Review nguồn: Gitblob của v1 vẫnSHA256`b25b2f6ad72320a4b91600e64386ee36cbc399f36c1cb095ec3bcfaeb03b7d6e`;
checkout sau merge dùngCRLF nên workingbytesSHA`c2822f185b5f1a0d7b50908fdd47b44471efab3f2150b1f0536867e32a43355b`.
Đã đối chiếu chỉ225newline khác, khôi phục exactGitblob snapshot tại
`.runtime/strategy-engines/pullback-spec-reviewed-v1.md`; giữ receipt/pin cũ,
không sửa/normalize source hoặc dùng thay đổi newline để chứng nhận rerun.
