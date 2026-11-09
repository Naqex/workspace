# Danh mục nghiên cứu chiến lược — cập nhật09/11/2026

88 hồ sơ: 47 có policy/model version được ghi trong danh mục (58 versions), 40 chưa có account policy và 1 risk component. Trong 58 versions có 25 native offline rules và 33 tooling/coarse/model versions; gồm 9 controls. R080–R083 không retained; R084 mua chính không đạt, follow-up bán sau fix R085 cũng không đạt khi mở rộng lịch sử. R086 FOMC price momentum không qua stressgate; R087 Nhật–Mỹ knownnet âm và có coveragegap, chưaannualPnL. R088 sauFOMC net dương nhưng eventincrement2022 khôngđạt. Price components không đếm thành account policies hoặc independent edges. **Chưa có bản nào challenge-qualified.**

[Bản đồ cơ chế và task](MECHANISM-FIRST-EXECUTION-20261109.md) gom đủ80historicalIDs
khôngtrùng/thiếu;R081 làconditionalderivative liênquanR080.8buckets cócontrols/
ML/riskroles, không8provenedges. Historicalnegative/pins giữ nguyên.

[JSON](STRATEGY-CATALOGUE-20261107.json) là cùng dữ liệu có cấu trúc; protocol/source giữ exactrecipes, không automatic dispatch/rejection hoặc broker authority.

R076/R077 thêm [paper-window component v2](INDEX-PAPER-WINDOW-IMPLEMENTATION-20261109.md)
đã [reviewed và không retained](INDEX-PAPER-WINDOW-RESULTS-20261109.md). Revision lineage nằm ngay trong
hai JSON records; v1 negatives giữ nguyên, không tăng account-policy count
hoặc đếm delays thành independent edges. [Protocol](INDEX-PAPER-WINDOW-ECONOMIC-PROTOCOL-20261109.md)
freeze trước outcomes; old quarter-mask failure và corrected attempt đều giữ.

