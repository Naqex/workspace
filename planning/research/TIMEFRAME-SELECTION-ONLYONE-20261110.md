# Chọn timeframe cho vòng only one đầu tiên

Research10/11/2026 theo yêu cầu owner chốt được khung, đối chiếu cộng đồng và
quỹ lớn rồi đề xuất bằng bảng. **Owner đã chốt M15 làm khung tín hiệu cho vòng
nghiên cứu onlyone đầu tiên**, qua xác nhận “OKE CHỐT khung m15 đi” ngày10/11.
Quyết định này thay đề xuất H1 ban đầu; sản phẩm, cơ chế và các phần case còn
lại chưa được chốt. Đây là scopechoice, không proof M15 optimal/profitable.
Không strategy/data/numericalrun, cache/schema/risk/holding/authority thay đổi.

## Nguồn đã đọc và giới hạn chuyển giao

| Nguồn primary/cộng đồng | Bằng chứng có thể dùng | Không được suy |
|---|---|---|
| [Man AHL, The Need for Speed,04/01/2023](https://www.man.com/insights/need-for-speed-trend-following) | Article text mô tả MAC nhiều tốc độ,50futures/FXforwards1995–08/2022; fast speed phản ứng/riskproperties khác slow, turnover làm chi phí tăng; aftercost scenarios cho5bnUSD | Speed là sensitivity theo ngày/tuần/tháng, không chartM5/M15/H1. Không quỹ đề xuấtM15 hoặc mọi faststrategy tệ; không đọc số trong chart bịexternalrender để tự lập ranking |
| [AQR, Transactions Costs: Practical Application,2018](https://images.aqr.com/-/media/AQR/Documents/Insights/White-Papers/AQR-Transactions-Costs---Practical-Application.pdf) | PDF26pages; đọc executive/introduction và sections explicit/implicitcosts: commissions, spreads/slippage và measurement context cần phân biệt | Không retailEURUSDcost, M15hit-rate hoặc templatechọnkhung. Landing/find refresh cótimeout; PDFopen đã đọc được, không claim fullpaper reproduced |
| [FTMO Academy, How to Create a Trading Idea](https://academy.ftmo.com/lesson/how-to-create-a-trading-idea/) | Chọn duration/session/instrument và timeframe theo tradeidea; ví dụH1direction/M15entry | Tài liệu giáo dục, không thống kê tài khoản thắng, không endorsement M15 hoặc yêu cầu multitimeframe |
| [Reddit, NQ M5/M15/H1 comparison](https://www.reddit.com/r/algotrading/comments/1wxrg86/same_nq_breakout_rules_three_candle_sizes_100_on/) | Tác giả kể fees làm fastversion âm; comments và tác giả thừa nhận20bars đổi horizon giữa khung; cluster-by-day cần xem | Chưa code/raw/brokerstatement verified, cólink sản phẩm. Không kết quả đại diện/controlledpureTFcomparison hoặc chuyển NQfutures sangEURUSDprop |
| [Reddit, best timeframe](https://www.reddit.com/r/algotrading/comments/o7kdyc/) | Nhiều ý kiến/markets/horizons; nhắc fee/execution constraints | Không sample đại diện, currentfees hoặc proof HFTguaranteedprofit/khungnào luôn thắng |

Search cộng đồng chỉ dùng xác định câu hỏi và lỗi so sánh, không suy mode/
median timeframe thành công. Tài liệu tổ chức cho nguyên tắc speed/cost/risk,
không cung cấp survey chung xác nhận hedgefund haypropwinner dùngM15 nhiều nhất.
Không truy cập gate/login, cài package hoặc lấy private fund data.

## Đề xuất xếp theo độ phù hợp với hồ sơ owner

Owner: thu nhập chính trong tương lai, vốnprop/riskcá nhân thấp,24/7declared,
onlyone, recent-first. Muốn đủ cơ hội để kiểm chứng nhưng chưa có mức chịu
chuỗiSL/cashflow/reserve cụ thể. Các ranks là qualitative judgement, chưa đo.

| Khung quyết định | Quan sát trong24h liên tục có đủ data | Đánh đổi và đề xuất |
|---|---:|---|
| M1 |1.440bars|Đểsau; chỉ khi cơ chế thật sự ngắn và execution/cost đủ cơ sở. Không allM1gambler hoặc ticks là trades |
| M5 |288bars|Có thể phù hợp cơ chế nhanh nhưng thêm nhạy cảm về thời điểm signal/fill; chưa ưu tiênvòngđầu |
| **M15** |**96bars**|**Owner đã chốt vòng1**: quan sát intraday thường xuyên hơnH1, vẫn tách khỏi mục tiêu scalpingrấtngắn; chưa biết có thêm independenttrades |
| M30 |48bars|Hợp lý nếu cơ chế cần; chưa evidence làm nó tốt hơnM15 hoặc cần thêm một branch nghiên cứu |
| H1 |24bars|Khung dự phòng khi cơ chế dài hơn; có nhiều toolingreuse. Không đổi sangH1 để cứu một loser hậu kiểm |
| H4/D1 |6/1bars|Phù hợp hướng dài hơn nếu có cơ chế; ít điểm quan sát theo ngày, không suy ítbar là ítsignal độc lập hoặc luôn sai cho income |

M15=4điểmbarclose/h, H1=1; không M15=4trades/h hoặc gấp4effectiveN. Thêm lệnh
trong cùng phiên/trend có dependency; sample/uncertainty cần đo trên trade/event
groups. Winrate càng precise vẫn có thể là netnegative; không bỏ fees/risk.
Nhịp2–5trade/tuần ở profile chỉ mong muốn, không observedforecast hoặc quota.

### Khung tín hiệu đã chốt và phần phạm vi còn cần chọn

- Một khung **tín hiệu M15 đóng nến**, dùng thông tin biết tại decision; order
  fill sau decision. Chưa chỉ định session/indicator/entry/exit/lookback/SL.
- Một cơ chế/candidateversion và một sản phẩm; **EURUSD** vẫn là đề xuất reuse,
  FTMO2-StepSwing làm targetprofile. Không tự xem hai phần này là lựa chọn mới
  của owner hoặc triển khai account. H1confirmation không tự thêm vào vòng1.
- Tick/BidAsk được dùng để kiểm execution/risk; M1nếu cần làm nguồn tổng hợp,
  không tự thành một chiến lược mới. Chưa chứng nhận M15loader/engine đã đáp ứng
  mọi gate; trước numerical cần source/aggregation/timing theo protocol mới.
- Giữ risk0,25% chỉ ở baselineoffline đã đề xuất; không riskgrid, chốtlivebudget
  hoặc chọn accountsize. Intraday là hướng; exactholding/cutoff cần economics
  và replay, không tự forceclose oldbooks để làm sạch gap/payout.
- Đánh giá một đợt hữu hạn rồi review; giữ kết quả âm, không đổiM15→M5→M1 theo
  chart. Muốn đổi khung phải có cơ chế/evidence, recordtrial vàprotocol mới.

Đây là quyết định chốt khung để tránh phân tán, không nghĩa bỏ qua một cơ chế
thực tế chỉ vì cần độ phân giải khác. Bước kế là chọn sản phẩm và admission
một hypothesis phù hợp khung; chưa tìm winner bằngmultiframegrid hoặc thêm
manager/framework. C1/C2 và mọi gateholdout2025+/broker giữ nguyên.

## Bẫy kiểm chéo khi sau này có lý do so khung

20bars×5min=100min;20bars×15min=300min;20bars×60min=1.200min. Giữ tham số20
không giữ cùng informationhorizon, ATR/SL và turnover cũng có thể đổi. Nếu câu
hỏi là tác động sampling đơn thuần, cần thiết kế control time-matched trước
outcome và giữ session/sizing/cost/fill assumptions rõ; không tự đổi ATR cùng
mọi biến rồi quy chênh lệch cho timeframe. Equalclocklookback cũng không tự
kiểm soát hết các khác biệt. Không chạy phép so này trong lượt research.

Locators kế thừa: [profileowner](PROP-FIRM-FIT-20261102.md#only-one-hồ-sơ-mục-tiêu-và-các-case-để-owner-chọn--10112026),
[source-transfers](STRATEGY-ORIGIN-TRANSFER-REVIEW-20261108.md),
[recent-window limits](RECENT-WINDOWS-EDGE-DECAY-AND-DISCRETION-20261110.md).
Không có benchmark mới; nguồn text/abstract/sections được đọc đúng scope đã ghi.
