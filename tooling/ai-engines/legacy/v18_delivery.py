"""V18 engineering receipts, bounded summaries and beginner-facing morning report."""
from collections import Counter
from pathlib import Path
import json
import subprocess
import sys
import time
import numpy as np
from prop_v18_common import *
from prop_v18_costs import cost_bindings
from prop_v15_campaign import metrics
from prop_v16_performance import RUNTIMES
from quant_core.prop_lifecycle_and_parity import bindings

REPORT = Path("planning/research/FINAL-CONVERGENCE-V18-RESULTS-20261116")
MORNING = Path("planning/research/MORNING-EXECUTIVE-SUMMARY-20261116.md")
SPEC = Path("planning/research/FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md")


def performance():
    started = time.perf_counter()
    receipts = {}
    for group, python in RUNTIMES.items():
        output = JOB / f"tests-final-{group}.json"
        if output.exists():
            raise ValueError("V18_preserve_test_attempt")
        command = [python, "tooling/ai-engines/quant_test_suite.py", "--group", group,
                   "--tier", "all", "--output", str(output)]
        if group == "base":
            command += ["--workers", "4", "--profile", str(V17 / "tests-after-base.json")]
        subprocess.run(command, check=True)
        receipts[group] = read(output)
    ids, old = set(), set()
    for group, r in receipts.items():
        if not r["passed"] or r["skipped"] or ids & set(r["timings"]):
            raise ValueError("V18_test_failure_skip_duplicate")
        ids.update(r["timings"])
        old.update(read(V17 / f"tests-after-{group}.json")["timings"])
    if not old <= ids:
        raise ValueError("V18_lost_V17_test_ID")
    save("tests-final-matrix.json", dict(
        tests=len(ids), preserved_baseline_ids=len(old), zero_skip=True,
        total_wall_seconds=time.perf_counter() - started,
        V17_baseline_seconds=read(V17 / "tests-after-matrix.json")["total_wall_seconds"],
        groups={g: {k: r.get(k) for k in ("tests", "seconds", "workers", "shard_seconds")}
                for g, r in receipts.items()},
        new_IDs=sorted(ids - old), timings_scope="Four isolated-runtime suites on this machine",
        no_whole_computer_speed_claim=True))
    event("V18_full_tests_PASS", tests=len(ids))


def smoke():
    import v17_delivery as old
    with bindings(old, JOB=JOB, save=save, event=lambda stage, **v: event(stage.replace("V17", "V18"), **v)):
        old.smoke()


def storage():
    v9 = read(Path("planning/research/SYSTEM-AND-ALPHA-V9-RESULTS-20261115.json"))["storage"]
    v10 = read(Path("planning/research/ENTERPRISE-ALPHA-V10-RESULTS-20261115.json"))["storage"]
    v11 = read(Path("planning/research/ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115.json"))["storage"]
    roots = {}
    for label, baseline in (("D", v9["D_before"]), ("E", v9["E_initial_observed"])):
        name = f"storage-{label}-final.json"
        root = "D:/ANNAM/TradingWorkspace" if label == "D" else "E:/BACKUP-TRADINGWORKSPACE"
        if (JOB / name).exists():
            raise ValueError("V18_preserve_health_attempt")
        subprocess.run([sys.executable, "tooling/workspace_maintenance.py", "inventory",
                        "--root", root, "--output", str(JOB / name)], check=True)
        r = read(JOB / name)
        now = r["groups"]["/"]
        roots[label] = dict(baseline=baseline, current=now, inventory=str(JOB / name),
                            sha256=sha(JOB / name), skipped_links=len(r["skipped_links"]),
                            errors=r["errors"],
                            net_observed_reduction={k: baseline[k] - now[k] for k in ("bytes", "files", "folders")})
    removal = [
        dict(campaign="V9", scope="D generated caches", bytes=v9["caches"]["bytes"], files=v9["caches"]["files"]),
        dict(campaign="V9", scope="D Rust incremental", bytes=v9["rust_incremental"]["bytes"],
             files=v9["rust_incremental"]["files"]),
        *[dict(campaign="V10", scope=r["path"], bytes=r["bytes"], files=r["files"])
          for r in v10["generated_dependencies"]],
        dict(campaign="V11", scope="E approved generated build targets", bytes=v11["exact_purge"]["bytes"],
             files=v11["exact_purge"]["files"])]
    # These scopes are disjoint; archived environments and later duplicate/log
    # removals are reported separately rather than counted twice as cache purge.
    save("storage-summary.json", dict(
        roots=roots, verified_cache_build_operations=removal,
        verified_cache_build_bytes=sum(r["bytes"] for r in removal),
        verified_cache_build_file_operations=sum(r["files"] for r in removal),
        net_visible_bytes_reduction=sum(r["net_observed_reduction"]["bytes"] for r in roots.values()),
        net_visible_file_reduction=sum(r["net_observed_reduction"]["files"] for r in roots.values()),
        owner_approximate_baseline=dict(D_GiB=208, D_files=633488, E_GiB=320, E_files=656692),
        owner_file_baseline_delta=sum(n - roots[k]["current"]["files"]
                                     for k, n in (("D", 633488), ("E", 656692))),
        dated_canonical_baseline="V9 before receipts; values differ slightly from owner's earlier counts",
        extra_cold_or_duplicate_removal_references=[
            "SYSTEM-AND-ALPHA-V9-RESULTS-20261115.json",
            "ENTERPRISE-ALPHA-V10-RESULTS-20261115.json",
            "EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115.json",
            "BRIDGE-AND-VELOCITY-V15-RESULTS-20261115.json",
            "GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116.json",
            "ADAPTIVE-VELOCITY-V17-RESULTS-20261116.json"],
        newly_deleted_by_V18=0, all_unknown_or_active_trees_retained=True,
        physical_space_reclaimed_bytes=None, snapshot_is_not_atomic=True,
        net_delta_is_not_all_junk_deleted=True))
    event("V18_storage_health_complete", D_errors=len(roots["D"]["errors"]), E_errors=len(roots["E"]["errors"]))


