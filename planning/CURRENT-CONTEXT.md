# Current context — Naqex Workspace

`24/11/2026` · `WORK: OVERNIGHT-8TIER-COMPLETE (26/26) | REVIEW: VERIFIER-APPROVED-ALL-LANES | DOC: COMPACTED-RESUMABLE`

`RESEARCH: 9/9 EX5 (0 ERR/0 WARN) + 90 PRESETS · RED-TEAM BE 2.26x · DUAL-P1 EV (THE5ERS +7.17x / FTMO +3.25x..+4.08x) · 4-SLEEVE POD OOS SHARPE 2.25 CALMAR 2.43 · PASS29-32 HONEST 0/66 + LOO TRAP · ORDERSEND=0`

## 1. Mục tiêu & Ràng buộc bất biến

- **North Star:** Hệ thống **One-Person Quant Pod 4 nhánh trực giao** — (1) **Intraday FX/Index Prop** (`PORT_7E`, `swap = 0`, Holdout mù `2025–2026` GO), (2) **Crypto Spot sạch survivorship bias** (`50` coin nhân quả), (3) **Crypto Delta-Neutral Funding Carry** (`2×` buffer, `0` thanh lý), và (4) **Cross-Asset Macro ETF 18 năm** cho vốn tự có — vận hành trên dây chuyền **Quant Factory 4 lớp** ([Bản tin sáng 24/11](MORNING-BRIEFING-20261124.md) · [Lộ trình prop](research/PROP-SYSTEM-ROADMAP.md)).
- **Ràng buộc an toàn bất biến:** Kho Development `.runtime/hot-m1-cache/` (`2018–2024`) và [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) khóa cứng (`holdout_rows_analysed = 0`); `OrderSend = 0` (`InpDryRunLogOnly = true` trên mọi `.mq5`); không sửa global config, `projects/vi-dubber` hay git của `projects/quant-trading`; không xóa dữ liệu ổ đĩa tự động.

## 2. Trạng thái Danh mục & Kiểm định Độc lập (Single Source: [PORTFOLIO-REGISTRY.json](research/PORTFOLIO-REGISTRY.json))

| Danh mục / Nhánh | Kiểm định Dev / Cl.A | Kiểm định Mù (Cl.B / Holdout) | Kết luận Hiện hành |
|---|---|---|---|
| **Nhánh #1 `PORT_7E + SYMCAP_100 + Red-News`** | Dev `+7,73% / DD 6,36%`, Red-Team BE **`2,26×`**, `5/5` khủng hoảng dương | **Holdout `2025–2026`:** **`+12,70% / DD 6,55% / Cal 1,94`** (`9/9` động cơ dương) | **GO — Sản xuất #1** (`9/9 .ex5` + `90 .set` sẵn sàng) |
| **Nhánh #2 Crypto Spot sạch (`F4_4H_EMA`, 50 coin)** | Cl.A `2019–2023`: `+16,30% / Sh 1,82 / DD 8,53%` | Cl.B mù `2024–2026`: **`+5,69% / Sh 0,78 / DD 9,72%`** (`BM -38,99%`, `DSR 0,991`) | **PASS** (đã tách `-6,6..-11,2 pp/năm` survivorship bias) |
| **Nhánh #3A Funding Carry (`CARRY_BTC_ETH_2XBUF`)** | Cl.A: `+7,69% / DD 0,95%` (`0` thanh lý FTX `-0,07%`) | Cl.B mù: **`+2,99% / DD 0,29% / Sh 9,06`** | **PASS** (trần `<= 15–35%` CEX counterparty cap) |
| **Nhánh #3B Macro ETF 18 năm (`M5_VOL_PARITY_TG`)** | Cl.A `2008–2018`: `+3,64% / Sh 0,61 / DD 10,45%` | Cl.B mù `2019–2026`: **`+7,58% / Sh 1,06 / DD 7,77%`** (`BH q=0,0062`, `DSR 0,958`) | **PASS** (`M1_TSMOM` dương cả GFC/COVID/2022) |
| **Pod 4 Nhánh (`ERC_Capped35`, `<= 35%` CEX)** | Overlap `2020–2024`, `r = -0,035..+0,149` | **OOS `2023–2024`:** **`+5,95% / Sh 2,25 / DD 2,45% / Cal 2,43`** | **GO** (Dashboard: `.runtime/pod_dashboard.html`) |

