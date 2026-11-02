# Bài nghiên cứu Forex/prop đầu tiên

Đăng ký: **02/11/2026**, trước khi xem kết quả giá Forex của bài này.
Owner đã chọn Forex major/MT5 và FTMO 2-Step Swing làm chuẩn mô phỏng.
Các thông số bên dưới là **giả định offline do agent chọn, dễ thay đổi**;
chưa là quyết định mua tài khoản, risk budget tiền thật hoặc chiến lược đạt.
Scope thuộc [AI plan](../trader/AI-RESEARCH-UI-PROTOTYPE-20261031.md);
kết quả thực thi thuộc [receipt hiện có](../checkpoints/ai-integrations-20261031/RECEIPT.md).

## 1. Phạm vi thử nhỏ trước

| Nội dung | Cấu hình nghiên cứu tạm |
|---|---|
| Sản phẩm | EURUSD CFD, long/short, một vị thế tối đa |
| Tín hiệu | H4, nến chuẩn UTC mở lúc 00/04/08/12/16/20 giờ; chỉ dùng nến đã đóng |
| Tài khoản mô phỏng | 10.000 USD, không phải vốn sở hữu hay khoản tiền sẽ nộp |
| Rủi ro dự kiến mỗi lệnh | Tối đa 25 USD = 0,25% vốn ban đầu, gồm chi phí dự kiến |
| Ngưỡng dừng nội bộ | Lỗ equity trong ngày 100 USD; lỗ tổng từ vốn đầu 500 USD |
| Khi chạm ngưỡng nội bộ | Không mở thêm; mô phỏng đóng vị thế ở quote tiếp theo. Gap có thể vượt ngưỡng |
| Margin | Mô phỏng theo đặc tả tài khoản/symbol; base leverage Swing 1:30 không là mục tiêu dùng hết |

Ngưỡng nội bộ chặt hơn giới hạn hãng để dành khoảng đệm, chưa được tối ưu bằng
kết quả. Đã có risk guard Python offline với quote tổng hợp; chưa nối strategy
runner, API/UI hoặc runtime sản phẩm. Phạm vi và giới hạn ở mục 6.
Không martingale, bình quân lỗ, tăng size sau thua hoặc ép giao dịch đủ số ngày.
Nếu lot tối thiểu vượt mức rủi ro, bỏ lệnh. Không lấy 15 triệu của owner làm
ngân sách challenge/retry; chưa rõ quỹ sinh hoạt/dự phòng.

## 2. Một giả thuyết cố định để kiểm đường chạy

Candidate `eurusd-h4-donchian20-10-atr14-r025-v1`:

- Long nếu close H4 vừa hoàn tất vượt high của **20 nến trước đó**; short nếu
  thấp hơn low của 20 nến trước đó. Không đưa chính nến tín hiệu vào kênh.
- Thoát long khi close dưới low 10 nến trước; thoát short khi close trên high
  10 nến trước. Không đảo chiều trong cùng một sự kiện khớp lệnh.
- Stop ban đầu cách giá khớp 2 × ATR14 Wilder tính từ dữ liệu đã biết khi ra
  quyết định; giữ stop, không trailing. Size theo stop và ngân sách 25 USD,
  làm tròn xuống theo bước lot, kiểm margin và chi phí trước khi chấp nhận.
- Khớp ở quote có thể giao dịch **sau** lúc đóng nến; buy tại ask, sell tại bid.
  Không khớp ngược về close đã dùng để sinh tín hiệu. Stop/gap theo quote khả
  dụng, không mặc định luôn khớp đúng giá stop. News/weekend cần stress gap/spread.
- Không tìm tham số trong lượt đầu. AI chưa đề xuất hay sinh candidate này.
  Benchmark ban đầu là cash và chính quy tắc cố định này làm incumbent cho các
  đề xuất AI sau, trên cùng data/timing/cost/risk; không so Forex leverage với
  return crypto spot để kết luận engine nào tốt hơn.

Quy tắc này chỉ là công cụ kiểm end-to-end, chưa có bằng chứng edge hoặc lợi
nhuận. Không chuyển code close-to-close/sqrt(365) của Quant crypto thành CFD.
Trader giữ FX execution/accounting và Prop domain; Quant chỉ reuse metric khi
đúng đơn vị, calendar và ngữ nghĩa.

## 3. Dữ liệu và cách tránh kết luận sai

