---
doc_type: execution-playbook
title: Sổ Tay Thực Thi Sổ Vốn Riêng Cho Cư Dân Việt Nam
date: 2026-11-28
worker: w4-m2b-vnbook
campaign: Total Offensive #4 v4.8.1 FINAL (Wave 2A)
gate_id: W4-G08-VNBOOK
order_send_capable: false
order_send_count: 0
spend_vnd: 0
holdout_cutoff_inclusive: "2024-12-31"
holdout_rows_analysed: 0
holdout_lock_sha256: f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486
source_summary_sha256: 7724297eff3fd1e93ad4b9d538b6a57c8cddcea1f4312c348e5f32525577ee7f
---

# Sổ Tay Thực Thi Sổ Vốn Riêng Cho Cư Dân Việt Nam (`VN-OWNBOOK-EXECUTION-PLAYBOOK`)

**Kết luận hành động:** Chỉ giải ngân dòng tiền từ `S7` Hậu Payout Prop (Giỏ 3) sang Sổ Vốn Riêng theo **`4` ngưỡng vốn cứng** (`< 100 tr` -> `100–250 tr` -> `250–500 tr` -> `>= 500 tr VND / 20.000 USD`), khóa chặt **`CEX <= 25,0%`**, tự xoay nhánh `Carry` sang T-Bill (`SGOV/BIL` hoặc **`IB01` UCITS**) khi funding `< 3,0%/năm`, và chuyển sang **UCITS Ireland** trước mốc **`60.000 USD`** để hạ thuế cổ tức Mỹ (`15%` thay vì `30%`) và tránh rủi ro thuế di sản Mỹ `40%`.

> **Khóa an toàn & Nguồn kiểm chứng:** `OrderSend = 0` · `0 VND` · `Holdout 2025+ SEALED` (`holdout_rows_analysed = 0`) · Tỷ giá SSOT [fx_rates.json](../../tooling/ai-engines/configs/ssot/fx_rates.json): **`1 USD = 25.765,94 VND`** (`26/11/2026`). Nguồn số liệu: [ownbook_shadow_ops_summary.json](../../.runtime/offensive4/frontier/ownbook_shadow_ops_summary.json) (`#788`), [ownbook_shadow_ops.py](../../tooling/ai-engines/quant_factory/wave4/ownbook_shadow_ops.py), [treasury_ledger.py](../../tooling/ai-engines/quant_factory/treasury_ledger.py), [PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md](PROP-VN-PAYOUT-LEGAL-AND-VPS-COMPLIANCE-20261125.md), [OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md](OWNBOOK-ETF-SUPER-SLEEVE-AND-IBKR-LOT-AUDIT-20261124.md) và [ownbook-merger-arb-and-vps-scaling-2026.md](../../knowledge/topics/ownbook-merger-arb-and-vps-scaling-2026.md). Mục 3 là khung sổ sách vận hành, **KHÔNG phải tư vấn pháp lý/thuế có chứng chỉ**.

---

## 1. Lộ Trình `S7` (Giỏ 3) Sang Sổ Vốn Riêng Theo `4` Ngưỡng Vốn VN

### 1.1. Khóa Tiền Mặt Thực Nhận (`Settled Cash`) & `3` Giỏ Hậu Payout `S7`
Theo [TOP1-SOLO-QUANT-MASTER-PLAN.md](../TOP1-SOLO-QUANT-MASTER-PLAN.md) §3.2 và [prop_lifecycle_orchestrator.py](../../tooling/ai-engines/quant_factory/wave4/prop_lifecycle_orchestrator.py), chỉ hạch toán **tiền thực đã về ngân hàng/ví** (`PAYOUT_SETTLED` + hoàn phí tiền mặt `EXTERNAL_CASH_REFUND`); loại hoàn toàn `PAYOUT_APPROVED` và tín dụng nội bộ `HUB_CREDIT_GRANT`.
- **Pha hoàn gốc (`Payout #1`):** Hoàn đủ **`100%`** vốn phí thi đã chi (`principal_recovered = true`) + giữ đệm **`>= 2x`** giá vé kế tiếp trước khi mở rộng.
- **Pha `S7` 3 giỏ (`PARETO_3_BUCKET_DEFAULT`):** Khi đủ hoàn gốc và `>= 2` kỳ payout dương thực nhận, chia tiền mặt ròng vào: **Giỏ 1 (`30%`)** Tiền an toàn & dự phòng thuế/hạ tầng (`TAX_PAID`, `OPS_CASH_OUT`) · **Giỏ 2 (`30%`, trần `5x` vé chuẩn)** Quỹ nâng cấp/đệm vé `S0` (vượt trần `5x` tự tràn **`100%`** sang Giỏ 3) · **Giỏ 3 (`40%` gốc -> `70%` khi Giỏ 2 đầy)** Sổ Vốn Riêng.

