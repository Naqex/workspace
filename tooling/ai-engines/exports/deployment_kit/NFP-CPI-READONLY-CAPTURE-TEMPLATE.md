# Mẫu Thu Thập Dữ Liệu Chỉ Đọc Quanh Tin Đỏ US NFP & US CPI (`OrderSend = 0`)

> **Mục đích:** Quy trình và biểu mẫu thu thập dữ liệu giá thực địa ở chế độ **chỉ đọc tuyệt đối (`OrderSend = 0`)** trên tài khoản **`FTMO-Demo (<DEMO_ID>)`** cho hai sự kiện tin đỏ lớn nhất tháng 12/2026:
> - **US NFP (Non-Farm Payrolls):** Thứ Sáu **`04/12/2026` lúc `20:30` giờ VN (`13:30:00 UTC`, `utc_ts = 1796391000`, mã sự kiện `US_NFP`)**.
> - **US CPI (Consumer Price Index):** Thứ Năm **`10/12/2026` lúc `20:30` giờ VN (`13:30:00 UTC`, `utc_ts = 1796909400`, mã sự kiện `US_CPI`)**.
>
> **Khóa an toàn bắt buộc:** `OrderSend = 0`, `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`), không mở/đóng lệnh trong cửa sổ đo, không chạm vào tài khoản chính hoặc tài khoản trả phí, không lưu thông tin đăng nhập, mật khẩu, IP nội bộ hay bí mật vào tệp Layer-1.

---

## 1. Phân tách rạch ròi giữa `QUOTE_ONLY` và `FILL_VERIFIED`

Để tránh tuyệt đối nhầm lẫn giữa **biến động giá chào (quote)** và **trượt giá khớp lệnh thật (execution slippage)** — bài học rút ra trực tiếp từ đợt kiểm tra `28` vòng lệnh ngày `25/11/2026` (khi `2` lệnh chạm SL trên `US100.cash` bị thiếu mốc thời gian khớp mili-giây và bị khoảng mù quét `5.000 ms` nên phải chốt **`KHÔNG TÁCH ĐƯỢC` / `UNSEPARABLE_MISSING_TRIGGER_QUOTE`**) — mọi bản ghi phải gắn nhãn tầng bằng chứng rõ ràng:

| Tầng bằng chứng (`record_tier`) | Phạm vi cho phép trong mẫu này | Dữ liệu được thu thập | Kết luận ĐƯỢC phép rút ra | Kết luận BỊ CẤM suy diễn |
|---|---|---|---|---|
| **`QUOTE_ONLY`** | **CHẾ ĐỘ CHÍNH (`OrderSend = 0`)** | Luồng giá Bid/Ask từng tick (`CopyTicksRange` theo `time_msc`), độ giãn spread (`spread_pts`, `spread_bps`), bước nhảy giá giữa hai tick liên tiếp và trong `1` giây (`13:25..13:45 UTC`), độ trễ im lặng giữa hai tick (`inter_tick_gap_ms`). | Đo mức giãn spread cực đại, biên độ nhảy quote dưới `1` giây, thời gian hồi phục spread sau tin đỏ trên feed `FTMO-Demo`. | **KHÔNG** kết luận giá khớp SL thực tế phía máy chủ, **KHÔNG** tuyên bố đã đo được trượt khớp lệnh thật. |
| **`FILL_VERIFIED`** | **KHÓA (`0` dòng trong đợt chỉ đọc này)** | Chỉ tạo ra ở phiên riêng có cấp quyền mở lệnh và có đủ bộ đôi: `deal_time_msc` từ lịch sử giao dịch broker + luồng tick liên tục có `trigger_tick_time_msc` khớp trong `<= 250 ms` quanh mốc kích hoạt. | Mới đủ điều kiện tách riêng `market_overshoot_pts` (thị trường nhảy qua giá SL) và `broker_exec_slip_pts` (trượt khớp nội bộ sau khi chạm SL). | Nếu thiếu `deal_time_msc` hoặc có lỗ hổng tick `> 250 ms`, **bắt buộc** hạ nhãn thành `UNSEPARABLE_MISSING_TRIGGER_QUOTE` (`KHÔNG TÁCH ĐƯỢC`). |

---

## 2. Cấu hình cửa sổ đo & danh mục mã theo dõi

