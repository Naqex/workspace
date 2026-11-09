# Sửa nguồn long studies: có thay đổi lớn, chưa có ứng viên challenge

**Đã hoàn tất source correction2013–2024,24 annual books và monthly input
review trong scope đã đăng ký. C1/C2 tổng thể chưa đạt.** Hai bản RSI/preclose
không qua tiêu chí long review; monthly chưa đủ input và bị chặn trước portfolio
simulation. Không sửa thresholds hoặc xem riêng năm có lãi để nâng bước.
[Protocol trước outcome](INDEX-LONG-EXPLICIT-CORRECTION-20261108.md), checkpoint
`c966516`; producer/reader source `a2a3358` được reuse, không đổi giữa workers.

## Nguồn đã sửa và phần không được tự diễn giải

Tạo chín source-only views2013–2021 từ V6/cache đã có; giữ ba views2022–2024
sau revalidation, không tạo lại. Mỗi giá/volume retained khớp rawsource, source
timestamps/pairing được đối chiếu bằng native Node decoder riêng. Không network
hoặc download mới. Giữ old raw/exports/books, unpaired/availability journals và
các attempts lỗi trước. Đây là giữ nến nguồn, chưa là tick thực thi độc lập.

| Năm mới | Paired M1 mỗi side | Cash minutes có source/dự kiến | Padding bị loại, gộp hai side |
|---|---:|---:|---:|
|2013|218110|87459/97740|277832|
|2014|280855|90760/97740|247486|
|2015|228777|97049/97920|223876|
|2016|212887|96553/98100|195392|
|2017|190378|92585/97530|237692|
|2018|277562|96261/97350|253698|
|2019|309032|96534/97740|257784|
|2020|331321|96939/98310|204398|
|2021|334368|97952/98100|204482|

Không có unpaired rows mới trong paired-view subset này; **không** có nghĩa
rawsource không có side thiếu. Parent V6 đã intersection; side bị parent bỏ
không được tái dựng. Producer ghi explicit source không hiện diện trong parent,
giữ parent raw/unpaired journals. Missing cache/price/proof không fallback.
NYSE calendar vẫn chưa là hợp đồng giờ mở cửa CFD của broker đích.

## RSI/preclose: trước và sau trên cùng rules/risk/cost

Mỗi năm là một book10kUSD riêng, planned25USD/lệnh. Commission legacy0,5USD/
lot/side, slippage0,25/0,75 và funding1/2USD/lot/calendar day giữ nguyên.
Không dùng public commission0 mới để cứu các bản này. Net gồm cả floating
của vị thế cuối mẫu; không forceclose, không CAGR hoặc một account liên tục.

| Năm | RSI chuẩn/stress,USD | RSI entries | Preclose chuẩn/stress,USD | Preclose entries |
|---|---:|---:|---:|---:|
|2013|0/0|0|0/0|0|
|2014|0/0|0|0/0|0|
|2015|0/0|0|−12,16/−21,58|6|
|2016|0/0|0|+33,11/+26,84|2|
|2017|0/0|0|0/0|0|
|2018|+0,31/−8,97|8|+0,30/−8,98|8|
|2019|0/0|0|0/0|0|
|2020|+9,81/+5,25|4|−2,69/−6,26|4|
|2021|−6,21/−9,13|3|+15,68/+12,75|3|
|2022|−7,25/−20,74|19|+3,81/−7,06|20|
|2023|+11,23/+4,75|8|+20,51/+12,62|9|
|2024|+48,53/+39,93|10|+30,40/+20,91|11|

Số0 là book không có fill trong scenario này, **không là bằng chứng expectancy
bằng0 hoặc năm không rủi ro**. RSI có nofill2013/14/15/16/17/19;preclose có
nofill2013/14/17/19. Những năm đó giữ operationally inconclusive, không được
loại khỏi báo cáo để làm mẫu đẹp. Gaps và missing signal/fill không được điền.

