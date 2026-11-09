# NASDAQ cash RSI3 + IBS: phép sàng lọc economics có điều kiện

Đăng ký trước outcomes, tiếp [method](NASDAQ-DAILY-REVERSION-METHOD-20261108.md).
Chỉ chạy sau [M1 history review](NASDAQ-M1-HISTORY-PROTOCOL-20261108.md) đạt
`admitted_for_economic_registration`; full joint quality vẫn báo riêng.
Nếu gate không đạt, dừng trước economics; không giảm yêu cầu200sessions để chạy.

## Câu hỏi và recipe cố định

Liên quan R050/Pagonidis, adaptation sang NASDAQ CFD, không paper replication
hoặc independent hypothesis. R063 component ID
`nasdaq-cash-cutler3-10-40-ibs05-component-v1`; chưa account policy.

Daily cash Bid high/low/close từ mọi explicit M1 cash minute theo registered
NYSEproxycalendar, bao gồm halfday13NY. Bar thiếu một expected paired minute
hoặc crossedOpen/Close không complete, không impute. Warmup Nov–Dec2018/2021,
development2019/2022, giữ indicator state qua Jan1, bắt đầu flat mỗi năm.

CutlerRSI3 dùng4dailycloses, gain/loss simple sums; zero losses=>100.
IBS=(close−low)/(high−low), flat range=>undefined. Reuse pure math
`index_daily_reversion.plans_for(..., RSI)` và separate Fraction oracle;
không reuse US500 instrument, financial book hoặc funding clock.

- BUY nếu RSI<10, IBS<=0,5 và đủ14consecutiveTR/15completecashdays; ATR14
  parent readiness giữ dù component không dùng stop distance. Không tune
  readiness sau data. Chỉ long, một hypothetical unit/position, không pyramid.
- EXIT nếu RSI>40 hoặc IBS>0,5; incomplete cashday cũng safetyEXIT. Không TP,
  SL, risk sizing, margin hoặc account10k trong phép sàng lọc này.
- Decision tại cashclose; exact fill **close+1minute** sourceM1Open. BUY Ask,
  EXIT Bid; nếu exact minute thiếu/crossed thì cancel+log, không fill lại.
  Pending trước nextdecision bị cancelled/logged. Decisions trong gap vẫn
  được ghi, không chỉ observe những ngày có quote. Không warmup trade.
- Cuối mẫu giữ open và pending; mark final observed BidClose/AskClose từ
  last paired source minute, reserve full roundtrip slips; không forceclose.
  Đánh dấu path gaps khi holding; sourceM1Open/Close chỉ intervalproxy.

## Economics và retention

Một research unit=1USD/priceunit, không lot và không accountreturn. Reuse R061
declared cost assumptions: observed Bid/Ask, slip0,25/0,75mỗi side, commission0,
funding entryAsknotional×8%/16%/365, debit centHALF_UP tại22UTC/calendar day,
entry<boundary<=exit và accrue endexclusive khi open. Dividend/targetswap/
actualfills chưa biết. Không lấy noSL component làm challenge policy.

2years×2costs; null control có cùng decisions/cost nhưng không mở position.
Null net0, không là marketbenchmark. **Retain để mở rộng nghiên cứu** chỉ khi
cả2stressyears net gồm floating>0, >=10closedtrades/year, không missingfill
hoặc pending/open cuối mẫu. Mọi unresolved/gap giữ trong báo cáo; ngay cả
retained vẫn chưa chứng minh executable paths/SL/sizing/prop/selection/OOS.
Không thay thresholds/cost/calendar/rule sau outcome. Không retune nếu fail.

## Implementation/review

Reuse raw-bound books từ v2, không source refetch/2025+/broker/modelcalls.
Source result/review/config/8book/quality/calendars hashes được pin trước
numeric; fullsource reviewer đã kiểm, không tải ticks để kiểm component.
Code `nasdaq_cash_reversion_component.py`, tests về causal delay/gap/missing
decision/funding/boundaries/mark/noauthority. Separate Fraction signal oracle
và pertrade/funding arithmetic kiểm mọi outcome, source endpoint bindings,
mutation quote/time/funding/falseauthority reject. Sameagent/provider, không
independent human/model review. Output private
`execution-v1/nasdaq-cash-rsi-component-v1`, one writer/events/status/CANCEL/
failure/deadline120s và snapshots trước run. Nếu admission không đạt, chỉ
prepared code, chưa count implemented policy hoặc economic record.
