# Cash-close tick v2: đã sửa source consumer, cả hai vẫn chưa đạt

[Protocol](INDEX-PAPER-WINDOW-ECONOMIC-PROTOCOL-20261109.md) `170e9bd`, component
`885cdd7`; [source correction](INDEX-PAPER-WINDOW-SOURCE-CORRECTION-20261109.md)
`6c2a885`, full-year loader `004840d`. Corrected attempt đã terminal và qua
separate raw-selection/Fraction review. **Chưa có ứng viên challenge; Goal active.**
Đổi window/delay là recipe revision, không sửa parent v1 negatives thành pass.

## Kết quả chiến lược

Một hypothetical unit = 1 USD/index point, chưa lot/risk0,25%/account10k. Các số
là component net theo declared costs, không lịch sử fills/phí thật của broker.
Không cộng hai assets thành portfolio. Delay1s là primary đã khóa trước outcome.

| Component / delay | 2019 chuẩn | 2019 stress | 2022 chuẩn | 2022 stress |
|---|---:|---:|---:|---:|
| US500 / **1s primary** | −188,57 | −435,57 | −27,43 | −277,43 |
| US500 / 2s | −190,61 | −437,61 | −78,77 | −328,78 |
| US500 / 60s | −201,78* | −445,78* | −75,96 | −325,98 |
| NASDAQ / **1s primary** | −476,76 | −725,76 | +390,46 | +140,46 |
| NASDAQ / 2s | −490,10 | −739,10 | +163,12 | −86,88 |
| NASDAQ / 60s | −417,16 | −666,16 | +111,49 | −138,51 |

US500 planned2019/2022=247/250; NASDAQ=249/250. Primary1s và2s resolved toàn
planned. *US5002019/60s chỉ244/247 endpoints resolved; đây là known-partial sum,
không full annual net. Missing/expiry không bị gán PnL0 hoặc xóa khỏi census.
3source targets vượt expiry giữ nguyên. Two-year/all-delay cost gate không đạt:
US500 âm cả hai năm, NASDAQ2019 âm và2022 nhạy delay. Gác exactv2, không chọn
riêng NASDAQ2022/1s, hạ phí hoặc chỉnh clock/expiry để tạo winner.

3.018 cashday-delay records, 2.985 resolved asset-day-delay cases và29.850
role/cost cases có lặp calendar/assets/delay/cost/control; không independent
trades. Vẫn consumed development2019/2022, chưa cleanOOS/SL/equity/account/
prop/time-fit/prospective/ownerhandover. Không đo gamma hoặc futures replication.

## Lỗi đã bắt được và phạm vi sửa

Source reviewv1 dùng lại `[1,3]` của Jan/Jul pilot cho US500 cả năm. Q2/Q4 bị
gọi sai là missing canonical, khiến planned124/126 và tạo false no-exposure.
Raw economic reviewer tự chọn quotes/late price phát hiện mismatch nên attempt
đầu bị chặn; không dùng verdict/PnL đó. Giữ nguyên mọi old files/hashes/failure.

Sửa loader nhận accepted proofhash/year/side, buộc4quarters/8side seals và kiểm
census/clock/duplicate/year. 4regression tests đạt, gồm pilot-only/missing/tamper.
Actual source repair chỉ498US500Q2/Q4hours, kiểm148.064canonical OHLC fields;
**1.498 unaffected reports bytes exact**, raw/native tick/locators không đổi.
Late confirmation US5002019/2022=247/249 và250/250; NASDAQ=249/249 và250/250.
Quarter/feature coverage được kiểm trước PnL, không chờ summary hoặc nới gate.

Corrected attempt tính lại US500; **NASDAQ1.509 rows bytes exact reuse** từ old
sealed combined rows, rồi reviewer kiểm toàn hai assets. Không new source
fetch, raw/canonical rewrite, strategy/cost/risk change hoặc holdout read.
Một saved correction script có compile SyntaxError `else250`; sửa trước chạy,
không numeric/source run từ script lỗi. Old evidence và failure không bị thay.

## Nguồn đã có và khả năng tái sử dụng

| Bằng chứng | Phạm vi |
|---|---|
| Intake | 1.996instrument-hours /998regularasset-days, 16.080.264jointticks, native1.51.1 |
| Every-tick review | 80.401.320native fields so raw bằng integer-grid decoder |
| Fraction riêng | 20hours /1.213.185fields:16pilothours +4max-count hours; không claim all16million quaFraction |
| Canonical bridge sau sửa | 149.218commonM1sideOHLC,0conflict/0M1withoutticks/0tickswithoutM1/0latepriceconflict |
| Quote targets | 7.984targets /7.981within60s; archived timestamps, không arrival/broker fills |
| Storage của source này | Raw JSON376.002.849B; native exports2.326.604.618B; chưa inventory toàn project/backup proof |

