"""Measured delivery receipts and compact four-part V16 report."""
from collections import Counter
from datetime import datetime,timezone
from statistics import median
import subprocess
import sys
import time
import numpy as np
from prop_v16_common import *
from prop_v15_campaign import metrics

REPORT=Path("planning/research/GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116")


def smoke():
    plan=dict(attempts=10,fresh_process=True,workers=1,threshold_wall_seconds=.8,
        preserve_every_outlier=True,retry_to_find_good_streak=False,tests_unchanged=78)
    save("smoke-plan.json",plan);rows=[]
    for i in range(10):
        output=JOB/f"smoke-{i:02d}.json";start=time.perf_counter()
        subprocess.run([sys.executable,"tooling/ai-engines/quant_test_suite.py",
            "--group","base","--tier","smoke","--output",str(output)],check=True,capture_output=True)
        wall=time.perf_counter()-start;r=read(output)
        rows.append(dict(attempt=i+1,wall=wall,suite=r["seconds"],tests=r["tests"],
            passed=r["passed"],skipped=r["skipped"]))
    if any(r["tests"]!=78 or not r["passed"] or r["skipped"] for r in rows):
        raise ValueError("V16_smoke_coverage_or_failure")
    save("smoke-results.json",dict(plan=plan,rows=rows,wall_max=max(r["wall"] for r in rows),
        wall_median=median(r["wall"] for r in rows),suite_max=max(r["suite"] for r in rows),
        all_ten_below080=all(r["wall"]<.8 for r in rows)))
    event("V16_smoke_complete",maximum=max(r["wall"] for r in rows))


def year(at):return datetime.fromtimestamp(at/1000,timezone.utc).year


def summarize(rows):
    result=metrics(rows)
    recent=[r for r in rows if r["kind"]=="CHALLENGE" and r["start_msc"]>=DEV_END]
    result["recent_33"]=metrics(recent)
    return result


