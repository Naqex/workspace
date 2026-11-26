# FTMO Free Trial — hồ sơ đo thực thi, chưa là bot được cấp quyền gửi lệnh

**Sẵn sàng làm hồ sơ và chuẩn bị thu thập dữ liệu; chưa sẵn sàng bật bot V16
trên MT5.** Chưa có Champion đủ chứng cứ đường giá. V16 là bản tham chiếu để đo;
V17 là dự phòng Funded trong mô hình, chưa được chứng nhận “Ultra-Safe”.
Mục tiêu đợt đo đầu là biết giá/phí/đồng hồ có khớp giả định không.
Chưa đăng ký tài khoản, kết nối mới hoặc gửi lệnh trong V18.

## 1. Chọn đúng bài thử và hiểu giới hạn

Thông số tham chiếu từ
[snapshot nghiên cứu02/11/2026](PROP-FIRM-FIT-20261102.md) và yêu cầu V18.
**Chưa xác minh lại điều khoản hiện hành ngày16/11/2026:** web tool không trả
nội dung đối soát được, trình duyệt không attach được, HTTP fallback lỗi TLS.
Phải đối chiếu Client Area trước khi dùng kit với tài khoản cụ thể.

| Nội dung | Free Trial 2-Step |
|---|---|
| Thời hạn | 14 ngày |
| Mục tiêu lợi nhuận | 5% |
| Minimum Trading Days | 2 |
| Maximum Daily Loss / Maximum Loss | 5% / 10% static |
| Nền tảng dự kiến | MT5 theo yêu cầu của owner; cần xác nhận trên Client Area |

