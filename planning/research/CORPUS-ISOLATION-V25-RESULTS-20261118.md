# V25 — hạ tầng đã cải thiện; chưa có ứng viên mới đủ điều kiện

Ngày chốt số liệu: 18/11/2026. [Protocol](CORPUS-ISOLATION-V25-PROTOCOL-20261118.md)
được commit `427b3b7` trước outcome; [JSON đối soát](CORPUS-ISOLATION-V25-RESULTS-20261118.json).
Nhánh `codex/corpus-mining-and-isolation-v25`. PR103 đã merge `0bb221e`;
nhánh V24 đã xóa. Không tự merge PR bàn giao V25.

**Giữ V16/V19 `BASE_GUARD`, `prop_qualified=false`.** ISO tăng lợi nhuận nhưng
vẫn vượt trần drawdown đã khóa. GBP chỉ là kịch bản H1 và làm tăng drawdown.
Engulfing–RSI không qua Stage-0. Vì không có nhánh vượt cổng Development:
**0 lượt kiểm định mới trên 105 mốc, 0 chuỗi bootstrap mới**; không mở giá
2024–2026 để chọn hay cứu cấu hình.

## 1. Runtime, artifact và inventory Windows

Trader PR33 đã merge `74dad35db2d507f7ada4bae64ffb21c09ad193e9`, 5/5 CI xanh
tại head `3df8d7dd`. Workspace pin đúng merge này. Chọn lọc từ source
`7241a8b0` và `a60db1e5`, không merge toàn nhánh hoặc kéo Rust formatting.

- Launcher/wrapper ràng buộc worktree root, DB, port, output và manifest;
  runtime cách ly không thừa hưởng các tích hợp AI/provider/terminal tùy chọn.
- Artifact Windows có extended paths, khóa không cho writer thay nội dung
  trong lúc đọc, nhận diện ChangeTime/USN và full-hash fallback.
- Fixture containment dùng junction khi Windows không cấp quyền symlink;
  vẫn kiểm đường dẫn thoát root thực, không chuyển thành skip.
- 83 Python tests PASS, 0 skip, thêm 53 subtests. Actual
  `--check-isolation-only`: linked/isolated=true, không mở DB hoặc khởi động
  process. Rust compile/tests/lint được kiểm trên CI; local chỉ có fmt check.
  Chưa rollout/restart runtime hoặc chạy broker.

