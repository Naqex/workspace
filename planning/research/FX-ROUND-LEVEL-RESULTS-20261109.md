# R091: phần giá dương nhẹ, spread đã ăn hết — gác exact recipe

[Protocol](FX-ROUND-LEVEL-PROTOCOL-20261109.md) freeze `f72dcb7`, feature
`725f227` và economics `554e45f` trước actual features/PnL. Đã kiểm toàn bộ
521weekdays2019/2022 ×2geometry, 1.042rows/6.252financialcases/24books.
**Không retained:** primary net âm cả hai năm, ngay sau embedded spread đã âm.
Không có ứng viên challenge mới hoặc lý do chạy temporal/risk wrapper bản này.

## Cách thử và kết quả

Trong NY09:00–14:50, nhận crossing00/50 đầu tiên đã thấy ở joint quotes cách
5phút; quyết định target+60s, vào mốc5phút kế tiếp, giữ60phút. Rising dùng
Ask/falling dùng Bid. Chỉ1opportunity/day/grid; prefixgap dừng tìm ngày đó,
thiếu sau crossing không đổi selection. Placebo25/75 dùng rule/timing tương tự.
Không dùng nhãn tương lai15phút của paper để giả vào từ lúc chạm mốc.

Tiền là **USD/100.000EURnotional nghiên cứu**, không vốn tài khoản10k/risk25USD,
không lot an toàn hoặc kết quả challenge. 2geometry/2costs là alternative
experiments trên dữ liệu chồng nhau, không cộng thành portfolio/independenttrades.

| Primary00/50 |2019|2022|
|---|---:|---:|
|Cơ hội được chọn/đủ entry–exit|153/153|227/227|
|Midpoint benchmark, trước mọi phí|+331,00|+102,50|
|Embedded spread|−420,00|−838,50|
|**Sau spread, trước explicit fees**|**−89,00**|**−736,00**|
|Commission khai báo|−765,00|−1.135,00|
|Extra slippage trong phí cao|−612,00|−908,00|
|Funding trong registered window|0|0|
|Net phí chuẩn|−854,00|−1.871,00|
|**Net phí cao**|**−1.466,00**|**−2.779,00**|

Không trừ spread hai lần; native Bid/Ask gross đã chứa nó. Midpoint chỉ là
accounting benchmark, không giá chắc chắn khớp được hoặc expected edge.
Commission5USD/unit RT, extra slip4USD/unit RT là declaredmodel, chưa target
FTMO/The5ers fees. Funding0 vì entry/exit trước17NY, không khẳng định swap-free.
Tănglot không sửa kết quả trên mỗi unit. Chưa đáng mở feegrid: riêng spread
đã lớn hơn phần giá, và 2019 round mean còn thấp hơn placebo.

| Đối chiếu stress |2019|2022|
|---|---:|---:|
|Round mean/cơ hội,USD/unit|−9,5817|−12,2423|
|Placebo net,USD/unit|+493 (151cơ hội)|−7.665 (227cơ hội)|
|Placebo mean/cơ hội,USD/unit|+3,2649|−33,7665|
|Frozen sample/coverage gate|Đạt|Đạt|
|Frozen economic/increment gate|Không đạt cảhai|Net không đạt, increment đạt|

Không chuyển sang mốc25/75 vì một năm dương, chọn opposite thắng, hoặc đổi
sampling/holding/spread để cứu. Kết quả không bác bỏ mọi round-number strategy,
không chứng minh hiện tại bankorders không clustering. Đây là own causal
EURUSD/era/feed/horizon adaptation, không paper replication/causal order-flow proof.

## Nguồn, known-at và kiểm chéo

- Pilot Tuesday đầuFeb2019/2022:168/168slots đủ,14old hourlyslots reuse+154mới,
  native decoder vs raw Fraction selector/first-after/predecessor/order/grid;
  4mutations price/time/sequence/missingtarget bịchặn. Chưa actualfeatures/PnL.
- Full43.764targetslots:2019=21.924,2022=21.840;43.583within60s và181late/missing
  giữ explicit. 3.801slots reuse từ R090/pilot,39.963slots mới từ **oldraw**;
  0marketrequests/QDMexports. Rehash originals/raw/cache beforeuse, pin code/
  source/runtime; current runtime không tự trở thành original cache runtime.
- Raw-byte/Fraction và nativeCSV/decoder chọn giá độc lập; actual quote/time/
  sequence/price khớp kể cả late quotes. Accepted H1 reference so ở các target
  đúng giờ có H1source hợp lệ, không dùng H1 Open để chứng nhận mọi M5 slot.
