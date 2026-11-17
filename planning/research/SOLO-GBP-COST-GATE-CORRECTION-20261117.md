# S01 — sửa phép so sánh đúng ngưỡng chi phí15%

Đăng ký ngày17/11/2026, trước khi tính PnL của lệnh bị loại nhầm. Đây là
correctness repair của quy tắc `Friction/NaturalSL <=15%` đã khóa, không
thay ngưỡng, cấu trúc SL, tín hiệu hoặc chọn một lệnh theo lợi nhuận.

## Lỗi và bằng chứng giữ nguyên

Independent oracle v2 dừng với `raw_cost_gate` tại tín hiệu thứ218:
GBPUSD BUY, decision `2023-06-19 09:00 UTC`, Ask128184/Bid128175,
SL128064 trên grid1e-5. SL120units =12pip, ma sát spread9+fees9=18units
=1,8pip. `18/120 =15%` chính xác. Producer float tạo
`0.15000000000000002` nên loại sai. Đối chiếu raw records tìm đúng
một sai khác trong300 tín hiệu. **Chưa đo PnL lệnh này trước đăng ký.**

Giữ nguyên:

- Source-v2 đã admit và original source fail.
- `source-v2/economics-v1/{registration.json,run/*}` tại producer `7f9dd4c`.
- Oracle cũ trỏ original proof và lần oracle v2 fail.
- `source-v2/independent-review-v2/gate-diagnosis.json`, SHA256
  `f08f2dc64de389d733c902699e38050116325f3e1c867349495a9e84a33c073d`.
- Oracle v2 SHA256
  `e85e4e5795ac4eed954b8f26fb4d48788a1551e14084a9f67f6de9099e4628ac`.

Đường source-v2:
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S01-gbp-confirmation-source-v2/`.
Kết quả v1 giữ trạng thái historical, chưa đủ correctness để promote.
Oracle chưa đi tới annual aggregate/sáu đường GBP M1; không gọi chúng đã pass.

## Thay đổi duy nhất và ranh giới

Verdict cost gate dùng đơn vị giá nguyên với cross-multiplication (hoặc
Decimal chính xác): FX `100*(spread_units+9) <=15*natural_stop_units`.
Kiểm stop ở đúng executable side như trước. Các phí của Gold/indices phải
được biểu diễn đúng đơn vị nếu sửa helper dùng chung; không đổi giá trị
commission/slippage. Float có thể giữ để trình bày, không quyết định boundary.

Giữ toàn300 signals, source hashes, natural SL, timestamps, entry/exit
mechanics, risk150/75, baseline A+EUR, cost models, metrics/gates/trial history
của [S01](SOLO-GBP-CONFIRMATION-PROTOCOL-20261115.md). Không mở2024–2026.
Không bỏ lệnh do kết quả xấu, không đặt epsilon nới ngưỡng.

Helper có nhiều consumer: test đúng/bên dưới/bên trên boundary cho assets
được hỗ trợ. Sửa code không tự ghi lại lịch sử các campaign khác. Baseline
books/curves A+EUR của phép S01 vẫn là frozen inputs; không tái chọn chúng.
Trước promotion S02, cần kiểm riêng ảnh hưởng boundary ở raw cohort baseline
EUR và ghi gap nếu chưa xác minh; không suy repair GBP chứng nhận toàn lịch sử.

## Attempt mới

Code + protocol + tests được commit trước register/run. `economics-v2` là
directory mới, tuyệt đối không ghi vào `economics-v1`. Registration bind:

1. Prior economics registration/result hashes và independent failure/diagnosis.
2. Source-v2 registration/proof/manifest/correction lineage; toàn raw cohort.
3. Frozen baseline inputs/curves và prior producer commit.
4. Code mới, protocol này, old protocol, parameters không đổi và Dev cutoff.

Source đã admit bằng producer cũ không mất lịch sử vì helper nay được sửa.
Nếu cần historical producer verification, chỉ nhận đúng committed bytes
đã pin cho code cũ; dữ liệu external vẫn kiểm trực tiếp đúng hash. Không
tắt `verify_pins`, hạ tolerance hoặc cho phép arbitrary live-code drift.
Code mới chạy phải có pin riêng; không giả nó chính là code của v1.

Rerun đủ300 signals vì cost membership thay đổi. Dự kiến287 fills/13 rejects
chỉ là assertion cơ học; nếu có thay đổi khác thì dừng để điều tra. So286
trades cũ phải giữ entry/exit/SL/prices/costs, thêm đúng identified signal.
Tính lại GBP money150/75 và sáu M1 curves; baselines giữ nguyên và verify
ordinal semantics. Không chọn kết quả v1/v2 theo profitability.

Output giữ annual/by-side/by-exit/netR/concentration/coverage/marginal gates.
Gate verdict được tính lại dù xấu hơn. S02 tiếp tục chờ kết quả sửa được
oracle độc lập chấp nhận.

## Kiểm chứng

- Regression đúng ví dụ218; ratio bằng15% nhận, cao hơn một price unit loại,
  stop invalid vẫn loại; kiểm BUY/SELL và rounding/unit của assets.
- Lineage/output tamper, thay params/cohort/source, v1 overwrite, cutoff và
  missing source bị chặn trước run; synthetic tests không mở giá.
- Independent Decimal/struct oracle không dùng producer gate/money/merge:
  đối chiếu300 intents,287 fills,13 rejects, amounts150/75, annual totals,
  sáu GBP M1 arrays. Khác biệt material giữ failure, không sửa oracle theo
  kết quả producer chỉ để pass.
- Cả source-v2 và correction vẫn same-vendor, không FTMO parity; M1 additive
  portfolio chưa là shared-account replay, `prop_qualified=false`.
