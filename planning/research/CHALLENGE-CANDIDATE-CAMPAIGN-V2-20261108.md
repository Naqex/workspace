# Task tổng: US500 H1–M15 → kiểm chứng → challenge → payout

**ID: STRATEGY-E2E · Owner: chủ project · Thực hiện: agent phụ trách · 12/11/2026.**
Đây là task/PLAN chính của chiến dịch, thay phần điều hướng lịch sử trước audit.
Native Paperclip vẫn sở hữu task/run khi được dùng; protocol/artifact của từng
study sở hữu số liệu. Không tạo dashboard, ledger hoặc Goal song song.
App Goal được kiểm trong lượt audit: `null`; task này không tự bật Goal.

## Mục tiêu và phạm vi đã xác nhận

Tìm chiến lược tự động có bằng chứng đủ để đề xuất challenge, vận hành funded
và hướng tới reward thực nhận với rủi ro thấp. Owner muốn đây là nguồn thu chính
và ưu tiên tiếp cận vốn quỹ lớn; thu nhập/độ ổn định phải kiểm riêng, chưa có
chiến lược đạt hoặc bảo đảm sẽ tìm được bằng một số lượt thử cố định.

- Hướng hiện tại: **US500, H1 bias → M15 zone/setup → entry**, intraday.
- FTMO CFD **2-Step Standard** là mục tiêu chính; The5ers là nhánh đánh giá
  riêng. Không trộn luật 1-Step/Futures/Swing/Classic/New hoặc challenge/funded.
- Ưu tiên từ2022 trở đi và gần hiện tại; lịch sử xa dùng stress có câu hỏi.
  2022–24 đã exposed;2025 đã selection ở studies khác;2026 exposure tùy recipe.
  Mỗi study cần consumedmap/protocol riêng, không tự gọi một năm là unseen.
- Ngân sách25USD/10k (0,25%) là baseline offline đã dùng, chưa là lot/risk thật
  được chốt cho tài khoản hoặc trần bất biến. Ứng viên có edge nhưng return
  thấp được xét sizing khác khi còn đủ stressDD/headroom; không tăngrisk cứu
  netedge âm. Nhịp3–5/tuần là ưu tiên thiết kế, không quota có edge.
- AI giúp research/spec/code/review. Hành vi signal/risk/fill cần tái hiện được;
  không cho model tự đổi strategy/authorization ở mỗi lệnh.
- Các đề xuất retest/FVG/OB và defaults mới vẫn là hypotheses, không coi owner
  đã chọn exactrules từ việc đồng ý research hoặc yêu cầu task tổng.

### Research chiều sâu và cách dùng engine — yêu cầu bổ sung12/11

Owner mở câu hỏi nghiên cứu US500/EURUSD/asset khác, kế thừa backtests và
phối hợp năm engine trước task lớn. [Báo cáo đã hoàn tất trong scope](STRATEGY-DEPTH-ENGINES-AND-MILESTONES-20261112.md)
giữ chẩn đoán, nguồn, engine gaps và milestonesA–F nốiT1–T9/Q12. Khuyến nghị
US500 chính/EURUSD phụ,80/20 **công sức**, một hypothesis mỗi lane; FX ban đầu
chỉ rà evidence/readiness. Đây là đề xuất triển khai, chưa freeze recipe,
mở data mới, cross-engine parity hoặc thành tích kinh tế mới. T1 vẫn là
bước tiếp; không chờ hoàn thiện cả năm engine mới kiểm một hypothesis.

Checkpoint từ nay báo card→technicalpass→economicsurvivor→fresh/robust→demo
→challenge/payout cùng blockers, tách số trials/books; hiện0candidatechallenge.
Trước engine kiểm chéo đích, khóa phí/qty1–2–3/timing/SL/gap fixtures: old
smoke size2 có fee formulas khác nhau nhưng cùng số, chưa size-generalparity.

