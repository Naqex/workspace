# Quant core cho các chiến dịch sau V8

`market_data_store` đọc columnar cache hiện có bằng mmap read-only, seek theo
timestamp, SHA256 mỗi file generation (path/size/mtime/hash); không xuất mỗi
giờ thành một file mới. `QuoteStore` nhận manifest offsets V8 và cùng interface
endpoint/path. Binary được kiểm với manifest; raw hash được giữ như provenance,
không giả đã parse/kiểm lại toàn bộ raw feed. Input snapshots phải immutable.

`ftmo_execution_and_calendar` là cửa vào phí Gold và lịch 2018–2026 đã hiệu
chỉnh 31Dec2021. Giữ rõ ngày có official target times và declared guards.
SYM_FLAT/ASYM_ORDER là hai **giả định** cố định; không biểu phí FTMO live.
DAY vẫn min holiday/Friday deadline, funding được đếm theo timestamp.

`prop_lifecycle_and_parity` reuse V6 harvester, V7 account và alternate rational
oracle bằng adapter. Không copy state machine, không sửa các module V1–V8 có
seal. Tham số fee/risk của lifecycle backend vẫn là fixed scenarios đã kiểm;
đổi biểu phí hoặc policy cần adapter/version và parity riêng, không chỉ sửa
dataclass rồi coi legacy lifecycle tự nhận.

V9 Stage0 là consumer đầu tiên của data/cost/calendar; lifecycle tests gọi
adapter. Các chiến dịch sau import qua core; lịch sử dùng source đã freeze.
Đây là ranh giới reuse, không tuyên bố đã xóa toàn bộ duplication lịch sử.

## Kiểm thử

`quant_test_suite.py --tier fast --output <receipt.json>` bao gồm tất cả module
đã chạy ở CI trước V9, cùng core/V9/maintenance. `--tier historical` là tập
bù; hợp hai tập giữ nguyên đủ IDs. `--group base|native|statistics|worker`
chọn runtime theo các receipt V8; không chạy native dependencies ở Python base.

Historical suite vẫn chạy khi thay shared contracts/engine và trước bàn giao
chiến dịch. Fast CI không thay nghĩa coverage toàn bộ; CI không có private
market inputs. Shared capture fixture là immutable, mỗi test dùng writable
copy, kiểm baseline không đổi khi kết thúc module. Không mock storage/hash.

Benchmark: `quant_core_benchmark.py` kiểm field parity trước timing, xen kẽ
16 cặp cùng một lát M1. Không quy tốc độ seek thành speedup cả chiến dịch.

## V10: ma trận endpoint và test song song

`vectorized_stage0_scanner` đo raw signals × DAY/24H/48H/FRIDAY, rồi mới báo
cohort qua ngưỡng phí. Không dùng endpoint trước entry; entry tại/sau hard-flat
thứSáu không được carry sang tuần kế. Endpoint thiếu giá≤60s vẫn invalid.
Mọi median scale gate tính trên pooled cluster; annual diagnostics giữ riêng.
SYM/ASYM, HAC5/Holm và DSR proxy là screening theo protocol, không chứng nhận
broker fills, directional edge, SL-active PnL hoặc đường vốn quỹ.

Consumer `prop_v10_campaign.py` khóa544ô trước outcome. `prop_v10_verify.py`
đối soát persisted arrays bằng Fraction, giữ original attempt; technical retry
đăng ký riêng. `benchmark` so cùng136recipes/at/side/stop/config16cặp xen kẽ.
Nguồn private cần đúng admission/hash; các lệnh không tự tải provider.

```powershell
python tooling/ai-engines/quant_test_suite.py --tier smoke --output <private-job>/smoke.json
python tooling/ai-engines/quant_test_suite.py --tier all --workers 2 --profile <private-job>/serial.json --output <private-job>/parallel.json
```

Smoke30tests đo0,64s ở Windows15/11/2026; không thay full gate.
Hai subprocess chia nguyên module, có thể cân bằng bằng receipt serial;
parent đối soát modules và test IDs trùng. Không chia lớp có fixture chung.
`--group complete --tier all --workers 2` dùng khi một runtime có đủ native,
statistics và worker dependencies. Local còn giữ4runtime groups đã pin;
receipt V10 đối soát đầy đủ1.030IDs, giữ nguyên1.013IDs V9,0skip.
CI chạy full suite và lưu timings/IDs, không cần private prices.
Contracts chạy Windows để thực thi cả process ownership/sharing-race và
Windows absolute-path contracts; Linux còn secret scan/UI registry. Không
skip các test này để làm xanh full gate. HTTP fixtures dùng httpx từ Trader lock.

## V11: nguồn H1 gốc và bộ ghép cố định

