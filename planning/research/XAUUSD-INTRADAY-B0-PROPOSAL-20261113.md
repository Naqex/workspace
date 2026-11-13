# XAUUSD Intraday B0 — bản đề xuất, chưa được phép chạy

**PROPOSAL_PENDING_OWNER_APPROVAL.** Campaign ID `A0`, tên hiển thị
`XAUUSD Intraday B0`; khác EURUSD B0 và các chẩn đoán Gold R043 B1/B2 cũ.
Lượt này chỉ kiểm timestamp M1 và viết card, chưa code chiến lược, đếm tín
hiệu, tính markout hoặc chạy backtest vàng mới. Chưa dùng quyền EURUSD B1.

## Vì sao đáng khảo sát, và điều chưa biết

[Audit Development EURUSD](EURUSD-FUNNEL-AUDIT-RESULTS-20261113.md) chỉ ra
phễu theo một vùng London/ngày đang thưa. Hướng A đề xuất **pullback theo
xu hướng tới đường trung bình động**, tạo nhiều thời điểm quan sát trong
phiên. Đây là cơ chế mới cần kiểm, không khẳng định vàng có edge hoặc đủ
60–80 lệnh/năm. Nó vẫn thuộc họ trend/pullback đã nghiên cứu; không xóa
lịch sử thử chỉ vì đổi asset/timeframe.

Kho M1 Bid đã admit có thể dựng H1/M15; census07:00–21:00UTC có 33 ngày thiếu
đoạn>15 phút trong782 weekday windows. Tất cả là cuối khung giờ hoặc trống cả
ngày, không thấy gap nội phiên>15 phút trong CSV. Ngày nghỉ/đóng sớm chưa có
calendar lịch sử độc lập; **không gọi33 ngày là 33lỗi feed**. Chưa admit đầy đủ
observed Ask/tick cho card mới, nên chưa đủ đo executable net/DD/SLTP ordering.

Không mang tỷ lệ phí 6,4% của GoldR043 multiday sang intraday. Đổi exit làm đổi
winners/trades/path; không cộng8.950USDswap cũ thành lợi nhuận mới. Chỉ khi
đã xác nhận flat trước rollover thực tế mới không phát sinh swap theo contract.

## Một baseline để owner duyệt

Mọi tham số dưới đây là lựa chọn thiết kế trước outcome, không phải kết quả
quét/tối ưu. Không chạy grid MA/ATR/giờ/side, không tự thêm A1.

| Thành phần | Luật đề xuất A0 |
|---|---|
| Thị trường / account | XAUUSD, mô phỏng USD50k; FTMO CFD2-Step Standard là đích cần admission. BUY/SELL đối xứng, không chọn Long-only từ R043. |
| Source / clock | Source UTC, tín hiệu từ Bid H1/M15 đã đóng. Warmup canonical từ 01/11/2021, giữ continuous indicators xuyên năm. Chỉ admit M15/H1 đủ phút nguồn; không padding/volume-zero filter. |
| H1 bias | BUY: closedH1Close>SMA20 và SMA20>SMA20 của3completed H1 trước; SELL đối xứng; neutral/missing→abstain. |
| M15 zone | Với mỗi bar, khóa SMA20 và WilderATR14 từ các bar đóng **trước** bar đang xét. Zone=SMA20±0,20ATR. Không dùng SMA/ATR thay đổi trong bar để dời zone. |
| Setup / trigger | Nến M15 trước đóng ngoài zone theo hướng bias; nến hiện tại quay lại chạm zone và đóng vượt biên zone theo hướng bias. Không bắt buộc màu thân nến. Đây là pullback/reclaim, không thêm yêu cầu phá một rangeLondon cố định trước đó. |
| Entry | First admissible observed tick sau nến xác nhận đóng; BUYAsk/SELLBid. Chờ>60s hoặc unknownquote→không fill. Một vị thế tại một thời điểm, max2 fills/ngày UTC; sau exit chờ barclose mới. |
| Natural SL | BUY: low nến setup−0,10ATR đã khóa; SELL: high+0,10ATR. Round ra ngoài grid đúng targetspec. SL không hợp lệ hoặc không đạt cap phí→bỏ, **không nới SL**. |
| TP / quản lý | TP=2×initial price stop-distance; không trailing/BE/partial. Maxholding120 phút từentry; exit theo quote thật đầu tiên sau deadline. |
| Khung giờ | M15 bar mở từ 09:00UTC, quyết định và entry phải trước16:00UTC. Tín hiệu tối đa trong một phiên liên tục, không tối ưu riêng Âu/Mỹ. |
| Flat bắt buộc | Sớm nhất của: entry+120 phút;18:00UTC; datedsessionclose−15 phút; datedrollover−15 phút; restrictednews−5 phút. Đã đến cutoff thì cancel pending; thiếu lịch/quote hoặc chưa xác nhậnflat→unknown, không swap0. **22UTC không phải mốc cố định được chứng minh cho mọi account/ngày.** |
| News | Dùng lịch restrictedUSD đã biết tại thời điểm giao dịch. Không entry±5 phút quanh event, và phải còn ít nhất15 phút tới deadline thoát theo tin. Close5 phút trước; nếu event chưa có known-at calendar→không được gọi funded-compatible. |
| Risk | R0=150 USD=0,30% vốn đầu50k, fixedUSD, không compounding; sizing có native lotfloor/min/max, margin và cost reserve. Không chạy0,40% hoặc tăngrisk để cứu cadence/expectancy. |
| Friction | PlannedstressF/R0≤12%, ưu tiên≤10%; spreadreserve biết tại intent, commission/slip cảvòng. GrossBidAsk đã chứa spread, không trừ thêm. Báo realizedtail và capexceedances. |

