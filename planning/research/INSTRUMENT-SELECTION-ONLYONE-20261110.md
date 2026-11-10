# Chọn sản phẩm cho only one M15

Ngày nghiên cứu: 10/11/2026. Owner yêu cầu nghiên cứu EURUSD và các sản phẩm
khác trước khi chọn; không ưu tiên chỉ vì project có sẵn dữ liệu.

**Kết luận:** rút ưu tiên EURUSD dựa trên reuse; chưa chốt instrument hoặc
pullback. M15 vẫn là quyết định của owner. Đích là bot phù hợp challenge và
payout bền vững, không chọn sản phẩm chỉ vì chạy mạnh hoặc cộng đồng thích.

## Cách so sánh

So thị trường cùng cơ chế dự kiến, phiên giao dịch và chi phí của đúng hợp
đồng CFD/MT5 tại quỹ đích. Instrument không tự có winrate, RR hoặc tần suất
lệnh. Nến M15 chỉ là độ phân giải quyết định. Cùng một rule không mặc nhiên
phù hợp mọi tài sản; đổi asset/giờ/exit là trial mới nếu sau này chạy.

Thứ tự đánh giá: cơ chế có thể kiểm chứng → chi phí và khả năng khớp → rủi ro
đuôi/luật quỹ/lot tối thiểu → tần suất cơ hội thật → dữ liệu tái hiện được.
Reuse là lợi ích triển khai thứ yếu. Chất lượng và quyền dùng dữ liệu vẫn là
điều kiện bắt buộc; không chấp nhận nguồn sai chỉ để mở rộng universe.

## Đối chiếu sản phẩm

Đây là đánh giá định tính của agent về câu hỏi đáng kiểm, không bảng xếp hạng
lợi nhuận hay kết quả M15 đã đo. Tên US500/NAS100/DE40/WTI là nhãn nhóm;
symbol, loại cash/futures-linked và contract đích phải xác nhận riêng.

| Sản phẩm | Cơ sở để xem xét | Điểm phải kiểm ở bot M15 | Vị trí trong vòng chọn |
|---|---|---|---|
| EURUSD | Thị trường spot lớn; lịch kinh tế hai khu vực, có thể nghiên cứu theo phiên [S1] | Có đủ chuyển động sau spread/commission không; tin ECB/Fed; không có opening auction chung như cổ phiếu | Đại diện Forex cần so, chưa ưu tiên vì data cũ |
| USDJPY | Spot lớn; thêm câu hỏi về phiên châu Á và dòng tiền Nhật [S1] | Tin BoJ/Fed, can thiệp tỷ giá không nhất thiết theo lịch; MoF ghi nhận can thiệp USD/JPY trong 2024 [S7] | Đối chiếu FX nghiêm túc với EURUSD, không chỉ đổi cặp cứu recipe cũ |
| GBPUSD | Một major khác, lịch Anh/Mỹ; spot turnover có trong S1 | Đo costs và phân phối M15 thật; không mặc định nhiều sóng hoặc dễ hơn EURUSD | Giữ trong danh sách, cần giả thuyết gắn với GBP/phiên để ưu tiên |
| AUDUSD | Cơ chế lãi suất tương đối, hàng hóa/terms of trade theo RBA [S8] | Các drivers dài hạn không tự thành tín hiệu M15; giờ thanh khoản/chi phí phải đo | Đáng xét nếu muốn cơ chế Australia/Asia cụ thể |
| US500 / S&P 500 CFD | Underlying gồm 500 công ty lớn, phiên cash có open/close rõ [S4,S5]; index commission có lợi thế công bố [S2,S3] | Gap/open, DST, spread/slippage và funding; không chuyển lợi nhuận ETF/futures thành CFD hoặc coi đa dạng cổ phiếu là bot ít drawdown | Đại diện chỉ số để so cuối |
| NAS100 / Nasdaq-100 CFD | Exposure non-financial/growth; tập trung các công ty lớn theo weighting [S6] | Concentration/earnings, open/gap và chi phí; volatility cần đo, không mặc định pass nhanh | Alternative chỉ số khi có cơ chế phù hợp; không tự xếp trên US500 vì chạy mạnh |
| DE40 / DAX CFD | Phiên cash châu Âu có khung rõ; Xetra core 09:00–17:30 giờ địa phương [S9] | DST/auction và CFD ngoài core; đây không phải full CFD trading hours | Alternative nếu cơ chế tập trung mở phiên châu Âu |
| XAUUSD / vàng CFD | Drivers về lãi suất, USD, uncertainty và flow khác equity/FX [S10] | Tin Mỹ/geopolitics, tails, spread, percentage commission, lot/SL/funding; macro thesis không tự là edge M15 | Đại diện vàng để so cuối, không chọn vì payout screenshot |
| WTI / dầu CFD | Lịch tồn kho EIA và cung-cầu năng lượng có sự kiện cụ thể [S11] | Roll/adjustment của hợp đồng, gap và tồn kho; lịch có ngoại lệ. Data WTI cũ có source gaps chưa giải quyết | Chưa ưu tiên vòng only one đầu nếu chưa có cơ chế/source đủ rõ |
| BTCUSD / crypto CFD | Có thể nghiên cứu cơ chế riêng của crypto | Spot/perpetual/CFD khác nhau; fees, funding và giờ bảo trì cuối tuần [S2,S12]; biến động không tự là edge | Để sau nếu chưa có giả thuyết crypto đủ mạnh |

