# R086 — US500: tín hiệu giá trước FOMC, protocol trước outcomes

09/11/2026. Own adaptation, liên quan họ momentum/event; không independent
edge hoặc replication. Tiếp [source review](FOMC-SURPRISE-SOURCE-RESULTS-20261109.md),
không dùng future surprise để phân loại lệnh trước cuộc họp.

## Cơ sở và giới hạn

[Monetary Momentum, Neuhierl/Weber, May2024](https://faculty.chicagobooth.edu/-/media/faculty/michael-weber/momentum.pdf)
đã đọc fullmethod: §IV/table5 phân biệt chiến lược dùng dấu surprise biết sau
sự kiện với nhánh implementable từ ngày+1. Paper cho động cơ khảo sát giá
quá khứ, không chứng minh recipe dưới đây. Không nhận headline Sharpe hoặc
loại ZLB theo hindsight. PDF47pages/private personal reference, SHA256
`212dc8bbbb12c1c289ce245725eb0a8a375f2bb9b38c2a849c446105600a2d5d`.

## Quy tắc khóa trước giá/PnL mới

- Cohort: 8 scheduled FOMC dates2019 và8dates2022, exact accepted R062calendar
  SHA`fe6fa164e5b81281172d73dccfc773f2dd3f3b37ccd04835417243d3a539a307`.
  Schedule được công bố2018/2021. Hai năm đã exposed/development, không cleanOOS.
- Hai anchor roles: ngày sự kiện và ngày **7local calendar days trước đó**.
  Mỗi role tính lại lịch/feature/holding riêng, không dịch UTC cố định.
- US cash-session proxy: lịch2018/2019/2021/2022 đã có; chỉ thêm tail01–15Jan2020
  (đóng01Jan) và01–15Jan2023 (đóng02Jan). Không tuyên bố fullcalendar hai tailyears.
  Primary [ICE lịch2018–2020](https://ir.theice.com/press/news-details/2017/NYSE-Group-Announces-2018-2019-and-2020-Holiday-and-Early-Closings-Calendar/default.aspx),
  [ICE lịch2023–2025](https://ir.theice.com/press/news-details/2022/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar/default.aspx).
  Lịch exchange không là brokerCFD hours. Existing year/holdout guards giữ nguyên.
- Với anchor cash-session index`i`: feature là midpoint separate-side M1Open
  lúc12:00NY tại`i−2` trừ12:00NY tại`i−27` (**25cashsessions cách nhau**).
  Dấu dương BUY, âm SELL, đúng0 flat. Known-at upper bound mỗi M1 là phút+1,
  phải trước decision. Không dùng surprise/statement/VIX hoặc fullsamplefit.
- Entry decision14:00NY tại`i−1`, M1Open proxy14:01NY; exit decision12:00NY
  tại`i+15`, proxy12:01NY. Dùng12h để không vượt halfday13h. Entry rơi ngoài
  session/thiếu/crossed endpoint →unknown, không chuyển ngày/giờ hoặc droprow.
- Source `usa500idxusd` / `USA500.IDX/USD`, explicit source-listed M1 riêng Bid/Ask.
  Reuse accepted raw/proofs tại đúng ngày/phút, không refetch fullhistory.
  Tail thiếu có thể lấy tối đa8day-side URLs từ provider helper đã pin, toàn bộ
  trước2025; source admission trước economics. Không nới annual loader guard.
- Source/feature/endpoint census phát ra trước costs. Đủ endpoint không chứng
  minh holdingpath/equity/SL; M1Open riêng side không simultaneous tickfill.

## Books, costs và quyết định

Mỗi anchor có4rules: primary tín hiệu trên, opposite diagnostic, unconditional
BUY và null. Control không được tự promote nếu thắng. Nếu feature unknown,
primary/opposite unknown; BUY/null giữ semantics riêng. Flat không trả spread/
slip/funding nhưng vẫn giữ row, không tính là lệnh có exposure.

Hai scenario declared: base slip0,25point/side+funding8%/year, stress slip0,75+
16%; commission0, một researchunit=1USD/indexpoint. Entry/exit BidAsk đúng side.
Funding debit tại mỗi22:00UTC có`entry < boundary <= exit`, kể cả weekend;
mỗi debit=`entryAsk × annualrate /365`, cents ROUND_HALF_UP. Đây không là
target-broker swap/spec. Không phép suy nguyên USD/unit ra accountreturn.

2years ×2anchors ×4rules ×2costs =**32books /256planned financialcases**;
32anchor rows, mỗi book8events. Events/windows có overlap, không256independent
trades. Không SL/sizing/account/margin/prop/time-fit/portfolio hoặc brokercalls.

Frozen triage chỉ ưu tiên bước review tiếp nếu **cả hai năm** có primary và
matched resolved8/8, primary stressnet>0, primary−matched stressdelta>0.
Thiếu/gap →inconclusive đúng phạm vi, không chọn known subset hoặc sửa gate.
Control/concentration/positivecount là diagnostics, không dùng chọn rule mới.
Không đạt thì gác exactrecipe; không clock/lookback/funding grid cứu kết quả.

## Kiểm và lưu

Trước economic run: clock/DST/crossyear/halfday, missing/crossed/zero feature,
no future dependency, flat/null, BUY/SELL side costs, cents funding boundary;
Fraction oracle độc lập cách tính và mutations. Sau run đối soát **mọi** input
endpoint với raw delta decoder khác và mọi financialcase; self-review khác
method không là independentfeed/model/human. Bind protocol/code/source/output,
giữ snapshots/failures/progress/PID/deadline/nooverwrite và wall/CPU phases.
Không sửa frozenrecipe sau outcomes; bugfix giữ attempt và xét invalidation.

Chỉ thêm R086 catalogue khi có implementation/outcome, không tăng58account
policy-modelversions vì component này. C1/C2, broker/holdout/account/paidfeed/
challenge/runtime/globalconfig gates giữ nguyên. Không có authority từ report.
