# XAUUSD B0 — kiểm tra quy mô và thời gian giữ, chỉ Development

Owner đã duyệt merge PR #73 (`993db32`), gác B0 và yêu cầu chẩn đoán tiếp.
PR #73 đã merge vào main tại `f1fa995`; nhánh cũ đã xóa local/remote.
Đây là diagnostic theo chỉ thị, **không phải quyền chạy B1**, không đổi hay
ghi đè 67 lệnh B0, không dùng giá 2024 để thiết kế, không đọc 2025–2026.

## Câu hỏi và ngân sách khóa trước kết quả mới

- Chỉ đọc `2022-details.json`, `2023-details.json` của B0 và tick XAUUSD
  2022–2023. Không tải nguyên result/views/candidates chứa giá năm 2024.
- Cohort chính: toàn bộ 813 raw intents, 772 bị loại phí, 38 qua phí và
  37 fills thực. Phân biệt 14 fills có SL trong [6,5;8,0] USD/oz với toàn bộ
  fills. Không chọn thêm vùng SL/giờ/side sau khi biết kết quả.
- Chỉ ba mốc đã có trong câu hỏi: entry + 2h, 18:00 UTC, 20:30 UTC. Mốc cuối
  là cửa sổ quan sát owner yêu cầu, **chưa xác minh là safe close của CFD/CME**.
  Không quét exit time, SL, RR, ATR hoặc sizing. Giữ nguyên entry, side, SL/TP.
- Với 37 fills, đọc tick liên tục từ entry tới 20:30 để đo first passage.
  Cho nhóm 14 fills: (a) biên SL/TP nguyên gốc; (b) benchmark cố định −7,5 / +15
  USD/oz theo hướng tín hiệu, gồm spread tại entry. Giữ SL và TP là competing
  boundaries: báo biên nào chạm trước, số còn chưa chạm ở từng cutoff và gap.
- Markout: toàn bộ raw intents và các cohort cố định tại 2h/18:00/20:30.
  Giá liquidation Bid cho BUY, Ask cho SELL; entry theo đúng B0. Không đóng
  sớm vì SL/TP cho metric định hướng này. Báo gross sau spread và sau phí theo
  mỗi oz; không biến tổng các markout chồng lấn thành portfolio PnL.
  Khoảng bất định cho stress markout của toàn bộ raw signals: bootstrap theo
  cụm ngày, 2.000 lần, seed 20261113, percentile 2,5–97,5%; chỉ giữ phụ thuộc
  trong ngày, chưa xử lý phụ thuộc liên ngày hoặc hiệu chỉnh nhiều lần thử.
- Chẩn đoán giữ đến cutoff của fills: vẫn giữ nguyên SL/TP bảo vệ, chỉ quan
  sát first touch hoặc quote cutoff. Đây là counterfactual per-trade, **không
  chạy lại account, sizing, admission hoặc strategy B1**; trades có thể overlap.
- Không đọc giá sau cutoff đăng ký. Fresh quote tối đa 60s, giữ thứ tự same-ms.
  Missing quote/path >60s phải đánh dấu; không forward-fill hoặc ép thoát.
  Chưa chạm biên tại cutoff là right-censored, không phải SL/TP hoặc lỗi data.
  Median chỉ trên nhóm đã chạm phải ghi rõ mẫu số; median toàn cohort có thể
  chưa xác định. Không ép Kaplan–Meier khi cơ chế censoring phụ thuộc giờ vào.

## Kế toán ma sát và quy mô

- Fills: commission trả thực tế / số ounces; slippage chuẩn 0, stress 0,40
  USD/oz cả vòng. Spread từ quote entry và exit. Benchmark mid-to-mid có
  spread drag = (entry spread + exit spread)/2; tách phần TP limit không nhận
  price improvement để bridge khớp, không gọi đó là spread hoặc phí broker.
- Cổng B0 dùng **entry spread** biết tại intent và commission bound, khác
  realized spread benchmark. Báo cả hai, median của tổng và median từng phần
  (median các phần không mặc nhiên cộng bằng median tổng).
- Tỷ trọng slippage: median của tỷ số từng vòng và tỷ số tổng USD trên cùng
  cohort. Không lấy phần trăm trên net loss. Commission vẫn là giả định đã
  duyệt 0,0007% notional/side, chưa current-account verified.
- SL: tách khoảng close tới extreme nến setup, spread/entry drift và đệm
  0,10 × ATR14 M15. Kiểm công thức, so SL/ATR và range/ATR giữa nhóm loại/nhận;
  độ biến động lớn không tự chứng minh exhaustion hay directional edge âm.
- Không giả SL median của nhóm nhận là sàn phí chung. Giải phương trình
  approximate F/R tại entry, giữ lot floor/reserve; không thử nới SL để vào.

## Thực thi, quyết định và bằng chứng

Reuse native provider/cache/decoder và parent hash; chỉ bổ sung tick-hours
Development còn thiếu. Một writer, deadline 3600s tải / 1800s đo, bounded
retries; không account/provider mới. Giữ raw/cache, fail và protocol/code pins.
Fixtures first passage BUY/SELL, same-ms/gap/censoring/quote deadline và bridge
mid/spread/fees trước run. Self-audit số học/đối soát parent prefix sau run.

Ngưỡng quyết định không lấy một markout đẹp làm edge: xem dấu và độ đều theo
năm, n/unique days/overlap, core economics, cadence và khả năng thực thi.
Nếu dữ liệu không chứng minh direction thì báo **chưa có bằng chứng**, không
bác bỏ toàn bộ họ chiến lược. Chỉ đề xuất một B1 nếu có cơ chế cụ thể giải
quyết đồng thời phễu và horizon; nếu chỉ giữ lâu hơn mà cadence không đổi,
không coi đó là đã giải quyết cả hai. Giữ lịch sử exposure/trial, chưa dispatch.
