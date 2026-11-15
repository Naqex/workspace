# V9 — dọn storage, lõi dùng chung và kết quả tìm alpha

**Kết quả: hạ tầng gọn hơn; chưa tìm được chiến lược mới đủ để thi Challenge.**
PR87 đã merge `5f1b687`; nhánh `codex/system-and-alpha-v9`. PR V9 chờ owner duyệt.
Giữ VI Dubber WIP, Trader pin, canonical QDM/raw và các seal; không broker/paid/Astra.

## 1. Storage: đã dọn gì, giữ gì

| D: phạm vi đọc được | Trước | Sau | Giảm |
|---|---:|---:|---:|
| Dung lượng GiB | 208.588 | 197.561 | 11.027 |
| File | 633,571 | 591,665 | 41,906 |
| Folder | 80,979 | 76,352 | 4,627 |

GiB=2^30 bytes; giảm bytes ≈11,84GB thập phân. Đây là logical bytes, không allocated NTFS.
Hai thư mục pytest dưới VI Dubber không có quyền đọc ở cả hai lần: không sửa ACL, không
gọi là tổng tuyệt đối. Junction/symlink không được follow; map đầy đủ cấp1/2 ở private
inventory có SHA trong JSON kèm theo. E initial scan còn9 lỗi long-path; E final hỗ trợ
long path, không lấy chênh lệch hai lần đó làm số liệu cleanup E.

- HOT: source active, VI Dubber (~129GiB), canonical QDM/tick/M1 và reports/seals giữ nguyên.
- EPHEMERAL: 30.329 file cache/576.731.875 bytes và 6.524 file Rust incremental/
  10.665.360.906 bytes đã xóa. Giữ executable, deps, source và runtime active.
- COLD: hai `.venv` từ clean-setup fixture tháng10 đã archive vào E, roundtrip và
  rehash trước bỏ bản giải nén (2.097 +5.551 file sau purge cache). MANIFEST SHA256
  giữ từng file; không archive raw hay đổi path bằng chứng đang có seal.
- D net giảm ít hơn tổng purge vì Python tái tạo cache khi kiểm thử, cùng source/report mới.
- Không xóa venv/node_modules active, worktree thuộc chat khác hoặc log/evidence chỉ dựa tên.
- E chỉ inventory và backup dry-run, không purge bản backup; E tăng thêm các receipt/archive
  và cached EUR exports V9. Không `/MIR` hoặc `/PURGE`.

Các thư mục cấp1 lớn trước cleanup:

| Thư mục D | GiB | File | Folder |
|---|---:|---:|---:|
| `projects` | 190.254 | 393,060 | 41,125 |
| `.runtime` | 10.902 | 116,281 | 24,407 |
| `planning` | 3.239 | 33,965 | 5,197 |
| `tooling` | 1.353 | 60,362 | 6,180 |
| `education` | 1.228 | 9,542 | 513 |
| `.artifacts` | 1.174 | 18,447 | 2,601 |
| `.git` | 0.430 | 1,488 | 833 |
| `.worktrees` | 0.007 | 315 | 49 |
| `UI-Systems` | 0.000 | 49 | 31 |
| `docs` | 0.000 | 12 | 5 |

Cấp2 nhiều file nhất (không cộng lại với cấp1):

| Thư mục | GiB | File |
|---|---:|---:|
| `projects/integrations` | 3.091 | 161,772 |
| `projects/mt5-tradingview-backtester` | 44.223 | 97,379 |
| `projects/vi-dubber` | 129.058 | 82,693 |
| `projects/trader` | 13.737 | 45,968 |
| `.runtime/paperclip` | 0.582 | 39,425 |
| `planning/trader` | 3.089 | 32,767 |
| `tooling/strategy-engines` | 0.738 | 29,987 |
| `.runtime/hermes` | 0.613 | 22,755 |
| `tooling/ui-qa` | 0.492 | 22,006 |
| `.runtime/strategy-references` | 1.583 | 14,681 |

E final scan: **321.185GiB /
656,854 files**,0 lỗi đọc; không purge E.
Các thư mục cấp2 lớn nhất:

