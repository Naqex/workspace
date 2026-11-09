# Đợt 2 — hai giả thuyết auto tái hiện được

Đăng ký **05/11/2026 trước code/outcome mới**, theo owner giao thực thi các đề
xuất research. [Bằng chứng](PROP-AUTOMATION-AND-STRATEGY-EVIDENCE-20261105.md)
chỉ cung cấp đầu mối, không xác nhận các quy tắc dưới đây có lợi nhuận.
Scope thuộc [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md), kết quả
thuộc [receipt](../checkpoints/ai-integrations-20261031/RECEIPT.md).

## Quy tắc cố định trước kết quả

| ID | Quy tắc |
|---|---|
| `eurusd-h4-pullback20-80-atr14-r025-v1` | SMA20/SMA80 từ nến đóng. Long khi SMA20>SMA80, close trước<=SMA20 trước, close mới>SMA20 mới; short đối xứng. Thoát long khi SMA20<=SMA80, short khi SMA20>=SMA80. Không đảo chiều cùng event. Cần80nến trước tín hiệu để có SMA trước. InitialSL2×WilderATR14 |
| `eurusd-h4-utc-range00-08-atr14-r025-v1` | Range là high/low hai H4bar00:00–04:00 và04:00–08:00 **cùng ngàyUTC**, phải đủ cả hai. Chỉ xét bar bắt đầu08:00 hoặc12:00, dùng close vượt high/low để vào theo hướng phá vỡ. Tối đa một entry signal/ngày, kể cả sau đó không fill/bị risk chặn. Thoát ở close bar16:00 (20:00UTC), hoặc close hợp lệ đầu ngày sau nếu thiếu bar. InitialSL2×WilderATR14 |

Đây là quy tắc tự định nghĩa, không là exact replication của trader được phỏng
vấn. UTC range **không** được gọi London open: giờUTC cố định, không điều chỉnh
DST. Nghiên cứu London/session địa phương cần protocol/version và kiểmDST mới.
Pullback cùng họ trend với SMA/Donchian; không coi là bằng chứng độc lập chỉ vì
khác tên. Không thêm news filter có dữ liệu tương lai hoặc discretionary veto.

Mọi quyết định chỉ sau nến H4 đầy đủ đã đóng, tick fill sau quyết định. Không
bịa nến qua gap; range thiếu thì bỏ cơ hội. Vị thế qua thiếu dữ liệu vẫn chịu
risk/SL core và thoát ở opportunity hợp lệ tiếp theo, không giả đã flat đúng giờ.
Source snapshot cần đủ history/ATR, one-signal/day và position identity để
roundtrip; CLI resume giữa job vẫn chưa được công nhận.

## Dữ liệu, chi phí và kiểm chứng

- Reuse warmupQDM01–31/12/2021, development03–14/01/2022 đã consumed và manifest
  hash từ round1. Không tải lại, không xem2023+, không gọi là OOS.
- Reuse cùng tick Bid/Ask, sizing25USD gồm chi phí, daily100/overall500USD,
  10.000USD giả lập, commission2,50USD/lot/side và reference/stress hiện có.
  Account spec2026 áp lên2022 là counterfactual scenario, không phí lịch sử.
- Không đổi legacy/default runner hoặc ba candidate trước. Hai candidate mới
  opt-in với protocol/hash riêng. Không đổi threshold/giờ/exit/risk sau outcome.
- Focused checks: causal timing, hướng entry/exit, thiếu range/gap/day reset,
  one-entry-per-day, malformed state/roundtrip và đi qua cùng accounting core.
  Kế thừa test core còn nguyên; không gọi OrderCheck/OrderSend/model.
- Chạy hai scenario/candidate để kiểm numerical integration; đối chiếu baseline
  đã lưu thay vì chạy lại chỉ vì UI. Hai tuần không đủ rank edge/prop survival;
  broker/cost/intrabar qualification thiếu thì giữ false/unknown.

## Đối chứng bán tự động và bước sau