- **Cửa sổ thu thập tiêu chuẩn (`20` phút / sự kiện):**
  - `PRE_EVENT` (nền trước tin): **`13:25:00 .. 13:29:30 UTC`** (`20:25:00 .. 20:29:30 ICT`).
  - `IMPACT_CORE` (lõi ra tin, ưu tiên lấy đủ mọi tick qua `CopyTicksRange`, không bỏ sót mili-giây nào): **`13:29:30 .. 13:35:00 UTC`** (`20:29:30 .. 20:35:00 ICT`).
  - `POST_NORMALIZE` (theo dõi spread hồi phục về nền): **`13:35:00 .. 13:45:00 UTC`** (`20:35:00 .. 20:45:00 ICT`).
- **Nhóm `4` mã cốt lõi `7E` (bắt buộc):** `US100.cash`, `USDJPY`, `GBPUSD`, `EURJPY`.
- **Nhóm `4` mã tín hiệu phụ trợ (khuyến nghị bật cùng nếu đủ băng thông):** `US500.cash`, `EURUSD`, `AUDUSD`, `USDCAD`.
- **Nơi lưu tệp kết quả thô:** Chỉ lưu trong vùng cục bộ ngoài Git (ví dụ `private_vault/telemetry/nfp-cpi-202612/` hoặc `.runtime/live-overnight/`), **tuyệt đối không** đưa dữ liệu chứa mã tài khoản thật vào Git Layer-1.

---

## 3. Danh sách kiểm tra trước sự kiện (`T-30` phút đến `T-5` phút)

Thực hiện đầy đủ tất cả các mục dưới đây trước `13:25:00 UTC` (`20:25:00 ICT`). Nếu bất kỳ mục khóa an toàn nào không đạt, **dừng thu thập và xử lý trước**, không chạy chắp vá:

- [ ] **Đồng bộ đồng hồ hệ thống (`NTP < 1,0 s`, mục tiêu `< 100 ms`):** Kiểm tra độ lệch đồng hồ máy đo so với chuẩn `NTP` (ví dụ `w32tm /stripchart /computer:time.cloudflare.com /samples:5 /dataonly` hoặc tương đương) và ghi lại `ntp_offset_ms` trước giờ ra tin.
- [ ] **Khóa cứng chỉ đọc (`OrderSend = 0`):** Xác nhận tiến trình thu thập chỉ gọi API đọc quote (`CopyTicksRange` / `symbol_info_tick`), **không** bật Algo Trading (`[Experts] Enabled=0`, `AllowLiveTrading=0`), hoặc nếu gắn EA quan sát thì cả `InpDryRunLogOnly = true` và `InpGuardDryRunLogOnly = true`.
- [ ] **Xác nhận đúng tài khoản Demo cô lập:** Kiểm tra góc trên MT5 đúng máy chủ **`FTMO-Demo`** và đúng mã **`<DEMO_ID>`** (tài khoản Demo phụ dành cho đo đạc; **không** dùng tài khoản Demo chạy chiến lược chính và **không** dùng tài khoản trả phí).
- [ ] **Xác nhận tài khoản đo phẳng lệnh `100%`:** `positions_total = 0`, `orders_total = 0` trước `13:25 UTC` để chắc chắn không có vị thế nào dính vào giờ tin đỏ.
- [ ] **Kiểm tra trạng thái kết nối & Market Watch:** `terminal_connected = true`, đủ `4` mã cốt lõi (`US100.cash`, `USDJPY`, `GBPUSD`, `EURJPY`) và `4` mã phụ trợ (`US500.cash`, `EURUSD`, `AUDUSD`, `USDCAD`) đang cập nhật bid/ask tươi (`age < 2 s`).
- [ ] **Kiểm tra khớp lịch tin đỏ `naqex_red_news_utc.csv`:** Xác nhận mốc `1796391000,USD,US_NFP` (`04/12/2026 13:30 UTC`) và `1796909400,USD,US_CPI` (`10/12/2026 13:30 UTC`) có mặt đúng trong lịch tin đỏ, và kiểm chứng thực tế trên log rằng bộ lọc `±300s` / cấm cứng `±135s` hoạt động đúng.
- [ ] **Kiểm tra dung lượng lưu trữ & thư mục đích:** Ổ đĩa còn trống `>= 500 MB`, tệp CSV đầu ra trỏ vào thư mục ngoài Git (`private_vault/` hoặc `.runtime/`).

