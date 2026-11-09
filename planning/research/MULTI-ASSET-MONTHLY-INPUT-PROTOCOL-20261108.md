# Bộ quan sát tháng EURUSD/Gold/US500 — trước strategy outcomes

Tiếp [source admission](MULTI-ASSET-TREND-DATA-RESULTS-20261108.md). Đăng ký
chuẩn bị dataset nhỏ có version từ raw/cache đã có, không backtest strategy,
không tính momentum/volatility/PnL hoặc sửa các source/cost/risk gates cũ.

## Phạm vi và contract

-2013–2024,144NYSEcalendar months×3markets×2eventroles=864records. Giữ mọi
  missing/stale; không mở2025+. RawGold2009.11–2024 đã consumed:hash cả file,
  chỉ lấy records2013–2024. FXannualfiles và US500canonicalview giữ nguyên.
- `signal_close`: cutoff=close của **NYSEsession cuối tháng**, kể cả early
  close. US500/Gold cần đúng source M1 cuối cùng trước cutoff:barstart=cutoff−60s,
  close known-at=cutoff. EURUSD cần last observed tick **strictly before**
  cutoff, age≤60s. Đây là commonclock choice trước outcome, không FX/month-end
  benchmark replication; cuối thángNYSEclosed có thể khác ngàyFXcuối tháng.
- `rebalance_observation`: **10:00 America/New_York của NYSEsession đầu tháng**.
  Chọn giờ tròn sau30phút mở cash để dùng cùng clock và source-bound firstquote
  H1 đã có, giảm repeatedticks scan; không chọn theo PnL hoặc gắn vào một
  strategy đã có. Đây là dữ liệu cho futureexecutionproxy, chưa quyết định
  chiến lược phải trade thời điểm đó. EURUSD:first observed tick≥target,lag≤60s;
  US500/Gold:M1open đúng target. M1firstquote có timestampinterval[open,open+60s),
  chưa là actualtickfill/latencyproof; không dùng executionproxy làm signal.
- US500/EURUSD giữ observedBidAsk đúng source; Gold chỉ observedBid, `ask=null`,
  `observed_ask=false`. Không tự chèn spread hoặc dùng Askgiả định từ H1cache
  Gold. DeclaredAsk/costs chỉ được thêm bởi economicprotocol riêng sau đó.
- Đơn vị quoteUSD:EURUSD USD/EUR,Gold USD/oz,US500 USD/indexpoint. Account
  lot/contractsize/margin/swap không suy từ dataset này. Không cộng cashPnl
  các annualbooks hoặc nhân ngân sách theo số thị trường.

## Reuse và sự khác nhau giữa producers

FX2013–2022:reuse exact native `load_coarse_hours` với raw hash,currentproducer/
runtime bindings và CoarseHourinvariants; chỉ lastquote của giờ trước cutoff
và firstquote tại rebalancehour. Metadata đã xác minh10caches tương thích.
Không sửa binding/cache hoặc rebuild chỉ để đổi nhãn source.

FX2023–2024 caches dùng version`replay_tick_execution.py` cũ, kháccurrent.
**Không ép currentloader nhận chúng.** Explicitraw-sparse pass dùng rawsha,
date/order/sequence và selectedquotes để tạo projection mới, không regenerate
H1 hoặc chạyoldcode. Locator từ registrations đã freeze, cùng provider đã có.
Giữ oldcache và producersnapshots; không invalidate economicartifacts cũ.

Gold:reuse acceptedraw hash/quality, streaming sparseM1pass; giữ nguồnvolume0,
schema/date/order và kiểm OHLC/grid/volume của selectedbars. Không normalize
rawbytes hoặc invent quotes. Source-only US500:reuse proof/quarterseals đã kiểm;
join exact signal/rebalanceM1, không asof120s vì probe trước không thêm coverage.

## Kiểm chứng, status và chi phí thực hiện

- Fixture timestamps/DST/earlyclose, last-before/first-after, stale/missing,
  futureprefix, GoldAskunknown và data-role không lẫn với fillauthority.
- Kiểm fullhash ở source load/sparsepass; caches có producer/runtime/checksum/
  count/order guards. Giữ input/protocol/source/runtime/normalizedoutput pins.
  Không bỏ nativechecks để tiết kiệm I/O. Quan sát nhỏ sau chuẩn bị phải được
  seal/schema-check; future studies có thể dùng frozenprojection để tránh
  parse toàn raw một lần nữa, giữ provenance chứ không tuyên bố raw mới verified.
- Một writer,deadline900s,CANCEL/status/events/phasewall+CPU,attempt mới,không
  network/provider/account/model/broker calls. Không tự retry ở output đã có;
  lỗi giữ source và mọi sealedpartial trước quyết định recovery riêng.
- Output `execution-v1/multiasset-monthly-input-v1`:manifest,records,quality,
  status/events/source-snapshot/result. Recordcount864 là census, không số
  trades/independent observations hoặc đủ evidence edge/prop.

Sau dataset mới freeze R010exactrule/volestimator/warmup/weights/caps/cost/
financing/stop/quality và tiêu chí trước numeric; periods đã consumed,
không cleanOOS. Unknown targetcost giữ unknown/declaredscenarios, không giảm
phí cũ, tự dùng10%volpaper làm propbudget hoặc tự mua account/holdout/broker.
