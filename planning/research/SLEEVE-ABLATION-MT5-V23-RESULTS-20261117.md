# V23 — tách ba nhánh, thử loại F3 và kiểm watcher MT5

**Bỏ Gold F3 cải thiện Development, nhưng chưa đủ để thay V16/V19 BASE_GUARD. Ba phép chuyển F5 đều rớt; chưa có chiến lược đủ điều kiện mua Challenge.**

PR101/head `26de14c` đã merge `9309109`; nhánh V22 đã xóa. Nhánh V23 `codex/sleeve-ablation-and-mt5-v23`, freeze `d7e8150` trước khi tính thống kê mới trên lịch sử sau 2023. Lịch sử 2024–13/10/2026 đã exposed từ các chiến dịch trước, không gọi là OOS sạch. Không đổi signal, stop, risk, exit hoặc thử trọng số sau kết quả. PR102 để mở.

## 1. Đóng góp từng nhánh và phép loại trừ

Mỗi nhánh là một cơ chế giao dịch (sleeve). R ở bảng này = PnL ròng / 150 USD, có lot floor thực của model. Drawdown equity có floating theo đường M1 giả định; cashDD chỉ dùng lệnh đóng. Mỗi kỳ bắt đầu flat riêng. ExTop10 bỏ đúng 10 identity thắng lớn nhất toàn danh mục đã exposed; không bỏ 10 lệnh riêng của từng nhánh.

| Kỳ | Nhánh | Lệnh | Win% | NetR | MeanR | EquityDD R | CashDD R | ExGlobalTop10 R |
|---|---|---|---|---|---|---|---|---|
| Development | EURUSD F5 | 194 | 44.85 | 25.191 | 0.130 | 12.991 | 12.359 | -7.772 |
| Development | Gold F3 | 63 | 31.75 | -9.701 | -0.154 | 14.181 | 12.909 | -9.701 |
| Development | Gold F4 | 83 | 48.19 | 8.362 | 0.101 | 4.978 | 4.045 | 4.597 |
| Later_exposed | EURUSD F5 | 72 | 43.06 | 11.750 | 0.163 | 8.863 | 8.282 | -0.194 |
| Later_exposed | Gold F3 | 40 | 55.00 | 10.226 | 0.256 | 4.304 | 2.716 | 10.226 |
| Later_exposed | Gold F4 | 42 | 42.86 | -3.437 | -0.082 | 7.697 | 7.417 | -3.437 |

Cả hai thứ tự OLHC/OHLC có trong JSON. V22 G_L3_A **đã miễn EURUSD F5**; 17,289R là mọi khoản lỗ tránh được, trong đó L3 chỉ 10,858R. Cả 17,813R lời bị bỏ đều thuộc Gold.

| Nhánh | Lệnh chặn | Lỗ tránh R | Trong đó L3 R | Lời mất R | Delta NetR |
|---|---|---|---|---|---|
| EURUSD F5 | 0 | 0 | 0 | 0 | 0 |
| Gold F3 | 34 | 6.653 | 3.885 | 2.599 | 4.054 |
| Gold F4 | 44 | 10.637 | 6.974 | 15.214 | -4.577 |

Ba trial Development đã đăng ký; cổng yêu cầu net tăng, equityDD giảm, daily không tăng và hai cụm ba năm dương trong cả hai ordering. Không có grid trọng số. A1 chọn F3 vì mean Dev R/lệnh thấp nhất, không chọn bằng top10 toàn kỳ.

| Trial | Lệnh giữ | NetR | EquityDD R | Worst daily R | 2018–20 R | 2021–23 R | Gate |
|---|---|---|---|---|---|---|---|
| A1_DROP_WEAKEST | 277 | 33.554 | 11.437 | 1.765 | 11.821 | 21.733 | PASS |
| A2_F3_EXHAUSTION90 | 306 | 27.906 | 12.442 | 2.037 | 11.241 | 16.665 | EQUITY_DD_NOT_LOWER |
| A2_F4_EXHAUSTION90 | 296 | 19.275 | 15.784 | 1.593 | 6.781 | 12.494 | NET_NOT_HIGHER, EQUITY_DD_NOT_LOWER |

Baseline Dev: +23,8524R / 12,2065R equityDD. A1: +33.5535R / 11.4373R; giữ nguyên risk hai nhánh còn lại, không phân bổ lại risk F3. Day-range/ATR là biến biết tại entry; L3 là nhãn sau outcome, không dùng làm tín hiệu trực tiếp. Worst daily R ở screen unit-book dùng ngày UTC theo cùng helper baseline; daily loss tài khoản ở phần 3 dùng reset/anchor của lifecycle profile đã pin, không thay bằng ngày UTC.

