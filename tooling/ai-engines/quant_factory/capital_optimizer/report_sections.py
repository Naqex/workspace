"""Markdown report sections 5–8 for the Vietnamese Law-15 capital optimizer report."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quant_factory.capital_optimizer.constants import BANKROLL_GRID_VND_TR, TOPUP_GRID_VND_TR


def append_sections_5_to_8(
    lines: list[str],
    results: dict[str, Any],
    *,
    p_var: str,
    policy_vi_name: Callable[[str], str],
) -> None:
    """Append Sections 5–8 of the plain-Vietnamese Law-15 report (zero bare `$`)."""
    lines.append(
        "## 5. Lịch Sale Động Hai Chân Trời (B5): Mua Hôm Nay Hay Đợi `Y` Ngày Để Hưởng Giảm Giá `Z%`?"
    )
    lines.append("")
    lines.append(
        "- **Khắc phục triệt để 3 lỗi cũ:** (1) **Bỏ hoàn toàn binary search** -> quét chính xác toàn bộ "
        "từng ngày `Y = 0..180` vì chân trời hạn cứng không đơn điệu qua các chu kỳ rút tiền `10` phiên; "
        "(2) **Bỏ hoàn toàn đường tắt `2 * d7`** -> chạy mô phỏng MC thật cho cả `7d / 14d / 30d`; "
        "(3) Vé mua lại (retry) **luôn tính giá gốc** (không hưởng BF vĩnh viễn)."
    )
    lines.append(
        "- **Công bố song song 2 chân trời & quét dày toàn bộ `Y = 0..180` (ZERO tìm thưa quanh nghiệm giải tích):** "
        "**(a) Hạn lịch cố định 24 tháng tính từ hôm nay** *(đợi Y ngày = mất hẳn Y ngày giao dịch trước hạn)* và "
        "**(b) Chân trời tịnh tiến 24 tháng tính từ ngày mua** *(công thức `365 * ln(NPV_sale / NPV_orig) / ln(1 + r)` "
        "+ quét dày MC toàn bộ từng ngày nguyên `0..180` trên cửa sổ `[Y, Y+24T)`)*, "
        "công bố rõ cả 2 mốc **`max_continuous_positive_wait_days`** *(mọi ngày `0..Y` đều dương liên tục)* và "
        "**`last_positive_wait_day`** *(ngày dương cuối cùng nếu nhiễu MC bật lại sau khi đã rơi âm — **tuyệt đối "
        "không hiểu nhầm `last_positive_wait_day` là đợi ngày nào tới mốc đó cũng dương!**)*."
    )
    lines.append(
        "- **Công khai giả định bắt buộc:** Mọi con số ngày tối đa đáng chờ bên dưới **đều giả định đợt sale tương "
        "lai `Z%` chắc chắn 100% xảy ra đúng vào ngày `Y`**. Nếu xác suất có sale thực tế chỉ là `p < 100%` "
        "(ví dụ `HISTORICAL_PATTERN` ngoài Black Friday), số ngày đáng chờ thực tế phải rút ngắn tương ứng."
    )
    lines.append("")

    for retry_key, retry_title in (
        (
            "SINGLE_TICKET_0_RETRY",
            "5.1. Chế Độ 1 Vé (`max_retries = 0`, `C10_NEWS_ON` — "
            "Đối Chiếu Trực Tiếp Astra `~55 / 110 / 164d` trên `10K`)",
        ),
        (
            "RETRY_UP_TO_2_REGULAR_PRICE",
            "5.2. Chế Độ Có Thử Lại (`max_retries = 2`, Vé Ngày Mua Hưởng Sale + "
            "Vé Mua Lại Tính Giá Gốc, `C10_NEWS_ON`)",
        ),
    ):
        lines.append(f"### {retry_title}")
        lines.append("")
        lines.append(
            "| Kịch bản ngày hiện tại | Cỡ FTMO | Ma sát | Sale mục tiêu | Tiết kiệm ngay (USD) "
            "| **(a) Hạn cứng 24T: Tối đa đáng chờ** | `Delta` cứng (`7d / 14d / 30d`) "
            "| **(b) Tịnh tiến 24T: Công thức / MC (Liên tục · Cuối dương)** "
            "| `Delta` tịnh tiến (`7d / 14d / 30d`) |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---|---:|---|")
        non_mono_shift_examples: list[str] = []
        for row in results["sale_decision_table"]:
            if row.get("retry_regime") != retry_key:
                continue
            if row["scenario"] == "NON_PROMO_DAY_0PCT":
                sc_lbl = "Ngày thường (`0%`)"
                sav = f"`{row['upfront_saving_usd']:.1f}`"
            else:
                sc_lbl = f"Black Friday (`-{row['active_discount_pct']:.0f}%`)"
                sav = "—"
            d_fix = (
                f"`{row.get('delta_npv_at_7d_usd', 0.0):+.1f}` / "
                f"`{row.get('delta_npv_at_14d_usd', 0.0):+.1f}` / "
                f"`{row.get('delta_npv_at_30d_usd', 0.0):+.1f}`"
            )
            sh_f = row.get("shifting_horizon_formula_max_wait_days", 0.0)
            sh_cont = row.get("max_continuous_positive_wait_days")
            sh_last = row.get("last_positive_wait_day")
            if sh_cont is not None and sh_last is not None:
                if sh_last > sh_cont:
                    dip = row.get("first_nonpositive_wait_day", sh_cont + 1)
                    sh_lbl = f"**`{sh_f:.0f}d`** / LT `{sh_cont}d` · Cuối `{sh_last}d` *(gãy {dip}d)*"
                    non_mono_shift_examples.append(
                        f"`{int(row['capital_usd'] // 1000)}K @ {row['friction_x']:.2f}x "
                        f"(-{row['target_sale_discount_pct']:.0f}%)`: "
                        f"liên tục dương tới **`{sh_cont}d`** (rơi âm ngay tại **`{dip}d`**), "
                        f"nhiễu MC bật dương lần cuối tại **`{sh_last}d`**"
                    )
                else:
                    sh_lbl = f"**`{sh_f:.0f}d`** / LT `{sh_cont}d` · Cuối `{sh_last}d`"
            else:
                sh_lbl = f"**`{sh_f:.0f}d`**"
            d_sh = (
                f"`{row.get('shifting_delta_formula_7d_usd', 0.0):+.1f}` / "
                f"`{row.get('shifting_delta_formula_14d_usd', 0.0):+.1f}` / "
                f"`{row.get('shifting_delta_formula_30d_usd', 0.0):+.1f}`"
            )
            nm_tag = " *(không đơn điệu)*" if row.get("non_monotonic_fixed_deadline") else ""
            lines.append(
                f"| {sc_lbl} | **`{int(row['capital_usd'] // 1000)}K`** | `{row['friction_x']:.2f}x` "
                f"| `-{row['target_sale_discount_pct']:.0f}%` | {sav} "
                f"| **`{row['max_wait_days_fixed_deadline']}d`**{nm_tag} | {d_fix} | {sh_lbl} | {d_sh} |"
            )
        lines.append("")
        if non_mono_shift_examples:
            lines.append(
                "> **Cảnh báo đường cong tịnh tiến không đơn điệu (Astra Vòng 11 Q3c):** "
                "Vì quét dày toàn bộ `Y = 0..180`, các dòng có `Cuối dương > Liên tục` (ví dụ: "
                + "; ".join(non_mono_shift_examples[:4])
                + ") **KHÔNG ĐƯỢC hiểu là đợi bất kỳ ngày nào tới mốc `Cuối dương` đều có lãi** — "
                "phải lấy mốc **`Liên tục` (`max_continuous_positive_wait_days`)** làm ngưỡng an toàn bảo thủ."
            )
            lines.append("")

    # Section 6
    lines.append("## 6. Các Kiểm Chứng Tài Chính Thực Tế (`own_book = 0`, Vé Mua Lại Giá Gốc, Hoàn Phí Thẻ FTMO `0%`)")
    lines.append("")
    lines.append(
        "### 6.1. So Sánh 3 Nhánh: `2x 100K` Tuần Tự (`P4B`) vs `2x 100K` Song Song Ngày 0 "
        "(`P4B_PARALLEL`) vs `1x 200K` (`P4C`)"
    )
    lines.append("")
    lines.append(
        "*Lưu ý quan trọng (B6):* **`P4B_PARALLEL_2X100K`** mở cả 2 vé `100K` ngay Ngày 0 khi đủ vốn (`>= 2` vé) "
        "nên cả 2 vé chạy trên **cùng ngày thị trường** (`tương quan drawdown cùng ngày = 1,0`, thể hiện qua cột "
        "**`Cháy kép cùng ngày`**). Dù chịu cháy kép, ở vốn `50tr–80tr` tách thành `2x 100K` vẫn giữ thêm đạn dự "
        "phòng `100K` (giá gốc `15,8tr/vé`) trong khi `1x 200K` cần tới `31,6tr/vé` cho lượt mua lại!"
    )
    lines.append("")
    lines.append(
        "| Vốn ban đầu (`0tr/T`) | Ma sát "
        "| `P4B` Tuần tự `100K->2x100K`: Cháy / `NPV24` TB (TV, `P<=0`) "
        "| **`P4B_PARALLEL` `2x 100K` Ngày 0**: Cháy / Cháy kép / `NPV24` TB (TV, `P<=0`) "
        "| `P4C` `1x 200K`: Cháy / `NPV24` TB (TV, `P<=0`) "
        "| Đối chứng **Toàn bộ giá gốc**: `Par 2x100K` vs `1x200K` (`Cháy / NPV24`) |"
    )
    lines.append("|---:|---:|---|---|---|---|")
    for fkey in ("1.00x", "1.50x"):
        for r in results["head_to_head_2x100k_vs_1x200k"][fkey]:
            sq = r["sequential_2x_100k"]
            pa = r["parallel_2x_100k"]
            c2 = r["one_x_200k"]
            pr = r["parallel_2x_100k_all_regular"]
            cr = r["one_x_200k_all_regular"]
            lines.append(
                f"| **`{r['bankroll_vnd_tr']:.0f}tr`** (`{r['bankroll_usd']:,.0f} USD`) | `{fkey}` "
                f"| `{sq['ruin_pct']:.2f}%` / `{sq['ev_npv_24m_vnd_tr']:+.1f}tr` "
                f"(`{sq['med_npv_24m_vnd_tr']:+.1f}tr`, `{sq['p_npv24_le_0_pct']:.0f}%`) "
                f"| **`{pa['ruin_pct']:.2f}%`** / `{pa['simultaneous_fail_pct']:.1f}%` / "
                f"**`{pa['ev_npv_24m_vnd_tr']:+.1f}tr`** (`{pa['med_npv_24m_vnd_tr']:+.1f}tr`, "
                f"`{pa['p_npv24_le_0_pct']:.0f}%`) "
                f"| `{c2['ruin_pct']:.2f}%` / `{c2['ev_npv_24m_vnd_tr']:+.1f}tr` "
                f"(`{c2['med_npv_24m_vnd_tr']:+.1f}tr`, `{c2['p_npv24_le_0_pct']:.0f}%`) "
                f"| `Par {pr['ruin_pct']:.1f}% / {pr['ev_npv_24m_vnd_tr']:+.1f}tr` vs "
                f"`200K {cr['ruin_pct']:.1f}% / {cr['ev_npv_24m_vnd_tr']:+.1f}tr` |"
            )
    lines.append("")

    lines.append(
        "### 6.2. Độ Nhạy Chiết Khấu NPV (`0% / 4% / 6% / 8%/Năm`) & Tách Bạch Phí Hoàn Thẻ FTMO (`0,0%` vs `1,5%`, B6)"
    )
    lines.append("")
    lines.append(
        "| Cỡ FTMO Std (`1,00x`, 1 vé `C10_NEWS_ON`) | `r = 0%` (Chưa chiết khấu) | `r = 4%/năm` "
        "| **`r = 6%/năm` (Chuẩn VN)** | `r = 8%/năm` | Chênh lệch `6%` vs `0%` |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cap in (10_000.0, 100_000.0):
        by_r = {
            row["discount_rate_pct"]: row
            for row in results["npv_discount_sensitivity"]
            if abs(row["capital_usd"] - cap) < 1e-6
        }
        if 0.0 in by_r and 6.0 in by_r:
            d_pct = (
                100.0
                * (by_r[6.0]["ev_npv_24m_usd"] - by_r[0.0]["ev_npv_24m_usd"])
                / max(1e-6, abs(by_r[0.0]["ev_npv_24m_usd"]))
            )
            lines.append(
                f"| **`{int(cap // 1000)}K USD` (`24T` / `36T`)** "
                f"| `{by_r[0.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[0.0]['ev_npv_36m_vnd_tr']:+.1f}tr` "
                f"| `{by_r[4.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[4.0]['ev_npv_36m_vnd_tr']:+.1f}tr` "
                f"| **`{by_r[6.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[6.0]['ev_npv_36m_vnd_tr']:+.1f}tr`** "
                f"| `{by_r[8.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[8.0]['ev_npv_36m_vnd_tr']:+.1f}tr` "
                f"| `{d_pct:+.1f}%` |"
            )
    lines.append("")
    if results.get("fee_accounting_sensitivity"):
        lines.append(
            "**Độ nhạy tách phí mua thẻ (`+2,5%` không hoàn) · hoàn phí thẻ FTMO (`0,0%` mặc định vs `1,5%` kênh rút) "
            "· rút lợi nhuận (`1,5%`):**"
        )
        lines.append("")
        lines.append(
            "| Cỡ FTMO | Ma sát | `NPV 24T` hoàn về thẻ (`0,0%`) | `NPV 24T` nếu trừ `1,5%` kênh rút "
            "| Chênh lệch (`0,0% - 1,5%`) |"
        )
        lines.append("|---:|---:|---:|---:|---:|")
        for fr in results["fee_accounting_sensitivity"]:
            lines.append(
                f"| **`{int(fr['capital_usd'] // 1000)}K`** | `{fr['friction_x']:.2f}x` "
                f"| `{fr['refund_card_0pct_npv24_usd']:+,.2f} USD` "
                f"| `{fr['refund_rail_1_5pct_npv24_usd']:+,.2f} USD` "
                f"| `{fr['delta_card_minus_rail_usd']:+.2f} USD` (`{fr['delta_card_minus_rail_vnd_tr']:+.3f} tr`) |"
            )
        lines.append("")

    lines.append(
        "### 6.3. Quy Tắc Cắt Bỏ Chi Phí Chìm (`Sunk-Cost Abort` Khi Trượt Giá Sống Vượt `> 1,75x`, "
        "Vốn `35tr`, Gói `50K`, `C10_NEWS_ON`)"
    )
    lines.append("")
    lines.append(
        "| Mức trượt giá thực tế bất lợi | Cố mua vé gỡ (Không cắt): Tổng phí `24T` / `NPV 24T` "
        "| Dừng mua vé sau `42` phiên đo xấu: Tổng phí `24T` / `NPV 24T` "
        "| Tiền phí tiết kiệm được | Cải thiện `NPV 24T` |"
    )
    lines.append("|---:|---|---|---:|---:|")
    for row in results["sunk_cost_abort_study"]:
        bl, ab = row["blind_retry_chasing"], row["live_friction_abort_day42"]
        lines.append(
            f"| **`{row['adverse_friction_x']:.2f}x`** "
            f"| `{bl['mean_fees_24m_usd']:,.0f} USD` / `{bl['ev_npv_24m_vnd_tr']:+.1f} tr` "
            f"| `{ab['mean_fees_24m_usd']:,.0f} USD` / `{ab['ev_npv_24m_vnd_tr']:+.1f} tr` "
            f"| **`{row['fees_saved_vnd_tr']:+.1f} tr VND`** (`{row['fees_saved_usd']:+.0f} USD`) "
            f"| **`{row['npv24_saved_vnd_tr']:+.1f} tr VND`** |"
        )
    lines.append("")

    lines.append(
        "### 6.4. Giá Trị Thật Của Chia `1` Quỹ vs `2` Quỹ vs `3` Quỹ Sống Sót "
        "(Loại `E8 Pro`, Tắt `own_book`, Vốn `50tr`)"
    )
    lines.append("")
    lines.append(
        "*Lưu ý quan trọng:* Toàn bộ tài khoản chạy trên **cùng một ngày thị trường** "
        "(`tương quan sập thị trường = 1,0`). "
        "`The5ers` (`max(balance, equity)` tại reset) và `IC Funded` (`equity` tại reset) mang song song "
        "**`TERMS_VERIFIED_EXECUTION_UNMEASURED`** và **`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** "
        "*(công thức `balance * (1 - daily_lim)` chỉ đúng khi đóng sạch lệnh đúng giờ reset)*; `E8 Pro` đã bị "
        "**loại hoàn toàn** khỏi danh mục này do bẫy khóa sàn DD sau lần rút đầu."
    )
    lines.append("")
    lines.append(
        "| Xác suất sự cố riêng mỗi hãng/năm | Phân bổ (`own_book = 0`) | Cháy vốn "
        "| `NPV 24T` TB / TV (tr VND) | `P(NPV24 <= 0)` | `NPV 36T` (tr VND) "
        "| Tỷ lệ gặp sự cố hãng | Vốn Funded đỉnh TB |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    alloc_vi = {
        "SINGLE_FIRM_FTMO_2x100K": "1 Quỹ (FTMO `2x 100K` · ĐO DEMO)",
        "TWO_FIRM_SPLIT": "2 Quỹ (`FTMO + The5ers` · The5ers CHƯA ĐO)",
        "THREE_FIRM_SURVIVING_SPLIT": "3 Quỹ sống sót (`FTMO + The5ers + IC Funded` · 2 hãng CHƯA ĐO)",
    }
    for row in results["cross_firm_hazard_study"]:
        lines.append(
            f"| `{row['hazard_rate']}` | **{alloc_vi.get(row['allocation'], row['allocation'])}** "
            f"| `{row['ruin_pct']:.2f}%` | `{row['ev_npv_24m_vnd_tr']:+.1f}` / `{row['med_npv_24m_vnd_tr']:+.1f}` "
            f"| `{row['p_npv24_le_0_pct']:.1f}%` | **`{row['ev_npv_36m_vnd_tr']:+.1f}`** "
            f"| `{row['firm_disruption_rate_pct']:.1f}%` | `{row['mean_max_funded_nom_usd']:,.0f} USD` |"
        )
    lines.append("")

    # Section 7
    lines.append(
        f"## 7. Ma Trận Pareto 2 Mục Tiêu Theo Vốn & Nạp Hàng Tháng "
        f"(`{p_var}` · `own_book = 0` · BF Ngày 0 + Retry Giá Gốc · `DAILY_APPROX`)"
    )
    lines.append("")
    lines.append(
        "So sánh **10 chính sách** (`P1`, `P2`, `P3`, `P4A_DIRECT_50K` tham, **`P4A_WAIT_FOR_100K`** giữ khe 2 chờ "
        "`100K`, `P4B_DIRECT_100K` tuần tự, **`P4B_PARALLEL_2X100K`** song song Ngày 0, `P4C_DIRECT_200K`, "
        "`P5A/P5B` chia **`3` quỹ sống sót** bỏ `E8 Pro`) trên **`15` ô vốn** (`15 / 25 / 35 / 50 / 80 tr VND` × "
        "nạp thêm `0 / 3 / 5 tr/T`, `5.000` kịch bản MC/ô, rủi ro hãng `5%/năm`):"
    )
    lines.append("")
    lines.append(
        "- **Mọi ô đều công bố đầy đủ bộ ba:** **`TB` (Mean NPV24)** · **`TV` (Median NPV24)** · "
        "**`P<=0` (Xác suất hòa/lỗ 24T)** — tuyệt đối không che trung vị âm sau trung bình dương!"
    )
    lines.append("- **Hồ Sơ A (`NPV_Wealth_Safe5pct`):** Tối đa hóa `NPV` với ràng buộc **cháy vốn `<= 5,0%`**.")
    lines.append(
        "- **Hồ Sơ B (`Fast_Cashflow_Safe10pct`):** Rút ngắn thời gian chờ rút đầu & tháng đói "
        "với ràng buộc **cháy vốn `<= 10,0%`**."
    )
    lines.append("")

    for fkey, flbl in (
        ("1.00x", "7.1. Ma Sát Chuẩn `1,00x` (`C10_NEWS_ON`)"),
        ("1.50x", "7.2. Stress Trượt Giá Nặng `1,50x` (`C10_NEWS_ON` — Theo Dõi Chặt Trung Vị Âm & `P(NPV24 <= 0)`)"),
    ):
        lines.append(f"### {flbl}")
        lines.append("")
        lines.append(
            "| Vốn + Nạp/T | **Hồ Sơ A — CHỈ FTMO (`Cháy <= 5%`)** | **Hồ Sơ B — CHỈ FTMO (`Cháy <= 10%`)** "
            "| **Đa Hãng 3 Quỹ (`The5ers/IC CHƯA ĐO`)** | `P4A-Chờ100K` vs `P4A-Tham` (`NPV24 TB / TV / P<=0`) |"
        )
        lines.append("|---|---|---|---|---|")
        cells = results["pareto_grid"][fkey]
        for bank_tr in BANKROLL_GRID_VND_TR:
            for top_tr in TOPUP_GRID_VND_TR:
                ck = f"B{int(bank_tr)}tr_T{int(top_tr)}tr"
                c = cells[ck]
                pw = c["pareto_winners"]
                fw = pw.get("ftmo_only_verified_execution", pw)
                fa = fw["profile_a_npv_wealth_safe5pct"]
                fb = fw["profile_b_fast_cashflow_safe10pct"]
                all_a = pw["profile_a_npv_wealth_safe5pct"]
                p4w = c["policies"]["P4A_WAIT_FOR_100K"]
                p4g = c["policies"]["P4A_DIRECT_50K"]
                fa_tag = "" if fa["status"] == "FEASIBLE_RUIN_LE_5PCT" else " *(>5%)*"
                if fb["status"] == "FEASIBLE_RUIN_LE_10PCT":
                    fb_tag = ""
                elif fb["status"] == "FEASIBLE_RUIN_LE_10PCT_PAID_LT_50PCT":
                    fb_tag = " *(đạt rút <50%)*"
                else:
                    fb_tag = " *(>10%)*"
                lines.append(
                    f"| **`{int(bank_tr)}tr`+`{int(top_tr)}tr/T`** "
                    f"| **{policy_vi_name(fa['winner_policy'])}**{fa_tag}<br>"
                    f"Cháy `{fa['ruin_pct']:.2f}%` · TB `{fa['ev_npv_24m_vnd_tr']:+.1f}tr` · "
                    f"**TV `{fa['med_npv_24m_vnd_tr']:+.1f}tr`** · `P<=0` `{fa['p_npv24_le_0_pct']:.1f}%` "
                    f"| **{policy_vi_name(fb['winner_policy'])}**{fb_tag}<br>"
                    f"Cháy `{fb['ruin_pct']:.2f}%` · Chờ `{fb['uncond_med_pay1_days']:.0f}d` · "
                    f"TB `{fb['ev_npv_24m_vnd_tr']:+.1f}tr` · **TV `{fb['med_npv_24m_vnd_tr']:+.1f}tr`** · "
                    f"`P<=0` `{fb['p_npv24_le_0_pct']:.1f}%` "
                    f"| **{policy_vi_name(all_a['winner_policy'])}**<br>"
                    f"Cháy `{all_a['ruin_pct']:.2f}%` · TB `{all_a['ev_npv_24m_vnd_tr']:+.1f}tr` · "
                    f"**TV `{all_a['med_npv_24m_vnd_tr']:+.1f}tr`** · `P<=0` `{all_a['p_npv24_le_0_pct']:.1f}%` "
                    f"| Chờ100K: `{p4w['ev_npv_24m_vnd_tr']:+.1f}` / `{p4w['med_npv_24m_vnd_tr']:+.1f}` "
                    f"(`{p4w['p_npv24_le_0_pct']:.0f}%`)<br>"
                    f"Tham: `{p4g['ev_npv_24m_vnd_tr']:+.1f}` / `{p4g['med_npv_24m_vnd_tr']:+.1f}` "
                    f"(`{p4g['p_npv24_le_0_pct']:.0f}%`) |"
                )
        lines.append("")
        if fkey == "1.00x" and "B25tr_T0tr" in cells and "B35tr_T0tr" in cells and "B50tr_T0tr" in cells:
            b_list = [int(b) for b in BANKROLL_GRID_VND_TR if f"B{int(b)}tr_T0tr" in cells]
            w_vals = [(b, cells[f"B{b}tr_T0tr"]["policies"]["P4A_WAIT_FOR_100K"]["ev_npv_24m_vnd_tr"]) for b in b_list]
            g_vals = [(b, cells[f"B{b}tr_T0tr"]["policies"]["P4A_DIRECT_50K"]["ev_npv_24m_vnd_tr"]) for b in b_list]
            dip_pair = next(
                ((g_vals[i - 1], g_vals[i]) for i in range(1, len(g_vals)) if g_vals[i][1] < g_vals[i - 1][1]),
                None,
            )
            w_ladder_txt = " -> ".join(f"`{v:+.1f}tr` (`{b}tr`)" for b, v in w_vals)
            if dip_pair is not None:
                (b_prev, g_prev), (b_dip, g_dip) = dip_pair
                w_dip = dict(w_vals)[b_dip]
                dip_txt = (
                    f"Chính sách tham `P4A_DIRECT_50K` tụt phi đơn điệu ở mốc **`{b_dip}tr`** "
                    f"(`{g_dip:+.1f}tr` so với `{g_prev:+.1f}tr` ở `{b_prev}tr`, tức **`{g_dip - g_prev:+.1f}tr`**) "
                    f"do vội mở thêm vé `50K` thứ hai ngay khi vừa đậu (mốc tụt dịch từ `35tr` sang `{b_dip}tr` "
                    f"khi vé mua lại tính đúng giá gốc); ngược lại **`P4A_WAIT_FOR_100K`** giữ khe 2 chờ đúng `100K` "
                    f"giúp `NPV24` tăng đơn điệu sạch theo vốn: {w_ladder_txt} "
                    f"(riêng tại `{b_dip}tr` vượt bản tham **`{w_dip - g_dip:+.1f}tr`**)."
                )
            else:
                dip_txt = (
                    f"**`P4A_WAIT_FOR_100K`** giữ khe 2 chờ đúng `100K` giúp `NPV24` tăng đơn điệu sạch theo vốn: "
                    f"{w_ladder_txt}, vượt trội hơn bản tham `P4A_DIRECT_50K` ở mọi mức vốn trung bình."
                )
            lines.append(f"> **Đóng lỗi phi đơn điệu `P4A` (B2):** {dip_txt}")
            lines.append("")
        if fkey == "1.50x" and "B35tr_T0tr" in cells:
            p4b35 = cells["B35tr_T0tr"]["policies"]["P4B_DIRECT_100K"]
            lines.append(
                f"> **Cảnh báo rủi ro đuôi lệch ở `35tr @ 1,50x` (`P4B_DIRECT_100K`):** Dù `NPV24` trung bình vẫn "
                f"dương **`{p4b35['ev_npv_24m_vnd_tr']:+.1f}tr`**, nhưng **`NPV24` trung vị là "
                f"`{p4b35['med_npv_24m_vnd_tr']:+.1f}tr`** và xác suất không có lãi sau 24 tháng `P(NPV24 <= 0)` "
                f"lên tới **`{p4b35['p_npv24_le_0_pct']:.1f}%`**! Đây là bằng chứng trực quan nhất giải thích vì sao "
                f"**KHÔNG** đánh giá kế hoạch thi quỹ chỉ qua một con số trung bình."
            )
            lines.append("")

    lines.append(
        "### 7.3. Bảng Giao Điểm Theo Vốn Ban Đầu (`0 tr/T`, `1,00x`, `C10_NEWS_ON`) — "
        "`BF Ngày 0 + Retry Giá Gốc` vs `Toàn Bộ Giá Gốc`"
    )
    lines.append("")
    lines.append("Mỗi ô hiển thị `Cháy | TB / TV | P<=0` (`NPV 24T` theo triệu VND):")
    lines.append("")
    lines.append(
        "| Vốn (`0tr/T`) | `P1` Lặp `10K` | `P3` Leo Thông Minh | `P4A-Chờ100K` "
        "| `P4B` Tuần tự `100K` | **`P4B` Song song `2x100K`** | `P4C` `1x200K` | `P5B` 3 Quỹ (`CHƯA ĐO`) |"
    )
    lines.append("|---:|---|---|---|---|---|---|---|")
    for regime_lbl, src_map in (
        ("BF Ngày 0 + Retry Gốc", lambda btr: results["pareto_grid"]["1.00x"][f"B{int(btr)}tr_T0tr"]["policies"]),
        (
            "Toàn bộ Giá Gốc",
            lambda btr: results["all_regular_pricing_comparison"]["1.00x"][f"B{int(btr)}tr_T0tr"][
                "policies_all_regular"
            ],
        ),
    ):
        for bank_tr in BANKROLL_GRID_VND_TR:
            c = src_map(bank_tr)

            def _fmt_p(k: str, _c: dict[str, Any] = c) -> str:
                m = _c[k]
                return (
                    f"`{m['ruin_pct']:.1f}%` · **`{m['ev_npv_24m_vnd_tr']:+.1f}`**/"
                    f"`{m['med_npv_24m_vnd_tr']:+.1f}` (`{m['p_npv24_le_0_pct']:.0f}%`)"
                )

            lines.append(
                f"| **`{int(bank_tr)}tr`** *({regime_lbl})* "
                f"| {_fmt_p('P1_REPEAT_10K')} | {_fmt_p('P3_SMART_SKIP_DOWNGRADE')} "
                f"| {_fmt_p('P4A_WAIT_FOR_100K')} | {_fmt_p('P4B_DIRECT_100K')} "
                f"| {_fmt_p('P4B_PARALLEL_2X100K')} | {_fmt_p('P4C_DIRECT_200K')} "
                f"| {_fmt_p('P5B_CROSS_FIRM_SCALE50K_100K')} |"
            )
    lines.append("")

    # Section 8
    lines.append("## 8. Công Khai Trung Thực Về Giới Hạn Mô Hình & Bước Tiếp Theo (`0 VND` Hiện Tại)")
    lines.append("")
    lines.append(
        "1. **Mô phỏng vòng đời gắn cứng nhãn `DAILY_APPROX`:** Dữ liệu từng ngày được tái lập từ băng giá M1 với "
        "làm tròn `0,01` lot theo cỡ vốn đầu kỳ, ghép chuỗi 24–36 tháng bằng Circular Block-Bootstrap cấp ngày "
        "(`block_len = 5`). Như đã nêu tại Mục 3 (B1), tổn thất làm tròn ở bậc `5K/10K` còn khác cách thu nhỏ lot "
        "`85% free margin` và `balance * risk * 0,95` của EA MQL5 nên cần kiểm chứng MT5 `Model=4`."
    )
    lines.append(
        "2. **Chưa đo khớp lệnh & điều kiện flat tại reset ở các hãng ngoài FTMO "
        "(`TERMS_VERIFIED_EXECUTION_UNMEASURED` "
        "+ `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`):** `The5ers` (`max(balance, equity)` tại giờ reset MT5) và "
        "`IC Funded` (`equity` tại giờ reset server) mới được xác minh điều khoản và giá; công thức DD ngày "
        "`balance * (1 - daily_lim)` chỉ đúng khi tài khoản **đóng sạch lệnh (flat) đúng giờ reset từng hãng**. "
        "`E8 Pro` đã bị loại khỏi `P5/P5B` vì bẫy khóa sàn DD. Trước khi bỏ `1 VND` vào `The5ers` hoặc `IC Funded`, "
        "bắt buộc tự đo spread/trượt giá trên Demo MT5 thật và xin xác nhận văn bản cho EA."
    )
    lines.append(
        "3. **Kiểm tra độ tươi từng bậc giá & chống mốc tương lai/NaN (`fail-closed`):** Bộ nạp bảng giá bắt buộc "
        "mọi bậc giá (`42/42` tiers) phải có riêng `verified_utc`, từ chối mọi giá `NaN`/`Inf`/`<=0`, từ chối mốc "
        "thời gian tương lai (`> now + 1 ngày`, ví dụ `2099`), và tự báo lỗi nếu bất kỳ bậc giá nào cũ quá `7` ngày "
        "(`staleness_max_days`). Trước khi mua bất kỳ vé nào, chạy "
        "`python tooling/ai-engines/quant_factory/prop_pricing_refresh.py --refresh-fx --summary --check-staleness`."
    )
    lines.append(
        "4. **Trạng thái chi tiền (`0 VND`):** Báo cáo này là bản đồ toán học phục vụ quyết định **sau khi** các cổng "
        "kỹ thuật (`v1.02` + đối chiếu MT5 + theo dõi Demo) được chủ sở hữu phê duyệt riêng — tự bản thân báo cáo "
        "không cấp quyền mua vé hay gửi lệnh."
    )
    lines.append("")
