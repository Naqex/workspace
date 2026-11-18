# S02 — kết quả replay chung Gold + EURUSD + GBPUSD

Ngày18/11/2026. Đây là lần replay Development đã đăng ký trước, không phải
vòng tối ưu. Cửa sổ chỉ từ `2022-01-01` đến trước `2024-01-01`; 2024–2026
không được đọc. Mức risk cố định là Gold150USD, EURUSD75USD, GBPUSD75USD;
`common-R = USD/150`.

## Verdict

`INCONCLUSIVE_PATH` + `DATA_PATH_INCOMPLETE`.

Phần kế toán/timeline đã được đối soát độc lập trong phạm vi đã khóa. Tuy
nhiên, không được biến kết quả thành “không vi phạm” hoặc Challenge-ready vì
đường XAUUSD có các khoảng thiếu khoảng45 phút khi đang giữ lệnh. Các khoảng
này đều nằm ở phiên bảo trì buổi tối; engine giữ chúng là unknown vì lịch
miễn trừ maintenance chưa được chứng minh trong source contract. EURUSD và
GBPUSD không có unknown >15 phút trong các khoảng giữ lệnh của lần chạy này.

## Kết quả account replay

Mỗi model có ba tài khoản chẩn đoán (năm2022, năm2023 và liên tục 2022–2023)
cho mỗi hệ thống, cộng 24 monthly-start lifecycle accounts. Tổng cộng 108
accounts: hai cost models × hai systems ×27 accounts.

| Model | System | Scope | Net USD | Equity DD USD | Worst daily loss | Entries |
|---|---|---|---:|---:|---:|---:|
| SYM | Gold + EUR | 2022 | 586.10 | 2,807.71 | 0.8397% | 214 |
| SYM | Gold + EUR | 2023 | 2,514.85 | 3,241.59 | 0.7996% | 230 |
| SYM | Gold + EUR | Continuous | 3,100.95 | 3,683.59 | 0.8397% | 444 |
| SYM | Gold + EUR + GBP | 2022 | 1,082.43 | 3,080.00 | 0.9935% | 354 |
| SYM | Gold + EUR + GBP | 2023 | 4,240.17 | 4,225.99 | 0.8252% | 374 |
| SYM | Gold + EUR + GBP | Continuous | 5,322.60 | 4,225.99 | 0.9935% | 728 |
| ASYM | Gold + EUR | 2022 | 863.70 | 2,752.81 | 0.7935% | 214 |
| ASYM | Gold + EUR | 2023 | 2,891.10 | 3,053.69 | 0.7814% | 230 |
| ASYM | Gold + EUR | Continuous | 3,754.80 | 3,460.69 | 0.7935% | 444 |
| ASYM | Gold + EUR + GBP | 2022 | 1,361.68 | 3,025.10 | 0.9473% | 354 |
| ASYM | Gold + EUR + GBP | 2023 | 4,616.42 | 4,131.49 | 0.8260% | 374 |
| ASYM | Gold + EUR + GBP | Continuous | 5,978.10 | 4,131.49 | 0.9473% | 728 |

Continuous Net/DD tăng từ `0.842` lên `1.259` trong SYM và từ `1.085` lên
`1.447` trong ASYM. Đây là cải thiện trong mô hình đã khai báo, đồng thời DD
tuyệt đối tăng từ3,683.59 lên4,225.99USD (SYM) và từ3,460.69 lên4,131.49USD
(ASYM). Không gọi tương quan thấp hoặc ratio cao là bằng chứng an toàn tương lai.

### Lifecycle proxy

| Model / System | P1 / 24 | P2 / 24 | Observed breach | Reward proxy |
|---|---:|---:|---:|---:|
| SYM / Gold + EUR | 0 | 0 | 0 | 0 |
| SYM / Gold + EUR + GBP | 11 | 0 | 0 | 0 |
| ASYM / Gold + EUR | 4 | 0 | 0 | 0 |
| ASYM / Gold + EUR + GBP | 13 | 0 | 0 | 0 |

Không tài khoản nào hoàn thành cả hai phase trong mẫu 24 monthly starts. Các
monthly starts chồng lấn nên không phải 24 thử độc lập và không tạo xác suất
pass tương lai. Reward là proxy kế thừa, không phải quy trình payout FTMO đã
được xác minh.

## Gap và coverage