Phân nhóm ngày biến động lớn sau đây chỉ mô tả Dev, không là bộ lọc mới hay bằng chứng nhân quả. Mẫu ngày lớn của F5 có thể không đồng nhất với mọi chế độ đảo chiều.

| Nhánh | DayRange/ATR | Lệnh | NetR | MeanR |
|---|---|---|---|---|
| EURUSD F5 | <=0.9 | 143 | 24.602 | 0.172 |
| EURUSD F5 | >0.9 | 51 | 0.589 | 0.012 |
| EURUSD F5 | UNKNOWN | 0 | 0 | N/A |
| Gold F3 | <=0.9 | 29 | -5.647 | -0.195 |
| Gold F3 | >0.9 | 34 | -4.054 | -0.119 |
| Gold F3 | UNKNOWN | 0 | 0 | N/A |
| Gold F4 | <=0.9 | 39 | 3.785 | 0.097 |
| Gold F4 | >0.9 | 44 | 4.577 | 0.104 |
| Gold F4 | UNKNOWN | 0 | 0 | N/A |

Dữ liệu không xác nhận mệnh đề “F5 cần ngày đã chạy lớn”: Dev F5 ở DayRange/ATR≤0,9 đạt +24,602R / mean+0,172R, nhóm>0,9 chỉ +0,589R / mean+0,012R. Gold F3 âm trong cả hai nhóm; Gold F4 lại dương ở cả hai. Không suy causal regime hoặc mở filter mới từ bảng này. F3 đổi từ −9,701R Dev sang +10,226R kỳ sau; F4 đổi từ +8,362R sang −3,437R. Vì thế bỏ F3 có lợi trong tập chọn nhưng không tự bảo đảm bền qua chế độ thị trường.

## 2. Sáu quan sát H1 mỗi cặp và chuyển nguyên F5

**Giá đủ 100%: GBPUSD 2.288/2.288, AUDUSD 1.795/1.795.** Không thêm nến hoặc bịa early-close. 12 quan sát (không phải 12 ngày khác nhau) bị `ok=false` do Gold holiday guard, đều có entry/endpoint đúng giờ. Bảng sau tách quyền giao dịch đích khỏi sự tồn tại giá.

| Asset | Recipe | Ngày UTC | Giá entry/20:00 | FTMO session evidence |
|---|---|---|---|---|
| GBPUSD | B2:PD:sweep=0.1 | 2021-04-02 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| GBPUSD | B2:PD:sweep=0.1 | 2023-04-07 | Có / Có | FTMO_NOTICE_NORMAL_FX_HOURS |
| GBPUSD | B2:ASIA:sweep=0.1 | 2019-04-19 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| GBPUSD | B2:ASIA:sweep=0.1 | 2021-12-24 | Có / Có | FTMO_NOTICE_NORMAL_FX_HOURS |
| GBPUSD | B2:ASIA:sweep=0.1 | 2022-04-15 | Có / Có | FTMO_NOTICE_NORMAL_FX_HOURS |
| GBPUSD | B2:ASIA:sweep=0.1 | 2023-04-07 | Có / Có | FTMO_NOTICE_NORMAL_FX_HOURS |
| AUDUSD | B2:PD:sweep=0.1 | 2018-03-30 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| AUDUSD | B2:PD:sweep=0.3 | 2018-03-30 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| AUDUSD | B2:ASIA:sweep=0.1 | 2018-03-30 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| AUDUSD | B2:ASIA:sweep=0.1 | 2021-04-02 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |
| AUDUSD | B2:ASIA:sweep=0.1 | 2022-12-26 | Có / Có | SOURCE_CONFLICT_TARGET_SESSION_UNVERIFIED |
| AUDUSD | B2:ASIA:sweep=0.3 | 2018-03-30 | Có / Có | UNVERIFIED_DATE_SPECIFIC_FX_SESSION |