Không mở rộng sang mọi exotic/cross/silver/single-stock trong lượt này. Đây là
giới hạn effort theo mục tiêu, chưa kết luận các sản phẩm đó kém hiệu quả.
AUD/GBP/JPY khác biệt không đồng nghĩa lợi nhuận độc lập; tương quan cần đo.

## Bằng chứng định lượng hiện có và phần chưa biết

- BIS final June 2026, survey April 2025, Tables 3.1–3.2: global OTC **spot**
  turnover USD/EUR 577,362; USD/JPY 476,759; USD/GBP 189,662; USD/AUD 154,517
  triệu USD/ngày. Tức khoảng 577/477/190/155 tỷ USD. Đây là activity của thị
  trường tổ chức, không market depth/retail spreads của quỹ, không một mẫu
  bao phủ mọi chế độ, và không so trực tiếp với volume futures/gold/crypto.
- The5ers FAQ cập nhật 22/07/2026: Forex 4 USD/lot round trip, indices không
  commission, metals/oil/crypto dùng commission theo phần trăm. Trang không
  cho đủ rates từng symbol trong text; phải xác nhận đúng platform/spec.
  Khoảng 0,2–0,9 pip họ công bố cho majors là mô tả điều kiện thường, không
  quote executable hoặc phân phối lịch sử đã xác minh.
- FTMO công bố zero commission trên indices; **vẫn có spread, slippage và
  funding nếu giữ qua mốc tính phí**. Symbols page có bảng động; web text
  không expose đầy đủ live rows, chưa xác minh rates/lot/margin từng symbol.
- FTMO Swing FAQ hiện cho phép news/overnight/weekend trong phạm vi forbidden
  practices; chỉ thuộc 2-Step. Đây là rule, không guarantee fills hoặc lý do
  để mặc định giữ qua tin. The5ers phải đánh giá riêng, không kế thừa rule.
- Chưa có phép đo so sánh cùng kỳ về M15 range, cost/R, adverse fills, gap,
  signal frequency hay challenge outcome của shortlist trên target feed.
  Không dùng chart đẹp hoặc biến động danh nghĩa để điền chỗ trống này.