def attribution():
    cfg=read(V14/"candidate-freeze.json")
    original=read(V14/"OLHC-strategy-trades.json")
    core=read(V15/"Full-OLHC-PRIMARY-trades.json")
    baseline=[r for r in read(V15/"Full-OLHC-sizing-accounts.json")
        if r["profile"]=="CUSHION" and r["cell"].startswith("SYM")]
    book=next(r for r in baseline if r["kind"]=="STANDALONE_FULL")
    rows=[];values={"XAUUSD":1,"EURUSD":10}
    for identity in cfg["candidate_B"]:
        asset=identity.split("|")[0];scale=1000 if asset=="XAUUSD" else 100000
        for y in range(2018,2027):
            ts=[t for t in original if t["id"]==identity and year(t["decision_msc"])==y]
            closed=[t for t in ts if not t["censored"]]
            distances=[abs(t["entry_price_units"]-t["stop_units"]) for t in ts]
            used=[150000//(values[asset]*d)*values[asset]*d/150000 for d in distances]
            actual=[a for a in book["accepted"] if core[a["trade"]]["id"]==identity and year(a["at"])==y]
            actual_usage=[a["risk_state"]["new_stop_risk_milli_usd"]/(1000*a["risk_usd"]) for a in actual]
            rows.append(dict(id=identity,role="A" if identity in cfg["candidate_A"] else "B_EXTRA",
                asset=asset,year=y,trades=len(ts),BUY=sum(t["side"]=="BUY" for t in ts),
                SELL=sum(t["side"]=="SELL" for t in ts),censored=len(ts)-len(closed),
                SYM_R=sum(t["reference"]["SYM"]["net_R"] for t in closed),
                ASYM_R=sum(t["reference"]["ASYM"]["net_R"] for t in closed),
                median_natural_SL=float(np.median(distances)/scale) if distances else None,
                median_entry_price=median(t["entry_price_units"]/scale for t in ts) if ts else None,
                fixed150_reference_floor_reduced=sum(u<1-1e-12 for u in used),
                fixed150_reference_median_risk_usage_pct=100*median(used) if used else None,
                actual_standalone_admissions=len(actual),
                actual_standalone_floor_reduced=sum(u<1-1e-12 for u in actual_usage),
                actual_standalone_median_risk_usage_pct=100*median(actual_usage) if actual_usage else None))
    return rows


def table(headers,rows):
    return ["| "+" | ".join(headers)+" |","|"+"|".join("---" for _ in headers)+"|"]+[
        "| "+" | ".join(str(v).replace("|",r"\|") for v in row)+" |" for row in rows]


def collect():
    frozen=read(FREEZE);selection=read(JOB/"selection.json")
    comparison=[];reuse=[]
    for tag in ("OLHC","OHLC"):
        baseline=read(V15/f"Full-{tag}-sizing-accounts.json")
        baseline=[r for r in baseline if r["profile"]=="CUSHION"]
        primary=read(JOB/f"Full-{tag}-PRIMARY-accounts.json")
        strict=read(JOB/f"Full-{tag}-STRICT-accounts.json")
        for cost in ("SYM","ASYM"):
            for column,rows in (("V15_BASELINE",baseline),("V16_A_STRICT",strict),
                    ("V16_MULTI_PRIMARY",primary),("V16_MULTI_STRICT",strict)):
                chosen=[r for r in rows if r["cell"].startswith(cost)]
                comparison.append(dict(order=tag,cost=cost,column=column,**summarize(chosen)))
        proof=JOB/f"Full-{tag}-STRICT-accounts.json"
        reuse.append(dict(order=tag,source=str(proof),sha256=sha(proof),
            columns=["V16_A_STRICT","V16_MULTI_STRICT"],reason="Selected additions is exactly empty."))
    audits=[]
    for scope in ("Dev","Full"):
        for tag in ("OLHC","OHLC"):
            for mode in ("PRIMARY","STRICT"):
                for kind in ("path","account"):
                    p=JOB/f"{scope}-{tag}-{mode}-{kind}-audit.json";r=read(p)
                    if not r["passed"]:raise ValueError("V16_audit_missing:"+str(p))
                    audits.append(dict(scope=scope,order=tag,mode=mode,kind=kind,
                        count=r["paths"] if kind=="path" else r["accounts"],sha256=sha(p)))
    scans={a:read(JOB/f"{a}-scan.json") for a in ("XAUUSD","EURUSD","US500","GBPUSD","AUDUSD")}
    scan_summary={a:dict(cells=len(r["rows"]),statuses=dict(Counter(x["status"] for x in r["rows"])),
        reasons=dict(Counter(v for x in r["rows"] for v in x.get("reasons",[])))) for a,r in scans.items()}
    path_summary=[dict(scope=scope,order=tag,mode=mode,**read(JOB/f"{scope}-{tag}-{mode}-path-receipt.json"))
        for scope in ("Dev","Full") for tag in ("OLHC","OHLC") for mode in ("PRIMARY","STRICT")]
    source=read(JOB/"gap-identities.json")
    source_census=read(JOB/"raw-source-census.json")
    tests=read(JOB/"tests-after-matrix.json");before=read(JOB/"tests-before-matrix.json")
    smoke_result=read(JOB/"smoke-results.json")
    if tests["preserved_baseline_ids"]!=1126 or not tests["zero_skip"]:raise ValueError("V16_test_ID_loss")
    inventory={p.name:dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in JOB.iterdir()
        if p.is_file() and p.suffix in (".json",".npz",".zip")}
    result=dict(schema="V16-results-v1",decision="NO_QUALIFIED_ZERO_GAP_OR_VELOCITY_UPGRADE",
        prop_qualified=False,market_certified=False,selected_additions=selection["selected"],
        freeze=frozen,comparison=comparison,reuse=reuse,source_groups=source["groups"],
        source_census=dict(counts=source_census["counts"],candidates=len(source_census["records"]),
            zip_matches=len(source_census["zip_matches"]),errors=len(source_census["errors"])),
        source_admission=read(JOB/"source-admission-v16.json"),
        native_probe_counts=read(JOB/"native-probe.json")["counts"],
        alternate_probe=dict(files=read(JOB/"alternate-tick-probe.json")["files"],added_observations=0),
        csv_probe=dict(files=read(JOB/"csv-gap-probe.json")["files"],added_observations=0),
        scan_summary=scan_summary,scan_audit=read(JOB/"grid-corrected-scan-independent-audit.json"),
        grid_correction_parity=read(JOB/"grid-corrected-A-parity.json"),
        paths=path_summary,attribution=attribution(),audits=audits,
        storage=read(JOB/"cold-compaction.json"),tests_before=before,tests_after=tests,smoke=smoke_result,
        actual_broker_orders=0,actual_payout_usd=0,
        artifact_index=inventory,same_implementer_and_feed=True,
        limits=["Later prices already exposed; no pristine OOS.",
            "M1 two-order scenarios and fixed Ask proxy, not native intraminute broker fills.",
            "Overlap starts and payout sums are hypothetical, not independent probabilities or owner income.",
            "Partial 2026 ends 13Oct; recent starts are censored.",
            "No historical target-account news/slippage/swap execution certification."])
    REPORT.with_suffix(".json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    if REPORT.with_suffix(".json").stat().st_size>1024*1024:raise ValueError("V16_report_too_large")
    write_report(result)
    event("V16_report_written",path=str(REPORT),decision=result["decision"])


def write_report(s):
    primary=next(r for r in s["comparison"] if (r["order"],r["cost"],r["column"])==("OLHC","SYM","V16_MULTI_PRIMARY"))
    strict=next(r for r in s["comparison"] if (r["order"],r["cost"],r["column"])==("OLHC","SYM","V16_MULTI_STRICT"))
    full=next(r for r in s["paths"] if (r["scope"],r["order"],r["mode"])==("Full","OLHC","PRIMARY"))
    lines=["# V16 — Đóng trong ngày, quét đa tài sản và kiểm lại chứng cứ","",
        "**Chưa có nâng cấp đủ điều kiện Challenge.** Không có nhánh bổ sung qua đủ cổng trong 715 cấu hình.",
        f"Đóng A trước 20:30 UTC vẫn còn **{full['source_uncertain']} đường giá chưa đủ**, "
        f"mô phỏng chính hoàn tất **{primary['funded']}/105**, strict **{strict['funded']}/105**.",
        "Không đạt mục tiêu zero gap hoặc trung vị <18–24 tháng. Không promote G2 chỉ vì số gap giảm.","",
        "PR #94 đã merge `1c6e516`; nhánh V15 đã xóa. Bám bản sáu track hoàn chỉnh cuối attachment, "
        "không mở thêm grid MAE-stop/Day1 từ đoạn draft bị ngắt. PR #95 giữ mở để review.","",
        "## 1. Gap nào đã chứng minh được, gap nào còn thiếu?","",
        "V15 có **133 lượt trade–gap**: 95 model-low-risk và 38 loại trừ SL có điều kiện bằng native envelope. "
        "Đây không phải 95 lệnh độc lập. Strict cũ đổi 56 lệnh, không phải gán 95 lệnh thua đúng -1R.","",
        "38 trường hợp đều là EURUSD và có **0 tick ghi trong phút thiếu**. Có quote trước/sau, "
        "jump nhỏ hoặc SL xa không chứng minh feed liên tục hay sổ lệnh toàn thị trường. "
        "Không tự điền 38 nến M1 phẳng; **0 nến mới được admission**.",""]
    lines+=table(["Nhóm V15","Lượt gap","Asset","Flat morphology"],[
        [k,v["occurrences"],v["assets"],v["flat_morphology"]] for k,v in s["source_groups"].items()])
    lines+=["",f"Census hai project roots D/E: {s['source_census']['counts']['files']:,} files; "
        f"{s['source_census']['candidates']:,} candidates; {s['source_census']['zip_matches']} ZIP khớp; "
        f"{s['source_census']['errors']} lỗi giữ nguyên. Không phải quét tuyệt đối toàn ổ D/E. "
        "Các archive/format chưa giải mã và đường dẫn không đọc được vẫn unknown.",
        f"Đọc 122 CSV, thêm 62 tick fixtures khớp giờ/ngày: không thấy quote mới trong khoảng thiếu. "
        "Các view B0 theo phiên không được coi là tick trọn ngày. H1/H4 gộp lại từ cùng M1 thiếu "
        "không trở thành nguồn containment độc lập.","",
        "G2 chỉ dùng đồng hồ/lịch đã biết trước: đóng cùng ngày 20:30 UTC hoặc holiday sớm hơn; "
        "US500 thêm mốc 16:00 New York theo DST. Fill là quote quan sát đầu tiên tại/sau yêu cầu; "
        "không đóng hồi tố ở quote trước một outage chưa biết.",""]
    lines+=table(["Scope / order","Tín hiệu","Uncertain còn giữ","Qua đêm","Bar stress giả"],[
        [f"{r['scope']} / {r['order']}",r["signals"],r["source_uncertain"],r["entry_exits_overnight"],
         len(r["synthetic_patches"])] for r in s["paths"]])
    lines+=["", "Strict chèn excursion giả định chung cho các vị thế trên cùng asset/time, giữ toàn bộ "
        "observed bars và nhãn bất định gốc. Đây là sensitivity, không phải dữ liệu khôi phục hay "
        "biên dưới toán học. Uncertainty bằng 0 sau chèn không được dùng làm chứng nhận nguồn.","",
        "## 2. Vì sao chưa có đội hình nhanh hơn?","",
        "A giữ nguyên ba cơ chế, entry, SL/P1 và risk V15 factor 1,5 + cushion; chỉ đổi hạn thoát G2. "
        "Ngân sách DAY cũ 722 cells, bỏ 7 bản cùng asset+recipe A trước outcome, còn **715**. "
        "Không tạo tín hiệu, giờ giao dịch hoặc weight mới sau kết quả.",""]
    lines+=table(["Asset","Cells","Trạng thái"],[
        [a,v["cells"],v["statuses"]] for a,v in s["scan_summary"].items()])
    lines+=["", "Gold 18 và EURUSD 11 cells qua endpoint screen đều còn path gap; các lý do kinh tế, "
        "cadence và correlation theo từng cell nằm trong JSON/private job. US500 202 cells không qua "
        "Stage-0 economics/scale trên nguồn quarterly đã sửa; không gọi nguồn M1 này là đủ chỉ vì có loader. "
        "GBP/AUD có H1 sáu năm nhưng tick fixtures rời rạc, không dựng M1 giả. Vì vậy additions khóa **rỗng**.",
        "", "Attribution V15 theo nhánh (R của tín hiệu, chưa phải % tài khoản):",""]
    ids=list(dict.fromkeys(r["id"] for r in s["attribution"]))
    for n,identity in enumerate(ids,1):
        ts=[r for r in s["attribution"] if r["id"]==identity]
        lines.append(f"- S{n} `{identity}`: Development {sum(r['SYM_R'] for r in ts if r['year']<2024):+.4f}R; "
            f"2024–2026 {sum(r['SYM_R'] for r in ts if r['year']>=2024):+.4f}R.")
    lines+=["", "S4/S5 là hai nhánh B bổ sung trong V14; giữ riêng làm attribution, không chọn lại chiều/"
        "weights để cứu kết quả. Tổng A ở 2024–2026 chỉ +13,8926R; B thêm hai nhánh làm tổng giảm "
        "còn +6,1779R. Đó là đóng góp lịch sử đã exposed, không chứng minh nguyên nhân theo regime.",""]
    lines+=table(["A sleeve / năm","Lệnh","Net SYM R","SL trung vị","150 USD: risk dùng %","Actual standalone: risk dùng %"],[
        [f"S{ids.index(r['id'])+1} / {r['year']}",r["trades"],f"{r['SYM_R']:+.3f}",
         None if r["median_natural_SL"] is None else round(r["median_natural_SL"],5),
         None if r["fixed150_reference_median_risk_usage_pct"] is None else round(r["fixed150_reference_median_risk_usage_pct"],2),
         None if r["actual_standalone_median_risk_usage_pct"] is None else round(r["actual_standalone_median_risk_usage_pct"],2)]
        for r in s["attribution"] if r["role"]=="A"])
    lines+=["", "Gold SL đơn vị USD/oz; EURUSD SL đơn vị USD/EUR (nhân 10.000 thành pips). "
        "Giá Gold tăng riêng lẻ không làm lot giảm nếu khoảng SL giữ nguyên. Lot floor phụ thuộc "
        "risk USD / khoảng SL / contract và bước 0,01 lot. JSON có số lượt bị floor và cả reference "
        "150 USD lẫn lot thực của standalone; không gộp tài khoản chồng lấn thành số trade độc lập.","",
        "## 3. Bốn cột 105 cửa sổ và payout mô phỏng","",
        "V16_MULTI = A G2 vì không có sleeve đủ chuẩn. Cột 2 và 4 dùng cùng ledger strict có hash; "
        "không chạy lặp một portfolio giống hệt để tạo cảm giác có thêm chiến lược. "
        "Cột 1 reuse ledger V15 CUSHION nguyên vẹn. 66/72 starts cũ hoàn tất nhờ dùng giá đến "
        "13/10/2026, không phải hoàn tất toàn bộ trong Development.",""]
    lines+=table(["Order/phí","Cột","P1/105","Cả 2/105","Cả 2 recent/33","Median tháng","Daily %","Static %","Breach"],[
        [r["order"]+"/"+r["cost"],r["column"],r["phase1"],r["funded"],r["recent_33"]["funded"],
         None if r["median_months"] is None else round(r["median_months"],2),
         round(r["worst_daily"],4),round(r["worst_static"],4),r["breaches"]]
        for r in s["comparison"]])
    lines+=["", "Median chỉ tính cửa sổ hoàn tất; chưa hoàn tất vẫn censored và có mặt trong mẫu. "
        "2026 là YTD đến 13/10. Cửa sổ gần có ít thời gian hơn, tỷ lệ này không phải xác suất pass độc lập.",""]
    lines+=table(["Order/phí","Cột","Post-challenge count","Post-challenge USD (chồng lấn)","Standalone count","Standalone USD"],[
        [r["order"]+"/"+r["cost"],r["column"],r["payout_count_windows"],round(r["payout_windows_usd"],2),
         r["standalone_payout_count"],r["standalone_payout"]] for r in s["comparison"]])
    lines+=["", "Các khoản payout là số mô phỏng trước phí challenge/retry/vận hành. "
        "Không cộng các starts chồng lấn thành thu nhập, không phải tiền đã rút thật. "
        "Không suy risk thấp một đoạn lịch sử thành an toàn chắc chắn của FTMO.","",
        "## 4. Kiểm toán, hiệu năng, lưu trữ và bước tiếp","",
        f"Auditor riêng kiểm **{s['scan_audit']['counts']['endpoint_cash_legs']:,} endpoint cash calculations**, "
        f"**{s['scan_audit']['counts']['scalar_paths']:,} đường scanner** qua hai ordering. "
        f"Thêm **{sum(r['count'] for r in s['audits'] if r['kind']=='path'):,} A paths** và "
        f"**{sum(r['count'] for r in s['audits'] if r['kind']=='account'):,} account ledgers** mới. "
        "Cùng implementer/feed; độc lập phép tính và scalar traversal, không phải reviewer/người hay nguồn giá độc lập.",
        "",
        "Audit tìm 2 Gold DAY/P1 levels lệch 0,001 USD/oz do thiếu kiểm ô giá liền trước sau commission "
        "rounding. Sửa cùng cơ chế đã dùng cho US500; giữ failed audit và chạy lại đủ 29 SL-active cells. "
        "Activation, exit, cash và active protection của mọi A path không đổi; một unused level của A "
        "được ghi riêng, không bị coi là lệnh đã thay đổi. Không chọn lại subset từ lỗi này.",""]
    before=s["tests_before"]["total_wall_seconds"];after=s["tests_after"]["total_wall_seconds"]
    lines+=table(["Phép đo","Trước","Sau"],[
        ["Full four-runtime wall (giây)",round(before,3),round(after,3)],
        ["Tests / giữ IDs cũ",s["tests_before"]["tests"],f"{s['tests_after']['tests']} / 1126"],
        ["Base shard walls",s["tests_before"]["groups"]["base"]["shard_seconds"],
         s["tests_after"]["groups"]["base"]["shard_seconds"]]])
    lines+=["",f"Giảm wall {(before-after)/before*100:.1f}% trên phép đo này; dùng profile thật để cân "
        "hai shard của runner đã có, giữ process isolation, tất cả test IDs và 0 skip. "
        "Không thêm cache fixture dùng chung chỉ để tiết kiệm vài giây. Bản sau có các test V16 bổ sung, "
        "không gọi đó là benchmark cohort hoàn toàn giống nhau. Top15 timings giữ trong JSON.","",
        f"Smoke 10 fresh processes, đủ 78 tests/lượt: median/max wall "
        f"{s['smoke']['wall_median']:.3f}/{s['smoke']['wall_max']:.3f}s; 10/10 <0,80s: "
        f"**{s['smoke']['all_ten_below080']}**. Giữ mọi mẫu và outlier.",""]
    z=s["storage"]
    lines+=["",f"Inventory {z['inventoried_log_files']} log/stdout D/E ({z['inventoried_log_bytes']:,} bytes). "
        f"Nén {len(z['removed'])} console logs của các job đóng, {z['logical_removed_bytes']:,} bytes → "
        f"{z['archive_bytes']:,} bytes; giảm logic {z['logical_net_before_receipts']:,} bytes trước receipts. "
        "Đã extract và SHA từng member trước xóa bản gốc; mỗi đường cũ có `.v16-cold.json` chỉ archive/member/hash. "
        "Không xóa raw/tick/M1/column store/freeze/ledger/path hay package; không lặp purge V14/V15. "
        "Không claim dung lượng vật lý đã giải phóng.","",
        "Luồng dữ liệu: nguồn V14 giữ nguyên → A entry/SL tape cố định → clock G2 được đăng ký → "
        "hai đường M1 ordering + shared-gap stress → engine account cũ → scalar/Decimal audit → "
        "freeze commit trước đo chính sách mới trên giá 2024–2026. Scanner DAY dùng riêng Dev 2018–2023.",
        "",
        "**Khuyến nghị:** giữ V15 làm baseline nghiên cứu, gác G2 và không tăng risk/chọn thêm biến thể "
        "để đạt chỉ tiêu. Nút thắt còn lại là tín hiệu có R-velocity đủ cao trên đường giá kiểm được, "
        "không phải thiếu engine hoặc cần nới chuẩn. Một chiến dịch mới cần cơ chế/nguồn dữ liệu mới có "
        "lý do rõ và budget riêng; các failed attempts hiện tại giữ nguyên.",
        "",
        "Hậu kiểm: không biến quote absence thành continuity; dùng lịch biết trước, không hindsight "
        "outage exits; sửa lỗi arithmetic bằng regression rồi đối soát delta; reuse ledger chỉ sau parity; "
        "nén log có restore proof trước thay vì xóa nguồn. Không cần thêm skill trùng với source-transformations/"
        "qualification/evidence-continuity đang có.",
        "",
        f"Private evidence `{JOB}`; JSON báo cáo <1 MiB. PR #95 giữ mở, 3 checks trên đúng HEAD và "
        "CI quant IDs được đối soát bằng artifact tải về, receipt `ci-exact-head-reconciliation.json` "
        "ghi sau push. Không sửa HEAD chỉ để tự nhét hash CI vào cùng commit.",
        "",
        "VI Dubber WIP và Trader pin giữ nguyên. Không broker, deploy, provider download, "
        "Astra hay memory update; chưa owner handover/shadow/demo/target-account execution validation.",""]
    REPORT.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("smoke","collect"))
    globals()[p.parse_args().stage]()