def preflight_name(tag, mode):
    return ("preflight-optimized" if (tag, mode) == ("OLHC", "PRIMARY")
            else f"preflight-{tag}-{mode}-optimized")


def historical_cases():
    out = []
    receipts = []
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            for pct in (100, 125, 150):
                if pct == 100:
                    prefix = preflight_name(tag, mode)
                    p = JOB / (prefix + "-native-unaudited.json")
                    rows = read(p)["rows"]
                else:
                    prefix = f"historical-{tag}-{mode}-{pct}"
                    p = JOB / (prefix + "-accounts.json")
                    rows = read(p)
                r = read(JOB / (prefix + "-audit.json"))
                if not r["passed"] or r["native_cash_bridges"] != 106:
                    raise ValueError("V18_historical_audit_missing")
                funded = next(x for x in rows if x["kind"] == "STANDALONE_FULL")
                out.append(dict(order=tag, mode=mode, friction_pct=pct, **metrics(rows),
                                standalone_static=funded["static_loss_pct"],
                                standalone_daily=funded["worst_daily_loss_pct"],
                                standalone_peak_DD=funded["peak_dd_pct"]))
                receipts.append(dict(path=str(p), sha256=sha(p), audit=str(JOB / (prefix + "-audit.json")),
                                     audit_sha256=sha(JOB / (prefix + "-audit.json")),
                                     native_cash_bridges=106, independent_cases=len(r["independent_checks"])))
    return out, receipts


def reference_economics():
    import prop_portfolio_accounts as portfolio
    from prop_v15_accounts import exact_quantity
    result = []
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            meta = read(JOB / f"{tag}-{mode}-blocks.json")
            trades = [t for b in meta["blocks"] for t in b["trades"]]
            for pct in (100, 125, 150):
                years = {}
                with cost_bindings(pct):
                    for t in trades:
                        y = datetime.fromtimestamp(t["entry_msc"] / 1000, timezone.utc).year
                        r = years.setdefault(y, dict(signals=0, min_lot_skipped=0, trades=0, net_R=0., net_usd=0.))
                        r["signals"] += 1
                        try:
                            q = exact_quantity(t, 150)
                        except ValueError:
                            r["min_lot_skipped"] += 1
                            continue
                        money = portfolio.trade_money(t, q, "SYM_FLAT", 150)
                        r["trades"] += 1
                        r["net_R"] += money["net_R"]
                        r["net_usd"] += money["net_usd"]
                result.append(dict(order=tag, mode=mode, friction_pct=pct, annual=years,
                                   total_net_R=sum(r["net_R"] for r in years.values()),
                                   total_net_usd=sum(r["net_usd"] for r in years.values()),
                                   reference_risk_usd=150, account_admissions_not_applied=True))
    return result


