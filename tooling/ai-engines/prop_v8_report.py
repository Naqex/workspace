"""V8 report from sealed outputs, including canceled trials and prior exposure."""
from collections import Counter, defaultdict
from fractions import Fraction
from statistics import median
from prop_portfolio_review import parts
from prop_v6_report import aggregate, brief, n, table, readable_spacing
from prop_v8_common import *
from prop_v8_campaign import year_of
from prop_v8_source import Prices
from prop_v8_calendar_correction import CORRECTED, CORRECTION
from prop_portfolio_sources import BAR
from prop_portfolio_scan import gap_unknown
import numpy as np

OUT = Path("planning/research/PROP-GOLD-V8-RESULTS-20261115")


def development_review(dev):
    checked = 0
    for c in list(dev["candidates"].values()) + list(dev["sleeves"].values()):
        for a in c["economics"]:
            for budget, expected in a["budgets"].items():
                risk = int(budget)
                total, count, errors = Fraction(0), 0, []
                for t in c["trades"]:
                    if not t["day"].startswith(str(a["year"])) or not t["qualifies"]:
                        continue
                    if t["reason"] in ("CENSORED", "ENDPOINT_UNKNOWN_OPEN"):
                        continue
                    q = risk * 1000 // abs(t["entry_price_units"] - t["stop_units"])
                    if not 1 <= q <= 5000:
                        continue
                    money = parts(t, q, a["model"])
                    total += Fraction(money["net"], risk * 1000)
                    count += 1
                    errors.append(1 - q * t["natural_sl"] / risk)
                    checked += 1
                if count != expected["trades"] or abs(float(total) - expected["net_R"]) > 1e-8:
                    raise ValueError("V8_Dev_rational_bridge")
                if errors and abs(100 * max(errors) - expected["max_rounding_error_pct"]) > 1e-8:
                    raise ValueError("V8_Dev_rounding_bridge")
    attribution = {}
    baseline = dev["candidates"]["BASELINE"]["trades"]
    for name in ("N1", "N2"):
        c = dev["candidates"][name]
        transformed = {t["day"]: t for t in c["trades"]}
        classes = defaultdict(list)
        for t in baseline:
            child = transformed.get(t["day"])
            group = ("compression_or_context" if child is None else "kept" if child["qualifies"]
                     else "cost_and_stop_scale" if child["friction_ratio"] > .12 and child["natural_sl"] > 25
                     else "cost" if child["friction_ratio"] > .12 else "stop_scale")
            classes[(t["day"][:4], group)].append(t)
        rows = []
        for (y, group), trades in sorted(classes.items()):
            row = dict(year=int(y), category=group, trades=len(trades))
            for model in MODELS:
                net = Fraction(0)
                for t in trades:
                    q = 150000 // abs(t["entry_price_units"] - t["stop_units"])
                    net += Fraction(parts(t, q, model)["net"], 150000)
                row[model + "_baseline_R"] = float(net)
            rows.append(row)
        attribution[name] = rows
    old_sleeves = {}
    for name in CELLS:
        old = read(V3 / f"natural-{name}.json")
        filled = [t for t in old["records"] if t["status"] == "FILLED"]
        unknown = [t for t in old["records"] if "UNKNOWN" in t["status"]]
        incomplete = [t for t in filled if not t["source_path_complete"]]
        old_sleeves[name] = dict(
            old_filled=len(filled), old_incomplete=len(incomplete),
            old_incomplete_sides=dict(Counter(t["side"] for t in incomplete)),
            old_incomplete_days=[t["day"] for t in incomplete],
            old_unknown_endpoint_records=unknown,
            old_unknown_gap_days=[t["day"] for t in filled if t["unknown_gaps"]],
            explanation="Not a missing-holiday endpoint; prior SELL Ask path was a conditional proxy.")
    return dict(status="PASS", rational_cost_bridges=checked, attribution=attribution,
                old_sleeve_blockers=old_sleeves)


