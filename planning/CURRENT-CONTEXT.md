# Current context — Naqex Workspace

15/11/2026 · `RESEARCH: PROP_COCORE_V4_COMPLETED_CONDITIONAL · PROP: NOT_QUALIFIED · HOLDOUT: CLOSED`.

## Việc hiện tại

**V4 đã hoàn tất, chưa payout hoặc sẵn sàng mở full holdout:**
[báo cáo](research/PROP-COCORE-V4-RESULTS-20261114.md) /
[JSON](research/PROP-COCORE-V4-RESULTS-20261114.json) /
[quyết định](research/PROP-COCORE-V4-DECISION-20261114.json) /
[protocol](research/PROP-COCORE-V4-PROTOCOL-20261114.md).
Task `d6d78dc3-c7e9-40ee-a684-61490c368f27`, branch `codex/prop-cocore-v4`,
private job `execution-v1/prop-cocore-v4-20261114`.
Tên campaign dùng ngày UTC 14/11, bàn giao ngày địa phương 15/11.

PR81 đã merge `5864d8b`, branch V3 xóa. Top10 chỉ xét Dev 2022–2023:
không third sleeve đủ source/scale/carry gates. GBP Asia/London có screen
dương nhưng chỉ H1, QDM không list GBP cached dataset. EUR thực tế có
Dev drawdown 35,757R so với net14,334R, không gọi đường vốn mượt.
Trong 13 cửa sổ V3 chưa xong vòng2, 7 dương/6 âm. V3 funded equity từng
50.379,30USD nhưng flat balance đủ14/30ngày cao nhất49.849,38USD.

Một trial co-core: hai nhánh $200/$175/$125 theo phase, cap mở1,6%,
reserve floor46k (8%), throttle4%/6% và daily halt2% giữ nguyên.
48 Dev accounts đạt: worststatic7,9359%, daily1,34082%.
Commit composition `8b1bfba` trước replay2024; không chọn theo2024.
144 V4 accounts (36starts ×2models ×14/30day proxies): ASYM quaP1 14/36,
qua2vòng3/36; SYM13/36 và2/36; payout0 ở cả14/30ngày.
Mỗi model chỉ một đường funded riêng, không độc lập. Worststatic7,994/7,995%;
daily1,280/1,341%; peak-to-valley14,365/14,468% vốnđầu. Không modeledbreach.
Caprejects0 nhưng reserve chặn nhiều hơn V3; không tăng risk tiếp để ép payout.

209 tests (12 fixtures V4), oracle144accounts/32.866 admissions/
10.102 rejects/104.985.511 jointquotes đạt. 72V3defaults tái hiện đúng cash,
DD,accepted/closed/rejects/lifecycle. Cùng implementer, không independent
human/model review. Không numericalwriter còn chạy; delivery/CI receipt tại job.

Chỉ QDM symbol metadata: EURtick quảng bá tới01/11/2026, EURM1 07/10,
GoldM1 13/10; Goldpairedticks2025–26 chưa được chứng nhận. Chưa fullwindow
01/2025–10/2026 hoặc pristineOOS certified. FAQ FTMO fetch lỗiTLS;14ngày là
request proxy, không currentofficial acceptance hay tiền nhận thật.
Giữ giá2025–26 đóng, VI DubberWIP/Traderpin; không broker/model/paid/Astra,
không auto-merge PR V4 hoặc chạy holdout/newcampaign.
Các trạng thái bên dưới là lịch sử, không phải hàng đợi thực thi.

## V3 đã merge

**V3 đã hoàn tất Phase 0–4, chưa đủ điều kiện Challenge:**
[báo cáo](research/PROP-PORTFOLIO-V3-RESULTS-20261114.md) /
[JSON](research/PROP-PORTFOLIO-V3-RESULTS-20261114.json) /
[composition](research/PROP-PORTFOLIO-V3-DECISION-20261114.json) /
[protocol](research/PROP-PORTFOLIO-V3-PROTOCOL-20261114.md),
task `ded836a8-3f42-4204-9742-9fc0ad3c369e`.
PR #80 đã merge `91dd2d5`, nhánh cũ xóa; nhánh giao V3
`codex/prop-portfolio-v3`, job `execution-v1/prop-portfolio-v3-20261114`.