| ID | Ý tưởng | Họ/parent | Tình trạng | Policy versions | Evidence |
|---|---|---|---|---:|---|
|R001|Donchian20/10|trend_breakout|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R002|SMA20/80|trend_breakout / R001|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R003|Z-score20 ±2|price_reversion|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R004|Pullback20/80|trend_breakout / R002|Các exact FX versions đã gác sau cost screen|2|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R005|UTC range00–08 breakout|session_breakout|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R006|Failed20 breakout|level_reversion / R001|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R007|Compression6/24 breakout|trend_breakout / R001|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R008|UTC range fade|level_reversion / R005|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R009|Time-series momentum dài hạn|long_horizon_trend|Source-only32/132months eligible;guardchặn,khôngPnLmới|1|[Monthly admission](INDEX-LONG-EXPLICIT-RESULTS-20261108.md)|
|R010|TSMOM theo volatility|long_horizon_trend / R009|Gác mixedmonthlyproxy:−1.138,18/−3.519,01USD;chưa accountpolicy|0|[Component results](MULTI-ASSET-TREND-RESULTS-20261108.md);4books/1.008allocations reviewed|
|R011|Bollinger re-entry|price_reversion / R003|Các exact FX versions đã gác sau cost screen|2|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R012|RSI contrarian có xác nhận|price_reversion / R003|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R013|ATR shock fade|price_reversion / R003|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R014|Range midpoint fade|level_reversion / R006|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R015|Previous-day high/low breakout|session_breakout / R001|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R016|London opening-range breakout|session_breakout / R005|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R017|New York opening-range breakout|session_breakout / R016|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R018|Asia range → London breakout|session_breakout / R005|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R019|Break → retest prior level|trend_breakout / R015|Retest3 đã code; stage1 không đạt, giữ exact negative|1|[Paired results](PRIOR-DAY-RETEST-RESULTS-20261108.md);50/52trades, chưa tick/prop/OOS|
|R020|Fixing reversal có điều kiện|fixing_flow|method_clock_review|0|Chưa outcome riêng|
|R021|Pre-fix USD drift|fixing_flow / R020|Các exact FX versions đã gác sau cost screen|3|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R022|Post-fix USD reversal|fixing_flow / R020|Các exact FX versions đã gác sau cost screen|2|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
|R023|Local trading-hours currency flow|session_flow|PrimaryUScomponent không đạt retention|0|[Componentresults](LOCAL-SESSION-RESULTS-20261108.md); chưa policy/prop|
|R024|Post-weekend gap fade|gap_reversion|Component12h không đạt priority; chưa strategy|0|[Componentresults](WEEKEND-GAP-COMPONENT-RESULTS-20261108.md), [datareview](WEEKEND-GAP-DATA-RESULTS-20261108.md)|
|R025|Weekday/calendar effect|calendar|Source-corrected TOM chưa đạt; chưa bot|0|[Correction3days/reuse1507](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)|
|R026|Month-end relative-equity flow|fixing_flow / R020|Gác exactadaptation sau6years;stress−227,6pip/66resolved|0|[Continuationresults](R026-RELATIVE-EQUITY-CONTINUATION-RESULTS-20261108.md); giữ baseline2019/22, không bot/edge|
|R027|News-surprise continuation|event|Historical source reviewed; intraday known-at/access chưa admitted|0|[Source review](FOMC-SURPRISE-SOURCE-RESULTS-20261109.md); chưa ownoutcome|
|R028|News overreaction reversal|event / R027|Historical source reviewed; intraday known-at/access chưa admitted|0|[Source review](FOMC-SURPRISE-SOURCE-RESULTS-20261109.md); chưa ownoutcome|
|R029|Currency carry|carry|long_history_or_multi_data|0|Chưa outcome riêng|
|R030|Carry + trend|carry / R029|long_history_or_multi_data|0|Chưa outcome riêng|
|R031|Long-horizon value / PPP|value|long_history_or_multi_data|0|Chưa outcome riêng|
|R032|Value + momentum|value / R031|long_history_or_multi_data|0|Chưa outcome riêng|
|R033|Cross-sectional FX momentum|cross_section|Pilot3FX MOM1: gross/net âm, không giữ exact adaptation|0|[Pilot results](FX-CROSS-SECTION-PILOT-RESULTS-20261108.md); chưa account/prop/OOS|
|R034|FX factor-residual reversion|cross_section / R033|Stockmethod đã đọc; chưa chuyển được method/data sang FX|0|[Method admission](RESIDUAL-REVERSION-METHOD-ADMISSION-20261109.md); deferred, chưa ownoutcome|
|R035|Cointegrated FX spread|cross_section / R034|GBP/AUDformation2018/21 chưa đạtprefilter, chưa bot|0|[Formation results](FX-PAIR-FORMATION-RESULTS-20261108.md); khôngPnL/prop|
|R036|Volatility targeting / exposure cap|risk_modifier|component_only|0|Chưa outcome riêng|
|R037|Fixing composite3slots|fixing_flow / R022|Các exact FX versions đã gác sau cost screen|1|[624cases/decision](EURUSD-CATALOGUE13-RESULTS-20261108.md); không loại cả family|
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
|R054|Gold BUY00–08UTC|gold_session_flow|Gác exactpriceprobe;0/15stressyears dương|0|[Session results](GOLD-SESSION-COMPONENT-RESULTS-20261108.md);chưaSL/account|
|R055|Gold SELL10:30–15London|gold_session_flow|Gác exactpriceprobe;0/15stressyears dương|0|[Session results](GOLD-SESSION-COMPONENT-RESULTS-20261108.md);khôngLBMAprice/SL/account|
|R056|PreECB sessionRMS20x2 stop|fixing_flow /R021|Totaldương nhưng2/4stressblocksâm;khôngretained|1|[Results](PRE-ECB-SESSION-RISK-RESULTS-20261108.md);toolingcoarseprototype,chưanative/prop/OOS|
|R057|GBPUSDPreECB02NY→14Berlin|fixing_flow /R021|Stress+880,2pip nhưng9/15positiveyears/2negativeblocks;khôngretained|0|[TwoFXresults](TWO-FX-PRE-ECB-COMPONENT-RESULTS-20261108.md);sourceH1Openproxy,chưabot|
|R058|AUDUSDPreECB02NY→14Berlin|fixing_flow /R021|Stress−7.330pip/1positiveyear;khôngretained|0|[TwoFXresults](TWO-FX-PRE-ECB-COMPONENT-RESULTS-20261108.md);missing/crossedsourcegiữrõ|
|R059|GBPUSD BUY08–16NY|session_flow /R023|Phí cao −1.738,6pip; 7/15 năm dương, không giữ|0|[Local-flow results](LOCAL-FLOW-TWO-FX-RESULTS-20261108.md)|
|R060|AUDUSD SELL10–16Sydney|session_flow /R023|Phí cao −13.405,8pip; 1/15 năm dương, không giữ|0|[Local-flow results](LOCAL-FLOW-TWO-FX-RESULTS-20261108.md)|
|R061|NASDAQ100 H4SMA20/80|trend_breakout /R002|Không giữ exactrecipe: stress2019+240,59/2022−77,36USD,7/14trades|1|[Pilot results](NASDAQ100-H4-SMA-RESULTS-20261108.md); coarse/gap limits, chưa prop|
|R062|NASDAQ pre-FOMC23h|scheduled_macro_premium|Không đạt2019;2022dương, chưaaccountpolicy|0|[Component results](FOMC-NASDAQ-COMPONENT-RESULTS-20261108.md);64costcases/128quotes reviewed|
|R063|NASDAQ cash RSI3+IBS05|equity_daily_reversion /R050|Không giữ: stress2019−2,97/2022−486,42USD/unit,9/21trades|0|[Component results](NASDAQ-CASH-RSI-COMPONENT-RESULTS-20261108.md); chưaSL/account/prop/OOS|
|R064|NASDAQ cash first→last30|equity_close_momentum /R051|Không giữ: stress−481,64/−1.969,99USD/unit, kém longcontrol cả2years|0|[Results](NASDAQ-INTRADAY-MOMENTUM-RESULTS-20261108.md);413resolveddays/1.652cases, chưaaccount/prop|
|R065|NASDAQ opening5 direction/10R|cash_opening_direction|Gác exact recipe: conditional2019 stress −925,72→−914,80USD; original2019 vẫn unknown, chưa qualified|1|[Bounds review](NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md); giữ [exact datarevision](NASDAQ-OPENING5-ORB-DATA-REVISION-RESULTS-20261109.md)|
|R066|NASDAQ noise14 first daily break|equity_intraday_momentum / R048|Gác: conditional2019 −214,67/−250,47USD;2022 +217,58/+198,44USD; chưa qualified|1|[Results](NASDAQ-NOISE14-RESULTS-20261109.md)|
|R067|Gold/silver relative-value formation|precious_metals_relative_value / R035|Gác fixed formations: nguồn đủ503dates, cointp2018=0,7439/2021=0,0933; chưa PnL|0|[Formation results](GOLD-SILVER-FORMATION-RESULTS-20261109.md)|
|R068|Gold forest stopped/costed labels|trained_return / R039|Đã train/review,0tín hiệu đủ ngưỡng;gác exactrecipe|1|[Results](GOLD-ML-SL-LABELS-RESULTS-20261109.md);2019/2022zero trades,khôngedge|
|R069|Gold stopped-label forest shuffled control|falsification / R068|Control đăng ký cùngR068;0tín hiệu đủ ngưỡng|1|[Results](GOLD-ML-SL-LABELS-RESULTS-20261109.md);khôngindependentedge|
|R070|NY EURUSD MA4 reversal|session_conditioned_reversion / R003|Gác exact recipe theo conditional sensitivity; giữ H1 negatives/strict annual N/A|3|[Conditional review](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md); strict unknown không bị clear|
|R071|NY EURUSD MA4 momentum control|falsification / R070|Gác exact recipe theo conditional sensitivity; giữ H1 negatives/strict annual N/A|3|[Conditional review](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md); strict unknown không bị clear|
|R072|NY EURUSD MA4 reversal15min|session_conditioned_reversion / R070|Gác exact recipe theo conditional sensitivity; giữ H1 negatives/strict annual N/A|2|[Conditional review](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md); strict unknown không bị clear|
|R073|NY EURUSD MA4 momentum15min control|falsification / R072|Gác exact recipe theo conditional sensitivity; giữ H1 negatives/strict annual N/A|2|[Conditional review](NY-FX-GAP-SCENARIOS-RESULTS-20261109.md); strict unknown không bị clear|
|R074|NASDAQ overnight → first-half reversal|equity_opening_reversion|Gác exact component: stress −1.166,74 / −2.359,71 USD/unit|0|[Review](NASDAQ-OVERNIGHT-REVERSAL-RESULTS-20261109.md); 499 ngày, chưa account/prop/OOS|
|R075|S&P overnight → first-half reversal|equity_opening_reversion / R074|Gác exact transfer: stress −521,82 / −770,05 USD/unit|0|[Review](US500-OVERNIGHT-REVERSAL-RESULTS-20261109.md); 498 ngày, chưa account/prop/OOS|
|R076|S&P rest-of-day → last-half momentum|equity_close_momentum / R051|Gác exact component;2019 known-partial,2022 âm|0|[Review](INDEX-REST-OF-DAY-RESULTS-20261109.md); chưa account/prop/OOS|
|R077|NASDAQ rest-of-day → last-half momentum|equity_close_momentum / R064|2019 âm,2022 chuẩn dương/stress âm;gác exact|0|[Review](INDEX-REST-OF-DAY-RESULTS-20261109.md); chưa account/prop/OOS|
|R078|US500 firsthalf/ROD consensus|equity_close_momentum / R076|Hai năm âm sau phí, gác exact|0|[Results](INDEX-CONSENSUS-RESULTS-20261109.md); parent reuse, chưa account/prop/OOS|
|R079|NASDAQ firsthalf/ROD consensus|equity_close_momentum / R077|Hai năm âm sau phí, gác exact|0|[Results](INDEX-CONSENSUS-RESULTS-20261109.md); không reverse mask rescue|
|R080|US500 EU-open uncertainty resolution|equity_overnight_uncertainty_resolution|Knownnetâm,2019coverage thiếu;khôngretained|0|[Results](US500-EU-OPEN-COMPONENT-RESULTS-20261109.md)|
|R081|US500 prior closing-pressure conditional EU-open|equity_inventory_reversal_price_proxy /R080|Knownnetâm,selected2019coverage thiếu;gác exact|0|[Results](US500-INVENTORY-CONDITION-RESULTS-20261109.md);relatedvariant,chưaaccount/prop/OOS|
|R082|WTI Wednesday reaction→late conditional component|event-price momentum / R027|Không retained;2019unknown/2022net âm|0|[Results](WTI-WEDNESDAY-COMPONENT-RESULTS-20261109.md);retrospectivecalendar,không accountpolicy|
|R083|WTI Wednesday reaction→settlement conditional component|event-price momentum / R082|Không retained;đủ88days,stressâm2years|0|[Results](WTI-SETTLEMENT-COMPONENT-RESULTS-20261109.md);strict/endpointidentical,noaccountpolicy|
|R084|USDJPY Tokyo calendar component|fixing_flow / R021|Mua chính không đạt;follow-up bán R085 cũng không đạt|0|[Results](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md);32books/139dates,noaccountpolicy|
|R085|USDJPY postfix temporal extension|fixing_flow / R084|Không đạt;6/13newyears dương,2/4blocks âm|0|[Results](USDJPY-POSTFIX-EXTENSION-RESULTS-20261109.md);240books gồm discoveryreuse, chưaSL/account/prop|
|R086|US500 pre-FOMC past-price momentum|event / R062|Không qua stressgate cả2năm;funding đích unknown|0|[Results](US500-FOMC-PRICE-MOMENTUM-RESULTS-20261109.md);32books/256cases, noaccountpolicy|
|R087|Japan cash reaction sau phiên Mỹ|crossmarket_flow / opening-reversal related|Known net âm;2019coverage73,73%,202298,31%;fullannualunknown|0|[Results](JAPAN-US-CASH-REACTION-RESULTS-20261109.md);485rows/20books,JPYunit/noaccountpolicy|
|R088|EURUSD sau FOMC12–24h|event_session_flow / R021|Stressnet dương cả2năm;eventincrement2022 khôngđạt|0|[Results](EURUSD-POST-FOMC-RESULTS-20261109.md);32windows/192cases,noSL/account/prop/OOS|


