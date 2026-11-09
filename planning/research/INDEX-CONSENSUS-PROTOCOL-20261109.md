# R078/R079: chỉ trade khi first-half và rest-of-day cùng hướng

Đăng ký trước group outcomes mới; kế thừa [verified paper-window source/results](INDEX-PAPER-WINDOW-RESULTS-20261109.md).
Goal C1/C2 active. Parent R076/R077v1/v2 giữ không retained; đây là related
published policy riêng, không retune clock/fee hoặc independent discovery.

## Primary method và điểm khác

[Baltussen và cộng sự, JFE2021, Table6](https://academicweb.nd.edu/~zda/intramom.pdf)
định nghĩa η(rONFH,rROD): long khi cả hai returns dương, short khi cả hai âm,
không trade khi trái dấu. Đã đọc lại09/11; không copy code/data của paper,
claim CFD replication/gamma hoặc lấy pooled futures headline làm net edge.
Hypothesis đã ở queue trước parent outcomes; registration này diễn ra sau khi
biết parent fail, giữ selection/exposure history và không gọi2019/2022 là unseen.

R078 `us500-rod-firsthalf-consensus-tick-component-v1`, R079
`nasdaq-rod-firsthalf-consensus-tick-component-v1`. Mỗi asset là primary riêng,
không cộng USD/unit thành portfolio. Same calendars503cashdays/asset, years2019/
2022 consumed, predictor common-mask/late tick confirmation/previous expected
cashsession từ corrected parentv2. Không own2025+, new provider/account/broker.

Entry rule duy nhất: parent predictor valid, primary sign khác0 và trùng
first-half sign; flat/missing/opposite giữ explicit no exposure. Quyết định
chỉ dùng features known-at15:30, không net returns, later quote availability
hoặc current full-day quality. Không dùng tương lai để bỏ planned trade.

## Semantics giữ nguyên

- Decision15:30/exit16:00 NewYork, primary delay1s/stress2s/proxy60s; maxwait60s
  sau target, first quote/ordinal/BidAsk từ accepted corrected parent. Không
  chọn quote/delay/threshold theo group outcome hoặc native fills thật.
- One hypothetical unit=1USD/index point. Reference/stress slip0,25/0,75 mỗi
  side, observed spread, commission/funding0 scenario; same cents rounding.
  Không account10k/lot/risk/SL/TP/prop-equity proof. Unresolved selected trade
  giữ planned/unknown, không net0/fill; skipped trade costs=None/no exposure.
- Reuse sealed parent quotes/cost fields nếu selected; no exposure có entry/
  exit=None/outcomes={}, không giữ fake order. Original parent rows bất biến.
- 5roles: primary/opposite/alwayslong/alwaysshort/firsthalf. Trên consensus
  mask **firsthalf bằng primary** theo định nghĩa; đây là invariant, không
  benchmark phải vượt. Unfiltered parent rROD/firsthalf trên full calendar
  báo diagnostic về turnover/known net, không chọn cohort tốt hơn sau outcome.

## Triage khóa trước outcomes

Retain từng asset khi mỗi năm ở cả3delays: ≥100planned, ≥98%regular days có
base predictors valid, ≥98%selected planned resolved, stress primaryknownsum>0
và >alwayslong/alwaysshort trên cùng selected-resolved mask. Đây là triage,
có false negatives, chưa statistical proof/cleanOOS hoặc xác suất pass quỹ.
Known-partial sum và unknown comparisons giữ nhãn, không gọi full annual net.

Fail→gác exact consensus policy; không reverse agreement, retune window/fee/
threshold/requiredcount hoặc pick single year/asset/delay rescue. Positive
component mới đáng đăng ký risk/SL/selection-awareOOS/prop/time-fit/prospective/
ownerhandover; research report không cấp authority giao dịch/challenge.

## Correctness/reuse trước net và hậu kiểm

Input parent result SHA `7764da578805185e0293dbb0bdef5ce27763d92849fc85fa14023831d656c898`,
review SHA `4d3d0a3a1d2b5e24d0352e62cbc4e0ee46949126364ed3ea8e85d26e758ac52b`.
Source corrected review SHA `4624d538f9cfa5cfcba7b76d17609fe9af5499802062e88f64849324342afd1b`.
Bind parent rows/summary/protocol/code/current costs and source lineage; không
rerun raw16million tick review hoặc old simulations không đổi chỉ để đọc net.

Tests trước run: agree/disagree/flat/missing/selectedunknown, future price/net
mutation không đổi selection, bothside/profile/delay/scope, input immutable,
firsthalf identity, full calendar census và impossible-gate regression. Separate
Fraction reducer kiểm chọn cohort/cost fields/summary/gate trên toàn records,
verify selected outcomes exact parent; actual selection/net/census mutations.
Same agent/arithmetic khác, không independent model/human signoff.

Private output mới `execution-v1/index-consensus-components-v1/`, one writer,
no overwrite, PID/events/progress/CANCEL/deadline180s producer/reviewer riêng;
phase timings/pins/snapshots/results/review, source/network/broker/modelcalls0.
Sau kết quả, hậu kiểm gọn; chỉ tối ưu bottleneck mới có evidence, không tạo
skill/DB/UI hoặc archive chase mới để trì hoãn economic decision.
