# V20 — đi vốn O2, dữ liệu thiếu, MT5 shadow và nén evidence

**Hoàn tất phép đo V20; không chọn O2 thay V16/BASE_GUARD, chưa đủ điều kiện Challenge.** Giảm phương sai chưa cải thiện tốc độ qua vòng. Observer mới có bằng chứng replay, chưa có kết nối MT5 thật.

PR98/head `75edaa0` merge `9fba6e0`; nhánh V19 local/remote đã xóa. V20 đăng ký `1cee37d`, financial freeze `2dc7a1d`; PR99 để mở, không merge tự động. Giữ Trader pin, VI WIP, mọi nguồn/freezes/failed attempts. No Astra/broker orders.

## 1. Đi vốn theo phương sai và định vị 32 lệnh thiếu giá

O2 là nghiệm covariance có ràng buộc đã sửa đúng ở V19; không phải heuristic inverse-vol ban đầu bị bác. Giảm phương sai 44,53% không bảo đảm MaxDD giảm cùng tỷ lệ. 8% là mục tiêu nội bộ, khác trần static 10% của hồ sơ quỹ. Yêu cầu cùng DD với V16 và đồng thời dưới 8,2% không được coi là tương đương với công thức hệ số.

Theo công thức khóa trên tất cả tám Dev cases: `k_sigma` = **1,342725**, `k_DD = 8 / 7,9516` = **1,006087**; hệ số cuối **1,006087×**, chỉ thêm khoảng 0,609% risk yêu cầu. Không nâng lên 1,34× để cứu tốc độ. Actual MaxDD phải replay vì minlot/caps/rejects đổi đường vốn.

Unscaled O2 đã có cushion phase1 từ V19. `O2_VOL` tắt cushion để đo scale riêng; `O2_VOL_CUSHION` giữ cushion cũ, không thêm gamma/bonus mới. 1752 Dev accounts audit đầy đủ; unscaled khớp mọi field kinh tế của V19, ngoại trừ tên version. Freeze trước full outcomes; Validation cũ đã exposed.

| Profile Dev | Worst static % | Worst daily % | Worst hai vòng |
|---|---|---|---|
| O2_UNSCALED | 7,9516 | 1,7319 | 0 |
| O2_VOL | 7,9593 | 0,9515 | 0 |
| O2_VOL_CUSHION | 7,9593 | 1,7505 | 0 |

Toàn kỳ2018–13/10/2026; năm2026 chưa đủ năm. 105 mốc bắt đầu chồng lấn; median chỉ trên các cửa sổ hoàn tất. Bảng OLHC; JSON giữ cả OHLC và ba kịch bản nguồn/phí. Không cộng Net R của các mốc tài khoản chồng nhau thành hiệu suất danh mục.

| Profile / source / phí | Hai vòng/105 | Median tháng | Daily % | Static % | Recent hai vòng |
|---|---|---|---|---|---|
| V16 / PRIMARY / 1× | 71 | 47,08 | 1,9630 | 6,3825 | 0/33 |
| O2_UNSCALED / PRIMARY / 1× | 9 | 66,03 | 1,9883 | 5,4588 | 0/33 |
| O2_VOL / PRIMARY / 1× | 11 | 70,50 | 1,1012 | 5,5991 | 0/33 |
| O2_VOL_CUSHION / PRIMARY / 1× | 10 | 65,98 | 1,9959 | 5,5991 | 0/33 |
| O2_UNSCALED / PRIMARY / 1.5× | 4 | 75,46 | 2,0382 | 5,7589 | 0/33 |
| O2_VOL / PRIMARY / 1.5× | 0 | — | 1,1293 | 5,8232 | 0/33 |
| O2_VOL_CUSHION / PRIMARY / 1.5× | 4 | 75,46 | 2,0458 | 5,8232 | 0/33 |
| O2_UNSCALED / STRICT / 1× | 0 | — | 1,8946 | 8,1585 | 0/33 |
| O2_VOL / STRICT / 1× | 0 | — | 1,1012 | 8,1699 | 0/33 |
| O2_VOL_CUSHION / STRICT / 1× | 0 | — | 1,8946 | 8,1699 | 0/33 |

Sổ tham chiếu dùng 150USD × sleeve weight × k rồi lot floor; R dưới đây luôn quy về **150USD**, không đổi mẫu số để giấu tăng size. Cushion/account caps không áp trong unit book, nên hai bản VOL có cùng reference economics; lifecycle table mới xét cushion. Mean-matching của fit tuyến tính không bảo đảm giữ mean sau actual lot-floor/minlot skips.

