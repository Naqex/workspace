# R080: unconditional US500 EU-open component, đăng ký trước outcomes

[Method](EU-OPEN-AND-OIL-METHOD-20261109.md) và [8-date source pilot](EU-OPEN-SOURCE-PILOT-RESULTS-20261109.md)
đã đủ để khóa price-component experiment, chưa edge. R080
`us500-euopen-2330-0330-price-component-v1` hỏi cơ chế uncertainty resolution,
khác close-momentum prediction của R076/R078 đã gác. Không gọi CFD transfer
là futures replication hoặc independent/unseen confirmation.

## Cơ chế, calendar và clock

Theo primary Cambridge appendix được đọc ở method report: baseline full
EU-open mua đầu, đóng cuối. Chỉ **một fixed window**, không so grid những
subperiods/VIX conditions rồi chọn. Không có admitted VIX nên không dựng
conditional model từ headline. Không benchmark ROI futures headline với CFD.

Development 2019/2022 đã consumed, US500 source-only M1 Bid/Ask/calendar có sẵn.
503 cashday rows: 252/251 năm, 249/250 regular; halfdays skip theo calendar
biết trước, chưa futures trading-calendar equivalence. Nhãn theo exit date.
Mỗi regular day luôn planned BUY, không cần predictor/ATR/history readiness.

Decision entry 23:30 America/New_York ngày trước; entry M1Open23:31. Scheduled
exit decision03:30 ngày ghi nhãn; exit M1Open03:31. Local DST/UTC conversion và
Sunday→Monday đúng ngày, không last available bar/previous trading-day shortcut.
M1Open là separate-side interval proxy, không executable tick/delay thật.
Không nhìn exit/source full-day completeness để bỏ planned entry.

Missing/crossed entry hoặc exit giữ unresolved trong census, không net0, force
close/forwardfill/next quote. Internal M1 gaps ghi đủ observed/expected count,
không dùng để xóa entry hoặc chứng nhận protective/equity path. Không SL/TP/
sizing/account/position carry simulation ở component này; zero broker calls.

## Economics và controls

One hypothetical unit=1USD/index point. BUY Ask→Bid, opposite SELL Bid→Ask,
null no exposure0. Same two declared US500 scenarios: observed BidAsk spread,
slip0,25/0,75point mỗi side, commission0. Reuse accepted money/cost primitives,
không round quote price/gross trước account-money cents step.

Funding0 **theo scenario rollover17:00 New York**: holding23:31→03:31 không
cross17:00. NY date đổi không tự là funding event; chưa verified target-broker
rollover/spec/historical funding. Không gọi funding0/noSL component là actual
prop trade/no-risk. Không thêm paid provider hoặc sửa phí sau outcomes.

Retain exact component chỉ khi mỗi năm: ≥150planned, ≥98%planned endpoints
resolved, stress known primarynet>0 và >opposite on same resolved cohort/null0.
Count/gate là triage, không statistical pass; unknowns giữ rõ, known-partial
sum không full annual net. Báo quarterly contributions/concentration/worst/best/
net/trade count như diagnostics, không post-outcome thêm gate hoặc bỏ tail.
Không tăng risk/lot, đổi giờ/fees/SL hoặc chọn riêng năm đẹp để cứu failure.

Nếu retained, mới đăng ký long-history/cost/tick/funding robustness, một risk
wrapper và đúng program/prop-equity/time-fit, selection-awareOOS/prospective/
owner handover. Không auto-promote, mở holdout2025+ hoặc gửi lệnh/mua challenge.

## Source/full-scope và implementation gate

Bind accepted R075 receipt SHA
`d5a2c23310729dab1a456cc66aa0d16e5cce5e65fbc014aa8caac5e5d3b12190`, full quarter
proofs/canonical hashes/calendar và current consumer code. Dùng
`us500_year_source.load_year_side` đủ4quarters/8seals, không copy Jan/Jul subset
vào annual loader. Kiểm calendar endpoints/census/clock/grid/coverage **trước
costs**; không source fetch/rewrite. Pilot không thay full-year paired fields.

Fixtures trước numeric: cross-midnight labels, DST/holiday/Monday/halfday,
unconditional selection độc lập future net/exit, missing/crossed/internal gap,
source identity/grid/census/authority, both directions/cost rounding/zero funding.
Separate Fraction reviewer từ frozen prices/calendar tái dựng endpoint/cost/
row/quarter/summary/gate và actual mutations. Same agent/method khác, không
independent feed/model/human. Old studies/bindings không đổi, reuse helper core.

Output mới private `execution-v1/us500-euopen-price-component-v1/`, one writer,
PID/progress/events/CANCEL/no overwrite, producer/reviewer deadline180s riêng.
Prep/compute/hash/write/review wall+CPU; network/model/broker calls0. Sau run
hậu kiểm gọn, chỉ sửa lỗi hoặc tối ưu mới có evidence; Goal vẫn active nếu
chưa C1/C2, không mở study khác chỉ để tránh economic verdict.
