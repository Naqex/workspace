---
doc_type: research-receipt
generated_utc: 2026-11-25T05:45:11+00:00
order_send_count: 0
holdout_rows_analysed: 0
---

# Đối Chứng Khung Kiến Trúc Vòng 3 (7E Cố Định, Cap Cụm Hướng, Sizing Theo Rào & Ngày Lịch Thật)

- **Tập dữ liệu:** Dev niêm phong `2018-01-02..2024-12-31` (`2556` ngày lịch thật bao gồm cuối tuần & ngày nghỉ; `holdout_rows_analysed = 0`, `order_send_count = 0`).
- **Mô phỏng:** `N = 5,000` đường × `730` ngày lịch thật (`24` tháng lịch, seed `20261125`), có đủ độ trễ nhận tiền (`T+3` FTMO / `T+5` The5ers), phí rút (`1,0%` / `3,5%`), sàn rút (`50` / `150 USD`) và tách riêng hoàn phí tiền mặt ngoài.

## 1. Tác Động Của Khóa Cụm Hướng (`USD / JPY / US100`) Ở P1 (`4,0×`, Phí `1,0×`)

| Cấu hình P1 (`7E`) | Lãi ròng Dev (USD) | Max DD (%) | Ngày xấu nhất (%) | Đỉnh cụm USD (%) | Đỉnh cụm JPY (%) | Lệnh cắt/chặn bởi cụm |
|---|---:|---:|---:|---:|---:|---:|
| Chỉ khóa theo mã (`1,75%`) | `+14,071.18` | `23.77%` | `5.14%` | `3.50%` | `3.48%` | `0/0` |
| **Khóa mã + Cụm (`USD 2,25% / JPY 2,00% / Tổng 3,00%`)** | **`+13,692.72`** | **`23.26%`** | **`4.01%`** | **`2.25%`** | **`2.00%`** | **`421/0`** |

## 2. Đối Chứng Cặp Trên Ngày Lịch Thật (`24` Tháng = `730` Ngày Lịch, Khối `7` Ngày)

