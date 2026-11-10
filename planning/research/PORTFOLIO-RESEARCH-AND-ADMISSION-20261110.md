# Portfolio cho prop firm: chia nguồn rủi ro, kiểm một tài khoản chung

10/11/2026, owner yêu cầu research và áp dụng sau R093. **Áp dụng ngay vào
cách chọn nghiên cứu và cửa kiểm định; chưa có portfolio đủ evidence chạy
challenge.** Không cần đợi từng strategy standalone challenge-qualified mới
nghiên cứu phối hợp, nhưng chưa có căn cứ ghép mọi loser hoặc tối ưu hàng
nghìn cặp. Portfolio là một phiên bản hệ thống cần kiểm định riêng.

## Cách hiểu và lựa chọn cho project

Portfolio là nhiều strategy/market cùng dùng một ngân sách tài khoản. Mục
đích là giảm phụ thuộc vào một kiểu thị trường và một chuỗi thua, không tự
nhân lợi nhuận hay budget. Nhiều bot giống nhau vẫn có thể là một cược lớn.

| Cách ghép | Giá trị / rủi ro | Áp dụng |
|---|---|---|
|Nhiều tham số cùng indicator/symbol|Thường trùng cơ hội, có thể cùng thua; nhiều tên không là nhiều edge|Gom cùng family, không ưu tiên thêm biến thể để tăng số lượng|
|Khác cơ chế:trend/reversion/flow|Có thể bù giai đoạn thua nhưng vẫn có commonUSD/rates/equityrisk|Ưu tiên cơ chế có bằng chứng và đóng góp mới; không suy độc lập từ tên|
|Khác thị trường|Có thể phân tán rủi ro, nhưng US500/Nasdaq hoặc nhiều FX cóUSD có thể cùngbet|Kiểm currency/direction/macro exposure và equity losses đúng thời điểm|
|Khác thời gian giữ/phiên|Có thể ít tranh budget, nhưng spread/funding/news khác nhau|Tính đồng thời positions/pending/rollover, không chỉ correlation lệnh đã đóng|
|Mộtalpha + mộthedge|Hedge có thể giảm lợi nhuận bình quân để giảm tailrisk|Chỉ mở khi có cơ chếhedge đăng ký trước, kiểm incremental lợi ích và chi phí|

Không bắt mọi sleeve lời mọi năm. Một sleeve lỗ riêng có thể có ích khi
thực sự bù rủi ro của phần khác; cần evidence chung sau phí và ngoài mẫu.
Ngược lại, với weights không âm cố định và cùng linearunits/costpath,
expected arithmeticreturn của toàn bộ sleeves có expectationâm vẫnâm.
Correlation không biến nó thành dương. Dynamic weights/rebalancing/nonlinear
risk management đổi giả thuyết và cần trial riêng, không tự là lời giải.

## Nguồn đã đọc và phạm vi