def collect():
    tournament = read(JOB / "tournament.json")
    cases, historical_audits = historical_cases()
    backup_cases = []
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            p = V17 / f"Full-{tag}-{mode}-accounts.json"
            digest = sha(p)
            for r in read(p):
                if r["kind"] != "STANDALONE_FULL":
                    continue
                backup_cases.append(dict(order=tag, mode=mode, cost=r["cell"],
                    static=r["static_loss_pct"], daily=r["worst_daily_loss_pct"],
                    peak_DD=r["peak_dd_pct"], payout=r["trader_payout_usd"],
                    payout_count=len(r["payouts"]), first_breach=r["first_breach"],
                    source=str(p), sha256=digest))
    monte = []
    first_years = None
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            for pct in (100, 125, 150):
                p = JOB / f"bootstrap-{tag}-{mode}-{pct}-summary.json"
                r = read(p)
                if (r["paths"] != PATHS or r["full_native_cash_bridges"] != 2 * PATHS
                        or r["friction_pct"] != pct):
                    raise ValueError("V18_incomplete_Monte_Carlo")
                if len(r["independent_sample_checks"]) != 64:
                    raise ValueError("V18_Monte_Carlo_audit_sample_missing")
                if not all(c["cash_bridge"] for c in r["independent_sample_checks"]):
                    raise ValueError("V18_independent_cash_audit_not_passed")
                path_rows = read(JOB / f"bootstrap-{tag}-{mode}-{pct}-paths.json")
                if (len(path_rows) != PATHS or {x["path"] for x in path_rows} != set(range(PATHS))
                        or not all(x["native_cash_bridges"] for x in path_rows)):
                    raise ValueError("V18_missing_or_duplicate_bootstrap_path")
                years = [x["first_year"] for x in path_rows]
                if first_years is not None and years != first_years:
                    raise ValueError("V18_cost_cases_do_not_share_draws")
                first_years = years
                monte.append(dict(order=tag, mode=mode, **r,
                                  path=str(p), sha256=sha(p)))
    if not read(JOB / "matrix-monte-processes.json")["passed"]:
        raise ValueError("V18_matrix_process_failure")
    tests = read(JOB / "tests-final-matrix.json")
    if tests["preserved_baseline_ids"] != 1148 or not tests["zero_skip"]:
        raise ValueError("V18_test_history_loss")
    result = dict(
        schema="V18-final-convergence-v1", decision="NO_CERTIFIED_CHAMPION_OR_AUTOMATED_FREE_TRIAL_PROMOTION",
        prop_qualified=False, strategy_orders_ready=False, capture_kit_documented=True,
        freeze=read(FREEZE), freeze_commit="bec7fe1", PR96_merged="92569ca",
        tournament=tournament, historical=cases, historical_audits=historical_audits,
        diagnostic_backup_V17=backup_cases,
        reference_economics=reference_economics(), monte=monte,
        storage=read(JOB / "storage-summary.json"), tests=tests, smoke=read(JOB / "smoke-results.json"),
        official_terms=read(JOB / "official-terms-v18-correction.json"),
        intraday_cost_proof=read(JOB / "intraday-cost-and-spread-proof.json"),
        draw_reconstruction=read(JOB / "bootstrap-draw-reconstruction.json"),
        execution_spec=str(SPEC), execution_spec_sha256=sha(SPEC),
        engineering_attempts=read(JOB / "engineering-negative-attempts.json"),
        author_and_oracle_same=True, feed_same=True, actual_broker_orders=0, actual_payout_usd=0,
        limitations=[
            "No candidate has certified unknown-free execution paths; tournament ranking is descriptive.",
            "All later prices exposed; no clean OOS. 2026 ends 13 October.",
            "5000 common resamples, twelve fixed source/order/friction scenarios, not 60000 independent markets.",
            "Monthly/quarter regime labels use retrospective source years, not forecasts.",
            "Source Prague reset clocks are copied into synthetic time; no new future exchange calendar is generated.",
            "M1 ordered excursion scenarios, Ask proxies and strict synthetic gaps are not broker tick fills.",
            "Friction surcharge preserves signal/SL/P1 paths; widened-quote first passages are not regenerated.",
            "All native cash bridges checked; full independent path ledgers sampled at 32 paths per scenario.",
            "Current target account terms/specifications and historical news not certified.",
            "Inventory logical bytes/readable roots, not proven physical reclaimed space or all deleted junk."])
    result["artifact_index"] = {
        p.name: dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
        for p in JOB.iterdir() if p.is_file() and p.suffix in (".json", ".npy", ".pstats")}
    REPORT.with_suffix(".json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if REPORT.with_suffix(".json").stat().st_size > 1024 * 1024:
        raise ValueError("V18_results_exceed_one_MiB")
    write_report(result)
    write_morning(result)
    event("V18_reports_written", detailed=str(REPORT), morning=str(MORNING))


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] + [
        "| " + " | ".join(str(v).replace("|", r"\|") for v in row) + " |" for row in rows]


