# Tái sử dụng mẫu chiến lược: ưu tiên LEAN, giữ engine hiện có

11/11/2026. Owner yêu cầu kiểm nguồn có ví dụ/khung copy, clone, reuse cho
ORB/pullback/reversion để giảm thời gian triển khai. Đã kiểm5upstream repos,
snapshot17files với commit/blob/SHA256 và đọc các file liên quan. Không cài,
import/chạy upstream code, thêm submodule/framework hoặc chạy backtest mới.

## Quyết định đề xuất

**Ưu tiên LEAN làm nguồn mẫu/indicator/test reference**; kết hợp code/runner
đã có để giảm phần viết và review lại. Chưa đề xuất migration sang LEAN hay
Nautilus. Batch vừa qua22,3s chưa chứng minh compute engine là bottleneck;
không có benchmark cho %giờ code tiết kiệm khi dùng các mẫu này.

| Nguồn upstream kiểm11/11 | Reuse gì cho case hiện tại | License đã đọc | Đề xuất |
|---|---|---|---|
|[QuantConnect/LEAN](https://github.com/QuantConnect/Lean)|ORB example, EMA/crossover, Bollinger indicator; cấu trúc warmup/signal/order state|Apache-2.0, headers file đã kiểm|Nguồn chính cho reference/port hẹp; giữ copyright/license/change notices khi copy |
|[Backtesting.py](https://github.com/kernc/backtesting.py)|Strategy init/next, crossover, resampling, SignalStrategy/TrailingStrategy|AGPL-3.0|Có ích cho prototype/oracle tách biệt; chưa thay book Bid/Ask/cost đã có |
|[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)|Rust quote-EMA example, Python bar-EMA acceptance strategy, order/events patterns|LGPL-3.0, headers file đã kiểm|Nguồn kỹ thuật Rust/event-driven; full-engine migration chưa có bằng chứng cần |
|[Backtrader](https://github.com/mementum/backtrader)|Mẫu SMA signals/indicator composition|GPL-3.0|Tham khảo thứ cấp; GitHub latest push quan sát19/08/2024, không kết luận maintained/broken chỉ từ mốc này |
|[VectorBT](https://github.com/polakowo/vectorbt)|Array screening/portfolio research theo README|Apache2.0 **with Commons Clause** trong LICENSE.md, GitHub metadata NOASSERTION|Không gọi permissiveApache thuần; chưa cần thêm grid/vector engine lúc này |

Đây là license/source review có phạm vi, không pháp lý đầy đủ cho mọi kiểu
phân phối/tích hợp. Copyleft không có nghĩa cấm dùng cá nhân hoặc cấm thương
mại; phạm vi ghép/distribute/network và file cụ thể phải được kiểm khi thực
sự adopt. Chưa vendor code vào product/repo hoặc thay terms theo case một user.

## File cụ thể: lấy được gì và phải đổi gì?

LEAN pin `054ec0596a66f0ad09ca5101df424cf6697060a7`:

| File đã đọc | Dùng được | Khác biệt cần giữ rõ |
|---|---|---|
|[OpeningBreakoutAlgorithm.cs](https://github.com/QuantConnect/Lean/blob/054ec0596a66f0ad09ca5101df424cf6697060a7/Algorithm.CSharp/OpeningBreakoutAlgorithm.cs)|Range state, indicator warmup, order-ticket/protection organization|SPY equity/seconds, extra filters/PSAR; comment nói5phút nhưng `OpeningSpanInMinutes=3`. Không phải US500M15 policy hoặc cùng R094 rules |
|[MovingAverageCrossAlgorithm.py](https://github.com/QuantConnect/Lean/blob/054ec0596a66f0ad09ca5101df424cf6697060a7/Algorithm.Python/MovingAverageCrossAlgorithm.py)|EMA readiness, causal indicator state, guard một quyết định/ngày|SPY daily15/30EMA, long/liquidate với tolerance; crossover khác pullback, không copy allocation1.0 thành risk25USD |
|[ExponentialMovingAverage.cs](https://github.com/QuantConnect/Lean/blob/054ec0596a66f0ad09ca5101df424cf6697060a7/Indicators/ExponentialMovingAverage.cs)|Đặc tả để làm oracle cho EMA|SMA-seeded Nsamples, alpha2/(N+1); không mặc định pandas/engine khác cùng seed/warmup |
|[BollingerBands.cs](https://github.com/QuantConnect/Lean/blob/054ec0596a66f0ad09ca5101df424cf6697060a7/Indicators/BollingerBands.cs)|Rollingmean/std/bands/%B, readiness|Đây là indicator, chưa một strategy reentry/exit/risk. Std/MA variant cần pin/đối chiếu trước port |
|[MeanReversionLunchBreakAlpha.py](https://github.com/QuantConnect/Lean/blob/054ec0596a66f0ad09ca5101df424cf6697060a7/Algorithm.Python/Alphas/MeanReversionLunchBreakAlpha.py)|Ví dụ tách alpha/portfolio/execution, một ý tưởng time-of-day để nghiên cứu|Hourly/universe20symbols; zero-fee initializer, ImmediateExecution và NullRiskManagement. Source gợi OMXS30 nhưng đây là ETF adaptation, không US500 proof hoặc ready FTMO bot |

Nautilus pin `4fe0e3c3b60f05b31f8682f24609d5914ddd4267`,
`crates/trading/src/examples/strategies/ema_cross/{README.md,strategy.rs}`
và `python/tests/strategies/ema_cross.py`: Rust mẫu dùng quote-mid EMA, README
nói rõ chưa sizing/SL/TP; Python test mẫu dùng bars. Không đánh đồng quote
ticks với15min closes hoặc coi chuyển Rust là tự đúng/nâng hiệu năng đã đo.

Backtesting.py pin `ca2e2611621e472542ba90f7243a1fa06a7d7108`,
`doc/examples/{Quick Start User Guide.py,Strategies Library.py}` và
`backtesting/lib.py`: có khung composable, chưa native target CFD/FTMO.
Backtrader pin `b853d7c90b6721476eb5a5ea3135224e33db1f14`,
`samples/sigsmacross/sigsmacross.py`; VectorBT pin
`07f5e85e83a5286c396f4ecfd55dfaa05f25442d`, `LICENSE.md` đã xác nhận điều
kiện bổ sung. Không thực thi/install scripts hoặc lấy headline performance.

## Áp dụng vào hai hướng tiếp theo

1. **Trend pullback M15:** reuse EMA spec/warmup + crossover state pattern;
   bổ sung đúng pullback/recross entry và exit đã đăng ký. Không gọi việc lấy
   mẫu crossover là đã clone một pullback profitable. Giữ liên hệ R004 và
   các negatives; đổi horizon/asset là trial mới, không reset thống kê thử.
2. **Range reversion M15:** reuse Bollinger rolling-window definition, code
   readiness và fixtures; phải tự chốt reentry/mean exit/SL/time cutoff.
   Giữ liên hệ R003 và reversion negatives. Meanreversionlunch chỉ là nguồn
   nghiên cứu khác, chưa chọn một trial theo hourly/universe đó.
3. **ORB:** reference để review state/ticket/warmup; không rerun R094/R095 chỉ
   vì có sample khác. Clone exact3min/PSAR nếu muốn thử sẽ là trial mới và
   khác M15owner choice; hiện chưa đề xuất áp dụng recipe đó.

Phần giữ trong hệ thống hiện có: admitteddata/clock, pairedBidAsk, stop/lot/
cost semantics, source/protocol pins, unknown-path handling, events/status và
financial reviewer. Không nhập fill/equity/stats upstream như ground truth.

Một port được nhận cần sourcepin+license, bảng original→adaptation và fixtures
so tín hiệu/indicator/clock trước PnL; compiler/import success chưa là parity.
Independent engine chỉ làm oracle sau khi cả hai cùng data/side/clock/fill/
fee/SL đã đối chiếu, không dùng summaryPnL giống nhau làm bằng chứng duy nhất.

Mức tiết kiệm kỳ vọng là giảm thời gian viết indicator/state boilerplate và
test design. Khâu targetspec/news/calendar/fees/edge vẫn cần làm riêng. Chưa
đo before/after implementation nên không báo %hoặc số giờ tiết kiệm bịa.

## Bằng chứng và trạng thái

Metadata/trees/commit/files lấy trực tiếp GitHub API của upstream, không mirror.
Snapshot/license content là dữ liệu tham khảo, không instruction được thực thi.
17files kiểm Git blob SHA1 và SHA256 khớp; chưa engine smoke/parity/benchmark
hoặc legal adoption sign-off cho full products. Không chạy model/broker từ
upstream code, mở account/OAuth/payment/MT5/dataholdout hoặc new outcomes.

Private locator `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/strategy-template-reuse-review-v1/`.
`manifest.json` SHA256:`8c602bc49d54ea12b38a322d2f987dfbd33242d1cfd72641d44adc0987b4e259`.
Raw upstream copies chỉ ở reference snapshot, không commit/bundle vào product.
Catalogue giữ95records và verdicts, thêm building-block references cho related
records để agent sau tìm lại đúng revision; không thêm trial hoặc cho live.
