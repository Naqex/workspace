# Đính chính Lịch Tin Đỏ 2025, Nguồn T1 6 Đồng Tiền (2018–2024) & Bộ Nạp Thống Nhất SSOT

- **Ngày lập:** `2026-11-27`
- **Phạm vi:** Chuẩn hóa Single Source of Truth (SSOT) cho lịch tin đỏ `6` đồng tiền (`USD, GBP, EUR, JPY, AUD, CAD`), ghi nhận sai lệch năm `2025` trên tệp đóng băng, xác minh `100%` mốc live tháng `12/2026`, và xây dựng lịch Dev `2018–2024` xác minh nguồn gốc cấp `T1` (`OrderSend = 0`, `Holdout 2025+ SEALED`, Layer-1 không chứa bí mật hay địa chỉ máy cá nhân).
- **Tệp sản xuất giữ BẤT BIẾN (không chỉnh sửa):**
  - [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) (`492` sự kiện, chỉ dùng ký tự xuống dòng `LF`, SHA-256 `235722ed1821499f8d81b169418486d3a8b9c0e8911857c88fea8d2270d3dff7`)
  - [red_news_official_2025_2026.json](../../tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json) (`31` sự kiện `2025` + `32` sự kiện `2026`)
  - [red_news_official_2018_2024.json](../../tooling/ai-engines/configs/calendars/red_news_official_2018_2024.json) (`224` sự kiện USD Dev)
- **Tệp mới ban hành:**
  - [red_news.py](../../tooling/ai-engines/quant_core/red_news.py) — bộ nạp lịch thống nhất (xóa triệt để lỗi `KeyError`) và bộ cảnh báo chênh lệch phủ sóng `BACKTEST_USD32_VS_LIVE140_GAP`.
  - [red_news_official_2018_2024_6ccy.json](../../tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json) — lịch Dev `2018–2024` gồm `523` sự kiện `VERIFIED_T1` trên đủ `6` đồng tiền + danh sách `9` khoảng trống `unverified_gaps` công khai.
  - [test_red_news_ssot.py](../../tooling/ai-engines/tests/test_red_news_ssot.py) — bộ kiểm thử tự động xác minh cả `4` tệp JSON, cảnh báo `BACKTEST_USD32_VS_LIVE140_GAP`, tính bất biến của CSV sống và quy tắc kiểm tra dữ liệu fail-closed.

---

## 1. Sự cố đóng cửa Chính phủ Mỹ (01/10–12/11/2025) & việc BLS hủy CPI tháng 10/2025

Do tình trạng gián đoạn ngân sách liên bang Mỹ (**US federal government shutdown**) kéo dài từ **`01/10/2025` đến `12/11/2025`**, Cục Thống kê Lao động Mỹ (**BLS** — `bls.gov`) đã buộc phải hủy và dời hàng loạt bản tin vĩ mô cốt lõi cuối năm `2025`:

1. **Hủy hoàn toàn bản tin US CPI tháng 10/2025 (lẽ ra phát hành giữa tháng 11/2025):** BLS chính thức xác nhận không phát hành bản tin CPI toàn phần lẫn CPI lõi cho kỳ tháng `10/2025` vì hoạt động khảo sát giá bị gián đoạn trong thời gian đóng cửa và không thể thu thập hồi tố. Các chỉ số thay đổi `12` tháng phụ thuộc mốc nền tháng `10/2025` cũng bị bỏ trống trong báo cáo sau đó.
   - **Quy tắc dữ liệu bắt buộc:** **Tuyệt đối không được tự thêm hay bịa một sự kiện US CPI trong tháng `11/2025`**. Việc năm `2025` chỉ có `11` lần công bố CPI (`09/2025` công bố ngoại lệ ngày `24/10/2025` để phục vụ tính COLA An sinh Xã hội; `11/2025` công bố ngày `18/12/2025`) là **đúng với lịch sử thực tế của BLS**.