**Điều chỉnh owner12/11 — lọc sớm và sizing:** trước code sâu/native batch,
T1–T3 phải có [feasibility verdict](../../tooling/ai-engines/STRATEGY-WORKFLOW.md#lọc-độ-phù-hợp-trước-khi-triển-khai-sâu)
cho cadence/thời gian thu mẫu, code/causality, data, costs/fill, risk/RR/prop
và effort. Reuse old evidence hoặc count-only nhỏ để gác sớm bản không hợp
mục tiêu; chưa biết thì probe có budget, không full backtest để mới phát hiện
quá thưa. Giữ reason/history; không sửa frozenfloor hoặc bác edge hồi tố.
T5 có nhánh sizing cho survivor/near-miss có cơ sở: baseline0,25% không tự
loại bản có thể đạt mục tiêu ở risk khác trong safe envelope. RR cao/ít trade
không là hardfail chung; risk selection dùng account/equity replay khi cần,
khóa trước T6. Đây là workflow, chưa runner enforcement hoặc risk thật mới.

## Rà soát hệ thống: sai ở đâu, thiếu ở đâu?

Audit này rà luồng scope→data→code→simulation→validation→operations→handover,
đối chiếu source/tests/evidence và health check; **không là full code/security
certification, mọi module đã reruntest hoặc chấp nhận broker/runtime đích**.

| ID / ưu tiên | Phát hiện và độ chắc | Xử lý / gate còn lại |
|---|---|---|
|F1/P0|**Đã xác minh lệch hướng:** agent chuyển sang TC01 dù owner muốn H1→M15; R120 laneA không có H1|Quay lại scope owner; R121 mới là counterpart cóH1. TC01 giữ negativehistory, không tiếp tục như hướng chính|
|F2/P0|**Đã xác minh phân mảnh context:** CURRENT475dòng và campaign329dòng có nhiều next/latest cũ; workflow còn dẫn UIprototype làm scope|Snapshot hai bản trước; task tổng này giữ một thứ tự/stage; context chỉ route, protocol/results cũ giữ nguyên|
|F3/P0|**Đã xác minh sai tài liệu:** M5 draft ghi3M1, code `prepare` thực tế gom5M1|Sửa mô tả thành5M1, ghi correction; không sửa code/protocol tài chính hoặc rerun market history|
|F4/P0|**Semantic gap:** H1 cũ neo09:30cash, trước10:30 có thể carry phiên trước; chưa là H1 nativeMT5 hay cách bias owner học|T1 phải ghi clock/closedbar/carry/definition; mismatch là thay semantics/version, không tự gắn nhãn codebug|
|F5/P0|**Semantic gap:** zone cũ là nến hồi quanhMA; zone/setup/trigger và exact manualrule chưa chốt|Một strategycard trước code/PnL; comparator giữ nguyên; zone mới có available_at, expiry và selection rule|
|F6/P0|**Đã có source gaps:** recentbooks có fullnetN/A; TC01 đủ endpoints vẫn có2holdingwindows thiếuM1|T2/G1 giữ unknown; recovery/bounds chỉ đúng scope đăng ký; không drop/ffill để pass|
|F7/P0|**Chưa đủ target realism:** index cost scenarios declared, source proxy khác tài khoản FTMO đích|T2/T6 phải bind targetspec/fees/session/news/profile. Net theo scenario chưa là broker proof|
|F8/P0|**Chưa full prop path:** US500native runner không tự đánh giá toàn bộ lifecycle quỹ; `prop_profile.py` kiểm DD/headroom từ snapshot|Reuse existing prop lifecycle modules rồi kiểm connection theo profile cụ thể; DDsnapshot không thay intrabar/news/days/phase/reward|
|F9/P1|**Health đã đo:**4integration sources đúngpin/license/clean; doctor không truy cập được Papercliphealth theo configuredendpoint|Reconcile đúngruntimeowner trước khi sửa/khởi động. Offline research tiếp tục; chưa công nhận Studio/live healthy|
|F10/P1|**Có bằng chứng trong scope:** native accounting, causal fixtures, seals/reviews/reuse đã có; chưa chứng nhận toàn hệ thống|Giữ và dùng lại; chỉ chạy affectedchecks/reruns. Same-agent arithmetic khác independentfeed/person|
|F11/P1|**Quy trình có nguy cơ overfit:** thử/chọn nhiều biến thể trên exposeddata; sửa đến khi xanh không là kiểm định|T4–T6 tách exploration/validation, giữ mọi trial; vòng lặp hữu hạn, không reset exposure hoặc tăngrisk để cứu|
|F12/P2|**Chưa thấy lý do thêm hạ tầng:** các probe mới tính/review trong khoảng30s; chưa đo end-to-end research bottleneck đầy đủ|Ghi timing từngphase; profile khi có chậm thật. Không mặc định Rust/GPU/RAG/engine mới là bước tiếp|

Nguồn đọc: [H1/M15 research](H1-M15-ZONES-AND-AI-VALIDATION-20261112.md),
[protocol](US500-MULTIFRAME-PROTOCOL-20261111.md),
[code](../../tooling/ai-engines/us500_multiframe.py),
[prop snapshot](../../projects/trader/foundation_v2/trading_workspace_v2/semantics/prop_profile.py),
[existing lifecycle tests](../../projects/trader/foundation_v2/tests/test_ps02_prop_lifecycle.py),
[cadence/entry/recent evidence index](README.md). F8 không có nghĩa các prop
modules khác không tồn tại; khoảng trống cần kiểm là tích hợp đúng pipeline.

## Một luồng chiến lược rõ ràng

**Giả thuyết → H1bias → M15zone → setup → trigger → risk/admission → order/fill
→ SL/exit → accounting/reconciliation → đánh giá.**

| Thành phần | Phải ghi trước outcomes |
|---|---|
|Giả thuyết|Vì sao có thể có lợi nhuận, khi nào bị bác; priceproxy khác proof orderflow|
|Bias H1|MA/cấu trúc cụ thể, stream/timezone/baranchor, closedbar, thời điểm biết/carry/neutral|
|Zone M15|Định nghĩa vùng, anchor, available_at, biên, lựa chọn khi nhiều vùng, expiry/invalidation|
|Setup|Chuỗi tình huống như break→retest; điều kiện hợp lệ cùng bias, không chỉ “chạm vùng”|
|Trigger|Nến xác nhận nào, BUY/SELL, strict/equality, M15 trước; entryTF khác là bản riêng|
|Risk/admission|SL, plannedrisk/cost/minlot/margin/accountwidebudget, pending/unknown/news/closure guards|
|Entry/fill|Market/limit/stop, knownat/decision/fill, BidAsk, latency/slip/reject/gap semantics|
|Exit|SL/TP/trailing/time/trendlost cụ thể; RR là thuộc tính recipe, không ép chung mọi họ|
|Sổ và kết luận|Cash/equity/floating/fees, nguồn vốn mẫu số; correctness/edge/prop/operations/authority tách riêng|

Mỗi version dùng một card tự đủ và link source/protocol. Log cần trả lời được
“vì sao vào/không vào/thua”, gồm data block và không có setup; không log mỗi tick.
Bar gắn nhãn quá khứ chỉ được dùng sau available_at. R120/R121, MAproxy/zone
structure, entryM15/M5 không được tráo tên hoặc mặc định có cùng trade set.

## Đích và cách biết đã đạt

- **C1 — ứng viên:** đủ evidence về netedge/uncertainty, targetcost/risk/time-fit,
  prop path và prospective reconciliation để đề xuất challenge đúng profile.
- **C2 — quy trình:** rules/code/data/cost/pins/trials/selection/unknowns có thể
  kiểm lại; materialbugs đã xử lý; regression/independent codepath phù hợp.
- **Bàn giao:** owner giải thích được lúc trade/đứngngoài/cắt lỗ và cách dừng
  hoặc phục hồi. Thiếu kinh nghiệm trade tay không thay bằng lời agent “đã đạt”.
- **Kết quả thực tế:** qua challenge/funded và reward chỉ công nhận từ record
  thực nhận; 1payout chưa chứng minh thu nhập chính ổn định. Theo dõi net sau
  phí/retry/operation và sinh hoạt; không coi balance danh nghĩa là vốn sở hữu.

C1/C2 hiện **chưa đạt**. Audit/plan hoàn tất không là hoàn tất trading goal.
Nghiên cứu có thể kết thúc một chu kỳ bằng “chưa có candidate”; không hạ gate
hoặc kéo dài vô hạn trên cùng dữ liệu để tạo một kết quả dương.

## Một task tổng, các chặng thực hiện theo thứ tự

Trạng thái dưới đây là planning checklist của task này; native run/receipt giữ
trạng thái thực thi thật. Không tự tạo một issue/chat/agent cho mỗi hàng.

| Chặng | Việc cần làm / đầu ra | Điều kiện đóng | Hiện tại |
|---|---|---|---|
|T0 Rà và tinh gọn|FindingsF1–F12, authority map, archive nguyên lịch sử, scopeguard cho agent|Links/preservation/skill audit và resume walkthrough đạt|**Hoàn tất audit trong scope**; tiếp T1|
|**T1 Chốt một bộ luật**|Feasibility review trước code sâu; card H1→M15→risk/exit, clock/carry và comparator|Fit/unknown có verdict; luật/examples rõ; thiếu cadence dùng count-only ởT2–T3 trước financialbatch|**Bước tiếp bắt buộc**, chưa freeze recipe mới|
|T2 Data và target model|Inventory/reuse source; gaps/quality/availability; contract/fees/session, accountprofile/ruleversion và exposuremap|Đủ cho stage đã đăng ký; unknown không thành0; cost scenario khác actual target được gắn nhãn|Partial assets; target admission chưa đủ|
|T3 Code và kiểm kỹ thuật|Reuse nativeengine/runner; zone event lifecycle; oracle/prefix/mutations, BUY/SELL/equality/gap/reset/order/cash fixtures|Không material timing/state/accounting bug; kỹ thuật pass không thay C1|Old checks có evidence; zone mới chưa implement|
|T4 Sàng lọc nhỏ|Khóa hypothesis/rules/window/metrics/budget; count→financialscreen→cost/control/attribution|Giữ/gác/inconclusive có lý do, đủ mẫu theo câu hỏi; không quota lệnh/winner|Blocked bởi T1–T3 cho recipe mới|
|T5 Kiểm độ bền có chọn lọc|Horizon/regime/cost/delay/gap stress, concentration/dependence; risk/RR/entry variants khi có hypothesis|Evidence phù hợp selection và sample; không grid để cứu loser; version/trial giữ|Chỉ mở cho survivor/near-miss có lý do|
|T6 Kiểm mới và luật quỹ|Protocolchronological/freshfrozen/forward nếu chưa có cleanholdout; full equity/news/closure/phase/day/target lifecycle, time-fit3/6/12m|C1/C2 review đúngscope, mọi targetblocker xử lý hoặc không promote|Chưa candidate; không mở2025/26 ngầm|
|T7 Vận hành và bàn giao|Đúng owned runtime/account; health, status, stop/restart/unknown-order/reconcile, backup/restore, shadow→demo theo authority|Signal/order/fill/cost/model divergence trong bound đã khóa; recovery thật và owner runbook|Studiohealth chưa đạt; broker acceptance chưa audit lượt này|
|T8 Quyết định challenge|Một packet C1/C2, owner understanding, risk/fees/time-fit/stop criteria, profile exactfirm/phase/size|Đủ bằng chứng để đề xuất; mua challenge/gửi lệnh cần quyền cụ thể khi tới bước đó|Chưa đủ điều kiện, không mua hoặc gửi lệnh trong task audit|
|T9 Challenge → funded → payout|Vận hành cùngversion, dailyreconciliation, kiểm rulephase mới, payoutnet/fee/withdrawal/reset handling|Record actualpass/funded/reward và hậu kiểm; mở rộng vốn sau quan sát riêng|Chưa thực hiện; không hứa lợi nhuận hoặc ngày hoàn thành|

**Đọc tiếp ngay:** T1 → [H1/M15 proposal](H1-M15-ZONES-AND-AI-VALIDATION-20261112.md)
→ [oldB/C spec](US500-MULTITIMEFRAME-DRAFT-20261111.md)
→ [saved fulltable](US500-MULTIFRAME-FULL-TABLE-20261111.md). Agent tự đề xuất
một defaults có lý do dễ đảo ngược; không bắt owner chọn chi tiết nhỏ hoặc
lấy sự chưa biết của owner làm quyền tự thay cả phương pháp.

## Vòng lặp cải tiến và kiểm hồi quy

| Loại phát hiện | Vòng xử lý bắt buộc |
|---|---|
|Bug kỹ thuật|Tái hiện→fixture bắt lỗi→sửa→focused regression→review sourcepins→rerun phần bị ảnh hưởng; giữ fail/oldoutput|
|Code tối ưu giữ semantics|Đo bottleneck→sửa bounded→so event/fills/cash/unknown parity→benchmark cùngworkload; không chỉ so net|
|Đổi luật/zone/bias/risk/fees|Giả thuyết trước outcome→newversion/parent→development/screen→robustness/validation đúng exposure→giữ/gác; không gọi là bugfix|
|Lỗ đúng luật|Phân rã theo costs/signal/state/regime có evidence; một trade thua không buộc sửa strategy|
|Sai model so live|Dừng theo ops/riskpolicy→reconcile submitted/unknown→đo mismatch→sửa source/model contract→regression/shadow lại; không gửi lại khi chưa biết order cũ|

Mỗi T4–T6 study khóa budget/stop trước outcome. Mỗi lần review đề xuất tối đa
1–2relatedhypotheses có lý do trong lane hiện tại, không tự chạy toàn backlog.
Sau hai chu kỳ đổi luật cùng nhánh không tạo evidence mới hữu ích: checkpoint
lý do/unknown/chi phí và đề xuất tiếp, không thêm filter hoặc tự đổi market.
Đây là giới hạn phân bổ công sức tương lai, không economic rejection hồi tố.
Nếu thiếu dữ liệu/quyền thì làm phần độc lập; không giả pass hoặc dùng thời
gian chờ làm authorization. Dữ liệu đã xem không được “reset” bằng rename/fork.

## Những việc “xét sau” đã đưa vào task

Các mục Q là dependency-gated work của task tổng, không tự dispatch. Mỗi khi
mở phải ghi trigger/evidence, version và stage/permission phù hợp.

| Mục | Công việc | Khi nào mở / quay về chặng nào |
|---|---|---|
|Q1 BiasH1cấu trúc vsMA|Định nghĩa pivot/confirmation/neutral/carry và so cùngM15setup|Khi T1 xác định method mismatch hoặc câu hỏi riêng sau baseline; T1→T3→T4|
|Q2 EntryM5|So M15 với M5 trên cùngH1/zone/risk/exit, causal timestamps|Sau T3 và có lý do entrytiming ảnh hưởng chi phí/payoff; đăng ký T4, không chỉ vì khung nhỏ hơn|
|Q3 EntryM1|Đánh giá thêm timing/granularity/cost/latency|Sau Q2review chỉ ra value còn thiếu, source/tick/order semantics admitted; T2→T4|
|Q4 FVG|Một representative causal three-bar zone, birth/merge/mitigation/expiry|Sau T3baseline và T4primary đã có quyết định; ghi lý do riêng trước numeric, T1→T4|
|Q5 OB/supply-demand|Exact zone choice/displacement/knownat, code/license/source audit|Sau Q4triage hoặc có method cụ thể đủ rõ; không assume OHLC biết lệnh tổ chức; T1→T4|
|Q6 Risk/RR/SL/TP|Sizing sensitivity cho bản có netedge/evidence đáng giữ; đổi exit là strategy version khác|Risk envelope sơ bộ ởT1; sauT4 so sizing/accountwideDD/time-fit tạiT5, freeze trướcT6. Không hạ edgegate hoặc tăngrisk cứu net âm|
|Q7 Portfolio|Alpha/hedge roles, aligned returns/shared-account replay/exposurebudget|Khi có ít nhất các sleeves có lý do và owner mở scope; T5/T6; không cộng standalonePnL|
|Q8 The5ers/EURUSD/asset khác|Profile/source/method/cost riêng; US500 vẫn mainlane|Owner12/11 đã mở research mở rộng; EURUSD evidence/readiness được khảo sát. Financialtrial cần T1–T3/protocol/budget riêng; chưa dispatch. The5ers sau candidate FTMO đáng chuyển và exactprogram được chọn; T1/T2/T6|
|Q9 Engine khác/Rust/GPU/RAG|Admit capabilitygap/profile, boundedprototype/parity/benchmark/rollback|Chỉ khi bottleneck đo được có ảnh hưởng, không thay incumbent để kiếm edge; reuse full-framework assets hiện có|
|Q10 PaidEA/provider/cloud|Legal reference/preset, source/spec/permission/cost/rollback|Khi có gap đo được và authority/chi phí phù hợp; không mua/cài tự động hoặc suy hiệu suất từ ads|
|Q11 Vận hành lâu dài|Giám sát thụ động, runbudget/tokenbudget, logsretention, backuprestore và sessionreuse|T7 trước sử dụng thực; dùng nativeUI/status đã có, không thêm manager/dashboard song song|
|Q12 Thu nhập/payout/scaling|So netincome theo vốn/risk và3/6/12m, cashreserve/retryfees, account reset/counterparty|T8/T9; hypotheticaltargets không dự báo income. Tăng vốn/portfolio chỉ sau thực chứng riêng|

## Theo dõi tiến độ và quyền sở hữu

Mỗi run có PID/attempt/phase/counters, UTCtime, protocol/source/inputhashes,
log/checkpoint/deadline/cancel và receipt. Reuse theo binding; completed phải
qua accounting/artifacts. Worker không tự đọc skill mới hoặc mang instruction
mới vào một run cũ. Status stale khác processdead; không autorestart/mua/lệnh.

Owner cần nhìn được: **đang làm T nào → đã qua cửa nào → còn thiếu gì → lỗi ở
đâu → bước tiếp**. Logbook perrun và nativePaperclip giữ event/runstate, task
này giữ scope/dependencies. Numeric run dài mở status/terminal phù hợp; hiện
chỉ đọc health và tài liệu, không khởi động job/service. Không có ETA đáng tin
cho edge; ghi actual/estimate riêng và báo tiến độ theo phase thay vì hẹn1h
mới biết một lỗi chuẩn bị. Forward cần thời gian thật, warmup quá khứ có thể
reuse khi có binding; không rút gọn forward bằng replay rồi đổi nhãn.

## Nguồn phương pháp và luật đã kiểm 12/11

Kiểm chứng lượt audit:554localreferences/6anchors vào targets đã sửa hợp lệ;
2originalworkingbyte snapshots nén gzip có hash khớp, Gitblobhash tách riêng;
narrative archives giữ nguyên ngoài header/relocatedlinks. Numericalcode,
frozenprotocol và catalogue so vớibaseline`2b52c79` giữ nguyên. Workspace
contracts9guides/8pins đạt. Skillquickvalidator đạt trênbundledPython; product
venv thiếuPyYAML không bị cài thêm. Maintainer0errors/warnings,21skills,
global12.279B,project10.298/65.536B,reserve55.238B,combined22.577B.
Privateauditreceipt ở campaign `execution-v1/strategy-e2e-audit-v1/` giữhealth,
validation script/result. Không numeric/strategy/broker test mới trong audit.

- [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide): hypothesis trước code, nhận diện scope drift/overfit; không dùng bảng heuristic platform làm chứng chỉ.
- [Freqtrade lookahead](https://www.freqtrade.io/en/stable/lookahead-analysis/) và [H1/M15 source review](H1-M15-ZONES-AND-AI-VALIDATION-20261112.md): mượn kiểm causality/prefix/availability, không đổi sangFreqtrade hoặc coi chartlabel là livefeature.
- [FTMO objectives](https://ftmo.com/en/trading-objectives/): 2-Step có target10%/5%, daily5%initial, overallstatic10%,4minimumdays; balance/equity/reset và ruleversion phải đúng phase/package. Không copy1-Steptrailing/consistency sang2-Step.
- [FTMO news](https://ftmo.com/en/faq/can-i-trade-news/) và [holding](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/): phase Challenge/Verification vàSwing có exceptions; fundedStandard có restrictedexecution±2min cho targetednews, gồmSL/TP; breaks>2h có hạn chế. US500.cash có trong affectedUSindices. Design hướng payout cần kiểm fundedconstraints ngay cả khi evaluation cho phép.
- [The5ers HighStakes](https://the5ers.com/high-stakes/) và [DDFAQ](https://the5ers.com/faqs/what-is-the-drawdown-rule-for-high-stakes/): dailybase dùng higher prior balance/equity lúcservermidnight, khácFTMO. Classic/New/account terms cần bind riêng; publicpage không đủ targethistoricalspreads/spec.

Không có nguồn nào bảo đảm một workflow hay AIagents tìm ra edge. Quy trình
phải vừa có cơ sở kiểm chứng, vừa bám mục tiêu owner; testpass không là payout.
Ba linkFTMO trên là summary theo ngày, không sửa config hoặc chứng nhận tài khoản.
BaileyPBOPDF fetch timeout trong lượt này; không nâng ngày xác minh fullpaper cũ.

## Lịch sử, authority và khôi phục

[Campaign trước audit](../archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md),
[context trước audit](../archive/2026-11-12-strategy-e2e/CURRENT-CONTEXT.before.md)
và [manifest hashes/originalGit](../archive/2026-11-12-strategy-e2e/MANIFEST.json)
giữ lịch sử329/475dòng. Protocols/sourcebooks/data/trials/negatives không đổi;
originalbytes truy được tạiGit`2b52c79763b1653ea9cf96dba40ce5eaafa3e341`.
Productscope/runtime/executiongrant vẫn do ProductPlan/entrypoint/owner quản lý.

### Goal cập nhật — 09/11/2026

Anchor giữ cho caller cũ. Đây là [checkpoint lịch sử](../archive/2026-11-12-strategy-e2e/CAMPAIGN-V2.before.md#goal-cập-nhật--09112026),
không Goalactive hoặc lệnh resume hiện tại. Dùng T1 và currentcontext ở trên.
