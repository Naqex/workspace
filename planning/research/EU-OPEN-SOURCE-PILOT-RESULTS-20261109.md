# EU-open pilot: dữ liệu qua đêm có và khớp raw, chưa tính lợi nhuận

[Protocol](EU-OPEN-SOURCE-PILOT-PROTOCOL-20261109.md) `21006cf` trước source read;
8 ngày đã khóa, bao gồm New Year, Sunday→Monday và hai phía US March DST.
**32 side M1 bars / 192 timestamp-OHLC-volume checks exact**, ba mutations
open/clock/volume reject. Không PnL hoặc full-night-history acceptance.

Entry decision 23:30 ngày trước, exit decision 03:30 ngày ghi nhãn New York;
M1Open proxies 23:31/03:31. Cả tám holding intervals đều đúng bốn giờ theo
UTC, đúng local day/DST. Mỗi endpoint có raw explicit source, không decoder
padding/forwardfill; BidOpen≤AskOpen và OHLC/grid/volume khớp. Raw được tìm theo
đúng UTC day/side trong accepted proof, không chỉ tên file gần nhất.

Full-year reader buộc bốn quarters/eight side seals của 2019/2022 trước lấy
pilot subset. Giữ canonical/proof/calendar/raw/current-helper hashes và declared
scope frozen-source reuse. Source loader khác bản producer cũ không làm old
proof tự thành current-producer validation; raw compare ở đây chỉ 32 bars.

Wall 4,042 s, source/market/model/broker calls đều 0, process terminal 0. Code
đã syntax-compile trước run; one-writer/no-overwrite/deadline 180 s, progress/
events/manifest/result/failure guard. Reuse raw cache/proofs có sẵn, không
fetch lại lịch sử hoặc sửa source. Không có bottleneck mới cần tối ưu thêm.

Private `execution-v1/us500-euopen-source-pilot-v1/` dưới campaign root giữ
config/results/pins; saved script `check-us500-euopen-source-v1.py`. Kết luận
chỉ source admission cho window/date mẫu, không joint tick quote, actual fills,
funding/SL/account/prop/OOS/edge hoặc challenge authority. Chưa native strategy.

Tiếp [economic protocol](US500-EU-OPEN-COMPONENT-PROTOCOL-20261109.md): full
calendar/endpoints trước net, giữ missing/unknown và unit/cost assumptions;
không gọi mọi bar trong năm đã tick-verified từ tám ngày pilot này.