Không đòi quota hàng ngày. Nếu count trên Development chưa đạt60 fills/năm
sau mọi filter/data/news/size rules, gác card vì suitability; không tự nới luật.
60–80 lệnh/năm là sàn thiết kế, không chứng nhận độ chính xác thống kê.

## Cost contract đề xuất — phải chốt account trước dispatch

Tài liệu [FTMO25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
công bố metals commission **0,0007% notional/side** từ 29/09/2025. Đây là
published policy tại ngày đó; chưa chứng nhận rate/platform/account cụ thể
hoặc phí lịch sử 2022–2024. Trước chạy phải capture spec/units/commissionbasis
đúng account; nếu khác, sửa/chốt card trước outcome, không âm thầm thay model.

Đề xuất benchmark research theo biểu phí đích đã xác nhận, áp vào history như
**counterfactual current-cost stress**, không gọi là phí thật đã áp năm2022.
Với `C` ounces/lot và volume `q`:

`commission = 0,000007 × C × q × (entry_notional_price + exit_notional_price)`.

| Cost lane | Commission | Spread | Slippage đề xuất |
|---|---|---|---|
| Reference | Cùng rate target đã capture; nếu dùngpublishedproxy thì ghi declared | ObservedBid/Ask; không cóAsk thì N/A |0 USD/oz/side, là modelresearch|
| Stress | Cùng commissionbasis, không đổi sau outcome | Cùng observedquotes, đo realizedspread |0,20 USD/oz/side, là stress khai báo, chưa calibration broker|

Với tham chiếu `C=100oz/lot`, slippage stress cả vòng=40USD/lot. Ví dụ
**giả định để giải thích**, giáentry/exit cùng2.000 USD/oz: commissionroundtrip
2,80 USD/lot; tổngcommission+stress slip42,80 USD/lot **chưa gồm spread**.
Không lấy9 USD/lot củaEURUSD hoặc fixed5USDcommission cũ áp vào vàng.
Contract100 oz/lot, ticksize, lotstep, margin/leverage vẫn phải verify đúng target.
NativeMetalMarket cũ dùng fixedcommission/lot. Rate theo notional đòi hỏi
accounting hai phía và reserve known-at được đối soát bằng fixtures trước
PnL; chưa được coi native adapter A0 đã hỗ trợ chỉ vì có CostModel cũ.

Admission dùng boundcommission tại intent từ mức giá lớn nhất của entry/SL/TP
và reserve đã khóa; không đọc exitprice tương lai. Actualfee theo hai phía
executionnotional; spread/slip/gap có thể vượt reserve nên vẫn phải báo tail.

## Data / qualification gates trước bất kỳ numeric strategy run

1. G0: admit Bid/Ask M1 đủ Development 2022–2023, provenance/timestamp/grid,
   source/target session + known-atnews/rollover; selectedobservedticks đủ
   firstfill, ambiguitySLTP và cutoff. Nativebar envelope không tự thành tickfill.
   Không có dữ liệu cần thiết thì giữ data-blocked, không chạy net-PnL giảAsk.
2. Owner duyệt đúng card/cost/budget. Một A0, không tự chuyển leftoverEURB1
   thành quota thửGold. H1/M15bias/zone/trigger/cost/timing cần fixtures trước.
3. Count-only Development trước economics, giữ mọi reason/zero-months;
   cadence gate không đạt thì dừng. Chưa có quyền chạy bước này ở lượt hiện tại.
4. Nếu coreeconomics qua review, **mới xin scope** historicalvalidation2024
   sau freeze. Gold2024 đã từng dùng trong researchR043, không cleanOOS;
   lượt này chỉ mở timestamps để quality, không dùng giá 2024 sửa card.
5. Giá 2025–2026 tiếp tục đóng hoàn toàn; không có shadow/live/brokerauthority.

Nguồn target bổ sung: [accountspec FAQ](https://ftmo.com/en/faq/what-are-the-account-specifications/),
[session/trading updates12/11/2026](https://ftmo.com/en/blog/trading-updates/trading-update-12-nov-2026/).
Lịch hiện hành có ngày nghỉ/đóng sớm và GMT+2; không backdate nó thành calendar2022–2024.
