# Đăng ký own FX abnormal-day reversal trước outcome

09/11/2026. [Method và nguồn](FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md).
ID dự kiến R089; chưa ghi vào catalogue như policy đã chạy. Candidate component
`eurusd-prior-abnormal-day-reversal-utc-v1`, không account strategy hoặc quyền
giao dịch. Mẫu2019/2022 đã exposed trong campaign, không cleanOOS.

## Tín hiệu được biết trước

- EURUSD, weekdays thuộc2019/2022; chỉ xét entry Tue–Fri và ngày trước là đúng
  calendar Monday–Thursday. Không kéo Friday shock sang Monday hoặc thay ngày
  thiếu bằng tradingday xa hơn. Giữ skipped weekdays trong census.
- Own dayproxy của ngày d: midpoint nguồn first-after00UTC→first-after23UTC,
  mỗi slot lag≤60s. Đây là23hproxy, **không daily Open/Close đúng paper**.
  Có actualtimestamp/known-at upper bound, nguồn paired Bid/Ask, grid0,00001;
  midpoint chỉ benchmark, không giá fill. Không lấy OHLC Close làm quote.
- Calibration dùng20weekdays ngay trước d, mỗi return `(end/start−1)`; d
  không nằm trong calibration. Mean và sample variance (`ddof=1`), k=2 cố định.
  Missing bất kỳ weekday/slot → feature unavailable; không bỏ missing rồi lấy
  ngày xa hơn. Sunday source không được tính thành một weekday.
- Positive shock khi rd>0 và rd>mean+2std; negative khi rd<0 và rd<mean−2std;
  bằng boundary không shock. Variance0 → unavailable, không tạo signal từ
  flat calibration. Dùng squared comparison để tránh root rounding đổi nhánh.
- Primary giao dịch **ngược chiều shock**; opposite control cùng mask và null.
  Tail vượt mean nhưng không cùng dấu actualreturn không được coi positive/
  negative shock. Mọi feature và source availability phải trước decision.
- Decision ngày d+1 lúc00:59UTC, entry first-after01:00UTC, exit decision07:59,
  exit first-after08:00UTC; mỗi slot≤60s, đúng chronologicalorder. Không entry
  tại quote của decision hoặc dùng future exit để chọn ngày vào.

20weekdays và01–08UTC là own adaptation khóa trước outcome: calibration khoảng
một tháng và cửa sổ đầu ngày→đầu phiên châu Âu, không parameters suy ra từ
paper hoặc tối ưu theo PnL. Không thay DST/giờ/n/k sau khi xem outcome rồi giữ
cùngversion. Không dựa vào outcome controls để chọn lại primary.

## Phí, unknown và tiêu chí ưu tiên

- Một researchunit=100.000EURnotional; PnLUSD, không safe1lot hoặc return10k.
  Giữ source Bid/Ask, commission5USD khứ hồi/unit, reference extra slip0,
  stress0,4pip khứ hồi. Reuse nativecostcore. Không qua declared17NYrollover
  trong01–08UTC nên funding0 chỉ trong window này; targetfees chưaverified.
- Đây là endpoint-only component. Missing entry/exit không PnL0; giữ row/
  knownsubset/strict summary. Calibration missing là skip biết trước entry,
  khác future exit missing. Không SL/TP/accountlot/margin/equity/prop proof.
- Frozenpriority cho bước reviewrisk: mỗi năm≥20selected shocks và≥95%selected
  endpointsresolved; primary stressnet>0 ở cả2năm. Nếu còn selectedunknown thì
  chỉ có knownsubset, không strictannualnet hoặc automaticpass. Đủ coverage
  không xóa unknown. Thiếu mẫu/nguồn →inconclusive; đủ nguồn nhưngnet≤0 →gác
  exact recipe. Đây là heuristic ưu tiên nghiên cứu, không statistical edge.
- Báo BUY/SELL, selected/nonselected/unavailable, fees, source lag và primary/
  opposite/null đầy đủ. Không gọi2costs hoặc controls là independent trials;
  không bắt buộc primary−opposite phải dương nếu primary net không dương.

## Trình tự và kiểm chứng

1. Causal feature fixtures + Fraction oracle trên synthetic data trước nguồn
   thật; n/k cố định, strictboundary, future/currentday leakage, weekdaycensus,
   missing/invalidquote/zero variance. Không financialcase ở bước này.
2. Đăng ký bounded source fixture từ raw/cache đã consumed; kiểm dayproxy và
   sparse quote targets, source pins/schema/order/grid/availability. Source
   chỉ thực hiện sau frozenprotocol commit; không tải lại history không đổi.
3. Numeric/full financial review chỉ sau admission và preflight BUY/SELLcost/
   missing/null/units; exact input/code/protocolpins trước outcome. Một writer,
   nooverwrite, progress/events/PID/timers/deadline/cancel, giữ failures.
4. Cả source và finance reviewer dùng codepath/số học khác; cùngagent không
   được gọi independenthuman/feedreview. C2/correctness khác C1/edge/prop.

Không own2025+, broker/runtime/account/providertrảphí mới, muaEA/challenge.
Source gaps hoặc phí khác đòi amendment/version trước outcomes bị ảnh hưởng,
không tự đổi expectedhash hoặc trừ phí hậu kiểm để tựpass.
