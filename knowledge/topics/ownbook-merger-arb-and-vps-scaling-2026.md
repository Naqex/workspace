---
doc_type: evergreen
domain: knowledge
topic: ownbook-merger-arb-and-vps-scaling-2026
updated_utc: 2026-11-25
holdout_rows_analysed: 0
order_send_count: 0
sources:
  - "T1 (Học thuật): Mitchell & Pulvino (2001) JF 56(6); Baker & Savasoglu (2002) JFE 64(1); Jetley & Ji (2010) FAJ 66(2)"
  - "T1 (Chính thức): SEC EDGAR, MNA (NYLI), ARB (AltShares), SGOV/IB01 (iShares/BlackRock), IBKR Pro/CA/PTP 1446(f), AWS Lightsail, Vultr, Hetzner, ForexVPS, QuantVPS, Beeks"
  - "T1 (Nội bộ < 2025-01-01): .runtime/etf40-cache & .runtime/macro-etf-cache (2008–2024), MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md, alpha-hypothesis-ledger.md"
  - "T2/T3: Đo ping LD4 tới FTMO/The5ers; thực tế chào mua tự nguyện & thuế NRA trên IBKR"
---

# Thẩm định `F15` Sáp nhập Tiền mặt, Neo Tiền mặt & Kinh tế học VPS LD4/NY4 (`2026`)

> **Kỷ luật Bằng chứng:** Phân tách **`T1`** (học thuật, tài liệu chính thức, thực nghiệm nội bộ khóa cứng `max_date < 2025-01-01`, `holdout_rows_analysed = 0`, `OrderSend = 0`) với **`T2/T3`** (đo độc lập & cộng đồng). Không mở quyền đặt lệnh hay chạm Holdout `2025+`.

## Bảng Quyết định Điều hành

| Chuyên đề | Phán quyết | Ngưỡng vốn kích hoạt | So với Hệ thống Naqex Đương kim | Hành động |
|---|---|---|---|---|
| **1. Astra `F15` Cash Merger Arbitrage (DIY cổ phiếu lẻ)** | **`KILL`** *(DIY solo `< 100K USD`)* | Không DIY `< 100K` *(trên `100K` chỉ xét ETF `ARB` nếu T-Bill `< 2%`)* | Thua **`75% SGOV + 25% (B06+B02)`** (`Cl.B +4,80%`, `MDD 0,92%`, `Sh 2,70` vs `MNA +0,09%`, `ARB +4,21%`) | **Đóng hàng đợi DIY `F15`**, không mở Lab SEC |
| **2. Neo `75%` Tiền nhàn rỗi (`SGOV/BIL` vs Trái phiếu/Vàng/USD)** | **`GIỮ THUẦN SGOV`** *(`< 50K`)* → **`IB01` UCITS** *(`>= 50K–60K`)* | `< 50K`: `SGOV` (`0,09%`, hoàn QII `~0%`); `>= 50K–60K`: `IB01` (`0,07%`, né thuế di sản Mỹ `60K`) | Động lượng trái phiếu `SHY/IEF/TLT/TIP` **âm `-0,24%..-4,26%`** trên `2021–2024` (thua `BIL +2,84%`); `UUP` dính thuế PTP `1446(f)` `10%` giá bán | **Giữ `100% SGOV`** dưới `50K USD`; không xoay vòng trái phiếu |
| **3. Nâng cấp VPS Equinix LD4/NY4 (thay `naqex-node1` `0 USD`)** | **`GIỮ HOME-VPS < 50K`** → **`LD4 TỪ 75K–100K FUNDED`** | `50K`: đệm **Lightsail London `22 USD/tháng`**; **`>= 75K–100K`**: **LD4 `35–45 USD/tháng`** | Ở `10K–25K`, LD4 `35 USD` ăn **`21%–66%`** lãi ròng, hòa vốn `0,64–1,60 bps` RT (`0,95–2,38` pips) — vô lý vì `7E` miễn nhiễm `50 ms` vs `150 ms` | **Giữ `naqex-node1`** suốt `10K–25K`; nâng đúng theo 2 cổng mục 3 |