Ví dụ giả định: risk trước phí 25 USD, round-trip cost 2 USD = 0,08R, cost
5 USD = 0,20R. 0R trước phí sẽ âm sau phí. Risk 0,25% trên 10.000 USD chỉ là
baseline offline đã có, không risk mới được chốt. Cùng risk và SL dựa trên
volatility, asset chạy mạnh có thể dùng lot nhỏ hơn; vẫn còn gap/slippage,
lot-step và margin nên không suy mọi asset có cùng tail risk.

## Đối chiếu riêng FTMO Challenge — bổ sung theo yêu cầu owner 10/11

**Có spread và commission ngay trong challenge**, không chờ tới funded.
Scope ở đây là FTMO global CFD/MT5, target 2-Step Swing đã dùng trong hồ sơ;
không lấy biểu phí FTMO Futures hoặc FTMO US áp sang. Phí mua challenge là
chi phí tiền thật riêng của owner; trading costs bên dưới được phản ánh trong
tài khoản mô phỏng và ảnh hưởng net PnL/equity.

| Sản phẩm đang so | Commission công bố mỗi chiều | Mở rồi đóng cùng volume | Spread |
|---|---|---|---|
| EURUSD / USDJPY / GBPUSD / AUDUSD | 2,50 USD/lot | 5 USD/lot | Thả nổi; chưa có distribution đúng target account/phiên |
| US500 / NAS100 / DE40, đúng index symbol | 0 | 0 | Vẫn có; zero commission không zero cost |
| XAUUSD, Metals CFD | 0,0007% giá trị danh nghĩa mỗi chiều | Tính riêng notional mở và đóng; xấp xỉ 0,0014% notional mở nếu giá gần như không đổi | Thả nổi; chưa xác minh quote live |