### 1.2. Bốn Ngưỡng Vốn Thực Địa Cho Cư Dân Việt Nam

| Ngưỡng vốn Giỏ 3 (`VND` / `USD`) | Kênh được phép triển khai | Trần `CEX` | Mốc mở IBKR / UCITS / T-Bill & Kỷ luật phí |
|---|---|---:|---|
| **`< 100 tr VND`** (`< ~3.880 USD`) | **`100%` Thanh khoản an toàn trong nước** (tiết kiệm ngắn hạn / quỹ tiền tệ VN). | **`0%`** | **Cấm mở IBKR đa nhánh & Cấm CEX:** Ở `5.000 USD`, phí sàn IBKR `0,35 USD/lệnh` + làm tròn lô nguyên ngốn **`451–534 bps/năm`** (`SUPER_ETF_6ENG`) và `137–159 bps/năm` (`L7_TOP2`). |
| **`100 – 250 tr VND`** (`~3.880 – 9.700 USD`) | **Giữ `100%` thanh khoản nội địa** + hoàn thiện hồ sơ `OPS-5` & đối chiếu luật sư/kế toán. | **`0%`** | Dưới mốc sàn **`10.000 USD` (`~257,7 tr VND`)** của Master Plan §3.2. Dùng giai đoạn này tích lũy chứng từ nguồn tiền sạch và rà soát ngoại hối. |
| **`250 – 500 tr VND`** (`~9.700 – 19.405 USD`, chạm `10k–20k USD`) | **T-Bill + Macro ETF gọn `0` swap vòng quay thấp** (`S3B` `2–6x/năm` hoặc `L7_TOP2` `10x/năm`, bật Fractional); Crypto chạy bóng (`Shadow`). | **`0%`** | Chỉ mở IBKR Pro khi **có đường nạp chính chủ hợp pháp** (Mục 3). Ở `10k USD`, `L7_TOP2` tốn `112,5 bps/năm` (`Net CAGR +7,10%`, `Sh 0,93`); tránh `SUPER_ETF_6ENG` (`304 bps/năm`). Neo tiền mặt vào **`SGOV/BIL`** hoặc gom lệnh tháng/quý vào **`IB01` UCITS**. |
| **`>= 500 tr VND`** (`>= 20.000 USD`, chuẩn hóa `25k` & `50k USD`) | **Đủ `4` nhánh Own-Book (`60/10/15/15`)**: ETF + T-Bill + Crypto Spot + Funding Carry (`BTC/ETH`, đệm `2,0x`). | **`<= 25%`** | Từ **`20k–25k USD`** (`515–644 tr`): phần `25%` CEX đạt `5.000–6.250 USD` đủ chia vị thế `BTC/ETH` và `L7_TOP2` sạch **lô nguyên** (`TE 17,7 bps`). Từ **`50.000 USD` (`1,29 tỷ`)**, `SUPER_ETF_6ENG` sạch lô nguyên (`TE 19,0 bps`, tiền chết `1,34%`, `Net CAGR +6,59%`, `Net Sh 0,87`). |