---

## 1. Astra `F15` — Chênh lệch Sáp nhập Tiền mặt cho Trader Cá nhân

### 1.1. Bằng chứng Học thuật & Quỹ ETF Thực chiến (`T1`)
`F15` ([ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md](../../planning/research/ASTRA-INDEPENDENT-REDTEAM-AUDIT-20261125.md)) mua cổ phiếu mục tiêu sau khi công bố thâu tóm tiền mặt (`SEC 8-K / DEFM14A / Schedule TO`, [sec.gov](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)) để hưởng chênh lệch `+2%..+5%` trong `30–120` ngày. Ba bằng chứng `T1` bác bỏ lợi thế DIY solo:
- **Bất đối xứng kiểu bán Put (`T1`):** Mitchell & Pulvino (2001, *JF* `1963–1998`, [PDF](https://andreisimonov.com/N4106/pdf/MitchellPulvinoJFDec2001.pdf)) chứng minh các thương vụ **đổ vỡ cụm lại đúng lúc thị trường sập** (beta nhảy vọt). Baker & Savasoglu (2002, *JFE*) xác nhận phần bù chỉ là tiền gánh rủi ro vỡ thương vụ.
- **Biên lãi bị nén `> 400 bps` (`T1`):** Jetley & Ji (2010, *FAJ* `1990–2007`) chỉ ra vốn quỹ đầu cơ đã ép biên thương vụ "sạch" sát T-Bill; muốn lãi cao phải chịu rủi ro chống độc quyền (`FTC/DOJ/CFIUS`).
- **ETF thực chiến `2021–2024` (`T1`):** Quỹ chuyên nghiệp có đội pháp lý vẫn thua rổ Own-Book Naqex:

| Quỹ / Rổ (`T1`) | Phí/năm | `2021` | `2022` | `2023` | `2024` | **CAGR `21–24`** | MaxDD | Ghi chú |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`MNA`** ([nylim](https://www.newyorklifeinvestments.com)) | `0,78%` | `-3,27%` | `-1,49%` | `+0,36%` | `+4,96%` | **`+0,09%`** | `-10%..-12%` | Thụ động; 10 năm chỉ `~2,7%–3,5%` |
| **`ARB`** ([altshares](https://www.altsharesetfs.com)) | `0,76–0,82%` | `+3,20%` | `+4,04%` | `+5,58%` | `+4,04%` | **`+4,21%`** | `-3%..-5%` | Chủ động (`30–80` deal, AUM `~110,6 tr USD`) |
| **`BIL`** (cục bộ) | `0,135%` | `-0,10%` | `+1,40%` | `+4,94%` | `+5,19%` | **`+2,84%`** | **`0,13%`** | `SGOV` (`0,09%`) cao hơn `~+0,05%/năm` |
| **`75% SGOV + 25% (B06+B02)`** | `~0,07%` + spot | — | Dương | Dương | Dương | **`+4,80%`** | **`0,92%`** | **`Sharpe 2,70`**, `r(7E) +0,061`, từ `3K USD` |

### 1.2. Toán học `EV`, Đa dạng hóa & Ma sát IBKR Pro (Cư dân Việt Nam)
Theo `EV = p*C + (1-p)*B - A - r*A*T - k` (`T = 90` ngày, `SGOV` `r = 3,9%`, hoàn tất ngành `p = 90%–92%`, lỗ vỡ `-25%..-35%`): ở `p = 92%`, chênh `+3,5%`, vỡ `-30%`, lãi gộp chỉ `+0,82%/quý` (`+3,28%/năm`) — **thua `SGOV` `-0,62%/năm` trước cả phí**. Chỉ vượt `SGOV` `+1,54%/năm` (dùng vốn `75%`) nếu lọc tới `p = 94%`.

Để 1 cú vỡ `-30%..-40%` không vượt `1,5%–2,0%` tài khoản cần tối thiểu **`N = 20–25` thương vụ đồng thời**. Cư dân VN bắt buộc dùng **IBKR Pro** ([interactivebrokers.com/en/pricing](https://www.interactivebrokers.com/en/pricing/commissions-home.php): sàn `0,35 USD` Tiered `+ ~0,05` phí sở; hoặc `1,00 USD` Fixed). Với `4` vòng/năm, `1,5` lệnh/deal và `12 bps` spread RT:

| Vốn (USD) | Deal | Cỡ lệnh | Sốc 1 vỡ (`-30%/-40%`) | Tiered (`+48 bps` spr) | Fixed (`+48 bps` spr) | Cổ @ `60 USD` (`%` lẻ) | Khả thi Solo VN |
|---:|---:|---:|---:|---:|---:|---:|---|
| `10.000` | `20` | `500 USD` | `-1,5% / -2,0%` | `48,0` (**`96,0 bps`**) | `120,0` (**`168,0 bps`**) | `8` (`4,0%`) | **CHẾT** (phí nuốt hết phần bù) |
| `25.000` | `20` | `1.250 USD` | `-1,5% / -2,0%` | `19,2` (**`67,2 bps`**) | `48,0` (**`96,0 bps`**) | `20` (`4,0%`) | **KÉM** (ăn gần nửa phần bù) |
| `50.000` | `20` | `2.500 USD` | `-1,5% / -2,0%` | `9,6` (**`57,6 bps`**) | `24,0` (**`72,0 bps`**) | `41` (`1,6%`) | **YẾU** (dính 3 rào cản dưới) |
| `100.000` | `20` | `5.000 USD` | `-1,5% / -2,0%` | `4,8` (**`52,8 bps`**) | `12,0` (**`60,0 bps`**) | `83` (`0,4%`) | **THUA `ARB` & Pod sẵn có** |

**3 rào cản khóa phán quyết `KILL` (`< 100K USD`):** (1) *IBKR Corporate Actions* chốt hạn chào mua tự nguyện **sớm `24–48h` trước hạn SEC** ([IBKR Support](https://www.interactivebrokers.com/en/support/individuals.php)), cổ phiếu lẻ dễ kẹt bầu chọn; (2) Dữ liệu chống survivorship bias (`Capital IQ / MergerMetrics`) tốn hàng chục nghìn USD/năm; (3) **VN–Mỹ chưa có hiệp định thuế có hiệu lực** (bản `2015` chưa phê chuẩn) → khấu trừ **`30%`** cổ tức/cổ tức đặc biệt, và cổ phiếu Mỹ vượt **`60.000 USD`** chịu **thuế di sản Mỹ tới `40%`**.

---

## 2. Kiểm định Neo `75%` Tiền Nhàn Rỗi (`2008–2024`, `< 2025-01-01`)

Backtest nhân quả (`t -> t+1` cuối tháng) trên `.runtime/etf40-cache` (khớp `.runtime/macro-etf-cache`), **`2008-01-02..2024-12-31` (`4.429` phiên, `holdout_rows_analysed = 0`)**, phí IBKR Pro Tiered trên phần neo `75%` của sổ `10K/15K/25K USD` (`7,5K / 11,25K / 18,75K USD`):

| Chiến lược Neo (`Net @ 15K -> 11,25K Neo`) | `08–24` (Vượt `BIL`) | `Ex-Sh` (`p` NW) | `MDD` | Cl.A `08–20` (`MDD`) | **Cl.B `21–24` (Vượt `BIL`, `MDD`)** | `2022` (`DD`) | Phí (`10/15/25K`) | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`A0_PURE_BIL` (`SGOV/BIL`)** | **`1,04%`** (`0,00%`) | `0,00` (`1,000`) | **`0,78%`** | `0,49%` (`0,78%`) | **`+2,84%` (`0,00%`, `0,13%`)** | **`+1,40%` (`0,03%`)** | **`0/0/0`** | **`TỐI ƯU`** |
| `A1_MOM (BIL/SHY/IEF 6M)` | `2,51%` (`+1,47%`) | `+0,30` (`0,092`) | `10,75%` | `3,48%` (`10,75%`) | **`-0,58%` (`-3,43%`, `5,96%`)** | `+1,36%` (`0,03%`) | `14,2/13,8/13,8` | `LOẠI` |
| `A2_MOM (BIL/SHY/IEF/TLT 6M)` | `3,25%` (`+2,21%`) | `+0,24` (`0,143`) | `25,48%` | `5,67%` (`25,48%`) | **`-4,26%` (`-7,10%`, `19,17%`)** | `-2,61%` (`2,91%`) | `18,0/17,4/17,4` | `LOẠI` |
| `A3_MOM (BIL/SHY/IEF/TIP 6M)` | `3,36%` (`+2,32%`) | `+0,44` (`0,023`) | `7,75%` | `4,49%` (`7,75%`) | **`-0,24%` (`-3,09%`, `5,96%`)** | `-2,73%` (`3,72%`) | `16,9/16,3/16,3` | `LOẠI` |
| `A4_50%BIL + 50%Mom(SHY/IEF)` | `1,81%` (`+0,77%`) | `+0,31` (`0,083`) | `4,72%` | `1,96%` (`4,72%`) | **`+1,35%` (`-1,50%`, `1,93%`)** | `+1,38%` (`0,03%`) | `9,3/8,3/7,6` | `LOẠI` |
| `A5_80%BIL+10%GLD+10%UUP` *(PTP)* | `1,87%` (`+0,83%`) | `+0,53` (`0,011`) | `4,22%` | `1,23%` (`4,22%`) | `+3,98%` (`+1,14%`, `1,18%`) | `+2,11%` (`1,03%`) | *(Thuế PTP)* | **`CẤM 1446(f)`** |
| `A6_70%BIL+15%GLD/15%UUP SMA200` | `1,75%` (`+0,71%`) | `+0,34` (`0,074`) | `7,31%` | `1,32%` (`7,31%`) | `+3,15%` (`+0,31%`, `2,84%`) | `+1,73%` (`1,23%`) | `5,3/4,2/3,4` | `LOẠI` |
| `A7_70%BIL+30%Mom 5 phòng thủ` | `1,94%` (`+0,90%`) | `+0,49` (`0,018`) | `3,39%` | `1,85%` (`2,67%`) | **`+2,25%` (`-0,59%`, `3,39%`)** | `+0,85%` (`2,20%`) | `13,4/10,1/7,4` | `LOẠI` |
| *Không PTP:* `90%BIL + 10%GLD` | `1,71%` (`+0,68%`) | `+0,39` (`0,050`) | `5,61%` | `13–16: -0,88%` | `+3,44%` (`+0,60%`, `1,86%`) | — | `~1–2 bps` | `Tăng DD 7×` |

**Kết luận mục 2 (`KEEP_PURE_SGOV_UNDER_25K`, đồng nhất [alpha-hypothesis-ledger.md](alpha-hypothesis-ledger.md)):**
1. **Động lượng Trái phiếu (`A1–A4`) gãy khi lãi suất tăng `2021–2024`** (`-1,50%..-7,10%/năm` dưới `BIL`, `DD 6%–19%`), phá chức năng neo tiền mặt.
2. **Bẫy thuế `IRC 1446(f)` trên `UUP` (`T1`):** `UUP` là *Publicly Traded Partnership (PTP)*. Từ `01/01/2023`, cư dân ngoài Mỹ bán PTP bị thu **`10%` trên TỔNG GIÁ TRỊ BÁN** (kể cả lỗ) và IBKR chặn mặc định ([IBKR Non-US Tax](https://www.interactivebrokers.com/en/support/tax-nonus-general.php)). Bỏ `UUP` chỉ giữ `10% GLD` làm `MaxDD` nhảy `7×` (`0,78% -> 5,61%`), làm xấu độ mượt `0,92%` của `75% SGOV + 25% B06/B02`.
3. **Chọn mã theo quy mô (`T1` BlackRock):** Dưới `50K USD` giữ **`SGOV`** (`0,09%` ER, lợi suất `30d SEC ~3,65%–3,90%`, [ishares.com](https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf); IBKR hoàn tự động `30%` khấu trừ tháng `1–2` năm sau nhờ `~100%` QII). Từ **`50K–60K USD`**, chuyển sang UCITS Ireland **`IB01`** (`IE00BGSF1X88`, `TER 0,07%`, tích lũy, [blackrock.com](https://www.blackrock.com)) để **miễn `100%` thuế di sản Mỹ** và khỏi giam tiền chờ hoàn QII.

---

## 3. Kinh tế học Nâng cấp VPS Equinix LD4 / NY4 (`2026`)

### 3.1. So sánh Hạ tầng VPS Windows `2026` (`T1` Bảng giá + `T2/T3` Ping LD4)
Máy chủ MT5 của **FTMO** & **The5ers** nằm tại **Equinix LD4 (London)** (`T2/T3`). Hai quỹ cấm VPN tiêu dùng nhưng chấp nhận VPS có **Dedicated IPv4**:

| Nhà cung cấp (`2026`) | Datacenter | Cấu hình & Windows | Giá/tháng (Trả năm) | Ping LD4 | Phù hợp |
|---|---|---|---:|---:|---|
| **`naqex-node1` (Home-VPS)** | VN (`+ Heroku EU`) | Win 10 IoT LTSC sẵn có | **`0 USD`** | `~180–250 ms` *(fill `363–397 ms`)* | **Số 1 `< 50K` Funded** |
| **AWS Lightsail** ([aws](https://aws.amazon.com/lightsail/pricing/)) | London `eu-west-2` | `2c / 2 GB / 60 GB`, **kèm Win + Static IP** | **`22 USD`** (`4 GB: 44`) | `~1–2 ms` | **Đệm tốt nhất `50K–75K`** |
| **ForexVPS.net** ([forexvps](https://www.forexvps.net)) | **Equinix LD4/NY4** | `Core 2c/4G`; `Edge 4c/6G`, Dedicated IP, Win | **`40` (`32` năm)**; `Edge 60` (`48`) | **`~0,5–2 ms`** | **Chuẩn nhất `75K–100K+`** |
| **QuantVPS** ([quantvps](https://www.quantvps.com)) | **LD4 / NY4** | `2c / 4 GB / 50 GB NVMe`, kèm Win | **`~30–40`** (`+: 40–60`) | **`~1–2 ms`** | Hợp nếu thêm CME Futures |
| **Beeks FX** ([beeksgroup](https://www.beeksgroup.com)) | **Colocated LD4/NY4** | `Bronze 1c/2,5G`; `Silver ~4G` *(giá `GBP`)* | **`~38–42`** (`+OS/VAT`); `Silver ~59` | **`~0,5–1,5 ms`** | Uy tín, RAM/giá kém `ForexVPS` |
| **Vultr London** ([vultr](https://www.vultr.com/pricing/)) | London (LINX) | Compute `6–24` **+ Win riêng `>= 16 USD`** | **`~22–45+ USD`** | `~2–5 ms` | Kém gọn hơn Lightsail |
| **Hetzner Cloud** ([hetzner](https://www.hetzner.com/cloud)) | **Không có London** | Linux gốc; Win phải **BYOL** | `~5–15 EUR` *(chưa Win)* | `~8–15 ms` *(FRA)* | **LOẠI cho LD4** |

### 3.2. Toán học Hòa vốn Trượt giá `PORT_7E` (`450–469` lệnh/năm) & Cổng `<= 10%` Lãi ròng
Đo trực tiếp **`469` lệnh `2024`** ([MUI3](../../planning/research/MUI3-MASTER-PROP7E-REALTICK-2024-20261125.md), `holdout_rows_analysed = 0`) ở `10.000 USD` Funded (`1,0x`): danh nghĩa 1 chiều = **`3.411.687 USD/năm`** (`USDJPY 2,304M`, `GBPUSD 0,491M`, `US100 0,449M`, `EURJPY 0,168M`), quy chuẩn `450` lệnh = **`3.273.500 USD/năm`**. Tỷ lệ quy đổi FX thực đo: **`1 FX pip = 0,675 bps`**. Do trader trả `100%` tiền VPS nhưng chỉ nhận **`80%`** chia lãi, hòa vốn túi tiền đòi hỏi tài khoản tiết kiệm **`C_vps / 0,80`** trượt giá gộp; lãi ròng túi tiền bảo thủ = **`6,4%–8,0%/năm`** (`8%–10%` × `80%`):

| Funded (USD) | Lãi ròng túi (`6,4–8,0%`) | Gói VPS (`USD/tháng · /năm`) | VPS / Lãi (`<= 10%`?) | **Trượt giá hòa vốn (`450` lệnh/năm)** *(RT / mỗi chiều)* | Kết luận +EV |
|---:|---:|---|---:|---:|---|
| **`10.000`** | `640–800 USD` | Lightsail `22` / LD4 `35` / `60` | `33–41%` / **`53–66%`** / `90–113%` | **`1,01` / `1,60` / `2,75 bps` RT** (`1,49` / **`2,38`** / `4,07` pips) | **ÂM EV NẶNG** — Giữ `naqex-node1` |
| **`25.000`** | `1.600–2.000 USD` | Lightsail `22` / LD4 `35` / `60` | `13–17%` / **`21–26%`** / `36–45%` | **`0,40` / `0,64` / `1,10 bps` RT** (`0,60` / **`0,95`** / `1,63` pips) | **ÂM EV** — Giữ `naqex-node1` |
| **`50.000`** | `3.200–4.000 USD` | **Lightsail `22`** / LD4 `35` / `60` | **`6,6–8,2%` ĐẠT** / `10,5–13%` / `18–23%` | **`0,20` / `0,32` / `0,55 bps` RT** (`0,30` / `0,48` / `0,81` pips) | **ĐỆM:** Cân nhắc **Lightsail `22 USD`** |
| **`75.000`** | `4.800–6.000 USD` | **LD4 `35` (`420`)** / `45` (`540`) | **`7,0–8,8%` ĐẠT** / `9,0–11,2%` | **`0,21` / `0,27 bps` RT** (`0,32` / `0,41` pips · `0,16` pip/chiều) | **BẮT ĐẦU +EV** cho LD4 `32–35 USD` |
| **`100.000`** | `6.400–8.000 USD` | **LD4 `35` / `45`** / `60` (`720`) | **`5,2–6,6%` / `6,8–8,4%` ĐẠT** / `9–11%` | **`0,16` / `0,21` / `0,27 bps` RT** (**`0,24` / `0,31`** / `0,41` pips) | **CHẶT CHẼ +EV** cho LD4 `35–45 USD` |
| **`150.000`** | `9.600–12.000 USD` | **LD4 Pro `60` (`720`)** | **`6,0–7,5%` ĐẠT** | **`0,18 bps` RT** (`0,27` pips · `0,13` pip/chiều) | **CHẶT CHẼ +EV** cho gói `60 USD` |

**Khớp chứng cứ `MUI3` & Quy tắc Nâng cấp:** Trên `20,02M` tick thật (`Model=4`), `PORT_7E` **miễn nhiễm `50 ms` vs `150 ms`** (`+754,60` vs `+755,69 USD` ở `4,0x`), vì giữ lệnh `1–12h`, SL `~40–70` pip và khóa tin đỏ `±5` phút. Lợi ích thực của LD4 chỉ quanh **`~0,10–0,30` pip RT (`0,07–0,20 bps` RT)** cộng giá trị chống cúp điện/mạng VN. Do đó: **giữ cứng `naqex-node1` (`0 USD`) dưới `50K` Funded**; cân nhắc **Lightsail London `22 USD`** ở `50K–75K` nếu TCA báo lỗi mạng; chỉ nâng **Equinix LD4 `32–45 USD/tháng` từ `75K–100K` tổng Funded** (chạy chung nhiều tài khoản) và gói `60 USD` từ **`115K–150K+ USD`**.
