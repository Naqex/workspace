# Hai cách vào theo phá kênh: đã so cùng giờ, chưa thấy lợi thế ổn định

12/11/2026. Theo [protocol](US500-ENTRY-METHOD-COMPARISON-PROTOCOL-20261112.md),
commit trước numeric `ebd050a`. **Đã chạy BR01-common14-v1 và đối chiếu RS02;
chưa ứng viên nào đủ bằng chứng đi challenge.** Không chạy grid ATR/kênh.

## Chính xác đang thử gì?

| Thành phần | Lượt đối chiếu này |
|---|---|
| Cách A, BR01 | Nến M15 đóng vượt kênh + đệm; vào market phút sau |
| Cách B, RS02 | Sau cú phá đó, chờ nến sau chạm vùng đã phá rồi đóng trở lại theo hướng phá; vào market phút sau |
| Kênh | High/low của 20 nến M15 trước nến đang xét; không chứa currentbar |
| Đệm xác nhận phá | 0,10 × ATR14 từ nến đã đóng |
| Vùng chờ thử lại | Quanh mức phá ±0,10 × ATR tại cú phá; level/ATR giữ trong lúc chờ |
| ATR | Wilder chu kỳ14 trên M15, giá trị thay đổi theo biến động; chưa thử period khác |
| Cắt lỗ | 2 × ATR được dùng cho quyết định, có spread/slip/grid/risk checks |
| Giờ nhận cú phá | Cùng 10:00–14:00 New York, inclusive14:00 |
| Chờ hồi | Tối đa60phút, confirmation không sau15:00NY |
| Thoát cuối phiên | Decision15:30/fill15:31NY như parent; stop có thể đóng trước |
| Risk/size/cost | Cap25USD/reset10k, nativeNautilus1.231.0; BidAsk, zero declared commission; slip0,25/0,75point/fill |

“Vào sau phá” không vào intrabar ngay khi chạm biên. “Chờ hồi” cũng không
đặt limit và khớp ngay khi chạm vùng: cần nến xác nhận trở lại. Chưa bắt buộc
filter H1. Kênh20nến là số nến cố định, **giá biên kênh thay đổi theo nến**;
ATR14 là cách tính cố định, **giá trị ATR thay đổi theo giá**. Đệm0,10ATR và
stop2ATR là hai hệ số khác vai trò, không gộp chung thành “thử ATR”.

Muốn đổi số nến kênh, chu kỳ ATR, đệm phá, độ rộng retest hoặc stop là thay
các trục khác nhau. Chưa quét toàn bộ tổ hợp; đang giữ các trục đó để so cách
vào. Các mức đệm owner từng chọn cho study pullback cũ không tự thành grid
đã chạy cho nghiên cứu continuation này.

## Vì sao cần bản đối chiếu mới?

Review16savedbooks cũ0,671s đã xác minh331signals RS02 đều cùng parent
RS01 đầu/ngày, cùngside/frozenATR và trễ15–60phút. Nhưng RS01 cũ nhận cú phá
tới15NY, RS02 chỉ tới14NY. Vì vậy không thể nói so cũ chỉ đổi việc chờ hồi.

BR01 là **một related version mới** của RS01, chỉ giữ firstsignal có clock
≤14NY; không lấy signal sau để bù. Cutoff dựa vào contract RS02, không chọn
theo lãi/lỗ của late trades. Cùng window, risk, exit/cost/data; RS02 không đổi.
2022–2025 đều đã exposed; đây là methodology check sau discovery, không OOS.
RS02/2026 không được mở trong task này.

## Kết quả sau chi phí cao

**Bảng là tổng của các lệnh có đủ M1 trên đường giữ, không phải lợi nhuận
toàn kỳ nếu có unresolved.** Vốn từng năm reset10k, không tài khoản liên tục.

| Năm | A: số lệnh / unresolved | A: phần đủ dữ liệu | B: số lệnh / unresolved | B: phần đủ dữ liệu |
|---|---:|---:|---:|---:|
| 2022 | 165 / 1 | +77,61USD | 89 / 1 | +225,34USD |
| 2023 | 158 / 3 | −297,93USD | 77 / 1 | −401,21USD |
| 2024 | 148 / 1 | −558,94USD | 71 / 0 | −325,89USD |
| 2025 | 153 / 1 | −111,76USD | 94 / 1 | −28,33USD |