| Thư mục E | GiB | File |
|---|---:|---:|
| `workspace/projects` | 98.146 | 140,989 |
| `ai-engine-jobs/challenge-discovery4-20261108` | 38.762 | 138,656 |
| `naqex-migration-20261029/cargo-target` | 19.052 | 17,521 |
| `label-settings-20261029/api-target` | 18.394 | 12,126 |
| `controls-refine-20261024/rust-target` | 15.623 | 10,930 |
| `grid-system-20261025/rust-target` | 14.379 | 10,064 |
| `owner-system-audit-20261031/cargo-target` | 10.734 | 7,664 |
| `dashboard-refine-20261024/rust-target` | 7.827 | 6,083 |

## 2. Lõi dùng chung, tests và hiệu năng

`quant_core/market_data_store.py`: mmap read-only, seek timestamp, SHA256 từng file
generation; reuse binary/offset manifests, không đẻ file mỗi giờ. `ftmo_execution_and_calendar`
gom cửa vào fee/calendar, giữ uncertainty của holiday guards. `prop_lifecycle_and_parity`
reuse V6/V7 harvester/oracle bằng adapter; synthetic replay đã đối soát cash.
**Không rewrite V1–V8 đã seal; không tuyên bố đã xóa mọi duplication lịch sử.**
Core là consumer contract cho lượt sau. Backend lifecycle vẫn fixed fee/risk scenarios;
đổi phí không tự áp vào legacy backend nếu chưa có adapter/parity.

| Kiểm thử | Số test | Giây local |
|---|---:|---:|
| Trước, 4 runtime | 995 | 50.920 |
| Sau, đủ ID và thêm regression | 1012 | 46.711 |
| Fast CI | 278 | 12.216 |
| Historical, các runtime còn lại | 734 | 34.494 |

Không skip, không bỏ995 IDs cũ. Fast chứa mọi module CI cũ; historical là tập bù.
Thời gian sau là tổng các receipt cuối đúng scope; không là một simultaneous capacity test.
Lượt đầu sau purge cache lạnh mất55,70s; lượt warm đầu46,34s. Không giấu chi phí rebuild
cache hoặc coi một mẫu timing là cam kết tốc độ. Shared capture fixture tạo một lần
mỗi class, từng test dùng bản sao writable và kiểm fixture gốc bất biến.

| Top10 module theo tổng thời gian test (không import/class setup) | Trước s | Sau s |
|---|---:|---:|
| `test_shadow_reconcile` | 10.630 | 7.642 |
| `test_forex_study_batch` | 5.013 | 4.427 |
| `test_frozen_source_proof` | 2.631 | 2.562 |
| `test_shadow_night` | 2.166 | 2.113 |
| `test_explicit_m1_view` | 2.054 | 1.886 |
| `test_fx_pair_formation` | 1.900 | 1.847 |
| `test_us500_euopen_component` | 1.830 | 1.727 |
| `test_multiframe_runner_recovery` | 1.616 | 1.591 |
| `test_index_cash_close_tick_component` | 1.554 | 1.491 |
| `test_engine_worker` | 1.169 | 1.130 |

Benchmark16 cặp xen kẽ, cùng28,799 M1 tháng01/2022, parity từng field:
median 4.915ms → 0.502ms
(**9.79×** ở phép seek đã đo). Startup kiểm binary SHA mất
0.291s; không quy9,8× thành tốc độ toàn chiến dịch.

## 3. Alpha: S1/S2 không qua Stage-0 đa chế độ

Dev=2019–20 +2022–23; các năm khác chỉ được đánh giá mới khi candidate đủ Dev.
Toàn2018–2026 đã exposed. Dữ liệu giá mới ở V9 chỉ Dev và warmup trước mỗi cụm;
đọc catalog hoặc hash opaque bytes không là mở outcome validation.

S1: sweep high/low ngày trước vào London, SL extreme4H+0,1ATR trước nến.
DAY và24H là hai exit horizons của cùng entry, không hai alpha độc lập.
S2: ratio Asian width/median20 >1,5 dùng breakout/H4; phần còn lại dùng sweep
quay lại hộp, SL4H. Đây chỉ proxy chế độ, chưa chứng minh macro expansion.

Bảng sau là **raw endpoint markout**, chưa SL-active và chưa account PnL.
Net là USD/oz sau stress SYM; SL là median trước lọc, retention ở cổng15%.
Gold giữ commission0,0007% notional/side, slippage0,20USD/oz/side; swap
SYM−40/−40 và ASYM−45/−5USD/lot/rollover (BUY/SELL),22UTC, thứ Tư×3.
Đây là declared scenarios, không phải biểu phí FTMO live đã xác nhận.

