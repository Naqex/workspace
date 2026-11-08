# NASDAQ100: nhận phương pháp và kiểm nguồn trước PnL

Thuộc [campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md), tiếp sau
[R019](PRIOR-DAY-RETEST-RESULTS-20261108.md). Đây là source pilot, không trading
simulation hoặc quyền gửi lệnh. Protocol khóa trước download/price inspection.

## Lý do chuyển thị trường, không đổi tên US500

NASDAQ100 là universe equity khác EURUSD và broad US500; tỷ trọng ngành/công
ty khác nên có thể có trend và chi phí tương đối khác. Đây là lý do thử,
không bằng chứng có edge hoặc diversification độc lập. Dự kiến xét một H4
SMA20/80 trend adaptation sau source/cost admission, không grid và chưa đóng
recipe kinh tế. Không sửa các negative versions cũ để nhận là winner.

Nguồn đọc08/11/2026:

- [Nasdaq index](https://www.nasdaq.com/products/global-indexes/nasdaq-100):
  định danh underlying, không dùng marketing performance làm backtest.
- [Library instrument](https://www.dukascopy-node.app/instrument/usatechidxusd)
  và installed metadata1.51.1: `usatechidxusd` / `USATECH.IDX/USD` /
  `USATECH.IDX-USD`, US100Tech Index CFD. H1/M1 từ18/09/2011, ticks từ01/01/2013,
  daily từ07/11/1990. Không dùng daily start để giả có H1 từ1990.
- [Dukascopy historical](https://www.dukascopy.com/swiss/english/marketwatch/historical/):
  existing public provider; không thêm vendor/account/key/package.
- [FTMO zero index commissions](https://ftmo.com/en/blog/zero-commissions-on-indices/)
  xác nhận public index commission0, không chứng nhận historical2019costs hoặc
  US100current account contract. Browser FTMO Symbols lần này timeout rồi
  ERR_CONNECTION_CLOSED; không refresh row values từ search snippets.
- [The5ers specifications](https://the5ers.com/asset-specifications/) yêu cầu
  kiểm latest MT5 specification; text chỉ xuất Forex. Không lấy Forexfee hoặc
  [NQ/MNQ futures multipliers](https://the5ers.com/futures-faqs/trading-instruments/)
  gắn sang indexCFD. Target minlot/step/point/tickvalue/margin/swap/mode/
  rollover/calendar/dividend vẫn unknown trong scope cần thiết.

CFD feed này không là chính chỉ số NDX, QQQ ETF, NQ future, FTMO US100.cash
hoặc The5ers NAS100. Quotes không tự thành target broker fills, total return,
signed order flow hoặc exchange volume. Existing US500 market helper hard-code
US500/lot/financing; không thay instrument string để dùng lại mà không contract.

## Frozen source pilot: hai ngày / hai cash hours

| Fixture dayUTC | H1/M1 | Tick intervalUTC | Ý nghĩa |
|---|---|---|---|
| 02/01/2019 | Cả ngày Bid/Ask | 15:00–16:00 | 10–11 New York mùa đông |
| 01/07/2022 | Cả ngày Bid/Ask | 14:00–15:00 | 10–11 New York mùa hè |

Hai ngày chọn trước giá: đã là calendar development, không 2025+. Native H1
URL tải **toàn tháng January2019/July2022** mỗi side, nên ghi exposure cả tháng,
dù chỉ xuất fixtureday. M1 mỗi side tải source day. Tick request đúng1hour
mỗi fixture, phải kiểm URL count/scope trước gửi. Tổng4H1month sources,
4M1day sources,2tickhour sources; không đổi ngày nếu thiếu/fail hoặc có mismatch.

Reuse `dukascopy_cached_h1.cjs`, `dukascopy_cached_m1.cjs`, native package
BufferFetcher/CacheManager/processData/formatOutput. UTC, ignoreFlats=false,
explicit source timestamps, keep explicit volume0, no padding. Native retry0,
WAF/auth off; helper chỉ bounded transient retries3attempt/request với budget6,
deadline180s, không retry403/429/auth/schema. Request/cache/raw hashes cùng
package/runtime/source pins, one writer/progress/events/CANCEL/failure.

Raw price grid lấy từ **payload multiplier**, không target SYMBOL_POINT hoặc
MT5 trade tick. Không đo observed midpoint high/low bằng mean side extrema.
H1Open có interval `[start,start+1h)`, chưa actual joint tick timestamp;
high/low/close chỉ known sau interval. M1 tương tự. Tick timestamps mới có
actual millisecond order, nhưng vẫn same-provider indicative/research feed,
chưa order fill/size/latency của quỹ.

## Review và tiêu chí nhận nguồn

Driver `prepare-nasdaq-source-pilot-v1.cjs`, reviewer
`check-nasdaq-source-pilot-v1.py` tại private campaign root. Output mới
`execution-v1/nasdaq-source-pilot-v1`; pin protocol/driver/reviewer/helpers/
package và lock trước source calls. Không strategy/model/broker calls.

1. Check seals/config/URL/instrument/side/time/exposure. Reuse canonical candle
   decoder và separate Fraction delta arithmetic, so retained prices/volume
   transformations với raw. Volume native aggregate có round4, phải ghi rõ.
2. Không yêu cầu24H1/1.440M1 giả định thị trường không nghỉ. Retained census
   bằng explicit source timestamps trong scope; missing giữ missing.
3. Aggregate **observed source M1** thành mỗi H1; kiểm OHLC/containment và endpoint
   difference, không silently impute absent minutes. Giá M1/H1 mismatch là
   source fidelity gap, không tự clamp/bỏ ngày hoặc mở PnL.
4. Tick JSON có riêng delta milliseconds/BidAsk/volume: decode khác native,
   kiểm mọi tick order/grid/prices/source binding. Aggregate mỗi observed minute
   và toàn hour, đối chiếu source M1/H1 từng side. Reuse quote-bar oracle cho
   containment/exact checks; same-provider khác transport không nguồn độc lập.
5. Các negative mutations giá, timestamp, source/padding/missing row, false
   joint quote/authority phải bị reject. Source pass chỉ trong fixture, không
   full-history/rawtick/target broker/OOS/edge certificate.

Mọi mismatch giữ đầy đủ deltas, không cố làm reviewer pass bằng nới tolerance
hoặc đổi dates/fields. Kết quả có thể là partial/inconclusive. Chỉ đăng ký
history/economic recipe nếu đã biết representation/fidelity phù hợp câu hỏi.
H4 trend cần causal bar construction và stop/risk/cost/financing riêng; không
coi pilot là qualification. Goal C1/C2 còn active, chưa challenge candidate.
