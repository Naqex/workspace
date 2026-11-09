# R091 dự kiến: first observed 00/50 crossing → continuation

Đăng ký09/11/2026 trước source fixture/features/PnL mới. Method/limitations tại
[admission](FX-ROUND-LEVEL-METHOD-20261109.md). ID đề xuất R091, catalogue90/58
giữ tới implementation/outcome. Own EURUSD M5 quote-sampled component, related
R001/R015/R019 nhưng khác absolute round-level geometry; không independent edge.

## Recipe cố định

- Hai năm development đã exposed2019/2022, toàn weekday261+260=521days,
  không halfday/news/holiday outcome filter, không own2025+.
- Window America/New_York09:00→15:55; fixed quotes mỗi5phút,84slots/day.
  Joint Bid/Ask đầu tiên tại/sau target, lag≤60s; decision biết quote chậm
  nhất target+60s. DST dùng IANA NY, không cộng offset UTC cố định.
- Feature từ09:00, tìm crossing đầu tiên qua các target09:05→14:50.
  Grid chính step0,0050 (=50pip), offset0: các traditional00/50levels.
  Rising dùng Ask: previousAsk≤L<currentAsk; falling dùng Bid:
  currentBid<L≤previousBid. Equality ở current chưa cross, equality previous
  được nhận. Đi qua>1level hoặc cùng lúc có BUY và SELL→ambiguous, dừng ngày
  cho grid đó; không chọn level đẹp hoặc tiếp tìm crossing khác.
- Prefix thiếu/late trước crossing→unavailableprefix, không nhảy qua để
  chọn signal muộn hơn. Đã chọn thì thiếu quote sau đó không đổi selection.
  Mỗi grid chỉ1selected opportunity/day. Không forecast private order flow.
- Decision=current target+60s, entry=current target+5min, exit=entry+60min;
  cả hai first-after lag≤60s và entry actualtime>decision. Không instantaneous
  fill tại quote tín hiệu; không đổi lag/horizon sau kết quả. Last entry14:55,
  exit15:55, không qua declared17NY rollover nên funding0 theo scenario.
- Geometry control offset0,0025 (traditional25/75levels), cùng step/timing/
  first-cross rules. Chọn cố định trước giá, không random/fullsample extrema.
  Nó có cơ hội khác primary, chưa matched causal control hoặc bằng chứng
  statistical independence. Không promote control thắng sau khi xem outcomes.

## Giá, phí, unknown và gate

Một research unit=100.000EURnotional, không10kaccount/lot an toàn/risk25USD.
Mỗi geometry có follow/opposite/null ×reference/stress; cảhai geometry là
các kịch bản thay thế, không portfolio gộp exposure. Native cost core hiện có:
BUY Ask→Bid/SELL Bid→Ask, embedded spread không trừ hai lần, commission5USD/unit
khứ hồi, stress extra slippage0,00002 mỗi side=4USD/unit RT; reference slip0.
Đây là declared costs, chưa exact FTMO/The5ers fees/slippage. Báo midpoint
benchmark/spread/commission/slip/funding/net trên cùng path, không actual IS.

Selected thiếu entry/exit giữ exposed/unresolved, không0 hoặc skip; missing
trước selection khác missing sau selection. Không quyết định dựa exit quality.
Không SL/TP/sizing/margin/account equity/prop hoặc broker execution trong component.
Full census521days ×2geometry×3rules×2costs=6.252cases/24books, null exposure0.

Triage chuyển temporal review chỉ khi **mỗi năm**: ≥20selected mỗi geometry,
≥98%days có feature status known (no_cross/selected, không ambiguous/prefixgap),
0selectedunknown; primaryfollow stressnet>0 và mean/trade lớn hơn placebo
follow stressmean/trade. Các tỷ lệ/mẫu không independent/p-value hoặc đủ edge;
không nới gate, bỏ năm xấu hoặc đổi control/cost để cứu. Economicnegative
khác data-inconclusive; report cả gate components và raw known totals.

## Source/preflight/review trước và sau outcome

1. Pilot Tuesday đầu February2019/2022, đủ84slots×2=168slots trước features/
   PnL. Reuse sealed hourly targets khi binding còn đúng; targets5min mới dùng
   original raw observed EURUSD CSV. Hai selector độc lập: raw bytes/Fraction
   và native decoder. Kiểm first-after/predecessor/sequence/price/grid/clock/
   target census; compare accepted hourly packet overlaps. Pilot đòi168resolved.
2. Full43.764targets (2019=21.924;2022=21.840), chưa admission mọi slot phải
   đủ; missing/late giữ explicit. Rehash full raw/old cache seals trước dùng,
   original-vs-consumer runtime tách rõ. Không download/export/rewrite sources.
3. Synthetic trước numeric: BUY/SELL/equality/multilevel/dual-direction,
   first-only/prefixgap/future mutation, DST/census/holdout, selectedunknown,
   nativecost BUY/SELL/null/rounding/no funding. Có receipt trước actualfeatures.
4. Separate reviewer tái dựng cả521days, crossing bằng Fraction/brute levels,
   side/timing/selection/unknowns; tự tính BidAskgross/fees/net và summaries/
   gate. Actual mutations price/side/clock/missingrow/cost/net/authority chặn.
   Cùng agent/codepaths khác, chưa independenthuman/feed sign-off.

Source attempt `fx-round-level-source-pilot-v1` rồi `...-full-v1`, numeric
`fx-round-level-component-v1`; một writer, events/progress/PID/CANCEL,
source deadline600s và numeric180s, nooverwrite/failure retention. Bind protocol,
source/code/runtime, phase wall/CPU; không current-code repin old artifacts.
Nguồn nào lỗi thì giữ failure, chỉ affected review/recovery; không tự chạy lại
baseline nghiên cứu hoặc nới lag60s. Không có model/broker/paidprovider calls,
không authority mới. Survives component mới xét temporal/risk/prop/OOS/forward.