- **Nguồn giá ưu tiên: Dukascopy qua QDM CLI sẵn có**, theo
  [QDM workflow](../../projects/trader/docs/quantdatamanager.md). Đã export mẫu
  M1 và tick Bid/Ask ngày03/01/2022 từ cache; tick có hash/kiểm format ở receipt
  local. Chưa có manifest dataset execution hoặc đặc tả symbol/cost đủ cho runner.
  Không chạy backtest khi các trường này thiếu; không giả phí/swap bằng 0.
  Cần nguồn hợp lệ, timestamp/timezone, bid/ask, contract size, lot/tick steps,
  commission, swap/rollover và margin. Không tự kết nối tài khoản MT5 để lấy.
- Phân vùng dự kiến: 2018–2022 development, 2023–2024 validation; từ 2025 đến
  cutoff hợp lệ cuối cùng giữ riêng. Manifest phải xác nhận phạm vi khả dụng và
  dữ liệu từng được xem. Không gọi phần đã consumed là holdout mới. Thiếu dữ
  liệu thì sửa contract và ghi lý do **trước** khi đọc outcome, không dời split
  sau khi thấy kết quả. Holdout chỉ mở theo protocol/approval hiện hành.
- H4 là nhịp quyết định, không phải độ phân giải kiểm equity. Cần tick bid/ask
  hoặc bound bảo thủ đủ chứng minh không breach trong khoảng; M1 OHLC tự nó
  vẫn có thể mơ hồ thứ tự high/low, gap và stop. Thiếu coverage → approximate/
  insufficient, không cấp pass. Đồng hồ CE(S)T dùng `Europe/Prague`, có DST;
  không dùng giờ server broker hay UTC+1 cố định thay thế.
- Lưu causal timing, spread/commission/swap/slippage, intraday equity, entry
  days, margin và mọi lần breach. Stress chi phí và gap; không loại cửa sổ lỗ.
  Xét cả return, drawdown, số giao dịch, độ ổn định và phí vận hành. Ngưỡng
  promotion lợi nhuận/độ tin cậy phải đăng ký trước lượt đánh giá, hiện chưa có.

## 4. Luật hãng được đối chiếu và giới hạn phạm vi