- **Dual-P1 EV Frontier (`10k` nhánh `seed=20261124`):** `P1_Balanced_3to6m` (`4,00×` → `2,50×` → `1,00×`, trượt `22,6%–23,8%`, EV/USD phí `+3,25×` FTMO Swing / `+4,08×` FTMO BF-25% / **`+7,17×` The5ers HS**); `P1_Sprint_1to3m` (`4,75×` → `2,75×` → `1,00×`, trượt `30%–33%`, P1 `1,6–2,0` tháng, CF24 `+738 USD` Swing).
- **Kỷ luật Pass 29–32 (Dev `< 2025`):** `0/66` false positives (`29: 0/24`, `30: 0/24`, `31: 0/18` bị `research_council` chặn sạch); **Pass 32** chứng minh cắt tỉa LOO in-sample làm sập OOS (`2,045 → 0,387`), giữ nguyên `PORT_7E` sản xuất và lưu `V08_PORT9E_CAUSAL_ERC` (`Cl.B Cal 1,596`, cần trần `<= 0,75%`/mã thưa lệnh) làm ứng viên v2.

## 3. Hạ tầng Full-Stack Quant Factory, MT5 Deployment Kit & Knowledge Vault

- **MT5 Production Kit (`tooling/ai-engines/exports/`):** `9/9` file `.ex5` đã biên dịch thật tại `.runtime/mt5-compiled-ex5/` (`0 errors, 0 warnings`), `mql5_parity_checker.py`, `verify_deployment_kit.py`, `10` cấu hình / `90` `.set` trong `exports/deployment_kit/`, lịch tin đỏ `2018–2027` (`343` dòng UTC), Watchdog gọn local/VPS `ops_watchdog/naqex_mt5_watchdog.ps1`.
- **Python Quant Factory (`tooling/ai-engines/quant_factory/`):** `red_team_auditor`, `prop_ev_frontier`, `postmortem_gen`, `research_council`, `portfolio_allocator`, `pod_dashboard`, `crypto_causal_universe`, `funding_rate_carry`, `macro_etf_trend`, `pass29..32`, `tca_reconcile`, `live_decay_monitor`, `ops_monitor` + `system_doctor.py --mode fast|full`.
- **Personal Knowledge Vault (`knowledge/`):** `PROFILE.md`, `CURIOSITY-LOG.md`, `DECISIONS-JOURNAL.md`, `6` cẩm nang Super-Indie mới + `alpha-hypothesis-ledger.md` (`0 PENDING`), `brain_cli.py` (SQLite FTS5 không dấu + Vector RRF `< 40 ms`, kiểm broken links & duplicates), `research_cli.py` + skill `research-and-memory-ops`.

## 4. Bước thực thi tiếp theo (trưa 24/11 khi Owner thức dậy)

1. Mở [MORNING-BRIEFING-20261124.md](MORNING-BRIEFING-20261124.md) và `.runtime/pod_dashboard.html` để xem toàn cảnh kết quả 8 tầng và 3 quyết định ngắn.
2. Kéo `9` file `.ex5` (`.runtime/mt5-compiled-ex5/`) + preset `FTMO_FreeTrial_DryRun` / `FTMO_FreeTrial_Demo` theo `ACTIVATION-CARD-LOCAL-MT5.md` để khởi động **FTMO Free Trial `14` ngày (`0 USD`)** trên máy Windows hiện tại và chạy `postmortem_gen.py` sau tuần 1.
3. Quyết định có chạy lệnh `robocopy` 1 dòng trong [STORAGE-HYGIENE-AUDIT-20261124.md](research/STORAGE-HYGIENE-AUDIT-20261124.md) để giải phóng `16,64 GB` sang `E:` và có mở nhánh promotion cho `projects/quant-trading` theo [CRYPTO-PROMOTION-SPEC-20261124.md](research/CRYPTO-PROMOTION-SPEC-20261124.md) hay chưa.