def parent_parity(order, cases):
    prior = (read(V7 / order / "accounts.json") + read(V7 / order / "funded-accounts.json")
             + read(V7 / order / "annual-reference.json"))
    prior = [a for a in prior if a["policy_id"] == "GOLD_V4" and a["reference_side"] == "BOTH"]
    fields = ("accepted", "closed", "balance_usd", "phase_passes", "payouts",
              "peak_dd_pct", "static_loss_pct", "worst_daily_loss_pct", "terminal_equity_usd")
    differences = []
    def signatures(rows):
        return [{k: v for k, v in x.items() if k != "trade"} for x in rows]
    for a in cases:
        b = next(b for b in prior if all(b[k] == a[k] for k in
                 ("start_msc", "end_msc", "cell", "rolling", "standalone_funded")))
        for k in fields:
            av, bv = (signatures(a[k]), signatures(b[k])) if k in ("accepted", "closed") else (a[k], b[k])
            if av != bv:
                differences.append(dict(start=a["start_msc"], model=a["cell"], field=k))
    if differences:
        raise ValueError("V8_V7_baseline_changed:" + str(differences[:3]))
    return dict(status="PASS", cases=len(cases), fields=fields, trade_indices_remapped=True)


def source_diagnostics(tag, trades, folder):
    """Check long gaps only while a modeled position is alive."""
    first, end = (START, END) if tag == "full" else (BACK_START, BACK_END)
    bars = np.fromfile(folder / "bid-m1.bin", dtype=BAR)
    hours = read(folder / "hours.json")
    reader = Prices(read(folder / "manifest.json"),first,end)
    years, unknown_paths = [], []
    for y in range(year_of(first), year_of(end-1)+1):
        lo, hi = stamp(f"{y}-01-01"), min(stamp(f"{y+1}-01-01"), end)
        count = int(np.count_nonzero((bars["t"] >= lo) & (bars["t"] < hi)))
        rows = [t for t in trades if t["day"].startswith(str(y))]
        models = {}
        for model in MODELS:
            totals = dict(gross_R=0., commission_R=0., slippage_R=0., swap_R=0., net_R=0.)
            executable = 0
            for t in rows:
                q = 150000 // abs(t["entry_price_units"]-t["stop_units"])
                if not 1 <= q <= 5000:
                    continue
                p = parts(t,q,model)
                totals["gross_R"] += p["gross"]/150000
                totals["commission_R"] += (p["fee0"]+p["fee1"])/150000
                totals["slippage_R"] += 2*p["slip"]/150000
                totals["swap_R"] += sum(p["swaps"].values())/150000
                totals["net_R"] += p["net"]/150000
                executable += 1
            models[model] = dict(totals, executable=executable)
        years.append(dict(year=y, minutes=count, complete_H1=sum(
            lo<=h[0]<hi and h[5]==60 for h in hours), models=models))
    for t in trades:
        path,_ = reader.path(t["entry_msc"],t["exit_msc"])
        gaps = gap_unknown(path["t"],1)
        if gaps:
            unknown_paths.append(dict(day=t["day"],side=t["side"],gaps=gaps))
    return dict(years=years, active_unknown_long_gap_paths=unknown_paths,
                criterion=">15min excluding <=2h NY rollover; not intraminute certification")


