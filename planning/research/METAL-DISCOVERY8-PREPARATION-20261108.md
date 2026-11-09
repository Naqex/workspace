# Discovery8 preparation — mở rộng asset, chưa numerical strategy outcome

Hai EURUSDsurvivors annualnative vẫn chạy; không sửa product source đã pin.
Bootstrapconditional2023/2024 của cả hai đều bao gồm0, chưa đủ khuyên challenge.
Không giải quyết bằng mở nhiều lần holdout hoặc tune lại hours trên cùng data.

## Vì sao mở rộng và scope

Catalogue QDMlocal08/11 cho thấy XAUUSD_TW có M1cache2003–2026, không tickcache
XAUUSD. EURUSD mới là tickasset đã hỗ trợ. Chuẩn bị XAUUSDdevelopment2020–2024
để xem nhóm trend có hợp hơn; không kết luận gold tốt hơn trước outcome.
Chỉ reuse QDMCLI/cache đang có license, export local UTC2020.01.01–2024.12.31
vào output mới. Không update/download/fullhistory hoặc mở2025+, không đọc
licensefiles/accounts, không broker/networkprovider mới hoặc API/LLMorders.

[AQR original TSMOM](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data)
là cơ chế tham khảo trend đaasset dài hạn; **không chứng minh H4CFDgold có edge**.
Không tải/import paper dataset hoặc external EAcode.

Export header Date,Time,Open,High,Low,Close,Volume; bind CLIversion/source symbol/
UTC/dates/command/hash/count/ordering/OHLC/gaps. Chưa chứng thực OHLC là Bid/Ask/
mid, do đó chưa tạo quotes hoặc tuyên bố fulltick/BidAsk/backtest từ M1 này.
Metadata cache ngày cuối2026 không có nghĩa được đọc giá2025+.

## Contract cần giải quyết trước numerical screening

Reuse generic instrument/cost/execution core. Không gọi XAU là EURUSD hoặc
dùng100.000units/lot và0,00001tick của FX. Proposed declared scenario (chưa
brokerverified): XAUUSD/USD,100oz/lot,tick0,01,minimumlot/step0,01,leverage10,
reference spread0,30/slippage0,10eachside/commission2,50USDperlotperside,
stressspread0,60/slippage0,20, financingdebit20/40USDperlotpernight Wed×3 at22UTC.
Pricebasis và historicalcost unknown; cần exact immutable spec trước run.
Risk25USD, daily100/overall500, initial10k giữ nguyên; không đạtminlot thìskip.

Đợt đầu dự kiến fixed Donchian20/10, SMA20/80 và Z20±2/time6 trên H4 đóng,
SL2WilderATR14; **chưa đủ authority đăng ký numeric execution**. Phải freeze
exact generic identities/timeframe/boundaries/splits/costs/selection và kiểm
gold sizing/BidAsk/TP-SL/rounding/gaps/state/accounting trước đọc outcomes.
Đây là phần preparation độc lập, không đổi activeEURUSD protocols hoặc coi
barapproximation là nativeprop/DD qualification. Nếu tool/spec không đáp ứng,
ghi capability gap, không monkeypatch asset identity hoặc viết simulator khác.

## Preparation đã hoàn tất

Export/cache validation49,93s,1.773.334M1rows,first2020-01-01T23:00Z,last2024-12-31T21:58Z,hash834d4678f8e2a45914119854d5fe7d3ec45a1281c81d4952830fc76a65f636fb. QDM125.2692; CLIsha/command/UTC/protocol/rawhash/count/order/OHLC/gaps ở private metal-discovery8-preparation/provenance-review.json. Maximum adjacentgap274560s, giữ nguyên, không bù. Không strategyoutcome hoặc syntheticquotes đã tạo. **Capabilitygap xác minh:** ForexPilotSnapshot và sizing/reconcile hiện đóng vào EURUSD/100000units; phải mở rộng typedinstrumentcontract và regression trước tính XAUoutcomes, không chỉ đổi tênsymbol. Productsource78a8397f vẫn giữ nguyên trong lúc annualjobs chạy.

Minimumlot không trade được phải phân loạiinconclusive/infeasibleởsize10k, không bác bỏ cơ chế ở mọi accountsize. Nếu sau này so25k/50k thì giữ risk0,25% và đăng ký sizing/profile riêng; không tự mua account hoặc tăngriskpercent.

## Kiểm tra độc lập exporterM1 bằng ticks đã consumed

Engineeringfixture EURUSD03/01/2022:1.425/1.425M1OHLC khớp **Bid** từ65.215observed ticks, UTCbar-start timestamp (offset0). Ask/Mid0exact; timestamp−60s chỉ15/1414exact. Private m1-basis-diagnostic-v1 giữ frozen scope/command/inputhash/results, không strategyoutcome. Chứng minh cho sampleEURUSD/exporter hiện tại; chưa tự chứng thực Bid/AskXAU, nhưng không nên mặc định QDMM1làmid. Muốn dùng XAU cần same-asset quote fixture hoặc ghi pricebasisassumption đúngscope.

## Bổ sung fixture quote có giới hạn trước kiểm cùngasset

QDMupdate có thể tải fullhistory, nên không gọi choXAU. Để xác minh Bid/Ask/time/grid của M1XAU, cho preparation này query duy nhất XAUUSDticks03/01/2023UTC (to04/01exclusive) từ cùng publicDukascopy provider, không2025+. Reuseopensource dukascopy-node1.51.1 ở isolated.runtime/research-data: exactofficialrepo/npm/SRI/tar manifest+source review, lock23MIT/ISC/Apachedeps, installscriptsdisabled. WAFmodeoff/token-cachefalse, không browserinstall/recovery hoặc globaldata. Plain403/timeout dừng, không bypass/auth/muaapi. Đây là datafixture, chưastrategyPnL. Phải giữ native/sourceM1quotegrid khác targetbrokergrid nếu quan sát cho thấy khác, không roundrawprices để ép đúng declaredspec.

## Sameasset quote fixture hoàn tất — trước strategy outcomes

Dukascopy-node boundedrequest trả206.215ticks03/01/2023UTC, khôngsort/dedup; hash29fe3fb52252b0b13fe4f86dda5f06edd977d54ce317eab922d39fe8030dbefe.1.380/1.380M1candles QDM cùng ngày khớp BidOHLC/UTCbar-start exact; Ask/Mid0exact. Sameprovider/twotransports, không independentmarketfeed. Tickquotes đều khớpgrid0,001 và tất cả206.215records có ít nhấtmột side offgrid0,01; do đó proposedstudytick0,01 ở trên **bị thay thế bằng sourcegrid0,001**, brokergrid vẫnunknown. Không roundrawtick để ép contract. ObservedspreadUSD/oz median0,330,p99=0,477,max1,646 trong1ngày, không toàn5years.

Trước numericalscreen, tăng declared spread lên0,50reference/1,00stress (prior0,30/0,60 superseded), giữslippage0,10/0,20 vàcommission/financing nhưtrên. Thayđổi này dựa trên price/costmetadata trước strategyoutcome, không để cứu PnL; không nói fixedspread bao hếttails. Exactprotocol mới phải pin values và PricebasisBid/next-open semantics. Supplychain lock/review ở.runtime/research-data được giữ private, WAFoff/tokenfalse, khôngbrowser/globaldependencies. XAUextension sẽ ở isolatedmanagedworktree từTrader78a8397f; không sửa code đang chạy ởD:.
