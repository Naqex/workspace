# Native strategy engines

Owner 11/11/2026 chọn dùng framework thật của cả năm engine, thay đề xuất chỉ
đọc/port mẫu. Phạm vi hiện tại là research/backtest; chưa cutover Trader hoặc
kết nối broker. Full framework không có nghĩa cài mọi optional provider, dịch
vụ cloud hay thay mô hình dữ liệu để ép các engine ra cùng số.

## Vai trò và nguồn phiên bản

| Engine | Vai trò đề xuất | Nơi giữ runtime pin |
|---|---|---|
| NautilusTrader | Backtest theo sự kiện, hướng tích hợp execution sau qualification | `projects/trader/foundation_v2/engine_runtime/{pyproject.toml,uv.lock}` hiện có |
| LEAN | Engine nghiên cứu/backtest đầy đủ; đối chiếu chiến lược và indicator | Git commit trong source receipt của thư viện local, từ [source review](../../planning/research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md) |
| VectorBT | Screening nhiều tín hiệu/config bằng native Portfolio, không kết luận execution từ vector signals | `vectorbt/{pyproject.toml,uv.lock}` |
| Backtesting.py | Prototype Python ngắn và kiểm lại một quy tắc | `backtesting/{pyproject.toml,uv.lock}` |
| Backtrader | Backtest event-driven thứ hai để đối chiếu chọn lọc | `backtrader/{pyproject.toml,uv.lock}` |

Không chạy mọi candidate qua cả năm mặc định. Screening dùng một engine;
shortlist mới kiểm chéo một engine khác. Đây là phân vai đề xuất, chưa promotion
Nautilus thành mặc định cho các US500 studies. Engine hiện tại giữ baseline/
rollback và các receipts cũ không đổi. Không fork source khi chưa cần sửa.

