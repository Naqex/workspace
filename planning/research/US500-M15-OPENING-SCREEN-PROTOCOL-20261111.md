# US500 M15: hai luật mở phiên, đăng ký trước kết quả

11/11/2026. Owner đồng ý US500 chính/EURUSD khảo sát nhẹ và cho phép sàng lọc
để xem tiềm năng. Đây là screening offline, không broker/holdout/challenge.

## Câu hỏi và lineage

Sau quá trình mở phiên cash Mỹ, cú phá biên15phút đầu tiếp diễn hay bị hấp thụ?
Hai project hypotheses thuộc cùng họ, không hai edge độc lập. R094 liên quan
R016/R017 FX ORB và R065 NASDAQ first5direction; R095 liên quan failed-break
R006/R019. Giữ toàn bộ negatives, không gọi các bản mới là paper replication.
Khác biệt là cash-open US500, observed Bid M15 range, closed-bar first-break
và return-inside state; không chỉ đổi nhãn H1→M15 của một policy cũ.

Primary đọc11/11: [NYSE auctions](https://www.nyse.com/trade/auctions) xác nhận
quá trình mở phiên bắt đầu09:30ET, không phải mọi stock mở đồng thời. Đây là
cơ sở đặt câu hỏi, không bằng chứng lợi nhuận hoặc orderflow CFD đã quan sát.

## Hai bộ luật cố định

- Universe: USA500.IDX/USD Dukascopy, proxy cho target US500.cash FTMO. Dùng
  observed paired-source M1 Bid/Ask, không decoder padding hoặc quote-volume
  giả làm volume giao dịch sàn. M15 quyết định, M1 mô hình khớp/SL.
- Calendar: fixtures NYSE2022/2023/2024, America/New_York/DST; chỉ phiên390phút,
  halfdays skip theo lịch biết trước. Cash session không phải broker hours.
- Range: Bid high/low từ09:30 inclusive đến09:45 exclusive; phải đủ15phút cả
  hai side. Width=high−low>0. Không mean(side extrema) thành mid extrema.
- Kiểm các M15 đã đóng, lần lượt10:00,10:15,10:30,10:45,11:00NY. Mỗi lần chỉ
  dùng prefix09:30→decision; thiếu prefix thì không tạo tín hiệu sau đó trong
  ngày. Không dùng coverage cuối ngày để loại một entry quá khứ.
- **R094 `us500-m15-or15-firstbreak-width-stop-noon-v1`:** close đầu tiên >high
  thì BUY, <low thì SELL. Equality không breakout. Một attempt mỗi phiên.
- **R095 `us500-m15-or15-failedbreak-width-stop-noon-v1`:** ghi nhận breakout
  đầu tiên như R094, chưa vào. Khi một M15 sau đó đóng trở lại [low,high],
  giao dịch ngược hướng breakout đầu; phải có hai nến khác nhau và vẫn trong
  cửa sổ tới11:00. Không đổi chiều theo breakout tiếp hoặc dùng wick hindsight.
- Decision ở thời điểm nến đóng; entry exact M1 Open sau decision60giây.
  Thiếu fill minute thì reject, không điền giá hoặc khớp muộn. BUY Ask/SELL Bid.
- Cả hai: hard SL cách giá entry đúng một opening-range width, round ra ngoài
  theo grid0,001. **Không TP cố định**, không trailing/breakeven/retest/filter.
  Exit decision12:00NY, fill12:01NY nếu chưa SL. Không ép thắng/thua ở RR cố định.
- Reuse `index_m1_book`: open-gap SL trước scheduled action, rồi M1 SL trên
  Bid cho BUY/Ask cho SELL. Một barrier nên không cần đoán thứ tự SL/TP cùng nến;
  vẫn là mô hình M1, không native tick-first-crossing. Recovery EXIT mỗi cash
  open, như shared book; thiếu held path được đánh dấu unresolved và full-net
  năm đó là N/A trong báo cáo, không dùng recovered model sum làm exact PnL.

## Vốn/chi phí chỉ là kịch bản offline

Mỗi annual book bắt đầu10.000USD, planned stop-risk25USD gồm modeled fees/
slippage, max1position. Reuse sizing/contract1USD mỗi point mỗi lot, min/step
0,01lot/max50/grid0,001/leverage10 của shared book. **Không xác nhận spec
Standard hiện tại và không chốt risk thật của owner.** Không cộng ba annual
books thành tài khoản liên tục/CAGR hoặc xác suất pass.

Published current index commission0; spread nằm trong Bid/Ask, không trừ lần2.
Slippage reference0,25point/chiều, stress0,75point/chiều, là declared scenarios,
chưa measured FTMO. Unexpected carry dùng shared declared funding1/2USD/lot/
calendar-day, và vẫn giữ unknown path; không chứng nhận swap/dividend lịch sử.
[FTMO commission](https://ftmo.com/en/blog/zero-commissions-on-indices/) và
[news](https://ftmo.com/en/faq/can-i-trade-news/) đọc11/11; screening chưa có
historical restricted-news filter/closure engine nên **không Standard-compliant**.

## Input, phạm vi và tiêu chí đọc

Dùng đủ bốn quý mỗi năm2022–24 tại existing `us500-explicit-source-v1`.
Proof SHA từ receipt đã accepted, giữ cả missing/unpaired:

| Năm | source-observation-proof SHA256 |
|---|---|
|2022|7a41f021c86a04345ce2591b90efa72112792ef5479c16ff6d1167f7064dc840|
|2023|61d46d061a870e98a97b696b95d8efab2d28abe190d94f2fc04c1b2255b1909c|
|2024|ccda74a3510986a748d11c1a9b19e2d9b62da1ce61397ed8cb5cf0af218d1c1b|

Reuse frozen producer proof/snapshots và kiểm direct hashes của canonical
files/raw bindings; không tải data mới, sửa generic year guards hoặc mở2025+.
2022–24 exposed/unverified, không clean OOS. Trước outcomes commit protocol,
policy, focused synthetic tests; pin source/data/protocol trong manifest.

Tối đa2candidates×3years×(reference,stress,null)=18books. Mỗi năm load/source
validation một lần, dùng lại giữa policies/costs. Status/events/log ghi year,
candidate/scenario, stage/timers; deadline600giây, CANCEL ở phase boundaries
và replay callbacks; output mới, một writer, giữ failures/completed outputs.
Không tự retry numerical job hoặc sửa rule sau khi nhìn PnL.

Báo số lệnh, winrate sau phí, average win/loss, meanR trên25USD planned risk,
closed-balance DD (không intraday equity DD), loss streak, concentration top5,
known/full net và source/unknown counts. Phân rã executable quote gross,
slippage, commission/funding và mid endpoint diagnostic cho scheduled exits;
không bịa synchronous spread từ side extrema cho SL intrabar.

Đủ ưu tiên review tiếp nếu full paths đã biết, stress tổng ba annualbooks
dương và ít nhất2/3năm stress dương. Đây là effort triage, không statistical
proof, không bác bỏ cả họ nếu fail. Nếu chỉ đẹp ở reference, tập trung vài
trade hoặc có unknown thì ghi mong manh/inconclusive. Không tự promote bằng
winrate/số lệnh hoặc tune thresholds để ép pass. Chỉ survivor mới đáng kiểm
tick/spec/news/prop/time-fit/OOS/forward và owner handover riêng.

EURUSD: chỉ một dossier research/lineage, không mở thêm financial study trong
batch này. Private output `execution-v1/us500-m15-opening-screen-v1/` dưới
campaignbase đã có; logs/source snapshots/result/review giữ để audit.