Quy tắc consumer: UTCms/eventclock, BidAskjoint, grid0,001/indexpoints, native
quote-volume millions (không exchangevolume), ordinal/order, missing/expiry,
schema/version/source/hash/exposure/lineage. Native export/raw giữ immutable;
hourly review projections có seals là derived lookup, không ledger/DB cạnh tranh.
Không cần vectorDB/RAG service cho numerical prices; code đọc đúng artifacts.

## Thời gian và hậu kiểm

| Lát | Thời gian đã đo | Ghi chú |
|---|---:|---|
| Intake từ start đầu tới complete | 22m23,8s | Gồm network failure, khoảng nghỉ163s và resume; không toàn coding session |
| Invocation đầu | 826,533s tới failure | 1.353hours đã sealed; CPU đoạn này chưa được lưu |
| Invocation tiếp | 353,974s /CPU67,781s | Prefix validation10,486s nằm trong số này; chỉ643hours còn lại |
| Source review | First653,907s tới source-failure; resumed284,779s | Chạy chồng intake; không cộng thành duration tuần tự; CPU resumed117,516s |
| Correct canonical scope | 31,748s /CPU22,438s | Reuse tick results, không fetch/replay full source |
| Corrected producer | 6,455s /CPU6,234s | Prep2,963s; compute/reuse2,027s; ngoài ra hash/write/report |
| Economic raw/Fraction reviewer | 21,298s /CPU21,078s | Scan7.058.656rawdelta ticks để chọn quotes, không giữ wholehistoryFraction trong RAM |

Cache16hours, successful fresh responses1.980; có một fetch failure chưa phân
loại được cause vì upstream/catch không giữ nested cause. Same-code retry
invocation tiếp tục đúng hour thiếu; không broad retry auth/WAF/403/429 hoặc
provider fallback. Source/reviewer mỗi job một writer, immutable prefix, failure
history và per-run PID/events. Mọi workers đã terminal, không còn job phải chờ.

Priorities: correctness của cohort trước performance. Root omitted quarters đã
sửa ở loader/code test, không chỉ prompt. Cải tiến benchmark trước đó vẫn giữ:
inspect3,98× /cachedpin+decode replay7,04× trong cùng pilot scope; không gọi đổi
recipe/mask hoặc31,7s affected repair là speedup cùng workload. Chưa cần GPU,
Rust/NumPy/service mới. Gap log fetchcause để future-controller slice, không
rewrite pins/old proofs hoặc bật retry rộng để che lỗi chưa rõ.

Skill `strategy-research/references/source-transformations.md` thêm pilot→history
partition/role census trước PnL; không skill mới. Positive walkthrough là actual
fourquarter repair; negative là pilot1/3 và status-only không gây fullrerun.
4loader regressions, 6component tests/120Fraction cases, 8parent regressions,
48raw quote preflight và6actual economic mutations reject. Skill structure/link
audit và maintainer đạt0errors/warnings; global12.279B/project10.133of65.536B,
reserve55.403B/combined22.412B. Chưa native package publish hoặc model độc lập.

## Locator và bước tiếp

Private base `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/index-paperwindow-tick-source-v1/`: giữ intake/result/seals.
- `index-paperwindow-tick-review-v1/`: frozen, canonical scope sai ở US500Q2/Q4;
  thay interpretation bằng `index-paperwindow-tick-review-v2/` cho full source.
- `index-paperwindow-components-v2/`: frozen first attempt, affected US500/full
  verdict invalidated; `index-paperwindow-components-v2-corrected1/` là current.
- Saved scripts và preflight receipts bên cạnh private execution root; producers/
  reviewers hashes/snapshots trong manifest. Source correction helper `004840d`.

Source result SHA `e27f59da681ce168a29aef2f19180e37b56d798419d5437e4ee94be7937e70a1`;
corrected source review `4624d538f9cfa5cfcba7b76d17609fe9af5499802062e88f64849324342afd1b`.
Economic result `7764da578805185e0293dbb0bdef5ce27763d92849fc85fa14023831d656c898`;
economic review `4d3d0a3a1d2b5e24d0352e62cbc4e0ee46949126364ed3ea8e85d26e758ac52b`.

**Tiếp:** method admission cho published consensus signal đã ở queue trước
outcomes: [JFE2021 Table6](https://academicweb.nd.edu/~zda/intramom.pdf),
η(rONFH,rROD) chỉ trade khi hai signs đồng hướng. Đọc lại09/11 xác nhận định nghĩa;
không có group PnL mới trong lượt này. Nếu đăng ký: giữ selection history,
source reuse không fetch, gate/controls phù hợp trước outcomes. First-half
control trên cùng consensus mask bằng primary theo định nghĩa, không đặt
gate bắt primary vượt chính nó hoặc tự đổi gate sau kết quả. Đây là hypothesis
riêng trong cùng family, không rescue exactv2/independent discovery hoặc unseen.
Goal vẫn active; không hạ C1/C2 để tạo winner.
