# S02 — kết quả replay chung Gold + EURUSD + GBPUSD

Ngày18/11/2026. Đây là lần replay Development đã đăng ký trước, không phải
vòng tối ưu. Cửa sổ chỉ từ `2022-01-01` đến trước `2024-01-01`; 2024–2026
không được đọc. Mức risk cố định là Gold150USD, EURUSD75USD, GBPUSD75USD;
`common-R = USD/150`.

## Verdict

`INCONCLUSIVE_PATH` + `DATA_PATH_INCOMPLETE`.

Phần kế toán/timeline đã được đối soát độc lập trong phạm vi đã khóa. Tuy
nhiên, không được biến kết quả thành “không vi phạm” hoặc Challenge-ready vì
đường XAUUSD có các khoảng thiếu vật lý gần60 phút khi đang giữ lệnh. Sau khi
engine bỏ qua15 phút đầu của một khoảng thưa theo policy, phần được đánh dấu
`unknown` có median khoảng45,03 phút. Các khoảng này tập trung ở buổi tối và
lặp lại theo ngày trong source, phù hợp với giả thuyết daily maintenance nhưng
chưa phải bằng chứng lịch bảo trì. Engine giữ chúng là unknown vì lịch miễn
trừ maintenance chưa được chứng minh trong source contract. EURUSD và
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
phần unknown mỗi interval có median khoảng45,03 phút, còn khoảng source gap
vật lý gần60 phút. Các mốc rơi quanh 21:00–23:00UTC tùy DST (104 interval
bắt đầu theo giờ21UTC,44 theo giờ22UTC trong sample), từ thứ Hai đến thứ Năm.
Đây là mẫu gap buổi tối lặp lại, phù hợp với giả thuyết daily maintenance,
nhưng chưa phải calendar/source proof đủ để tự động miễn trừ. Không sửa số liệu bằng cách
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
- đường giá XAUUSD trong khoảng thiếu báo giá có thể được dùng cho daily/overall DD;
- clean OOS, alpha ngoài mẫu, payout hoặc thu nhập chính.

### Audit lịch nguồn ngày18/11

Audit timestamp trên108sổ tìm thấy148 khoảng duy nhất,74 trong mỗi năm.
Tất cả khớp17:00–18:00 `America/New_York` trong6giây (104DST/44standard).
Median full gap60,0326phút; unknown tail45,0326phút. Continuous candidate
unknown1,924739%, baseline2,178177%. Đây là khoảng thời gian quote cũ, không
phải tỷ lệ lệnh bị mất hoặc tỷ lệ dữ liệu toàn thị trường bị thiếu.

Lịch local chỉ có holiday/Friday guards; catalog QDM không ghi lịch phiên
nguồn theo ngày hiệu lực. Vì vậy **không miễn trừ coverage**. Lịch FTMO2026
khác nguồn/năm không chứng nhận lịch Dukascopy2022–2023. Dù lịch được chứng
minh sau này, vẫn phải giữ kiểm tra reopen/gap/SL, swap và Prague reset;
không tạo giá trong giờ đóng cửa hoặc gọi broker path đã xác minh.

Report/JSON/receipt ở
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/three-asset-preparation/xau-gap-calendar-audit-20261118/`.
Report SHA256 `41dacc33a84385a57caa82e5ab68269b5561bcdaf486bed30131639830881ace`;
JSON SHA256 `1fa88974a831c905f307f652495bca827ff5bad0a2a452c9c2877e16e80eb62d`.
Audit chỉ dùng timestamps/evidence, không backtest hay mở2024–2026.

### Đối chiếu nguồn chính thức và chẩn đoán vòng 2

Ngày18/11 đã tải được [lịch Dukascopy hiện tại](https://wiki.dukascopy.com/en/manuals/jforex4-desktop/trading-sessions):
XAU, `America/New_York`,18:00–17:00; tương ứng nghỉ17:00–18:00.
Đây là bằng chứng củng cố148gaps, **chưa chứng nhận hiệu lực2022–2023**.
Archive query bị429; FTMO FAQ tiếp tục lỗi TLS. Không miễn trừ gap hoặc chạy
lại S02 chỉ để đổi diễn giải. Packet nguồn công khai ở sibling
`historical-session-sources-20261118/`, report SHA256
`c6ab15dd29d1e6bd27f75f17b36bc9e253d5d176a742067671193b9077fee607`.

Chẩn đoán sau outcome chỉ đọc ledger cho thấy0P2 do cả thời gian còn ngắn và
lợi nhuận cuối2023 yếu, không chỉ do cutoff. Candidate quaP1 đều trong10/2023;
11/13windows còn68–88ngày nhưng chỉ4/3đườngP2khác nhau (SYM/ASYM).
Median thời gianP1 chỉ trong nhóm hoàn tất là292,85/323,85ngày. BestP2net cuối
kỳ+644,38/+853,68USD so target2.500USD;7windows mỗi model kết thúc âm.
Không dùng số cửa sổ chồng lấn làm xác suấtpass, không có median hoàn tấtP2.

Candidate có354/374lệnh năm2022/2023. Net2022 trừ3lệnh lớn nhất theoUSD còn
−2.096,43/−1.846,98USD;2023 còn+615,63/+939,38USD. Phép trừ này mô tả mức
tập trung, không là replay loại3lệnh rồi chạy lại admissions. Tần suất đã tăng;
độ đều và tốc độ lợi nhuận vẫn chưa đạt mục tiêu Challenge nhanh.
Diagnostic/JSON/script ở sibling `lifecycle-diagnosis-20261118/`, report SHA256
`a32496950aa8dbfb22ac7ed60b40cc364f524dd442b4ca513fb5714a5261506e`.

## Quyết định tiếp theo

Giữ composition Gold + EUR + GBP là ứng viên nghiên cứu tốt hơn baseline trong
Development, nhưng **chưa mở 2024** và chưa đề xuất Challenge. Audit local và
nguồn công khai đã hoàn thành trong giới hạn trên. Bước tiếp:

1. Giữ unknown lịch sử; không suy lịch đích từ lịch nguồn. Không chờ vô hạn
   hoặc lặp request thất bại khi có thể kiểm câu hỏi validation có điều kiện.
2. Chỉ khi coverage được admit hoặc vẫn giữ unknown có chủ đích, freeze một
   protocol riêng cho Historical Validation2024. Nếu mở, phải coi 2024 là
   exposed validation theo lịch cũ, không phải clean OOS.
3. Cập nhật news/margin/contract/feed assumptions từ nguồn hiện hành khi truy
   cập được; refresh FTMO17/11 và18/11 thất bại, chưa có nguồn FTMO mới thay thế.
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