| Profile / source / phí | Net USD tham chiếu | Net R /150USD | Minlot skips |
|---|---|---|---|
| V16 / PRIMARY / 1× | 6.345,52 | 42,30 | 0 |
| V16 / PRIMARY / 1.5× | 4.299,78 | 28,67 | 0 |
| V16 / STRICT / 1× | -757,11 | -5,05 | 0 |
| O2_UNSCALED / PRIMARY / 1× | 4.644,19 | 30,96 | 5 |
| O2_VOL / PRIMARY / 1× | 4.701,97 | 31,35 | 5 |
| O2_VOL_CUSHION / PRIMARY / 1× | 4.701,97 | 31,35 | 5 |
| O2_UNSCALED / PRIMARY / 1.5× | 3.220,21 | 21,47 | 5 |
| O2_VOL / PRIMARY / 1.5× | 3.268,03 | 21,79 | 5 |
| O2_VOL_CUSHION / PRIMARY / 1.5× | 3.268,03 | 21,79 | 5 |
| O2_UNSCALED / STRICT / 1× | -316,52 | -2,11 | 5 |
| O2_VOL / STRICT / 1× | -279,30 | -1,86 | 5 |
| O2_VOL_CUSHION / STRICT / 1× | -279,30 | -1,86 | 5 |

Cùng 5.000 draws/36 tháng, prefix12/18/24; không chọn lại quý/năm. 60000 new MC ledgers và 1908 full historical ledgers qua oracle toàn bộ, cùng tác giả/feed. New MC chỉ PRIMARY100, cả hai ordering; historical matrix giữ cost/source stress. Tần suất resampling không là xác suất tương lai.

| Bản OLHC PRIMARY100 | Hai vòng12/18/24/36 % | Median khi đậu | Funded riêng USD/năm | Sau Challenge USD/năm |
|---|---|---|---|---|
| V16 | 1,24/6,08/14,32/33,36 | 25,90 | 946,37 | chưa đo trong receipt này |
| O2_UNSCALED | 0,18/0,94/3,28/14,36 | 29,14 | 686,04 | 27,61 |
| O2_VOL | 0,04/0,24/0,98/6,12 | 31,04 | 691,15 | 10,43 |
| O2_VOL_CUSHION | 0,18/0,98/3,44/14,56 | 29,07 | 691,15 | 28,60 |

Payout đều mô phỏng, giữ zeros và chưa trừ phí Challenge/retry/thuế/vận hành. Funded riêng giả định đã Funded từ ngày đầu; khác tiền rút sau hai vòng. Payout thực nhận0.

| Năm | Lệnh chưa xác minh/tổng | Tỷ lệ % | PRIMARY R | STRICT R |
|---|---|---|---|---|
| 2018 | 2/43 | 4,65 | 10,20 | 8,64 |
| 2019 | 2/47 | 4,26 | -1,03 | -2,79 |
| 2020 | 0/57 | 0,00 | 0,17 | 0,17 |
| 2021 | 12/51 | 23,53 | 1,81 | -14,97 |
| 2022 | 4/66 | 6,06 | -4,57 | -10,09 |
| 2023 | 5/76 | 6,58 | 17,27 | 11,10 |
| 2024 | 2/65 | 3,08 | 13,55 | 8,85 |
| 2025 | 2/51 | 3,92 | 1,20 | -7,00 |
| 2026YTD | 3/38 | 7,89 | 3,78 | 1,05 |

| Giai đoạn | Unknown/tổng | PRIMARY R | STRICT R |
|---|---|---|---|
| 2018-2021 | 16/198 | 11,15 | -8,96 |
| 2022-2026YTD | 16/296 | 31,24 | 3,91 |

32 lệnh chia đều16/16 giữa hai giai đoạn; tỷ lệ gần đây thấp hơn nhưng chưa sạch. Chỉ4/32 lệnh thuộc2018–2020; năm2021 nhiều nhất với12 lệnh, nên giả thuyết chủ yếu nằm ở ba năm đầu không được số đếm ủng hộ. Giữ55 gap occurrences riêng, không nhầm với32 trade identities. Không xóa lệnh thiếu hoặc chọn bắt đầu năm2022 từ bảng này; không có quote mới/certificate mới.

## 2. MT5 read-only / shadow và quickstart

[Ba bước chạy](QUICKSTART-FTMO-FREE-TRIAL.md). Runtime observer riêng đã cài/khóa MetaTrader5, pyarrow, zstandard, NumPy/tzdata; smoke-test imports và Parquet roundtrip. Không có terminal64.exe đang chạy ở probe; **chưa attach tài khoản FTMO thật**.

`python -m tooling.ai_engines.ftmo_trial_runner --mode read-only` và `--mode shadow-paper` dùng cùng implementation hiện có. Không có terminal thì replay được gắn nhãn, không ngầm gọi là live. CLI có spec snapshot năm asset, parity diff, timestamped Parquet zstd9, quote/receive clocks và shadow ledger/journal. Account phải DEMO/TRIAL USD đúng FTMO; không login/restart/order_send/order_check.