---

## 4. Cấu trúc cột CSV chuẩn (Exact CSV Column Schema)

### 4.1. Tệp luồng tick chỉ đọc — `nfp_cpi_quote_ticks_<EVENT_ID>.csv` (`record_tier = QUOTE_ONLY`)

Bắt buộc ghi đủ `23` cột theo đúng thứ tự dưới đây (mã hóa `UTF-8`, dấu phẩy `,`, không đổi tên cột):

```csv
record_tier,event_id,utc_ts_ms,utc_iso_ms,server_tick_msc,local_recv_msc,ntp_offset_ms,account_alias,server,symbol,bid,ask,mid,spread_pts,spread_bps,point,tick_flags,delta_bid_pts,delta_ask_pts,inter_tick_gap_ms,seconds_from_release,window_phase,order_send_count
```

| Tên cột | Kiểu dữ liệu | Đơn vị / Quy ước | Ý nghĩa kỹ thuật |
|---|---|---|---|
| `record_tier` | `string` | Cố định `QUOTE_ONLY` | Khẳng định đây là dữ liệu giá chào, không phải dữ liệu khớp lệnh. |
| `event_id` | `string` | `US_NFP_20261204` hoặc `US_CPI_20261210` | Mã định danh sự kiện tin đỏ. |
| `utc_ts_ms` | `int64` | Mili-giây UTC (epoch ms) | Mốc thời gian chuẩn hóa UTC của tick (suy từ `server_tick_msc` trừ độ lệch giờ máy chủ FTMO, hoặc `local_recv_msc` có ghi chú). |
| `utc_iso_ms` | `string` | `YYYY-MM-DDTHH:MM:SS.mmmZ` | Chuỗi thời gian UTC đầy đủ tới mili-giây (`3` chữ số thập phân). |
| `server_tick_msc` | `int64` | Mili-giây máy chủ MT5 | Giá trị `MqlTick.time_msc` gốc từ `CopyTicksRange` (bắt buộc lưu nguyên vẹn để ghép mốc). |
| `local_recv_msc` | `int64` | Mili-giây UTC máy cục bộ | Thời điểm máy thu thập nhận được tick (dùng phát hiện nghẽn mạng / đơ terminal). |
| `ntp_offset_ms` | `float` | Mili-giây (`ms`) | Độ lệch đồng hồ cục bộ đo qua NTP trước sự kiện (phải `< 1000,0 ms`). |
| `account_alias` | `string` | `<DEMO_ID>` | Bí danh ẩn danh tài khoản Demo (không ghi số login thật nếu chia sẻ ra ngoài). |
| `server` | `string` | `FTMO-Demo` | Tên máy chủ broker. |
| `symbol` | `string` | `US100.cash`, `USDJPY`, `GBPUSD`, `EURJPY`, ... | Mã giao dịch trên Market Watch. |
| `bid` | `float` | Giá niêm yết | Giá Bid tại tick. |
| `ask` | `float` | Giá niêm yết | Giá Ask tại tick. |
| `mid` | `float` | Giá niêm yết | Giá trung bình `0,5 * (bid + ask)`. |
| `spread_pts` | `float` | Broker points | `(ask - bid) / point` (ví dụ `US100.cash` `point = 0,01` -> `1,95` điểm chỉ số = `195,0` broker pts). |
| `spread_bps` | `float` | Basis points (`bps`) | `((ask - bid) / mid) * 10000`. |
| `point` | `float` | Giá trị `1` broker point | `0,01` (`US100.cash`), `0,001` (`USDJPY`/`EURJPY`), `0,00001` (`GBPUSD`). |
| `tick_flags` | `int` | Bitmask `MqlTick.flags` | Cờ thay đổi Bid/Ask/Last từ MT5 (`TICK_FLAG_BID`, `TICK_FLAG_ASK`). |
| `delta_bid_pts` | `float` | Broker points | `(bid_t - bid_{t-1}) / point` so với tick liền trước của cùng mã (đo bước nhảy giá trực tiếp). |
| `delta_ask_pts` | `float` | Broker points | `(ask_t - ask_{t-1}) / point` so với tick liền trước của cùng mã. |
| `inter_tick_gap_ms` | `int64` | Mili-giây (`ms`) | `server_tick_msc[t] - server_tick_msc[t-1]` (phát hiện đóng băng quote / lỗ hổng thanh khoản). |
| `seconds_from_release` | `float` | Giây (`s`, có dấu) | `(utc_ts_ms - release_utc_ts_ms) / 1000,0` (âm trước tin, `0,000` đúng `13:30:00.000 UTC`). |
| `window_phase` | `string` | `PRE_EVENT` / `IMPACT_CORE` / `POST_NORMALIZE` | Phân đoạn cửa sổ đo (`13:25..13:29:30`, `13:29:30..13:35`, `13:35..13:45 UTC`). |
| `order_send_count` | `int` | Bắt buộc `0` | Bộ đếm lệnh gửi đi trong phiên đo (`0` ở mọi dòng). |

