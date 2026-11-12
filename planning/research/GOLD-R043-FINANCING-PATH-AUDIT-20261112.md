# Gold R043: xác minh phí đích trước, chưa port hoặc đổi cách thoát

12/11/2026. Owner duyệt kết quả Bước 1–2 tại `1c21e84`, yêu cầu merge PR66,
dọn nhánh đã gộp và giải phẫu R043 bằng sổ đã có. **Tạm dừng Bước3–4/Prop Risk
Overlay trên `us500_multiframe.py`.** Lượt này không đổi strategy, sizing, exit,
cost assumptions, runner hoặc verdict của các study cũ; không simulation mới.

Kết luận: **R043 đáng một lượt xác minh đúng hợp đồng phí/tài khoản, chưa đáng
port sâu vào Trader ngay.** BUY tạo phần lãi chính; SELL yếu cả trước swap.
Phần lớn phí nằm ở các lệnh dài, cũng là nguồn lợi nhuận của recipe H4 này.
Không thể cộng ngược 8.950,80 USD rồi coi đó là kết quả của strategy intraday.

## Phạm vi và số liệu có thể tái kiểm

Exact ID `xauusd-h4-sma20-80-atr14-r025-v1`, scenario `cost-stress`;
15 sổ năm **bắt đầu lại** 2010–2024, mỗi sổ50.000 USD, planned risk125 USD.
220 lệnh đã đóng và5 vị thế còn mở tại cuối các sổ; không là tài khoản15năm.
Input là M1 Bid→H1→H4, Ask và chi phí mô hình, stop theo mức/H1 envelope.

Nguồn gốc: [review tài chính](GOLD-SMA50K-REVIEW-20261108.md),
[phân rã cũ](SELECTIVE-LOSS-DIAGNOSIS-RESULTS-20261109.md),
[signal review có điều kiện](GOLD-SMA-SIGNAL-REVIEW-RESULTS-20261109.md),
[dossier Bước1–2](STRATEGY-STATUS-AND-CANDIDATE-DOSSIERS-20261112.md).
[JSON lượt này](GOLD-R043-FINANCING-PATH-AUDIT-20261112.json) giữ số exact,
hash input, danh sách nhánh, inventory và giới hạn.

## 1. Swap đang được giả định như thế nào?

| Scenario đã khóa | BUY | SELL | Lịch áp dụng |
|---|---:|---:|---|
| Reference | Trừ20 USD/lot/lần | Trừ20 USD/lot/lần |22:00 UTC cố định, thứ2–6; thứ4 nhân3|
| Cost-stress đang phân tích | Trừ40 USD/lot/lần | Trừ40 USD/lot/lần |Cùng lịch trên|

Công thức mỗi event: `round_half_up_cents(rate × lot × multiplier)`.
Ví dụ stress0,10lot:4 USD ngày thường;12 USD thứ4. Không là %/năm, points hay
swap broker đã xác minh; cả hai chiều đều debit, không có credit trong study.
Producer ghi phí trước quote tại boundary, giảm balance ngay, không đợi đóng
lệnh; reference/stress không được cộng làm hai mẫu độc lập.

Frozen sources: `scripts/metal_coarse_screen.py` COSTS;
`scripts/forex_h4_pilot.py:184–194` calendar;
`scripts/forex_coarse_screen.py:73–80,101–102` posting.
Đã đối soát **2.007 financing events** theo lot/weekday/multiplier/position.
Không áp lịch22UTC cố định này như lịch thật cho FTMO hoặc Exness.

### BUY và SELL — 220 lệnh đã đóng

Gross giá dưới đây **đã chứa spread** vì dùng giá Bid/Ask mô hình. Phí khác
là commission+slippage; cột trước swap đã trừ hai khoản này.

| Chiều | Lệnh | Gross giá USD | Phí khác USD | PnL trước swap USD | Swap trừ USD | Net USD |
|---|---:|---:|---:|---:|---:|---:|
|BUY/Long|116|+11.870,60|422,55|+11.448,05|5.305,20|+6.142,85|
|SELL/Short|104|+191,77|351,00|−159,23|3.404,00|−3.563,23|
|**Tổng**|**220**|**+12.062,37**|**773,55**|**+11.288,82**|**8.709,20**|**+2.579,62**|