Toàn kỳ A có624trades,618known/6unresolved; B331trades,328known/3unresolved.
Không cộng reference+stress thành samples độc lập. B giữ53,04% số entry củaA;
ít lệnh không tự là betteredge. Known subsets stress cộng qua4sổ: A−891,02USD,
B−530,09USD; **không phải exact whole-study PnL**. Known mean mỗi lệnh A−1,44USD,
B−1,62USD, nên tổng lỗ ít hơn chưa chứng minh chất lượng lệnh tốt hơn.

2025known means stress A−0,74/B−0,30USD; reference A+45,21/B+57,93USD trên
known subsets. Tăng phí làm kết quả yếu đi nhưng không tự chứng minh có
grossedge hoặc actualFTMOcost quá cao. Reference/stress có thể đổi lot/stop/
fill; không đơn giản cộng lại khoản phí để hứa performance mới.

Fullnet A vẫnN/A mọi năm, B2022/23/25N/A; chỉ B2024full-known−325,89USD
trong M1model. Phút thiếu chung04/04/2025 11:02NY không được sửa hay bỏ khỏi
verdict. Nhiều nến/ticks có checksum khớp không làm đường thiếu thành known.

## Ghép cùng parent ngày: tránh kết luận sai về retest

Saved-book retrospective review còn tách matched-parent-day khỏi ngày chỉ A
có lệnh. Ví dụ2025stress, trên93ngày cả hai trade đều known: RS01/BR01 vào
sớm cónet+196,74USD, RS02−28,33USD;59ngày chỉ BR01 có knowntrade đóng góp
lỗ. Do vậy nhìn tổng RS02 ít lỗ hơn không đủ nói “đợi hồi giúp vào giá tốt hơn”.
Phần matched này biết sau phiên; **không được vào sớm rồi lọc theo việc tương
lai sẽ có retest**. Không randomization/causalproof; sizing, entry timing và
stop interaction vẫn thuộc recipe. Review retained cohorts, không tạo filter
mới từ các ngày đẹp/xấu hoặc gọi subset có lời là chiến lược deployable.

## Kiểm chứng, thời gian, quyết định

- Native mới:8financial BR01 +4null; reuse8RS02books byte-exact, so mới bằng
  source+signal/input và Fraction/cash/exit checks.20books có seals/reviews.
- Regenerated signals/cadence2022–25 khớp savedparents trước cutoff; mọi
  RS02 có parent nằm trong window mới, cùngside/ATR và later≤60min.
- Cutoff fixtures:13:45/14:00 được giữ,14:15 bị loại, empty và signalidentity
  giữ. Prior derived review phát hiện cả3mutations vềclock/side/ATR, bảo toàn
  fullnetN/A và reconcile knownsubset/matchedsubset arithmetic.
- Null cash10k/flat; nguồn/input/protocol pins cuối lượt khớp,20book/review/
  manifest seals được recheck. Đây là cùng agent/separate arithmetic, không
  independent reviewer/feed hoặc targetbroker/tick verification.
- Wall70,618s,CPU69,531s cho controlled native/reuse review. Saved16book
  comparison0,671s là workload khác, không speedup ratio của cùng simulation.
  Research/code/docs/time chưa đo riêng. Khôngjob nền, broker/modelcalls0.
- Metadata probe đầu dùng Python hệ thống thiếu timezone database trênWindows,
  dừng trước xử lýsignals. Đã chuyển sang engine_runtime/.venv/Scripts/python.exe
  cótzdata, không cài mới hoặc dùng UTC thay NewYork để né lỗi.
- Điểm kỹ thuật đạt trong scope chưa đủedge/G3/prop/forward. Không thay score
  hoặc hạ gate để chọnwinner; không mở2026 hoặc tối ưuATR/channel tự động.

**Quyết định:** chưa chọn A hoặc B cho vận hành. Giữ conclusion retest giảm
cadence nhưng chất lượng không ổn định, currentrecipes chưa có cơ sở mạnh để
đào grid. Nếu kiểm tiếp cần câu hỏi mới có lý do và đăng ký sensitivity từng
trục riêng; dữ liệu đã xem vẫn development. Không suy cảfamily continuation
không có edge, không coi một mứcATR hoặc channel20 đã tối ưu.

Private campaign `execution-v1/us500-entry-common14-v1/` giữ12new+8reusedbooks,
manifest/snapshots/status/events/inputs/timers/reviews/seals và result.
`us500-breakout-retest-comparison-v1/` giữ derived16book review trước common14.
Scripts được copy vào artifacts; không overwrite outputs để chạy lại. Lưu
trials trong catalogue supplement, không sửa lịch sử RS01/RS02 cũ.
