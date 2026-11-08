# Hai giả thuyết phiên vàng: protocol trước kết quả

Thuộc [campaign v2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md), kế tiếp
[mixed monthly trend không đạt](MULTI-ASSET-TREND-RESULTS-20261108.md).
Mục đích: kiểm một nguồn lợi nhuận giá theo phiên, với holding ngắn và phí đầy
đủ trước khi chi công sức thêm SL/sizing/account replay. Không nới phí của R010.

## Cơ sở, nguồn và khác biệt

Đọc ngày 08/11/2026, chỉ dùng mô tả/phương pháp để tự viết code, không nhập
code hoặc phân phối lại dữ liệu/paper:

- [Blose/Gondhalekar/Kort, publisher abstract, 2017/2018](https://link.springer.com/article/10.1007/s12197-017-9403-0):
  báo bất đối xứng day/night trên gold và London Fix. Không đọc được full paper
  qua subscription, không nhận recipe bên dưới là replication của tác giả.
- [Wei, SSRN abstract 7257240, 13/08/2026](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7257240):
  phân tách 00–08 UTC/08–14:30/14:30–24 trên hourly spot 07/2024–08/2026.
  Dùng mô tả indexed của tác giả; mở trực tiếp PDF/page bị 403. Chưa xác minh
  full methods hoặc peer review. Không sử dụng/copy code/data được cấp CC BY-NC.
- [ICE, giờ đấu giá và cách công bố](https://www.ice.com/iba/lbma-precious-metals),
  [LBMA](https://www.lbma.org.uk/prices-and-data/lbma-precious-metal-prices):
  gold auctions bắt đầu 10:30/15:00 London; giá cuối công bố sau khi hoàn tất
  rounds, không phải chắc chắn đúng phút bắt đầu. Dùng clock anchors, không
  lấy auction result tại 10:30 hoặc gọi giá QDM là LBMA benchmark.
- Có thông tin **ngược chiều** ở [GVSU grant abstract 2011](https://scholarworks.gvsu.edu/fsdg/200/)
  so với publisher 2017. Thiếu full methods nên chưa giải quyết khác biệt
  định nghĩa/mẫu hoặc lỗi metadata. Giữ bất định này; literature không là
  ground truth chứng nhận side. Hai sides có controls khóa trước outcome.

R054/R055 khác exact gold H4 indicators, Asia breakout hoặc SELL15–19London
đã gác. Đây là calendar hypotheses mới, không independent evidence từ các
versions đó. Không tự thêm điều kiện/giờ đẹp sau outcome.

## Recipe/data/cost đã khóa

| ID | Primary | Control cùng mask |
|---|---|---|
| R054 | BUY XAUUSD 00:00 → 08:00 UTC cùng weekday | SELL cùng giờ |
| R055 | SELL XAUUSD 10:30 → 15:00 Europe/London cùng weekday | BUY cùng giờ |

- Tất cả weekdays 01/01/2010–31/12/2024, không holiday filter hồi tố. Mỗi
  candidate/ngày đều có row, kể cả thiếu; timestamp dùng UTC milliseconds,
  London dùng IANA DST, không offset cố định. 2025+ đóng. Source đã consumed
  trong gold screens; không gọi đây là clean OOS. Hai probes cũng không
  independent của cả chiến dịch chọn lựa trước.
- Input: exact existing QDM UTC M1 Bid export `metal-discovery9-preparation`,
  SHA `d209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9`,
  5.399.878 rows 11/2009–12/2024. Giữ raw bất biến. Chỉ lấy Open của exact
  minute tại entry/exit; thiếu không nearest/carry-forward/zero. Timestamp
  là interval M1 `[target,target+60s)`, không actual tick fill. Strategy side
  định trước giờ vào, không dùng future close để quyết định entry.
- Tách source observations khỏi economics: Bid thật từ CSV; Ask source vẫn
  null. Trong cost scenario mới đặt Ask=Bid+0,50(reference)/1,00(stress),
  contract100, 2,50USD/lot/side, slippage0,10/0,20price mỗi side. Mỗi phép
  đo dùng continuous 1ounce =0,01lot chỉ làm đơn vị đo, không là budget owner.
  Reuse shared `calculate_round_trip_cost`, net round2USD; không double spread.
- Các windows không qua declared 22UTC rollover; financing=0 vì không có
  event trong holding interval, không xóa financing của một lệnh qua đêm.
  Giá/rollover/commission chưa là current hoặc historical target-firm contract.
  Không SL/TP/margin/lotstep/account/prop equity. Không tạo position cuối mẫu;
  missing exit là unresolved price observation, không giả đã đóng broker.

## Tiêu chí trước kết quả

Với **mỗi primary riêng**, đủ để ưu tiên đăng ký risk wrapper khi stress sum
>0, ≥10/15 năm stress dương, cả năm block 2010–12/13–15/16–18/19–21/22–24
stress sum>0 và mỗi năm ≥200 resolved weekdays. Không đạt thì giữ negative
component, không loại toàn bộ family hay chọn opposite control thành winner.
Heuristic này chưa là edge hoặc xác suất pass; cần native risk/cost/OOS riêng.

Báo mỗi recipe/view/year/cost: planned/resolved/unresolved, gross/net sum,
mean/win/loss, min/max và top5positive share; five blocks, no-trade=0 và
opposite identity. Hai candidates × primary/control × hai cost scenarios;
không cộng chúng thành portfolio hoặc gắn denominator10k vào per-ounce sum.
Không grid, ML hoặc threshold tuning.

## Run, kiểm và lưu

Focused fixtures trước số thật: UTC/London DST, weekend/holdout bounds,
exact/missing endpoints, source Ask không bịa, BUY/SELL tính tay/spread,
control identity và census. Một writer/root mới, deadline120s, PID/status/
events/failure/CANCEL; pin protocol/code/runtime/source metadata và raw SHA.

Source pass hash toàn raw, kiểm order/date bounds/census, sparse parse các
target Open theo price grid. Không đọc lại toàn OHLC chỉ để tính return;
input đã qua prior OHLC validation nhưng provenance không thay endpoint check.
Independent implementation trong cùng agent dùng CSV reader khác lấy lại
**mọi selected Open**, Fraction cost và calendar offsets để so rows/summaries;
không import producer signal/cost cho phần đối chiếu. Kiểm mutation source
price, missing row, wrong net, invented Ask, false authority.

Đóng lượt ghi all negatives/delta/timing; không cần skill/service/engine mới.
Nếu giữ được candidate: freeze wrapper/sizing/invalidation/SL và data path
trước account replay; không mở holdout/broker hoặc mua challenge từ probe.