Mid-price benchmark trước spread của cùng đường fill là13.781,37 USD;
spread1.719,00→gross Bid/Ask12.062,37. Đây không là giao dịch mid khả thi.
SELL không chỉ bị swap làm hỏng: sau spread/commission/slip, trước swap đã
âm159,23 USD. Đây là chẩn đoán exposed sample, không cho phép tự bỏ SELL.

**Cầu nối để không phân bổ nhầm phí:**

- 8.950,80 tổng financing = **8.709,20 của220 lệnh đóng +241,60 của vị thế mở**.
- 2.579,62 closed net +1.697,04 terminal floating −241,60 open financing
  = **4.035,06 USD tổng annual equity net**, khớp lịch sử.
- 12.985,86 =4.035,06+8.950,80 là tổng equity trước financing của các sổ,
  đã phản ánh các phí khác trong mô hình; khác gross giá của220 lệnh đóng.
- 77,75% là tỷ trọng8.709,20 trong **11.201,75 closed cost-drag**; không là
  phần trăm lợi nhuận hoặc toàn bộ phí8.950,80 chia cho gross.

## 2. Giữ lệnh bao lâu, phí có tập trung ở outliers?

| Thống kê 220 lệnh đóng | Ngày lịch | Đơn vị thời gian4giờ tương đương |
|---|---:|---:|
|Trung bình|12,268–12,294|73,608–73,761|
|Trung vị|5,167|31|
|Phân vị90|31,833|191|
|Dài nhất|78,167|469|

Stop intrahour chỉ có exit interval, nên mean là khoảng earliest→latest;
median/p90 tình cờ cùng giá trị ở hai đầu. Percentile dùng type7 interpolation,
`h=(n−1)×p`.4giờ tương đương gồm cuối tuần, **không là số nến H4 quan sát thực**.
5vị thế còn mở là right-censored, không đưa vào phân bố220 lệnh đóng.

| Nhóm holding theo earliest exit | Lệnh | Swap USD | % swap lệnh đóng | Net USD |
|---|---:|---:|---:|---:|
|≤1ngày|45|100,00|1,15%|−4.948,45|
|>1đến5ngày|63|472,40|5,42%|−7.543,39|
|>5ngày|112|8.136,80|93,43%|+15.071,46|

112/220lệnh giữ>5ngày mang **90,91% tổng8.950,80** khi tính cả open financing
vào mẫu số.22lệnh giữ lâu nhất (10% số lệnh đóng) trả4.072,00 USD, bằng46,76%
closed financing/45,49% tổng financing; chúng cũng đóng net+16.307,36 USD.
Phí tập trung mạnh ở lệnh dài, nhưng không chỉ một vài outlier duy nhất.

Nhóm≤1ngày vẫn trả swap100USD vì **thời lượng dưới24giờ vẫn có thể cắt rollover**.
Muốn tránh overnight debit phải đóng trước đúng rollover với margin thực thi,
không chỉ đặt thời lượng tối đa24giờ. Phân nhóm holding là nhìn lại kết quả,
không entry filter hoặc bằng chứng mọi strategy intraday vàng đều lỗ.

## 3. Time-fit và drawdown trên từng sổ50k

Mọi năm planned risk **125USD/lệnh =0,25% vốn ban đầu50k**, không compound theo
balance đang đổi. Đây là ngân sách sizing dự kiến, không bảo đảm lỗ tối đa125USD
khi gap/financing/chi phí; chưa kiểm lại sizing/fill toàn tick.

**Không có field equity MaxDD trong15book gốc**: `intrabar_drawdown` và
`internal_risk_and_prop` đều `not_evaluated`. Bảng sau là diagnostic mới từ
cash events cũ: credits khi đóng, funding trừ đúng lịch; include initial50k.
Mọi closed checkpoint khớp reviewer cũ. Không thêm giá hoặc replay thị trường.

| Năm | Lệnh đóng | MaxDD cash USD | % vốn đầu | Cash thấp nhất còn cao hơn45.000 USD | Cash lãi cao nhất sau đóng USD |
|---|---:|---:|---:|---:|---:|
|2010|14|1.118,01|2,236%|3.881,99|130,30|
|2011|13|771,02|1,542%|4.504,51|1.987,42|
|2012|16|1.254,88|2,510%|4.114,63|580,40|
|2013|13|705,51|1,411%|4.294,49|1.198,90|
|2014|14|984,73|1,969%|4.212,73|488,48|
|2015|17|1.681,50|3,363%|3.638,35|319,85|
|2016|12|625,06|1,250%|4.687,60|1.580,09|
|2017|9|528,69|1,057%|4.719,11|721,80|
|2018|21|1.834,67|3,669%|3.165,33|0|
|2019|14|1.082,67|2,165%|3.917,33|870,94|
|2020|20|1.930,54|3,861%|3.069,46|0|
|2021|16|507,94|1,016%|4.893,13|1.493,03|
|2022|13|994,48|1,989%|4.005,52|0|
|2023|12|358,16|0,716%|4.776,59|554,14|
|2024|16|602,44|1,205%|4.425,33|2.168,91|

