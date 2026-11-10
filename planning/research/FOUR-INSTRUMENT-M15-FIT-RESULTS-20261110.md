# Bốn sản phẩm M15: đã kiểm mẫu dữ liệu, chưa chốt chiến lược

Thực hiện 10/11/2026 theo [protocol trước số đo](FOUR-INSTRUMENT-M15-ADMISSION-20261110.md),
commit `4c2af3e`. Cả bốn sản phẩm tạo được M15 từ M1 nguồn thật trong mẫu đã
đăng ký. Chưa sản phẩm nào có bot M15 được chứng minh đủ challenge từ lượt này.

## Kết quả đo thực tế trong mẫu nhỏ

Bốn ngày cố định năm 2022, hai giờ/phiên/sản phẩm; **32 nến/sản phẩm, tổng128**.
Đây là 16 asset-days chồng ngày và cùng macro shocks, không 128 lệnh độc lập.
Bid/Ask từ Dukascopy; không phải quote FTMO, không đủ đại diện 2022→nay.

| Sản phẩm, cửa sổ đã đăng ký | M1 Bid/Ask đủ / kỳ vọng | M15 đủ / kỳ vọng | Biên M15 trung vị | Chênh Ask-open/Bid-open trung vị / p95 | Proxy phí / biên M15, trung vị |
|---|---:|---:|---:|---:|---:|
| EURUSD,08–10 London |480/480|32/32|12,55pip|0,40/0,60pip|7,0%|
| USDJPY,09–11 Tokyo |480/480|32/32|8,90pip|0,70/1,10pip|15,6%|
| US500 proxy,09:30–11:30 New York |480/480|32/32|10,433điểm|0,510/0,815điểm|4,5%|
| XAUUSD,08:30–10:30 New York |480/480|32/32|4,2665USD/ounce|0,339/0,424USD/ounce|8,1%|

**Cách đọc:** endpoint của hai side không chắc đồng thời, nên không gọi cột
chênh giá là spread executable. Proxy phí cộng commission công bố hiện nay
vào dữ liệu giá 2022: Forex5USD/100kbase RT, index0, gold0,0007%/side,
commission-equivalent gần flat. Không có slippage/swap trong proxy; không là
tổng phí giao dịch hoàn chỉnh hoặc tái hiện biểu phí từng biết năm2022.
USDJPY quy commissionUSD thành JPY-price bằng giá của từng bar, không dùng
pipEURUSD. Các phiên khác nhau đã chọn trước; đây là so market-session pairs,
không phép cô lập tác động instrument trên cùng session và policy.

Phần trăm là median của từng bar `(endpoint-spread-proxy + commission-price)
/ bid-side-high-low`, không tỷ lệ hai medians. **Biên nến không là lợi nhuận
có thể lấy hết hoặc SL đề xuất.** 4,5% không nghĩa US500 kiếm được95,5% còn
lại hoặc luôn rẻ nhất; không có signal/exit/fill hay account equity trong phép đo.
Tần suất opportunity, winrate, RR, tail probability và expected income chưa đo.

## Cơ hội có lý do tồn tại, và giới hạn của lý do đó

| Sản phẩm | Cơ chế có nguồn đáng kiểm | Bằng chứng project phải giữ | Kết luận cho M15 |
|---|---|---|---|
| EURUSD | Dòng tiền quanh fixing; dealer inventory và khách hàng cần giao dịch theo giờ. BoC2021-48; không vì indicator tự dự báo được | Exact FX breakout/pullback/fixing/round-level versions đã có kết quả không retained; R091 gross dương nhẹ nhưng spread ăn hết | Có câu hỏi kinh tế; chưa có hypothesis M15 mới đủ điều kiện chỉ bằng đổi H1→M15 |
| USDJPY | Nhu cầu thanh toán ngoại tệ của doanh nghiệp Nhật quanh bank fixing; Ito/Yamada NBER22820 và BoC | R084 primary buy không qua stress, R085 post-fix extension không đạt độ bền; không nâng sensitivity/control thành winner | Cơ chế gắn thị trường rõ nhưng recipes đã thử không đạt; không rerun giờ cũ hoặc chọn clock theo kết quả |
| US500 | Mở/đóng cash, thông tin qua đêm và nhu cầu thực hiện lệnh tạo câu hỏi intraday; Gao et al. về SPY first→last30min và calendar NYSE | First→last CFD adaptation2022–24 âm; các index phiên bản khác và source corrections giữ trong catalogue | Đáng ưu tiên thiết kế câu hỏi theo cash session, nhưng không chạy lại recipe cũ hoặc coi SPY/futures paper là proof CFD |
| XAUUSD | Lãi suất thực, inflation expectations, uncertainty/flow; Chicago Fed và WGC | Gold H4 survivor không tự thành Gold M15; R054/R055 exact session recipes không vượt phí | Có macro story, nhưng bằng chứng đã đọc chưa cho exact M15 edge. Không mua theo tin tốt/sóng mạnh mà thiếu measurable rule |

