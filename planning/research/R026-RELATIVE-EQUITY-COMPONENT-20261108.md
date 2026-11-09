# R026 price-proxy component v1 — đăng ký trước outcome

Thuộc [campaign v2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md). Pilot source
[đã admitted](RESEARCH-DATA-ADMISSION-RESULTS-20261108.md), chưa equity signal
hoặc FX outcomes. Đợt này là adaptation hai vùng EUR/US; không exact panel
paper, không account bot hoặc WMR benchmark/fill reconstruction.

## Một primary, không chọn rule theo outcome

- Hai năm2019 và2022, đủ12tháng/năm; tất cả là historical development/exposed
  validation, không clean OOS. Không2025+. Last NYSE cash-session day là
  **calendar proxy**, không lịch WMR được xác minh; ghi limit ngay tại output.
- Equity endpoints: close của phút cuối NYSE session đầu tháng và áp chót.
  Reuse calendars frozen, kể cả early closes. EZU_USD, SPY_USD và EURUSD phải
  có raw-listed Bid/Ask đúng cùng timestamp; không carry/fill hoặc đổi ngày.
  Dùng Bid close để tạo price signal; tất cả known-at=baropen+60s phải trước
  quyết định15:00 Europe/London của ngày proxy cuối tháng.
- Gross local return factors: `GE=(EZU1/EURUSD1)/(EZU0/EURUSD0)`,
  `GU=SPY1/SPY0`. GE>GU ⇒ SELL EURUSD; GE<GU ⇒ BUY; bằng nhau ⇒ no signal.
  Đây là sign-only bilateral adaptation, không fit coefficient/threshold/
  leverage hoặc tuyên bố ETF là Total Market/total-return index. ETF adjustments
  vẫn unknown; preserve proxy bias, không cộng PnL ETF hoặc giả cổ tức0.
- Primary FX component: first M1 **open endpoints**15:01 và16:03 London,
  đúng cả Bid/Ask nguồn. Entry sau decision một phút; exit sau normal4pm
  five-minute window, không claim khớp fix. M1 side endpoints có thể không
  synchronous executable ticks: kết quả chỉ costed price component.
- BUY: exitBid−entryAsk; SELL: entryBid−exitAsk. Standardlot100kEUR,
  commission2,50USD/lot/side; reference slippage0, stress0,00002/side;
  FXcost helper đã có. Báo netpips/USDperlot, không%tài khoản. Không financing
  trong holding window này; target-firm commission/slippage chưa account-verified.
- Baselines: alwaysBUY, alwaysSELL, opposite-primary cùng endpoints/costs.
  Chỉ diagnostics; primary fail không promote baseline sau outcome.
- Missing source/side/endpoint ⇒ unresolved, giữ mọi month row và lý do.
  Không tính unresolved là0 hoặc chỉ báo số tháng còn lại.

## Tiêu chí và thực thi

Ưu tiên bước native/risk/longer validation chỉ khi **primary có ít nhất10/12
tháng resolved từng năm và tổng stressnet>0 ở cả hai năm**. Đây là heuristic
triage đã khóa, không statistical edge certificate hoặc hard reject family.
Báo từng tháng/cost, counts/win/loss/concentration/maxloss và reference/stress;
không tối ưu threshold hoặc đảo hướng sau khi biết kết quả.

Tối đa336 requests instrument-side/day, reuse exact28pilot requests và raw
cache; không sửa pilot. Cùng existing public provider/pinned1.51.1, không
account/key/dependency mới. Một writer, raw/seals/source/protocol/config pins,
status/events/deadline/CANCEL; native retry0, helper tối đa2retries transient
timeout/5xx với cumulative cap8/deadline1200s; auth/WAF/429/schema không retry.
Giữ partial; next attempt phải đăng ký recovery delta, không lặp thành công.

Source admission trước outcomes. Kiểm synthetic algebra/currency direction,
known-at/future mutation, DST/earlyclose và missing-side. Reviewer Fraction
không import cost/signal function để so signal/financials trên mọi tháng;
kiểm raw endpoint locators và control census. Timing theo download/admission/
compute/review riêng. Review cùng agent, chưa independent human/model sign-off.

Nếu primary đạt triage vẫn cần SL/sizing, tick/delay/source-realism, prop-equity
path/time-fit3/6/12months, genuinely unseen protocol/holdout và prospective
shadow/reconciliation trước C1/C2. Nếu không đạt, giữ negative adaptation và
chuyển hypothesis có cơ sở; không hạ phí/risk/calendar requirements để cứu.
