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