Ghi tín hiệu và tạo mẫu decision journal trống có source/protocol/input binding.
Owner cần quyết định nhận/bỏ và lý do **trước** outcome; demo vận hành về sau mới
đánh giá can thiệp người thật. Không auto-fill quyết định hoặc cộng riêng PnL
của trade được chọn để gọi là replay semi-auto: bỏ lệnh làm đổi state/exposure.
Decision journal chỉ là preparation, chưa là comparison đo được hoặc quyền
override risk. Nếu chưa có dữ liệu người thì ghi `not_measured`.

Sau correctness/integration, mở rộng development theo protocol đã đăng ký nếu
cần, rồi freeze và audit consumed/coverage trước validation/holdout. Không chọn
winner hoặc mua challenge từ lượt ngắn này. Rules/account approvalThe5ers phải
kiểm riêng; không dùng FTMO cost/risk rồi gắn nhãn The5ersverified.

## Mở rộng development Q1 — đăng ký trước outcome mới05/11

Owner giao tiếp vận hành/nghiên cứu song song. Mở rộng cùng candidate/cost/risk
sang03/01–31/03/2022 với commonwarmup01–31/12/2021; inputmanifestQ1 đã có,
toàn bộwindow đã consumed bởi baseline trước. Không gọi là OOS hoặc mẫu độc
lập với hai tuần. Không đổi threshold/giờ/exit để sửa kết quả âm/dương vừa thấy.

Cùng batch so5candidate (Donchian/SMA/zscore/pullback/UTCrange), mỗi candidate
reference +stress, input/output riêng và sourcepinchung. C01 cần chạy với
commonwarmup mới để so đồng điều kiện, không coi là bằng chứng độc lập mới.
Mục tiêu tăng sample development và xem cost/risk/exposure, chưa tối ưu/hứa pass.
Controller finite có deadline20phút, log/progress5giây, không retry tự động hoặc
overwrite attempt. Model/broker/validation/holdoutcalls0. Nếu lỗi/timeout, giữ
artifact và trạng thái thật; CLIresume chưa có nên không giả đã phục hồi.

Ghi counts/openposition/netbalance/equity và qualificationgaps; nhiều scenario
hoặc window chồng nhau không làm trial count reset. Recipe tiếp theo vẫn là
freeze/audit trước OOS, và bổ sung coverage/cost evidence trước propqualification.

### Đợt tiếp sau dừng hiệu năng — đăng ký trước outcome

Owner duyệt hoàn thiện runner và chạy hết Q1. Attempt1 giữ nguyên trạng thái
dừng sớm, không resume từ partial checkpoint. Attempt2 dùng parser đã kiểm
output-equivalence và supervisor JobObject có stdin gate; candidate đầu chạy
một mình để đo trọn journey, sau đó tối đa3worker số học song song trên máy
6core. Không có model calls. Job hoàn tất chỉ được reuse sau kiểm dossier,
source/input/protocol/account-cost binding; job lỗi không retry tự động.

Thay deadline20phút chung đã chứng minh không đủ bằng hard ceiling30phút/job
và90phút/batch; đây là trần an toàn, không phải ETA. Bản tin5giây, một writer,
terminal phân biệt verified-completed/nonzero/invalid-artifact/cancel/timeout.
Giữ kết quả job đã xong khi job khác lỗi. Không đổi tín hiệu, sizing, chi phí,
dữ liệu, tiêu chí qualification hoặc đếm thử nghiệm lại; vẫn development đã
consumed. Không mở OOS/holdout, broker hoặc suy lợi nhuận từ runtime pass.

Làm rõ execution trước outcome của4candidate còn lại: supervisor sau probe
phát hiện lỗi merge identity trong progress; giữ Donchian đã verified, batch mới
reuse bằng dossier/hash thay vì mô phỏng lại. Probe mất1165s, khoảng1CPU và68MiB
RAM. Cho4candidate còn lại chạy tối đa4worker trên6core để tránh hai lượt chờ;
hardcap30phút/job và90phút/batch giữ nguyên. Chỉ đổi điều phối/diagnostics,
không sửa candidate hoặc chi phí theo outcome Donchian. Các partial job bị hủy
giữ nguyên, không coi thành kết quả hoặc resume giữa mô phỏng.