`native_hourly_source.PairedHourlyStore` đọc Bid/Ask H1 gốc qua index và hash;
không dựng M1 giả để lấp đường giá trong giờ. `IndexedUs500Store` dùng lại
JSON M1 theo quý và source proof cũ. Cả hai đọc nguồn trên E, không nhân bản
full raw. Adapter công thức chạy module V10 cô lập với closed frames chuẩn bị
sẵn; không sửa file frozen hay monkeypatch instance dùng chung.

US500 dùng lại lịch `prop_portfolio_sources.deadline`: hạn rơi vào break
16:15–18:00 New York chuyển sớm về 16:00 cùng ngày. Không dùng quote sau giờ
nghỉ để lấp thiếu. Attempt ban đầu được giữ, bản sửa có protocol/commit riêng.
H1 FX thiếu quote 20:30 vẫn là thiếu, không nội suy hoặc lấy 21:00.

`zero_tuning_ensemble.mechanical_composition` nhận daily endpoint proxy và
thời điểm tín hiệu từ Development. Trong cùng asset/family, graph nối các
nhánh tương quan ≥0,30 hoặc trùng ≥50% quyết định; mỗi connected component
giữ medoid trung tâm. Sort theo asset/family/ID, nhận lần lượt khi corr <0,30
với các nhánh đã giữ, tối đa 8. Không thử mọi subset, trọng số hoặc direction.

Endpoint R ghi theo ngày entry chỉ phục vụ sàng lọc. Nó không thay actual
daily MTM covariance, đường lệnh SL-active, prop DD hay portfolio accounting.
V11 có 1.264 cells, 42 dual-positive, 33 component-admitted, 6 selected;
fail cổng Development nên hủy các bước SL-active/validation/lifecycle.
Đọc [protocol](../../../planning/research/ENSEMBLE-AND-STORAGE-V11-PROTOCOL-20261115.md)
và [report](../../../planning/research/ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.md)
trước khi tái sử dụng.

Full local Windows V11 giữ 1.030 test IDs cũ, thêm 18, tổng 1.048, không skip.
Smoke 44 tests quan sát 0,673s; full grouped 28,47s. Đây là timing của từng
lượt, không bảo đảm tốc độ host khác. Oracle dùng Fraction/scalar và source
decoder khác đường producer; cùng implementer, không phải reviewer độc lập.

## V12: stop-active paths và ledger oracle

`vectorized_sl_active_kernel.PathIndex` dùng extrema blocks 64 bars rồi resolve
first hit bằng bar gốc. `replay` hỗ trợ P0 natural SL, P1 net +1,5R rồi protect
net +0,15R tại lúc kích hoạt, P2 TP 3R. Stop mới có hiệu lực từ bar kế tiếp;
same-bar stop/TP thì stop trước; gap qua stop khớp open bất lợi. H1 có deadline
giữa giờ không được lấy extrema của phần bar sau deadline. Missing path là
unknown, không tự dựng quote hoặc tính thành 0R.

`money` giữ V11 cost scenarios, tính carry đến exit thực. Đây là reference
1 lot, chưa shared-account quantity model. US500 giá 0,001 point cần round
gross leg tới cent trước net; nghịch đảo P1 phải xử lý plateau cent. Lần đầu
oracle bắt sai khác đó; bản sửa chỉ rerun US500, giữ bốn asset và failed attempt.
`daily_mtm` ghi entry/exit cost đúng leg và carry, dùng cho correlation; không
thay M1 intraday equity/DD hay execution trên account.

`independent_ledger_auditor.py` ở cấp `ai-engines/` cố ý không import Quant
Core accounting. Nó tự tính Decimal cash/fees/carry, kiểm first-hit/calendar
và Prague balance anchor qua raw quote snapshots. Ledger cần contract/cost/
calendar, exit reason và protection decision ngoài các fields tối thiểu;
không suy tất cả từ symbol hoặc đọc producer PnL làm oracle.

Consumer `prop_v12_campaign.py` khóa 2.888 path cells. `--attempt cent-corrected`
reuse hash-bound Gold/EUR/GBP/AUD và chỉ đo lại US500. `prop_v12_verify.py`
decode accepted source riêng và kiểm cash/path; báo đầy đủ scope của partial
coverage. Current composer thêm `correlation_limit`, default 0,30 giữ V11,
V12 gọi 0,25; exact V11 source còn trong Git/snapshot, không đổi seal lịch sử.

V12 chưa có component đủ path để ghép ensemble, không mở giá 2024–2026 hoặc
chạy lifecycle. Đọc [protocol](../../../planning/research/SL-ACTIVE-ENSEMBLE-V12-PROTOCOL-20261115.md),
[cent correction](../../../planning/research/SL-ACTIVE-ENSEMBLE-V12-CENT-CORRECTION-20261115.md)
và [report](../../../planning/research/SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115.md).
Full local giữ 1.048 IDs cũ, tổng 1.072/0 skip; smoke 66 tests quan sát 0,670s.
Các query/property cases vẫn đầy đủ, chỉ bỏ NumPy scalar-access overhead
trong test oracle. Không chuyển timing kernel thành timing toàn pipeline.