### 1.3. Quy Tắc Thuế Công Cụ: `UCITS Ireland` vs `US ETF` vs `T-Bill`
VN–Mỹ **chưa có hiệp định thuế hiệu lực** (`2015` chưa phê chuẩn), cần khóa `3` quy tắc:
1. **`US ETF` (`SPY`, `SGOV`, `BIL`) vs `UCITS Ireland` (`IB01`, `CSPX`, `VUAA`, `IGLN` giao dịch `USD` trên LSE):** ETF Mỹ chịu **`30%`** thuế cổ tức (T-Bill `SGOV/BIL` thường hoàn QII đầu năm sau nhưng bị tạm giữ tiền) và tài sản gốc Mỹ vượt **`60.000 USD`** (`~1,55 tỷ VND`) dính rủi ro **thuế di sản Mỹ `18%–40%`**. **UCITS Ireland** chỉ chịu **`15%`** thuế cổ tức nội quỹ, **`0%`** khấu trừ từ Ireland ra VN, và **miễn `100%` thuế di sản Mỹ**.
2. **Mốc chuyển đổi:** Dưới `50k USD` có thể dùng `SGOV` (`TER 0,09%`, sàn Mỹ `0,35 USD/lệnh`) hoặc gom quý sang **`IB01`** (`IE00BGSF1X88`, `TER 0,07%`, tích lũy T-Bill 0–1 năm). Trước mốc **`50.000–60.000 USD`**, chuyển toàn bộ T-Bill và ETF giữ dài hạn sang **UCITS Ireland (`IB01`, `CSPX`, `IGLN`)**.
3. **Cấm PTP (`IRC 1446(f)`):** Không mua ETF dạng *Publicly Traded Partnership* (`UUP`, `USO`, `DBC`) vì bị thu **`10%` trên tổng giá trị bán** kể cả lúc lỗ.

---

## 2. Cơ Cấu Phân Bổ `#788` (`60/10/15/15`) & Kết Quả `4/4` Stress Test

Trích từ `ownbook_shadow_ops_summary.json` (Dev `2020-01-01..2024-12-31`, `1.305` phiên Mon–Fri, loại `474` dòng ETF + `4.146` funding + `691` Spot của `2025+`, `holdout_rows_analysed = 0`).

| Nhánh (`ownbook_shadow_ops.py`) | Tỷ trọng | Lưu ký | `20.000 USD` (`515,32 tr`) | `50.000 USD` (`1.288,30 tr`) | Dev đơn lẻ (`2020–2024`) |
|---|---:|---|---:|---:|---|
| **`MACRO_ETF_SUPER_SLEEVE`** | **`60%`** | IBKR *(phi-CEX)* | `12.000` (`309,19 tr`) | `30.000` (`772,98 tr`) | `CAGR +6,82%` · `DD 12,35%` · `Sh 0,90` · `Cal 0,55` |
| **`CRYPTO_SPOT`** (1x) | **`10%`** | **Ví lạnh** + CEX | `2.000` (`51,53 tr`) | `5.000` (`128,83 tr`) | `CAGR +15,00%` · `DD 9,72%` · `Sh 1,65` · `Cal 1,54` |
| **`CRYPTO_FUNDING_CARRY`** (`2,0x` đệm) | **`15%`** | CEX `BTC/ETH` | `3.000` (`77,30 tr`) | `7.500` (`193,24 tr`) | `CAGR +7,08%` · `DD 1,01%` · `Sh 6,61`* · `0` liq |
| **`CASH_TBILL_BUFFER`** (`SGOV`/`IB01`) | **`15%`** | IBKR *(phi-CEX)* | `3.000` (`77,30 tr`) | `7.500` (`193,24 tr`) | `CAGR +2,26%` · `DD 0,21%` · `Sh 8,52`* · `Cal 10,85`* |
| **TỔNG HỢP CÓ KHIÊN (`Guarded`)** | **`100%`** | **`75%` phi-CEX / `<= 25%` CEX** | **`20.000 USD` (`515,32 tr`)** | **`50.000 USD` (`1.288,30 tr`)** | **`CAGR +6,69%` · `Vol 4,83%` · `DD 8,09%` · `Sh 1,36` · `Cal 0,83`** |

*(\*) `Sharpe` đơn lẻ của `Carry`/`T-Bill` cao do biến động thấp (`0,26%–1,04%`), nhưng `Carry` chịu rủi ro đối tác sàn nên bị khóa `Spot + Carry <= 25%`. Khiên nén funding kích hoạt **`229` ngày (`17,55%`, `57` lượt xoay)**, kéo `CEX` trung bình còn **`22,37%`** (đỉnh `25,0%`) và chỉ giảm nhẹ `-0,37 đ%/năm` so với bản tĩnh (`+7,06%`, `DD 7,58%`, `Sh 1,44`). Quy đổi Dev minh họa: mốc `20k` lãi `~34,47 tr/năm`, DD `~41,69 tr`; mốc `50k` lãi `~86,19 tr/năm`, DD `~104,22 tr`.*