MaxDD cash là peak-to-trough; cột cách45k dùng minimum cash và static initial
floor, nên hai cột không suy ra nhau. Phần trăm luôn chia đúng50k từng sổ.
**Cash trông còn đệm, nhưng daily/overall EQUITY headroom cả15sổ vẫn UNKNOWN.**
Không lấy2.500 trừ MaxDD cash của cả năm để công bố daily buffer; cash có thể
khác equity theo cả hai hướng và không cung cấp floating/first breach.

[FTMO2-Step](https://ftmo.com/en/2-step-challenge/) kiểm12/11 xác nhận targets
10%/5%, daily5%, overall10%: trên50k là5.000/2.500 target và2.500/5.000 loss.
[Daily loss](https://academy.ftmo.com/lesson/maximum-daily-loss/) tính equity
gồm open PnL/phí/swap, reset midnight CE(S)T; khác22UTC funding mô hình.
Các ngưỡng này là reference, chưa run phase1→reset→phase2 hoặc chứng nhận quỹ.

0/15sổ có cash checkpoint sau đóng đạt2.500 hoặc5.000USD; cao nhất2.168,91USD.
3/6/12tháng Jan-start prefix cash tốt nhất lần lượt1.233,33/1.589,49/1.846,75USD.
Không suy ra mọi rolling start đều thất bại, không chia target cho meanannual
để đoán thời gian pass, không nhân lot từ DD cash này.

## 4. Dữ liệu vàng2025–2026 và lựa chọn intraday

Đã gọi native QDM `-symbol action=list` **metadata only** lúc15:30:51UTC12/11,
không `update`, export hoặc đọc giá. Catalogue local đang báo:

| Asset / độ phân giải | Phạm vi cache báo bởi QDM | Records toàn cache | Ý nghĩa |
|---|---|---:|---|
|XAUUSD M1|05/05/2003–13/10/2026|7.972.007|Có phạm vi metadata bao gồm2025 và2026 một phần; chưa kiểm từngngày/gaps2025–26|
|XAUUSD tick|Không có QDM tick symbol đã cache|—|Campaign có fixture03/01/2023,206.215Bid/Ask ticks; chưa xác minh bulk tick2025–26|
|XAUUSD H4 năm2025–26|Chưa có export/cache được admit trong luồng R043|—|Có thể dựng từ M1 theo protocol; chưa được tạo/kiểm trong lượt này|
|EURUSD M1|05/05/2003–07/10/2026|8.755.235|Cùng catalogue, cần kiểm phạm vi exactstudy trước dùng|
|EURUSD tick|05/05/2003–01/11/2026|517.750.341|Có cache Bid/Ask và actual nativepath đã kiểm trên selected2022–24, không fullcoverage certification|

Inventory cũng đọc metadata của fixture XAU và manifest/review cũ; không đọc
ticks hoặc CSV. Phạm vi kiểm là QDM managed catalogue + campaign artifacts,
không forensic scan toàn bộ ổ đĩa, database mọi sản phẩm hoặc lịch sử ngoài máy.
Ngày đầu/cuối và total count không chứng minh cache liên tục/đúng từng ngày;
2026 chưa tới hiện tại12/11, không gọi full2026.

**Exposure/OOS:** original R043 manifest chỉ chạy2010–24, exports liên quan
kết thúc2024; các review đọc lại không thêm2025+. Không tìm thấy run R0432025–26
trong evidence chain này. Tuy nhiên **chưa chứng nhận hoàn toàn unconsumed OOS**
cho toàn project/người dùng: lịch sử exposure ngoài chain chưa đủ; owner từng
không nhớ rõ. Lượt này không tiêu thụ giá2025–26 và không tự mở holdout.
Trước study mới phải pin cutoff/splits, kiểm exposure ledger và gọi đúng
“unverified exposure” nếu chưa chứng minh sạch, không đổi nhãn sau khi xem kết quả.

**Ưu tiên hạ tầng cho intraday: EURUSD.** Ngoài tick/M1 cache, đã có causal
H1signals/nextquote fills, native accounting/risk/ForexPropObserver, checkpoint,
resume, tickDD/dailyreset/headroom trên một số sổ2022–24:
[native results](H1-NATIVE-SURVIVORS-RESULTS-20261108.md).
Đây là readiness advantage, không là khẳng định FX có edge hơn vàng hoặc exact
H1→M15 strategy đã có. XAU M1 rộng phù hợp count-only/triage, nhưng execution
vẫn thiếu multi-year observed Ask/tick và target metal/prop admission. Fixture
1ngày chỉ xác minh BidOHLC/grid/time trên ngày đó, không cả lịch sử vàng.

## 5. Bước nên làm tiếp — đề xuất, chưa triển khai

| Thứ tự | Công việc hợp lý | Cửa quyết định |
|---|---|---|
|1|Thu source package đúng FTMO CFD2-StepStandard/account/platform/server/symbol: contract, digits/point/tickvalue, swapmode, signed long/short rates, lịch triple/holiday/rollover, commissionbasis, spread/slip, ngày hiệu lực|Không đủ thì ghi unknown, chưa đổi phí hoặc gọi old20/40 là conservative|
|2|Xem economics/time-fit với hợp đồng được xác minh và budget đã khóa; giữ parent/outcomes/exposure. Reprice cùngpath nếu có chỉ là conditionalcost diagnostic, không executablevariant|Có cơ sở mới đáng kể mới đăng ký exact native path study; không port sâu để chỉ xác nhận lại alpha quá thưa|
|3|Nếu vượt feasibility, nối đúng market contract với existingTrader risk/prop lifecycle bằng fixtures nhỏ trước; kiểm equity quanh rollover/news/weekend và target closure/phase reset|Chưa giao triển khai ở lượt này; không nối overlay vào US500 đã gác|
|4|Một intraday hypothesis H1→M15 với EURUSD nếu ưu tiên reuse: định nghĩa clock/zone/setup/trigger/exit-before-rollover, count-only trước PnL|Card/protocol/budget riêng; không cứu recipeGold bằng cutoff mới hoặc quét cả hai asset|

R043 có bằng chứng dương trong mẫu ở declaredstress và funding nhạy nên đáng
**cost feasibility audit ngắn**. Còn cadence≈14,67closed/year, concentration,
khả năng đóng đạt target, freshvalidation và đường equity; chưa đủ ưu tiên
engine integration lớn hoặc challenge. Không long-only, không tăng risk.

Nguồn đích kiểm12/11:

- [FTMO commission announcement25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/):
  metals0,0007% volume/side từ29/09/2025; là publishedpolicy ngày đó, chưa là
  đúng account/historical2010–24. Không lấy fixed2,50USD/lot/side trong study làm FTMOgold fee thật.
- [FTMO holding rule](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/):
  Challenge/Verification và Swing được miễn hạn chế giữ qua marketbreak>2giờ;
  funded Standard phải đóng trước break đó. Không cấm mọi đêm thường.137/220
  closedpositions cũ cắt mốcSaturday00UTC trong interval đã ghi, nên cần kiểm
  compatibility funded; con số này chưa là replay holiday/session/actualbreach.
- [Exness swap](https://get.exness.help/hc/en-us/articles/360014709151-About-swap):
  21UTC mùa hè/22UTC mùa đông, rates/units/calendar theo symbol; khác fixed22UTC.
  [Swap-free](https://get.exness.help/hc/en-us/articles/4402341895570-Swap-free-status)
  liệt kê XAUUSD nhưng phụ thuộc trạng thái/hoạt động, có thể mất eligibility và
  bị tính swap cho positions đang mở. Chưa kiểm PA của owner; không giả miễn phí
  bền vững cho longholding. **Điều kiện broker Exness không chuyển thành FTMO prop terms.**

Nếu intraday đóng thành công trước mọi rollover áp dụng, nó tránh khoản
overnight swap tương lai theo contract; vẫn có spread/commission/slip/gap và
rủi ro đóng không kịp. **Đổi exit làm đổi tradepath, winners và cơ hội kế tiếp**;
không được giữ nguyên13k gross rồi cộng lại8.950,80 của15sổ cũ như savings khả thi.

## Repo hygiene đã thực hiện

[PR66](https://github.com/Naqex/workspace/pull/66) merge commit
`c310bd279ec5a38dfb21d95bbd2e898130c6ba99`, sau3CI SUCCESS đúng head`1c21e84`.
Fetch và fastforward localmain; VI Dubber WIP giữ nguyên. Không đổi pinTrader.

Đã xóa đúng refs ở cả local/remote sau ancestry/worktree/openPR/remote-tip checks:
`focused-research-lanes`, `local-strategy-source-library`,
`m15-standard-research-direction`, `strategy-fit-review`,
`strategy-template-reuse-review`, `us500-cadence-research`,
`us500-channel-history`, `us500-m15-research-focus`, `us500-m15-rule-screen`,
`us500-opportunity-screen`, `us500-session-and-research-stages`,
`us500-recent-discovery` — tất cả có prefix `codex/`.
**Thực tế là12 nhánh =11 nhánh cũ +nhánh PR66**; không xóa nhánh khác chỉ để
khớp số11 trong câu yêu cầu. Exact oldtips có trong JSON/cleanup receipt.

| Nhánh giữ nguyên local/remote | Commits ngoài main | Nội dung / khuyến nghị |
|---|---:|---|
|`codex/us500-frequency-review` (`8c64748`)|2|Causal frequencydiagnostic +kết quả/giữ tất cảtrial;5filecore/protocol/results identicalmain, sharedcontext đã tiến triển. Có thể xem xét dọn sau xác nhận, giữ SHAprovenance|
|`codex/us500-ma-reclaim-study` (`6ef96ec`)|3|MAreclaim, exploratorycostadmission, income/cadence;7filecore identicalmain, kết quả/income có followup. Giữ lịch sử chờ xác nhận, không merge đè bản mới|
|`codex/us500-multiframe-study` (`b77fc68`)|6|Multiframe study, nativeclosure/missingpath fixes và bảng outcomes;10fileidenticalmain, runner/main có Windowslock regression mới hơn. Giữ chờ xác nhận và đối chiếu provenance, không merge lại code cũ|

Không path nào trong changedfile inventory của3nhánh bị thiếu trênmain;
**file hiện diện không chứng minh mọi semanticdelta đã hợp nhất**. Không xóa
3nhánh này hoặc remote-only refs khác. Branch cho báo cáo này là một đợt coherent,
không tách mỗi subtask hoặc thêm issue/cleanupservice.

## Kiểm chứng và nơi resume

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`:
`gold-financing-path-audit-20261112-v1/` giữ `audit.py`, `result.json`,
`qdm-inventory.json`, `branch-cleanup.json`, `evidence.json`, `verify.py`, `verification.json`.
Script không import engine, không đọc CSV/tickprices;24inputsbind bằngSHA.

- Rehash sealed originals/derivedbooks và3frozen source snapshots;220trade
  net/funding khớp originals,15cash paths khớp mọi oldclosecheckpoint.
- Decimal sums đối chiếu Fraction; cashDD đối chiếu rational suffix-min oracle.
  2.007eventfees theo rate/lot/weekday; closed/open/equity bridge khớp.
- `verify.py`:99ô số trong các bảng đối chiếu JSON exact/rounding,24inputhash
  giữ nguyên; local links của4file Markdown liên quan không có lỗi.
- Holding bounds từ entry/exitinterval; không fundingevent trong interior của
  exitinterval chưa rõ nên cash ordering không phụ thuộc chọn đầu/cuối interval.
- Audit arithmetic/hash wall0,307s; QDMmetadata7,576s. Không là total research/
  Git/webtime hoặc speedup so với simulation. Marketprice rescans/simulations/
  broker calls/newholdout0. Sameagent review, không independenthuman/feed.
- Wrapper QDM import trong engine_runtime venv thiếu`psycopg`; dùng native list
  command tương đương đã capture/parse/smoke-check, không cài dependency/restart.

Đủ giải đáp diagnostic bằng evidence hiện có; **equity MaxDD/headroom thật và
global cleanOOS chưa thể điền bằng số**. Existingqualification skills đã yêu cầu
đúng phân biệt này; không tạo/sửa skill để lặp lại report. Resume từ sourcepackage
cost/path decision ở mục5 khi có scope mới; US500 overlay tiếp tục paused.