Nguồn chính thức đã đối chiếu: [24/12/2021](https://ftmo.com/es/blog/trading-update-16-12-2021/), [15/04/2022](https://ftmo.com/it/blog/trading-update-07-04-2022-2/), [07/04/2023](https://ftmo.com/en/blog/trading-updates/trading-update-30-mar-2023/), [thông báo trước lễ 15/12/2022](https://ftmo.com/it/blog/trading-update-15-12-2022/), [bảng hồi cứu 12/01/2023](https://ftmo.com/it/blog/trading-update-05-01-2023-2-2-2/). Hai nguồn cuối mâu thuẫn về FX26/12/2022 (mở bình thường so với đóng): giữ SOURCE_CONFLICT/TARGET_SESSION_UNVERIFIED, rút claim closed ban đầu và giữ artifact cũ. Có4 quan sát normal được hỗ trợ,8 quan sát thuộc4 ngày còn unknown/conflict. 2018/2019/2021 Good Friday chưa có thông báo đúng ngày được xác minh; giữ unknown. Không lấy lịch broker khác thay FTMO. Các phép đo transfer dùng declared weekday scenario, chưa chứng nhận lịch đích.

F5 giữ H4 / vùng 5 ngày / ADX≤25 / buffer 0,1ATR / tín hiệu đầu tiên mỗi ngày UTC / naturalSL P0; không thêm parameter. FX dùng H1 thật để dựng H4, không tạo M1; deadline 20:00. Gold M1 dùng 20:30 và lịch guard đã khóa. Bảng này là raw markout sau phí stress trước stop, không phải account replay.

| Asset | Raw/priced | Cost giữ% | Median SL | Friction/SL% | 2018–20 R | 2021–23 R | Dual/Stage0 |
|---|---|---|---|---|---|---|---|
| GBPUSD | 172/172 | 97.09 | 39.95 pip | 4.51 | -15.476 | 19.211 | False / False |
| AUDUSD | 188/188 | 82.98 | 27.15 pip | 7.00 | -13.931 | -12.661 | False / False |
| XAUUSD | 197/197 | 63.96 | 7.91 USD/oz | 9.64 | -2.007 | -15.998 | False / False |

**0/3 qua Dual-Cluster; 0/3 qua Stage-0.** Không chạy SL/account cho losers. Tất cả còn thiếu cadence≥40 mỗi năm và ít nhất một năm âm/không bù ma sát.

## 3. A1: mô phỏng vòng đời tài khoản, chưa là giao dịch thật

Chỉ A1 qua Dev nên mới được chạy toàn kỳ. Reuse quote/event quarter tapes V19, bỏ đúng actions F3, giữ quotes/reset/session/cost/lot/shared risk/house-money. Mỗi case gồm 105 mốc mở Challenge hằng tháng và 1 sổ Standalone Funded, với oracle kiểm toàn ledger. Không cộng payout của các mốc chồng nhau thành thu nhập.

| Model | Path | Friction% | Vòng1/105 | Hai vòng/105 | Median tháng* | Daily% | Static% | Breach |
|---|---|---|---|---|---|---|---|---|
| V19 | PRIMARY | 100 | 80 | 71 | 48.06 | 2.027 | 6.383 | 0 |
| V19 | PRIMARY | 150 | 74 | 15 | 40.93 | 2.031 | 7.723 | 0 |
| V19 | STRICT | 100 | 14 | 0 | N/A | 1.986 | 8.400 | 0 |
| A1 | PRIMARY | 100 | 78 | 63 | 42.08 | 1.876 | 5.974 | 0 |
| A1 | PRIMARY | 150 | 75 | 36 | 63.03 | 1.905 | 6.151 | 0 |
| A1 | STRICT | 100 | 14 | 0 | N/A | 1.840 | 8.400 | 0 |

*Median chỉ trên mốc đã hoàn tất; không chứng minh mốc mới sẽ pass nhanh hơn. A1 PRIMARY100 chỉ 63/105 hai vòng so với 71/105 V19; 33 mốc bắt đầu từ 2024 vẫn 0 hoàn tất. Giảm median có thể do thay nhóm đã pass, không đủ để promote. STRICT là stress nguồn thiếu, không sửa 32 path gốc. Dev72 starts và OHLC mọi case giữ đầy đủ trong JSON.

A1 fixed150 toàn kỳ giữ 391/494 lệnh, NetR 41.8664 so với baseline42,3917R. Cadence khoảng 44.52 lệnh/năm; ExGlobalTop10 còn -6.8063R (baseline -6.2810R). A1 còn30/391 path source-uncertain so với32/494 gốc: loại F3 không khôi phục dữ liệu thiếu. Đây là sổ đơn vị, chưa phải đường vốn tài khoản adaptive.

Bootstrap: **5.000 cùng draw plans cho mỗi ordering**, mỗi draw có Challenge + Standalone Funded, 36 tháng và prefixes 12/18/24, giữ tương quan giữa tài sản qua joint quarter blocks. 10.000 draw-order evaluations / 20.000 ledgers đều audit. Đây là tần suất resampling lịch sử đã exposed, không phải xác suất tương lai.

| Model | Order | Hai vòng12m% | 18m% | 24m% | 36m% | Standalone payout USD/năm |
|---|---|---|---|---|---|---|
| V16 | OLHC | 1.24 | 6.08 | 14.32 | 33.36 | 946.37 |
| V19 | OLHC | 1.38 | 6.20 | 14.50 | 33.56 | 946.41 |
| A1 | OLHC | 1.52 | 5.32 | 12.04 | 29.86 | 904.62 |
| A1 | OHLC | 1.52 | 5.32 | 12.04 | 29.86 | 904.62 |

Payout cột cuối là model Funded ngay từ đầu mỗi draw, khác payout sau khi pass Challenge. JSON ghi riêng post-Challenge payout. Chưa tính đây là thu nhập owner hoặc tiền rút thật. **Giữ incumbent V16/V19 BASE_GUARD**; A1 là bằng chứng cấu trúc đáng giữ nhưng chưa giải quyết time-fit/robustness.

## 4. Watcher, kiểm toán, hiệu năng và storage

Lệnh mới (foreground, giới hạn chờ và capture; không cài service):

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --watch-mt5 --watch-timeout 300 --seconds 60
```

Watcher dò terminal đã chạy → kiểm FTMO Demo/Trial USD và quote đủ mới → bind executable/account hash/server → snapshot spec + parity diff → lưu Bid/Ask/spread thành Zstd Parquet/SHA256. Nếu terminal mất hoặc account đổi, ghi failure; không tự chạy fixture. Không mở terminal/login/symbol_select hoặc gửi lệnh. Timeout/poll/capture đều hữu hạn; không tự chuyển shadow. Commission/lịch phiên/tin có thể vẫn unknown.

CLI thực tế: `TIMEOUT_NO_READY_TARGET`, 2 probes / 2.218s, không terminal đích và không broker orders. 15 regressions V23 gồm detect/capture giả lập, timeout, interrupt, terminal biến mất, replay giả, thiếu binding và account drift. Native capture thành công còn chưa kiểm trên terminal thật.

Full suite **1295 PASS / 0 skip**, giữ nguyên **1.280 V22 IDs**, wall **19.728s**; mục tiêu <13,2s: **False**. Smoke 10 fresh serial processes/same78 IDs: **0/10 <0,72s**, median **0.876s**, max **1.047919s**. Giữ mọi outlier; không retry chọn streak. Startup và fixture I/O nằm trong timer.

Profile smoke cho thấy chi phí import/filesystem. Thử A/B 8 samples xen kẽ dedup import roots không cho cải thiện nhất quán; không đưa thay đổi đó vào source. MC workers cùng chạy trong A/B, nên không so absolute samples đó với final timing sau khi MC kết thúc. **Chưa đạt acceptance hiệu năng V23.** Tải ngoài trong đúng cửa sổ đo cuối chưa được profile; chưa đủ bằng chứng quy nguyên nhân, không đổ toàn bộ cho15 test mới hoặc khẳng định máy đã idle.

31 bảng Zstd9: 183,365,521 → 7,192,853 bytes; SHA256 compressed/original và roundtrip đã kiểm. Journals/checkpoints/raw logs giữ nguyên để đối soát/resume; small human-readable receipts giữ JSON, không nhân bản price cache hoặc xóa nguồn.

Kiểm toán độc lập agent tại `6d2df38`: không finding material trong ablation/calendar/watcher, 15 tests xanh và29 manifests lúc review; không bao gồm final aggregates/CI chưa có lúc đó. Integrity audit cuối kiểm thêm toàn bộ ledgers/manifests. Không phải nguồn giá độc lập hay broker acceptance.

Review bổ sung tại `fb82499` xác nhận arithmetic/period DD/ExTop10 và phát hiện P2: hai thông báo FTMO mâu thuẫn về26/12/2022. Đã sửa provenance/claim trong v2, giữ initial review, không thay financial runs.

| Hậu kiểm | Kết luận |
|---|---|
| Bỏ nhánh âm Dev vẫn làm ít mốc pass hơn | Diversification, account path và phase state khác cộng R; không promote bằng Dev tổng |
| `ok=false` bị gọi là thiếu giá | Tách price availability và target-session eligibility; giữ V22 receipts, sửa active interpretation |
| Cổng exhaustion gộp F3/F4 mất winner | Split đúng cơ chế vẫn phải qua net/DD; hai A2 đều fail |
| Terminal có thể mất giữa probe/capture | Require native + executable/account binding; fail-closed, giữ report |
| Benchmark nhiễu | Giữ samples, bác tối ưu không chứng minh được; không xóa tests hoặc chọn streak |

PR102 để mở; exact-head 3CI/downloaded test IDs chốt trong private `ci-exact-head-reconciliation.json` và `completion-receipt.json` sau push. Giữ Trader pin/VI Dubber WIP, không có broker execution/deploy/payout thật.

[Protocol](SLEEVE-ABLATION-MT5-V23-PROTOCOL-20261117.md) · [Freeze](SLEEVE-ABLATION-MT5-V23-FREEZE-20261117.json) · [JSON](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.json) · [Quickstart](QUICKSTART-FTMO-FREE-TRIAL.md)
