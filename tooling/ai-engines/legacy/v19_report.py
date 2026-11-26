"""Bounded V19 report from completed immutable account, path and test receipts."""
from pathlib import Path
import json
import numpy as np
from prop_v19_common import *
from prop_v19_stress import verify
from prop_v14_accounts import trade_money
from prop_v15_accounts import exact_quantity
from prop_v18_costs import cost_bindings
from v19_delivery import idle

REPORT = Path("planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116")


def fmt(value, digits=2):
    return "—" if value is None else f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] + [
        "| " + " | ".join(str(v).replace("|", r"\|") for v in row) + " |" for row in rows]


def economics():
    rows = []
    import prop_portfolio_accounts as portfolio
    for version, root in (("V16", V18), ("V19", JOB / "Full-pack")):
        for mode, pct in (("PRIMARY", 100), ("PRIMARY", 150), ("STRICT", 100)):
            blocks = read(root / f"OLHC-{mode}-blocks.json")["blocks"]
            trades = [t for b in blocks for t in b["trades"]]
            by_year = {}
            skipped = 0
            with cost_bindings(pct):
                for t in trades:
                    year = datetime.fromtimestamp(t["entry_msc"] / 1000, timezone.utc).year
                    r = by_year.setdefault(year, dict(signals=0, trades=0, net_USD=0., net_R=0.))
                    r["signals"] += 1
                    try:
                        quantity = exact_quantity(t, 150)
                    except ValueError:
                        skipped += 1
                        continue
                    money = portfolio.trade_money(t, quantity, "SYM_FLAT", 150)
                    r["trades"] += 1
                    r["net_USD"] += money["net_usd"]
                    r["net_R"] += money["net_R"]
            rows.append(dict(version=version, source=mode, friction=pct, years=by_year,
                reference_net_R=sum(r["net_R"] for r in by_year.values()),
                reference_net_USD=sum(r["net_USD"] for r in by_year.values()), min_lot_skips=skipped,
                reference_risk_USD=150, account_caps_or_harvest_not_applied=True))
    return rows