Nguồn xác định **per side** là [FTMO update 25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/),
đọc lại 10/11/2026: áp từ market open 29/09/2025, nói áp dụng cho all accounts.
Index0 theo [FTMO announcement](https://ftmo.com/en/blog/zero-commissions-on-indices/).
Không tìm thấy thông báo thay thế các mức này trong lượt tra; đây vẫn là
published reference, chưa là commission đối soát từ deals của đúng account.
Không suy hai tài khoản luôn có Bid/Ask/fill giống hệt hoặc mọi historical
year từng có mức phí này. Không áp The5ers rates vào FTMO.

Số 3 USD/lot round trip thuộc mức Forex cũ 1,50 USD/lot/chiều. Bài
[tips FTMO](https://ftmo.com/en/blog/tips-for-completing-the-ftmo-challenge-how-to-avoid-mistakes/)
vẫn có ví dụ 5 lots mất 15 USD: giữ ví dụ như nội dung lịch sử, không dùng nó
thay rate sau update. Search index của Symbols hiện trả Forex commission5,
nhưng web-open text chỉ có khung trang; browser thử đọc bảng bị connection
closed. **Không thu được live spread snapshot**, không coi search cache là
quote executable. Không đổi TLS/proxy/security settings để lấy bảng.

Spread = Ask − Bid, thay đổi theo thanh khoản và tin; FTMO giải thích trực
tiếp trong bài tips. Không có một số pip cố định cho cả challenge. Để so
asset, cần spread median/tail theo giờ có thể giao dịch và đúng account,
không chỉ giá nhỏ nhất quảng cáo. M15 range/ATR và spread cần cùng units.

Ví dụ **giả định**, không quote FTMO: EURUSD0,10lot, contract100.000EUR/lot,
pip0,0001 và USD account → 1USD/pip. Commission round trip0,50USD; spread
0,3pip tương đương0,30USD nếu spread mở/đóng tương tự; tổng khoảng0,80USD
trước slippage/swap. Với giá trị danh nghĩa vàng100.000USD mỗi chiều,
commission0,70USD/chiều, tổng1,40USD nếu notional không đổi. Giá mở/đóng khác
thì phải tính riêng; không copy entry×2 khi cần phí chính xác.

Khi replay đã dùng Bid/Ask cho fills, spread đã nằm trong PnL, **không trừ
lần hai**; cộng riêng commission, slippage chưa mô hình và funding/dividend
theo contract. Swap chỉ phát sinh khi giữ qua mốc tính phí, không đơn giản
là lệnh kéo dài hơn24h. [FTMO 05/11](https://ftmo.com/en/blog/trading-updates/trading-update-5-nov-2026/)
và [spec FAQ](https://ftmo.com/en/faq/what-are-the-account-specifications/)
hướng tới specification hiện hành; rates có thể đổi.

| Giai đoạn 2-Step | Cách dùng trong nghiên cứu |
|---|---|
| Challenge → Verification | Có costs; đánh giá khả năng chạm target/tránh drawdown bằng net equity, không gross trước phí |
| FTMO Account / payout | Không được tự bỏ costs sau pass; tiếp kiểm symbol/server/contract và luật giai đoạn thực tế. Published all-account schedule không chứng nhận fills giống nhau |
| Free Trial/demo đang có | Dùng để quan sát spec/quotes trong quyền được cấp; không tự chứng nhận paid Challenge hoặc tạo deals chỉ để đo commission |

[FTMO Academy daily loss](https://academy.ftmo.com/lesson/maximum-daily-loss/)
nêu equity gồm floating PnL/commission/swap. Vì vậy cost và spread widening
không chỉ giảm lãi; có thể làm sát hoặc chạm giới hạn dù chưa đóng lệnh.

Đã đối chiếu bằng chứng project: [Forex pilot §10](FOREX-PROP-PILOT-20261102.md#10-thông-số-ftmo-hiện-tại-và-development-dài-hơn--0211)
đã dùng2,50USD/lot/chiều làm reference, account-deal verification vẫn false;
[Gold target cost](GOLD-TARGET-COST-ADMISSION-20261109.md) đã giữ metals rate
theo notional và swap/account gaps; [index cost review](FTMO-INDEX-COMMISSION-REVIEW-20261108.md)
giữ scenario commission0 riêng. Không phải mọi backtest trước bỏ costs,
cũng không phải mọi declared scenario đã là exact FTMO historical replay.
Giữ frozen artifacts và verdict, không reprice/rerun trong lượt này.

**Hệ quả cho lựa chọn:** US500/NAS100/DE40 có lợi thế một thành phần phí,
chưa đủ thắng Forex/vàng về tổng cost/R hoặc edge. Trước study tiếp, khóa
target-cost reference, adverse scenario, phase và các unknown rõ ràng; chỉ
nâng account-specific verified khi có bằng chứng đúng account, không mở lệnh
để xác minh từ yêu cầu tư vấn này.

## Đề xuất tiếp theo, chưa dispatch

So cuối **ba nhóm, bốn sản phẩm: EURUSD và USDJPY (Forex), US500 (equity),
XAUUSD (vàng)**. Mục đích là kiểm lựa chọn nhóm thị trường, chưa tạo portfolio
hoặc chạy bốn bot. GBPUSD/AUDUSD/NAS100/DE40 giữ làm alternatives nếu có cơ chế
cụ thể tốt hơn. Shortlist là judgement về mức khác biệt câu hỏi và effort,
không proof bốn sản phẩm này thắng phần còn lại.

Trước chọn only one cần packet gọn cho từng sản phẩm: target contract/cost
và min-lot/margin, giờ/clock/DST, một cơ chế có nguồn, chất lượng dữ liệu,
cost/range và cost/R phù hợp cơ chế, rủi ro đuôi; đánh dấu unknown thay vì score
bịa. Sau đó chọn đúng **một instrument + một hypothesis** để đăng ký study.
Không xếp hạng bằng PnL trên hàng loạt recipe rồi che số lượt thử.

Project đã có exact FX recipes không retained, Gold H4 survivor còn gap
time-fit/cost, index recipes không retained hoặc source/transfer issues:
[catalogue](STRATEGY-CATALOGUE-20261107.json),
[transfer review](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md),
[owner report](OWNER-EVIDENCE-REPORT-20261108.md).
Giữ các kết quả âm; không lấy chúng để bác cả asset, hoặc đổi timeframe để
cứu loser. Cũng không promote Gold M15 từ H4 survivor.

Lượt này chỉ đọc nguồn public, không numerical run, account/provider mới,
OrderCheck/OrderSend, benchmark engine hoặc mở dữ liệu holdout 2025+.

## Nguồn và giới hạn truy cập

Nguồn mở/đọc ngày 10/11/2026; không dùng các trang bán bot để xếp hạng.

- **S1:** [BIS final survey annex, June 2026](https://www.bis.org/publications/triennial-survey/rpfx25-fx-annex-2606.pdf),
  Tables 3.1–3.2, PDF pages 16–17 zero-based; đọc text số liệu. [Overview](https://www.bis.org/publications/triennial-central-bank-survey-foreign-exchange-and-over-the-counter-otc-derivatives-markets-2025)
  xác nhận release final, không dùng preliminary percentages như final.
- **S2:** [FTMO symbols](https://ftmo.com/en/symbols/),
  [zero commissions on indices](https://ftmo.com/en/blog/zero-commissions-on-indices/),
  [Swing FAQ](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/),
  [instruments/strategies FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/).
  Đọc commission section, FAQ body; không coi ví dụ VWAP trong blog là kết quả.
- **S3:** [The5ers spreads/commissions](https://the5ers.com/faqs/what-are-the-spreads-and-commissions/),
  [asset specs](https://the5ers.com/asset-specifications/). Public text xác nhận
  Forex/lot-step; các tab còn lại chưa đủ rates. MT5 spec là nơi kiểm cuối.
- **S4:** [S&P 500 definition](https://www.spglobal.com/spdji/en/indices/equity/sp-500/),
  không dùng historical equity return làm forecast M15/CFD.
- **S5:** [NYSE core hours/calendar](https://www.nyse.com/trade/hours-calendars),
  09:30–16:00 ET; 20:30/21:30 giờ Việt Nam khi mở tùy DST. Đây là cash session,
  không giờ toàn bộ CFD hoặc futures. Bot vẫn cần holiday/early-close calendar.
- **S6:** [Nasdaq index overview](https://www.nasdaq.com/products/global-indexes/nasdaq-100),
  [holdings snapshot 01/05/2026](https://www.nasdaq.com/docs/2026/05/04/NDX.pdf).
  Đọc definition/weighting và holdings; không tính volatility/concentration
  score hiện tại từ snapshot. Newsroom article fetch timeout; không claim đọc full.
- **S7:** [Japan MoF intervention April–June 2024](https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2024_2Qe.html),
  actual historical operations, không dự báo thời điểm can thiệp tiếp theo.
- **S8:** [RBA AUD drivers](https://www.rba.gov.au/education/resources/explainers/drivers-of-the-aud-exchange-rate.html),
  macro education, không M15 trading rule.
- **S9:** [Deutsche Börse trading hours](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours),
  core khác extended retail và CFD. Không hard-code offset CET quanh năm.
- **S10:** [WGC mid-year 2026](https://www.gold.org/goldhub/research/gold-mid-year-outlook-2026),
  chỉ public executive summary; phần dưới yêu cầu login, không truy cập.
  [Chicago Fed gold drivers](https://www.chicagofed.org/publications/chicago-fed-letter/2021/464)
  chỉ search abstract được đọc, không full paper reproduced. Không dùng price targets.
- **S11:** [EIA release schedule](https://www.eia.gov/petroleum/supply/weekly/schedule.php),
  chuẩn Wednesday 10:30 ET có holiday exceptions, không surprise feed known-at.
- **S12:** [CFTC virtual-currency advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/understand_risks_of_virtual_currency.html),
  risk education về spot/derivatives; không rule hay pricing crypto CFD của quỹ.
