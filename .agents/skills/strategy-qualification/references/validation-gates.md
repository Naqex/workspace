# Cửa kiểm chứng: bằng chứng nào cho phép kết luận gì?

Áp dụng từng cửa theo stage, không bắt research ban đầu có đủ mọi điều kiện của
broker execution. Nguồn/đối chiếu hiện hành ở
[audit khung validation](../../../../planning/research/STRATEGY-VALIDATION-FRAMEWORK-20261105.md).
PLAN/protocol và receipt vẫn own scope/outcomes; bảng này own phương pháp review.

| Cửa | Bằng chứng cần | Kết luận tối đa |
|---|---|---|
| G0. Thiết kế trước kết quả | Cơ chế giả thuyết, exact rules/baseline/cost/risk, consumed map/split, main metrics/stop/decision và bản freeze có thời điểm đáng tin | Được chạy đúng experiment đã đăng ký; hash nội dung riêng không chứng minh timing |
| G1. Dữ liệu/code/timing | Kiểm ordering/gaps/timezone/BidAsk; chỉ dùng dữ liệu đã có tại decision, fill sau decision; case tính tay/oracle đơn giản và regressions độc lập với helper bị kiểm | Implementation có bằng chứng trong scope đã kiểm; còn gap thì nêu rõ |
| G2. Simulation assumptions | Spread/commission/slippage/financing/lot/margin, stress/gap/delay, equity/cash và cuối mẫu đúng semantics, nguồn và giới hạn assumptions | Kết quả dưới assumptions đó; chưa suy broker fills hay prop compliance |
| G3. Edge ngoài mẫu | Freeze trước window chưa used, trial history gồm failures/variants, sample/exposure/dependence/regimes/uncertainty, selection-aware assessment khi đủ assumptions | Review robustness/edge; PnL dương hoặc một Sharpe threshold không tự pass |
| G4. Prop-specific | Đúng firm/program/phase/size/version, reset/DST/daily/overall equity, first breach, entry rules, sample coverage, cost/permissions | Prop-fit trong phạm vi profile đã kiểm, không đồng nhất internal budgets với luật hãng |
| G5. Forward/reconciliation | Shadow/demo đúng code/config; đối chiếu signal→order→fill/cost/risk, disconnect/restart/unknown handling, dữ liệu live theo quyền riêng | Bằng chứng vận hành và model-vs-broker gap; chưa bảo đảm lợi nhuận tương lai |
| G6. Authority | Account/scope/budget/grant còn hợp lệ và gate của execution owner | Được thực thi đúng phạm vi, không do research report tự cấp |

Trước validation research: cần G0, G1 và G2 có assumptions rõ, không nợ lỗi
material; chưa đủ realism thì chỉ được kết luận ở mức scenario. Trước đề xuất
shadow/demo cho strategy: review thêm G3/G4 theo mục tiêu, nêu remaining gaps.
Mọi gửi lệnh cần G6 riêng; system demo test không tự chứng minh strategy edge.

## Stage-0: Unconditional Markout & Scale Screen

**Chính sách sàng lọc của owner ngày 13/11/2026 cho cơ chế tín hiệu mới**, trước
khi đóng gói SL/TP/sizing, partial close hoặc filter phụ. Không áp hồi tố để
đổi sealed outcomes; chưa được runner tự enforce và không phải chuẩn thống kê
phổ quát. Bài học: US500 BR01/RS02, EURUSD Catalogue13/B0 và
[XAUUSD scale/horizon audit](../../../../planning/research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.md).

1. **Raw markout trước SL/TP/filter:** khóa tín hiệu thô, Development, cost
   stress, đơn vị và horizon chính trước outcome; khóa cả budget horizon phụ.
   Đo phân phối sau spread/commission/slippage và financing nếu có tại các mốc
   cố định phù hợp: +1h/+2h/+4h/cuối phiên hoặc +1d/+3d/+5d. Giữ count, unique
   days, overlap, từng năm, uncertainty và missing quotes; không chọn horizon
   thắng sau khi xem kết quả. Bid/Ask đã chứa spread thì không trừ lần hai.
   **Dừng Stage-0** nếu mean net stress tại horizon chính không dương ở mọi
   năm Development, hoặc nhỏ hơn mean ma sát thực thi stress trên cùng cohort,
   cùng đơn vị. Không viết tiếp biến thể SL/TP, partial close hoặc filter để
   cứu kết quả; thiếu nguồn/cost thì giữ blocked/unknown, không giả bằng 0.