Funding reserve chỉ dùng deadline biết trước, không nhìn exit tương lai.
Một trial D1 SMA50/slope5/0.5x làm giảm tỷ số Net/DD, giữ A_Original.
112 Natural-SL screens; 42 đủ đường cho M1 scenario. US500 khôi phục
715/732 endpoint cũ, 17 còn unknown; GBP/AUD thiếu M1/tick, USDJPY thiếu nguồn.
Lượt lỗi Ask=0 ở Gold giữ nguyên trong quarantine, không dùng để chọn.
Chỉ chọn `EURUSD.SWEEP.ASIA.LONDON.DAY`: tick Dev +3,7714R / +10,5621R,
112/124 lệnh, correlation ngày khoảng 0,10; cải thiện Net/DD ghép nửa ngân sách.
Composition commit `ec602f7` trước release/mở 2024; LF/CRLF preflight đã chặn
trước release, semantic/byte binding sửa rồi commit lại, không đổi tham số.
Historical Validation 2024 của EUR: 67 lệnh, +6,3371R; đã exposed, không clean OOS.

144 accounts (2 models × 2 systems × 36 monthly starts), cùng shared-account
lifecycle và joint paired ticks. Portfolio qua vòng 1 15/36 ở cả SYM/ASYM;
hoàn tất hai vòng 0/36 SYM, 2/36 ASYM, payout 0. Hai cửa sổ ASYM chỉ có
một đường funded riêng biệt: funded lỗ $1.096,26 cuối 2023, lãi $847,82
năm 2024, cuối mẫu $49.751,56. Không suy thành xác suất pass tương lai.
Worst static portfolio 6,998% / 6,997%, sát reserve nội bộ 7%;
worst daily 1,132% / 1,071%; không observed modeled breach.

197 tests (21 fixtures V3) và bốn đối soát đạt: 112 screens, 420 D1 decisions,
25.447.523 tick EUR khớp CSV gốc, 144 account ledgers cùng admissions/rejections.
Cùng implementer dùng phép tính khác; không reviewer người/model độc lập.
Giữ A + EUR để review hữu hạn tiếp theo, chưa Challenge/thu nhập chính:
không payout, top-trade concentration, completion phụ thuộc swap proxy,
actual target spec/news/margin/feed/forward còn thiếu. `prop_qualified=false`.
Không numerical writer còn chạy; CI/delivery receipt ở private job.
Giữ đóng giá 2025–2026, WIP VI Dubber; không broker/model/paid/Astra,
PR81 sau đó đã merge `5864d8b` theo chỉ thị V4; nhánh V3 đã xóa.

## V2 đã hoàn tất

**V2 đã hoàn tất phép đo, chưa đủ điều kiện Challenge:**
[báo cáo](research/PROP-ATLAS-V2-RESULTS-20261114.md) /
[JSON](research/PROP-ATLAS-V2-RESULTS-20261114.json) /
[quyết định đã khóa](research/PROP-ATLAS-V2-DECISION-20261114.json) /
[protocol](research/PROP-ATLAS-V2-PROTOCOL-20261114.md).
PR #79 đã merge `a42fb9f`, nhánh cũ đã xóa. Nhánh giao V2:
`codex/prop-stage0-atlas-v2`; private job `execution-v1/prop-atlas-v2-20261114`.

2024 BUY +14,689R / SELL −12,044R; 13 tài khoản cũ vòng 2 đều hết dữ liệu,
không vi phạm DD. CA1/CA2 không đạt đủ cổng Development, giữ A0.
Atlas 112 cấu hình / 5 tài sản: 84 đủ endpoint nhưng không qua cổng, 28 còn
thiếu endpoint; 0 sleeve. Stage-1/correlation N/A, không dựng portfolio giả.
Risk v2 trên 36 mốc tháng/mô hình: SYM qua vòng 1 2/36, ASYM 5/36;
không hoàn tất hai vòng, không payout. Worst static 6,157% / 6,083%,
worst daily 1,071% / 0,979%. Cổng dự trữ 7% chặn 0 lệnh.

