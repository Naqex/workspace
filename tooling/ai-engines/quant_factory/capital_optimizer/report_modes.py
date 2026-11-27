"""Markdown report Section 4 (multi-firm & multi-mode comparison + Step 5 MT5 pairs)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quant_factory.capital_optimizer.constants import DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT


def append_section_4(
    lines: list[str],
    results: dict[str, Any],
    *,
    p_var: str,
    s5: dict[str, Any],
    find_mode: Callable[..., dict[str, Any] | None],
) -> None:
    """Append Section 4 of the plain-Vietnamese Law-15 report (zero bare `$`)."""
    lines.append(
        f"## 4. So Sánh 4 Quỹ & Mọi Chế Độ Thi — 1 Vé Không Thử Lại (`{p_var}` Chính + `C00` Đối Chứng, `DAILY_APPROX`)"
    )
    lines.append("")
    lines.append(
        "- Mỗi chế độ có trần lỗ ngày chặt hơn (`3%` ở FTMO 1-Step/Instant, `2,5%` ở E8 Pro, `4%/8%` ở The5ers "
        "`50K/100K`) đều được **tự động hiệu chuẩn hệ số rủi ro an toàn riêng** trên nhánh **`C10_NEWS_ON`**."
    )
    lines.append(
        "- **Mốc neo DD ngày theo đúng hợp đồng từng quỹ (`daily_dd_anchor`) & nhãn kiểm chứng DD "
        "(`dd_rule_verification_tag`):** FTMO & E8 Pro tính trần lỗ ngày theo **vốn gốc ban đầu** "
        "(`s_bal - cap * daily_lim`). Riêng **`The5ers`** *(neo theo `max(balance, equity)` tại mốc reset `00:00` "
        "MT5)* và **`IC Funded`** *(neo theo `equity` tại mốc reset `00:00` GMT+2/+3)* đều gắn nhãn "
        "**`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** song song với **`TERMS_VERIFIED_EXECUTION_UNMEASURED`**: "
        "công thức mô phỏng `balance * (1 - daily_lim)` chỉ đúng khi tài khoản **đóng sạch lệnh (flat) đúng giờ "
        "reset từng hãng**."
    )
    lines.append(
        "- Cột `Đậu / Rớt / Chờ` ở mọi mốc tháng (`3T / 6T / 12T / 24T`) luôn có tổng đúng bằng **`100,0%`**. "
        "Cột `Cháy Funded 12T` tính trên **đúng mẫu số các vé đã vào Funded** (cần `~299` quan sát độc lập không "
        "cháy ngoài thực tế để chứng minh cận trên `95% < 1%`)."
    )
    lines.append("")
    lines.append(
        "### 4.1. Bảng So Sánh Ở Ma Sát Nền `1,00x` (Phí Thực VN: Mua Thẻ `+2,5%`, Hoàn Thẻ FTMO `0%`, "
        "Phí Rút Lãi `1,5%–4,0%`, Chiết Khấu `6%/Năm`)"
    )
    lines.append("")
    lines.append(
        "| Hãng / Chế độ / Cỡ (`Biến thể` · `Giá`) | Khớp lệnh | Phí (USD / tr VND) | Luật DD (`Mốc neo`) & Rủi ro "
        "| `24T` Đậu / Rớt / Chờ (`100%`) | Chờ Payout TV (ĐK / KĐK `730d`) | Cháy Funded `12T` (Wilson `95%`) "
        "| Tháng đói (`P50/P95`) | `NPV 24T` TB / TV (tr VND) | `P(<=0)` | `EV/Phí` |"
    )
    lines.append("|---|---|---:|---|---|---|---|---|---:|---:|---:|")
    for m in results["mode_comparison"]:
        if abs(m["friction_x"] - 1.00) > 1e-6:
            continue
        s = m["single_ticket_zero_retry"]
        m24 = s["monthly_pass_fail_pending"].get("24m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        fb = s["funded_12m_breach"]
        cm = m["calibrated_mults"]
        badge = "ĐO DEMO" if m["execution_evidence_tag"] == "MEASURED_DEMO_EXECUTION" else "CHƯA ĐO"
        anc_short = (
            "PrevBal · FLAT_RESET_ONLY"
            if m.get("dd_rule_verification_tag") == DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT
            else ("PrevBal" if m.get("daily_dd_anchor") == "prev_day_balance" else "InitBal")
        )
        pr_short = "BF" if m.get("pricing_mode") == "BF_DAY0_PLUS_REGULAR_RETRIES" else "Gốc"
        dd_desc = (
            f"{m['dd_daily_pct']:.1f}/{m['dd_max_pct']:.0f}% {m['dd_type'][:3]} ({anc_short}) · "
            f"{cm['p1']:.2f}/{cm['p2']:.2f}/{cm['funded']:.2f}x"
        )
        cond_d = f"{s['cond_med_pay1_cal_days']:.0f}d" if s["cond_med_pay1_cal_days"] > 0 else "N/A"
        lines.append(
            f"| **{m['mode_name']} {int(m['capital_usd'] // 1000)}K** (`{m['variant']}` · `{pr_short}`) "
            f"| `{badge}` | `{m['promo_usd']:.0f}` / `{s['effective_fee_vnd_tr']:.1f}tr` | `{dd_desc}` "
            f"| `{m24['pass_pct']:.1f}% / {m24['fail_pct']:.1f}% / {m24['pending_pct']:.1f}%` "
            f"| `{cond_d}` / `{s['uncond_med_pay1_cap730_days']:.0f}d` "
            f"| `{fb['breach_12m_pct']:.2f}%` (`<={fb['wilson_95_upper_pct']:.1f}%`) "
            f"| `{s['funded_dry_months_pct']:.0f}%` (`{s['funded_dry_streak_p50_months']}/"
            f"{s['funded_dry_streak_p95_months']}T`) "
            f"| **`{s['ev_npv_24m_vnd_tr']:+.1f}`** / `{s['med_npv_24m_vnd_tr']:+.1f}` "
            f"| `{s['p_net_le_0_24m_pct']:.1f}%` | **`{s['ev_per_fee_npv24']:+.2f}x`** |"
        )
    lines.append("")

    m_1step_100 = find_mode("FTMO_1STEP", 100_000.0, 1.00, p_var)
    m_inst_100 = find_mode("FTMO_INSTANT", 100_000.0, 1.00, p_var)
    m_e8_50 = find_mode("E8_PRO", 50_000.0, 1.00, p_var)
    s1st = m_1step_100["single_ticket_zero_retry"] if m_1step_100 else None
    sins = m_inst_100["single_ticket_zero_retry"] if m_inst_100 else None
    se8 = m_e8_50["single_ticket_zero_retry"] if m_e8_50 else None
    parts_trap = []
    if s1st is not None:
        parts_trap.append(
            f"(1) **`FTMO 1-Step` (`100K`)** có `EV/Phí` cao (`{s1st['ev_per_fee_npv24']:+.2f}x`) nhưng luật "
            f"**`50%` Best Day + EOD Trailing** làm **`{s1st['funded_dry_months_pct']:.1f}%`** số tháng Funded khô "
            f"hạn và kéo ngày chờ payout đầu lên **`{s1st['cond_med_pay1_cal_days']:.0f}` ngày**"
        )
    if sins is not None:
        parts_trap.append(
            f"(2) **`FTMO Instant` (`100K`)** rút nhanh nhất (`{sins['cond_med_pay1_cal_days']:.0f}` ngày) nhưng phí "
            f"cao gấp `5,5x` 2-Step (`EV/Phí {sins['ev_per_fee_npv24']:+.2f}x`), cháy Funded `12T` nhảy lên "
            f"**`{sins['funded_12m_breach']['breach_12m_pct']:.2f}%`** (Intraday Trailing) và "
            f"**`{sins['funded_dry_months_pct']:.1f}%`** tháng đói (`30%` Best Day)"
        )
    if se8 is not None:
        e8_buf_rows = results.get("e8_pro_buffer_sensitivity", {}).get("mc_buffer_sweep_50k_1_00x", [])
        buf_txt = ""
        if len(e8_buf_rows) >= 3:
            b8, b10 = e8_buf_rows[1], e8_buf_rows[2]
            buf_txt = (
                f"; ngay cả khi cố chờ lãi **`+8%` / `+10%`** trước lần rút đầu (đệm giữ lại `4% / 5%`), mô phỏng MC "
                f"vẫn cháy **`{b8['funded_12m_breach_pct']:.2f}%` / `{b10['funded_12m_breach_pct']:.2f}%`** trong 12 "
                "tháng (Astra Vòng 10 đối chứng **`34,18%` / `17,38%`** ở `1,00x`) -> **ĐÃ LOẠI `E8 Pro` khỏi mọi "
                "danh mục đa quỹ `P5/P5B`**"
            )
        parts_trap.append(
            "(3) **`E8 Pro` (`50K`)** bị bẫy **khóa sàn DD về vốn gốc sau lần rút đầu** + giữ lại `50%` + trần lãi "
            f"ngày `2%`: rút ngay `+1%` làm cháy **`{se8['funded_12m_breach']['breach_12m_pct']:.2f}%`** tài khoản "
            f"Funded trong 12 tháng{buf_txt}"
        )
    if parts_trap:
        lines.append("> **Phát hiện bẫy cấu trúc cực quan trọng (B4):** " + "; ".join(parts_trap) + ".")
        lines.append("")

    lines.append(
        "### 4.2. Chi Tiết `Đậu / Rớt / Chờ` Theo Tháng (`3T / 6T / 12T / 24T`, Tổng = `100%`) — "
        "`FTMO 2-Step Standard 100K` (`C10_NEWS_ON` Chính vs `C00` Đối Chứng vs `C10` News-OFF)"
    )
    lines.append("")
    lines.append(
        "| Biến thể & Ma sát | `3` Tháng (`Đậu/Rớt/Chờ`) | `6` Tháng (`Đậu/Rớt/Chờ`) | `12` Tháng (`Đậu/Rớt/Chờ`) "
        "| `24` Tháng (`Đậu/Rớt/Chờ`) | `NPV 24T` TB / TV (tr VND) | `P(NPV24 <= 0)` |"
    )
    lines.append("|---|---|---|---|---|---:|---:|")
    for var_c in ("C10_NEWS_ON", "C00", "C10"):
        for fm in (1.00, 1.50):
            mm = find_mode(
                "FTMO_2STEP_STANDARD", 100_000.0, fm, var_c, "BF_DAY0_PLUS_REGULAR_RETRIES"
            ) or find_mode("FTMO_2STEP_STD", 100_000.0, fm, var_c)
            if not mm:
                continue
            s = mm["single_ticket_zero_retry"]
            mb = s["monthly_pass_fail_pending"]

            def _c(k: str, _mb: dict[str, Any] = mb) -> str:
                r = _mb.get(k, {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
                return f"`{r['pass_pct']:.1f}% / {r['fail_pct']:.1f}% / {r['pending_pct']:.1f}%`"

            tag_v = (
                " *(Chính)*"
                if var_c == p_var
                else (" *(Đối chứng)*" if var_c == "C00" else " *(Chỉ tham khảo News-OFF)*")
            )
            lines.append(
                f"| **`{var_c}`{tag_v} @ `{fm:.2f}x`** | {_c('3m')} | {_c('6m')} | {_c('12m')} | {_c('24m')} "
                f"| **`{s['ev_npv_24m_vnd_tr']:+.1f}tr`** / `{s['med_npv_24m_vnd_tr']:+.1f}tr` "
                f"| `{s['p_net_le_0_24m_pct']:.1f}%` |"
            )
    lines.append("")

    if s5.get("mt5_model4_q4_2024_same_phase_pairs"):
        lines.append(
            "### 4.3. Đối Chiếu Thực Tế MT5 `Model=4` Real-Tick (Q4/2024) Từ Step 5 (`C00` vs `C10`) & "
            "Lý Do Chốt `C10_NEWS_ON`"
        )
        lines.append("")
        lines.append(
            "| Pha (`FTMO_STD 10K`, `swap=0`) | `C00` (News ON) Lệnh / Lãi / `PF` / `EqDD` "
            "| `C10` (News OFF P1/P2) Lệnh / Lãi / `PF` / `EqDD` | Chênh lệch (`C10 - C00`) |"
        )
        lines.append("|---|---|---|---|")
        for ph in ("P1", "P2", "FUNDED"):
            pair = s5["mt5_model4_q4_2024_same_phase_pairs"].get(ph)
            if not pair:
                continue
            c0, c1, dl = pair["C00"], pair["C10"], pair["delta_c10_minus_c00"]
            lines.append(
                f"| **`{ph}`** | `{c0['trades']}` / `{c0['net_profit_usd']:+.2f} USD` / `PF {c0['profit_factor']}` / "
                f"`EqDD {c0['equity_dd_pct']}%` | `{c1['trades']}` / `{c1['net_profit_usd']:+.2f} USD` / "
                f"`PF {c1['profit_factor']}` / `EqDD {c1['equity_dd_pct']}%` "
                f"| `{dl['net_profit_usd']:+.2f} USD` (`EqDD {dl['equity_dd_pct']:+.2f}%`) |"
            )
        lines.append("")
        lines.append(
            "> Vì `C10` (tắt tin đỏ) thua nặng ở P1 Q4/2024 (`-337,64 USD`, `EqDD 8,82%`), trong khi Step 6 chứng "
            "minh **`C10_NEWS_ON`** (giữ cỡ lệnh & ProfitLock `C10` + **BẬT khiên tin đỏ ở mọi pha**) vượt cả `C00` "
            "lẫn `C10` News-OFF, toàn bộ bản tối ưu `v2` đã khóa nhánh chính là **`C10_NEWS_ON`**."
        )
        lines.append("")
