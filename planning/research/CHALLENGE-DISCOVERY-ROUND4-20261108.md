# Discovery4: tám hypothesis H1 — khóa trước outcome, 08/11/2026

Scope trong [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md): mở timeframe
H1 trên EURUSD, giữ native execution/risk. Không thay8H4rules hoặc xem outcome
holdout2025+. Tám bộ dưới là recipes của project, không exact paper replication.
Rủi ro selection/trial count tăng theo recipes/variants; không gọi8edge độc lập.

## Chung cho cả tám

Nến H1mid từ observed Bid/Ask, chỉ observe sau khi đóng. Entry/strategy exit
ở quote sau decision qua core hiện có; không same-bar fill. Một position,
không reverse cùng event. SL1,5×WilderATR14 tại entry, planned25USD/initial10k,
không fixedTP; exact sizing/cost/margin/financing/internalrisk từ core cũ.
Reference/stress giữ pin account-spec của studies cũ khi dùng native tick;
H1screen dùng referencebuy9,3/sell−0,31USD/lot và stress20/20, slip0/0,00002,
commission5USD/lot round trip (2,50mỗi side, khớp core). Không bỏ funding hoặc spread embedded.

Warmup ít nhất100observed H1, không bịa missing hours; ATR/RSI/state/clock
phải prefix/restore được. RSI Wilder14, khởi tạo gain/loss từ14changes;
loss=0/gain>0 trả100, gain=loss=0 trả50. Equal thresholds không tự crossing.
Held-bars gồm bar chứa fill; reset theo positionID, không theo trade outcome.
Distance dùng ATR cập nhật tại decision; shock test dùng ATR của bar trước.
SL/TP ở risk/engine không tự chuyển thành authority gửi broker.

## Recipes cố định

| ID suffix, prefix `eurusd-h1-` | Entry khi flat | Exit |
|---|---|---|
| `rsi14-reentry-atr14x1p5-time12-r025-v1` | BUY khi RSI trước<=30<RSI mới; SELL khi RSI trước>=70>RSI mới | BUY RSI>=50, SELL RSI<=50; hoặc12bars/SL |
| `shock2-reclaim-atr14x1p5-time12-r025-v1` | Bar trước có range>=2×ATR trước, close ở1/4dưới và bar mới close>midpoint thìBUY; đối xứngSELL | BUY close>=mean20prior, SELL<=mean20prior; hoặc12bars/SL |
| `prior-day-break-atr14x1p5-close20-r025-v1` | Decision08–16UTC, BUY close>previous valid dayhigh, SELL close<daylow; một emitted entry/ngày | Decision>=20UTC hoặc ngày đổi, hoặcSL |
| `prior-day-fade-atr14x1p5-close20-r025-v1` | Cùng clock/range; sweep một biên rồi close trở lại range, không sweep cả hai; một entry/ngày | Midpoint range theo hướng position, hoặc20UTC/ngày đổi/SL |
| `bb20-reentry-atr14x1p5-time12-r025-v1` | Dùng20closes trước tạo mean±2populationSD; prevclose<=lower<newclose thìBUY, prevclose>=upper>newclose thìSELL | Mean20prior theo hướng hồi, hoặc12bars/SL |
| `pullback20-80-atr14x1p5-time24-r025-v1` | Fast20/slow80 tính tới nến mới; BUY fast>slow và prevclose<=prevfast, newclose>fast; SELL ngược | Fast đảo qua slow, hoặc24bars/SL |
| `europe-am-short-atr14x1p5-close13-r025-v1` | SELL tại decision08:00 Europe/Berlin của weekday; một emitted entry/ngày | Decision>=13giờ cùng localclock/ngày đổi, hoặcSL |
| `london-postfix16-20-atr14x1p5-r025-v1` | BUY tại decision16:00 Europe/London của weekday; một emitted entry/ngày | Decision>=20giờ localclock/ngày đổi, hoặcSL |

Daily range: gom observed H1 theo ngàyUTC; chỉ một ngày có>=18observed hours
mới được dùng làm prior range, giữ high/low thực đã có. Sunday thiếu hours
không thay prior range. Range cũ hơn4calendar days không entry. Rules dùng
prior range khi signalbar đã đóng, không chứa signalday. Các trường hợp
missing clock/gap không giả entry/exit ở giờ không có quote; ghi delay thực.
Berlin/London dùng zoneinfo/DST theo decision timestamp (barstamp+HOUR).

Hai clock hypotheses gợi từ dòng tiền/benchmark, giờ và SL là lựa chọn của
project trước outcome, không khẳng định đây là portfolio của tác giả. Không
được sửa giờ/threshold sau screen để tiếp tục dùng cùng version.

## Thứ tự và tiêu chí của đợt

1. Code/fixtures8recipes, H1warmup/source/restore; kiểm legacyH4 prefix giữ
   nguyên decisions/fills/accounting. Chưa chạy economic outcome trước tests.
2. ConsumedQ1/2022 screen8×2costs để mô tả counts/PnL và chất lượng. Đây là
   development, không ranking edge. Tick check một nhóm có lý do và bản định
   gác; nếu có material mismatch thì sửa/re-register trước annual stage.
3. Historical2023 (đã consumed) chỉ được mở sau source/protocol/input pins và
   stage record được lưu. Giữ tất cả8recipes khi screen để giảm winner-only
   selection. Net âm/thưa trades là no-promotion/inconclusive trong scope,
   không tự reject family. Không chọn một quý đẹp hoặc đổi cost để đi tiếp.
4. Native tick/risk review ưu tiên tối đa2bản có net dương ở cả phí trên cả
   hai periods; nếu không có bản thì không ép survivors. Trường hợp coarse
   near-zero/stop uncertainty phải tick review trước khi dựa vào dấu PnL.
5. Review C1/C2 và quyết định round mới trước outcome;2024/2025 hoặc sizing/
   exit variants cần stage/protocol mới, không tự mở holdout từ file này.

## Nguồn, không là lời hứa lợi nhuận

- [RSI definition](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/),
  [Bollinger definition](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/): định nghĩa, không evidence recipe có edge.
- [SNB2011-04](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2011/working_paper_2011_04/publications0_en/working_paper_2011_04.n.pdf), method/session discussion pp6–12:
  historical intraday/orderflow mechanism; không CFD implementation của project.
- [BOC2021-48](https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf),
  fixing timing/reversal portfolios: cơ chế pre/postfix; không exact recipe hours
  hoặc PnL của hai clock hypotheses trên.
- [NYFed125](https://www.newyorkfed.org/research/staff_reports/sr125.html): mechanism
  levels/reversal; prior-day/ATRshock/thresholds vẫn là project hypotheses.

Đây là study-design freeze; actual source/input hashes và finite-job status ở
attempt/AI receipt. Mọi lỗi giữ attempt cũ. Không auto retry cả study hoặc báo
eligible challenge chỉ vì screen dương.