**Kết quả `4/4` bài kiểm sốc cực đoan (`ALL PASS`, `holdout_rows_analysed = 0`):**
1. **`STRESS_1` (Vỡ sàn CEX mất `-100%`):** Chặn fail-closed mọi cấu hình `CEX > 25%` (`35%` -> `ValueError`). Sập trắng sàn CEX khóa lỗ toàn Sổ Vốn Riêng tối đa **`25,0%`** (`128,83 tr` ở `20k`; `322,07 tr` ở `50k`), giữ sống **`75,0%`** tại IBKR/T-Bill.
2. **`STRESS_2` (Nén funding `< 3%` trong `180` ngày + giật `-22%`):** `FUNDING_COMPRESSION_ALERT` nổ sau **`+6` ngày**, xoay **`15% -> 0%`** Carry sang `SGOV/BIL` (`30%` T-Bill, `10%` CEX). Nhánh có khiên lãi **`+1,65%`** (`DD 0,27%`, góp `+0,25%`) so với để trần lỗ **`-1,00%`** (`DD 1,06%`, kéo lùi `-0,15%`).
3. **`STRESS_3` (Khủng hoảng kép cổ + trái phiếu `2022`, `260` phiên):** Own-Book âm **`-6,35%`**, **`MaxDD 7,87%`** so với `60/40 SPY/IEF` âm `-16,39%` / **`MaxDD 20,69%`** (giảm **`12,82` đ%**, bằng **`0,38x`** mức sập `60/40`; `SPY/TLT` âm `-22,83%` / `26,89%`).
4. **`STRESS_4` (Flash Crash Crypto `-35%` / 24h + basis `-300 bps` + giật `+35%`):** **`0` cháy ký quỹ** (`0` Spot / `0` Isolated / `0` Cross) nhờ đệm `2,0x` (ngưỡng thanh lý **`+95,0%`**, còn dư **`60,0%`**). Sụt ròng toàn sổ chỉ **`3,74%`** (`-1.870 USD` / `-48,18 tr` ở `50k`), giữ **`96,26%`** vốn sống sót.

---

## 3. Tách Bạch: Dữ Liệu Đã Xác Minh vs Pháp Lý & Thuế VN Cần Đối Chiếu Chuyên Gia

### 3.1. Đã Xác Minh Trong Kho & Nguồn Công Khai
- **Định lượng & hạ tầng:** Số liệu `#788`, phí lô nguyên IBKR Pro Tiered (`0,0035 USD/cp`, sàn `0,35 USD/lệnh`), và cảnh báo `OPS-4` đã kiểm thử tự động trên dữ liệu Dev `<= 2024-12-31`.
- **Rào cản kênh nạp rút đã kiểm (`25/11/2026`):** IBKR **cấm nạp bên thứ ba** (bắt buộc từ tài khoản ngân hàng đúng tên -> **không rút thẳng từ Prop Firm/Riseworks vào IBKR**); Wise VN không mở đủ tài khoản nhận USD nối sang IBKR; thuế cổ tức Mỹ `30%` / di sản `60k` / PTP `1446(f)` `10%` vs UCITS `15%`.
- **Văn bản VN công khai đã ghi nhận:** Ngoại hối `TT 20/2022/TT-NHNN` & `NĐ 70/2014/NĐ-CP`; tài sản số theo Luật Công nghiệp công nghệ số, `NQ 05/2025/NQ-CP` (`09/09/2025`, thí điểm 5 năm qua **CASP** được Bộ Tài chính cấp phép), và `TT 32/2026/TT-BTC` (`27/03/2026`, miễn VAT, thuế TNCN **`0,1%`/lần chuyển nhượng** qua CASP).