def build():
    release = verify()
    dev = read(JOB / "development.json")
    if release["decision"] != read(DECISION) or release["decision"] != dev["decision"]:
        raise ValueError("V8_composition_drift")
    tests = read(JOB / "tests.json")
    if tests["status"] != "PASS":
        raise ValueError("V8_tests_not_passed")
    review = development_review(dev)
    write_json(JOB / "development-accounting-parity.json", review)
    scenarios, bindings = {}, []
    for tag in ("full", "backward"):
        scenarios[tag] = {}
        first, end = (START, END) if tag == "full" else (BACK_START, BACK_END)
        for order in ORDERS:
            folder = (CORRECTED if tag=="backward" else JOB) / tag / order
            cases = read(folder / "accounts.json")
            physical_trades = read(folder / "system-trades.json")
            parity = read(folder / "accounting-parity.json")
            if parity["status"] != "PASS" or parity["accounts"] != len(cases):
                raise ValueError("V8_accounting_not_passed")
            if any(a["open_positions"] or a["first_breach"] for a in cases):
                # Preserve results if a breach exists, but require explicit review wording.
                raise ValueError("V8_breach_or_open_needs_report_review")
            models = {}
            for model in MODELS:
                rolling = [a for a in cases if a["rolling"] and not a["standalone_funded"] and a["cell"] == model]
                funded = [a for a in cases if a["standalone_funded"] and a["cell"] == model]
                refs = [a for a in cases if not a["rolling"] and a["cell"] == model]
                years = []
                for a in refs:
                    accepted = a["accepted"]
                    sides = Counter(physical_trades[t["trade"]]["side"] for t in accepted)
                    years.append(brief(a) | dict(year=year_of(a["start_msc"]), sides=dict(sides)))
                jan = min(funded, key=lambda a: a["start_msc"])
                models[model] = dict(
                    rolling=aggregate(rolling), old=aggregate([a for a in rolling if a["start_msc"] < stamp("2025-01-01")])
                        if tag == "full" else None,
                    fresh=aggregate([a for a in rolling if a["start_msc"] >= stamp("2025-01-01")])
                        if tag == "full" else None,
                    Jan_first=brief(jan),
                    funded_all_starts=[brief(a) for a in funded],
                    funded_yearly=[dict(year=y, events=sum(year_of(p["at"]) == y for p in jan["payouts"]),
                        trader_usd=sum(p["trader_usd"] for p in jan["payouts"] if year_of(p["at"]) == y))
                        for y in range(year_of(first), year_of(end-1)+1)],
                    annual=years,
                    rolling_accounts=[brief(a) for a in rolling])
            scenarios[tag][order] = dict(
                models=models, parity={k:v for k,v in parity.items() if k != "records"},
                quality=read(folder / "path-quality.json"),
                source=read(folder / "source-proof.json"),
                economics=read(folder / "annual-economics.json"),
                source_diagnostics=source_diagnostics(tag,physical_trades,folder) if order==ORDERS[0] else None,
                parent_parity=parent_parity(order, cases) if tag == "full" else None)
            for name in ("accounts.json", "accounting-parity.json", "system-trades.json",
                         "path-quality.json", "source-proof.json", "manifest.json", "annual-economics.json"):
                path = folder / name
                bindings.append(dict(path=path.as_posix(), sha256=digest(path)))
    for path in (CORRECTION, CORRECTED/"calendar.json", CORRECTED/"release.json",
                 JOB/"development.json", JOB/"development-accounting-parity.json", JOB/"tests.json"):
        bindings.append(dict(path=path.as_posix(),sha256=digest(path)))
    if (JOB/"portability-parity.json").exists():
        bindings.append(dict(path=(JOB/"portability-parity.json").as_posix(),
                             sha256=digest(JOB/"portability-parity.json")))
    result = dict(schema="PROP-GOLD-V8-RESULTS-v1", date="2026-11-15",
        verdict="NO_GO_NORMALIZED_AND_PORTFOLIO", prop_qualified=False, main_income_proven=False,
        evidence_status=dict(development="ECONOMIC_FAIL_AND_SCALE_RETENTION_SHORTFALL",
                             backward_control="ECONOMIC_FAIL_IN_DECLARED_M1_MODEL",
                             full_path="DATA_PATH_INCOMPLETE_TWO_ACTIVE_PATHS_2024"),
        merged_PR86_commit="c99fa7ec0f96fd5192a92d83c4ff98629b01acd7",
        freeze_commit=release["commit"], decision=release["decision"],
        source_labels=dict(full="POST_HOLDOUT_DIAGNOSTIC_2022_2026",
                           backward="BACKWARD_HISTORICAL_VALIDATION_PRIOR_PROJECT_EXPOSURE"),
        clean_OOS=False, backward_release_count=1, backward_reselection=False,
        backward_technical_attempts=2, pristine_one_shot_claim=False,
        calendar_correction=dict(registration=read(CORRECTION),release=read(CORRECTED/"release.json")),
        archived_backward_attempt=dict(
            reason="2021-12-31 wrongly CLOSED by US federal observance proxy",
            source=JOB.as_posix()+"/backward",cases=224,
            annual=[brief(a)|dict(year=year_of(a["start_msc"]))
                    for a in read(JOB/"backward"/ORDERS[0]/"accounts.json") if not a["rolling"]]),
        development={k: {name: {field:value for field,value in c.items() if field != "trades"}
                         for name,c in dev[k].items()} for k in ("candidates","sleeves")},
        calibration=dict(k=dev["decision"]["compression_k"], days=dev["ratio_calibration_days"], percentile=85),
        diagnostic_review=review, scenarios=scenarios,
        canceled_columns=dict(normalized_post_dev="NO_GO_ON_DEVELOPMENT",
                              portfolio="NO_ADMISSIBLE_NORMALIZED_CORE_OR_SLEEVE"),
        tests={k:v for k,v in tests.items() if k != "matrix"} |
              dict(matrix=[{k:v for k,v in x.items() if k not in ("ids","modules")} for x in tests["matrix"]]),
        accounting_cases=sum(s["parity"]["accounts"] for t in scenarios.values() for s in t.values()),
        code=[dict(path=p.as_posix(),sha256=digest(p)) for p in sorted(Path("tooling/ai-engines").glob("prop_v8_*.py"))],
        bindings=bindings, private_job=JOB.as_posix(), broker_executions=0,
        actual_payout_received_usd=0, same_implementer_alternate_accounting=True,
        independent_person_or_model_review=False)
    write_json(OUT.with_suffix(".json"), result)
    render(result)
    event("V8_report_complete", verdict=result["verdict"], cases=result["accounting_cases"],
          tests=result["tests"]["unique_tests"])


