# NASDAQ: overnight gap → đầu phiên, đăng ký component trước outcomes

## Vì sao thử và nguồn đã đọc

Đổi cơ chế từ NY FX MA4 sang phản ứng đầu phiên của chỉ số cổ phiếu, reuse
NASDAQ M1/calendar đã review. Không đảo R064 first→last-half hoặc R024 weekend
FX gap để cứu kết quả cũ; đây vẫn là related reversal family, không edge độc lập.

Ngày 09/11 đọc primary search-served abstract/introduction của
[Liu & Tse 2017](https://www.sciencedirect.com/science/article/pii/S1059056016301563):
overnight return liên hệ ngược chiều với first-half-hour returns trong mẫu
ETF/futures Hoa Kỳ. Chưa đọc full method; direct publisher/SSRN trả 403.
[Iwanaga & Sakemoto 2026 abstract](https://www.sciencedirect.com/science/article/abs/pii/S1062940826001294)
và [trang tác giả](https://sites.google.com/site/rsakemotohomepage/reserach)
củng cố câu hỏi nhưng cảnh báo quan hệ suy yếu ở giai đoạn gần đây. Chỉ kế
thừa ý tưởng, không claim paper replication hoặc đã xác minh profits trên CFD.

Không import code/data có bản quyền khác. Không dùng xác suất chạm gap làm
winrate/PnL. Không cần đợi full paper để bác bỏ một own adaptation đã ghi rõ.
Không thêm volatility/news/volume/quintile filters hoặc parameter grid.

## Input, timing và semantics khóa trước

Candidate `nasdaq-overnight-first30-reversal-price-component-v1`, record R074.
Reuse `execution-v1/nasdaq-m1-history-v2`: result SHA
`3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`, review SHA
`8b0bced9723138d52242552a66ed74c33f5a43d8d3013288b515d2db7c4b9703`.
Development 2019/2022, warmup Nov–Dec 2018/2021; đã consumed, không clean OOS.
Bind toàn bộ 8 source books/calendar; không download hoặc own 2025+.

- Mỗi expected cashday có một row; regular 390 minutes mới eligible, halfday
  210 minutes skip theo calendar. Previous close dùng **đúng previous expected
  cashsession** cuối phút, kể cả halfday; không last available quote.
- Gap = current 09:30 BidOpen − prior cash last M1 BidClose. Pair phải có cả
  side, clock/grid hợp lệ và Bid ≤ Ask tại field đã dùng. Thiếu/crossed predictor
  ghi signal unavailable, không gọi là gap bằng 0. Gap dương → SELL, âm → BUY,
  bằng 0 không trade. Không cần ATR readiness vì không SL/sizing ở component.
- 09:30 Open proxy biết muộn nhất 09:31; decision 09:31, entry 09:32 M1Open.
  Exit decision 09:58, fill 09:59 M1Open. Chờ một phút sau decision, không
  claim executable tick tại đúng timestamp. Không nhìn current first30 close,
  full day hoặc future quality để chọn signal. Không TP tại prior close.
- Một hypothetical unit worth 1 USD/price unit, không lot/account risk. BUY
  entry Ask/exit Bid; SELL entry Bid/exit Ask. Observed spread, slippage
  0,25/0,75 mỗi side, commission 0 theo NASDAQ declared cost helper. No planned
  overnight funding. Target broker costs/specs/latency chưa xác minh.
- Không SL/TP/sizing/margin/account equity/prop drawdown. Giữ census missing
  M1 trong 27-minute holding window, không dùng để xóa entry hindsight. Missing/
  crossed endpoints = unresolved, không next-quote fill hoặc cộng 0 thành known PnL.

## Controls và cửa quyết định

Mỗi planned day cùng mask/endpoints: primary, opposite-gap control, always-long,
always-short; cả 2 costs. Null không exposure/net 0. Controls không được promote
nếu primary fail, không dùng best clock/threshold/risk từ outcome.

Retain để nghiên cứu tiếp chỉ khi **từng năm**: ≥100 planned primary signals,
≥98% regular days có predictor hợp lệ (flat gap vẫn valid), ≥98% planned days
resolved endpoints, stress known sum > 0 **và lớn hơn cả always-long và
always-short** trên cùng resolved mask. Đây là triage nhằm phân biệt predictor
với direction bias, không statistical proof; có thể bỏ sót edge nhỏ. Partial
sum không là full-year/account result khi còn unresolved. Báo concentration,
positive/negative count và coverage; không dùng winrate làm tiêu chí chính.

Fail → gác exact recipe, không tune exit/direction/cost/threshold để rescue.
Pass → đăng ký duy nhất một wrapper/risk design trước outcome mới, rồi review
selection-aware robustness/OOS, prop equity/time-fit, prospective execution và
owner handover; không tự chuyển thành challenge-qualified.

## Thực thi, review và hậu kiểm

Code/fixtures trước numeric: BUY/SELL/flat, previous halfday/holiday, DST,
missing/crossed/clock/grid predictors/endpoints, future mutation không đổi
signal, common control mask, exact calendar/denominator/authority/holdout guards.
Separate reviewer dựng signal bằng Fraction từ source, kiểm toàn bộ rows,
cost decomposition/cents rounding/summaries/gate và mutations; cùng agent/
provider, không independent human/model signoff. Synthetic review trước actual.

Output mới `execution-v1/nasdaq-overnight-reversal-component-v1`, một writer,
PID/events/progress/CANCEL/deadline 120 s, snapshots/pins/config trước outcomes.
Đọc source một lần/year; không lặp whole raw source audit đã đủ binding.
Lưu preparation/compute/review wall+CPU và failures; hậu kiểm sau terminal.
Skills hiện có đủ; không framework/UI/DB mới, không runtime/broker changes.
