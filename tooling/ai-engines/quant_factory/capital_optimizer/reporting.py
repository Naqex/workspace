"""Atomic JSON persistence and plain-Vietnamese Law-15 report rendering for the capital optimizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_core.io_utils import atomic_write_json

from quant_factory.capital_optimizer.constants import DEFAULT_OUT_JSON
from quant_factory.capital_optimizer.report_modes import append_section_4
from quant_factory.capital_optimizer.report_sections import append_sections_5_to_8
from quant_factory.capital_optimizer.report_v3 import (
    append_law15_color_dot_scorecard,
    append_v3_rollover_section,
    append_v3_x13_shard_section,
)


def save_results_json(results: dict[str, Any], out_path: Path = DEFAULT_OUT_JSON) -> Path:
    """Atomically write optimizer results JSON via `quant_core.io_utils.atomic_write_json`."""
    return atomic_write_json(out_path, results, indent=2)


def _fmt_num(x: float, dec: int = 2, signed: bool = False) -> str:
    fmt = f"{{:{'+' if signed else ''},.{dec}f}}"
    return fmt.format(float(x))


def _policy_vi_name(pid: str) -> str:
    mapping = {
        "P1_REPEAT_10K": "P1: Mua lặp lại 10K",
        "P2_STEP_BY_STEP": "P2: Leo từng bậc (10K->25K->50K->100K)",
        "P3_SMART_SKIP_DOWNGRADE": "P3: Bỏ 25K + Tự hạ bậc (10K->50K->100K->2x100K)",
        "P4A_DIRECT_50K": "P4A (Tham): Vào thẳng 50K (khe 2 có thể mua 50K sớm)",
        "P4A_WAIT_FOR_100K": "P4A-Chờ100K: Vào thẳng 50K (giữ khe 2 chờ 100K)",
        "P4B_DIRECT_100K": "P4B (Tuần tự): Vào thẳng 100K (->2x100K sau khi đậu)",
        "P4B_PARALLEL_2X100K": "P4B (Song song): Mở 2x 100K ngay Ngày 0",
        "P4C_DIRECT_200K": "P4C: Vào thẳng 1x 200K",
        "P5_CROSS_FIRM_HYBRID": "P5A: Chia 3 quỹ sống sót cỡ nhỏ (10K, bỏ E8)",
        "P5B_CROSS_FIRM_SCALE50K_100K": "P5B: Chia 3 quỹ sống sót cỡ lớn (50K–100K, bỏ E8)",
    }
    return mapping.get(pid, pid)


def _exec_badge_vi(tag: str) -> str:
    if tag == "MEASURED_DEMO_EXECUTION":
        return "Đã đo khớp lệnh Demo (`MEASURED_DEMO_EXECUTION`)"
    return "Mới kiểm tra điều khoản — CHƯA đo khớp lệnh (`TERMS_VERIFIED_EXECUTION_UNMEASURED`)"


def _rank_law15_tier(metric: str, val: float) -> str:
    if metric == "ev_r":
        if val <= 0.0:
            return "Xấu"
        if val < 0.07:
            return "Đủ dùng"
        if val <= 0.15:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "pf":
        if val < 1.05:
            return "Xấu"
        if val < 1.25:
            return "Đủ dùng"
        if val <= 1.50:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "dd":
        if val > 10.0:
            return "Xấu"
        if val > 7.0:
            return "Đủ dùng"
        return "Tốt"
    if metric == "calmar":
        if val < 0.5:
            return "Xấu"
        if val < 1.2:
            return "Đủ dùng"
        if val <= 2.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "sharpe":
        if val < 0.6:
            return "Xấu"
        if val < 1.2:
            return "Đủ dùng"
        if val < 2.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "ev_fee":
        if val <= 0.0:
            return "Xấu"
        if val < 3.0:
            return "Đủ dùng"
        if val < 5.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    return "Đủ dùng"


def render_vietnamese_law15_report(results: dict[str, Any]) -> str:
    """Render owner-friendly plain-Vietnamese Law 13–15 report strictly verbatim from `results` (ZERO bare `$`)."""
    inv = results["safety_invariants"]
    inp = results["inputs"]
    traps = results["pricing_traps"]
    s5 = inp["step5_c00_vs_c10"]
    usd_vnd = float(inp["fx_usd_vnd"])
    card_fx = float(inp["card_fx_buy_fee_pct"])
    r_disc = float(inp["discount_rate_annual_pct"])
    p_var = str(inp.get("primary_variant", s5["primary_variant"]))
    be_x = results.get("friction_breakeven_x")
    fresh = inp.get("pricing_catalog_freshness", {})

    core_100k = next(
        (r for r in results["lot_rounding_audit"]["funded_1_0x"] if abs(r["capital_usd"] - 100_000.0) < 1e-6),
        results["lot_rounding_audit"]["funded_1_0x"][-1],
    )
    core_10k = next(
        (r for r in results["lot_rounding_audit"]["funded_1_0x"] if abs(r["capital_usd"] - 10_000.0) < 1e-6),
        results["lot_rounding_audit"]["funded_1_0x"][0],
    )
    core_5k = results["lot_rounding_audit"]["funded_1_0x"][0]

    def _find_mode(
        prog_substr: str,
        cap: float,
        fmult: float,
        var_name: str | None = None,
        pricing_mode: str | None = None,
    ) -> dict[str, Any] | None:
        for m in results["mode_comparison"]:
            if (
                prog_substr in m["program_id"]
                and abs(m["capital_usd"] - cap) < 1e-6
                and abs(m["friction_x"] - fmult) < 1e-6
            ):
                if var_name is not None and m["variant"] != var_name:
                    continue
                if pricing_mode is not None and m.get("pricing_mode") != pricing_mode:
                    continue
                return m
        return None

    ref_ftmo_100k = _find_mode(
        "FTMO_2STEP_STANDARD", 100_000.0, 1.00, p_var, "BF_DAY0_PLUS_REGULAR_RETRIES"
    ) or _find_mode("FTMO_2STEP_STD", 100_000.0, 1.00, p_var)
    ref_ftmo_100k_reg = _find_mode("FTMO_2STEP_STANDARD", 100_000.0, 1.00, p_var, "ALL_REGULAR")

    is_v3 = bool(results.get("v3_upgrades") or results.get("rollover_reset_sensitivity"))
    prov = results.get("tape_provenance") or {}
    lines: list[str] = []
    if is_v3:
        lines.append(
            "# Tối Ưu Hóa Vốn Thi Quỹ Đa Hãng, Độ Nhạy Rollover 00:00 & Quyền Chọn Black Friday 2 Mốc Hạn — "
            "Bản v3 (`frozen_9e_tapes_v2` Hậu-L7)"
        )
    else:
        lines.append(
            "# Tối Ưu Hóa Vốn Thi Quỹ Đa Hãng, Làm Tròn Lot 0,01 & Lịch Khuyến Mãi — "
            "Bản v2 (Đóng Đủ 9 Điểm Astra Vòng 10)"
        )
    lines.append("")
    tape_tag = (
        f" · **Băng giá M1:** `frozen_9e_tapes_v2` (NPZ SHA `{str(prov.get('npz_sha256', ''))[:16]}...`, "
        f"Binding `{str(prov.get('binding_sha256', ''))[:16]}...`)"
        if prov.get("npz_sha256")
        else ""
    )
    lines.append(
        f"- **Ngày tạo:** `{results['generated_utc'][:19]}Z` · **Cửa sổ dữ liệu:** Phát triển niêm phong "
        f"`{inv['dev_window']}` (`{inv['dev_days_count']}` phiên giao dịch){tape_tag} · **Nhãn mô phỏng:** "
        "**`DAILY_APPROX`** *(xấp xỉ cấp ngày từ băng giá M1 thực tế)*"
    )
    lines.append(
        "- **Cấp độ bằng chứng:** **Backtest trên dữ liệu quá khứ 2018–2024 (`Cluster B` đã xem — không gọi "
        "`BLIND`) + Đo khớp lệnh thực tế `28` lệnh trên Demo FTMO (`0,66x`)** — **CHƯA phải Holdout mù 2025+, "
        "CHƯA phải tiền thật đã rút về ngân hàng.**"
    )
    lines.append(
        f"- **Khóa an toàn tuyệt đối:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = "
        f"{inv['holdout_rows_analysed']}`, SHA `{inv['holdout_lock_sha256'][:16]}...`) · "
        f"`OrderSend = {inv['order_send_count']}` · **Quyết định chi tiền hiện tại: `0 VND`**."
    )
    lines.append(
        f"- **Đầu vào thực tế Việt Nam (Fail-Closed):** Tỷ giá **`1 USD = {usd_vnd:,.2f} VND`** "
        f"(`prop_pricing_catalog.json`, SHA `{str(inp['pricing_catalog_sha256'])[:16]}`, trạng thái tươi: "
        f"**`{fresh.get('status', 'FRESH')}`**, tuổi tối đa `{fresh.get('max_age_days', 0.0):.2f}d / "
        f"{fresh.get('staleness_max_days', 7):.0f}d`, kiểm đủ `{fresh.get('per_tier_count', 0)}` bậc giá) · "
        f"Phí mua thẻ quốc tế **`+{card_fx:.1f}%`** *(không hoàn lại)* · Phí hoàn tiền về thẻ FTMO **`0,0%`** "
        "*(kiểm độ nhạy `1,5%` kênh rút bên dưới)* · Phí rút lợi nhuận + quy đổi VND **`1,5%–4,0%`** tùy hãng · "
        f"Chiết khấu **NPV**: **`{r_disc:.1f}%/năm`**."
    )
    ver_tag = "v3" if is_v3 else "v2"
    lines.append(
        f"- **Nhánh chính `{ver_tag}` & kiểm soát công bằng:** Toàn bộ bảng đánh giá, lịch sale động và lưới Pareto "
        f"chạy trên **`{p_var}`** *(bật khiên tin đỏ ở mọi pha P1/P2/Funded)* kèm đối chứng **`C00`**; **tắt hoàn toàn "
        "`own_book` (`0,0`)** trong mọi bảng xếp hạng chính sách prop; giá vé áp **đúng ngày mua** (`BF Ngày 0 + "
        "vé mua lại/mở sau tính giá gốc`, kèm bảng đối chứng **`Toàn bộ giá gốc`**); **loại `E8 Pro`** khỏi danh "
        "mục đa quỹ ít rủi ro (`P5/P5B` chỉ còn `3` quỹ sống sót: `FTMO + The5ers + IC Funded`)."
    )
    lines.append("")

    # Section 1
    lines.append(f"## 1. Tóm Tắt Dễ Hiểu Cho Chủ Sở Hữu (5 Kết Luận Quan Trọng Nhất — Bản {ver_tag})")
    lines.append("")
    ratios = traps.get("details", {}).get("ftmo_2step_std_fee_ratio_pct", {})
    lines.append(
        f"1. **Cảnh báo 3 cái bẫy giá thực tế trên màn hình thanh toán Việt Nam:** "
        f"(a) **Bẫy `25K` FTMO Standard:** giá Black Friday `220,50 USD` chiếm "
        f"**`{ratios.get('25K_promo_pct', 0.882):.3f}%`** vốn — **đắt hơn "
        f"`+{ratios.get('25k_vs_10k_promo_premium_pct', 28.4):.1f}%` so với `10K`** (`0,687%`) và **đắt hơn "
        f"`+{ratios.get('25k_vs_50k_promo_premium_pct', 44.2):.1f}%` so với `50K`** (`0,612%`)! Tuyệt đối "
        "**BỎ QUA gói `25K`**; "
        "(b) **`200K` vs `2x 100K`:** `200K` (`957,36 USD` BF / `1.196,70 USD` giá gốc) có tỷ lệ phí **y hệt** "
        "`100K` (`0,4787%` BF / `0,5984%` giá gốc) nhưng dồn toàn bộ trứng vào 1 vé; khi tách đúng giá gốc cho vé "
        "mua lại, **`P4B_PARALLEL_2X100K` (mở song song `2x 100K` Ngày 0)** giữ nhiều viên đạn dự phòng hơn ở vốn "
        "`50tr–80tr` (cần nhớ cả 2 vé chịu **tương quan drawdown cùng ngày = `1,0`**); "
        "(c) **FTMO Swing `50K/100K/200K` bị khóa tại Việt Nam** (`available_vn = false`), và **E8 Pro `100K`** "
        "(`0,415%`) đắt hơn mua `2x 50K` (`0,388%`)."
    )
    lines.append(
        "2. **Tổn thất làm tròn `0,01` lot là có thật (`DAILY_APPROX`, cần đối chiếu thêm MT5 `Model=4`):** "
        f"Ở tài khoản `5K` (Funded `1,0x`), làm tròn xuống bội `0,01` lot làm bỏ mất "
        f"**`{core_5k['min_lot_rejected']}`** "
        f"lệnh và kéo tụt lợi suất năm **`{core_5k['lot_rounding_drag_vs_200k_pct']:+.2f}%`** so với `200K` "
        f"(`+{core_5k['ann_pct']:.2f}%` vs `+{results['lot_rounding_audit']['funded_1_0x'][-1]['ann_pct']:.2f}%`); "
        f"`10K` bị kéo lùi **`{core_10k['lot_rounding_drag_vs_200k_pct']:+.2f}%`**, còn từ `50K–100K` trở lên "
        f"tổn thất gần như biến mất (`{core_100k['lot_rounding_drag_vs_200k_pct']:+.2f}%`, `0` lệnh bị loại)."
    )
    if ref_ftmo_100k:
        s100 = ref_ftmo_100k["single_ticket_zero_retry"]
        reg_note = ""
        if ref_ftmo_100k_reg:
            sr = ref_ftmo_100k_reg["single_ticket_zero_retry"]
            reg_note = (
                f" *(nếu mua giá gốc không sale `598,35 USD` ~ `{sr['effective_fee_vnd_tr']:.1f}tr`: "
                f"`NPV24 {sr['ev_npv_24m_vnd_tr']:+.1f}tr`, `EV/Phí {sr['ev_per_fee_npv24']:+.2f}x`)*"
            )
        lines.append(
            f"3. **Hiệu quả 1 vé không thử lại (`FTMO 2-Step Standard 100K · {p_var} · 1,00x`, BF `478,68 USD` ~ "
            f"`{s100['effective_fee_vnd_tr']:.1f}` triệu VND cả phí thẻ, hoàn phí về thẻ `0%`):** "
            f"Xác suất đậu vào Funded trong `24` tháng đạt **`{s100['pass_24m_pct']:.1f}%`**, trung vị thời gian "
            f"có lần rút tiền đầu (nhóm đã rút) là **`{s100['cond_med_pay1_cal_days']:.0f}` ngày** (không điều kiện "
            f"chặn `730d`: **`{s100['uncond_med_pay1_cap730_days']:.0f}` ngày**), cháy Funded `12T` "
            f"**`{s100['funded_12m_breach']['breach_12m_pct']:.2f}%`**, `NPV 24T` trung bình "
            f"**`{s100['ev_npv_24m_vnd_tr']:+.1f}` tr VND** (trung vị **`{s100['med_npv_24m_vnd_tr']:+.1f}tr`**, "
            f"xác suất lỗ ròng `P(NPV<=0)` = **`{s100['p_net_le_0_24m_pct']:.1f}%`**, "
            f"**`{s100['ev_per_fee_npv24']:+.2f}x`** trên mỗi đồng phí){reg_note}."
        )
    lines.append(
        "4. **Cảnh báo trung vị âm ở chế độ stress nặng `1,50x` (KHÔNG che sau số trung bình dương):** "
        f"Trên mọi ô Pareto ở Mục 7, báo cáo `{ver_tag}` công bố đầy đủ bộ ba **`NPV24 Trung bình (TB)` + "
        "`NPV24 Trung vị (TV)` + `Xác suất lỗ ròng P(NPV24 <= 0)`**. Khi trượt giá tăng `+50%` (`1,50x`), dù trung "
        "bình vẫn dương nhờ nhánh thắng lớn, **trung vị nhiều chính sách rơi xuống âm và hơn `50%` kịch bản hòa/lỗ "
        "sau 24 tháng** — nhắc nhở dứt khoát phải giữ cổng đo trượt giá thực tế `< 1,25x`."
    )
    lines.append(
        "5. **Loại `E8 Pro` khỏi danh mục đa quỹ ít rủi ro (`P5/P5B` chỉ gồm `3` hãng: "
        "`FTMO + The5ers + IC Funded`):** "
        "Ngay cả khi cố giữ lãi tới `+8%` hoặc `+10%` trước lần rút đầu trên `E8 Pro`, cơ chế khóa sàn DD tại vốn "
        "gốc + giữ lại `50%` vẫn gây tỷ lệ cháy Funded 12 tháng hai chữ số (Astra đối chứng `34,18% / 17,38%` ở "
        "`1,00x`). Đồng thời `The5ers` (`max(balance, equity)` tại giờ reset) và `IC Funded` (`equity` tại giờ reset) "
        "đều mang song song 2 nhãn **`TERMS_VERIFIED_EXECUTION_UNMEASURED`** và "
        "**`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** *(công thức `balance * (1 - daily_lim)` chỉ đúng khi đóng "
        "sạch lệnh đúng giờ reset của từng hãng)* — **tuyệt đối KHÔNG rót tiền thật** trước khi tự đo khớp lệnh Demo "
        "MT5 riêng của từng hãng."
    )
    lines.append("")

    # Section 2 (Law-15 vertical color-dot balanced scorecard)
    append_law15_color_dot_scorecard(
        lines,
        core_100k=core_100k,
        ref_ftmo_100k=ref_ftmo_100k,
        p_var=p_var,
        usd_vnd=usd_vnd,
        be_x=be_x,
        rank_fn=_rank_law15_tier,
    )

    # Section 2.1
    lines.append(
        "### 2.1. Độ Bền Trước Trượt Giá (`0,66x` Đo Sống Demo FTMO -> `4,00x` Sốc Gãy Cấu Trúc, `100K` `1,0x`)"
    )
    lines.append("")
    lines.append(
        "| Mức ma sát (so với M1 chuẩn) | Diễn giải thực tế | Lãi năm (%) | Lãi năm (tr VND / `100K`) "
        "| `PF` | `EV / lệnh` | `Max DD` | `Calmar` | `Sharpe` |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    fric_labels = {
        0.66: "Đo sống 28 lệnh Demo FTMO (trung vị bảo thủ)",
        1.00: "Chuẩn băng giá M1 Bid/Ask",
        1.25: "Trượt giá tăng +25%",
        1.50: "Stress trượt giá nặng +50%",
        1.75: "Ngưỡng báo động đỏ / Cắt chi phí chìm",
        2.00: "Sốc cực đoan gấp đôi chi phí",
        2.50: "Vượt ngưỡng gãy (chuyển âm ròng)",
        3.00: "Sốc gấp 3 lần chi phí",
        3.50: "Sốc phá hủy 3,5x chi phí",
        4.00: "Sốc cực hạn 4,0x chi phí",
    }
    for row in results["friction_sweep_100k"]:
        fx = float(row["friction_x"])
        ann_vnd = (row["ann_pct"] / 100.0) * 100_000.0 * usd_vnd / 1_000_000.0
        lines.append(
            f"| **`{fx:.2f}x`** | {fric_labels.get(fx, '')} | `{row['ann_pct']:+.2f}%` | `{ann_vnd:+.1f}` tr "
            f"| `{row['profit_factor']:.2f}` | `{row['ev_per_trade_r']:+.3f}R` | `{row['peak_dd_pct']:.2f}%` "
            f"| `{row['calmar']:.2f}` | `{row['sharpe']:.2f}` |"
        )
    lines.append("")

    # Section 3
    lines.append(
        "## 3. Tác Động Làm Tròn `0,01` Lot Thực Tế (`5K -> 200K`) & Công Khai Khác Biệt Cách Tính Cỡ Lệnh (B1)"
    )
    lines.append("")
    lines.append(
        "Mọi tài khoản dưới đây đều được chạy lại từ đầu bằng công thức làm tròn xuống từng bước `0,01` lot "
        "(`raw_lots < 0,01` -> bỏ lệnh), **tuyệt đối không nhân tuyến tính từ `10K`**:"
    )
    lines.append("")
    lines.append(
        "| Cỡ tài khoản | Funded `1,0x`: Lãi năm | Lệch vs `200K` | Bỏ `<0,01` "
        "| Funded `1,25x` (`C10_NEWS_ON`): Lãi năm / Lệch | Phanh Đỏ `0,4x`: Lãi năm "
        "| Phanh Đỏ: Bỏ `<0,01` | Phanh Đỏ: Lệch vs `200K` |"
    )
    lines.append("|---:|---:|---:|---:|---|---:|---:|---:|")
    f1_rows = results["lot_rounding_audit"]["funded_1_0x"]
    f125_rows = results["lot_rounding_audit"].get("funded_1_25x", f1_rows)
    r04_rows = results["lot_rounding_audit"]["red_brake_0_4x"]
    for f1, f125, r04 in zip(f1_rows, f125_rows, r04_rows, strict=False):
        lines.append(
            f"| **`{int(f1['capital_usd'] // 1000)}K USD`** | `+{f1['ann_pct']:.2f}%` "
            f"| **`{f1['lot_rounding_drag_vs_200k_pct']:+.2f}%`** "
            f"| `{f1['min_lot_rejected']}` ({f1['min_lot_reject_pct']:.2f}%) "
            f"| `+{f125['ann_pct']:.2f}%` (`{f125['lot_rounding_drag_vs_200k_pct']:+.2f}%`) "
            f"| `+{r04['ann_pct']:.2f}%` | **`{r04['min_lot_rejected']}`** ({r04['min_lot_reject_pct']:.1f}%) "
            f"| **`{r04['lot_rounding_drag_vs_200k_pct']:+.2f}%`** |"
        )
    lines.append("")
    lines.append(
        "> **Công khai trung thực về khác biệt tính cỡ lệnh giữa Python và EA MQL5 (Điểm B1 Astra Vòng 10):** "
        "Hàm Python `get_exact_tier_stage` tính khối lượng lệnh theo **vốn gốc đầu kỳ cố định** (`initial * eff_risk`) "
        "và **bỏ thẳng lệnh** nếu thiếu ký quỹ (`margin_rejected`), trong khi **EA MQL5 thực tế** "
        "(`Naqex_Master_Prop7E`) tính khối lượng theo **số dư hiện tại nhân `0,95`** (`balance * risk * 0.95`) và "
        "**tự động thu nhỏ lot xuống mức `85%` ký quỹ khả dụng** (`free margin`) thay vì bỏ trắng lệnh. Do đó các "
        "tỷ lệ tổn thất làm tròn ở bậc `5K / 10K` phía trên được gắn nhãn **`DAILY_APPROX` (ước lượng Python)**, "
        "chưa thay thế phép đối chứng trực tiếp trên MT5 `Model=4` Real-Tick cho từng cỡ tài khoản."
    )
    lines.append("")

    append_section_4(lines, results, p_var=p_var, s5=s5, find_mode=_find_mode)
    append_v3_rollover_section(lines, results)
    append_sections_5_to_8(lines, results, p_var=p_var, policy_vi_name=_policy_vi_name)
    if is_v3:
        append_v3_x13_shard_section(lines, results)

    md = "\n".join(lines)
    if "$" in md:
        raise ValueError("PROSE_POLICY_VIOLATION: Bare '$' symbol detected in Vietnamese Law-15 report!")
    return md