Replay mặc định có intent fixture. Thêm replay Development sinh tín hiệu thật từ 23.857 H1 đã đóng: guard chặn khi SL không thuộc tick-grid0,01; giữ failed attempt. Fixture grid nghiên cứu0,001 sau đó có một entry paper, không thay SL hay khẳng định broker dùng grid0,001. Đây là M1 OLHC scenario, không tick broker quan sát. Vị thế paper còn mở được giữ trong ledger khi process kết thúc, không ép đóng lấy số đẹp.

Session APIs đầy đủ cần MQL5 export bridge; exporter chưa compile/chạy trên terminal. Thiếu session/timezone/holiday/news/seed parity thì native shadow chặn, không suy unknown là phiên an toàn. Spec của ba asset ngoài danh mục chỉ được ghi nhận, không tự trade. MFE/MAE từ quote đã thấy; quote-only không đo slippage. Chưa EA/broker readiness.

## 3. Nén giữ nguyên bằng chứng V19

Nén **51 files** JSON/JSONL/NPY bằng Zstandard9: 1,508GiB → 0,102GiB; payload giảm **1,407GiB**. Mọi bản gốc/bản nén có SHA256; giải nén kiểm100% byte trước unlink, preflight toàn bộ original identities/hashes trước xóa. Chỉ apply sau khi financial readers đã xong.

MANIFEST và APPLIED receipt ở private V19 job/evidence-zstd-v20. New reader đọc JSON/NPY trực tiếp từ archive và trả canonical original SHA. Legacy frozen consumer cần đường file gốc có lệnh restore chính xác; không sửa source pinned hoặc xóa negative attempts. Test corruption, scope escape, drift, collision, hash và numpy dtype/values đều giữ.

| Kho | Trước GiB | Sau GiB | Delta GiB | Delta files | Lỗi trước/sau |
|---|---|---|---|---|---|
| D | 197,380 | 197,377 | -0,002 | -636 | 2/2 |
| E | 216,653 | 215,362 | -1,291 | 210 | 0/0 |

Snapshot toàn kho bao gồm runtime/evidence V20 mới, khác payload tiết kiệm riêng V19. Không gọi delta logical/non-atomic là physical bytes freed; giữ lỗi đọc VI và WIP.

## 4. Full suite, smoke và bàn giao

Full suite **1239 PASS/0skip**, giữ đủ **1.216 V19 IDs**, wall **13,437s**; target<16s: **đạt**. Năm runtime groups overlap; base giữ bốn worker. Workload có regression mới, không gọi đây là tốc độ whole-machine hay cùng một bài backtest9năm.

Smoke đúng10 fresh serial processes/cùng78IDs: **10/10 <0,78s**, median **0,655s**, max **0,680s**. Target10/10: **đạt**; median0,55–0,65s: **chưa đạt**. Giữ mọi mẫu, không retry chọn streak; startup/import/fixture IO vẫn trong wall.

Runner thực là unittest, không pytest plugin. cProfile/importtime chỉ ra import filesystem probes và fixture IO; không đủ trace để quy chính xác mọi jitter cho GC/AV/disk. Index chỉ các module local đã ưu tiên, vẫn SourceFileLoader/source/pyc cũ; không đổi assertions hoặc prewarm ngoài timer. Paired diagnostic, temp-root và -S thử nghiệm giữ riêng; -S không được dùng trong final benchmark. Fixture vẫn tạo/đọc/xóa trên đĩa thật.

Lượt smoke đầu dừng tại lần4/10: corruption test dùng same-size overwrite quá nhanh trên Windows vẫn có cùng mtime. Probe30 files có25 lần cùng timestamp và25 cache hits không phát hiện sửa. Fixture mới khai báo generation bằng mtime khác rõ ràng, giữ assertion checksum mismatch và cache reuse. Không đổi Checksums hay financial source; cache vẫn giả định inputs immutable, không bảo vệ sửa nội dung giữ nguyên metadata. Giữ failed logs tại job gốc; full/smoke sau sửa nằm trong `test-recovery-v2`, không lựa chọn lượt nhanh nhất giữa các attempts.

| Hậu kiểm | Quyết định / bằng chứng |
|---|---|
| Variance giảm nhưng DD không giảm tương ứng | Giữ k theo formula; không ép1,34×, không promote O2 |
| Session APIs SDK thiếu | Export bridge + unknown-blocking; native acceptance còn mở |
| Metadata timestamp làm corruption test không xác định | Fixture generation xác định; giữ cache limitation/failed attempt |
| Evidence V19 lớn | Zstd9, SHA/roundtrip/restore trước unlink; không xóa nguồn giá |

PR99 để mở; exact-head3CI/downloaded IDs chốt trong private `ci-exact-head-reconciliation.json` và `completion-receipt.json` sau push, không sửa HEAD để tự đóng dấu. Không có Challenge purchase, account reset, broker order hoặc triển khai sản phẩm.

[JSON](VOLTARGET-SHADOW-V20-RESULTS-20261117.json) · private job `E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\voltarget-shadow-v20-20261117`.