Nguồn chính thức đọc ngày02/11/2026:
[Trading Objectives, phần 2-Step](https://ftmo.com/en/trading-objectives/) và
[Swing account](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/).
Ngày này là ngày quan sát nguồn, không khẳng định ngày hãng thay điều khoản.

Với 10.000 USD mô phỏng: target phase1 1.000 USD, phase2 500 USD, phải đóng vị
thế; daily allowance 500 USD; floor ngày = balance lúc 00:00 Prague −500 USD;
overall floor static 9.000 USD. So equity gồm floating P/L và chi phí; **dưới**
floor mới breach. Mỗi phase cần 4 ngày có mở vị thế, không đếm thêm ngày chỉ
giữ lệnh. Swing cho giữ qua đêm/cuối tuần và giao dịch tin, vẫn chịu forbidden practices.

Fixture có source/version và hai phase ở
[`ftmo-swing-offline.json`](../../projects/trader/foundation_v2/tests/fixtures/ftmo-swing-offline.json).
Nó kiểm tiền/quy tắc bằng sự kiện tổng hợp, **không phải preset đầy đủ trên UI**
hoặc chứng nhận FTMO. `reset_order=fees_then_reset` là giả định fixture;
thứ tự commission/swap đúng boundary cần ledger/spec nguồn xác nhận. Cả hai
thứ tự generic đều được regression-test, không suy thứ tự hãng từ test pass.

Chưa mô phỏng đủ margin/liquidation, chất lượng khớp giá, EA/forbidden-practice
compliance, inactivity, payout, KYC, thuế, hợp đồng hoặc phí challenge/retry.
Không dùng snapshot/model báo cáo để tự xác nhận pass hay xác suất nhận payout.

## 5. Điểm dừng và bước tiếp

Lát dữ liệu tiếp nối đăng ký **03/01/2022, 12:00–13:00 UTC**, EURUSD, thuộc
development để kiểm ingest/accounting, chưa đủ warmup H4/candidate. Sau owner
nhắc QDM, dùng integration hiện có thay đường tải trực tiếp mới. Export cache
QDM giới hạn cả ngày03/01/2022 (CLI nhận ngày), rồi kiểm riêng giờ đã đăng ký.
Mẫu M1 ban đầu là `provider_default`; sau tải cache đã export65.215 tick
Bid/Ask Dukascopy ngày03/01/2022, có3.829 tick trong giờ đăng ký. Header,
millisecond, UTC, thứ tự và giá đã kiểm;15 phút không có quote được giữ nguyên.
Hash/provenance/coverage ở receipt; probe BUY/SELL accounting đã đạt theo
scenario mục7, chưa chạy strategy thật hoặc xác minh khớp lệnh broker.
Raw data chỉ lưu local cho nghiên cứu, chưa duyệt quyền redistribution.
Không tiếp cận giá validation/holdout hoặc biến export thành strategy return.

**Bổ sung trước tải tick, 02/11:** owner cho phép tải toàn bộ lịch sử EURUSD
vào cache QDM để reuse lâu dài. Quyền này chỉ mở phạm vi thu thập/lưu cache;
chỉ export và kiểm giá ngày03/01/2022, tập trung giờ12:00–13:00 UTC đã đăng ký.
Không export/đọc outcome validation2023–2024 hoặc holdout từ2025. Dùng CLI
hiện có, symbol tick riêng; không sửa symbol M1, không đổi activation hoặc DB.
Job dài giữ PID/log/checkpoint; không khởi chạy instance QDM thứ hai.

Chi phí tham chiếu được xác minh thêm từ
[FTMO Trading Update25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/):
từ29/09/2025, commission Forex được công bố là2,50 USD/lot/mỗi chiều,
tức5 USD/lot cho mở và đóng. Với0,01lot:0,025 USD/chiều,0,05 USD/hai chiều,
trước quy tắc làm tròn của tài khoản. Đây là mức công bố có ngày hiệu lực,
chưa xác nhận cấu hình tài khoản cụ thể hoặc phí năm2022. `CostModel` hiện nhận
`commission_per_side_account` là số tiền cho cả lệnh, không phải rate mỗi lot:
khi nối runner phải nhân2,50 với quantity trước; không truyền2,50 cho lệnh0,01lot.
Nếu áp vào giá2022
phải gắn nhãn scenario theo điều kiện phí tham chiếu, không tái dựng phí lịch sử.
Swap, lot/tick limits, margin và execution vẫn thiếu xác minh đầy đủ.
[Update29/10/2026](https://ftmo.com/en/blog/trading-updates/trading-update-29-oct-2026/)
nhắc swap thay đổi và dùng midnight server, còn daily loss theo Prague;
không thay hai đồng hồ bằng cùng một reset hoặc mặc định swap=0.

Lát này hoàn thành khi contract được lưu, Prop domain hỗ trợ balance anchor
riêng và focused checks đạt. Receipt ghi kết quả và source revision.
Tiếp theo: chọn manifest Forex/cost hợp lệ và nối một lượt replay/accounting
offline của candidate cố định. Chưa dispatch workflow crypto cũ cho Forex.
Sau offline có bằng chứng mới xét free trial; mua challenge và mọi quyền
broker/demo/live vẫn cần phạm vi và quyết định riêng của owner.

## 6. Risk guard offline — source candidate 02/11/2026

Module: `projects/trader/foundation_v2/trading_workspace_v2/forex_pilot_risk.py`.
Reuse tick execution/accounting hiện có, không thêm engine khớp lệnh riêng.
Chỉ hỗ trợ EURUSD, tài khoản USD; snapshot pin giới hạn 25/100/500 USD.

- `initialize_forex_pilot` đăng ký thời điểm bắt đầu và daily balance anchor.
  `queue_forex_pilot_order` yêu cầu stop; tại quote khớp dự kiến, kiểm loss tới
  stop gồm chi phí khai báo và ngân sách ngày/tổng còn lại trước khi mở lệnh.
- `advance_forex_pilot`: quote → mark equity trước/sau xử lý → chốt cờ dừng
  ngày/tổng → đóng ở quote kế tiếp nếu còn vị thế. Quote cùng millisecond nhưng
  sequence lớn hơn vẫn là quote tiếp theo. SL/TP có thể đóng ngay ở quote chạm
  ngưỡng; không đóng lần thứ hai. Giá gap có thể khiến loss vượt 25 USD hoặc
  vượt ngưỡng dừng; 25 USD là rủi ro dự kiến tại stop, không là bảo đảm khớp giá.
- Daily anchor dùng balance được mang sang trước hành động của quote đầu ngày
  Prague; không dựng quote nửa đêm. Cờ dừng ngày reset theo `Europe/Prague`
  (DST); cờ dừng tổng giữ nguyên. Lệnh đóng chờ không mất khi đổi ngày/restart.
- Snapshot JSON giữ execution, last quote/sequence, giới hạn, stop evidence và
  risk rejection journal. Một cửa sổ quote lỗi không công bố state nửa chừng.
  Risk rejection nằm ở journal pilot, không giả thành margin rejection.

Đây là kiểm soát trên **quote được cung cấp**; không chứng minh không breach
giữa các tick thiếu. Giữ `intrabar_equity_coverage=insufficient` của core khi có
exposure; chưa cấp Prop pass. Equity là net liquidation value của core, gồm
round-trip costs và financing tổng đã khai báo; chưa thêm timed swap/cash ledger,
fee rounding hoặc đặc tả broker đã xác minh. Stop nội bộ dùng equity <= floor;
luật breach FTMO riêng vẫn dùng equity < floor. Risk snapshot này chưa là API
contract/preset native, chưa chạy với chiến lược hay đưa vào runtime.

Kiểm chứng source: 13 ca pilot synthetic, 22 ca tick execution, 20 ca Prop
connection và 10 ca immediate execution đạt. Ca stress đóng chậm dùng vị thế
carried cố tình quá lớn để kiểm guard; normal admission sẽ từ chối stop rộng
đó. Kết quả/commands/source revision ở receipt AI; không suy ra hiệu quả kiếm tiền.

## 7. Probe accounting đăng ký trước outcome — 02/11

Chỉ dùng tick ngày03/01/2022,12:00–13:00 UTC. Hai account mô phỏng độc lập,
mỗi account10.000 USD, một BUY hoặc SELL0,01lot; không chọn chiều theo outcome.
Queue trước12:00, khớp quote đầu từ12:00; SL BUY = bid cuối trước12:00 −0,0010,
SL SELL = ask cuối trước12:00 +0,0010. Không TP; nếu chưa chạm stop thì tất toán
giá trị tại quote cuối trước13:00 bằng helper close hiện có. Đây là valuation
cuối kỳ, chưa bảo đảm có thể khớp lệnh đóng thực tế ở quote đã qua. Đây là probe,
không entry/exit của candidate H4. Nếu thiếu phút, fail thay vì bù quote.

Scenario tham chiếu công bố, không tái dựng account FTMO năm2022:

| Trường | Giá trị và mức xác minh |
|---|---|
| Contract/đơn vị |100.000 EUR/lot; reference từ bảng [Symbols](https://ftmo.com/en/symbols/) được search index trả về; chưa xác nhận terminal mục tiêu |
| Leverage |1:30 theo [Swing FAQ](https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/); core dùng fixed research margin, chưa tiered/stop-out |
| Commission |2,50 USD/lot/chiều từ [update25/09/2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/), áp scenario cho giá2022;0,01lot →0,025 USD/chiều |
| Tick/pip |0,00001 quan sát từ CSV; pip0,0001 là quy ước probe, chưa verified broker tick-value |
| Lot min/step |0,01/0,01 là giả định khai báo, chưa account-specific verified |
| Spread |Nhúng trong Bid/Ask, không cộng thêm spread cố định |
| Slippage |Baseline0; stress0,00002/chiều (giá), cùng quote/entry/exit; đây là sensitivity giả định |
| Rounding |ROUND_HALF_UP2 số lẻ trên tổng tiền; chưa xác nhận rounding mỗi chiều của broker |
| Financing |0 cho probe intraday này vì bắt buộc flat trước13:00 UTC, không có rollover; không phải swap rate bằng0 |

[Update29/10/2026](https://ftmo.com/en/blog/trading-updates/trading-update-29-oct-2026/)
nhắc swap thay đổi và phải kiểm contract; chưa pin swap points/triple-day để
chạy strategy qua đêm. Public symbols dynamic không trả bảng qua page extractor;
không dùng giá trị swap trong search cache làm historical schedule. Probe phải
ghi assumptions và `broker_spec_verified=false`, `strategy_pass=false`.

Tiêu chí kỹ thuật: hash/source order/day bounds đúng, BUY ask→bid và SELL
bid→ask, entry causal, closed-position/account checkpoint khôi phục được,
Decimal oracle độc lập khớp gross/commission/slippage/net/balance. Chạy baseline
và stress cho cả hai chiều, không tìm tham số hoặc chọn lượt có lãi. Manifest
và raw results lưu local; receipt AI giữ tổng kết. Gate thiếu broker specs,
timed financing và dữ liệu H4 vẫn giữ sau khi probe đạt.