### 3.2. BẮT BUỘC Đối Chiếu Kế Toán Thuế / Luật Sư Trước Khi Chuyển Tiền Lớn
1. **Ngoại hối nạp IBKR (`>= 250–500 tr VND`):** `TT 20/2022/TT-NHNN` không cho cá nhân cư trú VN tự chuyển tiền từ ngân hàng nội địa ra nước ngoài mua chứng khoán/ETF. **Cấm** chuyển chui, P2P lách ngoại hối hoặc khai gian địa chỉ; phải tham vấn luật sư về nguồn ngoại tệ hợp pháp trước Nấc 3–4.
2. **Thuế TNCN Prop Payout:** Cư dân thuế VN (`>= 183` ngày/năm) chịu thuế toàn cầu; payout là thu nhập dịch vụ nước ngoài (**không phải kiều hối miễn thuế**). Cần kế toán chốt diện kê khai/thuế suất; tạm giữ `20%–30%` trong Giỏ 1 tới khi quyết toán.
3. **Chứng từ nguồn tiền & Lưu trữ `OPS-5` SHA-256:** Ưu tiên **SWIFT về ngân hàng VN** cho khoản lớn (tránh khóa tài khoản do P2P dính tiền bẩn). Lưu theo năm tại kho ngoại tuyến (`<OFFLINE_BACKUP>/compliance/YYYY/`, không đẩy Git Layer 1): sao kê thẻ `VND` (chứng minh hoàn gốc `EXTERNAL_CASH_REFUND`), hợp đồng, `Reward Invoice`, giấy báo có SWIFT và gói bất biến **`OPS-5` (`payout_audit_packager.py package` / `verify`)** có chuỗi băm **SHA-256**.
4. **Crypto CASP:** Giữ chạy bóng (`OrderSend = 0`) tới khi đối chiếu xong danh sách CASP cấp phép theo `NQ 05/2025/NQ-CP` & `TT 32/2026/TT-BTC`.

---

## 4. Quy Trình Vận Hành Hàng Tuần & Hàng Tháng (`OPS-4`, Ví Lạnh & Sổ Cái)

### 4.1. Đèn Giao Thông `OPS-4` (`ownbook_shadow_ops.py` — `OrderSend = 0`)
- 🟢 **`GREEN` (`1,0x` — Dev `2024-12-31`: `CEX 25%`, funding `9,29%`, `DD 2,34%`):** `CEX <= 25%`, funding 7 ngày `>= 3,0%/năm`, `4/4` stress PASS, `DD < 10%` -> giữ `60/10/15/15`.
- 🟡 **`AMBER` (Đã kiểm probe `1,20%`):** Kích hoạt khi nổ **`FUNDING_COMPRESSION_ALERT`** (funding 7 ngày **`< 3,0%/năm`** -> xoay `100%` Carry `15%` sang `SGOV/BIL` hoặc `IB01`, thành `30%` T-Bill & `10%` CEX), hoặc `CEX_CAP_CLAMPED`, hoặc `DD >= 10%`.
- 🔴 **`RED` (Dừng ngay):** `CEX > 25%` (`CEX_CAP_BREACH`), trượt `>= 1/4` stress test, `DD >= 20%`, hoặc lỗi toàn vẹn dữ liệu -> khóa mở mới, rút phần vượt trần về T-Bill/ví lạnh, điều tra `R4 -> R1`.

### 4.2. Kỷ Luật Lưu Ký & Lịch 1 Người Solo
- **Trần `CEX <= 25%` & Ví lạnh Self-Custody:** Giữ cứng tổng số dư sàn tập trung `<= 25%` (chia `>= 2` sàn hạng nhất từ `50k+`). Phần lõi **`CRYPTO_SPOT` (`10%`)** và lãi tích lũy rút định kỳ về **ví lạnh phần cứng (*hardware wallet*)** tự giữ khóa ngoại tuyến; chỉ để trên sàn phần ký quỹ `Carry` (`15%`, đệm `2,0x`, đòn bẩy Perp đúng `1,0x`, tách biệt cross-margin) và phần Spot cần xoay vòng.
- **Hằng tuần (Thứ Bảy, `10–15` phút):** Chạy offline `ownbook_shadow_ops.py` kiểm đèn `OPS-4` và funding 7 ngày (`< 3%` -> xoay T-Bill); kiểm tỷ lệ `CEX` sau biến động giá (nếu `> 25%` -> chốt bớt về T-Bill/ví lạnh); kiểm đệm ký quỹ Carry `>= 2,0x`.
- **Hằng tháng (Ngày `1`, `20–30` phút):** Tái cân bằng theo lịch **`Monthly_1st`** (`0,45 bps/năm`) hoặc **`DriftBand 3%`** (`0,09 bps/năm`, tránh đảo hàng ngày theo [QUANT-POD-V2](QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md)); ghi đủ sự kiện (`PAYOUT_SETTLED`, `OWN_BOOK_DEPOSIT`, `OWN_BOOK_PNL`, `OPS_CASH_OUT`, `TAX_PAID`) vào `treasury_ledger.py`, xuất GIPS-Lite TWR (tách rõ `SIMULATED_*` vs `LIVE_VERIFIED`), và lưu gói sao kê `OPS-5` SHA-256.

---