def collect():
    idle()
    frozen = verify()
    summary = read(V18 / "tournament.json")
    historical, monte, historical_audits = [], [], []
    parent = read(Path("planning/research/FINAL-CONVERGENCE-V18-RESULTS-20261116.json"))
    for tag in ("OLHC", "OHLC"):
        for mode, pct in (("PRIMARY", 100), ("PRIMARY", 150), ("STRICT", 100)):
            old = next(r for r in parent["historical"] if
                       (r["order"], r["mode"], r["friction_pct"]) == (tag, mode, pct))
            historical.append(dict(version="V16", order=tag, mode=mode, friction_pct=pct, **{
                k: old[k] for k in ("phase1", "funded", "median_months", "worst_daily",
                                   "worst_static", "breaches", "standalone_payout")}))
            label = f"Full-{tag}-{mode}-{pct}"
            value = read(JOB / (label + "-summary.json"))["cases"][0]
            historical.append(dict(version="V19", order=tag, mode=mode, friction_pct=pct, **value))
            new_rows = read(JOB / (label + "-accounts.json"))
            old_audit = read(JOB / f"baseline-history-{tag}-{mode}-{pct}-audit.json")
            old_packet = read(Path(old_audit["source"]))
            old_rows = old_packet["rows"] if isinstance(old_packet, dict) else old_packet
            for output, books in ((historical[-2], old_rows), (historical[-1], new_rows)):
                recent = [r for r in books if r["kind"] == "CHALLENGE" and r["start_msc"] >= DEV_END]
                output.update(recent_starts=len(recent),
                    recent_completions=sum(any(p["phase"] == 2 for p in r["phase_passes"]) for r in recent))
            for version, name in (("V16", f"baseline-history-{tag}-{mode}-{pct}-audit.json"),
                                  ("V19", label + "-audit.json")):
                audited = read(JOB / name)
                if not audited["passed"] or audited["accounts"] != 106:
                    raise ValueError("V19_full_historical_audit_incomplete")
                historical_audits.append(dict(version=version, path=name, accounts=audited["accounts"],
                                               sha256=sha(JOB / name)))
            for version in ("V16", "V19"):
                name = f"MC-{version}-{tag}-{mode}-{pct}-summary.json"
                value = read(JOB / name)
                if value["paths"] != 5000 or value["accounts_fully_audited"] != 10000:
                    raise ValueError("V19_MC_full_audit_incomplete")
                monte.append(dict(version=version, path=name, sha256=sha(JOB / name),
                    payout_basis="Standalone Funded from path start; not payouts after passing Challenge.", **value))
    states = read(JOB / "state-first-passage.json")
    paid = read(JOB / "state-payout-supplement.json")
    unit_drag = read(JOB / "Dev-fit.json")["volatility_drag"]
    for r in states["rows"]:
        p = next(p for p in paid["rows"] if p["policy"] == r["policy"] and p["state_pct"] == r["account_return_pct"])
        r["post_funded_payout_per_elapsed_month_USD"] = p["mean_USD_per_elapsed_month"]
        r["payout_zero_paths"] = p["zeros"]
        denominator = (1 + r["account_return_pct"] / 100) ** 2
        r["volatility_drag_reference"] = dict(
            approximate_daily_log_drag=unit_drag["approximate_daily_log_drag"] / denominator,
            approximate_annual_log_drag=unit_drag["approximate_annual_log_drag"] / denominator,
            basis="Same fixed-$150 Dev unit-book USD variance divided by hypothetical opening equity squared.",
            not_measured_adaptive_account_returns=True,
            measured_adaptive_account_log_drag=None)
    reset = []
    for policy in ("V16", "V19"):
        fresh = next(r for r in states["rows"] if r["policy"] == policy and r["account_return_pct"] == 0)
        for r in states["rows"]:
            if r["policy"] != policy or r["account_return_pct"] >= 0:
                continue
            reset.append(dict(policy=policy, state_pct=r["account_return_pct"],
                restricted_wait_to_fresh_ratio=r["funded"]["restricted_mean_months"] /
                    fresh["funded"]["restricted_mean_months"],
                exceeds_two_fresh_restricted_waits=r["funded"]["restricted_mean_months"] >
                    2 * fresh["funded"]["restricted_mean_months"],
                conditional_wait_ratio=(r["funded"]["conditional_mean_months"] /
                    fresh["funded"]["conditional_mean_months"]) if r["funded"]["conditional_mean_months"] is not None
                    and fresh["funded"]["conditional_mean_months"] else None,
                actual_payout_per_elapsed_month_USD=r["post_funded_payout_per_elapsed_month_USD"],
                fresh_payout_per_elapsed_month_USD=fresh["post_funded_payout_per_elapsed_month_USD"],
                unconditional_expected_wait_ratio=None, optimum_reset_boundary_identified=False,
                retry_fee_not_known=True, automatic_account_reset=False))
    tests, smoke = read(JOB / "tests-final-matrix.json"), read(JOB / "smoke-final-results.json")
    if tests["preserved_V18_IDs"] != 1153 or not tests["zero_skip"]:
        raise ValueError("V19_test_history_incomplete")
    receipts = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in JOB.iterdir()
                if p.is_file() and p.suffix in (".json", ".jsonl")}
    correction_root = JOB / "O2-constraint-correction"
    correction_fit, correction_decision = read(correction_root / "fit.json"), read(correction_root / "decision.json")
    correction_audits = [read(p) for p in correction_root.glob("Dev-*-audit.json")]
    if len(correction_audits) != 8 or not all(r["passed"] for r in correction_audits):
        raise ValueError("V19_exact_O2_Dev_audit_incomplete")
    correction_count = sum(r["accounts"] for r in correction_audits)
    result = dict(schema="V19-results-v1", decision="NO_QUALIFIED_CPPI_OR_GAP_IMMUNIZATION_UPGRADE",
        prop_qualified=False, actual_broker_orders=0, actual_payout_USD=0,
        frozen=frozen, merged_PR97="beaabdd44acc24d6724dfe7f9af2738cef571638",
        Dev_fit=read(JOB / "Dev-fit.json"), Dev_full_ledger_audits=1752 + correction_count,
        corrected_O2=dict(fit=correction_fit, decision=correction_decision,
            full_ledger_audits=correction_count, original_heuristic_fit_retained=True,
            audit_bindings=[dict(path=p.name, sha256=sha(p)) for p in
                            sorted(correction_root.glob("Dev-*-audit.json"))],
            correction_registered_after_baseline_Validation_exposure=True),
        gaps=read(JOB / "gap-identities.json"), source_probes=read(JOB / "source-probe-verdict.json"),
        source_census_delta_summary={k: read(JOB / "source-census-delta.json")[k] for k in ("records", "unchanged", "errors")},
        historical=historical, historical_audits=historical_audits, reference_economics=economics(),
        monte=monte, full_MC_ledger_audits=sum(r["accounts_fully_audited"] for r in monte),
        state_first_passage=states, state_assumptions=dict(phase=1, initially_flat=True,
            prior_qualifying_trading_days=0, midnight_anchor="hypothetical opening balance",
            static_reference_USD=50000, prior_peak="max(initial capital, hypothetical opening equity)",
            not_an_estimate_conditioned_on_all_states_of_an_actual_underwater_account=True),
        O3_actual_payout_measurement=paid["rows"], reset_analysis=reset,
        O3_original_first_passage_outcomes_identical=paid["all_original_first_passage_outcomes_identical"],
        engineering=dict(tests=tests, smoke=smoke, storage=read(JOB / "storage-final-summary.json"),
            storage_growth_attribution=read(JOB / "storage-growth-attribution.json"),
            V18_slow_fast_attribution=read(JOB / "V18-smoke-slow-fast-attribution.json"),
            smoke_profile_pair=read(JOB / "smoke-diagnostic-paired.json"),
            smoke_workers_comparison=read(JOB / "smoke-diagnostic-workers.json"),
            scalar_oracle_parity=read(JOB / "scalar-oracle-parity.json")),
        adapter=dict(CLI=read(JOB / "adapter-CLI-verification.json"),
            final_CLI=read(JOB / "adapter-final-v3-CLI-verification.json"),
            native_signal_parity=read(JOB / "adapter-native-signal-prefix-parity.json"),
            spec="planning/research/FTMO-FREE-TRIAL-ADAPTER-V19-20261116.md",
            spec_sha256=sha("planning/research/FTMO-FREE-TRIAL-ADAPTER-V19-20261116.md"),
            native_terminal_verified=False, automatic_broker_order_capability=False,
            broker_current_spec_or_news_verified=False),
        sources=read(JOB / "official-source-access.json"),
        official_public_recheck=read(JOB / "official-public-recheck-20261116.json"),
        MT5_primary_docs=dict(
            rows=[{k: r[k] for k in ("url", "path", "sha256", "status") if k in r}
                  for r in read(JOB / "MT5-primary-doc-review.json")["rows"]] +
                  [read(JOB / "MT5-copy-rates-range-primary.json")],
            raw_HTML_and_excerpts_retained_privately=True, native_runtime_not_exercised=True),
        unresolved_limits=[
            "No new source observations or market/feed certificates; 32 historical unknown trades remain.",
            "Previously exposed historical Validation; not clean OOS.",
            "Quarter bootstrap is conditional on recorded history and copied clocks, not calibrated future probability.",
            "Cost stress is a surcharge on fixed signal/SL/P1 paths; does not regenerate every widened-quote crossing.",
            "Same implementer/feed; separate oracle does not mean independent human review.",
            "Restricted first-passage estimates censor nonhits at 36 months; no finite unconditional expectation inferred.",
            "Optimal reset boundary requires retry fee/rules and identified future distribution; none is certified.",
            "Official public 2-Step rules rechecked; actual account specs/news and native FTMO fills remain unverified.",
            "2.2% guards are admission/observation policies, not guarantees against gaps/slippage.",
            "Storage measures readable logical snapshots, not physical freed space."],
        private_artifact_index=receipts)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if len(text.encode("utf-8")) > 1024 * 1024:
        raise ValueError("V19_bounded_results_exceed_1MiB")
    REPORT.with_suffix(".json").write_text(text, encoding="utf-8", newline="\n")
    write_report(result)
    event("V19_report_written", path=str(REPORT), bytes=len(text.encode("utf-8")))


