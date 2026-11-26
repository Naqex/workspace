# Current context — Naqex Workspace

`26/11/2026 16:45 ICT` · `WORK: STEP4-HARDENING-RESTART-Q2-AND-DECOMP-COMPLETE | HALTED_AT_PARITY_GATE | 0-VND | LIVE-NODE1: ONLINE-CONNECTED-FLAT | HOLDOUT 2025+ SEALED`

`GOAL-NOW: BƯỚC 4 HOÀN TẤT (4.1 FAIL-CLOSED + 5/5 ĐỘT BIẾN ÂM | 4.2 RESTART 2 TIẾN TRÌNH NGOÀI TESTER 100% | 4.3A Q2 5/5 MT5 PASS & 622/622 KHÔNG HỒI QUY | 4.3B PHÂN RÃ 4 TẦNG CÒN 0,00 USD DƯ) | GIỮ CỔNG KINH TẾ DỪNG & 0 VND | CHỜ ASTRA VÒNG 8`

## 0. Trạng Thái Hiện Tại Sau Bước 4 (`26/11/2026`)

- **Bước 4 — Siết Bộ So Sánh, Diễn Tập Restart 2 Tiến Trình, Kiểm Riêng `Q2` & Phân Rã 4 Tầng ([STEP4 Report](research/STEP4-HARDENING-RESTART-Q2-AND-DECOMP-AUDIT-20261126.md)):**
  - **Bước 4.1 (Fail-closed + 5/5 đột biến âm + sửa `MathRound`):** Bỏ hẳn `OnDeinit` `margin_1lot_sample/ref_ask_sample` (dùng công thức hợp đồng tĩnh đầu kỳ); siết bộ so sánh kiểm toàn trường (`equity`, `reason` nguyên văn, `norm_sl`, `raw_lots`, `factor_headroom`, trả `exit 2`); bắt và vá lỗi làm tròn `round()` vs `MathRound()` MQL5. Kết quả: `edge_holiday` (`window_seeded`) **`16/16` deal, `638/638` sự kiện (`max Δbal 0,00 / Δeq 0,14 USD`)**, `edge_dst` (`window_seeded`) **`30/30` deal (`6/6` SL `0s`), `60/60` sự kiện (`0,00 / 0,00 USD`)**, **5/5 đột biến âm bị chặn** (`exit 0` sạch, `exit 2` khi bơm `equity +123,45 USD`).
  - **Bước 4.2 (Diễn tập restart 2 tiến trình MT5 thật ngoài Tester — `Q3a`):** Thêm lưu trạng thái cơ hội (`naqex_opp_state_<login>_<srvhash>.txt`, `RestoreOppStateOnce` không lặp `OPP_START`) và đóng chờ (`PendingCloseFileName`) chỉ chạy khi `!MQL_TESTER`. Chạy qua **2 tiến trình OS tách biệt (`PID 14472 → 17576`)** khóa proxy cô lập `127.0.0.1:1`, `AllowLiveTrading = 0`, `0` `OrderSend`: **`all_restart_invariants_passed = True`** (neo Prague + `autoKill`, `HydrateTradedDays` fail-closed, tiếp tục `OPP_E6` `eval 12 → 13` không lặp `OPP_START` → hết hạn `1` lần → tái vào `ep_seq = 2`, đóng chờ không lật sớm `ProfitLock`). `naqex-node1` nguyên vẹn `ONLINE GREEN`.
  - **Bước 4.3A (Kiểm riêng `Q2` `InpPostCloseRefreshMode = 0` mặc định, `5` lượt `Model=4`, `30` tệp gốc):** Tại `18:00:00` sau khi `E1` đóng lãi `+103,31 USD` (`0,2085% → 1,2416%`), `refresh = 0` giữ `NORMAL@4,0×`, `refresh = 1` lật ngay `PROFIT_LOCK@2,0×` trên ảnh chụp nhất quán (`bal=10.124,16 / eq=10.138,47`), và ở `Mult = 0,20` hạ lot thật `0,10 → 0,01 lot`. Trên 4 tháng (`C10 P2` `9` lần, `C00 P1` `2` lần `POST_CLOSE_REFRESH`), khớp nguyên văn **`622/622` deal (`+0,00 USD`)** với `refresh = 0`. Biên dịch **`0 errors, 0 warnings`** (`.ex5` `b548fbbb7cc554a7`), `8/8` parity, `130` SHA kit, `System Doctor [FULL]` **`10/10 PASS` (`1.816` test)**.
  - **Bước 4.3B (Phân rã đối chứng 4 tầng `L0 → L4` — chẩn đoán nguồn gốc, `0,00 USD` dư):** Trên `5.347.386` chu kỳ (`01/09–30/12/2024 23:54`): **`C10 P2`** (`+38,11 USD` mù `L0` = `+12,50` trượt SL trực tiếp + `+23,61` dây chuyền SL + `+2,10` đệm `tick_value_loss` khi phẳng `- 0,10` đệm tỷ giá chéo `EURJPY` = **`0,00 USD` dư, `0` lệch lot**); **`C00 P1`** (`+18,14 USD` mù `L0` = `+8,87` trượt SL trực tiếp + `+2,85` dây chuyền SL + `+6,53` đệm `tick_value_loss` `- 0,11` đệm `EURJPY` = **`0,00 USD` dư, `0` lệch lot**).
  - Kho bằng chứng gốc: `private_vault/strategies/step4-hardening-restart-q2-20261126/` (`30` tệp log thô Q2 + `10` tệp diễn tập restart + báo cáo JSON `4.1 / 4.2 / 4.3A / 4.3B`).
