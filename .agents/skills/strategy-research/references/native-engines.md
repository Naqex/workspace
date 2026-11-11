# Dùng engine upstream trong nghiên cứu

Đọc khi task dùng LEAN, NautilusTrader, Backtesting.py, Backtrader hoặc VectorBT
để triển khai/chạy chiến lược. Không load cho câu hỏi tiến độ hay bài học trading.
Owner có thể chọn full framework; không hạ yêu cầu đó thành chỉ tham khảo mẫu.

[Runtime guide](../../../../tooling/strategy-engines/README.md) giữ vai trò,
commands, pins/locks owner và acceptance. [Source review](../../../../planning/research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md)
giữ file/pin/license và adaptation history. Không nhân registry phiên bản trong
skill; source clone, installed wheel và engine thực sự chạy là ba bằng chứng khác.

## Chọn phạm vi

- Full-engine use: native APIs quản lý data/events/orders/fills/accounting;
  custom code chỉ lo strategy, admitted data adapter và qualification. Không
  chỉ tính bằng incumbent rồi dán tên Nautilus/LEAN lên báo cáo.
- Code/template port: ghi original→adaptation, license/change notice và fixture
  so indicator/signal. Không gọi đây là full-engine adoption.
- Installation/cutover dùng `upstream-integrations` và môi trường riêng; reuse
  runtime đã pin trước tạo venv/pin/framework trùng. Mẫu API2.x không được coi
  tương thích stable1.x. Không chạy installer/example chưa inspect.
- Mỗi study có một engine thực thi, một writer và baseline rõ. Screening rộng
  chạy một lane; kiểm chéo chọn lọc cho shortlist. Owner muốn dùng cả năm không
  tự yêu cầu mỗi trial chạy năm lần hoặc năm broker runtimes cùng lúc.

## Trước kết quả tài chính

1. Tra trial lineage/negatives trước: đổi asset/timeframe/indicator seed vẫn
   là trial liên quan, không cơ hội độc lập mới. Crossover không là pullback;
   Bollinger indicator chưa là chiến lược hoàn chỉnh; demo miễn phí/null risk
   chưa đủ điều kiện prop. Không ưu tiên sample chỉ vì clone được.
2. Freeze bảng source→target: instrument/contract/unit, Bid/Ask/mid, timestamps/
   bar close/DST, warmup/seed/std definition, decision→fill, lot/rounding,
   fees/slippage/funding, stops/gaps, missing data và end-state. Những mục chưa
   khớp giữ unknown; không biến M1 OHLC thành observed tick path.
3. Kiểm bằng native API trên fixture có expected events/fills/fees, long/short,
   no-trade, next-event timing và stop/gap/ambiguity. Common PnL chỉ hữu ích khi
   assumptions đã khớp. Không gọi ba smoke bằng nhau là US500 engine parity.
4. Lưu exact engine/version/lock, source/protocol/input hashes, trace và thời
   gian import/load/simulation/review. Giữ fail/cancel/rejected; không sửa frozen
   baseline để khớp engine mới. Chỉ promote sau admitted development pilot và
   financial/equity review phù hợp; giữ incumbent rollback.

Không tự mở holdout, account/broker, cloud credentials hoặc thay product runtime.
Engine readiness không là edge, target broker support hoặc challenge readiness.
Task chỉ giải thích một mẫu thì không cần cài engine hay chạy batch mới.