def render(r):
    d = r["development"]
    s = [
        "# V8 — thử chuẩn hóa Gold A, mở lại ba sleeve và kiểm định lịch sử",
        "**Kết luận: N1, N2 và cả ba sleeve đều chưa qua cổng Development. Không hình thành danh mục V8 đủ điều kiện.** "
        "Đã hoàn thành chẩn đoán và kiểm baseline đối chứng; không gọi việc hoàn tất hạ tầng/báo cáo là đạt mục tiêu Challenge hay thu nhập chính.",
        "PR #86 đã merge tại `c99fa7e`; branch V8 `codex/prop-gold-v8`. "
        f"Quyết định No-Go được commit `{r['freeze_commit']}` trước mở giá lùi thời gian. "
        "2024–2026 không dùng để chọn N1/N2/sleeve; không có trial ngoài hai bản core và ba horizon đã đăng ký.",
        "## 1. Hai điều cần sửa trong tiền đề",
        "SL 28,21/58,85 USD/oz không phải hộp Á: hộp Á median là 23,33/46,06 USD/oz năm2025/2026. "
        "Quan sát hộp/SL tăng chưa chứng minh “sóng đã chạy xong”. V8 kiểm hai giả thuyết cụ thể; "
        "thu nhỏ stop có thể làm tăng số lần bị quét và ma sát theo R.",
        "**2018–2021 không phải clean holdout toàn dự án.** Gold R043 đã dùng2010–2024; "
        "`GOLD-ML-SL-LABELS-PROTOCOL-20261109.md` dùng2018/2021. Nhánh H1 dùng warmupNov2021; "
        "`PROP-PORTFOLIO-V3-PROTOCOL-20261114.md` dùng warmup từJan2021. "
        "V8 giữ đóng toàn bộ price partitions này trong thiết kế, rồi mở trong một release sau commit, "
        "nhưng phải gọi đúng là **backward historical validation, có prior exposure**. Đây cũng không phải forward test tương lai.",
        "**Ngoại lệ kỹ thuật được ghi nhận:** có một cấu hình strategy đã khóa nhưng **hai lượt đo backward**. "
        "Sau lần đầu, FTMO Trading Update16/12/2021 xác nhận Metals ngày31/12/2021 Normal Hours, "
        "khác lịch federal-observed proxy ghi CLOSED. Đã commit sửa đúng ngày này trước khi đo lại, "
        "giữ guard Dec31 16:58 đã đăng ký và mọi ngày/entry mechanism/SL/k/risk khác. "
        "Attempt1 (224sổ) và oracles vẫn giữ nguyên; chỉ backward đo lại. Không gọi đây là một pristine one-shot run, "
        "không dùng kết quả để chọn lại N1/N2 hoặc sleeve.",
        "## 2. Đã thử đúng những gì?",
        f"- **N1:** giữ SL toàn hộp, chỉ nhận Asia range / median20 ngày Á trước đó ≤P85 Development, k={n(r['calibration']['k'],6)} "
        f"từ {r['calibration']['days']} ngày đủ context. Không fit k theo lợi nhuận.",
        "- **N2:** SL theo Low/High của nến H1 breakout +0,1ATR_H1 trước nến, chỉ thay khi gần hơn cấu trúc toàn hộp. "
        "Không cắt SL đến một mức USD tùy ý, không mid-box/grid/biến thể kết hợp.",
        "- Hai bản chỉ nhận natural SL≤25 USD/oz và stressF/SL≤12%. Với risk125 USD, SL≤25 bảo đảm ít nhất5oz =0,05lot; "
        "budget125/150/200 đều được kiểm trên cùng trade set. Lệnh không đạt thì bỏ, không ép level/volume.",
        "- Giữ H4 bias, H1 entry, BOTH, không TP cứng, tối đa48 giờ lịch và Friday/holiday flat. "
        "Cổng Dev yêu cầu net dương cả hai năm/hai phí/ba budgets, ≥40lệnh/năm, retention≥50%, scale≤12%.",
        "## 3. Kết quả core chỉ trên2022–2023",
    ]
    rows = []
    for name,c in d["candidates"].items():
        for a in c["economics"]:
            if a["model"] != "SYM_FLAT":
                continue
            rows.append([name,a["year"],a["raw"],a["normalized_before_cost"],a["admitted"],
                         n(a["natural_median_sl"]),n(100*a["scale_ratio"]),n(a["budgets"]["150"]["net_R"],3)])
    s += [table(["Bản","Năm","Baseline raw","Sau compression","Lệnh nhận","SL trước phí USD/oz","F/SL %","NetR SYM $150"],rows),
          "Baseline không áp các bộ lọc mới; cột lệnh nhận của baseline gồm toàn bộ tín hiệu. "
          "SYM swap BUY/SELL−40/−40, ASYM proxy−45/−5 USD/lot/rollover; commission/slip giữ V7."]
    rows=[]
    for name,c in d["candidates"].items():
        for a in c["economics"]:
            if a["model"]!="ASYM_FLAT":
                continue
            rows.append([name,a["year"]]+[n(a["budgets"][str(b)]["net_R"],4) for b in (125,150,200)]
                        +[n(max(a["budgets"][str(b)]["max_rounding_error_pct"] for b in (125,150,200)),2)])
    s += [table(["Bản","Năm","R ở$125","R ở$150","R ở$200","Max lỗi lot %"],rows),
          "**N1 không cứu được kinh tế:** năm2023 SYM khoảng−12,77R thay baseline+13,79R. "
          "Năm2022 ASYM còn đổi dấu giữa125/150/200 dù đã có ít nhất5oz. "
          "Giảm sai số lot không bảo đảm bất biến dấu cho một kỳ vọng rất gần0.",
          "**N2 lặp lại nút thắt stop quá nhỏ:** SL median5,76/4,49 USD/oz, F/SL13,75%/16,64%; "
          "phí loại57/103 và81/107 tín hiệu. Chỉ còn45/26lệnh, năm2022 SYM−15,24R. "
          "Thu nhỏ stop đến cấu trúc H1 là thay chiến lược và tăng nguy cơ bị dừng sớm, không phải sửa lỗi miễn phí.",
          "### Phân rã N1: những tín hiệu bị bỏ trước đây đóng góp bao nhiêu?",
          "Dưới đây là R của **lệnh baseline gốc**, chia theo lý do N1 giữ/bỏ; không chạy trial nới filter nào."]
    s += [table(["Năm","Nhóm","Lệnh","Baseline R SYM","Baseline R ASYM"],
                [[a["year"],a["category"],a["trades"],n(a["SYM_FLAT_baseline_R"],3),n(a["ASYM_FLAT_baseline_R"],3)]
                 for a in r["diagnostic_review"]["attribution"]["N1"]]),
          "Các thay đổi gồm compression, trần natural SL và cost gate; không quy toàn bộ chênh lệch cho riêng compression.",
          "## 4. Ba Gold sleeve cũ: sửa đúng blocker, không chỉ gọi là lỗi lịch",
          "Cả ba là **PREVDAY sweep/reversal trên H1**, tín hiệu08–11 UTC London: "
          "giá xuyên high/low ngày trước rồi đóng trở lại và nến xác nhận cùng chiều. "
          "SL ở extreme H1+0,1ATR; ba horizon DAY20:30,24h,48h đều chịu Friday/holiday clamp. "
          "Không có H4 trend filter cho sweep này; không mô tả nhầm là trend breakout.",
          "Hồ sơ V3 đã có endpoint: không có `ENDPOINT_UNKNOWN` và không có ngày gap chưa giải quyết trong các lệnh FILLED. "
          "DAY/24H có12/45 lệnh thiếu observed Ask path;48H có14/45, đều liên quan SELL/proxy. "
          "V8 dùng observed paired tick hours sẵn có, giờ thiếu thì M1 Bid+Ask proxy0,338 có nhãn. "
          "Đạt100% endpoint trong model **không biến proxy Ask thành dữ liệu broker thật**."]
    rows=[]
    for name,c in d["sleeves"].items():
        for a in c["economics"]:
            if a["model"]!="SYM_FLAT":
                continue
            rows.append([name.rsplit(".",1)[-1],a["year"],a["raw"],a["admitted"],n(a["retained_pct"],1),
                         n(100*a["scale_ratio"],2),n(a["endpoint_coverage_pct"],1),n(a["budgets"]["150"]["net_R"],3)])
    s += [table(["Horizon","Năm","Raw","Nhận","Giữ %","F/SL %","Endpoint %","NetR SYM"],rows),
          "**Cả ba dương nhưng chưa đạt scale/retention:**23/51 và21/56, tức45,1%/37,5%; "
          "medianF/medianSL15,82%/16,92%, quá trần15%. "
          "Không tự hạ gate hoặc nới SL để “giải cứu”. So với V7,2023 trước đây22 lệnh nay21 do nguồn Bid/Ask và fills được thống nhất; "
          "outcomes mới không được ghi đè lên artifacts V3. Cổng50% là chính sách sàng lọc đã khóa của project, "
          "không phải định lý thống kê chứng minh các sleeve dương này không có edge.",
          "## 5. Chốt trước mở backward và các cột bị hủy",
          "Không core mới nào đạt và không sleeve nào đạt. **NORMALIZED và ALL-GOLD PORTFOLIO bị dừng ở Development.** "
          "Không dùng2018–2021 hay2024–2026 để chọn lại k/stop/horizon. Theo fallback đã đăng ký trước outcome, "
          "Phase3 chỉ chạy baseline control. Không có các con số “SL2025 đã giảm” hoặc “portfolio vượt quỹ” cho cấu hình không qua gate.",
          table(["Giai đoạn","V7 baseline","Gold normalized","All-Gold portfolio"],[
              ["Dev2022–2023","Đã đối soát","N1/N2: No-Go","3horizon: No-Go"],
              ["Full2022–13/10/2026","Đã đo đủ57mốc","N/A — canceled trước đánh giá","N/A — không composition đủ gate"],
              ["Backward2018–2021","Control đã đo48mốc","N/A — canceled trước mở","N/A — không composition đủ gate"]]),
          "## 6. Baseline control: annual và lifecycle",
          "Risk lifecycle V4:200/175/125 USD P1/P2/Funded; cap800, reserve46k, throttle150/90 và harvester Funded giữ nguyên. "
          "Annual reference:150 USD=0,30% vốn50k, không throttle/harvester. "
          "Hai orders M1 là độ nhạy O-L-H-C và O-H-L-C, không phải observed intraminute path."]
    for tag,label in (("full","2022–2026 YTD đến13/10"),("backward","2018–2021, backward có prior exposure")):
        p=r["scenarios"][tag][ORDERS[0]]
        s += [f"### {label}"]
        rows=[]
        for model,m in p["models"].items():
            for a in m["annual"]:
                rows.append([a["year"],model,a["entries"],f"{a['sides'].get('BUY',0)}/{a['sides'].get('SELL',0)}",
                             n(a["net_R"],3),n(a["mean_net_R"],4),n(a["peak_dd_pct"],3),
                             n(a["static_loss_pct"],3),n(a["worst_daily_loss_pct"],3)])
        s += [table(["Năm","Phí","Lệnh","BUY/SELL","NetR","MeanR","Peak-DD %","Static %","Daily %"],rows)]
        rows=[]
        for model,m in p["models"].items():
            groups=[("48 backward",m["rolling"])] if tag=="backward" else [("36 cũ",m["old"]),("21 mới",m["fresh"])]
            for group,a in groups:
                rows.append([model,group,a["passed1"],a["passed2"],
                    n(a["median_months_to_both_among_successes"]),a["payout_windows"],a["payout_events"],
                    n(a["trader_usd_window_sum"]),n(a["max_daily_pct"],3),n(a["max_static_pct"],3)])
        s += [table(["Phí","Mốc","P1","Cả2","Median tháng cả2","Mốc payout","Payout events","Trader USD chồng lấn","Daily %","Static %"],rows)]
        rows=[]
        for model,m in p["models"].items():
            a=m["Jan_first"]
            rows.append([model,len(a["payouts"]),n(a["trader_payout_usd"]),n(a["balance_usd"]),
                         n(a["worst_daily_loss_pct"],3),n(a["static_loss_pct"],3)])
        s += ["Standalone Funded giả định có tài khoản ngay đầu kỳ, nối liên tục:",
              table(["Phí","Payout events","Trader USD","Balance cuối","Daily %","Static %"],rows)]
    s += ["Không cộng các mốc chồng lấn thành thu nhập của một account. Payout là **mô phỏng đủ điều kiện/request proxy**, "
          "không tiền nhận thật; chưa trừ challenge/retry/vận hành. Không suy tỷ lệ pass mẫu thành xác suất tương lai.",
          "**Annual reference và lifecycle khác nhau:** reference không có throttle/reserve; "
          "riêng2018 SYM có Static Loss10,377% trên đường M1. Các sổ lifecycle có risk guard mới là nhóm được thống kê "
          "không modeled breach; không lấy kết quả đó để gọi bản risk150 cố định là an toàn.",
          "### Backward: âm do tín hiệu hay chỉ do phí?",
          table(["Năm","M1 bars","H1 đủ60phút","Gross sau spread R","Commission R","Slip R","Swap R ASYM","NetR ASYM"],
                [[a["year"],a["minutes"],a["complete_H1"],n(a["models"]["ASYM_FLAT"]["gross_R"],3),
                  n(a["models"]["ASYM_FLAT"]["commission_R"],3),n(a["models"]["ASYM_FLAT"]["slippage_R"],3),
                  n(a["models"]["ASYM_FLAT"]["swap_R"],3),n(a["models"]["ASYM_FLAT"]["net_R"],3)]
                 for a in r["scenarios"]["backward"][ORDERS[0]]["source_diagnostics"]["years"]]),
          "2018,2019,2021 đã âm gross sau spread trước commission/slip/swap; "
          "năm2020 gross dương nhỏ rồi bị ma sát/carry ăn hết. Vì vậy không thể giải thích cả bốn năm chỉ bằng phí swap. "
          "Đây là kết quả dưới nguồn/calendar/Ask model đã khai báo, không chứng minh mọi Asian breakout đều không có edge.",
          "## 7. Kiểm chứng và hậu kiểm"]
    rows=[]
    for tag,ss in r["scenarios"].items():
        for order,a in ss.items():
            p=a["parity"]
            rows.append([tag,order,p["accounts"],p["status"],p["accepted"],p["rejected"],p["costs"],p["dynamic_fills"]])
    s += [table(["Kỳ","Order","Sổ","Oracle","Admissions","Rejects","Costs","Dynamic fills"],rows),
          f"**{r['tests']['unique_tests']} tests PASS**,{r['tests']['V8_fixtures']}fixtures V8; "
          f"**{r['accounting_cases']} sổ account** đối soát bằng rational/cash-posted oracle và "
          f"**{r['diagnostic_review']['rational_cost_bridges']} bridges** cho economics Dev ba budgets. "
          "Cùng implementer, không có independent human/model reviewer.",
          "492sổ ở bảng là kết quả authoritative sau sửa lịch (268full+224backward). "
          "224sổ backward attempt1 cũng đã đối soát nhưng archived vì calendar sai; "
          "không cộng các lượt đo trùng profile thành mẫu độc lập. Correction chỉ bổ sung tín hiệu ngày31/12/2021, "
          "không mở vòng tìm tham số mới.",
          "Hai full orders khớp V7 Gold V4 về accepted/closed/cash/phase/payout/DD sau remap trade IDs, tổng268sổ. "
          "Full/backward đều giữ nguồn, không force-close cuối mẫu để tạo lãi hoặc fallback last quote tùy ý.",
          "Backward chỉ có Bid M1 và Ask proxy, các giờ holiday2018–2021 là conservative guards chưa certified từ FTMO lịch sử. "
          "Lịch2022–2026 giữ V7, gồm các giờ đã xác minh và những guard còn unknown. "
          "Không ghi nhận modeled breach trong các sổ lifecycle đã dựng không bảo đảm mọi đường tick thực đều an toàn. "
          "JSON giữ riêng danh sách khoảng trống>15phút khi vị thế đang sống, loại trừ giờ rollover thường lệ; "
          "đủ endpoint không thay thế kiểm đường giá.",
          "**Gap còn lại được phát hiện khi audit full:** hai vị thế SELL mở08/10 và09/10/2024 cùng đi qua "
          "khoảng thiếu native ticks từ09/10/2024 23:05:51,002 đến10/10/2024 00:11:48,930 UTC "
          "(khoảng66phút, ngoài rollover thông thường). Có giá entry/exit không chứng minh floating DD trong khoảng đó. "
          "Giữ sealed results V7/V8, gắn DATA_PATH_INCOMPLETE ở đúng claim full-path; không tự chèn tick giả "
          "hoặc sửa policy nguồn sau outcome. Backward không phát hiện long-gap đang giữ lệnh theo tiêu chí này, "
          "nhưng vẫn là M1/Ask proxy, không tick certification.",
          table(["Phần","Phát hiện","Đã làm","Giới hạn"],[
              ["Packaging","Registration cần tạo private directory trước write",f"Sửa trước khi mở dữ liệu; regression{r['tests']['V8_fixtures']}fixtures","Không đổi strategy outcome"],
              ["CI portability","LF/CRLF làm khác byte-hash của cùng lịch","Chỉ chấp nhận chuyển newline theo frozen Windows hash; content mutation vẫn fail; calendar-v2 parity PASS","Không sửa source prices hoặc rerun tài chính"],
              ["Calendar","Federal observance khác giờ Metals31Dec2021","Nguồn FTMO xác minh; giữ attempt1; commit fix và rerun riêng backward","Hai technical attempts, không pristine one-shot"],
              ["Reuse","V6/V7 đã có lifecycle/harvester/oracle","Adapter chỉ đổi inputs/observer; restore bindings trong finally; parent parity268sổ","Không gọi self-review là independent person"],
              ["Selection","Cả2core/3sleeve failDev","Khóa No-Go trước backward; không tuning cứu kết quả","Chưa có all-Gold candidate mới"],
              ["Source/exposure","2018–21 đã có prior use; M1không thànhtick","Giữ fence tới release; ghi nhãn đúng; seek partitions","Không sạch OOS, không broker validation"],
          ]),
          "## Quyết định cuối",
          "**Không promote N1/N2 hoặc sleeve; chưa mua Challenge hoặc tăng risk.** "
          "V8 bác bỏ hai cách sửa cụ thể dưới chi phí/gates đã khóa; không bác toàn bộ trend-following hoặc Gold. "
          "Bước tiếp có ích phải là một giả thuyết kinh tế mới với budget/gates đăng ký rõ, hoặc cải thiện bằng chứng execution đích; "
          "không tiếp tục nới điều kiện chỉ để các bản này thành winner. Mục tiêu thu nhập chính vẫn chưa đạt.",
          "## Bằng chứng",
          f"- Freeze trước backward: `{r['freeze_commit']}`; decision/protocol/calendar cùng prefixV8 trong thư mục này.",
          f"- Full ledgers, tests, release, source proof, Development raw/outcomes: `{JOB.as_posix()}`.",
          "- JSON cùng tên giữ baseline/control, annual/lifecycle, diagnostic attribution, canceled columns, oracle counts và hashes.",
          "- Phép dựng lại báo cáo: `python tooling/ai-engines/prop_v8_report.py`; không phát sinh trial hoặc backtest mới.",
          "- Nguồn lịch: V7 FTMO receipt và các declared guards; CME https://www.cmegroup.com/trading-hours.html ; "
          "https://www.cmegroup.com/trading/metals/files/metals-prod-guide-2020.pdf . Không dùng giờ NYSE thay giờ CFD được chứng nhận.",
          "- FTMO correction31/12/2021: https://ftmo.com/es/blog/trading-update-16-12-2021/ ; "
          "`PROP-V8-CALENDAR-CORRECTION-20261115.json` giữ source/old hash/scope.",
          ]
    text = readable_spacing("\n\n".join(s)+"\n")
    for before, after in (("N 1", "N1"), ("N 2", "N2"), ("warmupNov", "warmup Nov"),
                          ("từJan", "từ Jan"), ("thànhtick", "thành tick"), ("R 043", "R043")):
        text = text.replace(before,after)
    OUT.with_suffix(".md").write_text(text,encoding="utf-8")


if __name__ == "__main__":
    build()