S02 đã kiểm `733` trade books (Gold210, EUR236, GBP287), preflight
`62,359,581` held tick visits trong runner và 108 account ledgers. Independent oracle đối chiếu
`1,219,429` field checks và `46,082` quote-age checks, đạt:

- `34,301` accepted decisions, `8,699` rejected decisions và `34,301` cost
  bridges khớp;
- 28 phase passes trong các lifecycle account, 0 reward events;
- 96,403,641 quote updates và các source hours Development đúng cutoff;
- toàn bộ receipts ghi `prices2024_2026_read=false`, `prop_qualified=false`.

Khoảng unknown chỉ xuất hiện ở XAUUSD. Trong continuous candidate ASYM có
148 intervals, tổng khoảng111.07 giờ unknown trong phần thời gian đang giữ;
median mỗi khoảng khoảng45.03 phút. Các mốc rơi quanh 21:00–23:00UTC tùy DST
(104 interval bắt đầu theo giờ21UTC,44 theo giờ22UTC trong sample), từ thứ Hai
đến thứ Năm. Đây là dấu hiệu mạnh của daily maintenance, nhưng chưa phải
calendar/source proof đủ để tự động miễn trừ. Không sửa số liệu bằng cách
đặt gap thành giá phẳng hay bỏ lệnh.

## Independent review và giới hạn

Oracle độc lập trả `CORRECTNESS_PASS_FOR_DECLARED_S02_SCOPE`:

- 108 accounts;
- 1,219,429 field checks và 46,082 coverage checks;
- tự xây merge `(timestamp, asset_rank, source_ordinal)`, cash ledger,
  funding, phase/reward và quote-age masks;
- không import producer merge/account/cost/policy ở real path;
- giữ cùng admitted feeds, không phải independent market feed.

Kết quả này chứng minh sự nhất quán của runner với oracle trong đúng source,
cost và policy đã đăng ký. Nó chưa chứng minh:

- exact broker/FTMO feed, spread, slippage, margin, netting hoặc contract;
- lịch selected news USD/EUR/GBP và quy tắc Standard funded;
- đường giá XAUUSD trong gap bảo trì có thể được dùng cho daily/overall DD;
- clean OOS, alpha ngoài mẫu, payout hoặc thu nhập chính.

## Quyết định tiếp theo

Giữ composition Gold + EUR + GBP là ứng viên nghiên cứu tốt hơn baseline trong
Development, nhưng **chưa mở 2024** và chưa đề xuất Challenge. Lát tiếp theo
nhỏ nhất là calendar/path audit cho XAUUSD maintenance và target account:

1. Xác minh deterministic session-break/maintenance schedule đúng timestamp,
   source và DST; không dùng kết quả PnL để chọn lịch.
2. Chỉ khi coverage được admit hoặc vẫn giữ unknown có chủ đích, freeze một
   protocol riêng cho Historical Validation2024. Nếu mở, phải coi 2024 là
   exposed validation theo lịch cũ, không phải clean OOS.
3. Cập nhật news/margin/contract/feed assumptions từ nguồn hiện hành khi truy
   cập được; hiện refresh FTMO ngày18/11 vẫn chưa có bằng chứng web thành công.
4. Sau đó mới review owner handover, shadow/demo reconciliation và runbook;
   không gửi broker, không mua Challenge tự động.

## Evidence

- Runner report: `E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S02-three-asset-replay/attempt-1/REPORT.md`.
- Runner result SHA256:
  `2d56e5b50e3374b6c2e7fcb91382141f7b419248b4068789b8c6ffa13da83f65`.
- Independent S02 receipt SHA256:
  `010efb944b7490fb1d53f81c6937a6cf9c51ac95251a712576ae8220ec02fb73`.
- Independent account review SHA256:
  `8c05a98e923bb29d18a3036ac0758bfa8f971ffb574dfeb53610dd6ac1e77b55`.
- Immutable release SHA256:
  `a48b83cf8bd6d91f2596d90396729b3a5104ab01c7560b2e544232fd1d0aeefe`.
- Protocol: [S02 protocol](SOLO-THREE-ASSET-REPLAY-PROTOCOL-20261117.md).

The independent oracle's retained tooling incident (a temporary typo-path
placeholder outside the assigned output, immediately removed; empty directory
cleanup was policy-blocked) is recorded in its preparation note and did not
touch source, market data or runtime state.
