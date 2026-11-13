# Audit phễu B0 — Development, không chạy biến thể

Owner duyệt merge PR71 và giao audit chỉ EURUSD2022–2023; PR71 đã merge
`7d29ce4`. B0 được gác với `CADENCE_OR_SAMPLE_SHORTFALL` +
`DATA_PATH_INCOMPLETE`; news/phiên chưa admit, `PROP_UNMEASURED` giữ riêng.
Không sửa protocol/source/result của lượt B0 đã khóa.

## Scope trước khi đếm

- Đọc đúng per-year details2022/2023 và sealed Bid H1/M15 views của B0.
  Nov–Dec2021 chỉ khởi tạo chỉ báo theo canonical seed đã duyệt, không chẩn đoán,
  không tính cơ hội/PnL warmup. Không đọc EURUSD2024/2025/2026 trong audit.
- Reuse hàm indicators của B0 sau đối chiếu frozen source (ghi hash bytes và
  kiểm trường hợp chỉ khác LF/CRLF). Không gọi simulator, entry/exit/cost engine,
  account replay, alternative signal, markout hoặc backtest mới.
- Saved setup events là nguồn các setup đã được B0 nhận. Từ mỗi setup, đọc tối
  đa4M15 kế tiếp và tái dựng đúng priority: cutoff→missing→bias→touch→trigger→expiry.
  Đối soát tổng/reasons/timestamp với saved counters và intents, không nhận thêm lệnh.

## Mẫu số và cách phân loại

Một zone/ngày có thể có nhiều setup/tín hiệu. Không coi `517−67=450` là số
zone fail trước khi đếm unique days. Xuất cả ba cấp:

1. Zone: phân loại loại trừ nhau theo tầng xa nhất thực tế đã đạt: không setup
   bias-breakout hợp lệ; có setup nhưng không firsttouch; firsttouch không
   confirmation; ít nhất một confirmation. Tổng phải bằng validzones.
2. Với zone không setup: xét geometric breakout tại các barclose08:15–10:45
   theo buffer/ATR gốc; tách không có geometric breakout, chỉ bias neutral/
   unavailable, chỉ opposite bias, hoặc trộn neutral/opposite. Unknown giữ riêng.
   Không gọi ngày chưa có price breakout là ngày fail H1bias.
3. Setup: expiry không chạm/cutoff không chạm/biascancel/gapcancel/
   touchfailed/touchconfirmed. Không đồng nhất no-admitted-touch với “giá chạy
   thẳng”: muốn chứng minh chạy thẳng có lời cần research khác, không được giao.
   Failedtrigger tách close-reclaim fail, candle-body fail và cả hai.

Ngày có nhiều lý do giữ đủ event list; nhãn tầng xa nhất là phân loại mô tả,
không giả mọi zone chỉ bị một filter độc lập gây ra.

## 43 cost rejects

Chỉ đọc SL/spread/lot đã lưu của intents bị `friction_cap_rejected`.
Với d=SLdistance theo đơn vị0,00001 và s=entryspread cùng đơn vị:

`lot_steps=floor(15000/(d+10))`; native1grid reserve+9USD/lot fees.
`F_cents=lot_steps×(s+9)≤1800` tương ứng12% của150USD.
Tính ngưỡng d tối thiểu từ bất đẳng thức và lotfloor, báo range/median theo
entryspread; không có một pipfloor chung. Đây là toán threshold tại quote đã
lưu, **không nới SL thật, không thay admission hoặc chạy giả định fee0**.

## Go / No-Go và hướng A

Counts chỉ chứng minh lượng cơ hội qua luật gốc, không chứng minh một thay đổi
tăng đồng thời cadence lẫn net expectancy. No-Go dispatchB1 nếu chưa có bằng
chứng cho cả hai; không suy ra EURUSD không thể có edge. Việc hủy quyền B1 là
khuyến nghị để owner duyệt; không chuyển ngân sách bỏ trống sang biến thể mới.

Nếu đề xuất hướngA, chỉ census XAUUSD M1**2022–2024**07:00–21:00UTC đúng yêu
cầu (đây là scope Gold được phép, khác EURUSD2024 bị khóa cho diagnostic).
Chỉ quality/counts, không Goldsignals/PnL. Expectedgrid mỗi weekday840phút,
giữ ngày trống; đếm missingruns>15phút, tách interior/boundary/whole-day.
Xuất thêm conventionalinterbar-gap>15phút để tránh off-by-one. Chưa có dated
holiday/sessioncalendar thì không gọi mọi phút thiếu là feed outage.

Card Gold chỉ PROPOSAL_PENDING_OWNER_APPROVAL. Currentpublished fees không là
historical account terms; rollover theo account/symbol/date, không hard-code
22UTC. Không chuyển tỷ lệ phí/lợi nhuận multidayR043 sang intraday hoặc cộng
lại swap cũ như khoản lợi nhuận có sẵn.

Lưu input/code hashes, timestamped events/status, per-zone/per-setup details,
threshold proofs, quality-by-day gaps, report/JSON vào output mới. Test mẫu số,
đếm trùng, firsttouch/priority, lotfloor threshold và missingrun15/16phút trước
actual audit. B0 files/raw/failed attempts giữ nguyên; không provider/brokercall.
