---
doc_type: evergreen
domain: knowledge
topic: quant-pod-and-career-pyramid
updated_utc: 2026-11-23
---

# Tháp 5 Tầng Quant Trading & Mô hình "One-Person Quant Pod"

## 1. Bản đồ 5 tầng thực tế của ngành

1. **Tầng 1 — Retail cảm tính / EA curve-fit:** Phần lớn âm dài hạn (`Sharpe < 0.5`).
2. **Tầng 2 — Independent Systematic Quant:** Quy tắc toán học rõ, kiểm OOS/MC/FDR, chạy tự động (`Sharpe live 1.0–1.8`, `Calmar 1.0–2.0`, vốn `10k–2M USD`).
3. **Tầng 3 — CTA / Systematic Macro Hedge Fund (AQR, Man AHL, Winton):** `Sharpe live 0.8–1.5`, dung lượng hàng tỷ USD.
4. **Tầng 4 — Multi-Manager Stat-Arb Pods (Citadel, Millennium, WorldQuant):** Hàng trăm–nghìn tín hiệu vi mô trung hòa thị trường + alt-data (`Sharpe live 2.0–4.0`, `Calmar 2.5–5.0+`).
5. **Tầng 5 — Ultra-Low Latency HFT & Market Making (Jane Street, Jump, HRT, Medallion):** Microstructure, FPGA/ASIC, co-location, maker rebate (`Sharpe live 5.0–15.0+`, rào cản vật lý và hạ tầng hàng chục triệu USD).

## 2. Lợi thế bất đối xứng của cá nhân (IQ `115–120` + AI Agents)

- Không đua Tầng 5 HFT; tập trung khai thác **Small-Capital Edge** ở các ngách dung lượng `50k–3M USD` mà quỹ tỷ đô không vào được vì trượt giá.
- **Bằng chứng thực nghiệm nội bộ (`23/11/2026`):** Ghép Nhánh #1 (`PORT_7E` Intraday FX/Index Prop — đã qua Holdout `2025–2026` mức **GO**, `Calmar 1.75–1.94`) + Nhánh #2 (`C1/C2` Crypto Spot Vol-Managed Trend — tương quan `r = 0.02`, dương `+6%..+9%/năm` ngay trong thị trường gấu `2025–2026`) đưa danh mục tổng lên **`Sharpe 1.91–1.99`, `Calmar 2.09–2.36`** ([Chi tiết nghiên cứu](../../planning/research/CRYPTO-SLEEVE2-AND-QUANT-POD-STUDY-20261123.md)).
- Vai trò quyết định của con người khi dùng AI Agents: làm **Giám đốc Khoa học & Rủi ro** (chặn overfit siêu tốc, giữ kỷ luật Holdout 1 lần, đối soát TCA thực tế, giữ tâm lý ổn định trong pha đi ngang).