## 5. Thang Đánh Giá Sổ Vốn Riêng (Tầng 3 Luật 15 — Danh Sách Dọc Chấm Màu)

**4 điểm neo thực tế (Tầng 3 — Sổ Vốn Riêng Đa Tài Sản):**
- **Bộ chỉ số cân bằng (`Guarded Dev 2020–2024`, `1x`):** `CAGR +6,69%` · `AnnVol 4,83%` · `Sharpe 1,36` · `Sortino 1,24` · `MaxDD 8,09%` · `Calmar 0,83` · `2022 DD 7,87%` vs `60/40` `20,69%` · Tháng đói thuần `~36,7%` (`28,3%–31,7%` khi ghép cùng Prop `7E`) · `4/4` Stress PASS.
- **Quy đổi VND/USD:** `20k USD` (`515,3 tr`) ~ `+34,5 tr/năm`, DD `~41,7 tr`; `50k USD` (`1,29 tỷ`) ~ `+86,2 tr/năm`, DD `~104,2 tr`.
- **Cấp độ bằng chứng:** `DEV_BACKTEST_2020_2024_PRE_HOLDOUT` (`holdout_rows_analysed = 0`) — hiện có **`0` tháng tiền thật (`0 VND`)**.
- **Ngưỡng gãy:** Mở `< 10k USD` (phí IBKR ăn `137–534 bps/năm`); bỏ khiên funding `< 3%` (Carry lỗ `-1,0%`); vi phạm `CEX > 25%` hoặc Perp `> 1x`; giữ US ETF `> 60k USD` dính rủi ro thuế di sản Mỹ `40%`.

**Định vị dọc Tầng 3 (chấm riêng cho Own-Book, không dùng trần bot Prop CFD đơn lẻ):**
- 🔴 **Xấu:** `Sharpe < 0,6`, `Calmar < 0,5`, `MaxDD > 15%`, để `CEX > 25%`, Perp `> 1x`, thiếu chứng từ nguồn tiền hoặc dính PTP `1446(f)`.
- 🟡 **Đủ dùng — HIỆN TẠI VỀ BẰNG CHỨNG THỰC ĐỊA & `CALMAR` (`Calmar 0,83`, `0` tháng thật, `0 VND`):** Đã rõ khiên phòng thủ và chi phí, nhưng chưa đủ vốn `250–500 tr VND` và chưa chạy tiền thật.
- 🟢 **Tốt — HIỆN TẠI CỦA KIẾN TRÚC TRÊN DEV (`Sharpe 1,36`, `MaxDD 8,09%`, `2022 DD 7,87%`, `4/4` Stress PASS, `CEX <= 25%`, `OPS-4` xanh):** Đạt chuẩn phòng thủ rủi ro đuôi trên Dev `<= 2024-12-31`, sẵn sàng giải ngân khi Giỏ 3 đủ ngưỡng.
- 🏆 **Top 1% thực tế (Mục tiêu Tầng 3):** `Sharpe 1,8 – 2,5`, `Calmar >= 2,0`, `MaxDD <= 7%–10%`, tháng đói `< 30%`, đo **`>= 12` tháng tiền thật** kiểm toán GIPS-Lite, chuẩn UCITS Ireland, `0` sự cố lưu ký/pháp lý và vượt `Crossover`.

**`3` khoảng trống tới `🏆 Top 1%`:** (1) Tích từ `0 VND` lên `>= 250–500 tr VND` từ Giỏ 3 và đủ `>= 12` tháng `LIVE_VERIFIED`; (2) Nâng `Calmar 0,83 -> >= 2,0` bằng chạy đồng bộ `3` nhánh lệch pha (Prop `7E` + ETF + Crypto `CEX <= 25%`); (3) Chốt tư vấn pháp lý/thuế VN về đường nạp IBKR và CASP trước khi giải ngân lớn.

---

## 6. Hành Động Kế Tiếp (`< 2` Phút, `0 VND`, `OrderSend = 0`)

Chạy lệnh kiểm tra offline xác nhận đèn `OPS-4` và `4/4` bài kiểm sốc Sổ Vốn Riêng xanh trên dữ liệu Dev niêm phong `<= 2024-12-31`:

```powershell
.\.runtime\quant-audit-v24\Scripts\python.exe tooling\ai-engines\quant_factory\wave4\ownbook_shadow_ops.py --cutoff-date 2024-12-31 --ibkr-capital-usd 50000
```
