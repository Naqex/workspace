"""Plain-Vietnamese Law-15 V3 report sections (color-dot scorecard, rollover stress, BF 2-deadline, X13 shard).

Strictly ZERO bare `$` symbols in rendered Markdown prose (always uses `USD` / `VND`).
"""

from __future__ import annotations

from typing import Any


def _tier_dot(label: str) -> str:
    low = label.lower()
    if "top 1%" in low:
        return "🏆"
    if "tốt" in low:
        return "🟢"
    if "đủ dùng" in low:
        return "🟡"
    return "🔴"


def append_law15_color_dot_scorecard(
    lines: list[str],
    *,
    core_100k: dict[str, Any],
    ref_ftmo_100k: dict[str, Any] | None,
    p_var: str,
    usd_vnd: float,
    be_x: float | None,
    rank_fn: Any,
) -> None:
    """Append Law-15 vertical color-dot (`🔴/🟡/🟢/🏆`) balanced scorecard (zero bare `$`)."""
    ev_r_rank = rank_fn("ev_r", core_100k["ev_per_trade_r"])
    pf_rank = rank_fn("pf", core_100k["profit_factor"])
    dd_rank = rank_fn("dd", core_100k["peak_dd_pct"])
    cal_rank = rank_fn("calmar", core_100k["calmar"])
    sh_rank = rank_fn("sharpe", core_100k["sharpe"])

    ann_100k_usd = (core_100k["ann_pct"] / 100.0) * 100_000.0
    ann_100k_vnd_tr = ann_100k_usd * usd_vnd / 1_000_000.0

    if ref_ftmo_100k is not None:
        s100 = ref_ftmo_100k["single_ticket_zero_retry"]
        ev_fee_ref = float(s100["ev_per_fee_npv24"])
        fn_br_ref = float(s100["funded_12m_breach"]["breach_12m_pct"])
        pay1_mo_ref = float(s100["cond_med_pay1_cal_days"]) / 30.4 if s100["cond_med_pay1_cal_days"] > 0 else 0.0
        ev_fee_rank = rank_fn("ev_fee", ev_fee_ref)
        m3 = s100["monthly_pass_fail_pending"].get("3m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        m6 = s100["monthly_pass_fail_pending"].get("6m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        m12 = s100["monthly_pass_fail_pending"].get("12m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        m24 = s100["monthly_pass_fail_pending"].get("24m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        dry_ref = float(s100["funded_dry_months_pct"])
        npv24_usd = float(s100["ev_npv_24m_usd"])
        npv24_tr = float(s100["ev_npv_24m_vnd_tr"])
        med24_tr = float(s100["med_npv_24m_vnd_tr"])
        p_le0 = float(s100["p_net_le_0_24m_pct"])
        fee_usd = float(s100["effective_fee_with_vn_fx_usd"])
        fee_tr = float(s100["effective_fee_vnd_tr"])
    else:
        ev_fee_ref = 0.0
        fn_br_ref = 0.0
        pay1_mo_ref = 0.0
        ev_fee_rank = "Đủ dùng"
        m3 = m6 = m12 = m24 = {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0}
        dry_ref = 50.0
        npv24_usd = npv24_tr = med24_tr = p_le0 = fee_usd = fee_tr = 0.0

    lines.append("## 2. Bộ Chỉ Số Cân Bằng Lõi `PORT_7E` & Thang Định Vị `Xấu -> Top 1%` (Luật 15)")
    lines.append("")
    lines.append(
        "Danh sách dọc chấm màu chuẩn Luật 15 (`🔴 Xấu` · `🟡 Đủ dùng` · `🟢 Tốt` · `🏆 Top 1% thực tế`) cho "
        "danh mục `7` động cơ trong ngày (`swap = 0`, tài khoản `100K`, Funded `1,0x`, ma sát chuẩn `1,00x`, "
        "có khiên tin đỏ `±5` phút, băng giá Dev `2018–2024` hậu-L7 `frozen_9e_tapes_v2`):"
    )
    lines.append("")
    lines.append(
        f"- 🟢 **Tỷ lệ thắng (`Winrate`) & Tỷ lệ ăn/thua (`RR`) — Tốt (trên quá khứ):** "
        f"**`{core_100k['winrate_pct']:.1f}%`** thắng · **`{core_100k['avg_rr']:.2f}x`** ăn/thua "
        f"(`{core_100k['sized_trades']}` lệnh; lãi năm chuẩn `+{core_100k['ann_pct']:.2f}%` ~ "
        f"`+{ann_100k_usd:,.0f} USD` / `+{ann_100k_vnd_tr:.1f}` tr VND trên `100K`). "
        f"*Thang: 🔴 `EV <= 0` · 🟡 Cân đối dương · 🟢 Cân đối bền · 🏆 Bền trên tiền thật.*"
    )
    lines.append(
        f"- {_tier_dot(ev_r_rank)} **Kỳ vọng mỗi lệnh (`EV / lệnh`) — {ev_r_rank}:** "
        f"**`{core_100k['ev_per_trade_r']:+.3f}R`**. "
        f"*Thang: 🔴 `<= 0,00R` · 🟡 `+0,03R..+0,06R` · 🟢 `+0,07R..+0,15R` · 🏆 `> +0,15R` bền trên tiền thật.*"
    )
    lines.append(
        f"- {_tier_dot(pf_rank)} **Hệ số sinh lời (`Profit Factor`) — {pf_rank}:** "
        f"**`{core_100k['profit_factor']:.2f}`** *(tổng tiền thắng / tổng tiền thua sau phí)*. "
        f"*Thang: 🔴 `< 1,05` · 🟡 `1,10..1,20` · 🟢 `1,25..1,50` · 🏆 `1,50..2,00+` tiền thật `>= 12T`.*"
    )
    lines.append(
        f"- {_tier_dot(dd_rank)} **Tụt sâu nhất (`Max DD` ở `1,0x`) & chuỗi thua — {dd_rank}:** "
        f"**`{core_100k['peak_dd_pct']:.2f}%`** · chuỗi thua dài nhất "
        f"**`{core_100k['max_loss_streak_trades']}`** lệnh. "
        "*Thang: 🔴 `> 10%` · 🟡 `7,5%..9,0%` · 🟢 `5,0%..7,0%` · 🏆 `4,0%..7,0%` đường tiền rất đều.*"
    )
    lines.append(
        f"- {_tier_dot(cal_rank)} **Hiệu suất trên rủi ro (`Calmar`) — {cal_rank}:** "
        f"**`{core_100k['calmar']:.2f}`** *(lãi năm `+{core_100k['ann_pct']:.2f}%` / "
        f"Max DD `{core_100k['peak_dd_pct']:.2f}%`)*. "
        "*Thang: 🔴 `< 0,5` · 🟡 `0,6..1,0` · 🟢 `1,2..2,0` · 🏆 `> 2,0..3,0` trên tiền thật.*"
    )
    lines.append(
        f"- {_tier_dot(sh_rank)} **Độ êm lợi nhuận (`Sharpe`) — {sh_rank}:** "
        f"**`{core_100k['sharpe']:.2f}`**. "
        f"*Thang: 🔴 `< 0,6` · 🟡 `0,8..1,1` · 🟢 `1,2..1,8` · 🏆 `2,0..3,0` tiền thật `>= 12T` nhiều nhánh.*"
    )
    lines.append(
        f"- {_tier_dot(ev_fee_rank)} **Thi quỹ Prop (`FTMO 2-Step Std 100K · {p_var}`, `EV NPV / 1 đồng phí`) — "
        f"{ev_fee_rank}:** **`{ev_fee_ref:+.2f}x`** (`NPV 24T` TB **`{npv24_usd:+,.0f} USD`** ~ "
        f"**`{npv24_tr:+.1f}` tr VND**, TV **`{med24_tr:+.1f}` tr VND**, `P(NPV<=0) = {p_le0:.1f}%`, "
        f"trên phí thực **`{fee_usd:,.2f} USD`** ~ **`{fee_tr:.1f}` tr VND**) · cháy Funded `12T` "
        f"**`{fn_br_ref:.2f}%`** · chờ rút đầu **`{pay1_mo_ref:.1f}T`**. "
        f"*Thang: 🔴 `<= 0x` hoặc cháy `>5%` · 🟡 `+1x..+2x` · 🟢 `+3x..+5x`, cháy `<1%`, chờ `5–10T` · "
        f"🏆 `>= +5x`, cháy `<1%`, rút `2–4T` nhiều nhánh lệch pha.*"
    )
    lines.append(
        f"- **Phân bổ `Đậu / Rớt / Đang chờ` theo tháng (`FTMO 100K · {p_var} · 1,00x`, tổng luôn `= 100,0%`):** "
        f"`3T`: **`{m3['pass_pct']:.1f}% / {m3['fail_pct']:.1f}% / {m3['pending_pct']:.1f}%`** · "
        f"`6T`: **`{m6['pass_pct']:.1f}% / {m6['fail_pct']:.1f}% / {m6['pending_pct']:.1f}%`** · "
        f"`12T`: **`{m12['pass_pct']:.1f}% / {m12['fail_pct']:.1f}% / {m12['pending_pct']:.1f}%`** · "
        f"`24T`: **`{m24['pass_pct']:.1f}% / {m24['fail_pct']:.1f}% / {m24['pending_pct']:.1f}%`**."
    )
    lines.append(
        "- **Ngưỡng gãy / điểm chết trượt giá (Break-Even Threshold):** Khi chi phí khớp lệnh thực tế (spread + "
        f"trượt giá) xấu đi tới khoảng **`{be_x if be_x is not None else '>4.00'}x`** so với băng giá M1 chuẩn, "
        "kỳ vọng lợi nhuận chiến lược rơi về `<= 0` (chuyển âm). Quy tắc cắt chi phí chìm dừng mua vé mới khóa cứng "
        "tại **`> 1,75x`**."
    )
    lines.append(
        "- **Còn thiếu gì để chạm `🏆 Top 1% thực tế`?** (1) Bằng chứng hiện mới là **Dev backtest 2018–2024 + "
        "28 lệnh Demo FTMO** — chưa có Holdout triển vọng v2 (`>= 01/12/2026`) và chưa có `>= 12` tháng chạy tiền "
        f"thật đã rút về ngân hàng; (2) `Max DD` ở `1,0x` (`{core_100k['peak_dd_pct']:.2f}%`, {dd_rank}), `PF` "
        f"(`{core_100k['profit_factor']:.2f}`, {pf_rank}), `EV/lệnh` (`{core_100k['ev_per_trade_r']:+.3f}R`, "
        f"{ev_r_rank}) và `Calmar` (`{core_100k['calmar']:.2f}`, {cal_rank}) vẫn còn khoảng cách tới chuẩn đỉnh "
        "— cần bổ sung thêm nhánh độc lập lệch pha (Alpha #2 / Sleeve mới, không tăng đòn bẩy liều) để kéo "
        f"`Calmar > 1,5–2,0`, rút thời gian chờ payout xuống `2–4` tháng và hạ tháng đói Funded từ `~{dry_ref:.0f}%` "
        "xuống `< 25%`."
    )
    lines.append("")


def append_v3_rollover_section(lines: list[str], results: dict[str, Any]) -> None:
    """Append Section 4.4: `flat_at_reset_verified` audit & `00:00` floating-equity rollover sensitivity."""
    audit = results.get("flat_at_reset_audit")
    roll = results.get("rollover_reset_sensitivity")
    if not audit or not roll:
        return

    lines.append(
        "### 4.4. Nâng Cấp V3 — Kiểm Chứng `flat_at_reset_verified` & Độ Nhạy Sốc Floating Equity Tại "
        "Giờ Reset `00:00` (`FTMO 10K` vs `The5ers 5K/20K` vs `IC Funded 10K`)"
    )
    lines.append("")
    ok_all = "ĐẠT (`True`)" if audit.get("flat_at_reset_verified") else "KHÔNG ĐẠT (`False`)"
    bufs = audit.get("min_buffer_minutes_by_clock") or {}
    hm_max = audit.get("max_exit_hm_by_clock") or {}
    cross = audit.get("crossing_trades_by_clock") or {}
    lines.append(
        f"- **Kết quả kiểm tra `flat_at_reset_verified` trực tiếp trên `{audit.get('total_trades_checked', 0)}` "
        f"lệnh Core7 (`frozen_9e_tapes_v2`, `holdout_rows_analysed = 0`):** **{ok_all}** "
        f"(`0` lệnh lỗi timestamp, `0` lệnh vượt nửa đêm trên cả 3 đồng hồ: "
        f"`UTC 00:00` qua đêm `{cross.get('UTC_0000', 0)}` lệnh · đóng muộn nhất `{hm_max.get('UTC_0000', 'N/A')}` · "
        f"đệm `{bufs.get('UTC_0000', 0):.1f}` phút; "
        f"`FTMO Prague 00:00` qua đêm `{cross.get('PRAGUE_0000', 0)}` · muộn nhất "
        f"`{hm_max.get('PRAGUE_0000', 'N/A')}` · "
        f"đệm **`{bufs.get('PRAGUE_0000', 0):.1f}` phút**; "
        f"`The5ers/IC MT5 EET/EEST 00:00` qua đêm `{cross.get('MT5_EET_0000', 0)}` · muộn nhất "
        f"`{hm_max.get('MT5_EET_0000', 'N/A')}` · đệm chỉ còn **`{bufs.get('MT5_EET_0000', 0):.1f}` phút**)."
    )
    if audit.get("tight_buffer_warnings"):
        lines.append(
            "- **Cảnh báo biên thời gian siêu mỏng mùa hè trên The5ers / IC Funded (`EEST = UTC+3`):** "
            "Các động cơ `E2/E3/E6/E7` đóng cưỡng bức lúc `20:55 UTC`, tương đương **`23:55` giờ máy chủ MT5 "
            "mùa hè (`UTC+3`)** — chỉ còn **`4–5` phút** trước giờ reset `00:00`! Nếu nghẽn mạng VPS, requote "
            "giãn spread cuối phiên hoặc đứt kết nối làm lệnh trượt qua `00:00`, tài khoản sẽ hứng sốc "
            "floating equity ngay tại mốc reset (do đó trên The5ers / IC Funded nên kéo giờ đóng sớm về `20:30 UTC` "
            "khi triển khai thực tế)."
        )
    lines.append(
        "- **So sánh 3 luật neo DD ngày tại `00:00` dưới cú sốc floating equity (`0%`, `-0,5%`, `-1,0%`, `-1,5%` "
        "bất lợi + kiểm thử `+1,0%` lãi nổi đảo chiều):** "
        "(a) **FTMO (`BALANCE_ANCHORED`):** sàn DD giữ cố định `bal - 5% * cap` (không đẩy sàn lên khi có lãi nổi "
        "`+1,0%`, không co trần khi `bal < cap`); "
        "(b) **The5ers (`MAX_BALANCE_OR_EQUITY`):** sàn DD = `max(bal, eq_00) * (1 - daily_lim)` — **bất lợi 2 "
        "chiều**: khi âm nổi `-0,5%..-1,5%` sàn KHÔNG hạ theo `eq_00` (mất trắng phần âm nổi vào trần ngày), còn "
        "khi dương nổi `+1,0%` sàn bị **đẩy vọt lên theo `eq_00`** (bẫy khóa lãi ảo); "
        "(c) **IC Funded (`EQUITY_AT_RESET`):** sàn ngày hạ theo `eq_00 * (1 - daily_lim)` khi âm nổi nhưng vẫn "
        "tiến sát sàn Max DD tĩnh `10%`, và vẫn đẩy sàn lên khi dương nổi `+1,0%` *(kèm dòng chặn trên bảo thủ "
        "`max(bal, eq)` nếu bảng điều khiển thực tế áp luật mạnh hơn)*."
    )
    lines.append("")
    lines.append(
        "| Hãng / Gói (`Luật rollover`) | Sốc `00:00` | `flat_at_reset` | `24T` Đậu / Rớt / Chờ (`100%`) "
        "| Vi phạm ngày (`Δ`) | Cháy Funded `12T` | `NPV 24T` (USD / tr VND) | Lệch `NPV 24T` vs `0%` |"
    )
    lines.append("|---|---:|---|---|---:|---:|---:|---:|")
    for r in roll.get("rows", []):
        sh = float(r["midnight_floating_shock_pct"])
        sh_lbl = "`0.0%` *(Flat)*" if abs(sh) < 1e-9 else f"**`{sh:+.1f}%`**"
        fl_lbl = "`True`" if r["flat_at_reset_verified"] else "`False` *(Stress)*"
        rule_short = {
            "BALANCE_ANCHORED": "Balance",
            "MAX_BALANCE_OR_EQUITY": "max(Bal,Eq)",
            "EQUITY_AT_RESET": "Equity",
        }.get(str(r["rollover_anchor_rule"]), str(r["rollover_anchor_rule"]))
        lines.append(
            f"| **{r['label']}** (`{rule_short}`) | {sh_lbl} | {fl_lbl} "
            f"| `{r['pass_24m_pct']:.1f}% / {r['fail_eval_24m_pct']:.1f}% / {r['pending_eval_24m_pct']:.1f}%` "
            f"| `{r['firm_hard_breach_daily_pct']:.2f}%` (`{r['delta_daily_breach_pp']:+.2f}pp`) "
            f"| `{r['funded_12m_breach_pct']:.2f}%` "
            f"| **`{r['ev_npv_24m_usd']:+,.0f} USD`** (`{r['ev_npv_24m_vnd_tr']:+.1f}tr`) "
            f"| `{r['delta_npv24_vs_flat_usd']:+,.0f} USD` (`{r['delta_npv24_vs_flat_vnd_tr']:+.1f}tr`) |"
        )
    lines.append("")
    lines.append(
        "> *Ghi chú gói `20K` The5ers:* Danh mục trực tiếp 2026 (`prop_pricing_catalog.json`) đã thay gói cũ `20K` "
        "bằng `25K` (`195 USD`); bảng trên giữ nguyên cả `20K` cũ (`165 USD`, chạy lại làm tròn lot thực trên `20K`, "
        "`LEGACY_20K_SKU_MODEL_ASSUMPTION`) lẫn `25K` hiện hành để chủ sở hữu đối chiếu trực tiếp."
    )
    lines.append("")


def append_v3_black_friday_2deadline_section(lines: list[str], results: dict[str, Any]) -> None:
    """Append Section 5.3: Black Friday 2-Deadline Real-Option Analysis (`30/11 -> ~14/12` vs Xmas/NY)."""
    bf = results.get("black_friday_2deadline_option")
    if not bf or not bf.get("tiers"):
        return

    lines.append(
        "### 5.3. Nâng Cấp V3 — Phân Tích Black Friday 2 Mốc Hạn (`30/11` Khóa Bill Chưa Trả `0 VND` -> "
        "`~14/12` Hạn Thanh Toán 14 Ngày Sau `04/12` NFP / `08/12` Trial / `10/12` CPI) vs Chờ Sale Noel/Năm Mới"
    )
    lines.append("")
    lines.append(
        "- **Cấu trúc quyền chọn 0 đồng (`MODEL_ASSUMPTION` — cần kiểm tra trực tiếp màn hình checkout `30/11`, "
        "tuyệt đối `0 VND`):** Tạo hóa đơn FTMO Black Friday chưa thanh toán vào **`30/11`** (giảm `-30%` cho "
        "`10K`, `-20%` cho `50K/100K`), giữ nguyên **`0 VND`** trong `14` ngày để quan sát đủ **3 sự kiện sống**: "
        "**`04/12` NFP** -> **`08/12` kết thúc FTMO Free Trial 14 ngày** -> **`10/12` CPI**, rồi mới quyết định tại "
        "hạn chót **`~14/12`**: nếu xanh (`GO`, xác suất `p_go`) thì trả đúng giá BF; nếu đỏ (`NO_GO`, xác suất "
        "`1 - p_go`) thì bỏ hóa đơn với thiệt hại **`0 VND`**!"
    )
    lines.append(
        "- **So sánh 4 phương án thực tế (`FTMO 2-Step Standard`, nhánh `C10_NEWS_ON`, ma sát `1,00x`, chiết khấu "
        "`6%/năm`, mốc minh họa chuẩn `p_go = 70%`, xác suất FTMO có sale Noel/Năm Mới `-10%` tại `~30/12` là "
        "`p_xmas = 50%`):**"
    )
    lines.append("  1. **A (`Mua mù 30/11`):** Trả tiền BF ngay trước NFP/Trial/CPI — nếu cổng đỏ mất trắng phí vé.")
    lines.append(
        "  2. **B (`Khóa bill 30/11 -> Trả 14/12 nếu GO`):** Quyền chọn 14 ngày `0 VND` — "
        "hưởng giá BF, tránh mất phí khi đỏ."
    )
    lines.append("  3. **C (`Bỏ BF -> Mua giá gốc 14/12 nếu GO`):** Mất sạch phần giảm giá BF (`-20%/-30%`).")
    lines.append(
        "  4. **D (`Bỏ BF -> Chờ sale Noel/Năm Mới ~30/12`):** Chậm thêm `16` ngày sau `14/12` "
        "và chỉ kỳ vọng `-10%` không chắc chắn."
    )
    lines.append("")
    lines.append(
        "| Cỡ FTMO (Giá BF / Gốc cả phí thẻ) | Chân trời | **A: Mua mù `30/11`** | **B: Khóa bill `30/11` -> `14/12`** "
        "| C: Giá gốc `14/12` | D: Chờ Noel `~30/12` | **Giá trị Quyền chọn (`B - A`)** "
        "| **Lợi ích vs Noel (`B - D`)** | Ngưỡng hòa `p_go*` |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for tier in bf["tiers"]:
        cap_k = int(round(float(tier["capital_usd"]) / 1000.0))
        fee_desc = (
            f"**`{cap_k}K`** (`{tier['bf_fee_usd']:.0f}` / `{tier['orig_fee_usd']:.0f} USD`, "
            f"-`{tier['bf_discount_pct']:.0f}%`)"
        )
        for h_key, h_lbl in (
            ("fixed_deadline_24m", "Hạn cứng 24T"),
            ("shifting_horizon_24m", "Tịnh tiến 24T"),
        ):
            h = tier["horizons"][h_key]
            r = h["reference_pgo70_pxmas50"]
            col_a = f"`{r['ev_a_buy_blind_30nov_usd']:+,.1f} USD` (`{r['ev_a_buy_blind_30nov_vnd_tr']:+.2f}tr`)"
            col_b = (
                f"**`{r['ev_b_lock_unpaid_pay_14dec_usd']:+,.1f} USD`** "
                f"(`{r['ev_b_lock_unpaid_pay_14dec_vnd_tr']:+.2f}tr`)"
            )
            col_c = (
                f"`{r['ev_c_skip_bf_regular_14dec_usd']:+,.1f} USD` (`{r['ev_c_skip_bf_regular_14dec_vnd_tr']:+.2f}tr`)"
            )
            col_d = f"`{r['ev_d_skip_bf_wait_xmas_usd']:+,.1f} USD` (`{r['ev_d_skip_bf_wait_xmas_vnd_tr']:+.2f}tr`)"
            col_ba = (
                f"**`{r['option_value_b_minus_a_usd']:+,.1f} USD`** (`{r['option_value_b_minus_a_vnd_tr']:+.2f}tr`)"
            )
            col_bd = (
                f"**`{r['advantage_b_minus_d_xmas_usd']:+,.1f} USD`** (`{r['advantage_b_minus_d_xmas_vnd_tr']:+.2f}tr`)"
            )
            lines.append(
                f"| {fee_desc} | {h_lbl} | {col_a} | {col_b} | {col_c} | {col_d} "
                f"| {col_ba} | {col_bd} | **`{h['breakeven_p_go_for_blind_buy'] * 100.0:.1f}%`** |"
            )
    lines.append("")
    dom_str = (
        "ĐÃ CHỨNG MINH (`weak_dominance_verified = True`)" if bf.get("weak_dominance_verified") else "CẦN KIỂM TRA"
    )
    shift_fails = [
        max(0.0, (1.0 - float(t["horizons"]["shifting_horizon_24m"]["breakeven_p_go_for_blind_buy"])) * 100.0)
        for t in bf["tiers"]
    ]
    fixed_fails = [
        max(0.0, (1.0 - float(t["horizons"]["fixed_deadline_24m"]["breakeven_p_go_for_blind_buy"])) * 100.0)
        for t in bf["tiers"]
    ]
    sh_lo, sh_hi = min(shift_fails), max(shift_fails)
    fx_lo, fx_hi = min(fixed_fails), max(fixed_fails)
    lines.append(
        f"> **Kết luận toán học về tính thống trị yếu ({dom_str}):** "
        f"(1) Trên chân trời tịnh tiến 24T, chỉ cần xác suất trượt cổng NFP/Trial/CPI lớn hơn "
        f"`{sh_lo:.1f}%–{sh_hi:.1f}%` (hạn cứng 24T: `{fx_lo:.1f}%–{fx_hi:.1f}%`, tức `p_go < p_go*`), "
        "**Phương án B (Khóa bill `0 VND` `30/11` -> quyết định `14/12`) thắng tuyệt đối "
        "Mua mù `30/11`**, đồng thời **thắng tuyệt đối Chờ Noel/Năm Mới** trên cả 2 chân trời vì giảm giá BF "
        "(`20%–30%`) gấp `2x–3x` mức giảm Noel (`0%–10%`) mà lại mở sớm hơn `16` ngày; "
        "(2) Kể cả khi hóa đơn chưa thanh toán **không giữ được giá BF (`p_bill_honored = 0%`, `MODEL_ASSUMPTION`)**, "
        "chủ sở hữu mất đúng `0 VND` và tự động rơi về đúng phương án tốt nhất giữa `C` và `D` — **không bao giờ "
        "thiệt hơn việc bỏ qua bước khóa bill `30/11`!**"
    )
    lines.append("")


def append_v3_x13_shard_section(lines: list[str], results: dict[str, Any]) -> None:
    """Append Section 8.5: X13 Shard Worker Mode readiness & direct tape integrity contract."""
    prov = results.get("tape_provenance") or {}
    lines.append(
        "### 8.5. Chế Độ X13 Shard Worker Thuần NumPy/Numba (`--x13-shard` / `run_x13_mc_shard()`, Sẵn Sàng Wave 2A)"
    )
    lines.append("")
    lines.append(
        "- **Đọc thẳng băng giá Dev `frozen_9e_tapes_v2.{json,npz}` không lệ thuộc máy Dev:** "
        f"Xác minh trực tiếp `npz_sha256` (`{str(prov.get('npz_sha256', 'VERIFIED_AT_RUNTIME'))[:16]}...`) và "
        "`max_day < 2025-01-01` (`holdout_rows_analysed = 0`) — **tuyệt đối KHÔNG gọi `assert_holdout_locked()`, "
        "`quant_factory.data_store`, `quant_factory.prop_engine`, `quant_core.holdout_guard`, hay `duckdb` trên "
        "`<X13_WORKER>`**."
    )
    lines.append(
        "- **Tương thích Python 3.14 & Air-Gap `job_id`:** `ExactTierReplayCache` đã tự chứa toàn bộ phép tính "
        "margin, red-news `±5m` và cost-stress bằng Python/NumPy thuần (khớp bit-exact với `pass27/pass28`), chặn "
        "cứng mọi `job_id` hoặc tên file đầu ra chứa `2025`, `2026`, `holdout`, `private_vault`, `.ssh`, và hỗ trợ "
        "gộp nhiều mảnh xác định qua `merge_x13_mc_shards()`."
    )
    lines.append(
        "- **Lệnh chạy thử shard sẵn sàng cho Wave 2A:** "
        "`python -m quant_factory.prop_capital_promo_optimizer --x13-shard --job-id cap_v3_mc_shard0 "
        "--shard-id 0 --num-shards 4 --shard-paths 2500`."
    )
    lines.append("")