### 4.2. Tệp đối khớp lệnh thực — `nfp_cpi_fill_audit_<EVENT_ID>.csv` (`FILL_VERIFIED` — ĐỂ TRỐNG `0` DÒNG TRONG ĐỢT CHỈ ĐỌC)

Bảng dưới đây chỉ dùng nếu về sau chủ sở hữu mở riêng một thí nghiệm có lệnh khớp thật; trong chiến dịch thu thập chỉ đọc `04/12` & `10/12`, tệp này **không sinh giao dịch (`0` dòng dữ liệu, `OrderSend = 0`)**:

```csv
record_tier,event_id,account_alias,server,symbol,position_id,deal_id,position_side,exit_reason,deal_time_msc,trigger_tick_time_msc,quote_match_delta_ms,trigger_bid,trigger_ask,expected_price,fill_price,market_overshoot_pts,broker_exec_slip_pts,total_adverse_slip_pts,separability_verdict,order_send_count
```

- **Quy tắc gán `record_tier` và `separability_verdict`:**
  - Chỉ được gắn `record_tier = FILL_VERIFIED` và `separability_verdict = SEPARABLE_MATCHED_TRIGGER_TICK` khi `deal_time_msc > 0`, `trigger_tick_time_msc > 0`, `|quote_match_delta_ms| <= 250`, và `inter_tick_gap_ms` quanh thời điểm kích hoạt không có lỗ hổng mất dữ liệu.
  - Nếu thiếu bất kỳ điều kiện nào -> bắt buộc gán `separability_verdict = UNSEPARABLE_MISSING_TRIGGER_QUOTE` (`KHÔNG TÁCH ĐƯỢC`), để trống `market_overshoot_pts` và `broker_exec_slip_pts` (tuyệt đối không ước đoán bằng mắt).

---

## 5. Biểu mẫu tổng hợp kiểm toán sau sự kiện (`T+20` phút — điền vào hồ sơ `private_vault/`)

Sao chép khối dưới đây vào tệp nhật ký hậu kiểm tương ứng (`private_vault/telemetry/nfp-cpi-202612/audit_<EVENT_ID>.md`) sau khi kết thúc cửa sổ `13:45:00 UTC`:

```markdown
### Báo Cáo Hậu Kiểm Chỉ Đọc — <US_NFP_20261204 | US_CPI_20261210>

- **Tài khoản & Máy chủ:** `FTMO-Demo (<DEMO_ID>)`
- **Tầng bằng chứng (`record_tier`):** `QUOTE_ONLY` (`FILL_VERIFIED = 0` dòng)
- **Khóa an toàn:** `order_send_count = 0` | `positions_total = 0` | `holdout_rows_analysed = 0`
- **Độ lệch đồng hồ NTP trước / sau sự kiện:** `<___> ms` / `<___> ms` (đạt chuẩn `< 1000 ms`: `PASS / FAIL`)
- **Cửa sổ thu thập thực tế (UTC):** `13:25:00.000Z` .. `13:45:00.000Z`
- **Tệp dữ liệu gốc (ngoài Git) & SHA-256:** `<duong_dan_private_vault_csv>` | `<sha256_16>`

| Mã (`symbol`) | Tổng số tick (`20` phút) | Spread nền `P50` `PRE` (`pts` / `bps`) | Đỉnh Spread `IMPACT` (`pts` / `bps`) | Bước nhảy 1 tick lớn nhất (`pts` / `idx_pts`) | Bước nhảy `1s` lớn nhất (`pts` / `idx_pts`) | Đóng băng quote lâu nhất (`inter_tick_gap_ms`) | Thời gian spread hồi về `<= 1,5x` nền (`s`) | So với giả định `STRESS_ASSUMPTION` (`750 / 1.000` pts)* |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `US100.cash` | `<n>` | `<pts> / <bps>` | `<pts> / <bps>` | `<pts> / <idx>` | `<pts> / <idx>` | `<ms>` | `<s>` | `<CHI_SO_SANH_QUOTE_ONLY>` |
| `USDJPY` | `<n>` | `<pts> / <bps>` | `<pts> / <bps>` | `<pts> / <pip>` | `<pts> / <pip>` | `<ms>` | `<s>` | `N/A (FX)` |
| `GBPUSD` | `<n>` | `<pts> / <bps>` | `<pts> / <bps>` | `<pts> / <pip>` | `<pts> / <pip>` | `<ms>` | `<s>` | `N/A (FX)` |
| `EURJPY` | `<n>` | `<pts> / <bps>` | `<pts> / <bps>` | `<pts> / <pip>` | `<pts> / <pip>` | `<ms>` | `<s>` | `N/A (FX)` |

*Ghi chú bắt buộc dưới bảng: Mọi mức so sánh với giả định `750 / 1.000` broker pts (`7,5 / 10,0` điểm chỉ số `US100.cash`, tương ứng `5,33% / 7,11%` trung vị SL Dev `140,65` điểm của `E4` và `4,88% / 6,51%` trung vị SL Dev `153,57` điểm của `E5`) ở bảng trên đều thuộc nhãn **`QUOTE_ONLY` vs `STRESS_ASSUMPTION`**, tuyệt đối không phải bằng chứng về giá khớp SL thực tế.*

- **Kiểm tra lịch tin đỏ (`naqex_red_news_utc.csv`):** Đã xác nhận mốc tin đỏ kích hoạt đúng vùng chặn `±300s` / cấm cứng `±135s` (`PASS / FAIL`).
- **Bất thường kỹ thuật (nếu có):** `<ghi rõ nếu rớt mạng, mất tick > 1.000 ms, hoặc chênh đồng hồ>`.
```

---

## 6. Ghi chú giới hạn trung thực (Honest Limitations — Đọc trước khi ra quyết định)

1. **Bước nhảy quote (`QUOTE_ONLY`) KHÔNG chứng minh giá khớp SL phía máy chủ:** Ngay cả khi thu được từng mili-giây Bid/Ask quanh `13:30:00 UTC`, đường giá chào chỉ phản ánh đỉnh/đáy thanh khoản hiển thị trên feed `FTMO-Demo`. Giá khớp thực tế của một lệnh Stop-Loss phía máy chủ còn phụ thuộc vào hàng đợi khớp (execution queue), khối lượng lệnh (lot size), độ sâu sổ lệnh thực tế (order-book depth) và độ trễ cầu thanh khoản (liquidity bridge) tại đúng thời điểm kích hoạt.
2. **Khoảng cách giữa `FTMO-Demo` và tài khoản trả phí / Funded thật:** Máy chủ Demo thường phản ánh tốt hướng giãn spread và bước nhảy giá vĩ mô, nhưng vẫn có thể khác tài khoản Live/Funded ở hành vi trượt giá đuôi trong `1–5` giây đầu sau công bố NFP hoặc CPI.
3. **Không suy diễn tách trượt giá khi thiếu `DEAL_TIME_MSC`:** Không được dùng dữ liệu `QUOTE_ONLY` để khẳng định trượt giá khớp lệnh sẽ nằm dưới một mức cứng cố định. Mức **`750 / 1.000` broker pts (`7,5 / 10,0` điểm chỉ số `US100.cash`)** vẫn giữ nguyên nhãn **`STRESS_ASSUMPTION`** cho kịch bản kiểm tra độ bền vốn, không phải mức trần được bảo đảm.
4. **Hàng rào bảo vệ vận hành thực tế vẫn là tránh cầm lệnh xuyên tin đỏ:** Đối với tài khoản `FTMO Standard` có quy định cấm giao dịch quanh tin đỏ, biện pháp giảm rủi ro đuôi mạnh nhất không phải đoán trượt giá SL mà là khóa cứng lịch `naqex_red_news_utc.csv` (chặn mở mới `±300s`, tự động đóng phẳng trước tin ở khung `-300s..-135s`, và cấm gửi lệnh đóng thường trong `±135s`).
