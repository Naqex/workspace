# R064: NASDAQ first-half → last-half, frozen price-component screen

Tiếp [method admission](NASDAQ-INTRADAY-MOMENTUM-METHOD-20261108.md), đăng ký
trước numeric. Adaptation liên quan R051 đã âm trên US500, không independent
edge hoặc paper replication. Không sửa/gộp outcome R063 để rescue family.

## Đầu vào, tín hiệu và timing

Reuse exact8books/calendar của `execution-v1/nasdaq-m1-history-v2`: resultSHA
`3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`, reviewSHA
`8b0bced9723138d52242552a66ed74c33f5a43d8d3013288b515d2db7c4b9703`.
Warmup Nov–Dec2018/2021, development2019/2022; không2025+/network/broker.
Role/exposure giữ development đã dùng, không cleanOOS. Không sửa raw/quality.

Candidatecomponent `nasdaq-cash-firstlast30-price-component-v1`:

- Mỗi cashday có một row; halfday210minutes skip theo calendar trước outcome.
  Regular390minutes mới có thể signal. Previouscashclose là BidClose của
  expected last M1 đúng previouscashsession, kể cả halfday. Không dùng last
  available quote khi endpoint thiếu.
- Firsthalf BidClose09:59, known10NY; so previouscashBidClose: cao hơn BUY,
  thấp hơn SELL, bằng nhau không trade. Previous14consecutivecashTR phải đủ
  và dương theo pure parent `index_close_momentum.plans_for`; không cần full
  currentday để quyết định. ATR readiness giữ để transfer parent nhất quán,
  component chưa dùng stopdistance. Signaloracle Fraction dựng độc lập.
- Decision15:30, entry exact M1Open15:31; scheduledexit decision15:58,
  exit exactM1Open15:59. Source Open là intervalproxy, không executable tick
  đúngmillisecond. Nếu endpoint thiếu/crossed: unresolved row giữ denominator,
  không forcefill/skipbadtrade/nextquote hoặc tự cộng0 thành PnL đã biết.
- Không SL/TP/trailing/sizing/margin/account balance. One hypothetical unit
  worth1USD/priceunit. BUY entryAsk/exitBid, SELL entryBid/exitAsk; không đổi
  side sau xem outcome. Fullpath M1availability ghi riêng, khôngno-gapclaim.

## Economics, control và gate đã khóa

Reuse NASDAQ declared market/cost primitives, không US500 financial identity.
Observedspread, slip0,25/0,75priceunit/side, commission0. Entry/exit cùng ngày,
khôngplannedfunding; unresolvedexit không gọi là flataccount hoặc funding0
đã xác minh cho actualposition. Quote volume không exchangevolume; target
specs/delay/swaps/dividends và executablepaths vẫn chưa được chứng nhận.

So primary với **always-long trên chính same signal-day mask và endpoints**,
không chọn control theo giá. Null control không mở exposure, net0. Control
không tự được promote nếu primary fail. Perday ×2costs×primary/longcontrol;
2nullsummaries cho2years. Không xem các cost/controlcases là independenttrials.

**Retain để nghiên cứu tiếp** chỉ khi mỗi year:>=100plannedprimarysignals,
>=98%signaldays có đủ cả2endpoints, stressprimary knownsum>0 và
stress(primary−alwayslong)>0 trên commonresolvedmask. Báo unresolved và
concentration, không gọi knownsum là fullnet khi còn endpoint unknown.
Gate là workload triage đã chọn trước, không thống kê chứng minh edge.
Nếu fail: giữ negative exactrecipe, không tune clock/side/ATR/fees/control.

## Thực thi và đối soát

Reuse source proofs/quality và input hashes; đọc source M1 một lần mỗi year.
Code/fixtures xong trước economicrun: overnight-included sign, past14TR,
priorhalfday, futuresource mutation không xóa entry, DST/halfday, delayed
exactfills, BUY/SELLcosts, missing/crossed retention, sharedmask/control,
sampledenominator/duplicateyear/falseauthority.

Output mới `execution-v1/nasdaq-intraday-momentum-component-v1` dưới private
campaignroot;1writer/PID/progress/events/CANCEL/failure/deadline120s, pins và
sourcesnapshots trước numeric. Reviewer separate Fraction/causal signal,
source endpoint lookup, rowcensus/financial/controlsummaries và mutation
wrongside/quote/time/missingrow/authority/hash. Sameagent/provider, không
independenthuman/modelreview. Hashcode khác reviewreceipt phải ghi đúng loại.
Scope chỉ economicscreen, chưaaccountpolicy/SL/prop/OOS/forward/handover/C1C2.
