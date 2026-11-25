# Nghiên cứu Nguồn Alpha #2 Không Tương Quan (Crypto Spot Quant) & Ghép "One-Person Quant Pod"

- **Ngày thực hiện:** `23/11/2026`
- **Biên nhận máy kiểm chứng (SHA-256 `5356da02cdc3c189`):** [CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.json](CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.json)
- **Nguồn dữ liệu đọc-không-sửa:** `5` chuỗi Binance Spot khung ngày đã niêm phong trong `projects/quant-trading/data/raw/` (`BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `ADAUSDT`, `SOLUSDT`; `2018-01-01` → `2026-08-23`, `3.157` ngày).
- **Ràng buộc tuân thủ `projects/quant-trading/AGENTS.md`:** Tín hiệu ngày `t` chỉ khớp từ ngày `t+1` (100% nhân quả), chỉ Spot Long/Cash (`weight ∈ [0, 1]`, không short, không leverage, không kết nối sàn/API key), phí + trượt giá `15 bps` một chiều (và stress gấp đôi `30 bps`), không forward-fill trước ngày niêm yết (`SOLUSDT` chỉ vào rổ sau khi niêm yết và đủ cửa sổ).

---

## 1. Hiệu suất Nhánh Crypto Spot (Dev `2018–2024` vs OOS mù `2025–2026`)

| Chiến lược (Spot Long/Cash, `t → t+1`) | Dev `CAGR` (`15 bps`) | Dev `MaxDD` | Dev `Sharpe` | Dev `Calmar` | **OOS `2025–2026` `CAGR` (`15 / 30 bps`)** | **OOS `MaxDD`** | **OOS `Sharpe`** | **OOS `Calmar`** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `BH_BTC` (Mua & giữ BTC) | `+44.19%` | `76.63%` | `0.89` | `0.58` | `-11.30% / -11.38%` | `52.97%` | `-0.05` | `-0.21` |
| `BH_EQW5` (Mua & giữ đều 5 coin) | `+69.43%` | `82.52%` | `1.08` | `0.84` | `-23.15% / -23.16%` | `66.90%` | `-0.12` | `-0.35` |
| **`C1_TSMOM_VOL20`** *(Xu hướng đa coin + Vol-Target 15%)* | **`+14.98%`** | **`11.04%`** | **`1.66`** | **`1.36`** | **`+5.98% / +4.66%`** | **`6.46%`** | **`+0.73`** | **`0.93`** |
| **`C2_XSEC_TOP2_TREND`** *(Top-2 dẫn dắt + Lọc BTC SMA100)* | **`+20.34%`** | `13.87%` | **`1.67`** | **`1.47`** | **`+8.98% / +6.01%`** | **`8.21%`** | **`+0.83`** | **`1.09`** |

**Điểm ấn tượng nhất trên OOS mù `2025–2026` (`600` ngày thị trường gấu crypto):** Trong khi `BTC` sập sâu `-52.97%` và rổ `5` coin sập `-66.90%`, cả `C1` và `C2` đều **dương ròng (`+10.02%` và `+15.18%` tổng lãi)** với `MaxDD` chỉ **`6.46%–8.21%`** (nhỏ hơn `8–10` lần Buy-and-Hold!) và vẫn dương ròng ngay cả khi nhân đôi chi phí giao dịch lên `30 bps` một chiều!

---

## 2. Ghép "One-Person Quant Pod": Nhánh #1 (`FX/Index Prop`) + Nhánh #2 (`Crypto Spot`)

Đo trên toàn bộ `2.453` ngày lịch liên tục (`2018-04-15` → `2024-12-31`, giữ nguyên 100% lợi nhuận cuối tuần của Crypto 24/7):

| Tổ hợp Pod (`2018–2024`, `2.453` ngày) | Tương quan mọi ngày | Tương quan `5%` ngày FX xấu nhất | `CAGR` | `Vol/năm` | `MaxDD` | **`Sharpe`** | **`Calmar`** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Nhánh #1 đơn lẻ (`PORT_7E @ 1.5×`) | — | — | `+11.42%` | `9.46%` | `8.34%` | `1.19` | `1.37` |
| Nhánh #2 đơn lẻ (`C1 @ 0.75×`, `15 bps`) | — | — | `+11.11%` | `6.47%` | `8.37%` | `1.66` | `1.33` |
| **Pod #1 (`FX7E 1.5×` + `C1 0.75×`)** | **`+0.0205`** | `+0.0851` | **`+23.78%`** | `11.54%` | **`10.07%`** | **`1.91`** | **`2.36`** |
| **Pod #2 (`FX7E 1.5×` + `C2 0.75×`)** | **`+0.0156`** | `+0.1105` | **`+28.15%`** | `12.87%` | `13.50%` | **`1.99`** | **`2.09`** |

**Kết luận & giới hạn trung thực:**
- Hai nhánh gần như **độc lập tuyệt đối (`r = +0.016` đến `+0.021`)**, đẩy toàn bộ danh mục cá nhân từ `Sharpe 1.19 / Calmar 1.37` vọt lên vùng **`Sharpe 1.91–1.99 / Calmar 2.09–2.36`** (đúng ngưỡng mục tiêu *One-Person Quant Pod*).
- **Hạn chế cần ghi rõ (chống thiên lệch):** (1) **Survivorship bias:** 5 coin (`BTC, ETH, BNB, ADA, SOL`) là các đồng sống sót mạnh nhất tới 2026; khi đưa vào vận hành thật phải chọn rổ **nhân quả theo thanh khoản/khối lượng 30 ngày trượt** (ví dụ Top-10 Binance Spot volume trượt theo từng tháng); (2) Đây mới là nhánh Spot Long/Cash — chưa có phần Futures Funding-Rate / Cash-and-Carry (sẽ chỉ nghiên cứu thêm khi người dùng yêu cầu rõ mở phạm vi ngoài Spot).