def write_report(s):
    tests, smoke = s["engineering"]["tests"], s["engineering"]["smoke"]
    lines = ["# V19 — đi vốn, khoảng trống dữ liệu và adapter Free Trial", "",
        "**Chưa có nâng cấp CPPI hay “miễn nhiễm gap” đủ chứng cứ. Chưa mua Challenge.** "
        "Đã hoàn tất các phép đo, giữ cả kết quả âm; adapter chỉ đọc/shadow, chưa gửi lệnh broker.", "",
        "PR #97/head `014e1eb` đạt 3CI, merge `beaabdd`. V19 đăng ký `f2c7dd8`, "
        "khóa lựa chọn Dev/code `9aaaf29` trước kết quả V19 trên 2024–13/10/2026. "
        "Nhánh `codex/asymmetric-recovery-and-mt5-v19`; PR #98 để mở. "
        "Exact-head CI và downloaded test IDs được đối soát sau push bằng receipt private.", "",
        "## 1. Vì sao căn bậc hai không thắng?", "",
        "V16 đã giữ risk cơ sở đến −5% rồi mới giảm; không có bậc giảm cơ sở ở −1% đến −3,5%. "
        "Hàm cushion mũ 0,35/0,50 giảm chậm hơn hàm tuyến tính nhưng vẫn giảm risk ở vùng mà "
        "V16 chưa giảm. Nó là hàm lõm theo cushion, không phải bảo đảm lồi/bảo toàn vốn tuyệt đối. "
        "Lãi tích lũy cũng là equity có thể mất; hai lệnh thua không bảo đảm chỉ mất “tiền nhà”.", "",
        "Đăng ký tối đa sáu cấu hình. O2 bị loại ngay khi fit: trọng số mean-matched inverse-vol "
        "vượt [0,25;2] và tăng variance, không giải bài toán minimum variance toàn cục. "
        "Ba cấu hình đầu đi qua 1.752 sổ Dev/kiểm toán toàn bộ; hai O1 không cải thiện hai "
        "tiêu chí chính đã khóa. `BASE_GUARD` là bản đối chiếu tiếp, không được đổi tên thành "
        "một chiến lược CPPI thành công.", ""]
    lines += table(["Bản Dev", "Hai vòng — xấu nhất", "Thời gian quan sát TB tháng — xấu nhất", "Static %", "Daily %"], [
        [r["profile"]["name"], r["worst_completions"], fmt(r["slowest_restricted_months"]),
         fmt(r["worst_static"], 4), fmt(r["worst_daily"], 4)] for r in s["frozen"]["ranking"]])
    fit = s["Dev_fit"]["O2"]
    lines += ["", "Chỉ số thời gian Dev tính cả mốc chưa đạt bằng phần lịch sử còn quan sát được "
        "đến cuối 2023; mốc bắt đầu muộn có thời gian quan sát ngắn hơn. Chỉ dùng so cùng các "
        "mốc giữa profiles, không coi là thời gian kỳ vọng không bị kiểm duyệt.", "",
        f"O2: weights {fit.get('weights')}; unit-book variance "
        f"{fmt(fit.get('equal_variance'))} → {fmt(fit.get('weighted_variance'))}. "
        "Không nới cap hoặc chọn lại gamma sau Validation.", "",
        "Self-review phát hiện heuristic trên chưa giải đầy đủ objective minimum variance. "
        "Đã đăng ký [correction O2](V19-O2-CONSTRAINT-CORRECTION-20261116.md) ở `2d7bc94`, "
        "**sau khi baseline Validation đã exposed**, rồi chỉ fit lại trên Dev. Giữ cả bản sai/"
        "ineligible; không gọi correction là một thí nghiệm chưa từng thấy Validation.", ""]
    corrected = s["corrected_O2"]
    q = corrected["fit"]["fit"]
    lines += [f"Nghiệm covariance có ràng buộc: weights {q['weights']}; variance unit-book "
        f"{fmt(q['equal_variance'])} → **{fmt(q['weighted_variance'])}**, cùng sample mean. "
        "27 active sets là cách giải một bài toán tối ưu lồi ba biến, không phải 27 strategy trials. "
        "Đây chưa là mức giảm DD hoặc lợi nhuận thật sau lot grid/account policy.", "",
        f"Ba profile O2 sửa đúng objective đi qua thêm **{corrected['full_ledger_audits']} full Dev ledgers**. "
        "Theo gate đã đăng ký, cần thắng hai metric chính và không làm worst DD xấu hơn; nếu chỉ "
        "tốt ở variance/payout tie-break thì vẫn giữ incumbent.", ""]
    lines += table(["O2 Dev sau correction", "Hai vòng — xấu nhất", "Thời gian quan sát TB tháng", "Static %", "Daily %"], [
        [r["profile"]["name"], r["worst_completions"], fmt(r["slowest_restricted_months"]),
         fmt(r["worst_static"], 4), fmt(r["worst_daily"], 4)]
        for r in corrected["decision"]["ranking"]])
    lines += ["", f"O2 promotion gate: **{corrected['decision']['eligible_upgrade']}**; "
        f"giữ bản `{corrected['decision']['selected']['profile']['name']}`. "
        "Không thay profile dựa trên kết quả 2024–2026.", "",
        "Volatility drag ở đây là xấp xỉ `0,5 × variance` của **fractional daily account returns**, "
        "không phải 0,5 lần phương sai R rồi gọi là % vốn. "
        f"Daily unit-book drag Dev: {fmt(s['Dev_fit']['volatility_drag']['approximate_daily_log_drag'] * 100, 5)}%; "
        "đó chưa là mức giảm vốn thực tế của account engine.", "",
        "## 2. Các lệnh vướng giá thiếu và guard có tác dụng gì?", "",
        f"{s['gaps']['affected_trades']}/{s['gaps']['total_signals']} lệnh qua "
        f"{len(s['gaps']['rows'])} gap occurrences; 25 EURUSD/F5, 2 Gold/F3 và 5 Gold/F4. "
        "50 khoảng thiếu 1 phút, 3 khoảng thiếu 2 phút, 2 khoảng thiếu 3 phút. "
        "Đóng trong ngày tránh swap/cuối tuần, không tự sửa việc nguồn thiếu vài phút giữa ngày.", "",
        "Rà source D/E và các tick/M1/HTF exports đã có tìm được **0 quan sát mới trong gap**. "
        "Không bịa nến phẳng. M5/M15/H1 không tái tạo thứ tự chạm SL trong phút thiếu; "
        "proprietary/unproven archive formats vẫn chưa được chứng nhận.", "",
        "Guard 30 phút trước entry loại 0 tín hiệu; có 2 timeout requests trên Full. "
        "Thoát ở quote đầu tiên sau timeout, không bán hồi tố ở nến cuối trước mất feed. "
        "Vẫn còn 32 nhãn source-uncertain. Stress là giả định excursion bất lợi ở vùng chưa biết, "
        "không phải chứng minh thị trường thực đã chạm SL hay flat haircut tùy ý.", "",
        "## 3. Đối chiếu V16 với V19 trên 105 mốc lịch sử", "",
        "Bảng dưới lấy OLHC; JSON giữ cả OHLC và full oracle của **mọi sổ**. "
        "Median chỉ tính cửa sổ hoàn tất; 105 mốc chồng lấn không là 105 bài thi độc lập.", ""]
    lines += table(["Bản / dữ liệu / phí", "Vòng 1", "Hai vòng", "Recent hai vòng", "Median tháng", "Daily %", "Static %", "Funded riêng USD"], [
        [f"{r['version']}/{r['mode']}/{r['friction_pct']/100:g}×", r["phase1"], r["funded"],
         f"{r['recent_completions']}/{r['recent_starts']}",
         fmt(r["median_months"]), fmt(r["worst_daily"], 4), fmt(r["worst_static"], 4),
         fmt(r["standalone_payout"])] for r in s["historical"] if r["order"] == "OLHC"])
    lines += ["", "Sổ tham chiếu risk 150 USD/lệnh đo kinh tế tín hiệu; khác account sizing/admission/harvest. "
        "R không là % lợi nhuận tài khoản. 2026 kết thúc ngày 13/10, chưa đủ năm.", ""]
    lines += table(["Bản / dữ liệu / phí", "Net R tham chiếu", "Net USD tham chiếu"], [
        [f"{r['version']}/{r['source']}/{r['friction']/100:g}×", fmt(r["reference_net_R"]),
         fmt(r["reference_net_USD"])] for r in s["reference_economics"]])
    lines += ["", "Tăng phí được tính lại trên actual lot/cash/reserve. Paths SL/P1 giữ nguyên; "
        "không giả vờ đã tái tạo mọi first crossing khi spread giãn. "
        "Không có modeled breach không chứng minh rủi ro ngoài thị trường bằng 0.", "",
        "## 4. 5.000 chuỗi đường lệnh, không xáo PnL cuối ngày", "",
        "Cùng seed/draws V18, mọi sleeve trong quý đi cùng nhau, giữ ordered excursions và "
        "account state/clock xuyên seams. 36 tháng, báo prefix 12/18/24; "
        "cả hai ordering, 3 cost/source cases cho từng V16/V19. "
        "**120.000 sổ Monte Carlo đều qua native cash bridge và full independent ledger/path oracle**; "
        "không chỉ lấy mẫu. Oracle cùng tác giả và feed, không phải reviewer độc lập.", ""]
    lines += table(["Bản / dữ liệu / phí (OLHC)", "Hai vòng 12/18/24/36 %", "Median khi đậu, tháng", "Funded riêng: mean payout/năm USD"], [
        [f"{r['version']}/{r['mode']}/{r['friction']/100:g}×",
         "/".join(fmt(h["both_pct"]) for h in r["horizons"]), fmt(r["conditional_median_months"]),
         fmt(r["mean_annual_payout_USD"])] for r in s["monte"] if r["order"] == "OLHC"])
    lines += ["", "Cột payout dùng một sổ **đã Funded ngay từ đầu** chạy song song; không phải thu nhập "
        "sau thời gian thi. Tiền rút sau khi thực sự vượt hai vòng được đo riêng trong thí nghiệm "
        "state ở mục 5. Đây là tần suất resampling lịch sử đã exposed, không là xác suất tương lai đã "
        "hiệu chỉnh. Payout là mô phỏng, gồm cả các đường 0 USD và chưa trừ phí mua/retry/thuế/"
        "vận hành. **Payout thực nhận = 0; lệnh broker đã gửi = 0.**", "",
        "## 5. Bản đồ hồi vốn và chi phí cơ hội", "",
        "Từ −5% vốn, cần +5,26% trên equity hiện tại để về bờ, hoặc +300% của **đệm còn 5%** "
        "để đạt target vòng 1 +10%. Hai mẫu số này khác nhau. "
        "Bảng dùng 256 common Dev-only paths/state trong 36 tháng; không chọn lại policy. "
        "Mỗi state giả định đang flat ở vòng 1, chưa có ngày giao dịch hợp lệ trước đó và "
        "anchor ngày bằng balance giả định lúc bắt đầu. Không chỉ nhìn equity rồi suy đây là "
        "dự báo đầy đủ cho một account thật đang có vị thế/lỗ trong ngày. "
        "Nhóm không đạt vẫn giữ trong mẫu và chi phí thời gian hạn chế ở 36 tháng.", ""]
    lines += table(["V19 state %", "Buffer còn %", "ROI buffer tới +10% %", "Về bờ %", "Median về bờ nếu đạt", "Hai vòng %", "Median đậu nếu đạt", "Payout/tháng USD"], [
        [fmt(r["account_return_pct"], 0), fmt(r["remaining_buffer_pct"], 0),
         fmt(r["remaining_buffer_ROI_required_pct"]), fmt(r["recovery"]["hit_pct"]),
         fmt(r["recovery"]["conditional_median_months"]), fmt(r["funded"]["hit_pct"]),
         fmt(r["funded"]["conditional_median_months"]), fmt(r["post_funded_payout_per_elapsed_month_USD"])]
        for r in s["state_first_passage"]["rows"] if r["policy"] == "V19"])
    lines += ["", "Payout/tháng dùng tiền mô phỏng thực sự rút **sau khi qua hai vòng**, chia toàn bộ "
        "36 tháng và gồm zeros; không lấy thu nhập sổ Funded riêng gán cho tài khoản đang thi. "
        "Lượt đo bổ sung giữ nguyên mọi first-passage outcome và đối soát full ledger. "
        "JSON giữ bảng V16 bên cạnh, conditional mean, restricted mean và số không đạt.", "",
        "Drag tham chiếu dưới đây dùng cùng phương sai USD/ngày của unit book risk cố định "
        "150 USD, chia equity giả định từng state rồi lấy `0,5 × variance × 252`. "
        "Đây là phép đổi mẫu số để so quy mô; chưa đo drag của actual adaptive account tại từng "
        "state và không đưa các con số này vào chọn policy.", ""]
    lines += table(["State %", "Drag log/năm tham chiếu %"], [
        [fmt(r["account_return_pct"], 0),
         fmt(r["volatility_drag_reference"]["approximate_annual_log_drag"] * 100, 5)]
        for r in s["state_first_passage"]["rows"] if r["policy"] == "V19"])
    lines += ["",
        "**O3 chưa xác định được ngưỡng reset tối ưu.** Không suy thời gian kỳ vọng vô hạn từ "
        "median của nhóm thắng, không coi restricted mean là expected time thật. "
        "Phí retry/điều kiện reset chưa biết; nhận định mua lại giúp nhanh hơn chưa có cơ sở. "
        "Không reset tài khoản, bỏ chuỗi thua hoặc mua Challenge trong V19.", "",
        "## 6. Adapter, tốc độ và lưu trữ", "",
        "[Adapter/runbook](FTMO-FREE-TRIAL-ADAPTER-V19-20261116.md): READ_ONLY mặc định hoặc "
        "SHADOW_PAPER, demo binding, raw spec/spread, Prague reset, news/session/stale guards, "
        "native V16 signals và frozen V19 sizing, expected-vs-external-fill logger. "
        "CLI/file bridge/native-gateway giả lập và 6 full-seed signal prefixes đã kiểm. "
        "SDK chưa có trong runtime kiểm thử; chưa attach MT5 thật. Native shadow cần seed, "
        "spec/lịch tin được xác minh; chưa là EA hoặc broker parity acceptance.", "",
        f"Full suite: **{tests['tests']} PASS / 0 skip**, giữ đủ **1.153 V18 IDs**. "
        f"Wall **{fmt(tests['total_wall_seconds'], 3)} giây**, target <22s: "
        f"**{'đạt' if tests['target_under22'] else 'chưa đạt'}**. "
        "Bốn runtime groups chạy chồng có kiểm soát; không gọi là cùng workload nhanh hơn toàn máy.", "",
        f"Smoke cùng 78 IDs/assertions, 10 fresh processes và startup: **{smoke['below078']}/10 "
        f"dưới 0,78s**, max **{fmt(smoke['wall_max'], 3)}s**, median **{fmt(smoke['wall_median'], 3)}s**. "
        f"Target 10/10 dưới 0,78s: **{'đạt' if smoke['all_ten_below078'] else 'chưa đạt'}**. "
        "Giữ mọi outliers; không retry lấy chuỗi đẹp. Profile và paired diagnostics được giữ; "
        "không chứng minh chính xác nguyên nhân ba lần chậm lịch sử chỉ từ timing V18.", "",
        "Timing V18 cho thấy ba lần chậm hơn nhóm còn lại trung bình 80,2ms: 23,7ms ở import, "
        "40,6ms ở phần thân test và 15,2ms ngoài suite. Dữ liệu cũ không có GC/syscall trace "
        "để quy toàn bộ chênh lệch cho một module hoặc disk I/O. Không đổi metric sang internal "
        "suite time để bỏ chi phí khởi động Python.", "",
        "Tối ưu đã kiểm: bỏ thăm AST expression khi chỉ tìm ImportFrom (đối chiếu cùng các nested "
        "imports), bỏ sys.path trùng sau module loading; giữ oracle checking/fixture assertions. "
        "Hai worker smoke không thắng rõ nên không dùng. Oracle single-point bỏ NumPy array một "
        "phần tử sau 16 full-ledger parity checks; không bỏ quote/reset/exit clocks.", ""]
    lines += table(["Kho", "Hiện tại GiB", "Delta so V18 GiB", "Delta files", "Lỗi đọc"], [
        [root, fmt(r["current"]["bytes"] / 2**30), fmt(r["delta_since_V18"]["bytes"] / 2**30, 3),
         r["delta_since_V18"]["files"], len(r["errors"])]
        for root, r in s["engineering"]["storage"]["roots"].items()])
    growth = s["engineering"]["storage_growth_attribution"]
    lines += ["", f"Job V19 giữ **{fmt(growth['job_logical_bytes'] / 2**30, 3)}GiB / "
        f"{growth['job_files']} files**, chủ yếu JSON account/path packs và NPY quote arrays. "
        "Đây là evidence được giữ có chủ đích, gần toàn bộ mức tăng quan sát trên E. "
        "Không xóa dữ liệu mới hoặc chứng nhận toàn ổ không có rác. Snapshot logical/non-atomic "
        "không là physical freed bytes; hai lỗi đọc D thuộc VI Dubber và giữ nguyên.", "",
        "## 7. Chốt bước tiếp", "",
        "**Giữ research-only; chưa mua Challenge hoặc tự gửi lệnh Free Trial.** "
        "Ưu tiên thu dữ liệu đích có binding và kiểm continuity/spec/news cùng seed, rồi mới "
        "đánh giá execution gap. Không dùng sizing để biến nguồn thiếu hoặc alpha yếu thành đã qualified.", "",
        "Đã đọc lại được các trang FTMO công khai về 2-Step, daily/static loss, giữ lệnh và tin; "
        "giữ riêng receipt mới và các lần TLS timeout cũ. Client Area, specification/phí/lịch tin "
        "của account đích vẫn chưa xác minh. Free Trial 14 ngày có mục tiêu riêng; mô phỏng hai vòng "
        "trong báo cáo không là kết quả Free Trial. MQL5 SDK docs đã lưu HTML/hash; "
        "API documentation không thay runtime verification. "
        "Giữ VI WIP, Trader pin và mọi nguồn/freezes/failed attempts. PR #98 mở, không merge tự động.", "",
        f"JSON: [{REPORT.with_suffix('.json').name}]({REPORT.with_suffix('.json').name}). "
        f"Private job: `{JOB}`. `ci-exact-head-reconciliation.json` và `completion-receipt.json` "
        "được ghi sau 3 CI đúng HEAD/downloaded test IDs; không sửa HEAD chỉ để tự đóng dấu.", ""]
    REPORT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    collect()
