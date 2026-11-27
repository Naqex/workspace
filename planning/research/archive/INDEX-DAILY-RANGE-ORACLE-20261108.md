# D1/M1 US500: xác minh low ngày18/10/2022 trước dùng D1

ProviderD1Bid/Ask có3671bars2011-09-18→2024-12-31,daystart00:00UTC.
Đối chiếu310days2022 vớiM1:309exactOHLC;18/10khác low cảhai side:
BidD13692 vs M1low3685,530;AskD13692,095 vs M1low3686,068. LowM1 ở15:38UTC,
khác minute15:24 đãmissing. Vì vậy **chưa được quy nguyên nhân cho missingbar**
và chưa chấp nhận D1range cho strategyPnL/SL. Không sửa rawgiá hoặc bỏ ngày.

Diagnostic mới đăng ký trước đọc outcome:
existingprovider/package1.51.1/optionsreviewed,3requests `usa500idxusd`:
ticks18/10/2022 15:38→15:39UTC exclusive (1request),H1Bid vàAsk cùngUTCday
18/10→19/10exclusive (2requests). Scope chỉdatumoracle,khôngtradingstrategy.
Deadline120s,retry0/batch2/pause300ms,WAFoff/tokenfalse,CANCELgiữarequests;
403/error/emptydừng,khôngauth/bypass/fallbackprovider. Hash/source/protocol/
runtime/raw giữ riêng;không2025+/broker/model calls.

Kiểm ticks raworder/positive/grid/spread/scope; derive bid/askmin/max trong
exactminute,so với M1row. H1samehourlow/whole-dayrange so với M1/D1. Sameprovider
kháctimeframe không là independentfeed; oracle chỉxácđịnh phạm vi nhấtquán.
Nếu D1rangekhông đángtin,khôngpromote chỉvìclose/endpoints khớp. Cần nguồn
aggregation khác được validate hoặc giữ dataset chưa đủ năng lực.