| Primary source đọc10/11 | Dùng vào đâu / giới hạn |
|---|---|
|[MOSEK PortfolioCookbook§9](https://docs.mosek.com/portfolio-cookbook/risk_parity.html)|Risk contribution phụ thuộc weights và covariance; equal-dollar hoặc inversevol không tự là exactriskparity. Đọc§9.1–9.3, không cài/chạy solver|
|[Kirby/Ostdiek2012](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/its-all-in-the-timing-simple-active-portfolio-strategies-that-outperform-naive-diversification/05D18E04B226C6E9B8441482CC92F943)|Publisherabstract: optimization có thể thắng1/N nhưng turnover ăn mất lợi ích; không kết luận1/N luôn tốt nhất. Không fullpaper audit; DeMiguelpublisher/LBS không truy cập được nên không gọi đã đọc fullpaper|
|[AQRdiversification/drawdowns](https://www.aqr.com/insights/research/alternative-thinking/it-was-the-worst-of-times-diversification-during-a-century-of-drawdowns)|Landing summary: diversifying khác defensive, protection có trade-off lợi nhuận; không nhập correlations/returns AQR thành evidence cho mình hoặc fullpaper replication|
|[QCportfolio construction](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts)|Alpha→targets→risk→execution, hỗ trợ multialpha; tham khảo ownership, không đổi engine hoặc càiLEAN|
|[FTMOAcademy daily loss](https://academy.ftmo.com/lesson/maximum-daily-loss/)|2-Step equity gồm floating/commission/swap, midnightCE(S)Tbalanceanchor; không mỗi bot có một dailybudget riêng|
|[The5ersprohibited practices](https://www.the5ers.com/faqs/prohibited-trading-practices/),update03/11 và [Terms§11](https://the5ers.com/terms-and-conditions/),update28/10|Overexposure correlated instruments, manipulative crossaccount hedging/profitday engineering; wordingbulk simultaneous trades rộng. EA yêu cầu writtenapproval/sourceownership theoTerms. Portfolioanalysis không tự cấp permission|

The5ers không được mặc định cho concurrent multi-bot chỉ vì totalrisk nhỏ.
Wordingbulk và nguồnTerms/FAQ cần xác nhận phạm vi exactprogram/code trước
deployment; không diễn giải thành mọi phân tán đầu tư đều cấm hoặc tự né bằng
trì hoãn lệnh. Không nhắn support/thay owner/muaaccount trong lượt này.
Không suy mọi multiaccount hedge là arbitrage được phép; FTMO vàThe5ers là
hai profile/acceptance riêng. Chỉ đọc nguồn chuyên môn/official đủ cho quyết
định này, không lấy upvotes hoặc marketing làm profitability evidence.

## Baseline đơn giản trước optimizer

**Hai hoặc ba cơ chế có lý do là nhóm khởi đầu, không số lượng đủ để bảo đảm
đa dạng hóa.** Dùng split ngân sách plannedstoprisk cố định theo family trước;
giới hạn pertrade/currency/event/account chung, phần chưa dùng giữ cash.
Đây không exactequalriskcontribution. Chỉ thêm inversevol/ERC/shrinkage/HRP
khi đủ alignedreturnhistory và thắng baseline ở kiểm định ngoài mẫu sau phí;
chưa có lý do thêmsolver/ML/LLM allocation hoặc estimator mới.

Ví dụ minh họa, **không thay config/quyền hiện tại**: account10.000USD,
pertrade0,25%=25USD; giả định concurrentplannedriskcap0,5%=50USD. Ba bot
đều mở25USD làm tổng75USD, không phải50USD vì tên khác. Có thể giữ25USD và
chỉ nhận tối đa2lệnh theo priority đã khóa; hoặc đăng ký sizing nhỏ hơn cho
cảportfolio. Không mặc định giảm25USD xuống12,50USD mà không replay lotgrid/
fees/margin. Risk50USD là plannedstoprisk, gap/slippage vẫn có thể lỗ hơn.
Giới hạn này chỉ ví dụ, không luật hãng hoặc grant mới.

## Cửa thực thi nghiên cứu portfolio — bổ sung vào workflow hiện có

| Lát | Phải có trước khi kết luận | Quyết định hiện tại |
|---|---|---|
|P0.Chọn thành phần|Mechanism/source/version; alpha hay hedge; lý do phối hợp trước jointoutcome; giữ parent/negatives/trialcount|Tách alpha candidates và hedging research; không quét allpairs hoặc tự đảo sign các bản lỗ|
|P1.Cùng thước đo|Cùngtimestamp/calendar/accountcurrency, vốn đầu từngsổ, sizing/cost/rule; netequity gồm openPnL/costs. Knownflat0 khác missingunknown|Chưa có ready alignedportfolio panel cho các bản đang xét; không correlate tổngannualPnL hoặc trade thứn giữa hai chiến lược|
|P2.Dependency|Daily/hourlymarkout correlation kèm samples/CIs khi đủ, jointdownside/tail/coststress, overlap positions/pending, USD/rates/gold/equity/eventclusters|End-of-day analysis chỉtriage; không chứngminh intradaypropDD. Correlationfullsample thấp không là độc lập hoặc tailprotection|
|P3.Weights/allocation|Freeze membership, weights/risk/priority/rebalance/fitwindow; estimator chỉ dùngpast; đo incremental đóng góp và costturnover|So incumbent ở cùng totalrisk, hoặc cùngreturn vớirisk thấp hơn; không thưởng portfolio chỉ vì tăngnotional/lot|
|P4.Sharedaccount replay|Mộtcash/equity/margin/positions/pending owner; đồng thời signals có deterministictie-break, từchốivìcap/sizing đượcghi;netting/hedging/magicID cóattribution|Không cộng standaloneequity như đã chạyaccount; thay cost/risk có thể thayfills/trades. Không gộp annualresets thànhcontinuousbook|
|P5.Prop/timefit|Đúngfirm/program/phase, dailyreset/intradayfloating/overall/target/activation và3/6/12tháng; samples rollingstart phụthuộc|Firstbreach dừng đúng lúc, miss/slippage/funding/spread/gapstress; bootstrap phải giữcross-sleeve cùngtimeblocks, không shuffle từngbot độc lập|
|P6.Review/forward|OOS/prefixcausality/selectiontrialhistory, prospective/reconciliation vàowner hiểu eachsleeve|Portfoliofreeze là trialmới; historicalpair chọnđẹp khôngthànhcleanOOS. Không mởown2025+ hoặc broker grant|

Không yêu cầu mọi strategy phải qua standalone challengegate để vào P0.
Thành phần hedge có đường đăng ký jointtest riêng, với correctness/realism
đạt scope và hypothesis bù rủi ro rõ; không tự mở lại loser vì thấy âm tương
quan trên mẫu đã xem. Gates mỗi năm của R093 là triage experiment đó, không
luậtportfolio phổ quát. Khi mẫu thiếu:inconclusive, không gắn CI/xácsuấtpass giả.

## Đã đối chiếu project và áp dụng gì ngay?

| Evidence hiện có | Hạn chế cho portfolio | Hành động |
|---|---|---|
|R043SMA vàng,30annualbooks|Positive researchsurvivor, nhưng annualreset/fees/spec/nativeequity/timefit/cleanOOS gaps|Giữsurvivor, chưa chọn nó làm corechallenge hoặc tính covariance bằng15annualtotals|
|R088EURUSDpostFOMC,32windows|Pricecomponent dương nhưng eventincrement2022khôngđạt;notional100kEUR/noSL/account|Giữ kết quả, không gộpUSDunit vớiGold50k; nếu có cơ chếhedge mới phảifreezejointtest|
|R093optionsweek,48windows|2022midâm/netâm;fixedUSDperpoint/noSL/account|Gác exactalpha, không ghépGold để giấu thua hoặc tự short lại|
|R010multiassetmonthly|Đã thử inversevolproxyEURUSD/Gold/US500;funding làmnetâm, monthlyDDkhácpropDD|Reuse lesson/negative, không nói project chưa từng thửmultiasset hoặc thêm inversevol là đủ|
|RiskBudgetPython + automationgrantRust|Có limits/reservations và accountlock; chưasource bằngchứng về multistrategyallocationequityreplay|Giữnativeexecutionowner, không tạo3grants/3budgets hoặc competingmanager|

Source inspection tại Traderpin`930fa768`: `risk_promotion_contracts.py` là
purecontract, khôngruntime enforcementproof. `automation_grants.rs` accountkey
workspace/server/login chặn nhiều activegrant và reservespertradecap; kiểmtra
source không là vận hànhđãđạt multi-sleeve account trênbroker. Chưa sửaTrader,
runtime/account/grants/MT5 hoặc cần service mới.

**Đã áp dụng:** thêm portfolio stage ở strategyworkflow và campaign, lập
readiness/evidenceintake với pins của4baseline hiện có; giữ verdicts/units,
không báo có portfolioPnL/correlation/passrate khi chưa đo. Existing research/
qualificationskills đủ, chưa cần skill mới hoặc database/MCP/optimizer.

**Bước kế có ích:** mở research P0 theo cơ chế có inputcausal và pathreview
phù hợp; khi có hai sleeves khả dụng hoặc mộtalpha+mộtsupportedhedge mới,
đăng ký alignedmarkout và sharedaccountbaseline trước allocation thử. Chưa
cóconsumer/data đủ cho portfolioreplay thì không viết engine song song để
lấp bảng. OwnerđãxóaGoal, lượt này tiếp taskđượcgiao; C1/C2 vẫnchưađạt.

Privatecampaign`execution-v1/portfolio-admission-v1/` giữreadiness/sources/
sourcehashes/illustrativearithmetic/receipt, khôngmarketinputs mới hoặc PnL
thửnghiệm. Timing phân loại/sourceaudit là worker time riêng; activewebresearch/
code/review chưa đo đầy đủ, không báo0hoặc suy từGit.

Readiness4records và sourcepins đã ghi; closeout worker0,151s/CPU0,047s,
không phải toàn thời gian research. Synthetic arithmetic đối chiếu Fraction:
3×25=75>50USD; expectedmean của0,5×(−1)+0,5×(−2)=−1,5; hai sleeves unitvol
weights0,5/0,5 có volatility√0,5≈0,707 khi correlation0 và1 khi correlation1.
Ví dụ chỉ minh họa vai trò dependency, không measuredcorrelation/return của
project hoặc bằngchứng giảmriskprop. KhôngquyđổiVND bằngFXratechưađọc.