2. **Natural stop và quy mô phí:** trên raw cohort trước lọc phí, đo stop
   tự nhiên theo cấu trúc nhân quả; `median(F_stress) / median(natural_SL)`
   phải ≤ trần đã khóa trong **12%–15%** (ưu tiên 12%, không quá 15%). Hai vế
   phải cùng đơn vị giá, ví dụ USD/oz hoặc pip; không chia USD tiền tài khoản
   cho khoảng giá, không trộn phí nhóm fills với SL nhóm rejects. Đây là screen
   quy mô, khác `Friction/R0` trên từng intent; trần intent 12% hiện hành vẫn giữ.
3. **Không dùng cost gate để đổi bản chất mẫu:** cấm bộ lọc `Friction/R`
   loại **>50%** tín hiệu tự nhiên. Mẫu số là raw signals đã đăng ký, không
   thu hẹp bằng filter phụ rồi tính lại. Giữ funnel và lý do loại; vượt ngưỡng
   thì dừng recipe, không nới SL nhân tạo, tăng risk hoặc hạ stress sau outcome.
   Tỷ lệ loại lớn là rủi ro chọn lọc quy mô/nến cực đoan, chưa tự chứng minh
   exhaustion hoặc nguyên nhân nhân quả của khoản lỗ.

Qua Stage-0 chỉ cho phép xét đầu tư tiếp đúng protocol; raw markout có thể
chồng lấn, không là account PnL hay chứng minh edge/OOS/prop. G0–G6 vẫn áp dụng.

## Cách báo cáo

### Nhãn nguyên nhân dừng và phạm vi bằng chứng

Dùng nhiều nhãn khi các vấn đề cùng tồn tại; nhãn là interpretation có source,
không thay verdict/protocol đã freeze, không automatic rejection/dispatch.
Mỗi nhãn giữ candidate/version, scenario/window, stage, evidence và reason.

| Nhãn | Khi có thể dùng | Không được suy ra |
|---|---|---|
| `ECONOMIC_FAIL` | Net không đạt tiêu chí kinh tế đã đăng ký trong reference/stress, hoặc markout diagnostic yếu trong đúng cohort/horizon | Không bác toàn family; mean trong mẫu không là true expectancy. Gross/markout không tự là account PnL |
| `CADENCE_OR_SAMPLE_SHORTFALL` | Cơ hội/mẫu không đủ cho precision, time-fit hoặc vai trò đang xét; có thể cùng net dương trong mẫu | Không gọi net dương là edge đã chứng minh, không đặt minimum trades chung hoặc ép thêm lệnh |
| `PROP_TIMEFIT_REJECTED` | Exact candidate/model không đạt thời gian mục tiêu đã đo, hoặc owner gác sau review; giữ horizon, risk/cost, censoring và verdict source | Khác vi phạm DD, âm kinh tế hoặc bác toàn family; không suy mọi start/tương lai đều thất bại |
| `DATA_PATH_INCOMPLETE` | Thiếu đường giữ lệnh cho full PnL, hoặc thiếu intraminute path cần cho DD/prop | Phải ghi metric/stage bị thiếu: M1 full net đã đối soát không thành N/A chỉ vì chưa đủ tick DD |
| `PROP_UNMEASURED` | Chưa kiểm đủ rule/profile/path cho claim đang xét; ghi rõ partial checks nếu có | `prop_qualified=false`, null DD hoặc thiếu field không chứng minh đã vi phạm |
| `PROP_VIOLATED` | Có evaluator/model phù hợp profile và witness vi phạm: rule/version, thời điểm, anchor/floor, equity/cost/reset semantics | Không suy từ âm cuối kỳ, endpoint maxDD hoặc flag chưa-qualified. Modeled breach khác actual broker breach |

Tách `economic_result` (positive-in-sample / negative-in-model / unknown),
`edge_status`, `data_scope` và `prop_status`; không ép một primary label che
các blocker khác. Prop measured-within-limits chỉ đúng rules/window/coverage
đã kiểm, không tự pass G3/G5/G6. Có observed breach đủ evidence dù phần path
khác thiếu thì vẫn ghi witness; thiếu coverage cấm kết luận không-breach.
Branch chỉ chứa docs/source setup có scope not-applicable, không gán economic
failure. Technical invalidity vẫn theo G1/correctness, không gọi là alpha âm.

