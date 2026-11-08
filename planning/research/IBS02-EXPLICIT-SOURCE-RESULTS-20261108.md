# IBS02: đã sửa nguồn ba năm, chưa đạt tiêu chí ưu tiên

**R049 đã được tính lại trên source-only M1 và kiểm sổ tiền.** Giữ exact
rules/risk/cost; không đạt tiêu chí cũ mỗi năm dương cả hai costs. Không phải
hard rejection cả họ mean reversion hoặc kết luận đã biết lợi nhuận tương lai.

[Protocol trước outcomes](IBS02-EXPLICIT-SOURCE-CORRECTION-20261108.md),
commit`55f1743`; [source-compatibility clarification](IBS02-SOURCE-PREFLIGHT-NOTE-20261108.md)
commit`c125c22`. Data là ba paired explicit views2022–24 đã kiểm, không download
hoặc thêm market. Baseline expanded ở`us500-corrected-replay-v1/ibs-<year>`;
originalfiltered ở`us500-daily-reversion-v1/ibs-<year>` đều được giữ/pin.

## Trước và sau: vốn10.000USD mỗi annualbook riêng

| Năm | Expanded cũ: chuẩn/cao,USD | Source-only: chuẩn/cao,USD | Entries cũ→mới, mỗi cost |
|---|---:|---:|---:|
|2022|+68,82 /+43,33|+52,37 /+34,41|44→33|
|2023|−51,24 /−87,02|−49,08 /−63,68|39→20|
|2024|+102,44 /+71,15|+37,06 /+20,37|38→20|
|Tổng ba annualbooks|+120,02 /+27,46|+40,35 /−8,90|121→73|

Không CAGR, một account liên tục hoặc prop pass-rate. Tất cả vị thế được đóng
theo rules, không còn open/pending ở cuối ba books; không forceclose. Năm2023
vẫn âm ở cả costs, tổng stress cũng âm. Giữ originalcriterion, không nới risk/
clock/SL hoặc bỏ năm đó. Source/availability correction có thể bỏ signal và
đổi state về sau nên đã rerun whole affectedbook, không xóa trade để sửa PnL.

Số mới tình cờ trùng originalfiltered: cả9scenarios có14fields tài chính/state
được so sánh exact, gồm decisions/trades/funding/cash/floating/open/pending/
gaps/rejections/counts. Đây là kết quả đối chiếu thực tế, không chứng minh hai
dataset tương đương hoặc cho phép dùng lại mọi filteredstudy. Full JSON khác
metadata/hashes/timing; không gọi byte-parity toàn file. Delta từng field với
cả hai baselines được lưu tại private`delta-review.json`.

## Correctness, lỗi trong lượt chạy và cách phục hồi

1. V1guard dừng0,047s trước simulation vì full`plans_for`AST khác. Đối chiếu
   source cho thấy chỉ nhánh **candidateRSI** đã sửa safetyEXIT;`rsi3`ASTexact.
   Trước numerical, đã đăng ký phép specialization bỏ đúng nhánh không thể
   chạy với candidateIBS. Toàn bộ function còn lại ASTexact cả3snapshots.
   Không bỏ nhánh IBS/risk hoặc giảm numericchecks để pass; failedV1 giữ nguyên.
2. V2 hoàn tất2022simulation rồi observer/reviewerCLI bị gọi nhầm
   `--source-root` (CLI này không có flag đó), exit2. Đây là lỗi orchestration
   của lượt này; không là lỗi strategy/data hoặc numericaljob2022.
3. Recovery đọc/kiểm source/protocol/data/cost/result bindings, giữ driver/
   failedattempt/logs và **reuse2022, không mô phỏng lại**. Reviewer nhận explicit
   D:importpaths qua existingOwnedPython.2023/24 chạy tiếp, một worker/time,
   WindowsJobObject/deadline/CANCEL/status/events; originalpins không đổi.
4. Cả3books/9scenarios qua current independent-code-path arithmetic/fill/
   funding/openmark reviewer và sourceproofguard; nullcontrols0entries/net0.
   Tổng73closedpositions/cost nhưng **cả73path còn gaps unresolved**, không
   chứng minh intrabarDD/SLfirstcrossingtick hoặc brokerhours. Source-listed
   M1 không tự là executablequotes; không gọi flat-endbook là no-breach.
5. ExactID,legacycommission0,50/lot/side,slippage0,25/0,75,funding1/2 và10k/
   planned25 giữ. Source snapshots/reviews/hash/proof/calendar ở từng book;
   original/currentproducer sources không bị sửa. Sameagentreview, chưa
   independenthuman/modelsign-off, cleanOOS, targetbrokercontract hoặc nativeprop.

| Phần thực đo | Wallseconds | Scope |
|---|---:|---|
|V1 preflight failure|0,047|0simulationcalls|
|V2 trước CLIreviewerfailure|12,703|2022 đã completed và được giữ|
|Recovery|31,078|Review/reuse2022 +compute/review2023/24|
|Numerical CLI2022/23/24|11,358 /10,156 /10,061|Mỗi giá trị gồm currentinputverification và3scenarios|

Không cộng timers lồng nhau hoặc cả thời gian agent sửa orchestration vào
CPU/speedup; active research/reworktime chưa đo riêng. Không benchmark lại
cùng batch để chứng minh con số. Cải tiến cần giữ là binding-aware reuse và
kiểm đúng CLIcontract trước dispatch; existingrunner đã hỗ trợ, chưa cần
framework/helper/skill mới. Không sửa product hoặc chạy lại suite không đổi.

## Quyết định và phần tiếp

R049 từ “oldexpanded/filtered evidence còn cần sửa” sang “source-corrected,
không đạt oldpriority”. Giữ negativeversion và originalrecipes, không chạy
longIBS chỉ để tìm một năm đẹp. C2 repair của family này đã có bằng chứng trong
scope trên; không nâng thành whole-system C2 hoặc C1. R050/R052 không rerun.

Tiếp campaign ở data/target-contract admission trước discovery đắt: publicFTMO
symbol specifications cần đọc đúng row/clock/fees của market, không lấy generic
page hoặc historicalfeeannouncement làm verifiedtargetaccount. Sau đó chọn
boundedmechanism có đủ inputs từ catalogue; R026 vẫn thiếu relative-equity/
currency/corporate-action/fixingcalendar. Không mở2025+, broker/modelcalls,
account/provider trả phí, mua challenge hoặc production.

Private `execution-v1/us500-ibs02-source-corrected-v2`: `driver.py`,
`resume-review.py`, `recovery-manifest.json`, `completed-rows.json`,
`result.json`, `delta-review.json`, `2022/2023/2024`,3reviews,logs/events.
V1failure và V2CLIerror vẫn giữ. Recoveryprocess29688/session64993 terminalexit0;
khôngjobnền. `result.json` là completionreceipt hiện hành, không xóa failure
lịch sử để làm cảattempt trông chưa từng lỗi.