Nautilus source vừa tải là API2.x; adapter product đã pin stable1.x. Dùng bản
stable đã tương thích để khôi phục môi trường; không chạy mẫu2.x bằng1.x hoặc
coi wheel1.x được build từ pin2.x. Theo [official installation](https://nautilustrader.io/docs/latest/getting_started/installation/),
plain install hiện vẫn là1.x, docs latest là2.x; đổi major cần migration riêng.
[Official adapter list](https://nautilustrader.io/docs/latest/integrations/)
đã kiểm không liệt kê MT5/FTMO; chưa có bằng chứng ready-made broker adapter
cho case này. Framework full không cấp quyền broker.

Các wheel Python cài từ PyPI bằng `uv`, binary-only, từng venv riêng. Source
library pin và runtime release là hai identity riêng; không tự coi giống byte.
Giữ license upstream: LEAN Apache2; Nautilus LGPL3; Backtesting.py AGPL3;
Backtrader GPL3; VectorBT Apache2 kèm Commons Clause. Không đưa source của các
framework vào product hoặc mở rộng quyền redistribute/network-service ở đây.

## Dựng lại và chạy kiểm tra

Từ workspace root, với `uv` và CPython3.12 đã có:

```powershell
uv sync --project tooling/strategy-engines/backtesting --locked --no-build
uv sync --project tooling/strategy-engines/backtrader --locked --no-build
uv sync --project tooling/strategy-engines/vectorbt --locked --no-build
uv sync --project projects/trader/foundation_v2/engine_runtime --locked --no-build
```

Mỗi backend chạy bằng interpreter của nó; đổi output cho mỗi attempt:

```powershell
& tooling/strategy-engines/backtesting/.venv/Scripts/python.exe -X utf8 tooling/strategy-engines/smoke.py backtesting --output .runtime/strategy-engines/receipts/backtesting-v2.json
& tooling/strategy-engines/backtrader/.venv/Scripts/python.exe -X utf8 tooling/strategy-engines/smoke.py backtrader --output .runtime/strategy-engines/receipts/backtrader-v2.json
& tooling/strategy-engines/vectorbt/.venv/Scripts/python.exe -X utf8 tooling/strategy-engines/smoke.py vectorbt --output .runtime/strategy-engines/receipts/vectorbt-v2.json
```

`smoke.py` dùng native engine APIs trên sáu nến M15 giả lập: quyết định sau
nến1/3, mua2units ởopen2=102, bán ởopen4=104, phí0,50USD/order. Vốn10.000,
gross4, phí1, net3, flat cuối mẫu. Kiểm cả timing, fill và phí, không chỉ import.
Không dùng `python -O` vì smoke assertions là kiểm chứng.

Nautilus reuse bốn direct engine tests đã có, không bật destructive DB flag.
Từ `projects/trader`, dùng module path và chỉ chọn direct class:

```powershell
$env:PYTHONPATH = (Resolve-Path foundation_v2).Path
& foundation_v2/.venv/Scripts/python.exe -X utf8 -m unittest foundation_v2.tests.test_u5_nautilus.NautilusIndependentOracleTests -v
```

Không chạy cả module vào database đang dùng. Class integration kế thừa fixture
có TRUNCATE và cần disposable test DB riêng; các failures vì gate không là
accounting failures và không được bật env flag để né gate.

LEAN dùng .NET10 có sẵn, không cần Docker/login cho bundled C# example. Đọc
source receipt, đối chiếu Git HEAD trước build; chưa tự nâng pin:

```powershell
dotnet build .runtime/strategy-references/lean/Launcher/QuantConnect.Lean.Launcher.csproj -c Release --disable-build-servers -v minimal
```

Sau build, từ `lean/Launcher/bin/Release`, chạy native launcher với các absolute
paths tương ứng checkout hiện tại, không dùng config account:

```powershell
.\QuantConnect.Lean.Launcher.exe --config D:/ANNAM/TradingWorkspace/.runtime/strategy-references/lean/Launcher/config.json --environment backtesting --algorithm-type-name BasicTemplateAlgorithm --algorithm-language CSharp --algorithm-location D:/ANNAM/TradingWorkspace/.runtime/strategy-references/lean/Launcher/bin/Release/QuantConnect.Algorithm.CSharp.dll --data-folder D:/ANNAM/TradingWorkspace/.runtime/strategy-references/lean/Data --results-destination-folder D:/ANNAM/TradingWorkspace/.runtime/strategy-engines/lean/sample-v2 --close-automatically true
```

Bundled SPY2013 example không là fixture US500 hay bài roundtrip chung ở trên.
Backtest/sample result phải kiểm status/fills/artifacts, không chỉ exit0.

## Chuyển US500 vào engine

1. Freeze spec: cùng source Bid/Ask, M15 close clock/DST, thứ tự decision/fill,
   quantity/contract/rounding, fee/slippage/financing, stop/gap và missing path.
2. Import native data/instrument/strategy; engine đó thực sự tạo events/orders/
   fills/accounting. Không gọi incumbent để tính kết quả rồi gắn nhãn engine mới.
3. So event trace ở fixtures long/short, next-event fill, stop/gap, no-trade,
   costs và missing/ambiguous paths. Lệch semantics phải giải thích hoặc chặn;
   PnL giống nhau không tự chứng minh parity. Không syntheticize missing prices.
4. Chạy một registered development pilot trên exposed2022–24, kiểm financial
   ledger và equity path rồi mới promote lane. 2025+ giữ nguyên gate.
5. Qualified survivors mới kiểm FTMO/news/closure/time-fit và forward demo.

[Kết quả cài/chạy11/11](../../planning/research/STRATEGY-TEMPLATE-REUSE-REVIEW-20261111.md#owner-chon-dung-framework-day-du-ca-nam-engine)
phân biệt installation, fixture, market parity và product/runtime acceptance.
Rollback: ngừng chọn lane mới, dùng engine baseline; venv độc lập có thể dựng
lại từ locks. Không migration dữ liệu, sửa service hay xóa kết quả cũ.

## US500 native study đã chạy ngày11/11

[Results/limitations](../../planning/research/US500-MULTIFRAME-RESULTS-20261111.md)
ghi162financialbooks+9null, full native Nautilus1.231.0, chưa target execution
hoặc product cutover. Source pin của financialrun và hậu kiểm có identity riêng;
đọc correctedv3-review, không dùng oldv2qualityflags để kết luận missingpath.

```powershell
& projects/trader/foundation_v2/engine_runtime/.venv/Scripts/python.exe -X utf8 -W ignore::FutureWarning -m unittest discover -s tooling/ai-engines/tests -p '*us500_multiframe.py' -v
& projects/trader/foundation_v2/engine_runtime/.venv/Scripts/python.exe -X utf8 -W ignore::FutureWarning -m unittest discover -s tooling/ai-engines/tests -p test_multiframe_runner_recovery.py -v
```

Runner `tooling/ai-engines/run_us500_multiframe.py` yêu cầu data/output/protocol
paths và actual `--protocol-sha256`; optional `--year 2022/2023/2024` cho cohort
riêng. Mỗi output chỉ một writer, `CANCEL` marker và1800sdeadline. Chỉ dùng
`--resume-completed` khi original manifest/code/protocol/input bindings khớp;
không claim intra-book resume. Không rerun completed study không đổi.

`postreview_us500_multiframe.py` là correction đã ghi amendment, không generic
repair hoặc financial replay. `summarize_us500_multiframe.py` chỉ đọc completed,
sealed correctedcohorts. Savedview không thay nativefinancial source version.

[R123 MA-reclaim](../../planning/research/US500-MA-RECLAIM-RESULTS-20261111.md)
reuse shared nativeexecution qua optional offline `policy_factory`; mặc định
legacy không đổi. Runner `run_us500_ma_reclaim.py` giữ frequency gate và chỉ
cho G2costscreen riêng khi có exact registration/parentattempt bindings theo
[amendment](../../planning/research/US500-MA-RECLAIM-COST-SCREEN-AMENDMENT-20261111.md).
Đã9books/40scopedtests; exactrecipe không retained, không productcutover.