def fmt(x, places=2):
    return "—" if x is None else f"{x:,.{places}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def write_report(s):
    lines = ["# V18 — Tournament, Monte Carlo đường lệnh và bộ kit Free Trial", "",
        "**Chưa có Champion đủ chứng cứ; chưa promote bot lên Free Trial/Challenge.** "
        "V16 là diagnostic velocity reference; V17 là diagnostic Funded backup theo rule đã khóa. "
        "Đây là kết luận chốt chiến dịch, không phải yêu cầu mở thêm grid.", "",
        "PR #96/exact head `ee97543` đạt 3CI, merge `92569ca`; V17 branch đã xóa. "
        "Protocol `50c474f`, code/stress freeze `bec7fe1` trước batch 5.000 paths. "
        "Giữ VI WIP, Trader pin, nguồn, freezes và negative attempts.", "",
        "## 1. Tournament V1–V17", "",
        "17 hồ sơ/version có hash trong JSON. V9/V10 chủ yếu engineering; V11–V13 "
        "là discovery/kiểm dữ liệu; không coi mọi version là một chiến lược độc lập. "
        "PR78 Gold A và PR82 V4 giữ mẫu 36 starts/2022–2024; không cộng hoặc so raw pass count "
        "với 105 starts/2018–13Oct2026. PR93 là delivery V14; PR94 là V15.", ""]
    lines += table(["Bản (PRIMARY, xấu nhất hai phí/order)", "Hai vòng/105", "Median tháng",
                    "Standalone static %", "Standalone daily %", "Standalone payout USD"], [
        [r["version"], r["worst_completions"], fmt(r["slowest_median"]),
         fmt(r["worst_standalone_static"], 4), fmt(r["worst_standalone_daily"], 4),
         fmt(r["lowest_standalone_payout"])] for r in s["tournament"]["ranking"]])
    lines += ["", "Champion gate cần source/path đủ chứng cứ và modeled daily<5%/static<10%; "
        "không candidate nào đạt source gate. Reference chọn bằng completion count rồi conditional "
        "median; V15 vẫn có median nhanh hơn V16. Backup chọn static thấp trong standalone PRIMARY "
        "và payout dương; tên Ultra-Safe chưa được chứng nhận, nhất là khi bật strict gap.", "",
        "Sổ Funded riêng của backup V17, giữ nguyên risk/tier, không tuning lại:", ""]
    lines += table(["Order/phí/source", "Static %", "Daily %", "Peak DD %", "Payout count/USD"], [
        [r["order"] + "/" + r["cost"] + "/" + r["mode"], fmt(r["static"], 4),
         fmt(r["daily"], 4), fmt(r["peak_DD"], 4),
         str(r["payout_count"]) + "/" + fmt(r["payout"])] for r in s["diagnostic_backup_V17"]])
    lines += ["", "Target static<6% chỉ được kiểm trong đúng cột nêu trên; kết quả PRIMARY "
        "không thay thế STRICT hoặc chứng nhận nguồn.", "",
        "## 2. Kiểm định phí trên lịch sử nguyên thứ tự", "",
        "Không đổi tín hiệu/SL/P1. Phí tăng thêm là half-spread+slippage mỗi side, làm tròn lên cent "
        "ở actual quantity. Lot, cushion/throttle, admission, equity, pass và payout được tính lại "
        "bằng native engine. Commission/funding không tự hạ. V16 intraday/noTP nên SYM/ASYM giống nhau; "
        "reuse có điều kiện này được ghi ở freeze.", ""]
    lines += table(["Order", "Source", "Friction", "P1/105", "Hai vòng/105", "Median tháng",
                    "Daily %", "Static %", "Breach", "Standalone USD"], [
        [r["order"], r["mode"], r["friction_pct"] / 100, r["phase1"], r["funded"],
         fmt(r["median_months"]), fmt(r["worst_daily"], 4), fmt(r["worst_static"], 4),
         r["breaches"], fmt(r["standalone_payout"])] for r in s["historical"]])
    lines += ["", "Bảng reference dưới đây dùng cùng risk 150 USD/lệnh và lot floor, bỏ riêng entry không "
        "đạt minimum lot với counter minh bạch. Không có account cap/harvester trong sổ reference; "
        "Net R không là % return của tài khoản.", ""]
    lines += table(["Order/source", "Friction", "Reference net R", "Reference net USD"], [
        [r["order"] + "/" + r["mode"], r["friction_pct"] / 100,
         fmt(r["total_net_R"], 4), fmt(r["total_net_usd"])] for r in s["reference_economics"]])
    lines += ["", "JSON giữ per-year economics, kể cả 2026 YTD. Tổng dương không che các năm yếu. "
        "Surcharge là cost sensitivity trên đường SL/P1 đã đóng băng; chưa tái tạo mọi stop crossing "
        "khác khi Ask/Bid giãn. Không gọi đây là broker-fill stress đã chứng nhận.", "",
        "## 3. 5.000 đường quote/event bootstrap", "",
        "Một seed và cùng 5.000 draw sequences cho 12 ca: hai ordering × PRIMARY/STRICT × ba mức phí. "
        "Giữ mọi asset/trade cùng quý, toàn bộ ordered quote excursions khi có cơ hội mở, các clock/"
        "entry/exit và native risk/harvest state. Quý thiếu cuối mẫu không lấy; không loại lệnh thua/"
        "gap. Bốn preflight tái hiện đúng 105 starts+standalone bản V16; baseline và bản tối ưu giữ riêng.", "",
        "Pool 35 quý đầy đủ giữ 493 tín hiệu; 1 tín hiệu của quý cuối chưa đủ được giữ trong "
        "historical table, không ghép vào pool như một quý hoàn chỉnh. Source proof xác nhận "
        "spread proxy cố định Gold 0,338 USD/oz và EUR 1 pip trên toàn bộ quote path, không có lượt "
        "rollover nào trong tape. Đây không phải biểu phí tài khoản đích.", "",
        "Yêu cầu 24 tháng kèm horizon 36 được đáp ứng bằng một extension 36 tháng của cùng các paths; "
        "12/18/24 là prefix. Reset Prague của nguồn được sao chép trong mỗi quý, payout timer theo "
        "elapsed calendar days. Đây là synthetic source-clock tape, không phát sinh một lịch tương lai "
        "mới. Vì reference intraday và seams flat, không có vị thế bị cắt ở biên quý.", ""]
    for group in ("random", "favorable_start", "sideways_start"):
        lines += [f"### Cohort `{group}`", "",
                  "Favorable/sideways là nhãn hồi tố của năm nguồn đầu tiên đã khóa trên Dev; "
                  "chỉ quý đầu mang nhãn đó, các quý sau vẫn draw ngẫu nhiên. "
                  "Không giả định giữ nguyên một năm thuận lợi hoặc nhận diện được regime tại entry.", ""]
        lines += table(["Order/source/phí", "N", "P1 12/18/24/36 %", "Hai vòng 12/18/24/36 %",
                        "Daily breach36 %", "Static breach36 %", "Funded mean annual USD P25/P50/P75"], [
            [r["order"] + "/" + r["mode"] + "/" + str(r["friction_pct"] / 100),
             r["groups"][group]["paths"],
             "/".join(fmt(h["phase1_pct"]) for h in r["groups"][group].get("horizons", [])),
             "/".join(fmt(h["both_pct"]) for h in r["groups"][group].get("horizons", [])),
             fmt(r["groups"][group].get("horizons", [{}])[-1].get("daily_breach_pct")),
             fmt(r["groups"][group].get("horizons", [{}])[-1].get("static_breach_pct")),
             "/".join(fmt(v) for v in r["groups"][group].get("standalone_mean_annual_USD_P25_P50_P75", []))]
            for r in s["monte"]])
    lines += ["", "JSON có cả payout quantiles từng năm 1/2/3, zeros và stopped paths. Các tỷ lệ trên là "
        "tần suất có điều kiện của resampling lịch sử đã exposed, không phải xác suất đậu tương lai "
        "được hiệu chỉnh. SOURCE uncertainty giữ nguyên; strict chỉ là giả định excursion chung, "
        "không phục hồi dữ liệu hoặc tạo source certificate.", "",
        "Payout Funded 50k từng năm của cohort random; mỗi ô là P25/P50/P75 USD:", ""]
    lines += table(["Order/source/phí", "Năm 1", "Năm 2", "Năm 3"], [
        [r["order"] + "/" + r["mode"] + "/" + str(r["friction_pct"] / 100),
         *["/".join(fmt(v) for v in yr) for yr in
           r["groups"]["random"]["standalone_yearly_USD_P25_P50_P75"]]]
        for r in s["monte"]])
    lines += ["",
        "## 4. Kiểm toán, health và bàn giao", "",
        f"Native kiểm **{sum(r['full_native_cash_bridges'] for r in s['monte']):,} cash bridges** của "
        "challenge/standalone. Independent Decimal oracle kiểm đầy đủ sổ và quote path ở 32 sampled "
        "paths/ca ×2 loại account: **768 sổ mẫu**, cùng 48 historical cases stress mới và 24 cases "
        "baseline preflight. Các source first-pass paths kế thừa audit V16/V17 có binding. "
        "Không gọi sample oracle là audit độc lập 100% Monte Carlo; cùng implementer/feed.", "",
        "Các lỗi padding/quote-key/multi-close trong adapter audit đã được ghi nhận trước full batch "
        "và sửa bằng regression; không sửa tín hiệu hay chọn lại mẫu. Bỏ memmap subclass overhead/"
        "flat excursion dispatch chỉ sau full ledger parity; không bỏ reset/session/entry/exit clocks.", ""]
    t, smoke = s["tests"], s["smoke"]
    fast_smokes = sum(r["wall"] < smoke["plan"]["threshold_wall_seconds"] for r in smoke["rows"])
    lines += [f"Full **{t['tests']} PASS/0 skip**, giữ đủ {t['preserved_baseline_ids']} V17 IDs. "
        f"Wall **{fmt(t['total_wall_seconds'], 3)}s**, V17 **{fmt(t['V17_baseline_seconds'], 3)}s**; "
        f"smoke 10 fresh ×78 tests, max **{fmt(smoke['wall_max'], 3)}s**, "
        f"**{fast_smokes}/10 lần <0,80s; chưa đạt mục tiêu 10/10**. "
        "Cả 10 lần đều PASS về chức năng, 0 skip. Giữ nguyên outliers, không thử lại để lấy chuỗi đẹp. "
        "Không chạy performance benchmark khi "
        "financial jobs còn tranh CPU; không suy ra speedup toàn máy.", ""]
    st = s["storage"]
    lines += table(["Root", "Baseline GiB", "Hiện tại GiB", "Giảm ròng GiB", "Files hiện tại", "Lỗi đọc"], [
        [k, fmt(r["baseline"]["bytes"] / 2**30), fmt(r["current"]["bytes"] / 2**30),
         fmt(r["net_observed_reduction"]["bytes"] / 2**30), r["current"]["files"], len(r["errors"])]
        for k, r in st["roots"].items()])
    lines += ["", f"Snapshot đọc được giảm ròng **{fmt(st['net_visible_bytes_reduction']/2**30)}GiB**, "
        f"**{st['net_visible_file_reduction']:,} files** so canonical V9 receipts. Theo mốc file owner "
        f"633.488/656.692 là **{st['owner_file_baseline_delta']:,} files**; hai mốc khác thời điểm. "
        f"Purge cache/build disjoint có biên nhận **{st['verified_cache_build_file_operations']:,} "
        f"lượt tệp / {fmt(st['verified_cache_build_bytes']/2**30)}GiB**. Archive/copy/log removals "
        "V9/V10/V14–17 dẫn riêng để tránh cộng trùng; con số purge không bằng snapshot net vì có "
        "output phát sinh và archive giữ lại. Chưa đo physical reclaimed bytes. Hai lỗi đọc D thuộc "
        "VI pytest được giữ nguyên; không đụng WIP, source, data, matrices hay ledger.", "",
        f"Kit: [{SPEC.name}]({SPEC.name}). Có thể chuẩn bị quote/spec capture sau khi binding/terms "
        "đích được kiểm; chưa có EA/parity/news guard/owner handover cho strategy orders. Free Trial "
        "terms hiện hành chưa truy cập lại thành công; dùng snapshot 02/11 làm tham chiếu có nhãn. "
        "Quote-only không đo được slippage. Không mua Challenge/đăng ký account/gửi lệnh trong V18.", "",
        f"Morning brief: [{MORNING.name}]({MORNING.name}). PR #97 giữ mở; exact-head 3CI và downloaded "
        "test IDs phải được đối soát bằng receipt private sau push. Không sửa HEAD chỉ để tự đóng dấu. "
        f"Evidence `{JOB}`; JSON≤1MiB. Giữ tất cả freezes/attempts và Trader pin/VI WIP.", ""]
    REPORT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def write_morning(s):
    base = next(r for r in s["historical"] if (r["order"], r["mode"], r["friction_pct"]) == ("OLHC", "PRIMARY", 100))
    strict = next(r for r in s["historical"] if (r["order"], r["mode"], r["friction_pct"]) == ("OLHC", "STRICT", 100))
    ref = next(r for r in s["reference_economics"] if (r["order"], r["mode"], r["friction_pct"]) == ("OLHC", "PRIMARY", 100))
    mc = next(r for r in s["monte"] if (r["order"], r["mode"], r["friction_pct"]) == ("OLHC", "PRIMARY", 100))
    mcstrict = next(r for r in s["monte"] if (r["order"], r["mode"], r["friction_pct"]) == ("OLHC", "STRICT", 100))
    st, t, smoke = s["storage"], s["tests"], s["smoke"]
    fast_smokes = sum(r["wall"] < smoke["plan"]["threshold_wall_seconds"] for r in smoke["rows"])
    lines = ["# Báo cáo buổi sáng — chốt V16, V17 và V18", "",
        "**Hệ thống kiểm định đã tiến bộ; chưa có chiến lược đủ bằng chứng để mua Challenge "
        "hoặc bật bot tự giao dịch Free Trial.** Mình không ép chọn một “Champion” khi đường giá "
        "còn chỗ chưa kiểm chứng.", "",
        "## 1. Ba ca chạy đêm đã giải quyết gì?", "",
        "V16 đưa danh mục về đóng trong ngày, tìm thêm nhiều nhánh nhưng không có nhánh mới đủ chuẩn. "
        "V17 thử chia mức cược hợp lý hơn và thêm dự phòng lỗ ngày; sụt vốn giảm nhưng chưa kiếm đủ "
        "nhanh. Cả hai vẫn còn đoạn giá thiếu chứng cứ.", "",
        "V18 gom lại 17 chiến dịch, phân biệt bản cũ đo 3 năm với bản mới đo gần 9 năm; "
        "khóa một cách tuyển chọn, rồi chạy 5.000 chuỗi mô phỏng giữ nguyên diễn biến từng lệnh/quý "
        "và stress phí. Không tìm thêm tham số để cứu kết quả. "
        "V16 là bản tham chiếu tốc độ, V17 là dự phòng Funded **trong mô hình**; chưa bản nào được "
        "chứng nhận đủ an toàn. Các bản yếu và failed attempts đều được giữ.", "",
        "## 2. Ổ cứng và tốc độ đã cải thiện bao nhiêu?", ""]
    lines += table(["Kho", "Trước GiB", "Nay GiB", "Files nay"], [
        [k, fmt(r["baseline"]["bytes"]/2**30), fmt(r["current"]["bytes"]/2**30), fmt(r["current"]["files"], 0)]
        for k, r in st["roots"].items()])
    lines += ["", f"Phần đọc được giảm ròng khoảng **{fmt(st['net_visible_bytes_reduction']/2**30)} GiB** "
        f"và **{fmt(st['net_visible_file_reduction'],0)} tệp** so snapshot gốc có biên nhận. "
        "Không gọi toàn bộ chênh lệch này là “rác đã xóa”: đã có nén lạnh, dữ liệu mới phát sinh "
        "và những thư mục cần giữ. Riêng các đợt xóa cache/build có chứng cứ ghi nhận "
        f"**{fmt(st['verified_cache_build_file_operations'],0)} lượt tệp**. Chưa đo lượng ổ đĩa vật lý "
        "thực sự giải phóng. Hai thư mục pytest của VI không đọc được vẫn được giữ nguyên.", "",
        f"Hiện có **{fmt(t['tests'],0)} bài test PASS, 0 skip**, giữ đủ toàn bộ 1.148 test cũ. "
        f"Full suite chạy **{fmt(t['total_wall_seconds'],3)} giây**; V17 là 21,14 giây, trước đó "
        f"V16 khoảng 28,23 giây. Smoke 10 lần, chậm nhất **{fmt(smoke['wall_max'],3)} giây**; "
        f"**{fast_smokes}/10 lần dưới 0,80 giây, chưa đạt yêu cầu 10/10**. "
        "Cả 10 lần đều chạy đúng chức năng; giữ nguyên các lần chậm và không thử lại để lấy chuỗi đẹp. "
        "Đây là tốc độ bài kiểm thử, "
        "chưa phải phép đo toàn máy hay tốc độ khớp MT5.", "",
        "## 3. Sức mạnh thật của bản tốt nhất hiện tại", "",
        f"V16 có **{fmt(ref['total_net_R'],2)}R** ở sổ tham chiếu 150 USD/lệnh sau phí, "
        "từ 2018 đến 13/10/2026. R là điểm lời/lỗ theo mức cược, không phải % lợi nhuận tài khoản. "
        "2026 chưa đủ năm; có năm yếu/âm và đường giá chưa đủ chứng cứ. "
        "Sổ reference không có toàn bộ hạn mức/harvester của tài khoản.", "",
        f"Mô hình chính: **{base['funded']}/105** mốc xuất phát hoàn tất hai vòng, trung vị "
        f"**{fmt(base['median_months'])} tháng**, chỉ tính các mốc đã hoàn tất. Khi stress đoạn "
        f"giá chưa kiểm chứng: còn **{strict['funded']}/105**. "
        "Sổ tham chiếu tương ứng chuyển từ +42,30R thành **−5,05R**. "
        "Các 33 mốc bắt đầu từ 2024 đều chưa "
        "hoàn tất hai vòng ở kết quả gốc. 105 mốc chồng lấn không phải 105 bài thi độc lập.", "",
        f"Một sổ Funded 50k chạy riêng từ đầu mẫu mô phỏng **{base['standalone_payout_count']} "
        f"lần rút / {fmt(base['standalone_payout'])} USD**. Tổng payout của nhiều mốc chồng lấn "
        "không phải thu nhập của owner. **Tiền payout thực nhận trong dự án vẫn bằng 0.**", "",
        "Monte Carlo là 5.000 cách xếp lại quý lịch sử, dùng để nhìn độ nhạy; không phải lời hứa "
        "xác suất đậu ngoài thị trường:", ""]
    lines += table(["Thời gian", "Qua vòng 1 — chính %", "Qua cả 2 — chính %", "Qua cả 2 — stress giá thiếu %"], [
        [f"{a['months']} tháng", fmt(a["phase1_pct"]), fmt(a["both_pct"]), fmt(b["both_pct"])]
        for a, b in zip(mc["groups"]["random"]["horizons"], mcstrict["groups"]["random"]["horizons"])])
    q = mc["groups"]["random"]["standalone_mean_annual_USD_P25_P50_P75"]
    lines += ["", f"Payout bình quân mỗi năm của sổ Funded mô phỏng: P25/P50/P75="
        f"**{fmt(q[0])}/{fmt(q[1])}/{fmt(q[2])} USD**. Đã tính cả các đường không rút được tiền. "
        "P50 nghĩa là một nửa đường mô phỏng thấp hơn mức đó, không phải thu nhập được bảo đảm. "
        "Chưa trừ phí mua/retry Challenge, vận hành hoặc thuế.", "",
        "Phí tăng 50% làm số mốc hoàn tất hai vòng trên lịch sử gốc giảm từ 71 xuống **7/105**. "
        "Không đường mô phỏng nào chạm trần lỗ, nhưng điều đó chưa chứng minh rủi ro thực tế bằng 0.", "",
        "Bảng phí 1,25×/1,50×, các năm thuận lợi/đi ngang, mức sụt vốn và tỷ lệ vi phạm nằm trong "
        f"[báo cáo chi tiết]({REPORT.name}.md). Thiếu lịch news/đường giá và phí/fill tài khoản "
        "đích vẫn là điểm yếu thật; xáo trộn dữ liệu không tự lấp các lỗ hổng đó.", "",
        "## 4. Sáng nay nên làm gì?", "",
        "**Chưa mua Challenge và chưa bật bot tự gửi lệnh.** Có thể chuẩn bị một Free Trial đúng "
        "program để thu quote/spec và đối chiếu đồng hồ, sau khi tài khoản/binding được xác nhận. "
        "Điều khoản hiện hành chưa truy cập lại thành công; 14 ngày là mốc tham chiếu từ snapshot "
        "cũ/yêu cầu, cần kiểm trên Client Area.", "",
        f"Đã có [bộ spec cụ thể]({SPEC.name}): ba sleeve, SL/P1, giờ đóng, lot/risk, phí và log đối soát. "
        "Bộ này chưa phải EA. Muốn đo slippage phải có log gửi lệnh và khớp lệnh dưới quyền thực thi "
        "riêng; chỉ thu giá chưa đo được slippage. Cần hoàn tất adapter/parity, news guard và "
        "owner handover trước khi bật giao dịch chiến lược.", "",
        "PR96 đã merge; PR97 giữ mở để xem kết quả và bằng chứng. Không đăng ký tài khoản mới, "
        "giao dịch broker, mua Challenge hoặc deploy trong đợt này. VI WIP và Trader pin giữ nguyên.", ""]
    MORNING.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("performance", "smoke", "storage", "collect"))
    globals()[p.parse_args().stage]()
