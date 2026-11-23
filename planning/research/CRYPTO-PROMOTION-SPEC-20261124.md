---
doc_type: research_spec
date: 2026-11-24
lane: quant-rnd
milestone: M3.4
status: READY_FOR_OWNER_REVIEW
order_send_count: 0
projects_quant_trading_modified: false
---

# Crypto Promotion Spec & Kiểm Tra Sức Khỏe Chỉ-Đọc `projects/quant-trading`

- **Ngày thực hiện:** `2026-11-24`
- **Trạng thái submodule `projects/quant-trading`:** **100% SẠCH — KHÔNG CHỈNH SỬA BẤT KỲ TỆP NÀO** (tuân thủ Quyết định khóa #4 của owner).
  - Commit HEAD xác nhận: `2035522` (`git -C projects/quant-trading status -s` trả về rỗng).
  - Kiểm thử chỉ-đọc: `uv run pytest -q` chạy tại `D:\ANNAM\TradingWorkspace\projects\quant-trading` -> **`261 passed in 10.26s`** (exit code `0`).

---

## 1. Kiến Trúc Tái Sử Dụng Từ `projects/quant-trading` (Không Viết Lại Bánh Xe)

Submodule `projects/quant-trading` đã sở hữu sẵn hệ thống primitive offline kiểm định chất lượng cao (261 unit tests xanh):

| Module Hiện Hữu (`projects/quant-trading`) | Chức Năng Đã Kiểm Chứng | Cách Tích Hợp Cho Sleeve #2 (Crypto Spot) |
|---|---|---|
| `src/quant_lab/data.py` & `provenance.py` | Tải dữ liệu Binance công khai, hash SHA-256, kiểm soát cutoff | Mở rộng sau này (khi owner cho phép chạm submodule) sang danh mục 50 coin & khung `4h`; hiện tại giữ cache độc lập tại `.runtime/crypto-spot-cache/` |
| `src/quant_lab/backtest.py` & `metrics.py` | Thực thi nhân quả `t -> t+1`, phí + slippage, Spot `[0, 1]` | Đã đối chiếu hoàn toàn khớp chuẩn với [crypto_causal_universe.py](../../tooling/ai-engines/quant_factory/crypto_causal_universe.py) |
| `src/quant_trading/paper_soak.py` | Hợp đồng `PaperSoakReceipt` 30–60 ngày (`PREP_ONLY_OFFLINE`, fail-closed, cấm live/credential, bắt buộc kiểm tra restart = 0 duplicate intent) | **Cổng bắt buộc** trước khi chuyển bất kỳ chiến lược Crypto Spot nào sang tiền thật |
| `src/quant_trading/cost_monte_carlo.py` & `parameter_stability.py` | Stress chi phí Monte Carlo & độ bền vùng tham số | Chạy đánh giá phụ trợ cho `F4_4H_EMA_24_120_BTC` và `F3_DONCHIAN_4H_120_60` trong pha paper |
| `src/quant_trading/change_detection.py` & `distribution_drift.py` | CUSUM / phát hiện trôi phân phối | Giám sát decay hàng tuần của Sleeve #2 trong pha soak |

---

## 2. Đề Xuất Promotion Pipeline (Fail-Closed 4 Giai Đoạn)

Mọi quyền giao dịch/API key vẫn **KHÓA (`OrderSend = 0`, `execution_capability = false`)** cho đến khi hoàn tất từng cổng và có xác nhận rõ ràng của owner:

### Giai Đoạn 0 — Nghiên Cứu Không Thiên Lệch Sống Sót (ĐÃ HOÀN TẤT HÔM NAY)
- **Ứng viên chính Sleeve #2 (Spot Long/Cash):** **`F4_4H_EMA_24_120_BTC`** (chọn mù trên Cluster A `2019–2023`, `CAGR Cl.B = +5.69%`, `2x-cost = +4.94%`, `MaxDD = 9.72%`, `Sharpe full = 1.466`, `turnover = 4.76x/năm`).
- **Ứng viên dự phòng ít xoay vòng / dễ chạy D1:** **`F3_DONCHIAN_4H_120_60`** (`turnover = 3.23x/năm`, `MaxDD Cl.B = 6.67%`, `Sharpe Cl.B = 0.857`) và **`F1_TSMOM_D1_L60_VT15`** (thuần khung ngày `1d`, `MaxDD Cl.B = 6.04%`, hợp với nhịp vận hành ít tốn công của owner trong `projects/quant-trading/AGENTS.md`).
- **Ứng viên Sleeve #3A (Carry — CHỈ KÍCH HOẠT THEO CHẾ ĐỘ):** **`CARRY_BTC_ETH_CONS_2XBUF`** (`2x` equity buffer, `0` thanh lý ký quỹ qua 7 năm, `MaxDD Cl.B = 0.29%`), nhưng **tạm giữ ở mức theo dõi (`WATCHLIST`)** cho tới khi funding trung bình 7 ngày BTC/ETH vượt ngưỡng hấp dẫn so với lãi suất phi rủi ro (`> +8%/năm` danh nghĩa, tức `> +4%/năm` ròng sau đệm `2x`).

### Giai Đoạn 1 — Dry-Run / Paper Soak 30–60 Ngày (Khớp `paper-soak-contract-r1`)
- **Chế độ:** `PREP_ONLY_OFFLINE` / chỉ đọc giá công khai Binance Spot (`0` API key giao dịch, `0` đặt lệnh).
- **Lịch chạy:** Cron 1 lần/ngày tại `00:05 UTC` (cho nhánh D1 `F1_TSMOM_D1_L60_VT15`) hoặc 6 lần/ngày sau đóng nến `4H` (cho `F4_4H_EMA_24_120_BTC` / `F3_DONCHIAN_4H_120_60`).
- **Tiêu chí đạt cổng `ACCEPTED` (`PaperSoakReceipt`):**
  1. Tối thiểu **`30` ngày UTC liên tục** (tối đa `60` ngày), không bỏ sót nến đóng hoặc trễ cutoff nhân quả;
  2. Tối thiểu **`1` bài kiểm tra khởi động lại (restart recovery check)** xác nhận **`0` duplicate order intents**;
  3. So khớp giá thực thi giả định (`mid/ask/bid` thực tại thời điểm `00:05 UTC`) với mô hình backtest: chênh lệch trượt giá thực tế không vượt quá **`20 bps`** một chiều;
  4. Lưu biên nhận JSON có chữ ký SHA-256 + xác nhận thủ công bằng tay của owner (đánh giá kèm **behavioral fit**: chấp nhận trả lại một phần lợi nhuận chưa chốt khi bám xu hướng mà không can thiệp giữa lệnh).

### Giai Đoạn 2 — Pilot Vốn Nhỏ Spot-Only (Sau Khi Đạt Giai Đoạn 1 + Owner Phê Duyệt Rõ)
- **Vốn thử nghiệm:** Rất nhỏ theo mức thoải mái bằng VND của owner (ví dụ `5%–10%` ngân sách nhánh Crypto, tương đương ~`500–2.000 USD` ban đầu), **Spot-only trên 1 tài khoản phụ (sub-account) tách biệt**, API key chỉ bật quyền `Spot Trade`, tắt 100% quyền `Withdraw` và `Futures`, khóa IP whitelist.
- **Giới hạn rủi ro cứng (Kill Switches):**
  - Tổng tỷ trọng Spot `sum(w) <= 1.0`, tỷ trọng tối đa 1 coin `<= 25%`;
  - Ngừng tự động (circuit breaker) nếu tài khoản phụ giảm `> 12%` từ đỉnh (vượt `1.25x` MaxDD lịch sử `9.72%`) hoặc sai lệch đối soát vị thế `> 0.5%` NAV;
  - **Kỷ luật hành vi chống can thiệp giữa lệnh:** Mọi đánh giá sửa quy tắc chỉ thực hiện tại kỳ review cố định hàng tháng/quý, tuyệt đối không tự tay cắt lời/cắt lỗ ngang lệnh bot.

### Giai Đoạn 3 — Mở Rộng Tích Hợp Vào 4-Sleeve Quant Pod
- Chỉ tăng quy mô vốn Sleeve #2 sau **`>= 90` ngày Pilot** không lỗi vận hành, trượt giá thực tế nằm trong dải `<= 1.5x` giả định (`<= 22.5 bps` một chiều), và cập nhật tỷ trọng theo ma trận phân bổ 4-Sleeve của `@risk-auditor` (`QUANT-POD-4SLEEVE-ALLOCATION-20261124.md`).

---

## 3. Ranh Giới An Toàn & Trạng Thái Hiện Tại

- **Thay đổi trong `projects/quant-trading`:** `0` tệp.
- **Kết nối sàn có xác thực / API key / `OrderSend`:** `0`.
- **Bước tiếp theo cho owner quyết định sau buổi sáng:** Phê duyệt có bắt đầu **Giai Đoạn 1 (30-day Paper Soak không API key)** cho `F1_TSMOM_D1_L60_VT15` (thuần D1, 1 lần/ngày) hay `F4_4H_EMA_24_120_BTC` (4H, 6 lần/ngày) hay không.
