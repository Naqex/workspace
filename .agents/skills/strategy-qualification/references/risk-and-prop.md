# Risk và prop: giữ đúng nghĩa

Phương pháp, không chứa luật hãng hiện hành hoặc risk budget owner.
Pin rules/terms đúng account/program/phase và ngày hiệu lực.

| Khái niệm | Kiểm gì |
|---|---|
| Drawdown quan sát | Đỉnh→đáy của đúng balance/equity series, coverage/thời gian |
| Giới hạn hãng | Contract threshold, static/trailing, reset/basis/costs; không đồng nhất metric backtest |
| Giới hạn nội bộ | Budget được cấu hình và khoảng đệm; không tự dùng sát ngưỡng hãng |
| Daily / overall | Anchor ngày khác initial/high-water-mark; không reset overall/trial count theo ngày |
| Equity / balance | PnL mở/chi phí theo semantics; balance không đủ cho rule equity |
| Static / trailing | Anchor cố định khác high-water-mark đúng basis/timing/điều kiện ngừng trail |
| Risk mỗi lệnh | Stop-risk + cost/gap assumptions; SL không bảo đảm fill đúng giá |
| Tổng risk account | Positions/pending/reservations/unknown; không chia budget mỗi bot |
| Correlation/exposure | Nhiều ticker/strategy có thể cùng cược một hướng |
| Lợi nhuận owner | Tách simulated capital, payout và mọi phí challenge/retry/subscription |

Rule profile cần version/effective date/provenance, firm/program/phase/size,
loss semantics/timezone, news/holding/SL/EA permissions và target/day/payout.
Thiếu trường liên quan giữ unknown; không dùng default hãng khác.

Source Naqex khi có workspace:

- `projects/trader/foundation_v2/trading_workspace_v2/semantics/prop_profile.py`:
  versioned evaluator/data blockers, không suy hỗ trợ mọi luật.
- `projects/trader/foundation_v2/trading_workspace_v2/forex_pilot_risk.py`:
  pilot limits riêng, chưa là chứng nhận compliance/intrabar đầy đủ.
- `projects/trader/foundation_v2/trading_workspace_v2/risk_promotion_contracts.py`:
  pure reducer/budget không tự là adapter runtime enforce broker.
- `projects/trader/foundation_v2/api-rust/src/automation_grants.rs`: một owner/
  account, durable attempts/reservations; unknown không release chỉ vì timeout.
  Kiểm consumer send boundary, không suy từ struct/config đã enforce.

Mất quote/kết nối xử lý theo contract; không giả đã flat hoặc SL được broker
chấp nhận. Guard không chứng minh edge và không loại mọi loss tail.