| Hợp đồng & Cấu hình | Phí | Lãi ròng TB 24t (USD) | Trung vị 24t (USD) | P(Lỗ ròng ≤0) | Cháy ngày lượt 1 | Đạt payout 24t | Trung vị ngày lịch tới payout 1* | Max vốn ứng P95 (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `FTMO Swing 10K` · 7E · Static Lock | `1.00x` | `+558` | `+529` | `20.9%` | `0.0%` | `80.8%` | `321 ngày` | `336` |
| `FTMO Swing 10K` · 7E · Barrier Headroom | `1.00x` | `+435` | `+361` | `33.5%` | `0.0%` | `66.6%` | `341 ngày` | `168` |
| `FTMO Swing 10K` · 8E Baseline · Static | `1.00x` | `+540` | `+510` | `22.2%` | `0.0%` | `79.7%` | `322 ngày` | `336` |
| `FTMO Swing 10K` · 7E · Static Lock | `1.25x` | `+374` | `+326` | `30.4%` | `0.0%` | `71.8%` | `350 ngày` | `336` |
| `FTMO Swing 10K` · 7E · Barrier Headroom | `1.25x` | `+278` | `+139` | `44.5%` | `0.0%` | `55.5%` | `356 ngày` | `168` |
| `FTMO Swing 10K` · 8E Baseline · Static | `1.25x` | `+355` | `+310` | `32.0%` | `0.0%` | `70.2%` | `350 ngày` | `336` |
| `FTMO Swing 10K` · 7E · Static Lock | `1.50x` | `+205` | `+143` | `41.6%` | `0.0%` | `61.2%` | `377 ngày` | `504` |
| `FTMO Swing 10K` · 7E · Barrier Headroom | `1.50x` | `+138` | `-168` | `56.6%` | `0.0%` | `43.4%` | `362 ngày` | `168` |
| `FTMO Swing 10K` · 8E Baseline · Static | `1.50x` | `+178` | `+106` | `44.7%` | `0.0%` | `59.1%` | `379 ngày` | `504` |
| `FTMO Swing 10K` · 7E · Static Lock | `2.00x` | `-63` | `-168` | `64.7%` | `0.0%` | `39.5%` | `401 ngày` | `504` |
| `FTMO Swing 10K` · 7E · Barrier Headroom | `2.00x` | `-36` | `-168` | `74.9%` | `0.0%` | `25.2%` | `376 ngày` | `336` |
| `FTMO Swing 10K` · 8E Baseline · Static | `2.00x` | `-91` | `-168` | `65.8%` | `0.0%` | `38.6%` | `406 ngày` | `672` |
| `The5ers HS 5K` · 7E · Static Lock | `1.00x` | `+261` | `+265` | `28.5%` | `0.0%` | `71.5%` | `393 ngày` | `78` |
| `The5ers HS 5K` · 7E · Barrier Headroom | `1.00x` | `+209` | `+144` | `40.6%` | `0.0%` | `59.4%` | `405 ngày` | `39` |
| `The5ers HS 5K` · 8E Baseline · Static | `1.00x` | `+255` | `+207` | `29.4%` | `0.0%` | `70.6%` | `392 ngày` | `78` |
| `The5ers HS 5K` · 7E · Static Lock | `1.25x` | `+181` | `+141` | `39.8%` | `0.0%` | `60.2%` | `413 ngày` | `78` |
| `The5ers HS 5K` · 7E · Barrier Headroom | `1.25x` | `+142` | `-39` | `52.2%` | `0.0%` | `47.8%` | `413 ngày` | `39` |
| `The5ers HS 5K` · 8E Baseline · Static | `1.25x` | `+177` | `+140` | `40.3%` | `0.0%` | `59.7%` | `417 ngày` | `78` |
| `The5ers HS 5K` · 7E · Static Lock | `1.50x` | `+109` | `-39` | `52.1%` | `0.0%` | `47.9%` | `432 ngày` | `117` |
| `The5ers HS 5K` · 7E · Barrier Headroom | `1.50x` | `+80` | `-39` | `64.5%` | `0.0%` | `35.5%` | `426 ngày` | `39` |
| `The5ers HS 5K` · 8E Baseline · Static | `1.50x` | `+103` | `-39` | `53.1%` | `0.0%` | `46.9%` | `435 ngày` | `117` |
| `The5ers HS 5K` · 7E · Static Lock | `2.00x` | `+12` | `-39` | `72.7%` | `0.0%` | `27.3%` | `455 ngày` | `117` |
| `The5ers HS 5K` · 7E · Barrier Headroom | `2.00x` | `+10` | `-39` | `81.9%` | `0.0%` | `18.1%` | `444 ngày` | `78` |
| `The5ers HS 5K` · 8E Baseline · Static | `2.00x` | `+5` | `-39` | `73.0%` | `0.0%` | `27.0%` | `468 ngày` | `156` |

*Ghi chú: Trung vị ngày lịch tới payout đầu tính trên các đường đạt được payout trong 730 ngày lịch; tỷ lệ đường không đạt payout = `100% - Đạt payout 24t`.*

## 3. Khuyến Nghị Sizing Tự Động Tại Phí Stress `1,50×`: **`STATIC_LOCK`**

- **Kết luận trung thực về ma sát `2,00×`:** Nếu trượt giá thực tế trên demo/live đo được gần `2,00×` ngân sách M1, phần lớn đường chạy không còn kỳ vọng dương đủ bù công vận hành — đúng tiêu chí dừng/gác cơ chế nội ngày của Astra Vòng 3.
- **Ngưỡng quyết định tiếp theo:** Chỉ giữ cơ chế nội ngày khi đo thực tế trên `FTMO-Demo` (`naqex-node1`) cho trượt giá nằm gọn trong vùng `<= 1,25× – 1,50×` ngân sách M1 sau tối thiểu `10–15` lệnh đóng đối soát với statement.
