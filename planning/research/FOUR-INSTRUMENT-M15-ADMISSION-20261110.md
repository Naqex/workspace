# Kiểm sâu bốn sản phẩm trước chọn only one M15

Owner giao thực hiện các điểm kiểm đã đề xuất ngày 10/11/2026. Đây là kiểm
điều kiện nghiên cứu và contract, chưa phải screening strategy hoặc challenge.
[Hồ sơ lựa chọn](INSTRUMENT-SELECTION-ONLYONE-20261110.md) giữ nguồn thị trường
và biểu phí; report này giữ protocol, phép đo nhỏ và quyết định tiếp.

## Protocol trước số đo

- Scope EURUSD, USDJPY, USA500.IDX/USD (proxy US500 CFD), XAUUSD. Dữ liệu
  Dukascopy đang dùng, không chứng nhận quote/fills FTMO hoặc quỹ khác.
- Chọn trước bốn ngày: **04/01, 05/04, 05/07, 04/10/2022**, thứ Ba đầu tiên
  của mỗi quý. Không chọn theo lời/lỗ, không loại ngày có tin sau khi thấy giá.
  Đây là fixture bốn ngày, không mẫu đại diện hoặc đủ xếp hạng hiệu quả.
- Tối đa 32 day/side requests: bốn assets × bốn ngày × Bid/Ask; reuse native
  cache nơi có thể, ghi hash và explicit-source provenance. Dùng đúng
  `dukascopy_cached_m1.cjs`/Dukascopy1.51.1 đã có; không cài provider mới.
- Giới hạn 180 giây; dừng tại lỗi transport đầu tiên sau khi giữ phần đã xong,
  không đổi auth/WAF/TLS. Không tự mở rộng lịch sử để kiếm mẫu đẹp.
- Đọc M1 nguồn thật, không decoder padding. Tạo M15 UTC khi đủ cả 15 phút
  của từng side; không lấy H1 chia nhỏ, không lấy trung bình side-high/low
  làm observed-mid extrema. Giữ source bars volume0 nếu được nguồn liệt kê.
- Phiên so đã chọn trước: EURUSD London08:00–10:00, USDJPY Tokyo09:00–11:00,
  US500 NY09:30–11:30, XAUUSD NY08:30–10:30, theo IANA/DST. Đây là cửa sổ
  chẩn đoán, không khẳng định giờ tối ưu hoặc là strategy entry.
- Metrics: số phút/cây M15 đủ, bid-side M15 high-low và range median;
  chênh Ask-open/Bid-open M1 median/p95. Side opens không chắc cùng tick,
  nên chênh này chỉ là **endpoint proxy**, không spread executable.
- Cost/range: dùng spread proxy và published commission quy đổi về price
  units; không coi M15 range là lợi nhuận có thể lấy, stop tối ưu hoặc edge.
  Không tính PnL, winrate, lệnh, risk grid hoặc chọn survivor từ metric này.
- Account USD10k/risk25USD chỉ baseline minh họa. Min lot, lot step, contract,
  stops, margin/conversion phải có nguồn đúng account; thiếu thì giữ unknown,
  không gán default chung cho bốn sản phẩm.
- Không đọc own holdout2025+, gửi lệnh, OrderCheck, khởi động/reconnect MT5.
  Runtime owner đã lưu có API PID8720 nhưng PID này không còn tồn tại lúc
  kiểm read-only; không dùng ready flag lịch sử làm connected hiện tại.

Private evidence dự kiến:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/four-market-m15-fit-v1/`.
Lưu protocol/source hashes, source exports/provenance, progress/events,
result/review và cả lỗi. Verdict chỉ viết sau khi xem bằng chứng.
