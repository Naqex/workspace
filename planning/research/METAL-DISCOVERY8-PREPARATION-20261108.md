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