Sources: [BoC](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/),
[Ito/Yamada](https://www.nber.org/papers/w22820),
[Gao et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866),
[NYSE](https://www.nyse.com/trade/hours-calendars),
[Chicago Fed](https://www.chicagofed.org/publications/chicago-fed-letter/2021/464).
Ngày10/11 đọc được Chicago Fed body: annual-average regressions, không M15.
NBER/SSRN web-open403; kế thừa phần full-method đã ghi trong
[Tokyo method](TOKYO-FIX-METHOD-ADMISSION-20261109.md) và
[transfer review](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md), không claim
đọc lại full papers hôm nay. BoC landing text hiện không trả abstract đầy đủ;
không đổi ngày của full-method cũ thành lần kiểm mới.

Lịch sử cụ thể: [FX round-level](FX-ROUND-LEVEL-RESULTS-20261109.md),
[JPY primary](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md),
[JPY extension](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md),
[US500 first-last](US500-CLOSE-MOMENTUM-RESULTS-20261108.md),
[gold sessions](GOLD-SESSION-COMPONENT-RESULTS-20261108.md),
[catalogue](STRATEGY-CATALOGUE-20261107.json).

## Lot, margin và khả năng giữ risk nhỏ

| Sản phẩm | Contract/leverage có bằng chứng | Min lot/step/stop/margin hiện tại | Ý nghĩa |
|---|---|---|---|
| EURUSD | Snapshot FTMO02/11:100kEUR/lot, USD account, leverage30, tick1USD/lot | Min/step0,01lot, max50lot, stopslevel0 ở snapshot; chưa refresh hiện tại | Có thể tính minh họa theo snapshot, không tự thành authority giao dịch |
| USDJPY | Source mapping/pip0,01 đã kiểm; chưa có FTMO row/account packet đủ | Unknown | Không lấy minlot EURUSD hoặc point của Dukascopy thay FTMO |
| US500.cash | Public rendered08/11:contract1, Swing15, commission0 | Target minlot/step/tick-value/stop/dividend mode chưa đủ | Contract1 khác các CFD hoặc futures khác; sizing phải pin đúng spec |
| XAUUSD | Public rendered08/11:100oz/lot, Swing15, fee theo notional | Target minlot/step/point/swapmode/multiplier chưa đủ | Chưa chứng nhận mọi SL đều giữ được risk25USD hoặc cashswap từ points |

Nguồn kế thừa: [FTMO public observation08/11](FTMO-PUBLIC-SYMBOLS-20261108.json),
[symbol/clock admission](FTMO-SYMBOL-AND-CLOCK-ADMISSION-20261108.md),
[Forex pilot§10](FOREX-PROP-PILOT-20261102.md#10-thông-số-ftmo-hiện-tại-và-development-dài-hơn--0211).
Đây là public/snapshot evidence, không xác minh lại account hôm nay. Read-only
runtime inspection: owner API PID8720 không tồn tại, không listener8010 hoặc
terminal64 process; không restart, initialize SDK, reconnect hoặc gửi lệnh.

Ví dụ EURUSD theo snapshot, account10k/risk25USD, entry1,12210 và leverage30;
SL tính từ giá khớp, commission5USD/lot RT, chưa adverse slippage/swap:

| SL minh họa | Lot làm tròn xuống theo step0,01 | Lỗ tại SL + commission | Margin tính theo công thức |
|---|---:|---:|---:|
|5pip|0,45|24,75USD|1.683,15USD|
|10pip|0,23|24,15USD|860,28USD|
|20pip|0,12|24,60USD|448,84USD|

Không đề xuất SL5/10/20; ví dụ cho thấy **SL nhỏ làm lot/margin tăng**, không
đồng nghĩa riskUSD cao hơn. Floor theo step và từ chối nếu dưới minlot;
không làm tròn lên để đạt đủ risk. Nếu có gap/slippage có thể vượt25USD.
Lot quá nhỏ cũng có thể không thực hiện được risk nhỏ ở một stop rộng.
Rủi ro can thiệpJPY, tin Mỹ/gold và gap/open equity giữ khác nhau; bốn ngày
không đủ đo xác suất sự kiện đuôi. Không cho điểm an toàn dựa trên sample này.

## Quyết định và phần thực sự còn thiếu

**Đã hoàn tất kiểm offline có giới hạn cho cả bốn; chưa hoàn tất target-account
acceptance hoặc chứng minh edge.** Không đổi owner choice: chỉ M15 đã chốt.

Agent nghiêng **US500 làm hồ sơ ưu tiên để hoàn thiện và trình owner chọn**:
cash session có mốc rõ, commission0 có nguồn và source fixture M15 dùng được.
Đây là judgement về khả năng đặt câu hỏi/kiểm chứng; không chọn vì riêng4,5%,
không ranking lợi nhuận hay tái khởi động first→last recipe đã gác. EURUSD là
đối chiếu FX; JPY/gold chưa bị loại cả thị trường vì những bản cũ không đạt.

Trước khi đăng ký backtest M15: (1) đúng target symbol/minlot/step/tick/stop/
margin và quote-cost theo phiên; (2) một hypothesis thực sự khác, có nguồn,
causal entry/exit rõ, so với catalogue trước code; (3) source/clock coverage
cho full registered window, costs/adverse scenario và account equity checks.
Không bắt mua challenge để làm offline research; model khai báo phải ghi rõ
phần chưa verified. Không tìm winner bằng batch biến thể rộng trên cùng mẫu.

## Evidence, kiểm chứng và thời gian

Private root là path đã ghi trong protocol, gồm `manifest.json`,32 exports,
32 provenance/raw hashes, `result.json`, `review.json`, progress/events và cache.
Producer `prepare-four-market-fit-v1.cjs`, reviewer `review-four-market-fit-v1.py`
ở campaign base; scripts và protocol được hash, exports không overwrite.

- 32/32 requests hoàn tất, source3,427s; reviewer1,253s, tổng transport/review
  **4,680s**, không tính research/viết code/Git. Đây không tốc độ full-history.
- 222.510 raw fields được đối chiếu bằng decoder Decimal riêng từ cachedraw;
  đủ timestamp/grid/OHLCV/hash, không phải feed độc lập. Không gọi review cùng
  agent là independent reviewer sign-off.
- 1.578 decoder-padding rows Bid/Ask toàn ngày được loại theo provenance;
  các phiên đã đăng ký vẫn đủ1.920pairedminutes/128M15. Padding ngoài giờ có
  thể bình thường; không gọi toàn bộ là outage hoặc bản sửa lỗi mới của engine.
- 8 controls: extrema/close aggregation, thiếu phút, sizing có commission,
  reject dưới minlot, quantile và winter/summer NY offsets. Không sửa code
  production nên không chạy lại backtest/test engine không đổi.
- Review SHA256 `80ccc96972ccc9d09538813cc4a5ab0fac06c61586faa16cea565b04d806d6b7`.
- Không PnL/strategy, broker/model/holdout calls hoặc job còn chạy.

Hậu kiểm gọn: helper nguồn hiện có xử lý padding đúng, không có bug mới cần
vá hoặc lý do tối ưu engine ở lượt này. Thu thập/review dưới5giây; phần chậm
đang là chốt cơ chế và target contract/cost, không compute. Giữ mẫu/seals để
reuse, không lấy thêm nhiều ngày hoặc thêm framework chỉ để lấp unknown.