| Gold | Năm | Raw | Nhận | SL USD/oz | Giữ % | Net markout USD/oz |
|---|---:|---:|---:|---:|---:|---:|
| S1.DAY | 2019 | 43 | 7 | 3.224 | 16.3 | -1.0071 |
| S1.DAY | 2020 | 55 | 36 | 6.862 | 65.5 | -0.8734 |
| S1.DAY | 2022 | 51 | 37 | 5.920 | 72.5 | +4.0923 |
| S1.DAY | 2023 | 56 | 31 | 5.347 | 55.4 | -1.1347 |
| S1.24H | 2019 | 43 | 7 | 3.224 | 16.3 | -1.2152 |
| S1.24H | 2020 | 55 | 36 | 6.862 | 65.5 | -0.7723 |
| S1.24H | 2022 | 51 | 37 | 5.920 | 72.5 | +4.0805 |
| S1.24H | 2023 | 56 | 31 | 5.347 | 55.4 | -0.4485 |
| S2.DAY | 2019 | 103 | 33 | 3.819 | 32.0 | -1.3391 |
| S2.DAY | 2020 | 143 | 94 | 7.118 | 65.7 | -0.9459 |
| S2.DAY | 2022 | 161 | 98 | 5.885 | 60.9 | -1.0487 |
| S2.DAY | 2023 | 156 | 84 | 5.627 | 53.8 | +0.5496 |

S1 mở lại phễu2022/23 lên72,5%/55,4%, nhưng2019 chỉ16,3%; markout âm2019/20/23.
Nới phạm vi cấu trúc stop không tạo ra directional edge. S2 cũng âm ở2019/20/22.
Cả hai fail ngay cả tiêu chí tổng dương ở cả hai cụm, không chỉ fail một annual threshold.
Không chọn lại side/horizon/regime threshold hoặc tune bằng validation để cứu.
Gold dùng observed ticks khi có, M1 Bid +Ask proxy0,338 khi thiếu; source conditional
không biến thành execution/prop certificate.973 rows gồm S1 hai horizons trùng entries;
raw signal instances phân biệt là205 S1 và563 S2, không973 alpha độc lập.

Attribution bên trong S2 (không dùng để chọn lại nhánh sau outcome):

| Năm | Regime proxy | Raw | Net USD/oz |
|---|---|---:|---:|
| 2019 | ASIA_EXPANSION | 9 | -4.6837 |
| 2019 | ASIA_NORMAL_SWEEP | 94 | -1.0189 |
| 2020 | ASIA_EXPANSION | 17 | -0.4343 |
| 2020 | ASIA_NORMAL_SWEEP | 126 | -1.0149 |
| 2022 | ASIA_EXPANSION | 17 | -0.9463 |
| 2022 | ASIA_NORMAL_SWEEP | 144 | -1.0608 |
| 2023 | ASIA_EXPANSION | 17 | +2.0971 |
| 2023 | ASIA_NORMAL_SWEEP | 139 | +0.3603 |

Cả expansion lẫn normal đều âm2019/20/22 ở proxy này; không có bằng chứng quy tắc
đã tách được “ngày breakout thật” khỏi “ngày phá giả”. Không suy80% thị trường từ bảng.

EURUSD có local M1/tick đủ Dev; đã export cached Bid M1, không download/update.
Một S2.DAY conditional screen: Ask1pip, commission+slippage9USD/lot stress.
Không giả nguồn Ask là observed, không gọi đây là FTMO live spec.

| EURUSD S2 | Raw/định giá | Nhận | SL pips | Giữ % | Net USD/lot | Raw markout R |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | 156/156 | 88 | 13.65 | 56.4 | -20.42 | -28.00 |
| 2020 | 134/134 | 117 | 20.60 | 87.3 | +8.26 | -12.95 |
| 2022 | 136/136 | 131 | 27.05 | 96.3 | -88.76 | -45.65 |
| 2023 | 136/136 | 115 | 18.75 | 84.6 | -2.18 | -12.90 |

EUR đủ retention, nhưng âm2019/22/23; cả tổng markout R2020 cũng âm dù mean USD/lot
dương vì R chuẩn hóa theo SL khác nhau. Không lẫn hai cách weighting. US500 không có
cached QDM series; nguồn component trước đây chưa admit đủ M1/tick2019–20 cùng
cost/carry/calendar, nên không dựng synthetic raw hoặc tải provider mới để ép đủ bảng.

### Bảng9 năm: chỉ baseline đã có, không mạo nhận V9 mới