176 tests và bốn đối soát số học đạt, gồm 72 tài khoản; cùng implementer,
không gọi là review độc lập bởi agent khác. Cổng dự trữ kế thừa dùng exit
đã biết cho funding; kiểm lại bằng deadline khóa trước không đổi admissions,
nhưng helper chưa đạt nhân quả cho vận hành. Decision JSON khóa private trước
replay, chỉ commit lúc báo cáo: sai lệch yêu cầu commit trước Phase 3 được ghi rõ.
Giữ A0 làm benchmark, chưa đủ Challenge/thu nhập chính. Năm 2024 đã exposed,
chỉ Historical Validation; không mở giá 2025–2026, broker/model/paid.
Giữ WIP VI Dubber; không tự merge PR V2, gửi Astra hoặc mở chiến dịch mới.

## Chiến dịch V1 đã hoàn tất

**Chiến dịch exit → sleeves → phase-aware36monthlystarts đã hoàn tất:**
[báo cáo duy nhất](research/PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114.md) /
[JSON](research/PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114.json) /
[protocol](research/PROP-QUALIFICATION-CAMPAIGN-PROTOCOL-20261114.md).
PR78merged`3307fae`; freeze`95e3709`, Devdecision/code`2e713c1`.
Không E1/E2/E3 hoặc S1/S2/S3 nào đủ cổng Dev; giữ A0, không sleeve.
Risk.50→.35→.25%: P1 8/36SYM,13/36ASYM; P2/payout0; observedbreach0.
Worststatic9,321/8,899%, không đủ buffer để khuyến nghị Challenge.
147tests +72accountoracles +2.464Fractioncostbridges đạt; cùng implementer,
không Astra/agentreview. Chỉ2022–23select;2024HistoricalValidation;
khônggiá2025–26/broker/model/paid. WIP VI Dubber nguyên vẹn.
Privatejob`execution-v1/prop-qualification-campaign-20261114`; không numericalwriter
còn chạy. Branch`codex/prop-qualification-campaign` chờ owner duyệt PR, không tự merge.

## Baseline trước chiến dịch

**Đã hoàn tất calendar + Historical Validation 2024 + rolling accounts cho A BOTH/noTP.**
PR77 merged `3406ed1`, nhánh cũ đã xóa. [Protocol](research/XAUUSD-A-HOLIDAY-VALIDATION-PROTOCOL-20261114.md) /
[báo cáo](research/XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.md) /
[JSON](research/XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.json).
Lịch freeze trước mở2024: Friday20:30, holidayguard17UTC, GoodFridayevecut;
không đổi tín hiệu/SL. Coverage103/103,107/107,98/98; không loại ngày theo outcome.
11M1revisions2024 sửa workingcopy trướcPnL, all308signals/SL identical;
giữ nguyên original và attempt1fail. Hai phút cótick thiếuM1 được ghi riêng.

Risk.30%, SYM+4,050/+13,795/+1,845R và ASYM+5,901/+16,462/+2,645R (2022/23/24).
Năm2022 giảm vì holidayflat: SELL04July từ+3,921R thành−0,333R ASYM;
BlackFriday24Nov2023 khôi phục+0,673R. Top3/year chiếm hơn toàn bộ net profit;
phần còn lại âm3năm. Không chọn SELL-only hay vá exit sau nhìnValidation.
36monthlystarts×2risks×2costs=144cases;12quarterstarts làsubset.
Risk.30%0/36quaP1; risk.40%2/36SYM,5/36ASYMquaP1;0casequaP2.
Không observedbreach 5%daily/10%static; risk.40%worstrollingstatic7,234/7,083%.
**Đề xuất gác khỏi đường Challenge hiện tại; giữ researchbenchmark.** Positive point
estimates không chứng minh edge bền/thu nhập chính. Chưa timefit hoặc fullpropqualified;
actualswap/minstep/news/margin/feed/calendar còn gap. Không mở2025–26/variant/risk/broker.
209/222midnightmarks cũ>60s; DD/daily là observed/carriedmarkconditional, không boundunknownquotes.

14newfixtures+18execution+12Stage0regressions và2negativeCLIguards đạt;
308firstpassage/1.232rationalcostbridges/12annualcostbooks directtick selfaudit đạt.
Không independent/ASTRA review. Privatejob `execution-v1/xauusd-a-validation-20261114`:
`execution-config-v2.json`, `source-snapshot-v1` code, `source-snapshot-v2` inputs,
`attempt-2/result.json` và `arithmetic-review.json`; không còn numericalwriter.
Branch `codex/xauusd-holiday-validation`, chưa được giao merge báo cáo mới.
Giữ WIPVI Dubber; Trader không đổi. Bước mới cần scope riêng; không tự tiêu holdout.