2. **Hủy hoàn toàn bản tin độc lập US Employment Situation (NFP) tháng 10/2025 (lẽ ra phát hành ngày `07/11/2025`):** Dữ liệu khảo sát hộ gia đình (*Current Population Survey*) cho kỳ tháng `10/2025` không thể thu thập hồi tố; tỷ lệ thất nghiệp tháng `10/2025` bị bỏ trống vĩnh viễn. Riêng dữ liệu khảo sát bảng lương cơ sở (*Current Employment Statistics*) tháng `10/2025` được BLS gộp công bố chung trong bản tin NFP tháng `11/2025` vào ngày `16/12/2025`.
3. **Dời mạnh lịch công bố NFP tháng `09/2025` và `11/2025`:** Bản tin NFP tháng `09/2025` (dự kiến `03/10/2025`) bị dời `48` ngày sang **`20/11/2025` (`13:30 UTC`)**; bản tin NFP tháng `11/2025` (dự kiến `05/12/2025`) bị dời `11` ngày sang **`16/12/2025` (`13:30 UTC`)**.

---

## 2. Bảng đính chính 9 ngày sai trong năm 2025 của tệp đóng băng `red_news_official_2025_2026.json`

Đối chiếu toàn bộ `31` dòng năm `2025` trong tệp đóng băng [red_news_official_2025_2026.json](../../tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json) với kho lưu trữ chính thức của BLS (`bls.gov/schedule/news_release/empsit.htm`, `bls.gov/schedule/news_release/cpi.htm` và chuỗi phát hành lịch sử FRED/BLS) cho thấy **`9` ngày sai** (toàn bộ `8` kỳ FOMC năm `2025`, `24/10/2025` CPI và `18/12/2025` CPI đều chính xác):

| STT | Sự kiện | Ngày trong tệp đóng băng (`2025_2026.json`) | Ngày thực tế theo BLS (`T1`) | Giờ thực tế (`UTC`) | Nguyên nhân sai lệch |
|---:|---|---|---|---|---|
| 1 | `US_NFP` (dữ liệu `12/2024`) | `2025-01-03` | **`2025-01-10`** | `13:30:00Z` | BLS xếp Thứ Sáu tuần thứ hai do `03/01` sát Tết Dương lịch |
| 2 | `US_CPI` (dữ liệu `12/2024`) | `2025-01-14` | **`2025-01-15`** | `13:30:00Z` | Lệch 1 ngày so với lịch công bố chính thức BLS |
| 3 | `US_NFP` (dữ liệu `06/2025`) | `2025-07-04` | **`2025-07-03`** | `12:30:00Z` | `04/07` là Lễ Quốc khánh Mỹ (Independence Day), BLS đẩy sớm sang Thứ Năm |
| 4 | `US_CPI` (dữ liệu `06/2025`) | `2025-07-11` | **`2025-07-15`** | `12:30:00Z` | Lệch 4 ngày so với lịch công bố chính thức BLS |
| 5 | `US_CPI` (dữ liệu `07/2025`) | `2025-08-13` | **`2025-08-12`** | `12:30:00Z` | Lệch 1 ngày so với lịch công bố chính thức BLS |
| 6 | `US_CPI` (dữ liệu `08/2025`) | `2025-09-10` | **`2025-09-11`** | `12:30:00Z` | Lệch 1 ngày so với lịch công bố chính thức BLS |
| 7 | `US_NFP` (dữ liệu `09/2025`) | `2025-10-03` | **`2025-11-20`** | `13:30:00Z` | Dời `48` ngày do Chính phủ Mỹ đóng cửa `01/10–12/11/2025` |
| 8 | `US_NFP` (dữ liệu `10/2025`) | `2025-11-07` | **HỦY BỎ (`CANCELLED`)** | *Không phát hành* | BLS hủy bản tin độc lập tháng `10/2025` do gián đoạn khảo sát hộ gia đình |
| 9 | `US_NFP` (dữ liệu `11/2025`) | `2025-12-05` | **`2025-12-16`** | `13:30:00Z` | Dời `11` ngày để kéo dài thời gian thu thập hậu đóng cửa (gộp bảng lương cơ sở tháng 10) |

---

## 3. Xác nhận 100% chính xác các mốc giao dịch sống tháng 12/2026

Kiểm tra chéo trực tiếp với lịch phát hành chính thức năm `2026` của BLS (`bls.gov`) và Cục Dự trữ Liên bang Mỹ (`federalreserve.gov`) xác nhận các mốc tin đỏ tháng `12/2026` đang chạy trên hệ thống sống là **CHÍNH XÁC 100%**:

- **US NFP (dữ liệu `11/2026`):** `2026-12-04T13:30:00Z` (`08:30 EST`, `utc_ts = 1796391000`, mã `US_NFP`) — **CHÍNH XÁC 100%**.
- **FOMC quyết định lãi suất:** `2026-12-09T19:00:00Z` (`14:00 EST`, `utc_ts = 1796842800`, mã `FOMC`, kèm họp báo `19:30:00Z`) — **CHÍNH XÁC 100%**.
- **US CPI (dữ liệu `11/2026`):** `2026-12-10T13:30:00Z` (`08:30 EST`, `utc_ts = 1796909400`, mã `US_CPI`) — **CHÍNH XÁC 100%**.

Cả hai mốc `2026-12-04` (`US_NFP`) và `2026-12-10` (`US_CPI`) đã được bảo vệ bằng cổng kiểm tra tự động trong [nfp_cpi_quote_collector.py](../../tooling/ai-engines/ops_cloud/nfp_cpi_quote_collector.py) và [test_nfp_cpi_quote_collector.py](../../tooling/ai-engines/tests/test_nfp_cpi_quote_collector.py).

---

## 4. Vì sao `naqex_red_news_utc.csv` và `red_news_official_2025_2026.json` phải giữ BẤT BIẾN

1. **Khóa SHA-256 trên gói triển khai sống:** Tệp [naqex_red_news_utc.csv](../../tooling/ai-engines/exports/Files/naqex_red_news_utc.csv) (`492` sự kiện, chỉ `LF`, SHA-256 `235722ed1821499f8d81b169418486d3a8b9c0e8911857c88fea8d2270d3dff7`) và tệp metadata [naqex_red_news_meta.json](../../tooling/ai-engines/exports/Files/naqex_red_news_meta.json) đang được khóa đối chiếu trực tiếp với máy chủ chạy bot (`naqex-node1`) qua [node_cutover_dryrun.py](../../tooling/ai-engines/ops_cloud/node_cutover_dryrun.py), [mql5_parity_checker.py](../../tooling/ai-engines/exports/mql5_parity_checker.py) và [build_red_news_calendar.py](../../tooling/ai-engines/quant_factory/build_red_news_calendar.py).
2. **Bảo toàn bằng chứng kiểm thử Holdout & 3 bộ test khóa cứng:** Tệp [red_news_official_2025_2026.json](../../tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json) được bảo vệ bởi [test_holdout_and_tca_guards.py](../../tooling/ai-engines/tests/test_holdout_and_tca_guards.py), [test_red_team_and_ops.py](../../tooling/ai-engines/tests/test_red_team_and_ops.py) và [test_nfp_cpi_quote_collector.py](../../tooling/ai-engines/tests/test_nfp_cpi_quote_collector.py). Mọi sửa đổi trực tiếp sẽ phá vỡ tính tái lập của bằng chứng Holdout lịch sử.
3. **Không gây rủi ro cho vận hành live hiện tại:** Cả `9` ngày sai năm `2025` đều đã nằm hoàn toàn trong quá khứ; phần lịch sống `2026–2027` (`97` sự kiện năm `2026` + `140` sự kiện năm `2027` phủ đủ `6` đồng tiền) đã được đối chiếu và xác nhận chính xác. Vì vậy, hướng xử lý an toàn nhất là giữ nguyên bất biến hai tệp đang đóng băng, ghi nhận đính chính công khai tại tài liệu này, và dùng bộ nạp SSOT mới cùng lịch `6` đồng tiền `2018–2024` cho nghiên cứu và đối chứng mới.

---

## 5. Tổng hợp phủ sóng T1 & `unverified_gaps` của `red_news_official_2018_2024_6ccy.json`

### 5.1. Đóng lỗi `KeyError` & cảnh báo chênh lệch Dev `32`/năm vs Live `97–140`/năm

Bộ nạp cũ (`quant_factory/data_store.py`) truy cập cứng khóa `raw["events_by_day"]` nên văng `KeyError` ngay khi mở các tệp lịch đa tiền tệ mới dùng mảng `events: [...]`. Mô-đun mới [red_news.py](../../tooling/ai-engines/quant_core/red_news.py) giải quyết dứt điểm qua:

- `load_calendar_events(path)`: nạp thống nhất cả `4` tệp JSON (`events_by_day` và `events`) lẫn CSV `3` cột, kiểm tra nghiêm ngặt chuẩn UTC ISO-8601 (`Z` / `+00:00`), `6` đồng tiền hợp lệ, cửa sổ cấm giao dịch hữu hạn dương (`blackout_sec > 0`), và trường xác minh T1 (`source_agency`, `source_url`, `verification_status`).
- `get_calendar_coverage_report(dev_cal, live_csv)`: tự động thống kê số sự kiện theo từng đồng tiền / từng năm và phát cờ cảnh báo bắt buộc **`BACKTEST_USD32_VS_LIVE140_GAP`** bất cứ khi nào bộ backtest Dev chỉ dùng lịch USD (`<= 35` sự kiện/năm) so với lịch Live đa tiền tệ (`97–140` sự kiện/năm).

### 5.2. Độ phủ T1 của lịch Dev 6 đồng tiền `2018–2024` (`523` sự kiện `VERIFIED_T1`)

Mọi sự kiện đưa vào [red_news_official_2018_2024_6ccy.json](../../tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json) đều mang đầy đủ `source_agency`, `source_url`, `verification_status: "VERIFIED_T1"`, `blackout_sec`, và đã đối chiếu hai lớp giữa `ZoneInfo` và `compute_utc_ts` (`0` sai lệch DST, `0` sự kiện cuối tuần, `0` cặp `(utc_ts, ccy)` trùng lặp):

| Đồng tiền | Cơ quan nguồn `T1` | Số sự kiện (`2018–2024`) | Cửa sổ cấm (`blackout_sec`) | Mốc lịch & quy tắc giờ địa phương đã xác minh `T1` |
|---|---|---:|---:|---|
| `USD` | BLS & Federal Reserve (`bls.gov`, `federalreserve.gov`) | `224` (`32`/năm) | `300s` (`±5m`) | Bảo toàn **`100%` nguyên trạng** `224` mốc `utc_ts` từ `red_news_official_2018_2024.json` (`12` NFP + `12` CPI lúc `08:30 ET`, `8` FOMC lúc `14:00 ET`). |
| `EUR` | European Central Bank (`ecb.europa.eu`) | `56` (`8`/năm) | `300s` (`±5m`) | **`13:45` Frankfurt (`CET/CEST`)** đến hết `09/06/2022`; chính thức đổi sang **`14:15` Frankfurt** từ **`21/07/2022`** (gồm kỳ Thứ Tư `10/04/2019`). |
| `GBP` | Bank of England MPC (`bankofengland.co.uk`) | `56` (`8`/năm) | `300s` (`±5m`) | Chuẩn **`12:00` London (`GMT/BST`)**; ngoại lệ **`07:00` London** được xác minh trực tiếp cho `07/05/2020`, `06/08/2020`, `05/11/2020`; dời `15/09/2022 -> 22/09/2022` (quốc tang Nữ hoàng Elizabeth II). |
| `JPY` | Bank of Japan (`boj.or.jp`) | `57` (`8`/năm; `2020`: `9`) | **`3600s` (`±60m`)** | Đã xác minh toàn bộ lịch họp `mpo_2018..2024.htm` gồm các đợt điều chỉnh đại dịch `2020` (`16/03`, `27/04`, `22/05`, `15/07`). Do BoJ không cố định phút (`~11:30–12:30 JST`), neo `12:00 JST (03:00Z)` và nới cửa sổ cấm `±3600s` khớp `naqex_red_news_meta.json`. |
| `AUD` | Reserve Bank of Australia (`rba.gov.au`) | `74` (`11`/năm `2018–2023`; `8` năm `2024`) | `300s` (`±5m`) | **`14:30` Sydney (`AEST/AEDT`)**; Thứ Ba đầu tiên của tháng `02–12` giai đoạn `2018–2023` (đã xác minh `03/04/2018` chứ không phải `10/04/2018`); cải cách còn `8` kỳ từ `2024`. |
| `CAD` | Bank of Canada (`bankofcanada.ca`) | `56` (`8`/năm) | `300s` (`±5m`) | **`10:00` Toronto (`ET`)** trong suốt `2018–2023`; chính thức đổi sang **`09:45` Toronto** từ **`24/01/2024`**. |
| **Tổng cộng** | **6 NHTW / Cơ quan thống kê `T1`** | **`523`** (`72–76`/năm) | `300s` / `3600s` | Giảm hẳn khoảng cách phủ sóng so với `32`/năm USD-only; gỡ cờ `BACKTEST_USD32_VS_LIVE140_GAP`, chuyển sang ghi nhận minh bạch `DEV_6CCY_MISSING_NON_CB_MACRO_SERIES` (`53,4%` so với đỉnh `140`/năm của Live `2027`). |