| Metric/tiêu chí | RSI cũ → source-only | Preclose cũ → source-only |
|---|---:|---:|
|Tổng annual net chuẩn,USD|+23,77 → +56,42|−72,09 → +88,96|
|Tổng annual net stress,USD|−165,69 → +11,09|−351,21 → +29,24|
|Năm stress dương/12|6 →3|5 →4|
|Block2013–15 stress,USD|−20,33 →0|−164,53 →−21,58|
|Block2016–18 stress,USD|−111,40 →−8,97|−174,32 →+17,86|
|Block2019–21 stress,USD|−139,25 →−3,88|−112,74 →+6,49|
|Block2022–24 stress,USD|+105,29 →+23,94|+100,38 →+26,47|
|Tiêu chí cũ:≥8/12stressyears dương và cả4blocks dương|Không đạt → không đạt|Không đạt → không đạt|

Lợi nhuận bớt âm/chuyển dương không đủ để nâng bước. Rules yêu cầu đủ daily
inputs/ATR đã khóa; source thiếu làm giảm tập tín hiệu và fill thực hiện được.
Đây không là filter mới được chọn theo PnL. Nhiều vị thế còn path unresolved
qua khoảng thiếu giá; rawsource listed không chứng minh executable tick hoặc
phân biệt mọi khoảng thiếu với giờ broker đóng. Chưa chứng nhận native prop
drawdown, target costs/specs, cleanOOS hoặc forward/reconciliation.

## Đã kiểm gì để tránh quy nhầm mọi delta cho input?

- 24books/72scenarios, gồm24null controls, đều qua arithmetic/fill/funding/
  open-mark reviewer hiện hành và explicit-source binding. Null0, không source
  mutation giữa runs. Original scenarios/results/reviews và old/new locators
  được rehash; không sửa old pins để nhận currentcode.
- Signal functions `rsi3`/`plans_for`, preclose `bar_for`/`plans_for` và Fraction
  oracle có AST exact giữa source snapshots cũ/mới. Rules/candidate/risk/
  leverage/funding metadata giữ nguyên. Financial product dependencies không
  đổi; named-cost plumbing của wrapper/book đã thêm trong slice trước.
- Không gọi mọi numericalfile byteidentical: `simulate`/`simulator`/`market`
  đã có named-cost arguments. Để kiểm nhánh legacy không gây delta, đăng ký
  riêng bốn replay2024 trên **old expanded input** cho RSI/preclose ×2costs;
  20,593s, decisions/trades/funding/cash/floating/openstate exact, chỉ bỏ qua
  timing và cost-metadata fields mới. Năm2024 được chọn vì hai bản có open
  positions; scope là compatibility, không nâng oldsource thành source-only.
- Delta review6,875s đọc lại đủ72scenarios: financial before/after, added/removed/
  changed decisions, gaps/rejections, unresolvedpositions, selection và source
  differences. Không chỉ so net hoặc claim independent model/human review.

## Monthly:32/132 tháng có input, chưa được chạy portfolio mới

Giữ2013warmup,2014–2024evaluation và original momentum/longbenchmark rules.
`prepare` trên explicit input được so với một oracle dựng từ daily facts;
144monthlyplans mỗi policy và observations khớp. Đó là288 kế hoạch gồm warmup,
không288 giao dịch hoặc samples độc lập.

| Năm evaluation | Tháng eligible cũ → source-only, trên12tháng |
|---|---:|
|2014|2 →0|
|2015|0 →0|
|2016|0 →0|
|2017|1 →0|
|2018|12 →2|
|2019|12 →1|
|2020|10 →3|
|2021|11 →1|
|2022|12 →8|
|2023|11 →9|
|2024|12 →8|

Cảhai policy có counts giống nhau vì input eligibility chung. Từ83/132tháng
trước sửa xuống32/132; mỗi bản có94/144monthlyobservations thay đổi, gồm
warmup. Các năm không có tháng eligible hiện là2014–17, trước là2015–16.