Case adoption: [bảng chuẩn hóa và hồ sơ ứng viên](../../../../planning/research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
bind saved outputs, giữ unknown và old verdicts. Đây là derived review view,
không taxonomy đã được runner hoặc product API tự enforce.

Mỗi cửa ghi stage applicability, status **đã kiểm trong scope / chưa kiểm /
không đạt / chưa đủ bằng chứng**, locator/version và bước sửa nhỏ nhất. Tool
`strategy_evidence.py inspect` chỉ kiểm artifact invariants/bindings; đọc
`review_checks`, không suy từ exit0/hash match thành preregistration, causality,
OOS, independent review hoặc broker realism. Không biến user labels thành proof.

- Lỗi code/clock/data → invalidate/quarantine run bị ảnh hưởng, sửa và kiểm
  case lỗi rồi rerun phần cần. Không loại luôn ý tưởng hoặc sửa parameters cho đẹp.
- Thay rules sau khi nhìn validation → trial mới; window đã nhìn là consumed,
  không còn final unseen holdout cho bản đó. Giữ negative/abandoned variants.
- Sample/precision/coverage thiếu → inconclusive, không mặc định0 hoặc pass.
- Có material bug hoặc vi phạm xác minh → reject evidence/version liên quan.
- Eligible next-stage review cần bằng chứng cho đúng stage, chưa là authority.

Đừng chọn một con số Sharpe/số trades/p-value làm tem chuẩn chung. PBO/DSR/
resampling cần trial/dependence/distribution assumptions phù hợp; chúng không
sửa được lookahead, dữ liệu sai hoặc chi phí hư cấu. Walk-forward không là bắt
buộc cho mọi fixed strategy; purge/embargo chỉ áp khi cấu trúc samples/labels cần.

## Khi exact run dừng vì thiếu giá

Không mặc định phải khôi phục cả archive trước khi chọn việc tiếp theo. Có thể
đăng ký một sensitivity model riêng để hỏi uncertainty có làm đổi ưu tiên
nghiên cứu không; giữ exact unknown và protocol cũ. Đây không là permission
bỏ gap, tự đóng vị thế hoặc chấp nhận dữ liệu không đạt G1/G2.

- Nêu giả định có thể bác bỏ: ví dụ hidden prices nằm trong same-side H1
  envelope và protective execution theo model không rejection. Kiểm envelope
  chứa observations đã có; điều đó chưa chứng minh không có quote/outlier mất.
- Bao gồm mọi nhánh SL/TP/survival/gap có thể theo giả định, account costs và
  eligibility trên toàn cash interval. Thiếu terminal/source hoặc các nhánh
  làm đổi entry eligibility mà chưa mô hình hóa thì giữ inconclusive.
- H1 có thời gian trước entry không xác định được thời điểm chạm barrier;
  dùng retrospective bound không được đưa tương lai vào entry/size. Outer
  bounds có điều kiện không là confidence interval/xác suất pass đã hiệu chỉnh.
- Khóa tiêu chí trước outcome mới, so unaffected trades với exact baseline
  và kiểm bằng arithmetic/path khác. Kể cả hai đầu bound bằng nhau vẫn ghi
  conditional; không sửa actual-state/unknown/edge/prop verdict thành pass.
  Upper bound âm có thể giảm ưu tiên đúng recipe theo protocol, không bác bỏ
  cả family hoặc chứng minh mất giá đã được khôi phục.

Provenance: [R065 bounds](../../../../planning/research/NASDAQ-OPENING5-BOUNDS-RESULTS-20261109.md)
và [R066](../../../../planning/research/NASDAQ-NOISE14-RESULTS-20261109.md) đã có
registered models, full Fraction reviews và retained exact unknowns. Đây là
hai cases cùng agent/provider, không universal fidelity certificate.

## Prop Target Envelope — profile owner ngày 13/11/2026

Áp dụng chiến dịch H1→M15 intraday mới trong workspace, theo
[đề xuất design-from-constraints](../../../../planning/research/PROP-DESIGN-FROM-CONSTRAINTS-PROPOSAL-20261113.md).
Đây là điều kiện thiết kế/suitability của owner, **không phải chuẩn thống kê
phổ quát, luật FTMO, bằng chứng có edge hoặc quyền chạy study**. Freeze profile
trong protocol trước outcome; không áp hồi tố để sửa sealed results. Reference
này chưa được runner tự enforce. Funded và challenge có qualification riêng.

### Đơn vị và chi phí

- `R0` = ngân sách USD/lệnh cố định theo vốn đầu phase (gồm stop-risk và cost/
  gap allowance đã khai báo); netR = netPnL/R0. Ghi thêm `R_price` = lot×contract
  × khoảng cách entry fill tới SL, vì lotrounding khiến hai mẫu số khác nhau.
- `F_stress` = spread drag có benchmark hợp lệ + commission cả vòng + slippage
  cả vòng; không gồm financing. Gross Bid/Ask đã chứa spread thì **không trừ
  spread lần hai** để tính net. Thiếu benchmark/oppositequote → unknown/bounds,
  không0. Phân biệt ex-ante reserve với chi phí realized, không dùng exitquote
  tương lai để lọc entry.

| Điều kiện thiết kế | Gate trong scope này |
|---|---|
| Friction/R0 | Ưu tiên ≤10%; trần kế hoạch stress ≤12%/intent. Vùng10–12% cần ghi rõ trade-off, không nới sau outcome. Báo realized median/p90/tail/vượt cap; không xóa các lệnh phí cao hoặc hứa fill không bao giờ vượt reserve. |
| Overnight shield | Ưu tiên session-bounded, flat trước **rollover/session close đúng account/symbol/date trừ buffer thực thi**. 21:45UTC chỉ hợp lệ nếu calendar chứng minh nó đủ sớm. Không fresh exitquote/không xác nhận flat thì unknown/execution failure, không tự ghi swap0. |
| Nếu cho phép overnight | Khóa maxholding trước; financing debit ≤15% gross-positive-PnL pool của cùng closed cohort, đồng thời net sau mọi phí vẫn dương. Pool=sum(max(gross Bid/Ask trước commission/slip/swap,0)); pool0→N/A. Credits/open financing tách riêng; báo thêm net financing/gross signed, không dùng credit che debit hay mẫu số âm. |
| Cadence | Sàn suitability60 filled trades/năm đầy đủ; ưu tiên120/năm (5–10/tháng). Đếm sau mọi filter/lot/margin/news rules, giữ tháng0 và báo mức đều/tập trung/unique days/dependence. Không quota giao dịch, không chứng nhận statistical power. |
| R-velocity | +25 đến+40 netR0/năm stress là dải tham vọng ban đầu, **chưa đủ** để mặc định đạt challenge6–12tháng; dùng phép tính ngược phía dưới. Mean/R-year không thay distribution, rolling paths/OOS. |
| R-drawdown | Hướng tới cumulative peak-to-trough equityDD ≤15R0, báo static initial loss và daily loss riêng. Cần floating/cost/gap coverage; thiếu path không được pass bằng cashDD. |
| Sizing | 0,30%/0,40% là hai endpoint nghiên cứu có đăng ký, không risk thật hoặc tham số tối ưu. Core alpha dương trước review sizing; không tăng risk để cứu net âm. |

Intraday không tự tương thích100% Standard/Swing: còn news execution, market
breaks, sessions, margin và contract. Không cộng ngược8.950,80USD swap cũ vào
Gold intraday: đóng sớm còn thay chính returns/trades. Source hiện hành phải
kiểm lại khi freeze account profile, không lấy declared legacy rates làm thực.

### Tính ngược thời gian và rủi ro

Với phase targets10% rồi5%, mỗi phase reset vốn và fixed risk `r`, kế hoạch
lý tưởng cần `R_required = 10/r + 5/r` (r dùng cùng đơn vị phần trăm). Đây
chỉ là số học planning, **không time-to-pass dự báo**: chưa overshoot, min-days,
approval gap, đường lỗ/phí mới hoặc censoring. Phí đã ở netR không trừ lại.

| Risk/lệnh | R0 cần phase1 +phase2 | Pace cho12tháng | Pace cho6tháng |
|---|---|---|---|
|0,30%|33,33 +16,67 =50R0|50R0/năm|100R0/năm|
|0,40%|25 +12,5 =37,5R0|37,5R0/năm|75R0/năm|

Do đó25–40R0/năm không bảo đảm6–12tháng. Freeze **12tháng là mục tiêu chính,
6tháng là mục tiêu cao hơn**, rồi đo cả hai; không tăng lot hoặc nới DD khi
arithmetic không đạt. Với N trades/năm, cần kiểm thêm `net expectancy R0/trade
× N` so pace, không chỉ gross USD/lot. `R-Calmar = annual netR0 / maxR-DD`
là tỷ số báo riêng; annualR0 tự nó không phải Calmar.

Tại0,40%,15R0 =6,0%, **không phải <6,0%**. Nếu profile yêu cầu strict<6% thì
R-DD phải<15R0, còn allowance/gap cần buffer. DD≤15R0 không bảo đảm daily<2,5%:
phải đo riêng worstday<6,25R0 ở0,40% hoặc<8,33R0 ở0,30%, dưới cùng cash/reset
semantics. Giữ hard internal daily<2,5%, staticloss<6,5%; strict6% là mục tiêu
thiết kế chặt hơn, không đổi định nghĩa peakDD thành staticloss sau outcome.

Với payout: cần net edge, survival, reconciliation, eligibility/withdrawal và
dòng tiền sau owner costs riêng. Không áp target15% cho mỗi chu kỳ funded,
không gọi model-pass hoặc R-velocity là thu nhập chắc chắn. G0–G6 giữ nguyên.
