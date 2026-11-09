# Discovery10 — ba giả thuyết goldH1, freeze trước outcomes

Discovery9historical SMA50k dương10/15stressyears nhưng một5yearband âm và
lợi nhuận thấp; chưa challenge. Không tune SMA/Donchian/Z hoặc đổirisk. Hướng
này kiểm intraday ítcarry và nhiềutrades hơn, không giả định nhiềutrades=tốthơn.

## Recipes

| Candidate | Entry/exit/SL |
|---|---|
| xauusd-h1-asia09-15tokyo-london-break-atr14x1p5-r025-v1 |Exact clock/entry/exit/latch của EURUSDAsiaORBDiscovery7, SL1,5WilderATR14; asset/cost/sizinggoldriêng |
| xauusd-h1-rsi14-reentry-atr14x1p5-time12-r025-v1 |Exact RSI14reentry30/70, exit50 hoặc12observedH1holding bars từDiscovery4, SL1,5WilderATR14 |
| xauusd-h1-london-afternoon-reversal15-19-atr14x1p5-r025-v1 |Mon–Fri, chỉ decision15:00Europe/London; cần observed bar09:00local, currentclosed14–15 và≥100history. Nếu currentclose−09baropen≥ATR14thìSELL;≤−ATR14thìBUY, không có thìflat. Exit19London (late nextclose); SL1,5WilderATR14, maxoneemit/day |

NoTP/nointrahourreversal/noentrybù; next modeledH1open, noforceclose. Afternoon
heuristic điều kiện1ATR là registeredhypothesis, không paper-backedthreshold.
[LBMA auction times](https://www.lbma.org.uk/prices-and-data/about-lbma-daily-auction-prices)
và[ICE](https://www.ice.com/iba/lbma-precious-metals) xác nhận goldAM10:30/PM15London;
PMdecision trước publishedauctionoutcome, **không dùng licensedbenchmarkprices
hoặc giả vờ sauauction15:00đã biết finalprice**. Tênrecipe “afternoonreversal”,
không exactfixreplication. [Batten etal2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5407636/)
cho intradayvolume/spread/volatility context, không chứng minh meanreturnrule.
Cộng đồng chia sẻ overnight/intradaydecomposition chỉ gợi ý, chưa fees/SL/CFD
replication, không dùng làm proof. GoldLondonpatternkhácFXUSDfixpattern.

## Data/spec/test và cách chọn

Reuse exactDiscovery9raw20091101–20241231SHA d209df9a…;15annualbooks2010–2024,
warmupNov–Dec/H1history100. Chỉ50k,planned125USD(0,25%),lotminstep0,01,
contract100oz/grid0,001/leverage10. Reference/stress theoDiscovery9; sameM1Bid/
declaredAsk, financing/gaps/SLlimitations, notinternalrisk/prop/fulltickDD.
Không swap-freehack, grid/martingale hoặc đổirisk/cost để pass.3×2×15=90rows.

Typedassetpolicy giữ IDgold/stateidentity, không đưa gold vào nativeEURUSDCLI
hoặc bỏForexPilotSnapshotguard. Unit clocks/DST/missing09bar/timeexit,
restore/sideidentity/manualsizing/SLcash và oldEURUSD/goldH4goldens trước outcome.
Source/input/protocol/specpins+snapshot, mộtwriter/attempt/deadline900s/status/
failure; không overwrite parentresults. MainD:nativejobs nguồn78a8397fgiữ nguyên.

Ưu tiên max2versions totalnet dươnghai costs và stressdương≥10/15years; rank
weakest5yearstresssum theo normalizedsize.0trades/thiếucoverageinconclusive;
không tự chọnnhiềuhours/directions/thresholds sau outcomes. Tất cảdescendants/
trials/controls tính và giữfailures, không cleanOOS. Promotion vẫn cần actual
tick/risk/prop/uncertainty/selection/freshholdout/forward theo campaignC1/C2.
