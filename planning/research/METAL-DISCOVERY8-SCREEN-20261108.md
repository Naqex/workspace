# Discovery8 — frozen XAUUSD H4 screening

Owner cho phép mở rộng cách nghiên cứu; [preparation](METAL-DISCOVERY8-PREPARATION-20261108.md)
giữ data/transport/cost corrections trước strategyoutcome. Đợt này chỉ historical
development trên2021–2024, không cleanOOS hoặc broker execution.2025+closed.
Không sửa sourceD: đang chạy hai EURUSDannualbatches; triển khai ở isolated
`C:/Users/MIIKEY/.codex/worktrees/research-metals/trader`, base78a8397f.

## Fixed recipes và model

Ba version mới, cùng algorithms của comparatorEURUSD, không tối ưu thresholds:

| ID | Rules |
|---|---|
|xauusd-h4-donchian20-10-atr14-r025-v1|ClosedH4 vượt prior20high/low, exit opposite prior10channel; SL2WilderATR14 |
|xauusd-h4-sma20-80-atr14-r025-v1|SMA20/80 cross, exit mất direction; SL2WilderATR14 |
|xauusd-h4-z20-2-atr14-time6-r025-v1|Prior20populationz entry±2, exit0 hoặc6observedH4holding bars; SL2WilderATR14 |

NextH1modeledopen fills, no samebar/reversal, noTP hoặc forceclose cuối mẫu.
H4gaps/completeness như currentbuilder; M1→H1→H4 chỉ từ observedM1, không bù giá.
Signals từ modeledmid=Bid+declaredspread/2; rawprice giữ nguyên. M1OHLC là Bid,
không observedAsk; constantspread Ask/Bid extrema là scenario assumption,
không native quote stream hoặc broker fills. H1stops tại level/open không biết
firstcrossingtick/gaps nội bộ; rawticks count phảiunknown, reportsourceM1rows.

| Spec/cost | Reference | Stress |
|---|---:|---:|
| Instrument |XAUUSD,metal,XAU/USD,accountUSD|Cùngspec |
| Contract/quotegrid/minlot/step |100oz/lot;0,001;0,01;0,01|Cùngspec |
| DeclaredspreadUSD/oz |0,50|1,00|
| SlippageUSD/ozperside |0,10|0,20|
| CommissionUSD/lotperside |2,50|2,50|
| FinancingdebitUSD/lot/night,both sides |20|40|
| Financingclock |22UTCweekdays,Wed×3|Cùngcounterfactual |
| Declaredleverage |10|10|

Historicalbroker fees/grid/leverage/financing và tailspread chưa verified.
Quotegrid0,001 dựa1dayDukascopyfixture; không gắn nhãn FTMOverifiedspec.
Initial10k/planned25USD/trade, conservativeone-tick sizingreserve và quantity
floor0,01. Không đạtminimumlot thìskip/đánh dấuinfeasibleở10k, không tăngrisk.
Coarsekhông internal daily100/overall500/prop/DD; chúng vẫn là gates native
sau này. Không đổi limits để cứu kết quả hoặc nhận brokerpermission.

## Windows, execution và acceptance

RawexportSHA834d4678f8e2a45914119854d5fe7d3ec45a1281c81d4952830fc76a65f636fb,
1.773.334M1rows từ01/01/2020–31/12/2024, provenance/prep review có hash/time/grid.
Evaluation4calendar years2021/22/23/24 riêng, mỗi account startflat10k; warmup
Nov–Decnăm trước, không warmupPnL.2020 chỉ input warmup; không lựa year theo
PnL. Tối thiểu81validH4warmup. Các rules là related transfers, thêm vào history.

Trước outcome: typed instrument/market identity, goldlot/$risk, tick/spread/
slippage/commission/financing/margin, rejection unsupported nonUSD instruments;
candidate state/prefix/restore; EURUSDgolden parity. Reuse samecoarseexecution
core, không monkeypatch instrument hoặc tạo simulator mới. DefaultEURUSDCLI
không tự nhậnXAU hoặc đổi scope; M1driver opt-in/pinned input/source/spec/protocol.

Run3×2costs×4years, một writer/attempt, status/log/failure/deadline,24rows.
Metric netequityUSD gồm floating, counts/open/pending/minlot feasibility, cash
reconciliation; không ledgerDD/modeledbars thành actualtickDD. Source snapshot
trước dispatch, không overwrite results hoặc sửa frozenpins sau outcome.

Ưu tiên max2versions: totalnet dương ở cảcosts và ít nhất3/4years stress dương;
rank weakest-yearstress, giữ tất cả negatives. Annualaccounts chỉ dùng tổng
cho descriptive ranking, không cùng một portfolio/accountpath.0trades vì minlot
hoặc thiếucoverage làinconclusive, không0edge; count không đủ không promote.
Criteria này phân bổ review, không thống kê bảo đảm. Survivors vẫn cần actual
Bid/Askticks, risk/prop, selection-aware uncertainty, frozenfreshholdout và
forward/reconciliation trước C1. CurrentcampaignC1/C2chưa đạt.