**Parent đã hoàn thành — không thay kết luận cũ:**
**Lượt mới được owner mở:** [XAUUSD H1 Stage-0](research/XAUUSD-H1-STAGE0-PROTOCOL-20261113.md),
3 recipe cố định (Asian breakout/H4-trend H1 reclaim/momentum), BUY/BOTH views.
[Kết quả](research/XAUUSD-H1-STAGE0-RESULTS-20261113.md) /
[JSON](research/XAUUSD-H1-STAGE0-RESULTS-20261113.json): Development2022–23,
seedNov2021; không giá2024–26 hoặc bot SL/TP/account replay. RawBOTH103/107,
116/136,61/85. Primary8h/24h/8h chưa pass; chỉ48h có observedmeans dương2năm.
Lead ưu tiên A/BOTH48h:+1,767/+1,326USD/oz stress saufunding, observed63/65;
raw103/107, SL11,512/8,667, giữ90,3%/76,6% ở12%. C/BOTH48h leadphụ,
nhưng2022chỉ32observed. Không candidatechallenge; endpoint48h missing không
ngẫu nhiên (229weekend/231missing), CIqua0 và48h là horizonphụ đã xem.
Funding proxy20/40USD/lot,weekdays22UTC,Wed×3 chưa targetverified.
Job `execution-v1/xauusd-h1-stage0-20261113/attempt-2` completed;19.722.614ticks,
114.803M1OHLC khớp sau1M1openrevision, H1/H4 và608signals identical.
Giữfailedattempt1/snapshotv1; registration-v2/snapshotv2 vàFractionselfaudit
1.976markouts/608entries/48summarygroups đạt;12fixtures+11regressions+2guards.
PR76 đã merge/xóa branch; verdict primary cũ giữ nguyên, follow-up ở bằng chứng mới bên trên.
Đây là campaign mới được giao, không phục hồi các B1 đã hủy hoặc tự bật Goal.

