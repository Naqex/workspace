# US500 provider D1 — capability trước numerical study tiếp theo

Campaign vẫn tiếp tục sau hai adaptation daily cash-session. Chuẩn bị input
cho cơ chế dài hơn, chưa signal/PnL. Existing pinnedDukascopy-node1.51.1,
transport/license/source review giữ nguyên; không cài mới hoặc provider mới.

Exact2requests: `usa500idxusd`, timeframe`d1`, Bid vàAsk,
UTC01/01/2011→01/01/2025 **exclusive**. Chỉ provider D1,khôngtick/M1bulk,
không2025+. Data trước2022 là retrospective extension sau xem2022–24,
không tự gọi cleanOOS. WAFoff/tokencachefalse/retry0/batch2/pause300ms,
deadline180s/CANCEL giữarequests;403/error/empty dừng,khôngbrowserbypass.

Giữ raw/hash/seals/sourceprotocol/package/runtime/progress. Kiểm scope,
strict order, day starts và sideOHLC/volume/grid0,001. Provider D1 là source
tradingday definition, **không NYSEcashday**. Phải đối chiếu một số2022days với
rawM1 đã có để xác định bar boundaries và quote basis trước strategyoutcomes.
Không dùng dailyhigh/lowBidAsk để suy observedmidpath hoặc certifySL/DD.

Nếu aggregation không khớp thì giữ diagnostic, không sửaclock/rawgiá để ép
pass; chưa nhận dataset cho study. Những sourcebars bắt đầu2011 có thể là
metadata hơn là usablecoverage; chỉ kết luận sau fetch thật. Không OrderSend,
OrderCheck/model calls, account mới hoặc paid data. Các studies cũ không sửa.