Workspace reuse path guard cho inventory và `bot_reverse_engineer.py`:
manifest giữ logical path; đường I/O dùng `\\?\`; chặn parent traversal,
UNC và symlink/junction/reparse ancestor. Không đổi Windows global config.

| Số đo | V24 | V25 content scan |
|---|---:|---:|
| Candidate files | 272.988 | 273.378 |
| Signature matches | 4.821 | 4.875 |
| MQL/Pine/EX5 paths | 1.016 | 1.017 |
| Lỗi file/đường dẫn đọc được ghi nhận | 48.425 FileNotFound | 0 |
| Trong 48.425 đường dẫn cũ, đọc lại thành công | — | 48.425 |
| Aggregated rg traversal error | 1 | 1 ở lần đầu; xem đối soát dưới |
| File quá lớn không đọc | theo receipt V24 | 3.832 |

Không mặc định mọi FileNotFound cũ đều có cùng nguyên nhân. Bằng chứng hiện tại
là toàn bộ 48.425 path đã đọc được qua native path, không còn MAX_PATH/file-read
error trong content scan. Content scan mất **2.301,04 giây**; không chạy lại
273 nghìn lượt đọc chỉ để làm sạch thống kê.
Inventory rà signature trên source/config/report đã có; không phải một phép
chứng nhận holdout chưa từng bị đọc. Các financial run mới chỉ dùng
Development2018–2023; không mở một later price cohort để tính/chọn outcome.

Một path bot thêm được là **synthetic control của chính repo**:
`research/bot_reverse_lab/controls/range_rejection.pine`, không phải alpha
vendor mới. 1.029 SHA/profile gồm 603 Python, 153 MQ5, 264 EX5, 5 C#, 3 MQ4
và 1 Pine. Vì scope có thêm Python/C#, không được diễn giải 420→1.029 là tìm
thêm 609 bot độc lập. Nhóm MQ4/MQ5/EX5 vẫn có tổng 420 profile.

### Đối soát traversal, giữ nguyên giới hạn coverage

Raw stderr lần đầu ghi đúng hai thư mục access-denied:

- `D:/ANNAM/TradingWorkspace/projects/vi-dubber/work/pytest-p20`
- `D:/ANNAM/TradingWorkspace/projects/vi-dubber/work/pytest-p20-final`

Lần v2 chỉ **rà metadata**, thêm hai scope exclusion có tên cụ thể; không sửa
ACL, xóa file hoặc mở nội dung hai thư mục này. Hai root D/E đều rg exit0,
stderr0bytes trong 3,324 giây. Rà được 273.432 path: thêm 54 path mới
(34 JSON/20 Python), không mất path nào, không thêm MQL/Pine/EX5/C#.
Các path metadata mới chưa được quảng cáo là đã qua content profiling.
**Zero traversal error trong scope đã khai báo khác full-tree coverage.**
Giữ nguyên stderr, inventory và manifest v1; v2 không ghi đè chúng.

## 2. Phễu corpus và Top10

Phân loại v2 đã sửa nhận diện `iCCI/iMFI/iStochastic/iMACD/iSAR`.
Kết quả v1 giữ nguyên; đây là sửa metadata, không thêm alpha trial.
Hai source Python nội bộ (`bot_lab.py`, `prop_v25_inventory.py`) đã đổi sau
snapshot nên v2 ghi SOURCE_UNAVAILABLE/hash drift; không dùng nội dung mới
thay nội dung đã seal. SHA/defaults của E1 được chọn không đổi.

| Trạng thái v2, không chồng nhau | Profile |
|---|---:|
| Utility hoặc chưa nhận diện được execution entry | 652 |
| Có cờ cần review | 84 |
| Chưa xác minh SL/signal binding | 2 |
| Source đã đổi so snapshot | 2 |
| Synthetic control | 1 |
| Binary, chưa biết logic | 264 |
| CLEAN_STRUCTURAL_CANDIDATE | **24** |
| Tổng | **1.029** |

Cờ có thể chồng nhau: dynamic/external 68; hardcoded-date review 8;
no-stop 7; martingale 2; orphan signal block 4. Không có profile được gắn
ULTRA_TIGHT_SCALPER; thiếu symbol/point/execution context không chứng minh
không có scalping. Hardcoded date là cờ cần review, chưa là bằng chứng gian lận.
JSON/config được rà signature ở inventory, không tự coi là công thức entry.
EX4 có 0 profile; 264 EX5 không được nhận nhãn clean từ strings.

**24 chỉ là ứng viên cấu trúc theo defaults**: có entry, SL argument khác0,
SL default dương và không cờ đã nhận diện. Đây chưa là chứng nhận control-flow,
broker safety, quyền phân phối source hoặc lợi nhuận.

Top10 xếp bằng khả năng đọc/defaults/chỉ báo/tên/hash, không dùng PnL.
Tất cả là MQ5, có 5 aliases/hash trong kho; alias không tạo thêm alpha.
Nguồn chung là thư mục `MQL5/Experts/Free Robots` trong local MT5 cache
(path và SHA đầy đủ trong JSON). Source dùng `_Symbol/_Period`: **tài sản và
khung là chart-selected**, không tự suy ra tất cả được thiết kế cho EURUSD H1.

| # | File, bỏ đuôi .mq5 | Entry có thể đọc từ source | Chỉ báo thực sự được gọi |
|---|---|---|---|
| 1 | BullishBearish Engulfing RSI | Nến engulfing đảo chiều, body so mean12, trend SMA5; RSI BUY<40/SELL>60 | SMA5, RSI37 |
| 2 | BullishBearish Harami RSI | Harami đảo chiều, trend/body context; RSI BUY<40/SELL>60 | SMA5, RSI37 |
| 3 | HangingMan Hammer RSI | Hanging Man/Hammer, trend/body context; RSI BUY<40/SELL>60 | SMA5, RSI37 |
| 4 | BlackCrows WhiteSoldiers RSI | Three Crows/Three Soldiers; RSI BUY<40/SELL>60 | RSI37 |
| 5 | BullishBearish MeetingLines RSI | Hai nến Meeting Lines; RSI BUY<40/SELL>60 | RSI37 |
| 6 | MorningEvening StarDoji RSI | Morning/Evening Doji Star; RSI BUY<40/SELL>60 | RSI37 |
| 7 | BullishBearish Engulfing CCI | Engulfing + trend SMA5; CCI BUY<−50/SELL>50 | SMA5, CCI37 |
| 8 | BullishBearish Engulfing MFI | Engulfing + trend SMA5; MFI BUY<40/SELL>60 | SMA5, MFI37 |
| 9 | BullishBearish Harami CCI | Harami + trend SMA5; CCI BUY<−50/SELL>50 | SMA5, CCI37 |
| 10 | BullishBearish Harami MFI | Harami + trend SMA5; MFI BUY<40/SELL>60 | SMA5, MFI37 |

SL/exit defaults chung của 10 source: SL200point, TP200point, duration10bars,
lot0,1; SL/TP xét spread tối thiểu theo code gốc. Không quy point thành pip
trước khi khai báo symbol/digits. RSI/MFI có exit khi cắt các mức30/70;
CCI tương ứng −80/+80; có expiry và SL/TP. Đây là metadata source, **chưa chạy
cả bộ exit**. Fingerprint có thể chứa tên chỉ báo trong text/strings; cột trên
đã đối chiếu actual calls, không coi chữ “CCI” trong source RSI là dùng CCI.

Các source này gần nhau về ý tưởng mẫu nến/oscillator; không coi đổi RSI sang
CCI/MFI là cơ chế độc lập. Theo card đã khóa, chỉ chọn **1 cơ chế đại diện E1**,
không cố dùng hết ngân sách tối đa3. Source DarkCloud/Piercing có khối BUY
nằm ngoài điều kiện dự định: bị gắn cờ, không tự sửa vendor logic để tạo winner.
Không execute/import bot hoặc phân phối lại source chưa rõ license.

### E1 — Engulfing + RSI37: dừng tại Stage-0

[Card](CORPUS-ENGULFING-RSI-CARD-20261118.md), source SHA
`f31d225aa34323541e4834c4f904d9b3a9d43c695afd04c319d4f3bcfed76313`.
Khai báo EURUSD H1, hai chiều, completed bars, SMA5/RSI37/AvgBody12, SL20pip
theo source200point trong context5digits; không thêm H4/session filter.
Đây là formula port được review, chưa có MT5 binary/source execution parity.

| Năm Development | Raw signals | Endpoint +8h có giá | Mean net +8h sau stress, pip |
|---|---:|---:|---:|
| 2018 | 14 | 14 | −13,1714 |
| 2019 | 15 | 14 | +3,1357 |
| 2020 | 15 | 15 | −5,9600 |
| 2021 | 13 | 13 | −18,4000 |
| 2022 | 15 | 15 | +5,4867 |
| 2023 | 13 | 13 | +5,2000 |

85 raw signals; median SL20pip; entry friction1,9pip, tỷ lệ9,5%, retention100%.
Chi phí gồm paired spread +9USD/lot và legacy funding khi qua rollover;
calendar/clamp là inherited scenario, chưa được chứng nhận riêng cho EURUSD.
Primary+8h không qua cadence>=40/năm, markout dương từng năm và coverage.
+4h chỉ diagnostic, cũng fail; không chọn nó để cứu trial.
**0 SL-active children**, không thêm RSI/MA/timeframe/horizon variant.

## 3. Exact-cost audit, ISO và GBPUSD

### Baseline không đổi membership

Đối chiếu sealed raw cohort: GoldF3 74, GoldF4 95, EURF5 200 =369.
Cả ngưỡng12% và15%: **0 restored, 0 newly rejected**. Không viết lại seal,
historical producers hoặc outcomes.

Initial audit dừng đúng với `FROZEN_FRICTION_MODEL_MISMATCH`: nhầm tiền phí
rounding ở native ledger với Stage-0 lịch sử dùng entry-notional chưa rounding.
Bản sửa giữ chính xác cost contract cũ bằng Fraction; log lỗi đầu vẫn giữ.
Đây là sửa audit, không phải giảm phí hoặc thay chiến lược.

### P80_20_ISO — chỉ một lần chuẩn hóa

Lấy saved metrics chưa làm tròn: `c=0,831878…`, F5=`1,0814413317462606`,
F3=F4=`0,5823145632479864`. Hai ordering M1 OLHC/OHLC cho cùng quyết định.
Các con số R dùng chung reference150USD, là tổng Development2018–2023.

| Số đo marked book | BASE_GUARD | ISO |
|---|---:|---:|
| Net R | +23,8524 | +26,7599 |
| Equity peak-to-valley DD, R | 12,2065 | **12,2419** |
| Static loss dưới vốn đầu, R | 3,9839 | 3,0680 |
| Worst daily R, inherited UTC clock | 2,0371 | 1,5459 |
| Max open stop risk, USD | 312,80 | 260,30 |
| Cluster2018–20 /2021–23, R | +9,3387/+14,5137 | +8,7722/+17,9877 |

**Fail vì DD tăng0,0354R, khoảng5,31USD**, dù net tăng2,9075R.
Lot floor/cent rounding khiến co vector risk không bảo đảm DD tuyến tính.
Không dùng sai số numerical epsilon để cho qua một chênh lệch kinh tế thật;
không co `c` lần nữa sau outcome. Không sinh ISO freeze/lifecycle.
Tỷ số cumulative NetR/DD không phải Calmar annualized.

### GBPUSD — đúng entry recipe, vẫn chưa có exact holding path

[Card H1 diagnostic](GBPUSD-V25-H1-DIAGNOSTIC-CARD-20261118.md).
S01 gốc `GBPUSD.SWEEP.ASIA.LONDON.DAY`, exit20:30; V25 đối chiếu H1
20:00 theo yêu cầu là **một counterfactual đã đăng ký**, không gọi là replay
nguyên bản. Main2.288 endpoint thuộc cohort khác, không tự vá path S01.

Hai correction H1 năm2022 chỉ áp trong RAM trên source copy, giữ raw nguyên.
Entry/side/stop Dev2022–23 khớp **300/300** S01. Dev2018–23:883raw,
830accepted,53costreject,0missing20:00endpoint;33calendar abstentions riêng.
Exact15% khôi phục **2 tín hiệu** từng bị float loại oan; đây là delta cohort
GBP, không phải delta baseline.

| Kịch bản Development | Net R | Equity DD, R | Max open risk USD | Portfolio ExTop5 | Portfolio ExTop10 |
|---|---:|---:|---:|---:|---:|
| Baseline | +23,8524 | 12,2065 | 312,80 | −1,9714 | −18,5087 |
| Baseline+GBP0,25x | +26,4037 | **15,5620** | **340,61** | +0,5799 | −15,9574 |
| Baseline+GBP0,50x | +28,2737 | **26,5211** | **380,41** | +2,0107 | −18,1638 |

ExTopN loại N trade thắng lớn nhất của **chính danh mục Development tương ứng**.
Đây là phép attribution từ tape đã có, không mở giá mới; net được đối soát
với marked book. Cùng một R=150USD; không cộng R theo risk riêng từng lệnh.

Riêng GBP standalone: +9,1738R, DD50,3331R, winrate34,58%;
ExTop5−31,1885R/ExTop10−59,8451R. Cluster2018–20 **−30,2048R**,
2021–23+39,3786R; năm2020−38,8077R. GBP0,25x đóng góp+2,5513R nhưng
riêng sleeve bỏ top5/10 còn−7,4142/−14,5100R;0,50x tương ứng
+4,4213R và−15,6412/−29,8943R.

**Không promote**: cả hai vệ tinh tăng DD/openrisk;0,50x còn xấu hơn về
static/daily loss và âm cluster đầu. Hai H1 ordering cùng số không chứng minh
đúng thứ tự giá trong giờ. Status vẫn `INCONCLUSIVE_PATH`, không có M1/tick
intrahour certification; các trường inherited `SL_active_validated` trong
raw JSON chỉ nói kernel đã chạy scenario, không chứng nhận nguồn H1.
Worst daily trong các bảng ISO/GBP là **UTC marked book**, chưa là FTMO
00:00 CE(S)T daily-loss qualification.

## 4. Hiệu năng, bằng chứng và quyết định

Run cuối trên `.runtime/quant-audit-v24/Scripts/python.exe`, source checkpoint
`e7158c5`, không còn inventory worker cạnh tranh. Runner6shards theo profile
module cũ, giữ đầy đủ1.340IDs, thêm18IDs; không skip, giảm coverage hoặc retry
để chọn một streak đẹp.

| Acceptance local, gồm process startup/fixture I/O | Kết quả | Mục tiêu |
|---|---:|---:|
| Full suite | **1.358 PASS,0skip /13,1008s** | <13,5s |
| Smoke, đúng78IDs /10fresh processes | **10/10 <0,72s** | 10/10 |
| Smoke median/max | 0,6379s /0,6845s | max<0,72s |

10 wall samples:0,6393/0,6130/0,6232/0,6845/0,6384/
0,6296/0,6527/0,6374/0,6220/0,6716s.
Giới hạn: số đo trên máy local với cache trạng thái tại run, không là SLA CI.
Không so lẫn V24 1.335tests13,278s với adoption1.340tests18,635s.

Profile78smoke không thấy child CreateProcess; filesystem fixtures còn thật.
Chỉ tối ưu nhỏ: khử search-path trùng **trước** resolve, giữ ưu tiên import
và canonical dedup. Profile có instrumentation0,7326s không được tính là
acceptance hoặc phần trăm speedup.

10 bảng Zstandard9 có SHA256 compressed/original và đã decompress đối soát
lại: **77.520.660→2.684.096bytes**. Bao gồm bảng classification v1/v2 và
metadata reconciliation; JSON receipts nhỏ không cần nén. Không xóa nguồn.
`evidence-reconciliation.json` khóa hashes/registrations/manifest/tail sums;
mọi binding code của các financial run vẫn khớp source. Giữ initial failures,
negative outcomes và mọi source/correction/protocol đã seal.

Private job:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/corpus-isolation-v25-20261118`.
Các receipt chính: `inventory-summary.json`, `inventory-enumeration-v2-summary.json`,
`corpus-funnel-summary-v2.json`, `ISO-Development-decision.json`,
`GBP-H1-diagnostic.json`, `external-Stage0-results.json`,
`baseline-exact-cost-membership.json`, `performance-final-summary.json`,
`product-adoption-receipt.json`, `evidence-reconciliation.json`.
Exact-head CI và PR ở `completion-receipt.json` sau publish; không nhận
self-review là independent review.

