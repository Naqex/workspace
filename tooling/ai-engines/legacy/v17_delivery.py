"""V17 engineering receipts and reporting; never selects financial parameters."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import json
import os
import subprocess
import sys
import time
import zipfile

from prop_v17_common import JOB, V15, V16, ROOT, FREEZE, DEV_END, read, sha, save, event
from prop_v15_campaign import metrics
from prop_v16_performance import RUNTIMES

REPORT = Path("planning/research/ADAPTIVE-VELOCITY-V17-RESULTS-20261116")
WORKSPACE = Path("D:/ANNAM/TradingWorkspace")


def performance():
    started = time.perf_counter()
    receipts = {}
    for group, python in RUNTIMES.items():
        output = JOB / f"tests-after-{group}.json"
        if output.exists():
            raise ValueError("preserve_V17_test_attempt")
        command = [python, "tooling/ai-engines/quant_test_suite.py", "--group", group,
                   "--tier", "all", "--output", str(output)]
        if group == "base":
            command += ["--workers", "4", "--profile", str(V16 / "tests-after-base.json")]
        subprocess.run(command, check=True)
        receipts[group] = read(output)
    ids, baseline = set(), set()
    timings = {}
    for group, r in receipts.items():
        if not r["passed"] or r["skipped"] or ids & set(r["timings"]):
            raise ValueError("V17_test_failure_skip_or_duplicate")
        ids.update(r["timings"])
        timings.update(r["timings"])
        baseline.update(read(V16 / f"tests-after-{group}.json")["timings"])
    if not baseline <= ids:
        raise ValueError("V17_historical_test_ID_loss")
    wall = time.perf_counter() - started
    before = read(V16 / "tests-after-matrix.json")
    save("tests-after-matrix.json", dict(
        tests=len(ids), preserved_baseline_ids=len(baseline), zero_skip=True,
        total_wall_seconds=wall, baseline_wall_seconds=before["total_wall_seconds"],
        latency_reduction_pct=100 * (1 - wall / before["total_wall_seconds"]),
        groups={g: {k: r.get(k) for k in ("tests", "seconds", "workers", "shard_seconds",
                                         "import_seconds")} for g, r in receipts.items()},
        top15=sorted(timings.items(), key=lambda x: -x[1])[:15],
        new_IDs=sorted(ids - baseline), baseline_matrix_sha256=sha(V16 / "tests-after-matrix.json"),
        base_workers=4, baseline_base_workers=2, cpu_count=os.cpu_count(),
        peak_process_tree_memory_bytes=None, memory_measurement="not measured",
        changes=["Immutable bytes baseline and isolated writable test copies",
                 "Four profile-balanced isolated base workers instead of two"],
        fixture_only_speedup=None, workload_identical=False,
        limitation="Historical baseline; ten additional tests. Combined changes, no causal attribution to fixture alone."))
    event("V17_full_tests_PASS", tests=len(ids), seconds=wall)


def smoke():
    rows = []
    plan = dict(attempts=10, fresh_process=True, workers=1, threshold_wall_seconds=.8,
                preserve_every_outlier=True, retry_to_find_good_streak=False, tests_unchanged=78)
    save("smoke-plan.json", plan)
    for i in range(10):
        output = JOB / f"smoke-{i:02d}.json"
        started = time.perf_counter()
        subprocess.run([sys.executable, "tooling/ai-engines/quant_test_suite.py",
                        "--group", "base", "--tier", "smoke", "--output", str(output)],
                       check=True, capture_output=True)
        r = read(output)
        rows.append(dict(attempt=i + 1, wall=time.perf_counter() - started,
                         suite=r["seconds"], tests=r["tests"], passed=r["passed"], skipped=r["skipped"]))
    if any(r["tests"] != 78 or not r["passed"] or r["skipped"] for r in rows):
        raise ValueError("V17_smoke_coverage_or_failure")
    save("smoke-results.json", dict(plan=plan, rows=rows, wall_max=max(r["wall"] for r in rows),
                                  wall_median=median(r["wall"] for r in rows),
                                  all_ten_below080=all(r["wall"] < .8 for r in rows)))
    event("V17_smoke_complete", maximum=max(r["wall"] for r in rows))


def census(root):
    """Bounded roots, do not traverse Windows junctions or symbolic links."""
    stack = [root]
    result = dict(path=str(root), files=0, bytes=0, skipped_reparse=[], errors=[])
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    st = entry.stat(follow_symlinks=False)
                    if entry.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                        result["skipped_reparse"].append(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        result["files"] += 1
                        result["bytes"] += st.st_size
        except OSError as exc:
            result["errors"].append(str(exc))
    return result


def storage():
    # Historical price/matrix/account packages remain protected, even if large.
    sizes = [census(p) for p in (V15, V16, JOB)]
    candidates = [p for root in (V15, V16) for p in root.iterdir()
                  if p.is_file() and p.name.startswith(("tests-", "smoke-"))
                  and p.suffix in (".log", ".stdout")]
    processes = json.loads(subprocess.check_output([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
        text=True))
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    texts = []
    for name in tracked:
        p = WORKSPACE / name
        if p.is_file() and p.suffix in (".py", ".json", ".yml", ".yaml", ".ps1", ".toml"):
            try:
                texts.append((name, p.read_text(encoding="utf-8-sig").replace("\\", "/").lower()))
            except (OSError, UnicodeError):
                pass
    admitted, held = [], []
    for p in candidates:
        relative = p.relative_to(ROOT).as_posix()
        refs = [name for name, text in texts if p.as_posix().lower() in text or relative.lower() in text]
        active = [x["ProcessId"] for x in processes if p.parent.as_posix().lower()
                  in str(x.get("CommandLine", "")).replace("\\", "/").lower()
                  and "v17_delivery.py" not in str(x.get("CommandLine", ""))]
        r = dict(path=str(p), member=relative, bytes=p.stat().st_size, sha256=sha(p),
                 code_references=refs, active_pids=active)
        (held if refs or active else admitted).append(r)
    archive = JOB / "closed-test-console-logs.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for r in admitted:
            z.write(r["path"], r["member"])
    restore = JOB / "cold-log-restore-proof"
    restore.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for r in admitted:
            p = (restore / r["member"]).resolve()
            if not p.is_relative_to(restore.resolve()):
                raise ValueError("V17_restore_scope")
            z.extract(r["member"], restore)
            if sha(p) != r["sha256"]:
                raise ValueError("V17_archive_roundtrip_SHA")
    digest = sha(archive)
    for r in admitted:
        p = Path(r["path"]).resolve(strict=True)
        if p.parent not in (V15.resolve(), V16.resolve()) or p.suffix not in (".log", ".stdout"):
            raise ValueError("V17_delete_scope")
        if sha(p) != r["sha256"]:
            raise ValueError("V17_log_drift")
        locator = p.with_name(p.name + ".v17-cold.json")
        with locator.open("x", encoding="utf-8") as f:
            json.dump(dict(original=str(p), archive=str(archive), archive_sha256=digest,
                           member=r["member"], sha256=r["sha256"], restored_and_hashed=True,
                           restore_instruction="Extract named member to original path; verify SHA256."),
                      f, indent=2)
        p.unlink()
        proof = (restore / r["member"]).resolve(strict=True)
        if not proof.is_relative_to(restore.resolve()):
            raise ValueError("V17_proof_scope")
        proof.unlink()
        r["locator"] = str(locator)
    d_paths = [WORKSPACE / n for n in tracked if n.startswith(("tooling/ai-engines/prop_v17",
               "tooling/ai-engines/v17_", "planning/research/ADAPTIVE-VELOCITY-V17"))]
    save("cold-compaction.json", dict(
        baseline_retention_inventory=str(V16 / "cold-log-inventory.json"),
        baseline_retention_sha256=sha(V16 / "cold-log-inventory.json"),
        bounded_sizes_before=sizes, D_campaign_tracked_bytes=sum(p.stat().st_size for p in d_paths if p.is_file()),
        D_scan_scope="V17 tracked campaign files; no full-drive census",
        removed=admitted, held=held, archive=str(archive), archive_sha256=digest,
        archive_bytes=archive.stat().st_size, logical_removed_bytes=sum(r["bytes"] for r in admitted),
        logical_net_before_receipts=sum(r["bytes"] for r in admitted) - archive.stat().st_size,
        physical_bytes_freed=None, restoration_proven_for_every_member=True, source_or_ledger_removed=0,
        absolute_zero_bloat_claim=False))
    event("V17_cold_logs_complete", files=len(admitted), held=len(held))


def summary(rows):
    out = metrics(rows)
    out["recent_33"] = metrics([r for r in rows if r["kind"] == "CHALLENGE" and r["start_msc"] >= DEV_END])
    return out


def collect():
    comparison, reuse, audits = [], [], []
    for tag in ("OLHC", "OHLC"):
        sources = [
            ("V15", "PRIMARY", V15 / f"Full-{tag}-sizing-accounts.json"),
            ("V15", "STRICT", JOB / f"Full-{tag}-V15-CUSHION-STRICT-accounts.json"),
            *[(version, mode, folder / f"Full-{tag}-{mode}-accounts.json")
              for version, folder in (("V16", V16), ("V17", JOB)) for mode in ("PRIMARY", "STRICT")]]
        for version, mode, p in sources:
            rows = read(p)
            if version == "V15":
                rows = [r for r in rows if r["profile"] == "CUSHION"]
            reuse.append(dict(version=version, mode=mode, order=tag, path=str(p), sha256=sha(p)))
            for cost in ("SYM", "ASYM"):
                chosen = [r for r in rows if r["cell"].startswith(cost)]
                value = summary(chosen)
                if value["windows"] != 105 or value["recent_33"]["windows"] != 33:
                    raise ValueError("V17_comparison_window_count")
                comparison.append(dict(version=version, mode=mode, order=tag, cost=cost, **value))
        for scope in ("Dev", "Full"):
            for mode in ("PRIMARY", "STRICT"):
                for kind in ("path", "account"):
                    name = (f"{scope}-{tag}-V17-{mode}-path-audit.json" if kind == "path"
                            else f"{scope}-{tag}-{mode}-account-audit.json")
                    p = JOB / name
                    r = read(p)
                    if not r["passed"]:
                        raise ValueError("V17_missing_independent_audit:" + name)
                    audits.append(dict(scope=scope, order=tag, mode=mode, kind=kind, path=str(p),
                                       count=r["paths" if kind == "path" else "accounts"], sha256=sha(p)))
        for kind in ("account", "path"):
            p = JOB / (f"Full-{tag}-V15-CUSHION-STRICT-account-audit.json" if kind == "account"
                       else f"Full-{tag}-V15-CUSHION-STRICT-path-audit.json")
            r = read(p)
            if not r["passed"]:
                raise ValueError("V17_parent_strict_audit")
            audits.append(dict(scope="Full", order=tag, mode="V15_CUSHION_STRICT", kind=kind,
                               path=str(p), count=r["paths" if kind == "path" else "accounts"], sha256=sha(p)))
    scan = {}
    for asset in ("XAUUSD", "EURUSD", "US500"):
        p = JOB / f"{asset}-scan.json"
        r = read(p)
        scan[asset] = dict(cells=len(r["rows"]), outcomes=r["outcomes"],
                           reasons=dict(Counter(x for row in r["rows"] for x in row.get("reasons", []))),
                           endpoint_cash_checks=r["endpoint_cash_checks"], scalar_paths=r["scalar_paths"],
                           source_uncertain_gaps=r["source_gap_records"], sha256=sha(p))
    paths = read(V16 / "Full-OLHC-PRIMARY-path-receipt.json")
    tests = read(JOB / "tests-after-matrix.json")
    if tests["preserved_baseline_ids"] != 1138 or not tests["zero_skip"]:
        raise ValueError("V17_ID_coverage")
    result = dict(schema="V17-results-v1", decision="NO_QUALIFIED_VELOCITY_OR_GAP_CONVERGENCE_UPGRADE",
                  prop_qualified=False, market_certified=False, freeze=read(FREEZE),
                  freeze_commit="d1d1d3b", PR95_merge="0fb47ae",
                  comparison=comparison, ledger_bindings=reuse, audits=audits,
                  tiers=read(JOB / "tier-selection.json"),
                  admission_diagnosis=read(JOB / "V16-Dev-admission-diagnosis.json")["summaries"],
                  parent_code_binding=read(JOB / "V16-parent-code-binding.json"),
                  scan=scan, selection=read(JOB / "selection.json"),
                  parent_path_summary=paths, tests=tests, smoke=read(JOB / "smoke-results.json"),
                  storage=read(JOB / "cold-compaction.json"),
                  independent_implementation_not_independent_author=True, same_feed=True,
                  actual_broker_orders=0, actual_payout_usd=0,
                  official_sources_attempted_20261116=[
                      "https://ftmo.com/en/faq/do-i-have-to-close-my-positions-overnight/",
                      "https://ftmo.com/en/faq/can-i-trade-news/"],
                  current_official_terms_reverified=False,
                  official_fetch_receipt=str(JOB / "official-terms-check.json"),
                  limits=["Later 2024-2026 prices already exposed; no pristine OOS.",
                          "2026 ends 13 Oct; overlapping monthly starts are not independent probabilities.",
                          "M1 two-order scenarios and declared Ask/slippage proxies, not verified broker fills.",
                          "Historical news, account specification and future data continuity not certified.",
                          "Strict synthetic excursions are sensitivity, not recovered data or mathematical bounds.",
                          "Prospective 2.4% daily reserve is an entry guard, not a guaranteed gap-fill loss bound.",
                          "Hypothetical payout sums across overlapping accounts are not owner income."])
    inventory = {p.name: dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
                 for p in JOB.iterdir() if p.is_file() and p.suffix in (".json", ".npz", ".zip")}
    result["artifact_index"] = inventory
    REPORT.with_suffix(".json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if REPORT.with_suffix(".json").stat().st_size > 1024 * 1024:
        raise ValueError("V17_report_size")
    write_report(result)
    event("V17_report_written", path=str(REPORT), decision=result["decision"])


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] + [
        "| " + " | ".join(str(v).replace("|", r"\|") for v in row) + " |" for row in rows]


def write_report(s):
    lines = ["# V17 — Trọng số, hạn mức và kiểm lại tốc độ Challenge", "",
             "**Chưa có nâng cấp đủ điều kiện Challenge.** Không có sleeve bổ sung qua đủ cổng; "
             "giữ toàn bộ kết quả âm và chưa mở V18.", "",
             "Ở phí SYM, V17 PRIMARY hoàn tất 68/105 cửa sổ, trung vị 42,95 tháng: nhanh hơn "
             "V16 (47,08) nhưng chậm hơn V15 (34,85). STRICT V17 chỉ 0/105; cả ba phiên bản "
             "đều 0/33 starts từ 2024. V17 giảm DD PRIMARY nhưng chưa giải quyết time-fit hoặc gap.", "",
             "PR #95 đã merge `0fb47ae`, nhánh V16 đã xóa. V17 đăng ký `e3a390d`, khóa "
             "code/tier/selection `d1d1d3b` trước đo chính sách mới trên 2024–13/10/2026. "
             "Đây là giá đã exposed từ nghiên cứu cũ, không phải OOS nguyên vẹn.", "",
             "## 1. Điểm nghẽn thật và chính sách đã khóa", "",
             "V16 có 494 tín hiệu full-period, **0 lệnh qua đêm**, còn 32 đường giá bất định. "
             "Không có vị thế 48 giờ chiếm hạn mức. Trong Dev PRIMARY, mỗi cost/ordering có "
             "36 lần từ chối cap trên các tài khoản chồng lấn, chỉ 3 tín hiệu riêng biệt; "
             "0 overnight blocker và 0 bóp lot một phần do cap. STRICT: 15 lần/6 tín hiệu, "
             "4.205 lần từ chối reserve. Không suy lợi nhuận tương lai của tín hiệu bị từ chối.", "",
             "Tại 20:30 không thể biết đường giá đêm tới có đầy đủ hay không. Dùng tick/HTF "
             "của tương lai để cấp phép carry sẽ nhìn trước dữ liệu. V17 giữ daily-flat, "
             "không carry/re-entry. Khung 07:00–20:30 cũng không bảo đảm M1 liên tục.", "",
             "Ba sổ sleeve riêng risk 150 USD được replay/audit trên Dev, lấy tỷ số annual Net R/"
             "floating R-DD xấu nhất của hai phí × hai ordering. Đây không phải CAGR Calmar.", ""]
    lines += table(["Sleeve", "Tier", "Worst annual R/DD"], [
        [r["id"], s["tiers"]["tiers"][r["id"]], round(r["worst_score"], 6)] for r in s["tiers"]["scores"]])
    lines += ["", "Tier nhân sau equity throttle của V15 factor 1,5+cushion, làm tròn xuống 0,001 USD. "
              "Không tăng cược hoặc chọn lại equal/tiered sau kết quả. Cap tổng 1.000 USD; "
              "swing ≤400, dành 600 intraday; intraday mượn phần swing chưa dùng. Phân giỏ theo "
              "deadline biết tại entry. Cả danh mục thực đều intraday nên cap swing chưa hoạt động; "
              "invariant hai giỏ được kiểm bằng fixture.", "",
              "Guard mới yêu cầu projected all-stop equity sau phí cao hơn balance đầu ngày Prague "
              "trừ 1.200 USD (2,4% sổ 50k), đồng thời giữ reserve tổng 8,4%, phase risk, daily halt "
              "và harvester cũ. Guard entry không là lệnh thanh lý hay bảo đảm fill xuyên gap <2,5%.", "",
              "## 2. Quét intraday và độ hoàn thiện đường giá", ""]
    lines += table(["Asset", "Cells", "Stage-0 fail", "SL-active reject", "Qualified"], [
        [a, r["cells"], r["outcomes"].get("STAGE0_ECONOMIC_OR_SCALE_FAIL", 0),
         r["outcomes"].get("REJECTED", 0), r["outcomes"].get("ELIGIBLE", 0)] for a, r in s["scan"].items()])
    lines += ["", "503 cells reuse budget V16, chỉ thêm hàng rào giờ entry ≥07:00; giữ recipes, cost, "
              "clone exclusions và hai cluster 2018–2020/2021–2023. Báo cả unconditional endpoint; "
              "Stage-0 gate kế thừa dùng admitted cohort. Không chọn horizon/cohort mới sau outcome. "
              "Mỗi endpoint được tính lại bằng Decimal; mọi SL-active path của cells qua Stage-0 "
              "được scalar audit hai ordering. Các lý do từng cell nằm trong private scan JSON.", "",
              "**Selection rỗng.** Không dựng adapter multiasset suy đoán. GBP/AUD tiếp tục data-incomplete; "
              "không biến tick rời rạc thành M1. Danh mục A vẫn giữ gap labels của V16; không bỏ trade "
              "sau khi thấy thiếu giá và không dùng synthetic stress để chứng nhận nguồn. "
              "Không đạt mục tiêu hội tụ PRIMARY/STRICT.", "",
              "## 3. V15–V17: cùng 105 starts, hai phí và hai ordering", "",
              "V15 PRIMARY reuse CUSHION có hash. **V15 STRICT cũ dùng risk V14**, nên lượt này replay "
              "cùng shared stress tape tại factor 1,5+cushion rồi audit để so đúng policy. "
              "V16 hai chế độ reuse ledgers có hash; V17 là sổ mới. SYM/ASYM là hai proxy swap đã đăng ký; "
              "V16/V17 intraday không có rollover nên không nhận lợi thế từ đổi proxy swap.", ""]
    lines += table(["Order/phí", "Bản", "Mode", "P1/105", "Hai vòng/105", "Recent/33",
                    "Median tháng", "Daily %", "Static %", "Breach"], [
        [r["order"] + "/" + r["cost"], r["version"], r["mode"], r["phase1"], r["funded"],
         r["recent_33"]["funded"], None if r["median_months"] is None else round(r["median_months"], 2),
         round(r["worst_daily"], 4), round(r["worst_static"], 4), r["breaches"]] for r in s["comparison"]])
    lines += ["", "Median chỉ trên cửa sổ hoàn tất; chưa hoàn tất vẫn censored. Starts mỗi tháng chồng lấn, "
              "không là xác suất pass độc lập; gần cuối mẫu ít thời gian theo dõi hơn. "
              "JSON có P1/P2 censoring, recent median/DD/payouts và toàn bộ ledger bindings.", ""]
    lines += table(["Order/phí", "Bản/mode", "Post-challenge count", "USD (chồng lấn)",
                    "Standalone count", "Standalone USD"], [
        [r["order"] + "/" + r["cost"], r["version"] + "/" + r["mode"], r["payout_count_windows"],
         round(r["payout_windows_usd"], 2), r["standalone_payout_count"], round(r["standalone_payout"], 2)]
        for r in s["comparison"]])
    lines += ["", "Payout là số mô phỏng trước phí mua/retry challenge, vận hành và thuế; tổng nhiều tài khoản "
              "chồng lấn không phải thu nhập. Chưa có payout hay lệnh broker thật.", "",
              "## 4. Kiểm toán, hiệu năng, lưu trữ và quyết định", "",
              f"Đủ {len(s['audits'])} receipts mới về đường giá/sổ tài khoản (Dev/Full, hai ordering, hai mode "
              "và V15 CUSHION strict). Oracle scalar/Decimal kiểm entry/SL/deadline, cash, phí, "
              "MTM, tier/cap/daily floor và payout; test có negative contract và replay 4-loss từ chối lệnh thứ tư. "
              "US500 oracle bổ sung contract=1, grid 0,001 và giờ nghỉ NY; hồi quy Gold/FX giữ nguyên. "
              "Receipt parent-code-binding đầu lượt giữ nguyên phiên bản cũ; oracle mở rộng có pin mới ở freeze V17. "
              "Độc lập implementation, **cùng tác giả và feed**, không giả reviewer độc lập.", ""]
    t = s["tests"]
    lines += [f"Full suite **{t['tests']} PASS, 0 skip**, giữ đủ {t['preserved_baseline_ids']} ID V16. "
              f"Wall **{t['baseline_wall_seconds']:.3f} → {t['total_wall_seconds']:.3f}s**, "
              f"giảm **{t['latency_reduction_pct']:.1f}%**. Baseline lịch sử, thêm 10 tests; không gọi "
              "hai workload hoàn toàn giống nhau. Bốn base worker cân bằng bằng profile thay hai; "
              "shared immutable bytes ở capture fixture, mỗi test vẫn có file/state riêng, có kiểm "
              "không sửa baseline. Không mock bỏ process/recovery assertions.", "",
              "Chưa đo peak process-tree RAM hay speedup riêng fixture; không quy toàn bộ cải thiện "
              "cho chia sẻ bộ nhớ. Process isolation và CPU trade-off được ghi rõ.", "",
              f"Smoke đúng 10 fresh processes ×78 tests: median/max "
              f"**{s['smoke']['wall_median']:.3f}/{s['smoke']['wall_max']:.3f}s**; "
              f"10/10 <0,80s: **{s['smoke']['all_ten_below080']}**. Không retry lấy streak đẹp.", ""]
    z = s["storage"]
    lines += table(["Job E", "Files trước nén", "Bytes trước nén"], [
        [Path(r["path"]).name, r["files"], r["bytes"]] for r in z["bounded_sizes_before"]])
    lines += ["", f"Nén {len(z['removed'])} test/console logs V15/V16 đã đóng: "
              f"{z['logical_removed_bytes']:,} → {z['archive_bytes']:,} bytes, giảm logic trước receipts "
              f"{z['logical_net_before_receipts']:,} bytes. Extract/SHA mọi member trước khi xóa bản log nóng; "
              "đường cũ có hydration locator. Reuse retention inventory V16; census chỉ các roots đã nêu "
              "và D campaign files, bỏ qua reparse/junction. Không scan lại toàn ổ, không xóa dữ liệu/"
              "matrix/path/ledger/freeze/package/failed attempt. Chưa đo physical freed; không claim zero bloat tuyệt đối.", "",
              "Luồng chính: A paths V16 giữ nguyên → Dev sleeve books → tier freeze → account guard V17 "
              "→ PRIMARY/shared-gap stress replay → independent oracle → comparison. Điều này giữ "
              "được nguồn gốc từng con số mà không tạo strategy mới sau outcome.", "",
              "**Khuyến nghị: không dùng V17 để mua Challenge, không tăng risk để cứu time-fit.** "
              "Trọng số và hạn mức không tạo thêm lợi thế tín hiệu hay lấp đường giá thiếu. Giữ baseline "
              "V15 và toàn bộ V16/V17 làm evidence; không promote cho đến khi có lý do/nguồn dữ liệu "
              "mới qua budget riêng. V18 chưa được thực thi.", "",
              "Hậu kiểm: phân biệt occurrences/unique signals; không đổ lỗi concurrency cho overnight "
              "khi thực tế daily-flat; không dùng future completeness làm carry gate; so đúng risk profile; "
              "lưu fail và kiểm ID thay vì chỉ số test count. Các skill hiện hành đã bao phủ các guard "
              "này; không thêm skill hoặc instruction trùng lặp.", "",
              "Đã thử truy cập official FTMO FAQ ngày 16/11/2026 nhưng web tool không trả nội dung "
              "đối soát được, HTTP fallback lỗi SSL; receipt `official-terms-check.json`. Chưa xác minh "
              "lại terms hiện hành. Giữ proxy lịch/news đã đăng ký, không coi chúng là chứng nhận "
              "đầy đủ lịch news/terms/spec execution lịch sử hay 100% tuân thủ FTMO.", "",
              f"Evidence `{JOB}`; JSON <1MiB. PR #96 giữ mở; receipt "
              "`ci-exact-head-reconciliation-v2.json` được ghi sau push/check/download artifact, "
              "không sửa HEAD chỉ để nhét SHA CI vào cùng commit. VI WIP/Trader pin giữ nguyên; "
              "không broker, deploy, provider download, Astra hay memory update.", ""]
    REPORT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("performance", "smoke", "storage", "collect"))
    globals()[parser.parse_args().stage]()