V9 không có ứng viên đạt, nên validation và lifecycle candidate bị hủy đúng protocol.
Bảng dưới reuse control V8 fixed150USD; các cột V9=N/A. Không cộng hai lifecycle
2018–21 và2022–26 thành một tài khoản chín năm.

| Năm | Baseline lệnh | SYM NetR | ASYM NetR | V9 |
|---|---:|---:|---:|---|
| 2018 | 84 | -30.9964 | -27.2054 | N/A: fail Dev |
| 2019 | 55 | -13.8519 | -12.6242 | N/A: fail Dev |
| 2020 | 98 | -3.0305 | -2.4709 | N/A: fail Dev |
| 2021 | 106 | -11.9998 | -9.8575 | N/A: fail Dev |
| 2022 | 103 | +4.0499 | +5.9006 | N/A: fail Dev |
| 2023 | 107 | +13.7949 | +16.4619 | N/A: fail Dev |
| 2024 | 98 | +1.8453 | +2.6449 | N/A: fail Dev |
| 2025 | 96 | -0.2847 | -0.1347 | N/A: fail Dev |
| 2026 | 71 | +3.1745 | +3.5321 | N/A: fail Dev |

Baseline lifecycle đã có:0/48 monthly starts hoàn tất hai vòng ở2018–21;
0/57 ở2022–26 mỗi fee model. Các cửa sổ chồng lấn, không future pass probability.
Năm2026 trong bảng chỉ tới13/10/2026, không phải dữ liệu tới ngày báo cáo15/11.
Không có **portfolio V9**, payout V9 hoặc9-year candidate lifecycle mới để báo.
Không tăng risk hoặc ghép các nhánh fail để tạo danh mục có vẻ đạt.

## 4. Workflow, kiểm chứng và lỗi đã giữ

- Anti-bloat CI chặn changed JSON/JSONL/CSV >1MiB/file, >8MiB tổng hoặc>100 files;
  raw/ledger và full storage maps giữ private, tracked JSON chỉ compact summary/pins.
- Maintenance có inventory/purge có preflight, cold archive roundtrip, backup `/L`.
  Không daemon, global config hoặc manager mới.
- Gold:973 entries/1.946 endpoints/3.892 Fraction cost bridges PASS. EUR:562 lệnh/
  1.124 quotes đọc trực tiếp từ CSV PASS. Khác implementation, **cùng implementer**;
  không independent person/model review hoặc Astra.
- Đã kiểm causal prefix, four-bar stop, checksum/tamper, lot/order-cost, holiday,
  synthetic lifecycle/cash, cache protections, archive và absolute snapshot containment.
- V8 development/release exact-byte seals PASS. V7 có newline seals khác trên shared
  source:18 input/code records có exact-byte view riêng; không claim cả V7/V8 raw seals
  cùng bind một working-tree representation. Không sửa frozen pins hoặc numerical content.

Các failed/technical attempts vẫn giữ private: cleanup attempt1 có ancestor scan O(n²),
dừng trước mutation (0 cache mất), thay bằng ancestor set; cleanup sau20,36s. Fixture
class setup lần đầu sai receiver, sửa rồi toàn suite pass. Checkout LF/CRLF có các
strict-hash failures đã giữ; restore chỉ khi exact registered SHA khớp.
Một snapshot attempt ghép absolute source path sai đã ghi lại **cùng bytes** vào4
private JSON inputs; SHA256 cả4 vẫn nguyên. Đã tạo view trong root riêng bằng helper
có containment guard và regression kiểm source mtime/bytes không đổi. Không giấu lỗi này
dưới nhãn read-only. Các attempt/result/seals gốc không được thay hash để ép pass.

Đánh giá: engineering đã có kết quả đo và regression; alpha vẫn NO_GO. Không thể bảo
đảm một workflow đúng sẽ tìm được edge. Chỉ mở cơ chế mới khi có hypothesis/budget mới;
không mua Challenge từ các kết quả này.

Private evidence: `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/system-and-alpha-v9-20261115`. JSON kèm theo giữ source hashes, inventory
locators, top10 timings, benchmark samples, annual controls và từng gate/reason.
Cách dùng: [maintenance](../../tooling/WORKSPACE-MAINTENANCE.md),
[quant core](../../tooling/ai-engines/quant_core/README.md),
[protocol](SYSTEM-AND-ALPHA-V9-PROTOCOL-20261115.md),
[EUR admission](SYSTEM-AND-ALPHA-V9-EURUSD-ADMISSION-20261115.md).
