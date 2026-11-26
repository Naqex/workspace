# US500 daily reversion — hai phiên bản đăng ký trước outcome

Tiếp campaign C1/C2 sau noise14 không đạt; checkpoint không là yêu cầu dừng.
Không đổi bản noise14. Dùng lại raw M1 Bid/Ask2022–2024 đã sealed và NYSE
calendar đã kiểm; không download, account mới, broker/model calls hoặc2025+.

## Cơ sở và giới hạn chuyển giao

Đã đọc08/11 [Pagonidis, The IBS Effect, NAAIM author paper](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf),
method/results/filter pp2–6. Paper dùng daily ETF OHLC/CSI đến2013; IBS là vị trí
close trong range ngày, có phân tích long/short và Cutler RSI3+IBS filter.
Tác giả lưu ý volume và chi phí quan trọng. Chưa có exchange volume đáng tin
cho CFD, nên không giả đã áp volume filter hoặc replication/performance paper.
Đây là adaptation price-only có SL/risk/funding/next-minute fills riêng.

## Hai policyIDs liên quan, không hai bằng chứng độc lập

| ID | Entry sau cash close đã biết | Exit |
|---|---|---|
| `us500-d1-ibs02-hold-atr14x1p5-r025-v1` | BUY khi IBS≤0,20 | EXIT khi IBS>0,20; giữ nếu ngày tiếp theo vẫn thuộc bucket thấp |
| `us500-d1-cutler3-10-40-ibs05-atr14x1p5-r025-v1` | BUY khi Cutler RSI(3)<10 và IBS≤0,50 | EXIT nếu RSI>40 hoặc IBS>0,50; không pyramid |

Daily range/close dùng **Bid** cash OHLC, không lấy trung bình independent
Bid/Ask extrema làm observed midpoint. IBS=(C−L)/(H−L); H=L thì unavailable.
RSI3 dùng ba thay đổi close liên tiếp (4closes), arithmetic gain/loss sums,
loss0→100. ATR14 là arithmetic mean14true ranges của đúng14cashsessions,
TR=max(H−L,abs(H−previousC),abs(L−previousC)); không dùng ATR tương lai.
Hai bản fixed hardSL distance1,5×ATR14, xác định lúc decision. Đây là risk
adaptation, không paper threshold optimization. Không TP hoặc trailing.

Daily signal chỉ hình thành sau close của phút cuối (16:00/13:00NY).
Entry/exit queue fill đúng open1phút sau decision (16:01/13:01), pending hết hạn
nếu phút đó không có quote; không same-close/closing auction fill. Giữ qua
đêm và weekend nếu exit rule chưa tới. Khi dailyOHLC thiếu, cả hai bản queue
safetyEXIT tại cashclose đã biết từ calendar; không đòi tính được IBS mới.
Không forcedclose cuối năm; open/pending/floating báo đủ. Hai ngày oversold
liên tiếp không đóng/mở giả tạo hoặc pyramid để nhân số giao dịch.

## Dữ liệu, mô phỏng và costs

Mỗi năm là annualbook riêng10k/plannedrisk25USD, không continuousportfolio.
Không entry trước đủ14TR và RSI history; đầu năm là warmup, khôngPnL bịa.
Missing bất kỳ cash minute→dailybar chưa đủ range, không dùng để tạo tín hiệu
entry/ATR; 14TR/4close windows phải consecutive đúngsessions, không chọn các
ngày đẹp ở xa hơn. Đây là causal gate tại dailyclose, không hindsight skip ngày.
Scheduled EXIT vẫn có thể queue dù bar thiếu; SL vẫn theo dõi trên mọi quote.

Shared M1 book dùng toàn bộ raw extendedsession, oneposition/queue, hardSL
closing-side OHLC qua existing `protective_exit_for_bar`, sizing/fees qua
existing financialprimitives. M1stop level/open không là firstcrossingtick.
Quote gaps trong exposure giữ flagged; weekend/dailyhalt vs feed gap chưa có
targetbrokercontract nên không chứng nhận intrabar DD/prop compliance.

Market/cost như noise14:1USD/point/lot,grid0,001,min/step0,01,max50,leverage10,
commission0,50USD/lot/side,slippage0,25/0,75point/side. Thêm **declared funding**
1USD/lot/reference hoặc2USD/lot/stress mỗi00:00UTC nếu đang giữ, gồmcalendar
weekend/holiday; mỗi khoản round cents. Không gọi đây là historicalbroker swap.
Funding giữ riêng cash/trade/net và mark equity; stopplanned25 chưa bao gồm
unknown holdingduration/futurefunding/gaploss, không quảng cáo totalrisk capped25.

## Kiểm trước và quyết định

Trước PnL: known IBS/RSI/TR, missinghistory, prefixcausality, quote delay/expiry,
SL gap, overnight/weekend funding/calendar, scheduledEXIT khi missingbar,
cash/floating/open-end và nullcontrol. Newoutput/source/protocol/calendar/data
hashes; một writer/status/events/failure/deadline. Không sửa thresholds sau outcome.

Tối đa2versions×3years×2costs=12numericrows, kèm nullcontrols. Báo cả âm/dương,
annualbooks không cộng thành CAGR. Ưu tiên review nếu mỗi năm dương cảcosts
và không materialdefect; ít trades/openpaths/OOS/missingcontract giữ unknown.
Đây chỉ exposeddevelopment/robustness, không C1. Survivors mới được đăng ký
long-history/native/prop/uncertainty/forward bước tiếp. Không nới risk hoặc
đưa losers vào challenge. Chi phí kỹ thuật/PnL/trialhistory đều giữ ngoài chat.
Nếu future expiry/clock cần thiết, phải đăng ký version mới; không tự đổi từ
regime hold sang fixed holding sau khi đã xem PnL.