- **Các bước lịch sử đã kiểm toán:** [STEP3 Report](research/STEP3-V102AB-MERGED-AND-CONTINUOUS-REPLAY-AUDIT-20261126.md) (đã đính chính phạm vi Vòng 7) · [STEP2 Report](research/STEP2-V102AB-ISOLATED-AND-PYTHON-REPLAY-AUDIT-20261126.md) (`48/48`) · [STEP1 Report](research/STEP1-V101-PREDECISION-OBSERVABILITY-AND-FORMULA-PARITY-20261126.md) (`44/44`) · [Sprint 6 giờ](research/SPRINT-6H-STANDARD-PARITY-AND-C00-VS-C10-AUDIT-20261126.md) (`90/90`).

## 1. Kiến Trúc Đã Khóa & Khóa An Toàn Bất Biến

- **Hợp đồng chuẩn:** [prop_contracts_v2.json](../tooling/ai-engines/configs/prop_contracts_v2.json) đã có đủ `ftmo_swing_10k`, `ftmo_standard_10k` (chính thức mới), `the5ers_hs_5k`; `3` preset `C10` mới giữ cứng `DryRun = true`, `4` preset `C00` v1.01 giữ nguyên.
- **Kiến trúc `2` trụ cột gọn sạch (`3 / 56 PASS` ngoài CFD):** (1) Prop Cash-Flow (`PORT_7E` cố định `E1..E7`, `swap = 0`, loại vĩnh viễn `S7_XAU_EXP120`, khóa cụm hướng `USD/JPY/US100`); (2) Own-Book (`75% SGOV/IB01 + 25% Crypto Spot B06/B02 Shadow`, trần `CEX <= 25%`, hoãn dưới `10k USD`).
- **Khóa bảo mật 2 tầng & Holdout:** [NATIVE_FTMO_HOLDOUT_LOCK.json](research/NATIVE_FTMO_HOLDOUT_LOCK.json) niêm phong tuyệt đối (`holdout_rows_analysed = 0`); Layer-2 `private_vault/` tách hoàn toàn khỏi Layer-1 Public (được bảo vệ bởi `test_layer1_opsec_guard.py` và bộ kiểm thử biên mới [test_standard_parity_and_boundaries.py](../tooling/ai-engines/tests/test_standard_parity_and_boundaries.py)).

## 2. Trạng Thái Hạ Tầng `naqex-node1` & `3` Repo Sản Phẩm (`projects/`)

| Thành phần | Trạng thái xác minh | Ghi chú & Điểm kiểm soát |
|---|---|---|
| **Home-VPS `naqex-node1`** | **`ONLINE GREEN / UNTOUCHED`** | Không chạm suốt Bước 1–4; Free Trial Demo phẳng (`open=0`, `order_send_count=0`, `orphan=0`, `KeepPrivate=1`, `NTP -0,061s`, Heroku EU Deadman v4 `OK`, Geo-IP `VN`). |
| **MT5 Dev Portable cục bộ** | **`0% CPU / 0 tiến trình`** | Đã đóng sạch sau toàn bộ diễn tập restart & `5` lượt `Q2`, `0` tệp tạm `step4_*.htm/png/set/mq5/ex5`. |
| **`projects/trader` (`Naqex/trader`)** | **`main @ c5a44c4f` (`15/15` CI PASS)** | Không chạm trong Bước 1–4. |
| **`projects/quant-trading`** | **`master @ 25fc67d` (`pytest` 100% PASS)** | Không chạm trong Bước 1–4. |
| **`projects/vi-dubber`** | **`origin/main @ 5da3c65` (TẠM DỪNG)** | 4 tệp WIP cục bộ của chủ sở hữu giữ nguyên 100%. |
| **Giáo dục (`education/`)** | **`check_setup.py` exit `0`** | Đã có `education/tools/drill_generator.py` (`leverage_margin_vs_pnl`). |

## 3. Việc Kế Tiếp (Ưu Tiên Theo Thứ Tự Khóa Cổng — `0 VND`)

1. **Gửi Prompt Astra Vòng 8** trong mục 2 của [STEP4-HARDENING-RESTART-Q2-AND-DECOMP-AUDIT-20261126.md](research/STEP4-HARDENING-RESTART-Q2-AND-DECOMP-AUDIT-20261126.md) để chốt `3` câu hỏi: thăng hạng chính thức `v1.02` (`A + B + Q2`), mở bài toán so sánh kinh tế cùng pha `C00` vs `C10` trên Dev (`<= 2024`, nhạy trượt giá SL + đối chứng MT5 `Model=4`), và giữ/đổi `0 VND`.
2. **Giữ cổng kinh tế dừng & `0 VND`, không mở Holdout `2025+`:** Chỉ thay đổi quyết định tài chính sau phán quyết rõ ràng của chủ sở hữu & Astra Vòng 8.
3. **Thu thập chỉ đọc `QUOTE_ONLY` (`OrderSend = 0`) quanh NFP `04/12` & CPI `10/12`** theo mẫu [NFP-CPI-READONLY-CAPTURE-TEMPLATE.md](../tooling/ai-engines/exports/deployment_kit/NFP-CPI-READONLY-CAPTURE-TEMPLATE.md).
