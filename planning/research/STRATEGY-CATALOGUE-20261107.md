# Danh mục nghiên cứu chiến lược — cập nhật08/11/2026

53 hồ sơ: 36 đã có implementation (41 policy versions), 16 ý tưởng chưa code và 1 risk component. Trong 41 versions có 24 native offline rules, 4 ML coarse-only, 6 gold coarse-only và 7 index M1 coarse-only; gồm 2 shuffled controls và 1 long-only benchmark. **Không phải 41 edges độc lập; chưa bản nào challenge-qualified.** Capital 10k/50k và các cost/year scenarios không được đếm thành strategy độc lập.

[JSON](STRATEGY-CATALOGUE-20261107.json) là cùng dữ liệu có cấu trúc; protocol/source giữ exactrecipes, không automatic dispatch/rejection hoặc broker authority.

| ID | Ý tưởng | Họ/parent | Tình trạng | Policy versions | Evidence |
|---|---|---|---|---:|---|
|R001|Donchian20/10|trend_breakout|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R002|SMA20/80|trend_breakout / R001|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R003|Z-score20 ±2|price_reversion|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R004|Pullback20/80|trend_breakout / R002|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY4-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R005|UTC range00–08 breakout|session_breakout|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R006|Failed20 breakout|level_reversion / R001|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R007|Compression6/24 breakout|trend_breakout / R001|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R008|UTC range fade|level_reversion / R005|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|Chưa outcome riêng|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R009|Time-series momentum dài hạn|long_horizon_trend|Source-only32/132months eligible;guardchặn,khôngPnLmới|1|[Monthly admission](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)|
|R010|TSMOM theo volatility|long_horizon_trend / R009|long_history_or_multi_data|0|Chưa outcome riêng|
|R011|Bollinger re-entry|price_reversion / R003|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R012|RSI contrarian có xác nhận|price_reversion / R003|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY4-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R013|ATR shock fade|price_reversion / R003|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY4-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R014|Range midpoint fade|level_reversion / R006|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY4-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R015|Previous-day high/low breakout|session_breakout / R001|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY4-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R016|London opening-range breakout|session_breakout / R005|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R017|New York opening-range breakout|session_breakout / R016|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R018|Asia range → London breakout|session_breakout / R005|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R019|Break → retest prior level|trend_breakout / R015|price_data_spec_possible|0|Chưa outcome riêng|
|R020|Fixing reversal có điều kiện|fixing_flow|method_clock_review|0|Chưa outcome riêng|
|R021|Pre-fix USD drift|fixing_flow / R020|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R022|Post-fix USD reversal|fixing_flow / R020|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R023|Local trading-hours currency flow|session_flow|method_clock_review|0|Chưa outcome riêng|
|R024|Post-weekend gap fade|gap_reversion|Component12h không đạt priority; chưa strategy|0|[Componentresults](WEEKEND-GAP-COMPONENT-RESULTS-20261108.md), [datareview](WEEKEND-GAP-DATA-RESULTS-20261108.md)|
|R025|Weekday/calendar effect|calendar|Source-corrected TOM chưa đạt; chưa bot|0|[Correction3days/reuse1507](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)|
|R026|Month-end fixing flow|fixing_flow / R020|Bounded fixture đạt; chưa signal/calendar spec|0|[Method](FX-MONTH-END-FIXING-METHOD-20261108.md), [source review](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md), chưa PnL|
|R027|News-surprise continuation|event|point_in_time_news_missing|0|Chưa outcome riêng|
|R028|News overreaction reversal|event / R027|point_in_time_news_missing|0|Chưa outcome riêng|
|R029|Currency carry|carry|long_history_or_multi_data|0|Chưa outcome riêng|
|R030|Carry + trend|carry / R029|long_history_or_multi_data|0|Chưa outcome riêng|
|R031|Long-horizon value / PPP|value|long_history_or_multi_data|0|Chưa outcome riêng|
|R032|Value + momentum|value / R031|long_history_or_multi_data|0|Chưa outcome riêng|
|R033|Cross-sectional FX momentum|cross_section|long_history_or_multi_data|0|Chưa outcome riêng|
|R034|FX factor-residual reversion|cross_section / R033|long_history_or_multi_data|0|Chưa outcome riêng|
|R035|Cointegrated FX spread|cross_section / R034|long_history_or_multi_data|0|Chưa outcome riêng|
|R036|Volatility targeting / exposure cap|risk_modifier|component_only|0|Chưa outcome riêng|
|R037|Fixing composite3slots|fixing_flow / R022|Đã code, chưa qualified|Exact FX versions đã gác sau frozen cost screen|[Kết quả](DISCOVERY6-7-RESULTS-20261108.md)|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family
|R038|Ridge4Hreturn policy|trained_return|Đã code, chưa qualified|1|[Kết quả](DISCOVERY5-RESULTS-20261108.md)|
|R039|Random forest4Hreturn policy|trained_return / R038|Đã code, chưa qualified|1|[Kết quả](DISCOVERY5-RESULTS-20261108.md)|
|R040|Ridge shuffled-label control|falsification / R038|Đã code, chưa qualified|1|[Kết quả](DISCOVERY5-RESULTS-20261108.md)|
|R041|Forest shuffled-label control|falsification / R039|Đã code, chưa qualified|1|[Kết quả](DISCOVERY5-RESULTS-20261108.md)|
|R042|Gold Donchian20/10|trend_breakout / R001|Giữ negative version|1|[Gold outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R043|Gold SMA20/80|trend_breakout / R002|Giữ research50k, hạ ưu tiên challenge do time-fit/gaps|1|[Time-fit review](GOLD-SMA50K-REVIEW-20261108.md), [original outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R044|Gold Z20 ±2|price_reversion / R003|Giữ negative version|1|[Gold outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R045|Gold Asia→London breakout|session_breakout / R018|Giữ negative version|1|[Gold outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R046|Gold RSI reentry|price_reversion / R012|Giữ negative version|1|[Gold outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R047|Gold afternoon reversal15–19London|fixing_flow|Giữ negative version|1|[Gold outcomes](METAL-DISCOVERY9-10-RESULTS-20261108.md)|
|R048|US500 noise14 bands|equity_intraday_momentum|Source-only correction vẫn không đạt triage|1|[Corrected outcomes](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)|
|R049|US500 daily cash IBS02 hold|equity_daily_reversion|Source-only3years không đạt oldpriority;path unresolved|1|[Corrected results](IBS02-EXPLICIT-SOURCE-RESULTS-20261108.md)|
|R050|US500 CutlerRSI3 +IBS05|equity_daily_reversion /R049|Source-only long không đạt;6nofillyears inconclusive|1|[Corrected long](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)|
|R051|US500 first→last30min|equity_close_momentum|Source-only correction vẫn âm cả2022–24/costs|1|[Corrected outcomes](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)|
|R052|US500 RSI3+IBS preclose2|equity_daily_reversion /R050|Source-only long vẫn không đạt;4nofillyears inconclusive|1|[Corrected long](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)|
|R053|US500 monthly long benchmark|falsification /R009|Source-only admissionfail;khôngportfolio rerun|1|[Monthly admission](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)|

## Cách đọc và việc đang chạy

Discovery4/6/7 historical screens đã completed; MLreal policies thất bại, giữ controls/negatives. Asia2023/2024 native review đã completed; Londonstresscả2years còn incomplete do timeout. [Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md) đã624/624cases,0/24retained trên observedhistory2010–2022. R048noise14 là cơchế/asset khác: [kết quả](US500-NOISE-RESULTS-20261108.md)2022dương nhưng2023/24âm ởcảcosts,khôngretained. Không writer còn chạy trongcácattempts này. Không dispatch lại screens hoặc gọi2023/2024cleanOOS.2025+vẫn đóng.

Nguồn chỉ cho cơ chế/định nghĩa/phương pháp; code và datalicenses cần kiểm trước import. Các adaptations H1/SL/holding không phải exact paper replication. Fixed-window variants, ORBs và MLcontrols có quan hệ; số versions không là số bằng chứng độc lập. Public payout/case study tay không xác nhận bot edge.

## Nguồn và ngày kiểm

Chỉ nâng ngày cho nguồn thực sự đọc lại; top updated_on không có nghĩa mọi paper đã refresh hoặc full-method audit.

- **NY125** — [Currency Orders and Exchange-Rate Dynamics](https://www.newyorkfed.org/research/staff_reports/sr125.html). 2026-11-07; Order/level mechanism; not our rolling thresholds.
- **NY150** — [Stop-Loss Orders and Price Cascades in Currency Markets](https://www.newyorkfed.org/research/staff_reports/sr150.html). 2026-11-07; Stop cascade mechanism; not a compression recipe.
- **BOC48** — [Foreign Exchange Fixings and Returns Around the Clock](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/). 2026-11-07; Fix-related drift/reversal; full method/clock must be read before replication.
- **SNB04** — [Intraday patterns in FX returns and order flow](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04). 2026-11-07; Historical local-hours effects; not a current EURUSD bot guarantee.
- **AQR-TS** — [Time Series Momentum: Original Paper Data](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data). 2026-11-08; 12-month lookback/monthly holding; futures/forwards, not H4 CFD.
- **AQR-VM** — [Value and Momentum Everywhere: Factors, Monthly](https://www.aqr.com/Insights/Datasets/Value-and-Momentum-Everywhere-Factors-Monthly). 2026-11-07; Long/short multi-market factors; not EURUSD-only replication.
- **BIS366** — [Currency Momentum Strategies](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies). 2026-11-07; Cross-sectional currency momentum with costs/limits to arbitrage.
- **CARRY** — [Carry Trades and Currency Crashes](https://economics.princeton.edu/working-papers/carry-trades-and-currency-crashes/). 2026-11-07; Carry mechanism and negatively skewed crash risk; CFD swaps not policy rates.
- **NEWS** — [How Economic News Moves Markets](https://www.newyorkfed.org/newsevents/news/research/2008/rp080908). 2026-11-07; Announcement surprise responses; does not validate continuation/reversal rules.
- **TV-RSI** — [Relative Strength Index](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/). 2026-11-07; Indicator definition only; no profit evidence.
- **TV-BB** — [Bollinger Bands](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/). 2026-11-07; Indicator definition only; no profit evidence.
- **QC** — [Backtesting Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide). 2026-11-07; Workflow reference in AI plan; not strategy profitability evidence.
- **LOCAL** — [Naqex exact eight candidate rules](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md). 2026-11-07; Exact implemented rules/history; published literature is mechanism context only.
- **SKLEARN** — [Scikit-learn preprocessing and time-series validation](https://scikit-learn.org/stable/common_pitfalls.html). 2026-11-08; Method only, not forex profitability evidence