### 5.3. Danh sách `9` khoảng trống `unverified_gaps` còn lại (tuyệt đối không đoán giờ)

Để giữ nguyên tắc **không bịa mốc thời gian chưa xác minh `T1`**, mọi chuỗi hoặc sự kiện bất thường chưa có giờ-phút công bố xác nhận trực tiếp từ nguồn chính thức được khai báo minh bạch trong mảng `unverified_gaps` của `red_news_official_2018_2024_6ccy.json`:

1. **`JPY` — Phút công bố nội nhật chính xác của BoJ (`2018–2024`):** BoJ công bố ngay khi kết thúc phiên họp (`~11:30–12:30 JST`), không có phút ấn định trước; đã bù đắp an toàn bằng cửa sổ `±3600s` quanh `03:00:00Z`.
2. **`USD` — `2` đợt cắt lãi suất khẩn cấp COVID-19 của Fed (`2020-03-03`, `2020-03-15`):** Không nằm trong bộ đóng băng `224` sự kiện USD cũ và chưa bổ sung bản lưu phút phát hành `T1`.
3. **`GBP` — `2` đợt cắt lãi suất khẩn cấp COVID-19 của BoE (`2020-03-11`, `2020-03-19`):** Đã xác minh ngày họp trên `bankofengland.co.uk`, nhưng phút phát hành chính xác không in trực tiếp trên trang tóm tắt lưu trữ `T1`.
4. **`EUR` — Thông báo gói PEPP bất thường buổi tối của ECB (`2020-03-18`):** Đã xác minh ngày trên `ecb.europa.eu`, chưa xác minh trực tiếp phút phát hành UTC.
5. **`AUD` — Quyết định gói khẩn cấp COVID-19 của RBA (`2020-03-19`, Media Release `2020-08`):** Đã xác minh ngày và giờ họp báo `16:00 AEDT` trên `rba.gov.au`, nhưng phút phát hành thông cáo báo chí không ghi rõ trên trang lưu trữ.
6. **`CAD` — `2` đợt cắt lãi suất khẩn cấp COVID-19 của BoC (`2020-03-13`, `2020-03-27`):** Đã xác minh ngày trên `bankofcanada.ca`, chưa xác minh trực tiếp phút phát hành từ bản tóm tắt.
7. **`USD` — Nhóm tin vĩ mô Mỹ ngoài NFP/CPI/FOMC (`2018–2024`):** US PPI (`bls.gov`), US Retail Sales (`census.gov`), US GDP & Core PCE (`bea.gov`), họp báo FOMC và biên bản FOMC (`federalreserve.gov`) — đã có trong lịch sống `2026–2027`, chờ một đợt truy hồi lịch sử `T1` riêng nếu cần nâng Dev từ `75`/năm lên `~140`/năm.
8. **`GBP` — Chỉ số lạm phát Anh UK CPI (`2018–2024`, `ons.gov.uk`):** Đã có `12`/năm trong lịch sống `2027`, chưa truy hồi xác minh từng kỳ `2018–2024`.
9. **`EUR` — Họp báo ECB (`2018–2024`, `ecb.europa.eu`):** Đã có trong lịch sống `2026–2027`; tạm để trống phần họp báo (mốc quyết định lãi suất đã được khóa trước đó `30–45` phút) chờ xác minh đầy đủ ngoại lệ từng phiên.