Admissionfail → actual `simulate` bị ValueError đúng mã
`monthly_input_has_unusable_evaluation_year` cho cảhai bản. Portfolio kernel
được thay bằng sentinel cấm gọi trong probe: **0simulationcalls**. Không bỏ
2014–17, giảm yêu cầu13monthends/14cashTR hoặc tính lại PnL để cứu strategy.
Old monthly numbers giữ expanded-view/unadmitted; không là kết luận về một
monthly strategy với dữ liệu đủ. Cần source/clock phù hợp trước thử tiếp.

## Thời gian, nhật ký và việc còn lại

| Phần | Thời gian đo | Scope |
|---|---:|---|
|Data correction9newyears + revalidate/reuse3years|322,391s wall|Tối đa2dataworkers;nativeoracle mỗi năm,0network|
|24 annual books +72scenario checks|503,328s wall|Một numericalworker,stream từng năm đã verified; chạy chồng với data|
|Legacy cost compatibility4cases|20,593s|Một năm2024,4scenarios trên oldinput, không independent economic evidence|
|Long before/after selection review|6,875s|0numericalsimulation mới|
|Monthlyinput/source/oracle/guard|55,453s wall/35,016s CPU|9,094s prepare+oracle+guard;0portfoliosimulation|

Không cộng các số wall trên thành end-to-end vì có overlap. Đây là correction,
chưa A/B cùng semantics nên không speedup claim. Không thêm GPU/framework hoặc
profile loop khi chưa có mục tiêu performance riêng. Chỉ lưu bài học có cơ sở.

Nhật ký quyết định: nguồn chèn → freeze correction → source-only/reader/native
oracle → giữ rules/risk/cost → rerun affected books → source/cost parity →
reject triage/inconclusive input. Giữ failures/unknowns và next action, không
gọi tổng PnL dương là mục tiêu đã xong. [Ba skills](../../docs/development/SKILL-MAINTENANCE.md#0811-nhật-ký-tối-ưu-và-quyết-định-chiến-lược)
đã được cập nhật theo owner để nhắc workflow này; chưa publish native runtime.

Private campaign root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/us500-long-explicit-source-v1`:new/reused years, proof/reader/
  native source oracle/log/source snapshots. Controller22904/launcher26812.
- `execution-v1/us500-long-source-corrected-books-v1`:24books/72scenarios,
  `source-delta-selection-review-v1.json`, snapshots và logs. Controller21768/
  launcher26972. `run-us500-long-source-books-v1.py` và
  `review-long-source-book-deltas-v1.py` giữ exactdriver/reviewer.
- `execution-v1/long-legacy-cost-compatibility-v1`:manifest trước outcomes,
  4results/source snapshots; `check-long-legacy-cost-compatibility-v1.py`.
- `execution-v1/us500-monthly-explicit-input-review-v1`:inputpins/dailyfacts/
  old-new observations/plans/guardrejections/source snapshots;
  `review-monthly-explicit-input-v1.py`,controller26000/launcher19636.

Các process trên đã terminal; không tự dispatch lại completed study. Báo cáo
là review trong cùng agent, không independent sign-off. C1/C2 vẫn mở: source
clock/target contract/tick/prop/OOS/forward còn thiếu. Không mởholdout2025+,
OrderCheck/OrderSend, mua challenge/account/provider hoặc production.

Kiểm cuối:10tài liệu không lỗi local link, catalogue vẫn53records/41versions;
12sourceyears/24uniqueannualbooks/72scenarios và2monthlyguardrejections đã
đối chiếu counts/hashes. Ba skills đã qua quickvalidate/links và maintainer
0errors/0warnings; global12279B/project10133B/reserve55403B/combined22412B.
Không rerun suite numerical không đổi trong lượt chỉ orchestration/correction;
dùng reader/oracle/arithmetic checks của actualdata,source snapshots và4case
compatibility cho khác biệt namedcost đã xác định.

**Bước tiếp có ích:** rà khả năng dữ liệu/clock của ứng viên còn tiềm năng
đã có (GoldSMA50k), và ưu tiên chỉ chạy thêm khi phép kiểm giải quyết bất định
cụ thể. Không dùng các longUS500 books này để qualify hoặc searchparams/clock
đến khi có winner. Không loại cả family vì dataset không đủ clock của recipe.
