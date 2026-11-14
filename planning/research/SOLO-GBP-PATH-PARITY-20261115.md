# S01 — bổ sung đối soát đường vốn trước kết quả kinh tế mới

Ngày 15/11/2026. Bổ sung correctness cho
[protocol S01](SOLO-GBP-CONFIRMATION-PROTOCOL-20261115.md);
không sửa protocol/registration đang khóa của downloader.
Chưa chạy economics thật. Không đổi signal, SL, horizon, risk, weight hay gates.

Review synthetic phát hiện helper `native_bars` kế thừa giới hạn theo timestamp,
nhưng một timestamp có thể chứa nhiều tick theo thứ tự gốc. Tick xuất hiện sau
ordinal đã khớp SL vẫn bị tính vào nến M1 đường vốn. Giá thoát và cash PnL không
đổi, nhưng floating equity/DD có thể lệch. Fixture cùng trade/cash cho DD
1,03R so với 66,67R khi thêm một tick sau thoát cùng millisecond.

## Phép sửa đã khóa trước outcome

- GBP mới: reader giữ đúng `entry_quote_index` và `exit_quote_index`, sau đó
  dùng lại `curves()` và money helpers. Không sửa các module source đã frozen.
- Baseline là **A Gold150 + EUR75**. Metadata đã xác minh: Gold210 trades mỗi
  model, EUR236 trades; toàn bộ có hai ordinal. Manifests Dev có sẵn: Gold6402
  hours, EUR2994 hours. Chưa tải thêm nguồn hay đọc giá để tính kết quả mới.
- Pin manifests, frozen trade files, legacy curves, addendum và producer code
  trong economics registration riêng, sau `SOURCE_RECONCILED` và commit/review.
- Đối chiếu producer functions `core_curves`, `curves`, `native_bars` với source
  trong commit composition V3 `ec602f737405dd5cad1cdcd60b72e8dd2e6c75e8`, cùng
  các hash đã ghi trong decision V3. Khác biệt source-only đã được biết là
  tham số `asset` của kiểm gap; nó không đổi contribution của từng phút.
- Với baseline, chỉ thay contribution ở nến M1 chứa entry/exit. Đọc boundary
  hours, xác minh timestamp/ordinal/giá khớp với frozen trades rồi loại tick
  trước entry ordinal hoặc sau exit ordinal. Chênh giá của close/low/high
  nhân cùng quantity, hướng và giá trị contract tạo delta tại đúng phút đó.
  Nếu phút entry thay đổi rồi có các phút không có tick, delta được giữ đến
  nến có dữ liệu tiếp theo, đúng cách producer cumsum giữ mark cuối. Phút exit
  chuyển sang cash ở phút kế tiếp nên delta kết thúc tại đó.
  Phí, funding và số tiền sau đóng lệnh giống nhau nên triệt tiêu trong delta.
  Những phút ở giữa không đổi. Không rerun signal hay chọn lại trade.
- Core regime files phải có nguyên entry/exit/SL của original A0. Tổng cash
  của frozen trades phải khớp điểm cuối legacy curve; điểm cuối corrected
  curve không đổi. Không khớp thì dừng phép đo, không promote từ baseline
  chưa rõ. Lưu riêng legacy/corrected metrics, các boundary bị sửa và delta.
- Cổng tương quan dùng **GBP75 thực tế sau làm tròn lot**, so với A150+EUR75.
  Báo thêm GBP150 để đối chiếu; không thay GBP75 bằng bản nhân 0,5 của GBP150.

Đây là sửa phép đo bằng đầu vào đã có, không phải thử nghiệm thay chiến lược.
Mọi kết quả V3 giữ nguyên; file corrected chỉ ghi trong S01/economics-v1/run.
Không đọc giá 2024–2026, không dùng kết quả thật để quyết định cách sửa.

## Kiểm chứng và giới hạn

Fixture phải so delta correction với dựng lại toàn bộ curve sau ordinal clip:
BUY/SELL, nhiều trade cùng phút, entry/exit cùng millisecond, phút thiếu tick
ngay sau entry, phí và funding,
giữ nguyên terminal cash. Kiểm thêm GBP75 correlation, gate nguồn/hash và
chặn junction/symlink trong đường output con.

Corrected curves vẫn là tổng các envelope M1 của từng tài sản; không chứng minh
thứ tự tick chung của ba tài sản, ngân sách tài khoản chung, Daily Loss chính xác
hay Challenge-qualified. Phép sửa baseline không phải một audit nguồn toàn bộ
đường giá mới. Chỉ khi các gate Dev đã khóa đạt mới xem xét shared-account replay.

Kiểm chứng implementation ngày 15/11/2026 trước commit/numerical: bộ
`test_solo_gbp_economics.py` chạy24 tests,23 đạt;1 test tạo symlink bị skip vì
Windows không cấp quyền tạo symlink. Bộ hồi quy `test_prop_portfolio_v3.py`
đạt21/21; `git diff --check` sạch. Đối chiếu source ba producer functions với
Git archive/decision hash đạt; kiểm này chỉ đọc code và metadata.

Commands dùng research Python riêng và `PYTHONPATH` trỏ ai-engines +
Trader `foundation_v2`: `python -m unittest discover -s tooling/ai-engines/tests
-p test_solo_gbp_economics.py` và tương tự với `test_prop_portfolio_v3.py`.
Chưa tạo economics registration, chưa chạy outcome thật, chưa commit bởi worker.