Nguồn cần đối chiếu: [FTMO Free Trial](https://ftmo.com/en/ftmo-free-trial/).
Kit dùng trial như môi trường mô phỏng để đo. Không suy ra quyền FTMO Account
từ việc đạt target; thời hạn/inactivity/điều kiện đóng trial phải ghi đúng
snapshot của tài khoản đích.

Hồ sơ đích đề xuất: **2-Step / Standard / USD / 50k / MT5**, nếu Client Area
của owner cung cấp tổ hợp đó. Chụp/lưu rule version và specification của
chính tài khoản trước khi đo. Không lấy chương trình1-Step/Instant có trailing
loss khác để so với engine10% static hiện tại.

Monte Carlo V18 vẫn đo bài thi trả phí **+10% rồi +5%, tối thiểu4ngày/vòng**.
Không dùng con số đó làm điều kiện đậu Free Trial. Trial14ngày không đủ để
chứng minh edge nhiều năm; không cố tạo lệnh hoặc tăng risk để đạt target.

## 2. Bản tham chiếu gồm những gì?

Ba sleeve A đã freeze từ V14, giữ V16 daily-flat. Đây là danh mục pha trộn
breakout, momentum và range rejection; không gọi cả ba là trend-following.
Code là nguồn công thức cuối cùng, không thay bằng indicator MT5 có tên giống.

| Sleeve | Quy tắc tạo cơ hội trên nến đã đóng | Natural SL |
|---|---|---|
| EURUSD F5 `tf=H4:n=5:adx=25:buffer=0.1`, DAY/P0 | Biên cao/thấp của5D1 đã biết; H4 quét ra ngoài rồi đóng lại bên trong. BUY: low dưới biên thấp, close trên midpoint nến; SELL đối xứng. ADX14 ≤25. | BUY: low H4 −0,1ATR H4; SELL: high H4 +0,1ATR. Làm tròn giá ra ngoài. |
| XAUUSD F3 `compression=BB:n=60:quantile=0.1:multiple=1`, 48H/P0 | H4 trước đó có độ rộng BB20 thuộc ngưỡng10% của60 độ rộng trước; H4 đóng phá biên high/low20H4 trước, thân nến cùng hướng. | Close H4 ±1ATR H4, theo phía đối diện lệnh. |
| XAUUSD F4 `hour=15:impulse=1:timing=MONTH:multiple=1`, 24H/P1 | H1 đóng15:00UTC, thân ≥1ATR H1; trong2ngày làm việc đầu hoặc2ngày làm việc cuối tháng. Theo hướng thân nến. | Close H1 ±1ATR H4 đã biết tại thời điểm đó. |

Nguồn công thức:
[F1–F4](../../tooling/ai-engines/prop_v10_signals.py),
[F5](../../tooling/ai-engines/prop_v12_signals.py),
[native frames](../../tooling/ai-engines/quant_core/native_hourly_source.py),
[source admission](archive/FINAL-CONVERGENCE-V18-FREEZE-20261116.json).
ATR14 dùng Wilder và giá trị đã biết trước nến quyết định; ADX và việc align
D1/H4/H1 dùng đúng implementation đã pin. Cần đủ warmup BB20+60, ATR/ADX và5D1;
thiếu warmup không được coi là “không có tín hiệu”.

Mỗi recipe chỉ lấy cơ hội đầu tiên mỗi ngàyUTC theo generator, trước phí.
Entry là quote thực thi đầu tiên tại/sau thời điểm quyết định, trong cửa sổ
60giây đã đăng ký. BUY dùng Ask, SELL dùng Bid. Giữ admission `Friction/SL≤15%`
và lot grid; không nới SL để vượt cổng. **Không thêm cửa vào07:00** cho ba core
sleeves: cửa đó chỉ dùng cho scan additions V17 đã bị loại hết.

## 3. Thoát lệnh và đồng hồ

- Giữ SL tự nhiên. P0 không có TP/trailing mới.
- P1: sau khi một M1 hoàn tất có markout net baseline ≥1,5R, mới kích hoạt
  stop bảo vệ mức net≥0,15R từ phút kế tiếp; làm tròn theo đúng
  [first-passage owner](../../tooling/ai-engines/prop_v14_paths.py).
  Đây không phải phép kiểm tra ngay tại high/low chưa biết của nến đang chạy.
- Hạn thoát V16 là sớm nhất của horizon gốc, **20:30UTC cùng ngày** và holiday
  guard đã đăng ký. Tên48H/24H không cho phép giữ qua đêm ở V16.
- Không tự lấy quote cuối trước outage để đóng hồi tố. Yêu cầu đóng được biết
  trước; fill dùng quote hợp lệ đầu tiên theo contract. Thiếu quote ghi unknown.
- Reset lỗ ngày dùng **00:00 Europe/Prague**, có DST; không dùng00:00UTC hay
  giờ Windows. 20:30UTC tương ứng03:30 Việt Nam ngày kế tiếp.

Lịch nghiên cứu là giả định được version hóa, chưa thay thế lịch broker hiện
hành. Trước mỗi phiên cần snapshot trading sessions/holiday updates và quy tắc
đóng sớm, kể cả ngày thị trường nghỉ. Nếu khác lịch nghiên cứu, ghi divergence,
dừng việc so như cùng một strategy; không sửa lịch cũ sau outcome.

[FAQ market breaks](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/)
và [FAQ news](https://ftmo.com/en/faq/can-i-trade-news/) là nguồn cần kiểm lại.
Engine kế thừa quy tắc nghỉ>2giờ và hồ sơ news±2phút với ngoại lệ theo
program/phase; đây chưa là xác nhận điều khoản hiện hành của tài khoản đích.
Daily-flat không tự chứng minh news-safe.
V18 chưa tái dựng đầy đủ lịch news lịch sử nên không chứng nhận Funded Standard.

## 4. Lot và ngân sách chung

Giữ V16/V15 factor1,5+cushion, không biến thành risk cố định theo % equity.
Vốn danh nghĩa50k là đơn vị mô phỏng, không phải số tiền owner đã có.

| Giai đoạn | Risk giá tới SL trước cushion/throttle |
|---|---:|
| Phase1 | 300 USD |
| Phase2 | 262,50 USD |
| Funded | 187,50 USD |

Phase1: cushion được arm khi balance≥51.500, disarm khi balance≤50.000;
khi arm và equity>50.000, cộng `min((balance−50.000)/5,250)` USD.
Sau đó equity≤46.500 cap75USD, equity≤47.500 cap150USD.
Áp dụng exact milli rounding và quantity owner, không nhẩm từ lot ví dụ.

Với giá đã đưa về grid nguyên:

```text
q = floor(risk_milli_USD / (VALUE × abs(entry_units − stop_units)))
XAUUSD: VALUE=1; q là oz; lots=q/100
EURUSD: VALUE=10; q là bước 0,01lot; lots=q/100
```

Ví dụ XAUUSD entry2.000, SL1.990, risk300USD: q30oz=0,30lot.
EURUSD entry1,10000, SL1,09800, risk300USD: q150=1,50lot.
Phí chưa nằm trong risk giá này; lỗ thực có thể lớn hơn khi cộng phí/gap.

Trước entry: kiểm cùng một tài khoản cho mọi sleeve; tổng initial-stop risk
≤1.000USD, projected stop equity sau phí/funding>45.800USD, shared daily/static
floor hợp lệ. Realized loss ngày đạt−1.000USD thì ngừng entry đến reset.
Không net BUY/SELL để “giải phóng” risk và không bóp lot tùy ý để lách cap.
Nhãn max/min lot nghiên cứu không phải specification broker: phải lấy
volume_min/step/max, contract size, tick size/value và stop/freeze levels
của chính symbol. Thiếu hoặc khác contract thì không có lệnh đủ chuẩn.

V17 backup còn tier EUR1,0/Gold0,6 và daily reservation1.200USD; không trộn
guard của V17 vào V16 để tự tạo một biến thể mới.

Funded harvester kế thừa: freeze theo balance/cửa sổ14ngày, đóng ở quote kế tiếp
khi có yêu cầu; payout chỉ khi flat, đủ thời gian và profit proxy≥20USD.
Engine debit100% lợi nhuận, mô phỏng share80%; đây là proxy nghiên cứu,
không phải lời hứa reward hay điều khoản hợp đồng hiện tại.

## 5. Phí nào đã biết, phí nào cần đo?

| Thành phần | Giả định nghiên cứu | Cần thu trên tài khoản đích |
|---|---|---|
| Spread | Bid/Ask proxy nguồn historical | Toàn bộ Bid/Ask có timestamp, cả lúc không vào lệnh |
| Gold commission | 0,0007% notional mỗi side, làm tròn cent | Deal-level commission/fee và specification |
| EUR commission | 3,50USD/lot mỗi side | Deal-level commission, currency conversion |
| Slippage stress | Gold0,20USD/oz/side; EUR1USD/lot/side | Signed requested-vs-filled price từng side |
| Swap | V16 daily-flat bằng0 trong mô hình | swap_long/short/mode/triple-day; charge thực nếu có |
| Mức stress V18 | Spread+slippage1,00/1,25/1,50; commission giữ nguyên | Không chọn mức thấp hơn chỉ vì muốn PnL dương |

V18 surcharge giữ nguyên đường SL/P1 và thêm chi phí mỗi side; chưa tái tạo
mọi thay đổi first-passage khi spread giãn. [Symbols](https://ftmo.com/en/symbols/)
là nguồn cần đối chiếu; chưa lấy được specification gắn riêng tài khoản.
Không coi các proxy trên là phí FTMO đã đo.

Với BUY, adverse slippage=`fill−request`; SELL=`request−fill`, tính bằng
USD/oz hoặc pips rồi quy đổi USD theo volume/contract. Giá request là quote
executable tại thời điểm gửi, không lấy close nến quyết định làm giá gửi.
Tách spread, commission, slippage, latency và swap; không trừ spread hai lần.
Market/stop/time-close có adverse slip; limit TP cần kiểm loại lệnh thực.

## 6. Ghi nhận và đối soát

Lưu evidence trong thư mục private theo account/session; không commit credential,
số đăng nhập đầy đủ, bearer token hoặc mật khẩu. Giữ bản gốc, checksum và clock
mapping; account trong báo cáo dùng hash/alias.

| Record | Trường tối thiểu |
|---|---|
| Session/spec | Program/phase, account hash, server, currency, capital, account/symbol spec, UTC/server clock mapping, news/session snapshot, source/code hashes |
| Quote | UTC milliseconds, server time gốc, Bid/Ask, flags, source binding, received time, gap/duplicate status |
| Paper intent | Stable signal ID, sleeve, decision time, closed-bar/warmup hashes, side, SL/P1/deadline, expected request price, risk/lot/reserve decision, reason skipped |
| Broker request/fill nếu được giao riêng | Intent ID, order/deal/position IDs, type, send/ack/fill times, request/fill prices, volume, partial fills, retcode, commission/fee/swap |
| Account mark | Balance/equity/floating, Prague-day anchor, open/pending/unknown orders, reserve, first breach/halt reason |
| Reconciliation | One-to-one/missing/duplicate/unexpected match, price/lot/time/cost deltas, evidence locators; không xóa lệnh xấu |

Có thể reuse recorder
[`mt5_observed_capture.py`](../../projects/trader/foundation_v2/scripts/mt5_observed_capture.py)
và history reconciliation
[`shadow_reconcile.py`](../../tooling/ai-engines/shadow_reconcile.py).
Recorder có manifest/binding/clock/secret private và `execution_capability=false`.
Không truyền placeholder account vào một command như đã kết nối được.
`mt5_shadow_step.py` hiện là fixed-H4 shadow khác; nó **chưa là adapter ba sleeve V16**.

Đối soát theo ba lớp: cùng input phải sinh cùng signal/SL/lot;
paper dùng quote broker để đo feed/cost khác historical;
fills thực trong demo cần join đúng intent và giữ mọi reject/partial/latency.
Không ép entry broker lệch giờ thành một “trade khớp” hoặc chọn lại bộ tín hiệu
sau khi xem lệnh nào thắng.

Kiểm tra offline có sẵn, không kết nối broker:

```powershell
$env:PYTHONPATH='projects/trader/foundation_v2;tooling/ai-engines;tooling/ai-engines/tests;tooling'
& '<CODEX_BUNDLED_PYTHON>' -m unittest test_prop_v18 -v
```

## 7. Bước hợp lý ngay sáng nay

**Có thể bắt đầu thu quote/spec sau khi owner tự chuẩn bị đúng Free Trial và
binding được xác minh. Chưa bật tự động gửi lệnh chiến lược.** Bộ kit không
phải EA; chưa có parity V16 trên broker candles, MT5 execution adapter, news
guard theo phase và owner handover. Thu quote đủ nhiều phiên, đối chiếu
spread/commission/clock trước; fill/slippage chỉ đo được khi có quyền thực thi
riêng cùng log request/fill. Không dùng quote capture để tuyên bố đã đo slippage.

Không có yêu cầu mua Challenge trong V18. Quyết định tiếp theo dựa trên báo cáo
[V18](archive/FINAL-CONVERGENCE-V18-RESULTS-20261116.md), không dựa vào việc trial có
miễn phí hay một chuỗi lệnh ngắn tình cờ có lời.
