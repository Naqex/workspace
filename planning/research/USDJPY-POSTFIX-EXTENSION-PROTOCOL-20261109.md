# R085 — kiểm bán sau Tokyo fix trên lịch sử rộng hơn

Đăng ký trước outcomes mở rộng ngày09/11/2026, tiếp
[R084 results](USDJPY-TOKYO-COMPONENT-RESULTS-20261109.md). R084 mua chính
không đạt; diagnostic bán sau fix dương ở2019/2022. **Chọn hướng này sau khi
đã thấy kết quả control**, không independent discovery hoặc clean OOS.
Liên quan R020/R021/R084, không reset trial count. Không sửa R084 để đổi winner.

## Câu hỏi và dữ liệu khóa

Giữ **SELL09:56→10:24 Asia/Tokyo**, scheduled09:55→10:23 cộng modeled lag1phút;
M1sideOpen proxy, không fill chính xác benchmark/bankTTM. Primary chỉ nominal
5/10/15/20/25/30 nếu là declared bank businessday. Sensitivity chuyển ngày
nghỉ về previousbusinessday, dedup. Cùng Christmas exclusion, không EOM31.

Mở rộng **toàn bộ các năm còn lại trong2010–2024**, không chọn vài năm thuận
lợi:2010–2018,2020,2021,2023,2024. Hai năm2019/2022 là discovery, reuse đúng
pins/rows từR084 và báo riêng; không đưa vào gate extension. Toàn bộ13năm mới
đều dùng calendar rule cố định, không đổi theo PnL hoặc price availability.
Source có thể đã xuất hiện trong research khác; không chứng nhận unseen data.
Không mở2025+/holdout hoặc gắn nhãn OOS sạch khi chưa audit exposure đủ.

CSV Cabinet officialSHA
`cec37a743c96995cdb9cb52b685c9003634682a9b0e1a640a6b9b96881fe964a`, đọc tất cả
holidays2010–2024. Monday–Friday trừ CSVholidays,Jan1–3,Dec31. Calendar-only
generator và oracle bằng thuật toán khác phải khớp toàn bộ mapping trước
source fetch. Không tự khẳng định đây là PIT/all-bank payment convention.

## Nguồn, đối chứng, phép tính

- Existing Dukascopy1.51.1, USDJPY M1 Bid/Ask UTCday,0.001JPY/USDgrid;
  giữ explicit vs padding và zero-volume source bars. New requestbudget tối
  đa2200day-side URLs, deadline1800s, failurecap1,noauth/WAF/retry. Copy/reuse
  source cũ theo hash, không ghi cache/raw/evidence R084. Một writer, status/
  events/seals/CANCEL; giữ completed prefix khi fail, không tự retry job.
- Strict29holdingminutes, bothsides Open/Close; missing/crossed bất kỳ planned
  row =>unknown, annualN/A. Không dùng futurequality làm filter vào lệnh.
- Primary postfixSELL, prefixBUY/prefixSELL/null chỉ controls; lịch phụ vẫn
  sensitivity, không substitute primary. 15years×2calendars×4rules×2costs =
  240books gồm32discoverybooks reuse, không240independenttrials.
- Cùng R084100kUSD notional,5USDcommission/100kRT,reference0/stress0.4pipRT,
  Ask/Bidspread,exit-midconversion perrow. Không account/risk/SL/funding
  policy hoặc brokerfees certificate. USD và pip aggregate riêng.
- Sourcefullraw/native/Fraction checks cho nguồn mới; hash + acceptedreview
  reuse cho old139days. Separate direct-fill financialoracle đối chiếu row/
  aggregate/fees/conversion/counts/null/unknowns. Mutatecash/calendar/authority/
  primary/gate/counts phải bị validator thực từ chối. Không update consumer
  đang pin trong khi source chạy.

## Gate ưu tiên nghiên cứu, chưa chứng minh edge

Chỉ **primary nominal postfixSELL, stress**, trên13extensionyears:

1. Không năm nào unknown, mỗi năm ít nhất35plannedresolvedtrades.
2. Ít nhất10/13năm netUSD>0.
3. Tổng netUSD dương trong cả bốn block đã khóa:2010–2013,2014–2017,
   2018–2021 (bỏ2019discovery),2022–2024 (bỏ2022discovery).
4. Không lỗi material; xem cả outliers/concentration/mean/median/counts.

Đây là heuristic triage freeze trước outcomes, **không p-value/chứng nhận
statisticaledge hoặc xác suất pass quỹ**. Unknown =>inconclusive đúng phạm
vi; resolved nhưng không đạt =>không ưu tiên exactrecipe. Controls hoặc
sensitivity thắng không tự qua primarygate. Không retune clock/fees/date/
lot/SL để cứu kết quả.

Nếu qua, đăng ký **một** protective-risk/path wrapper causal trước outcomes
mới; vẫn cần cost/execution realism, prop-specific equity/time-fit, OOS đủ
quyền, forward và owner handover. Nếu không qua, lưu negatives và chọn
mechanism mới có lý do. Không mua challenge/cài EA/broker calls.

Private `execution-v1/jpy-postfix-calendar-v1/`, `jpy-postfix-preflight-v1/`,
`jpy-postfix-source-v1/`, `jpy-postfix-component-v1/`. Ghi source/review/compute/
CPU/wall tách riêng, pins/snapshot và trạng thái cuối. Chuẩn bị/code/Git nếu
không có timer thì ghi unknown, không bịa time saved. Goal C1/C2 vẫn active.
