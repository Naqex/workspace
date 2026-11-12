# Bước 1–2: trạng thái chuẩn hóa, hồ sơ ứng viên và contract kiểm định

12/11/2026. Owner phê duyệt hai bước đầu sau quantitative self-audit:
chuẩn hóa nguyên nhân dừng và chốt contract Alpha–Sizing–Exit. **Chưa phê
duyệt triển khai Bước 3–5 trong lượt này.** Không code runner/product mới,
simulation, đọc market data/holdout mới, đổi risk thật hoặc tạo branch mới.
Task tổng vẫn là [STRATEGY-E2E](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).

[JSON dẫn xuất](STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.json) giữ số liệu
Gold và năm cấu hình US500, scope/labels cùng SHA256 của 54 input artifacts.
Đây là review view của kết quả đã lưu, không thay source of truth numerical,
catalogue/protocol/verdict cũ hoặc native Paperclip run state.

## Taxonomy và bảng trạng thái hiện có

Định nghĩa duy nhất ở [validation-gates](../../.agents/skills/strategy-qualification/references/validation-gates.md#nhãn-nguyên-nhân-dừng-và-phạm-vi-bằng-chứng).
Một trường hợp có thể có nhiều nhãn. Phải giữ scope để tách full PnL thiếu
đường giá khỏi full DD chưa đo dù M1 PnL đã đối soát.

| Trường hợp | Economics/sample trong mô hình đã dùng | Nhãn chuẩn hóa và scope | Trạng thái giữ nguyên |
|---|---|---|---|
| [EURUSD Catalogue13](EURUSD-CATALOGUE13-RESULTS-20261108.md) | 24 versions ×13 reset years ×2 costs;0/24 retained; tổng stress từng bản âm | `ECONOMIC_FAIL` cho frozen screen; `PROP_UNMEASURED` cho full target path | Không giữ các exact versions; không bác mọi FX. 624 cases không là624alphas |
| [ML Discovery5](DISCOVERY5-RESULTS-20261108.md) | Ridge stress−593,70USD/475closed; Forest−1.537,26/263closed;2024 consumed development | `ECONOMIC_FAIL`; `PROP_UNMEASURED` | Hai real models không giữ; không gọi là IS đẹp rồi fail clean OOS |
| [BR01/RS02 markout](US500-CONTINUATION-DIAGNOSTIC-RESULTS-20261112.md) | Gộp2022–25: đà trước phí yếu/âm;24annual cells stressmeanâm | `ECONOMIC_FAIL` cho endpoint diagnostic; `DATA_PATH_INCOMPLETE` với missing windows; `PROP_UNMEASURED` | Park exact components; markout R không là USD/account PnL hoặc proof mọi exit thất bại |
| [R123](US500-MA-RECLAIM-RESULTS-20261111.md) | 165lệnh/3reset books10k; reference+4,83/stress−307,03USD | `ECONOMIC_FAIL`; `CADENCE_OR_SAMPLE_SHORTFALL` cho current goal; `DATA_PATH_INCOMPLETE` chỉ intraminuteDD; `PROP_UNMEASURED` | Full M1 held coverage của study đã đủ; không biến net thànhN/A vì thiếu tickDD |
| Năm US500 dương bên dưới | Tổng stress dương trong cùng mẫu đã search;13–28lệnh/3năm | `CADENCE_OR_SAMPLE_SHORTFALL`; `DATA_PATH_INCOMPLETE` chỉ G4intraminuteDD; `PROP_UNMEASURED` | Positive-in-sample, edge chưa chứng minh. Không `ECONOMIC_FAIL` chỉ vì có một năm âm |
| [Recent RS01/RS07,2026](US500-RECENT-SCREEN-RESULTS-20261112.md) | 155/202trades;4/5held-path unresolved; known-subset net−80,75/−947,46USD | `DATA_PATH_INCOMPLETE` cho full PnL và intraminuteDD; `PROP_UNMEASURED` | FullnetN/A; diagnostic controls, không winner; subset âm không thành full-period verdict |
| GoldR043 bên dưới | Tổng stress+4.035,06USD/15reset books50k,220closed | `CADENCE_OR_SAMPLE_SHORTFALL` cho measured baseline time-fit/current goal; `DATA_PATH_INCOMPLETE` cho target tick/DD; `PROP_UNMEASURED` | Original research retention vẫn pass10/15; chưa proven alpha/challenge |
| [TC01](US500-SAME-CLOCK-RESULTS-20261112.md) | 673signals; aggregate midpoint cũng âm, stress point component âm3năm | `ECONOMIC_FAIL` cho component; `PROP_UNMEASURED` | Gác exact component, ngoài hướngH1→M15; không account strategy |

**Không có ca nào trong bảng được gắn `PROP_VIOLATED`:** chưa có witness
profile/path đầy đủ tương ứng để kết luận chúng bị Daily/Overall DD loại.
Điều đó cũng không chứng minh chúng đã qua luật quỹ. `prop_qualified=false`
và null fullDD ở saved outputs vẫn giữ nguyên, chỉ interpretation được làm rõ.
Đây là bảng các ca được giao audit; không ép123catalogue records chưa cùng
stage vào một nhóm nhãn hoặc gọi mọi record là strategy đã backtest.

### Branch không phải đơn vị chiến lược

Tên dưới bỏ prefix`codex/` cho gọn; không rename/merge/delete branch trong lượt này.

| Nhóm branch lịch sử | Vai trò / kết luận |
|---|---|
|m15-standard-research-direction; us500-m15-research-focus; focused-research-lanes; us500-session-and-research-stages|Chốt phạm vi/timeframe/phiên/cách tìm; không economic verdict riêng|
|strategy-template-reuse-review; local-strategy-source-library|Rà nguồn/license/pin/full-framework assets; không alpha trials riêng|
|strategy-fit-review; us500-cadence-research; us500-frequency-review|Suitability/cadence; bản thưa bị giảm ưu tiên theo goal, không mặc định không edge|
|us500-opportunity-screen; us500-channel-history|Count-only/cohort/coverage; history bị data blocks, không kết luận lợi nhuận hoặc stablecadence mọi regime|
|us500-m15-rule-screen; us500-multiframe-study; us500-ma-reclaim-study|Có economic studies theo scope/model riêng; weaknet/cost/sample và target realism chưa đủ; dẫn kết quả gốc trong research index|
|us500-recent-discovery / PR66|Nhiều study/source/recovery/docs trong cùng branch, không một alpha. Recent fullnetunknown/negative diagnostics và audit kế thừa|
|Trader research-metals|Source input/coarse research support đã vào main; indicative Ask không thành observed Ask; không một chiến lược metals mới đã qualification|

## Gold R043: hồ sơ chẩn đoán

Exact recipe`xauusd-h4-sma20-80-atr14-r025-v1`: SMA20/80, SL2ATR14,
thoát khi mất hướng; mỗi sổ50k/plannedrisk125USD (baseline0,25%),
15annual resets2010–2024. Giá Bid M1 được gom; Ask/spread/slip/commission/
financing là declared model. H4 và giữ nhiều ngày khác nhánh H1→M15/intraday
hiện tại; nghiên cứu hồ sơ này không tự mở lại lane Gold.

| Chỉ số stress đã lưu | Kết quả / cách hiểu |
|---|---|
|Tổng net equity, có floating cuối từng sổ|+4.035,06USD; cộng15sổ riêng, không một account15năm/CAGR/lãi mỗi năm|
|Closed trades; wins/losses|220;53/167. Khoảng14,67closed/năm reset là thống kê mẫu, không tần suất signal/live đảm bảo|
|Năm net equity dương|10/15; giữ original retention, không tự chứng minh edge/OOS|
|Closed net / terminal floating / open financing|+2.579,62 +1.697,04 −241,60 =+4.035,06USD|
|Financing đã ghi toàn bộ|8.950,80USD; funding là77,75% cost-drag debits của closed trades dưới stressmodel, không77,75% netloss hoặc phí broker đã xác minh|
|Năm có closed-cash checkpoint≥5.000/2.500USD|0/15 ở cả hai mốc. Cashnet cao nhất sau đóng+2.168,91USD; không forceclose cuối mẫu|
|3/6/12tháng stress cashnet min→max|−527,85→+1.233,33 /−1.082,28→+1.589,49 /−1.930,54→+1.846,75USD|
|Concentration5winner lớn nhất|+8.668,57USD,39,25% positive-trade contributions; netannualsum trừ contribution đó−4.633,51USD chỉ descriptive sensitivity|
|Terminal còn position|5/15stressbooks; floating không là tiền closed đạt profit target|

Nguồn: [financial/time-fit review](GOLD-SMA50K-REVIEW-20261108.md),
[phân rã chi phí](SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md),
[signal review mới hơn](GOLD-SMA-SIGNAL-REVIEW-RESULTS-20261109.md).

### Rào cản cụ thể và điều kiện mở lại Gold

1. **Target cost/funding:** declared fixed commission/swap không là verified
   historical/current target account fees. Có publicspec follow-up, nhưng
   point/mode/units/account/historicalrates vẫn cần bind. Không tự thay phí
   để tạo outcome đẹp; nếu đổi economics thì version/scenario riêng.
2. **Time-fit/cadence:** tại baseline,15Jan-start books không có checkpoint
   closedcash đạt hai mốc tham chiếu5k/2,5k trong12tháng. Không là actualphase2,
   pass probability, mọi rollingstart thất bại hoặc mục tiêu bắt buộc của quỹ
   phải xong12tháng. Không chia target cho meanannualnet để dự đoán thời gian.
3. **Concentration:** trend có thể cần ít winner lớn; không loại5winner,
   BUY/SELL/holding cohorts sau outcome hoặc lấy phần bỏ chúng làm strategy mới.
4. **OOS/selection:**2010–24 đã exposed/selected; không clean OOS.220trades
   trong15reset years không tự đáp ứng precision/dependence của mọi câu hỏi.
5. **Prop/path:** indicative/coarse stop không là observed first crossing,
   intraminute equityDD hoặc target funding/news/closure/phase proof. Giữ
   nhiều ngày cần kiểm lifecycle tới payout của exactprogram, không chỉ evaluation.
6. **Source/port:** frozen financial source khác current code; không lấy
   current main rồi gọi là cùng baseline. Native Gold port cần admission riêng.

**Đã có, không làm lại:**30saved financialbooks đã đối soát; signal review
sau đó kiểm40.662H4 evaluations/616decisions/450entries qua cả hai scenarios,
không mismatch trong conditional recorded-position path. Old financialreview
JSON còn`signal_oracle=not_evaluated` là historical field; không sửa nó. View
mới dẫn evidence bổ sung, chưa nâng thành independent stop/path/edge proof.

Gold đáng giữ để giải quyết targetcost/time-fit, nhưng chưa có cơ sở ưu tiên
viết overlay thật hoặc tăngrisk nhằm đạt challenge. Việc gác hiện tại khác
`ECONOMIC_FAIL` và khác thu hồi original retentionpass.

## Năm cấu hình US500 stress dương

Lấy **đúng năm** trong27configs từ corrected summaryv3 bằng tổngstress>0;
đây là retrospective census theo yêu cầu owner, không retention gate mới.
Mỗi dòng cộng3sổ riêng10k/2022–24, plannedrisk≤25USD; không account liên tục.
PairedM1 Bid/Ask gồm spread; commission0 và slip0,75point/fill là scenario,
chưa targetFTMOcosts. Common arm10:00–10:45NY, confirmation tới11:00,
oneattempt/day; A=M15, B=thêm closedcashH1bias. Không có laneC/M5 trong năm bản.

| ID / exactconfig | Closed trades2022/23/24 | Net stress2022 /2023 /2024 USD | Tổng stress /mean closed mỗi năm | Lý do riêng chưa đi tiếp |
|---|---|---|---|---|
|R100 — M15, MA20/80, đệm0,20ATR|8 /5 /4 =17|+11,13 /+26,50 /−27,94|**+9,69USD** /5,67|Tổng rất mỏng; năm2024 âm; mẫu nhỏ. Cùng financial trace với R107 trong phạm vi đã lưu|
|R107 — thêmH1, MA20/80, đệm0,20ATR|8 /5 /4 =17|+11,13 /+26,50 /−27,94|**+9,69USD** /5,67|H1 chưa tạo khác biệt về các lệnh được nhận/kết quả ở cặp này; không thêm một edge độc lập|
|R118 — thêmH1, MA10/40, đệm0,10ATR|16 /10 /2 =28|+18,30 /−76,55 /+61,42|**+3,17USD** /9,33|Tổng gần0; năm2023 âm; năm2024 dương từ2lệnh. Chưa chứng minh độ ổn định/độ chính xác hoặc phí đích|
|R120 — M15, MA40/160, đệm0,10ATR|9 /2 /4 =15|+2,81 /+11,99 /+34,07|**+48,87USD** /5,00|Dương3năm nhưng chỉ15lệnh;142/157tuần không entry. Review cũ giữ inconclusive_small_sample|
|R121 — thêmH1, MA40/160, đệm0,10ATR|9 /1 /3 =13|+2,81 /−8,64 /+28,86|**+23,03USD** /4,33|Bản cóH1 tương ứng R120, còn ít lệnh hơn và năm2023 âm; chưa có bằng chứng H1 tăng chất lượng|

Tham chiếu [bảng27configs](US500-MULTIFRAME-FULL-TABLE-20261111.md),
[phạm vi simulation](US500-MULTIFRAME-RESULTS-20261111.md),
[R120 concentration](US500-R120-SAVED-REVIEW-20261112.md).

Tất cả năm bản còn chung: selection từ27related configs;2022–24 development
đã exposed; chưa clean OOS/uncertainty đủ; full intraminuteDD=null và
prop_qualified=false; targetfeed/spec/news/closure/phase/forward chưa qualified.
H1 cũ neo09:30cash; trước10:30 có thể carry bias phiên trước, chưa là
nativeMT5H1 hoặc manualstructure owner học. DùngR121 làm fixture phải giữ
đúng nghĩa này; đổi bias/clock là version riêng, không gọi là samebaseline.
Không suy năm âm thành violation hoặc hardreject khi protocol không có gate đó.
0unresolved/flat cuối của selectedM1books không chứng minh fulltickcoverage.

Đã đọc15selected stressbooks và seals/reviews/manifests, đối soát tradecount,
cash-net sums với annual/cohort/summary. R100/R107 khớp side, decision/entry/
exit timestamps, entry/exit/stop, quantity và cash trên đủ17trades. Năm configs
chỉ có4financial trace signatures quan sát được; **không gọi là4independentedges**.
Không cộng hai bản trùng, ba năm hoặc hai costscenarios thành sample độc lập.

## Gap matrix và test cases nhỏ nhất cho Bước 3

Đây là **thiết kế để xét bước kế**, chưa implementation hoặc test thực thi mới.
Baseline Trader930fa768 và Workspace420126c; financial artifacts vẫn own
frozen original source identity, không ngầm đổi pin sang hai HEAD này.

| Thành phần đã có | Capability đã đọc từ source | Gap khi dùng trong US500 research | Case tối thiểu cần chạy sau approval |
|---|---|---|---|
|[Policy](../../tooling/ai-engines/us500_multiframe.py)|Tách closedbar alpha/exit decisions khỏi submit/fill; shared policy injection cho studies|Chưa có contract intent→account-risk verdict tách biệt đầy đủ; currentbaseline làMA/cashH1, không mọi manualzone|RP01baseline vàRP09alpha/execution trace|
|[_PilotGuard](../../projects/trader/foundation_v2/trading_workspace_v2/forex_pilot_risk.py)|Quan sát equity trước/sau quote, daily/overall latch, remainingbudget admission, timezonePrague, transactional checkpoint|FX offline1position; không phase-adaptive sizing trong NautilusUS500; phải phân biệt internalstop với firmrule|RP02budget/lot/margin,RP03reset,RP04halt|
|[ForexPropObserver](../../projects/trader/foundation_v2/trading_workspace_v2/forex_prop_observer.py)|Profile money oracle, perquote metrics/firstbreach, reset/cash/phase progression và checkpoint|Chưa nối vào US500 native loop; midnight dùng lastobservedquote là modeledcarry, không quote quan sát đúng00:00|RP03cash/reset,RP05coverage,RP07resume|
|[prop_session](../../projects/trader/foundation_v2/trading_workspace_v2/prop_session.py)|Versioned phase/rule/profile, basis/reset order, transitions và immutable event state|Không tự là funded reward/sizing controller; không tạo state machine thứ hai hoặc auto accountauthorization|RP06phase/policy binding,RP08unknown/reservations|
|[replay_execution](../../projects/trader/foundation_v2/trading_workspace_v2/replay_execution.py) và[tick execution](../../projects/trader/foundation_v2/trading_workspace_v2/replay_tick_execution.py)|Ticksequence/side fills/SL/TP, partialclose và protection amendments với ledger/cost basis|Primitive đã có không là automatic2R/BE exit trongUS500; partial-fill accounting của runner chưa hỗ trợ vì nonentryfill hiện setposition=None|RP10baselineexit giữ nguyên; partial/BE cases riêng nếu scope sau mở|
|[Pullback/AdverseFill/quote model](../../tooling/ai-engines/us500_multiframe.py)|Native orders/cash,25USD stop budget/lot/margin, M1barrier envelope và endpointmark|Chưa đầy đủ accountwide daily/overall/pre-entry headroom, dynamicphase risk hoặc intraminute propDD; chưa calibrated targetlatency/slip|RP01native parity,RP02/04admission,RP05coverage/gap|

| ID | Fixture nhỏ nhất được đề xuất | Expected contract |
|---|---|---|
|RP01|Baseline25USD, cùngsynthetic BUY/SELL/timestamps/quotes, overlaydisabled hoặc equivalentconstantpolicy|Giữ signals/orders/fills/cash; không tuyên bố financialhistory parity bằng fixture|
|RP02|Daily/overallheadroom thấp hơnpertrade, costreserve, lotstep/minlot và margin boundary|Size xuống hợp lệ hoặc reject córeason theo policy khóa trước; khôngroundup qua budget hoặc dùng threshold của quỹ như riskbudget|
|RP03|Qua00:00Prague/DST, floatingloss, fee/swap trùngreset, có/thiếuquote tại boundary|Đúngbasis/order; dailyreset không xóaoverall; carriedquote ghi đúngmodel/unknowncoverage|
|RP04|Gần internalhalt threshold rồi gap/SL, cùngevent cóclose và riskcheck|Ưu tiên event rõ, latch/dừngentry đúngscope; không hứa không thể breach khi gap vượt allowance|
|RP05|KnownM1PNL nhưng không intraminuteDD; mộtheldgap; mộtobserved breach witness đúngprofile|PnLscope không bị tráo; chưađo khác violation; modeledwitness khác actualbroker; khôngpromote bằngnull/false|
|RP06|Phasepassed khi cònopen/pending vsflat; chọn policy đúngChallenge/Verification/Fundedprofile|Không đổi phase để xóa lỗ hoặc tự tăngrisk; phase/policy binding và reset semantics từ lifecycleowner|
|RP07|Checkpoint trướcreset/cash/phasechange; uninterrupted vsresume; saiidentity/profile/policy/source|Sameevents/equity/state trongscope; mismatch bịchặn, không normalizehash để épresume|
|RP08|Pending/unknownsubmission và incremental adverse risk của existingposition|Khôngdoublecount floatingloss, khôngrelease reservedrisk khi timeout, khôngbudget riêng từngbot; current1position limitation rõ|
|RP09|Cùng rawdata/alpha version, sizing thay admissions hoặc lot rounding|Rule/known-at không đổi; acceptedtradepath có thể đổi và phải replay, không nhânPnL cũ hoặc giả same trades|
|RP10|Fullclose/SL/timeexit baseline và primitivepartial/protection capability|Baseline không tự bậtpartial/BE. Nếu scopeexit sau mở: cònquantity/fees/protection/checkpoint đúng; currentUS500 handler không được xem làpartialready|

Không viết tất cả integration một lượt. Sau owner chọn scope: bắt đầu RP01/02/05
để khóa interface/coverage, rồi boundary/resume theo source bị tác động. Hiện
chỉ existing outputs và source reading là evidence; nhữngcase này **chưa chạy**.

## Khuyến nghị chọn đối tượng cho bước kế

**Chưa bản nào đủ để tối ưu risk với kết luận challenge-ready.** Gold có số
lệnh nhiều hơn nhưng nguồn indicative/holding lâu và cost/time-fit gap lớn;
US500 có native runner sẵn nhưng sample nhỏ. Hai vấn đề không giải bằng
chọn cấu hình có totalPnL cao nhất giữa các model/vốn/horizon khác nhau.

- Nếu Bước3 là **kiểm tích hợp kỹ thuật**, đề xuất dùng runnerUS500 đang có,
  R121 làm representative đúngH1→M15 và R120 làm saved comparator M15. Việc
  chọn fixture vì method/implementation fit không là promote hai strategy.
  Chưa cần nativeGoldport hoặc dynamicexit để kiểm risk contract tối thiểu.
- Nếu ưu tiên **giải quyết candidate kinh tế**, vớiGold nên đóng targetcost/
  funding và time-fit/model admission trước; không đầu tư overlay để biến
  một kết quả coarse dương thành đủquỹ. Muốn quay lạiGold lane phải ghi scope
  và protocol rõ; nghiên cứu hồ sơ không tự chuyển hướng khỏiUS500.

Owner quyết định Bước3 và candidate/scope sau khi đọc hai hồ sơ. Bước3–5
chưa bắt đầu. C1/C2 challenge vẫn chưa đạt; không automaticpromotion/Goal.

## Dấu vết kiểm chứng và giới hạn

Lượt này chỉ đọc savedresults, số học Decimal và hashes. Checked54artifacts:
summary/correctedcohorts,15selectedstressbooks cùngseals/reviews/manifests,
Goldfinancialreview vàlatersignalreview. Reconcile count/net từngnăm và
Gold15annualsum; duplicatefinancialtrace đã kiểm. Không đọcrawprices,
rerunsimulation, rerunoldtests hoặc tự mở outcomes mới.

Privateextractor/validation receipts ở campaign`execution-v1/qualification-step12-v1/`.
Source markdown cũ/costs/oldlabels/raw outputs/pins không sửa; JSON mới là
derivedview. Updatedreferences theo maintainer/skillcreator, không skill mới
hoặc globalsystemconfig; local links và structure/audit được kiểm trướcGit.
Không gọi same-agent arithmetic là independent human/feed hoặc full code audit.