- Primary feature statuses2019:5unavailableprefix/153cross/103no_cross;
  2022:4/227/29. Placebo2019:4/151/106;2022:4/227/29. Giữ toàn521days,
  không biến9primaryprefixgaps thành zero-return trades. Không selectedunknown
  trong actual; nhánh ấy đã kiểm bằng synthetic trước outcomes.
- 6featuretests và3componenttests đạt; first-only/equality/BUY–SELL/multilevel/
  dualdirection/DST/census/holdout/futuremutation/unknown/nativecost/null.
  Preflight trước actualfeatures:288syntheticfinancialcases,6.252emptycalendar
  cases và6.252syntheticpositivecalendar cases; false-pass và retained branch
  đều được đối chiếu bởi reviewer riêng.
- Actual reviewer Fraction/brute-enumerated levels từ raw-oraclepacket, không
  import producer/candidate; tái dựng mọi crossing/known-at/side/time/source,
  6.252financialcases,24books, summaries/gates và costdecomposition.
  7actualmutations net/commission/side/decisionclock/sourceprice/missingrow/
  authority bịreject. Sameagent/feed, không independenthuman/feed sign-off.

Chưa SL/TP/sizing/account equity/margin/firstcrossingtick/prop/time-fit3/6/12m,
targetspec/actualfills/cleanOOS/prospective hoặc ownerhandover. Correctness pass
khác economics fail; không accountpolicy mới, quyền broker hoặc own2025+.

## Hậu kiểm kỹ thuật và thời gian

| Lát |Wall đo được|Quyết định|
|---|---:|---|
|Sourcepilot+review|34,304s|Reuse raw và hourlypackets, không network/export|
|Fullsource+review|112,389s /CPU110,188s|Giữ M5packet/seals cho consumer sau; không reread raw không đổi|
|Preflight riêng trong economic controller|2,243s|288cases + hai calendars; nằm trong tổng bên dưới|
|Actual numeric|0,623s|Cũng nằm trong economic controller, không end-to-endtime|
|Toàn economic controller+review/mutations|5,992s /CPU5,750s|Khôngfailure/retry; controller terminal0|

Fullsource+economic khoảng118,381s, cộngpilot khoảng152,685s; không gồm
research/authoring/tests/Git hoặc cộng chồng các subphases. Không A/B speedup
claim. Source admission vẫn tốn phần lớn thời gian; đã reuse helpers/packets,
không bottleneck cần GPU/Rust/newframework. Không hạ source/quality gate để nhanh.
Existing skills đủ, không cần skill mới cho một fixed hypothesis.

**Tiếp:** catalogue91records/58account-policyversions/25native/9controls,
C1/C2 chưađạt/Goalactive. Admission cơ chế khác có primaryinputs rõ hoặc gỡ
materialblocker củasurvivor bằngevidence mới; khôngroundlevel/offset/hour/lag/
holding/feegrid hoặcmởfullhistory đểcứu outcome đã âm hai năm. R091 là related
breakout hypothesis, không independentedge chỉ vì tên/cơ chế mô tả khác.

## Tái hiện và artifacts

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
saved `run-fx-round-level-source-v1.py` pilot/full,
`run-review-fx-round-level-v1.py`, `round-level-oracle-v1.py`.
Attempts `execution-v1/fx-round-level-source-pilot-v1/`, `...-full-v1/`,
`fx-round-level-component-v1/` giữ manifest/snapshots/targets/quotes/rows/
decomposition/result/review/events/progress. Không overwrite baseline.

| Artifact |SHA256|
|---|---|
|Pilot result|`a066c7422e12d3d6c43631c3c6ed71ae813a8bbe5a77fd711be26237a37a3200`|
|Full source result|`639d1ff852375c924a80431748eeba41bda7c4a2ecef61fcd89d06d456dd16cb`|
|Economic result|`540940509bff867e1f260c20f979ae23249ce1c412a6dd2b3d6fc9cb74c6d4a6`|
|Economic review|`662bbf532a5f3a491e012e607fbd1c94c5dabc4a5b8c13a0e164bace3b38e8cf`|
|Summary|`0d0f8d58103c315823e7bbb9e8cb4f97db65fef6899300e2450502bd1efa8616`|
|Decomposition|`a4a41cad8033c217fa76ce28dae65f7a3a4241efc407165aec49844ea10b8132`|

BundledPython3.12.14 đã chạy `unittest discover -s tooling/ai-engines/tests
-p test_round_level_feature.py -v` (6tests/0,008s body), tương tự
`test_round_level_component.py` (3tests/0,187s body). Sau đó saved source
controller với `pilot`, `full`, rồi economic controller; tất cả terminal0.
Handles29456/30625 đã terminal, khôngpoll/restart. Primarysource/render/
hash/ex-postlabel warning tại [method admission](FX-ROUND-LEVEL-METHOD-20261109.md).