### Hậu kiểm kỹ thuật và bước được đề xuất

| Phát hiện | Sửa/giữ | Bằng chứng và giới hạn |
|---|---|---|
| Long path không đọc được | Native I/O, guard; không đổi global policy |48.425/48.425 reread;5native-pathtests;2fixture exclusions còn rõ |
| Static fingerprint bỏ sót oscillator | Reuse detector; versioned reclassification |15→24structural;regressiontest;E1SHA không đổi |
| Source có signal block ngoài if | Cắm cờ, không sửa để cứu alpha |4profiles bị review;không chạy source |
| Rounded native fees khác frozen admission | Sửa audit theo contract cũ |369raw/0delta;giữ initial mismatch |
| Co trọng số không co DD chính xác | Giữ một trial, bác “chắc chắn pass” |ISO chênh0,0354R;không tune tiếp |
| Endpoint H1 khác exact path | Giữ nhãn scenario và gate đóng |830endpoints đủ;DD không được nâng thành FTMO qualification |
| Import path resolve lặp | Dedup sớm, không bỏ filesystem fixtures |giữ1.340IDs;18IDs mới;đạt run cuối |

Không cần thêm skill/policy mới cho từng incident: các skill hiện hành đã
yêu cầu source/hash binding, negative history, bounded trial và path uncertainty.
Regression nằm trong code/tests; interpretation và scope nằm trong báo cáo này.

Khuyến nghị: **đóng V25 với BASE_GUARD, review PR; chưa mua Challenge hoặc
promote thêm sleeve**. Nếu mở nghiên cứu tiếp, cần đăng ký riêng cơ chế độc
lập và/hoặc giải quyết nguồn đường giá có giá trị quyết định. Việc co ISO thêm,
đổi oscillator/timeframe hoặc tìm exit GBP khác đều là trial mới, không là
phần hoàn thiện còn thiếu của V25.
