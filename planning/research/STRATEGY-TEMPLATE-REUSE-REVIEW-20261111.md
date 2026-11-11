# Engine chiến lược: source library và adoption full framework

**Cập nhật theo owner:** yêu cầu dùng full framework cả năm engine thay đề
xuất chỉ reference bên dưới; xem [trạng thái adoption](#owner-chon-dung-framework-day-du-ca-nam-engine).
Các đoạn “chưa cài/chạy” bên dưới giữ trạng thái tại lần download, không mô tả
trạng thái mới. Chưa có US500 migration/parity hoặc challenge candidate mới.

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

## Đã lấy đủ năm kho source về local theo yêu cầu owner

Owner yêu cầu “lấy hết về” sau khảo sát. Đã clone đủ working tree của5repo
tại **các commit đã kiểm ở trên**, trong `.runtime/strategy-references/` của
workspace. Root `README.md` là cửa vào; `source-manifest.json` giữ receipt,
`candidate-files.json` giữ96file có từ khóa liên quan. **96file không là96
ứng viên hoặc chiến lược có edge.** Không thêm vào catalog active integrations.

| Thư mục local | Files checkout | Source MiB |
|---|---:|---:|
|`lean/`|6540|276,3|
|`backtesting-py/`|53|4,5|
|`nautilus-trader/`|5685|137,6|
|`backtrader/`|378|6,7|
|`vectorbt/`|306|167,9|
|Tổng|12962|593,0|

Dung lượng là working-tree source, chưa tính `.git`; clone shallow/filterblob
để tránh tải cả lịch sử. Các repo không có `.gitmodules` tại pins này; không
cài Git LFS payloads/dependencies/build hoặc chạy bất kỳ upstream script nào.
Root library đã được `.gitignore` hiện hành loại trừ, không vendor hàng nghìn
file/copy license vào product hoặc thay engine đang chạy.

Đã kiểm từng origin/HEAD đúng pin, `git fsck --connectivity-only`, working tree
sạch và giấy phép đủ.17file đã review trước đều khớp nội dung;11file khớp
bytes,6fileLEAN khác CRLF/LF trong working tree nên lưu riêng reviewSHA và
working-treeSHA cùng newline-equivalence. Không sửa source/blob để ép hash.
Index local links đã kiểm. Receipt SHA256:
`22f66e26ba45aa15c44b0139887cca89bd11374f79ad94e34d91ae40e6ffdcf4`.

Lệnh gộp inventory/index bị automatic review chặn không nêu lý do; source
clones đã hoàn tất trước đó. Đã hoàn tất index bằng script stdlib chỉ đọc
metadata/checksum trong root cố định và ghi receipt/index, không gọi code
upstream. Gitconfig có duplicatekeys hợp lệ dùng parser last-value; không đổi
Git config global. Download logs và per-repo status giữ trong root library.

Trạng thái đạt: **source đã có sẵn để đọc/port**, chưa engine installation,
import smoke, strategy parity/backtest hoặc runtime adoption. Lần tiếp theo
đọc local file đã pin qua index, giữ original→adaptation/fixture/license gate.

## Owner chon dung framework day du ca nam engine

11/11/2026 owner yêu cầu dùng **full Nautilus**, rồi mở rộng rõ cho **cả năm
engine**. Đây là quyết định mới thay khuyến nghị reference-only, không bị hạ
thành chỉ port indicators. Full ở đây dùng native engine APIs để backtest/
screening và hướng tới execution khi có adapter/gates; chưa live broker.

### Cài và chạy thực tế

[Runtime guide](../../tooling/strategy-engines/README.md) là owner commands/
lockfiles và cách chuyển US500; không thêm framework vào product imports hoặc
catalog apps Paperclip. User yêu cầu cài local và kiểm engine, không yêu cầu
mở tài khoản, API keys, optional provider services hoặc thay production DB.

| Engine/runtime thực sự chạy | Bằng chứng11/11 | Giới hạn |
|---|---|---|
| Nautilus1.231.0, reuse locked product engine_runtime | `uv sync --locked --no-build`; 4direct tests đạt, gồm long/short golden fills/timing/costs, runtime identity, version rejection và parent-death child cleanup | 4DB integration tests không chạy qua setup gate; chưa US500 M15 port |
| LEAN source pin ở trên, .NET10.0.400 | Native Launcher build0errors,4.456upstream warnings,92,02s; BasicTemplateAlgorithm completed,3.943data points,1actual simulated buy fill | Bundled SPY07–11/10/2013, còn holding mở; không là common roundtrip/US500/edge |
| Backtesting.py0.6.6 | Native Backtest/Strategy, syntheticM15 buy/sell/fees/timing đạt;4,502s gồm import | Chưa target Bid/Ask/SL/gap/equity parity |
| Backtrader1.9.78.123 | Native Cerebro/feed/Strategy/broker, cùngfixture đạt;3,624s gồm import | Upstream SyntaxWarning escape sequence; chưa target parity |
| VectorBT1.2.0 | Native Portfolio.from_orders, cùngfixture đạt;28,751s gồm cold import/JIT | Không benchmark throughput hoặc target fill semantics |

Ba smoke dùng cùng6nến OHLC giả lập2022: quyết định sau nến1/3, fillopen2=102/
open4=104,quantity2,fee0,50USD/order; gross4−fee1=net3USD, cash10.003, flat.
Đã kiểm indices/prices/fees/state; fixtureSHA256 giống nhau:
`983aec4a12583bc5088774f3e7a6937eb94933a0f958000462abfb8c5b9101a5`.
Đây là accounting sanity check, không proofUS500execution/model equivalence.
Negative test cùng receiptpath reject trước simulation; không overwriteattempt.

Nautilus module command thực tế chạy8tests/17,268s:4đạt,4fail ở fixture setup
với `TW_V2_ALLOW_DESTRUCTIVE_TEST_DB=1 is required for TRUNCATE fixture tests`.
Không bật flag, khôngTRUNCATE/migration, không gọi đây là8pass. Guide chỉ định
directclass cho lần sau; integratedDB cần disposabletestDB riêng. Runtime
PyArrow25.0.1 giữ riêng, productPyArrow21 không đổi; trackedTraderstatus sạch.

Nautilus downloaded source là2.x, wheel tương thích adapter hiện có là1.x.
Đã kiểm [official installation](https://nautilustrader.io/docs/latest/getting_started/installation/)
và PyPI metadata, không âm thầm dùng prerelease2.x hoặc nâng Python. Full
framework không đòi latestmajor; migration2.x có compatibility slice riêng.
[Official integrations](https://nautilustrader.io/docs/latest/integrations/)
không liệt kêMT5/FTMO tại ngày kiểm; chưa thể gọi ready-made propbroker connector.

Python installs dùng isolatedvenvs/binary-onlyPyPI; manifests+full dependency
locks được commit, wheels/cache/outputs không commit. LEAN build từ auditedpin
bằng SDKđãcó; sourceworkingtree sạch, khôngDocker/login/paidcloud. LEAN logfile
có “Disconnecting from brokerage” là simulatedbacktest lifecycle; không gọi
đó là MT5/broker connection. Không đo outbound network process-level, nên
không khẳng định toàn bộ LEAN execution tuyệt đối0HTTP từ logs.

Local evidence `.runtime/strategy-engines/receipts/{backtesting,backtrader,vectorbt}-v1.json`,
`.runtime/strategy-engines/lean/{build.log,run-v1.log,sample-v1/}`. Native
Nautilus direct tests dùng module hiện có, stdout được ghi trong execution
tool outputs; thất bại setup/command được giữ ở report này. Source download
manifest cũ giữ nguyên vì là receipt lịch sử, không sửa cácfalse thànhtrue.

### Đề xuất ứng viên, chưa freeze hoặc chạy PnL

| Thứ tự | Ý tưởng | Vì sao xem tiếp | Điều phải kiểm trước khi tạo trial |
|---|---|---|---|
|1|US500M15 trend pullback: giá đang theo hướng, hồi rồi tiếp tục hướng cũ|Luật có thể viết rõ, khác câu hỏi firstopeningbreak; reuseEMA readiness/state|RelatedR004SMA20/80H4đã thử, không edge độc lập mới; phải chốt EMA/seed, cách xác định hồi/recross, SL/exit/session và rationale transfer |
|2, dự phòng|US500M15 band reentry: ra ngoài dải rồi đóng trở lại, kỳ vọng về giữa|Một câu hỏi khác continuation; Bollinger chuẩn có code/reference rõ|RelatedR003zscore, không gọi BB là alpha mới; phải chốt prior/current-window bands, SL/meanexit/timecutoff, costs và tránh trend-day hindsightfilter |
|Gác exactversion|R094firstopeningbreak/R095failedbreak|Đã có kết quả và giới hạn, không đáng chạy lại chỉ vì engine mới|Chỉ dùng làm frozen compatibility fixture; semanticschange là trial mới, không reset negative/history |

Đây là shortlist triển khai dễ kiểm, **không xếp hạng expected profit**. Một
phiên bản mỗi hypothesis, không gridEMA/SL/RR/giờ để cứu outcome. Trước PnL:
freeze mechanism/negative lineage, bảngsource→target và nativeeventparity;
chạy mộtdevelopmentpilot, reviewer tài chính/equity rồi mới promote engine lane.
Không cần cả5engine mỗi thử nghiệm. Nautilus/LEAN đề xuất lanes kiểm sâu,
VectorBTscreening, Backtesting.py/Backtraderprototype/crosscheck chọn lọc.
2025+reserved, risk/account/challenge chưa chốt, không có job nền phải đợi.

### Skill và review

Reuse `strategy-research`, thêm conditional `references/native-engines.md`;
`upstream-integrations` dẫn runtime guide khi install/adopt. Không tạo5skills,
skillmanager hoặc thay global policy. Luồng agent: context/source→runtimeguide/
lock→nativefixture→registeredpilot→qualification; engine outputs không tự
ghi đè financial/source authority. Engine runtimes thật đã có nhưng chưa
publish Paperclip capabilities hoặc route current US500 runner sangengine mới.

Skillcreator validator cho2entrypoints và23localreference links đạt; smoke
script parse được, negative overwrite check đạt. Maintainer audit0errors/
0warnings:global12.279B,project10.298/65.536B,reserve55.238B,combined22.577B.
Entry points chỉ thêm routing có điều kiện; không tăng always-loaded policy.
