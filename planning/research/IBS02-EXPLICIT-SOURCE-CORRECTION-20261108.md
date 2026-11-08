# R049 IBS02hold — bổ sung phần source correction còn thiếu

## Lý do, baseline và phạm vi

Sau long RSI/preclose và Gold review, R049 còn kết quả expanded-view/filtered
cũ trong [daily outcomes](US500-DAILY-REVERSION-RESULTS-20261108.md). C2 cần sửa
đúng phần affected, trước khi dùng số đó chọn/loại strategy. Đây là sửa nguồn,
không strategy mới hoặc tối ưu performance. Oldoutcomes đã exposed; không OOS.

Giữ exact `us500-d1-ibs02-hold-atr14x1p5-r025-v1`: IBS≤0,20 BUY, exit khi
IBS>0,20,SL1,5ATR14, causal cashdailybar/14consecutivesessions, missingbar
safetyEXIT, nextminutequeue/expiry, một position, khôngTP/forceclose. Nguyên
rule/clock/annualreset ở [frozenoriginal](US500-DAILY-REVERSION-20261108.md).

2022–2024, mỗi năm10k/planned25USD, legacycommission0,50USD/lot/side,
slippage0,25/0,75 và funding1/2USD/lot/calendarday. Không dùng commission0
hiện hành để cứu kết quả. Mỗi book2costs+nullcontrol,3books/9scenarios; không
rerun R050/R052 đã corrected hoặc mở longhistory cho IBS trong lượt này.

## Input và correctness trước numerical

Reuse `execution-v1/us500-explicit-source-v1/<year>` đã sealed/proved trong
[source correction](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md), calendar từ
parentmanifest, currentreader/proof guard hiện có. Chỉ source-listed paired
M1; giữ raw/unpaired/availability/gap journals. Không padding, filtervolume0,
reconstruct missing side, download mới, đổi hashes hoặc sửa oldartifacts.

ExplicitD:productsource7ab57907, workspace numericalsource như longcorrection
`a2a3358`; lưu currenthashes đầy đủ. So AST`plans_for`/`rsi3` với snapshots
parentIBS trước chạy; nếu khác material thì dừng sửa reason/version trước.
Giữ financialdependencies/rules/risk/cost, source snapshots mỗi book. Input
đổi có thể đổi state về sau:rerun whole affectedannualbook, không xóa trade
rồi cộng trừ PnL. CurrentCLI negative/proof regression đã đạt ở slices trước;
không chạy lại suite không đổi chỉ để benchmark.

## Thực thi, review và tiêu chí

Privateattempt mới `execution-v1/us500-ibs02-source-corrected-v1`, một numerical
worker qua existingOwnedPython/WindowsJobObject, controllerdeadline900s,
existingCLIdeadline300s/book, CANCEL/status/log/progress, complete từng book
sau arithmetic/fill/funding/openmark review. Không sửa source đang pin. Lỗi
giữ completedbooks/failure, reconcile process trước retry; không restart tất cả.

Giữ originalprioritycriterion: mỗi năm netdương ở cảcosts và không material
defect mới được ưu tiên review thêm. Nofill/partial/gaps là inconclusive về
economics/operations, không “năm an toàn” hoặc tự drop. Không hardreject cả
family từ3years, không dùngsourcecorrectedM1 làm executabletick/propDDproof.
So old/new decisions/trades/funding/cash/open/gaps và inputcoverage; pin parent
manifest/output trước khi đọc numbers, giữ baseline lọc và expanded đầy đủ.

Đóng bằng results/decision/hậu kiểm/timers, updateR049catalogue/context khi có
evidence. Không gọi tests/checkerpass là edge; C1/C2overall chưa đạt. Không
2025+, broker/modelcalls, account/provider/payment/challenge/production.