## Cách đọc và lịch sử các batch đầu

Discovery4/6/7 historical screens đã completed; MLreal policies thất bại, giữ controls/negatives. Asia2023/2024 native review đã completed; Londonstresscả2years còn incomplete do timeout. [Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md) đã624/624cases,0/24retained trên observedhistory2010–2022. R048noise14 là cơchế/asset khác: [kết quả](US500-NOISE-RESULTS-20261108.md)2022dương nhưng2023/24âm ởcảcosts,khôngretained. Không writer còn chạy trongcácattempts này. Không dispatch lại screens hoặc gọi2023/2024cleanOOS.2025+vẫn đóng.

Nguồn chỉ cho cơ chế/định nghĩa/phương pháp; code và datalicenses cần kiểm trước import. Các adaptations H1/SL/holding không phải exact paper replication. Fixed-window variants, ORBs và MLcontrols có quan hệ; số versions không là số bằng chứng độc lập. Public payout/case study tay không xác nhận bot edge.

## Nguồn và ngày kiểm

Chỉ nâng ngày cho nguồn thực sự đọc lại; top updated_on không có nghĩa mọi paper đã refresh hoặc full-method audit.

- **NY125** — [Currency Orders and Exchange-Rate Dynamics](https://www.newyorkfed.org/research/staff_reports/sr125.html). 2026-11-08; official summary refreshed, không xác nhận exact prior-day/retest recipe.
- **NY150** — [Stop-Loss Orders and Price Cascades in Currency Markets](https://www.newyorkfed.org/research/staff_reports/sr150.html). 2026-11-07; Stop cascade mechanism; not a compression recipe.
- **BOC48** — [Foreign Exchange Fixings and Returns Around the Clock](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/). 2026-11-07; Fix-related drift/reversal; full method/clock must be read before replication.
- **SNB04** — [Intraday patterns in FX returns and order flow](https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04). 2026-11-08; fullPDFTable1/2/§2.2 đã đọc, [session probe](LOCAL-SESSION-RESULTS-20261108.md) khác EBSsample/chi phí, không bảo đảm bot hiện tại có lợi thế.
- **AQR-TS** — [Time Series Momentum: Original Paper Data](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data). 2026-11-08; 12-month lookback/monthly holding; futures/forwards, not H4 CFD.
- **AQR-VM** — [Value and Momentum Everywhere: Factors, Monthly](https://www.aqr.com/Insights/Datasets/Value-and-Momentum-Everywhere-Factors-Monthly). 2026-11-07; Long/short multi-market factors; not EURUSD-only replication.
- **BIS366** — [Currency Momentum Strategies](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies). 2026-11-08; full PDF method §2–4.1/4.2 read, không full appendix audit; [pilot3FX](FX-CROSS-SECTION-PILOT-RESULTS-20261108.md) khác broad universe/forwards của paper.
- **CARRY** — [Carry Trades and Currency Crashes](https://economics.princeton.edu/working-papers/carry-trades-and-currency-crashes/). 2026-11-07; Carry mechanism and negatively skewed crash risk; CFD swaps not policy rates.
- **NEWS** — [How Economic News Moves Markets](https://www.newyorkfed.org/newsevents/news/research/2008/rp080908). 2026-11-07; Announcement surprise responses; does not validate continuation/reversal rules.
- **TV-RSI** — [Relative Strength Index](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/). 2026-11-07; Indicator definition only; no profit evidence.
- **TV-BB** — [Bollinger Bands](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/). 2026-11-07; Indicator definition only; no profit evidence.
- **QC** — [Backtesting Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide). 2026-11-07; Workflow reference in AI plan; not strategy profitability evidence.
- **LOCAL** — [Naqex exact eight candidate rules](../../projects/trader/foundation_v2/docs/FOREX-RESEARCH.md). 2026-11-07; Exact implemented rules/history; published literature is mechanism context only.
- **SKLEARN** — [Scikit-learn preprocessing and time-series validation](https://scikit-learn.org/stable/common_pitfalls.html). 2026-11-08; Method only, not forex profitability evidence

- **GGR** — [NBER pairs trading](https://www.nber.org/papers/w7032). 2026-11-08; official stock-distance summary only, PDF403; không FXcointegrationedge.
- **SM-COINT** — [statsmodels coint](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html). 2026-11-08; docs/installed0.15.0source; fixedmethod contract, không profitabilityproof.

- **LEBARON-NYFX** — [Foreign Exchange Reversals in New York Time](https://people.brandeis.edu/~blebaron/wps/fxnyc.pdf). Fullprimarymethod§2–4/Table3/7read09Nov2026;EBS2003–06 không currentCFD/SL/DST/executionproof.

- **LIU-TSE-OVERNIGHT** — [Overnight returns of stock indexes](https://www.sciencedirect.com/science/article/pii/S1059056016301563). 09/11/2026, primary search-served abstract/introduction, direct 403; không full method hoặc CFD profit proof.
- **IWANAGA-SAKEMOTO-OPENREV** — [Overnight return and first half-hour](https://www.sciencedirect.com/science/article/abs/pii/S1062940826001294). 09/11/2026, primary search-served abstract và author landing; recent decay/stress dependence, chưa full method.

- **BALTUSSEN-ROD** — [Hedging demand and market intraday momentum](https://academicweb.nd.edu/~zda/intramom.pdf). Đọc primary method/cost sections09/11; chưa full appendix replication, CFD/latency adaptations và không actual gamma observation.
- **BOND-MURAVYEV-EUOPEN** — [Cambridge article](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/market-return-around-the-clock-a-puzzle/089E33AC0B4D3B9A02CBA31EDF6505B3), official appendix clock/baseline đọc09/11; futures→CFD/calendar/M1 adaptation, không VIX/prop/OOS proof.

- **WEN-EIA-USO** — [Primary accepted manuscript](https://digital.library.adelaide.edu.au/server/api/core/bitstreams/aee73b81-111e-4bef-9e0e-7b1164f368a1/content), §2.2/footnote6 đã đọc09/11; ownWTItransfer khôngpaperreplication hoặcPITcalendarproof.

- **CME-WTI-SETTLEMENT** — [SER4867](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-4867.html), 2009effective/2017filing/normalprocedure đãđốichiếu09/11; khôngCFDsettlementmapping hoặcalpha.

- **WANG-FX-FOMC2018** — [Wang thesis, chapter1](https://www.olsendata.com/data_products/client_papers/papers/201808-MinhoWang-EssaysOnCurrencyMarkets.pdf), primaryPDFpages13–50 đọc09/11;midpoint/excessreturn/multi-currency, khôngEURUSDCFDnetreplication.
- **XU-FX-FOMC-DISCUSSION2022** — [Xu discussion11/03/2022](https://www.nancyxu.net/_files/ugd/efd0b7_99257144559d4b61b592862dc067edfe.pdf),17pagesđọc09/11;12–24h vàjump/trendcritique, khôngcurrentfullpaper hoặccombinedpredictor.