**Chiến dịch cũ đã đóng theo owner:** [STRATEGY-E2E](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md).
Owner chốt No-Go XAUUSD B1, hủy lượt chưa dùng; EURUSD B1 cũng đã hủy.
PR74 đã merge `f0aadae`, nhánh cũ đã xóa. Không mở biến thể, batch, holdout
hoặc goal mới. C1/C2 chưa đạt, chưa có ứng viên challenge; đóng chiến dịch
khác đạt mục tiêu lợi nhuận. AppGoal kiểm khi chốt sổ=null.
[Stage-0](../.agents/skills/strategy-qualification/references/validation-gates.md#stage-0-unconditional-markout--scale-screen)
là chính sách mới cho nghiên cứu sau này; không chạy hồi tố hoặc tự mở lại.
Các checkpoint và backlog bên dưới giữ làm bằng chứng lịch sử.

**PR69 đã merge, chuyển sang thiết kế từ ràng buộc:** mergeSHA`920b48a`,
nhánh`codex/gold-eurusd-portfolio` đã xóa local/remote. [R043fixture](research/GOLD-R043-REGRESSION-FIXTURE-20261113.json)
đóng băng source/evidence: `CADENCE_OR_SAMPLE_SHORTFALL` + `PROP_TIMEFIT_REJECTED`;
dừng tối ưu challenge, giữ làm regression khi có correctness/sourcecompatibility need.
[B2report](research/GOLD-CONTINUOUS-B2-20261113.md) giữ720conditionalpaths,
36tests/7parity,120stresscached30,81s;0nhóm hoàn tất2vòng trong24tháng.

**Checkpoint mới — Scale & Horizon Audit, chỉ Development 2022–2023:**
PR73 đã merge `f1fa995`, nhánh cũ đã xóa local/remote.
[Báo cáo](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.md) /
[JSON](research/XAUUSD-SCALE-HORIZON-AUDIT-RESULTS-20261113.json):
ma sát median0,3486USD/oz chuẩn,0,7486stress; slip chiếm53,43% median.
772/813tínhiệu loại phí; SLrawmedian1,958USD/oz, sàn liên tục≈5,935,
fillsmedian7,02. Giữ cùng37fills tới18UTC vẫn stress−211,86USD;
14fills SL6,5–8 tới18UTC:1TP/6SL/7right-censored. Median toàncohort chưa xác định.
Rawmarkout18UTC meanstress+0,365USD/oz, dayclusterCI[−0,845;+1,731], chưa edge;
không bác mọi tínhiệu M15. **Owner đã chốt No-Go/hủy B1**, không dispatch.
B0 vẫn ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL,
PROP_UNMEASURED. 10fixtures/2sourceguards/153passage/2.401markoutchecks đạt;
23.829.464ticks chỉ2022–23, không2024design/2025–26giá/ASTRA/broker.
Privatejob `execution-v1/xauusd-scale-horizon-audit-20261113/attempt-1` completed;
branch audit đã merge/xóa ở PR74; Traderpin/VIWIP giữ nguyên.

**Bằng chứng kế thừa — XAUUSD Intraday B0/A0:**
PR72 đã merge `7ee9ace`; nhánh `codex/intraday-funnel-audit` đã xóa.
Owner hủy EURUSD B1, không chuyển quota. [Kết quả XAU B0](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.md)
/ [JSON](research/XAUUSD-INTRADAY-B0-RESULTS-20261113.json): chỉ A0, Development2022–23
và historicalvalidation2024. Raw399/414/390 → fills24/13/30; stress
+156,13/−425,93/−451,15USD. ECONOMIC_FAIL + CADENCE_OR_SAMPLE_SHORTFALL;
PROP_UNMEASURED, strictfunded còn calendar/targetspecblocked. Không A1/B1.
30.403.243ticks đã kiểm;135.281phútOHLC khớp sau3sourcecorrections trướcoutcomes,
giữ originalcache/failedviews/snapshot.11fixtures +134scenario-trade bridges,
2.035.213floatingmarks self-audit đạt; không independentagentreview.
Privateattempt `execution-v1/xauusd-intraday-b0-20261113/attempt-1` completedconditional;
registration và source-snapshot-v2 đóng băng. Branch cũ đã merge/xóa ở PR73;
Traderpin/runtime và VIWIP giữ nguyên;2025–26giáclosed, không ASTRA/broker.

**Bằng chứng kế thừa — audit Development EURUSD:** PR71 đã merge
`7d29ce4`; nhánh `codex/eurusd-b0-study` đã xóa local/remote. Owner gác EURUSD B0
với `CADENCE_OR_SAMPLE_SHORTFALL` + `DATA_PATH_INCOMPLETE`; prop vẫn unmeasured.
[Audit phễu](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.md) / [JSON](research/EURUSD-FUNNEL-AUDIT-RESULTS-20261113.json):
chỉ EURUSD2022–23,517zones→62ngày/67signals→24fills;455zones không confirmation.
43costrejects có medianSL6pip, cần median9pip theo spread/lotfloor.
NO-GO dispatchB1; owner đã hủy lượt chưa dùng, không chuyển quota sang Gold.
[Card XAUUSD Intraday B0/A0](research/XAUUSD-INTRADAY-B0-PROPOSAL-20261113.md)
đã được owner duyệt và thực thi theo protocol mới dẫn ở trên. M1timestampquality2022–24 cho10/11/12ngày
thiếu đoạn>15phút, không gapnộiphiên>15phút; chưa certify calendar/Ask/tick.
Không EURUSD2024diagnostic hoặc giá2025–26; GoldA0 là scope được duyệt riêng.

**Bằng chứng B0 đã được kế thừa:** PR70 đã merge `0a8542ba`, nhánh
`codex/prop-target-envelope` đã xóa. [Protocol B0](research/EURUSD-B0-PROTOCOL-20261113.md)
và [registration](research/EURUSD-B0-REGISTRATION-20261113.json) khóa duy nhất
EURUSD H1→M15 breakout/retest: Development2022–23 + historicalvalidation2024.
Nativecost/sizing + observedtickpath. [Kết quả B0](research/EURUSD-B0-RESULTS-20261113.md)
và [JSON](research/EURUSD-B0-RESULTS-20261113.json): 13/11/6 lệnh ở2022/23/24,
stressmodel +22,01/+864,84/+12,59USD;95pre-costsignals,65costrejects.
CADENCE_OR_SAMPLE_SHORTFALL;2023 có sourcegap54,54phút lúc giữlệnh,
DATA_PATH_INCOMPLETE. Strictfunded còn BLOCKED_BY_CALENDAR/PROP_UNMEASURED;
không gọi conditionalnet là edge, fullpathDD hoặc khả năngchallenge.
Không EURUSDB1/GoldA1 hoặc risk0,40%. Privateattempt:
`execution-v1/eurusd-b0-20261113/attempt-1`: completedconditional,17fixtures,
60scenario-trade checks/19.482bar parity; giữ frozenattempt/reviews, không rerun
unchangedbatch. Numericalcheckpoint `d33d917`; postrun chỉ sửa writer/reviewguards.
[Prop Target Envelope](../.agents/skills/strategy-qualification/references/validation-gates.md#prop-target-envelope--profile-owner-ngày-13112026)
là ownerdesignprofile, khônguniversalstandard/officialFTMOrule hoặc runner đãenforce.
F/Rplan ưu tiên≤10%,trần12%;cadence≥60/năm ưu tiên120;25–40netR0/năm là dảikhởiđầu.
Planning12tháng cần50R0 ở0,30% hoặc37,5R0 ở0,40%;6tháng cần gấpđôi. DD15R0
không bảo đảm Daily; giữ daily<2,5%/staticloss<6,5%,strict6% làdesignaspiration.

Trần4alpha versions mới toànchiếndịch;B0+tốiđa1diag,A0+tốiđa1diag chỉdựphòng,
khôngreset priortrialhistory hoặcdispatchA tựđộng. Dev2022–23 vàhistoricalvalidation2024
đều previouslyexposed.2025–26 **CLOSED**, chưa chứng nhậnglobalcleanOOS; khôngđọcgiá.
ExactEURCatalogue13 gác,khôngportfolio. US500overlaypaused; chưapayout/candidatechallenge.
Không còn branch audit cần giữ sau khi merge; không gửiASTRA,
broker/ordercalls hoặcđổiTraderpin/runtime. Publichistory2022–24 đã cache theo grantA0.
VIWIP vàotherownedworktrees giữ nguyên. Không Goal/skill mới hoặcglobalconfig.
[Hồ sơ Bước1–2](research/STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md)
giữ taxonomy/gap/testdesign; đề xuất US500overlay cũ đã được owner gác.

Research mở rộng US500/EURUSD và cách dùng cả năm engine đã được khảo sát.
[Báo cáo chiều sâu/engine/milestones](research/STRATEGY-DEPTH-ENGINES-AND-MILESTONES-20261112.md)
đề xuất US500 chính/EURUSD phụ (80/20 công sức), một hypothesis mỗi lane;
FX trước hết rà oldevidence/readiness, chưa numericalprotocol mới. Đây là
đề xuất phân bổ, không tự đổi exactmethod hoặc bật nhiều broker runtimes.

Owner bổ sung: [lọc feasibility sớm](../tooling/ai-engines/STRATEGY-WORKFLOW.md#lọc-độ-phù-hợp-trước-khi-triển-khai-sâu)
trước code sâu/financialbatch; reuse/count-only khi thiếu cadence. Bản có edge
được xét sizing khác nếu stressDD/prop cho phép;0,25% chỉ baseline, chưa đổi risk thật.

**T1 US500 lịch sử vẫn chưa freeze card mới**, không tự chạy study sau hậu kiểm: hypothesis →
H1bias/clock/carry → M15zone/available_at → setup → trigger → risk/entry/exit.
US500/intraday/Standard là scope trước đợtA; lượt hiện tại ưu tiên GoldSwing
continuous/EUR economics/portfolio theo chỉ thị mới, không tự mở US500overlay.
Đề xuất chính là confirmedM15level→break→retest, giữ MA-arm comparator;
đây chưa là exactrecipe đã được owner chốt. [Research/spec gaps](research/H1-M15-ZONES-AND-AI-VALIDATION-20261112.md)
và [oldB/C spec](research/US500-MULTITIMEFRAME-DRAFT-20261111.md) dẫn luật cũ.

Owner đã chỉnh rõ H1→M15; không tự chuyển sang thống kê20ngày/market khác
ngoài phạm vi research mở rộng vừa giao; numeric mới vẫn cần protocol riêng.
R120 làM15laneA, R121 mới là counterpart cóH1. Bias cũ là closedcashH1close
soSMA20; trước10:30 cócarryphiên trước. Không giả đó là nativeMT5H1 hoặc
manualstructure đã được xác nhận. Zone cũ là nến hồi quanhMA, không OB/FVG.

## Bằng chứng nghiên cứu cần kế thừa

- [Catalogue](research/STRATEGY-CATALOGUE-20261107.md):123historicalrecords/
  88versions/53native, cộng scopedstudies; không đếm chúng là independentedges.
- [R120 savedreview](research/US500-R120-SAVED-REVIEW-20261112.md):15lệnh/3năm,
  stress+48,87USD trên3sổreset10k; cadence142/157tuần vắng, giữ researchphụ.
- [TC01 same-clock](research/US500-SAME-CLOCK-RESULTS-20261112.md):673signals,
  endpointstressâm3năm;park exactcomponent, giữnegativehistory, không lanechính.
- [BR01/RS02 diagnostics](research/US500-CONTINUATION-DIAGNOSTIC-RESULTS-20261112.md)
  giữnegative/unknowns; không quét tiếp ATR/channel/exitgrid để cứu.
- [Recent8setups](research/US500-RECENT-SCREEN-RESULTS-20261112.md):2025selection,
  RS01/RS07 đã2026diagnostics; fullnetN/A doheldgaps. [Gap probe](research/US500-RECENT-GAP-RESULTS-20261112.md)
  chưa khôi phục phút thiếu; khôngdrop/ffill. Exposure/permission tùy protocol.
- GoldR043/FX/portfolio và các nhánh khác ở [researchindex](research/README.md)
  và [backlogQ1–Q12 của task](research/CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md#những-việc-xét-sau-đã-đưa-vào-task),
  không tự resume từ “bước tiếp” lịch sử.

Privateevidencebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`.
Giữ failedattempt/raw/seals/snapshots. Reuse khi đúngbinding; sửa luật là trial
mới, sửa bug chỉ rerun affectedscope. Không nối annualreset thành CAGR hoặc
pricecomponent thành accountPnL. Dataset đã xem không tự thành cleanOOS.

## Đọc theo phạm vi và quyền

| Việc | Authority / đường đọc |
|---|---|
|Task nghiên cứu hiện tại|TaskSTRATEGY-E2E → đúngstage → protocol/results/artifacts; [workflow](../tooling/ai-engines/STRATEGY-WORKFLOW.md) giữ phương pháp|
|Trader source/UI|[ProductPlan](trader/PRODUCT-COMPLETION-PLAN.md) → [entrypoint](trader/EXECUTION-ENTRYPOINT.md) → ledger; không thay bằng researchplan|
|Runtime/MT5/Paperclip|[Operations](../tooling/ai-engines/OPERATIONS.md), đúngruntime skill/owner; reconcile jobs/unknown submissions trước restart|
|Context/skills|[Lifecycle](CONTEXT-LIFECYCLE.md), [maintenance](../docs/development/SKILL-MAINTENANCE.md); không globalconfig/manager mới|
|Project khác|AGENTS/README của đúngrepo; không sửa/commit WIP VI Dubber hoặc restart integration từ audit này|

Auditdoctor đọc được4integration sources đúngpin/license; configuredPaperclip
health endpoint unavailable. Không kết luận mọi runtime hỏng, không tự start/
restart trong audit. Broker/target account/production chưa được acceptance.
Lượt mới đã có fixed-trade M1diagnostic được owner giao; không strategyjob mới,
holdout2025–26, install hoặc lệnh broker. Không promote/runtime từ kết quả này.

Ngoài nativePaperclip task/runstate và existingreceipts không tạo tracker/UI
cạnh tranh. Research/plan không cấp OrderCheck/OrderSend/account/provider/
paid/deploy/delete quyền mới. Giữ đúng authorization/accountscope khi tớiT7–T9.

## Lịch sử và khôi phục

[Snapshot trước audit](archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md),
[campaign trước audit](archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md) và
[manifest](archive/2026-11-12-strategy-e2e/MANIFEST.json) giữ trạng thái/nextactions
cũ; chỉ đọc khi truy why/regression. OriginalGit`2b52c79763b1653ea9cf96dba40ce5eaafa3e341`.
Các archive cũ hơn vẫn được giữ; ưu tiên task/stage hiện hành để resume.
