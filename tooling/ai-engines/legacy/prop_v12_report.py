"""Compact V12 report: paired diagnostics never stand in for a complete portfolio."""
from pathlib import Path
from collections import Counter
import json
import numpy as np
from prop_campaign_source import ROOT
from prop_v10_source import sha

JOB=ROOT/"sl-active-ensemble-v12-20261115"
FINAL=JOB/"cent-corrected"
V11=ROOT/"ensemble-and-storage-v11-20261115"
OUT=Path("planning/research/SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115")


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def table(headers,rows):
    return ["| "+" | ".join(headers)+" |","|"+"|".join("---" for _ in headers)+"|"]+[
        "| "+" | ".join(str(value).replace("|",r"\|") for value in row)+" |" for row in rows]


def compact(row):
    return {k:row[k] for k in ("id","asset","family","mode","horizon","raw","priced","admitted",
                               "path_unknown","annual","clusters","economics","reasons","dual_positive","exits")}


def run():
    discovery=read(FINAL/"discovery.json");rows=discovery["rows"]
    decision=read(FINAL/"decision.json")
    if decision["passed"]:
        raise ValueError("No-Go report cannot close a passing ensemble")
    old=read(V11/"clock-corrected/component-atlas.json")
    lookup={r["id"]:r for r in rows}
    oracle=read(FINAL/"independent-audit.json")
    if not oracle["passed"]:
        raise ValueError("do_not_publish_unresolved_accounting")
    tests=read(JOB/"tests-final-matrix.json")
    storage={a:read(JOB/f"storage-{a}-final.json") for a in ("D","E")}
    archives=read(JOB/"archive-members.json");dup=read(JOB/"duplicate-files-crosspath.json")
    directories=read(JOB/"duplicate-directory-candidates.json")
    duals=[compact(r) for r in rows if r["dual_positive"]]
    repair=[compact(r) for r in rows if r["reasons"]==["PATH_OR_ENDPOINT_INCOMPLETE"]]
    registry=[]
    for r in old["dual_positive"]:
        registry.append(dict(id=r["id"],asset=r["asset"],family=r["family"],
            V11_SYM_R=r["economics"]["SYM"]["net_R"],V11_annual=[
                dict(year=a["year"],admitted=a["admitted"],SYM_R=a["economics"]["SYM"]["admitted_net_R"])
                for a in r["annual"]],P0=compact(lookup[r["id"]+"|P0"]),P1=compact(lookup[r["id"]+"|P1"])))
    # A fixed reference only: the six V11 sleeves, with a common cohort for all three views.
    old0=np.load(JOB.parent/"enterprise-alpha-v10-20261115/raw-matrix-reviewed.npz")
    old1=np.load(V11/"clock-corrected/native-hourly-matrix.npz")
    matrices={a:np.load((FINAL if a=="US500" else JOB)/f"{a}-path-matrix.npz")
              for a in ("XAUUSD","EURUSD","GBPUSD","AUDUSD","US500")}
    paired={y:dict(year=y,n=0,V11_R=0.,P0_R=0.,P1_R=0.,P0_stopped_previous_winners=0,
                   P0_losses_reduced=0) for y in range(2018,2024)}
    reference=[]
    for identity in old["decision"]["selected"]:
        j=next(j for j,r in enumerate(old["rows"]) if r["id"]==identity)
        oldmat=old0 if j<544 else old1;k=j if j<544 else j-544
        p0,p1=lookup[identity+"|P0"],lookup[identity+"|P1"]
        m=matrices[p0["asset"]];cell=p0["source_cell"]
        assert np.array_equal(oldmat[f"{k}:at"],m[f"{cell}:at"])
        mask=oldmat[f"{k}:ok"] & (m[f"{cell}:ratio"]<=.15)
        mask &= m[f"{cell}:P0:valid"] & m[f"{cell}:P1:valid"]
        before=oldmat[f"{k}:SYM:net_R"]
        after0,after1=(m[f"{cell}:{mode}:SYM:net_R"] for mode in ("P0","P1"))
        years=m[f"{cell}:years"]
        reference.append(dict(id=identity,raw=p0["raw"],P0_priced=p0["priced"],P1_priced=p1["priced"],
                              paired=int(mask.sum()),P0_partial_SYM_R=p0["economics"]["SYM"]["net_R"],
                              P1_partial_SYM_R=p1["economics"]["SYM"]["net_R"]))
        for year,row in paired.items():
            use=mask & (years==year)
            row["n"]+=int(use.sum())
            row["V11_R"]+=float(before[use].sum())
            row["P0_R"]+=float(after0[use].sum());row["P1_R"]+=float(after1[use].sum())
            row["P0_stopped_previous_winners"]+=int((use & (before>0) & (after0<0)).sum())
            row["P0_losses_reduced"]+=int((use & (before<0) & (after0>before)).sum())
    best=[]
    f5=[]
    coverage=[]
    for asset in ("XAUUSD","EURUSD","GBPUSD","AUDUSD","US500"):
        group=[r for r in rows if r["asset"]==asset]
        clock_bad=gap_bad=0
        for r in group:
            m=matrices[asset];cell=r["source_cell"];entry=m[f"{cell}:entry_at"]
            weekday=(entry//86400000+3)%7
            invalid=(m[f"{cell}:deadline"]<entry) | (m[f"{cell}:natural"]<=0)
            invalid |= (weekday>=5) | ((weekday==4)&(entry%86400000>=73800000))
            clock_bad+=int(invalid.sum())
            gap_bad+=int(m[f'{cell}:{r["mode"]}:path_gap'].sum())
        coverage.append(dict(asset=asset,path_cells=len(group),dual_positive=sum(r["dual_positive"] for r in group),
            complete_nonempty_cells=sum(r["complete_path"] and r["raw"]>0 for r in group),
            economic_but_path=sum(r["reasons"]==["PATH_OR_ENDPOINT_INCOMPLETE"] for r in group),
            raw_cell_events=sum(r["raw"] for r in group),priced_cell_events=sum(r["priced"] for r in group),
            clock_or_natural_stop_invalid_events=clock_bad,path_gap_flag_events=gap_bad))
        for mode in ("P0","P1","P2"):
            candidates=[r for r in group if r["mode"]==mode and all(c["priced"]>0 for c in r["clusters"])]
            winner=max(candidates,key=lambda r:(min(c["net"]["SYM"]["raw"] for c in r["clusters"]),r["id"]))
            best.append(compact(winner))
        candidates=[r for r in group if r["family"]=="F5" and all(c["priced"]>0 for c in r["clusters"])]
        f5.append(compact(max(candidates,key=lambda r:(min(c["net"]["SYM"]["raw"] for c in r["clusters"]),r["id"]))))
    artifacts={}
    for folder,names in ((JOB,("registration.json","discovery.json","decision.json","independent-audit.json",
                               "timings.json","archive-members.json","duplicate-files-crosspath.json",
                               "duplicate-directory-candidates.json",
                               "storage-D-final.json","storage-E-final.json","tests-final-matrix.json",
                               "source-path-audit.json","V11-exact-composer.py")),
                         (FINAL,("registration.json","discovery.json","decision.json","independent-audit.json",
                                 "US500-path-matrix.npz","source-path-audit.json","timings.json",
                                 "oracle-logging-failure.json"))):
        for name in names:
            p=folder/name;artifacts[str(p.relative_to(JOB))]=dict(path=str(p),sha256=sha(p))
    result=dict(schema="SL-ACTIVE-ENSEMBLE-V12-v1",status="NO_QUALIFIED_ENSEMBLE",
        research_status=["DATA_PATH_INCOMPLETE","PROP_UNMEASURED"],
        parent_merge="2175685",trials=2888,base_cells=1264,F5_cells=120,technical_attempts=2,
        registry_42=registry,dual_positive=duals,economic_but_path=repair,top_by_asset_mode=best,
        F5_by_asset=f5,coverage=coverage,paired_V11_six=list(paired.values()),V11_reference=reference,
        decision=decision,oracle={k:v for k,v in oracle.items() if k not in ("sample_trades","failures")},tests=tests,storage={
            a:dict(readable=storage[a]["groups"]["/"],observed_utc=storage[a]["observed_utc"],errors=storage[a]["errors"])
            for a in storage},archives=dict(containers=len(archives["archives"]),
                statuses=dict(Counter(r["status"] for r in archives["archives"])),market_matches=archives["matches"],
                extracted=False,new_M1_admitted=False),
        duplicates={k:v for k,v in dup.items() if k!="verified_identical_file_pairs"},
        duplicate_identical_pairs=len(dup["verified_identical_file_pairs"]),deleted_in_V12=False,
        directory_candidate_pairs=len(directories["directory_candidates"]),
        duplicate_directory_examples=directories["directory_candidates"][:10],
        initial_timing=read(JOB/"timings.json"),correction_timing=read(FINAL/"timings.json"),artifacts=artifacts,
        validation_2024_2026_opened=False,clean_OOS=False,actual_account_replayed=False,
        FTMO_challenge=None,funded_payouts=None,prop_status="PROP_UNMEASURED",
        unknowns_are_not_zero=True,independent_person_review=False)
    OUT.with_suffix(".json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# V12 — đo SL thật trên đường giá, F5 và chất lượng dữ liệu","",
        "**Đã xây kernel SL-active, quét đủ 2.888 trường hợp; chưa có ensemble đủ điều kiện Challenge.**",
        "Có 28 path cells dương hai cụm trên phần đo được, gồm 20 F1–F4 và 8 F5.",
        "Có 19 trường hợp đạt các cổng kinh tế trên phần có đường giá nhưng còn thiếu coverage.",
        "Không ghép các phần thiếu thành portfolio đủ chuẩn, không mở giá 2024–2026, không mô phỏng payout.","",
        "PR #90 đã merge `2175685`, nhánh V11 đã xóa. V12 ở `codex/sl-active-ensemble-v12`;",
        "PR mới dự kiến #91 chờ owner, không tự merge. Giữ Trader pin và WIP VI Dubber.","",
        "## 1. Kernel, accounting và kiểm chứng","",
        "P0 giữ natural SL đến horizon; P1 kích hoạt từ net +1,5R theo SYM rồi bảo vệ net +0,15R",
        "tại lúc kích hoạt; swap tương lai có thể làm giảm mức net đó. Stop mới chỉ có hiệu lực từ",
        "bar kế tiếp. P2 chỉ dùng TP 3R cho F5; không search 2,5R/3R rồi chọn bản đẹp hơn.",
        "BUY thoát Bid, SELL thoát Ask; cùng bar chạm stop/TP thì stop trước. Gap qua stop khớp",
        "open bất lợi hơn, cộng slippage; không ép lỗ lớn về đúng −1R.",
        "Không đọc extrema của bar bắt đầu tại horizon, không dùng nến H1 chưa hoàn thành tại hạn 20:30.","",
        "64-bar extrema blocks tìm vùng có first hit, rồi xác định bar chính xác. Không Numba/new provider.",
        f'Kernel lần quét đầy đủ: **{result["initial_timing"]["kernel_total"]:.2f}s**; toàn pipeline '
        f'**{result["initial_timing"]["total"]:.2f}s**, gồm IO/source hashing, F5, profiles và ghi matrix.',
        "US500 load/proof là phần IO lớn; không gọi 36,9s là thời gian toàn bộ chiến dịch.",
        "Lần sửa cent chỉ chạy lại US500; các tài sản khác reuse đúng matrix/hash, không rerun tài chính.","",
        "### Sai khác auditor đã phát hiện và sửa","",
        "Lần đầu oracle phát hiện 562 sai khác US500: gross theo giá 0,001 point cần làm tròn",
        "tới cent theo từng leg trước khi cộng phí, và P1 phải tìm đúng giá quote trên plateau cent.",
        "Ví dụ +0,805 USD gross → +0,81 −2,50 phí = −1,69; làm tròn raw net −1,695 cho −1,70.",
        "Giữ attempt đầu và oracle fail; protocol correction commit `c88cafb` trước outcome mới.",
        "Phí danh nghĩa, signals, stops, horizon và gates không đổi.",
        "Đây là reference 1 lot. Khi sizing/lot grid đổi, phải replay theo quantity; không nhân R thành cash/payout.","",
        f'Oracle cuối: **{oracle["cash_cost_views"]:,} cost views tới cent**, '
        f'**{oracle["scalar_path_checks"]:,} first-hit checks**, 0 discrepancy.',
        "Auditor tự decode accepted inputs, dùng Decimal và lịch/fee formulas riêng; không import",
        "Quant Core PnL/DD. Bốn tài sản giữ nguyên; US500 chỉ được audit sau correction.",
        "Cùng implementer và cùng feed, không là independent person/feed review.",
        "Gold/EUR vẫn Ask proxy. M1 extrema và H1 conservative bars chưa phải broker-native tick fills.",
        "Cost/holiday assumptions giữ protocol V11/V12; chưa có target-native FTMO spec/news admission.",
        "Một lần audit sau correction dừng vì trùng tên counter trong log; đã sửa logging, giữ receipt",
        "và log fail, chỉ chạy lại auditor. Không chạy lại tài chính vì lỗi log này.",
        "Prague balance anchor/DST, funding, static floor và first-hit có fixtures riêng; **chưa có",
        "continuous account đủ điều kiện để audit daily/static prop loss trên dữ liệu thật**.","",
        f'Full Windows: **{tests["tests"]}/{tests["tests"]}**, giữ đủ **1.048 IDs cũ**, '
        f'thêm {tests["new_tests"]}, 0 skip. Smoke **{tests["smoke"]["tests"]} tests / '
        f'{tests["smoke"]["seconds"]:.3f}s**.',
        "Giữ các smoke attempts chậm ban đầu. Đổi scalar test từ truy cập NumPy từng phần tử sang",
        "Python lists, giữ nguyên 400 query cases; không bỏ test để ép timing. Timings là các lượt quan sát.","",
        "## 2. SL có cứu kết quả V11 và F5 có bù được năm yếu?","",
        "V11 đo raw endpoint; đó là screen đã đăng ký, không là lỗi giả sử bot không có SL.",
        "V12 là trial exit mới do owner duyệt. Stop vừa cắt lỗ vừa có thể loại lệnh sau đó hồi phục.",
        "Không mặc định −4R/−8R là nguyên nhân đã được chứng minh cho toàn bộ năm 2021/2022.","",
        "1.264 cells cũ × P0/P1 = 2.528; F5 5 assets × H1/H4 × N=3/5/10 ×4 horizons ×3 modes",
        "=360; tổng 2.888. Direction BOTH; ADX14 ≤25; wick +0,1 ATR; tối đa 1 event/ngày/recipe.",
        "F5 là phá biên nhiều ngày rồi đóng lại trong biên; không tự động được xem là counter-cyclical edge.",""]
    lines+=table(["Asset","Path cells","Dương 2 cụm (phần đo được)","Chỉ còn vướng path","Đủ path & có tín hiệu","Priced /raw cell-events"],
        [[r["asset"],r["path_cells"],r["dual_positive"],r["economic_but_path"],r["complete_nonempty_cells"],
          f'{r["priced_cell_events"]:,}/{r["raw_cell_events"]:,} ({r["priced_cell_events"]/r["raw_cell_events"]:.1%})'] for r in coverage])
    lines+=["","Số liệu trên là cell-records; P0/P1/P2 cùng recipe không là các edge độc lập.",
        "Invalid không đồng nghĩa mọi trường hợp đều là gap: có cả hạn DAY trước entry, entry sau",
        "Friday flat hoặc natural stop không hợp lệ. Các flag có thể trùng nhau; JSON tách counter.",
        "V11 có 42 endpoint cells dương; V12 F1–F4 còn 8 P0 +12 P1 dương trên phần có path.",
        "F5 thêm 3 P0 +3 P1 +2 P2 dương, đều EURUSD; chưa có F5 đủ coverage.",
        "Bản JSON có toàn bộ 42 hồ sơ V11, sáu năm, P0/P1, sample count, phí, exits và nguyên nhân dừng.","",
        "### Đối chứng 6 nhánh V11 — so trên cùng các lệnh có thể đo cả ba cách","",
        "Chỉ giữ common cohort có endpoint V11, P0 và P1 cùng xác định và qua phí. Đây là diagnostic",
        "có điều kiện, không là portfolio 6 năm đầy đủ; các lệnh giữ lâu dễ gặp gap hơn nên censoring",
        "có thể làm mẫu này thiên về lệnh bị stop. Không dùng bảng này để tự kết luận toàn bộ SL có edge/không edge.",
        "SYM, risk 1R/tín hiệu, chưa sizing/shared-account constraints. US500 có thêm correction cent đã nêu.",""]
    lines+=table(["Năm","N common","V11 endpoint R","P0 R","P1 R","Lệnh lãi endpoint bị P0 cắt lỗ","Lệnh lỗ được P0 giảm lỗ"],
        [[a["year"],a["n"],f'{a["V11_R"]:+.3f}',f'{a["P0_R"]:+.3f}',f'{a["P1_R"]:+.3f}',
          a["P0_stopped_previous_winners"],a["P0_losses_reduced"]] for a in paired.values()])
    lines+=["","Toàn bộ V11 cũ là +59,421R trên 516 admissions; không đặt tổng đó cạnh P0/P1 thiếu path",
        "rồi gọi chênh lệch là tác động thuần của SL. Chi tiết full/paired counts của từng sleeve trong JSON.","",
        "### Các nhánh dẫn đầu theo từng asset/mode, vẫn chỉ là chẩn đoán","",
        "Xếp theo min(raw R hai cụm), cần có giá ở cả hai cụm; không lấy cohort rỗng 0R làm best.",
        "Sáu giá trị năm dưới là admitted SYM R theo thứ tự 2018/19/20/21/22/23, chỉ phần xác định.",
        "Không dùng thứ hạng này để đổi composer hoặc ghép các mẫu bị thiếu.",""]
    lines+=table(["Asset","Mode","ID","Net R sáu năm (partial)","Path đủ /raw"],
        [[r["asset"],r["mode"],f'`{r["id"]}`',
          " / ".join(f'{a["models"]["SYM"]["net_R"]:+.2f}' for a in r["annual"]),
          f'{r["priced"]}/{r["raw"]}'] for r in best if r["mode"] in ("P0","P1")])
    lines+=["",
        "### F5 theo từng asset — xếp hạng chẩn đoán, chưa là ứng viên được tuyển",""]
    lines+=table(["Asset","Cấu hình có min(cluster R) cao nhất","18–20 raw R","21–23 raw R","Path đủ /raw","Trạng thái"],
        [[r["asset"],f'`{r["id"]}`',*[f'{c["net"]["SYM"]["raw"]:+.3f}' for c in r["clusters"]],
          f'{r["priced"]}/{r["raw"]}',", ".join(r["reasons"])] for r in f5])
    lines+=["","Bảng best theo từng mode/asset và đủ sáu năm nằm trong JSON. Không lấy available-only",
        "positive mean để promote: phải sửa path bằng nguồn có chứng cứ, giữ nguyên rule rồi mới kết luận.",
        "19 trường hợp chỉ còn vướng path gồm 13 Gold và 6 EURUSD; đây là danh sách cần xác minh dữ liệu,",
        "không phải 19 chiến lược đã chứng minh có edge.","",
        "## 3. Ensemble, validation 9 năm và Challenge/payout","",
        "Composer vẫn medoid/equal-risk; threshold V12 cố định 0,25, default 0,30 giữ V11 semantics.",
        "Exact V11 composer source lưu từ Git; không sửa historical pins. Graph ghép cùng asset/family",
        "nếu correlation cao hoặc trùng quyết định, không thử mọi subset/weights hoặc ép chọn F5.",
        "Không có component đồng thời đạt kinh tế và coverage, nên **K=0, composition=None**. Chưa hình thành ensemble để",
        "đo thật 5/6 năm dương hoặc ex-best-year >0; không diễn giải các giá trị rỗng thành hiệu suất 0.",""]
    lines+=table(["Phạm vi","Trạng thái"],
        [["2018–2023","Đã đo SL-active từng cell, còn path gaps; chưa có qualified ensemble"],
         ["2024","Không mở giá trong V12; không có annual portfolio performance"],
         ["2025","Không mở giá trong V12"],
         ["2026 YTD đến 13/10/2026","Không mở giá trong V12"],
         ["Monthly FTMO 2-Step /Standalone Funded50k","Không chạy — gate Dev chưa đạt"],
         ["Pass rate /tháng hoàn tất /payout count /payout USD","N/A, không phải 0"],
         ["Worst Daily Loss /Static Loss của tài khoản thật","PROP_UNMEASURED"]])
    lines+=["","2024–2026 từng có exposure các chiến dịch khác: chưa đo cho V12 không biến chúng thành clean OOS.",
        "Không tăng risk, hạ gate, thêm filter/subset hoặc chạy validation để cứu outcome.","",
        "## 4. Storage D/E, nguồn nén và việc còn thiếu",""]
    lines+=table(["Scope","Logical bytes đọc được","Files","Folders","Timestamp UTC"],
        [[a,storage[a]["groups"]["/"]["bytes"],storage[a]["groups"]["/"]["files"],
          storage[a]["groups"]["/"]["folders"],storage[a]["observed_utc"]] for a in ("D","E")])
    lines+=["","V11 đã xóa đúng 119,79 GB; **V12 không xóa thêm hoặc nén raw/WIP**. Snapshot là logical readable",
        "bytes ở thời điểm ghi, không allocated NTFS/free space. Hai VI permission gaps vẫn unknown.","",
        f'Đã kiểm metadata {len(archives["archives"]):,} containers: '
        f'{dict(Counter(r["status"] for r in archives["archives"]))}.',
        "Có 5 member matches: 3 ảnh GBP/US500 và 2 GBPUSD D1 sample của LEAN. Không nguồn M1 đầy đủ",
        "được admission mới; GBP/AUD vẫn H1. Gzip/zstd không phải archive có index member thì giữ",
        "unsupported, không giải nén/đọc payload validation để tìm kiếm. Không tuyên bố đã chứng minh",
        "toàn bộ E không có thêm dữ liệu. Full container list, exclusions và errors ở private artifacts.","",
        f'Cross-path code/docs: {dup["checked_pairs"]:,} candidate pairs, '
        f'{len(dup["verified_identical_file_pairs"]):,} cặp byte-identical, '
        f'{dup["bytes_hashed"]:,} bytes đã hash.',
        "Chỉ code/docs 4KB–2MB, budget 2.000 pairs; không raw data. Backup cố ý giống source vẫn có thể",
        "cần giữ. File giống nhau chưa chứng minh cả thư mục dư hoặc cho phép xóa source đang được pin.","",
        f'Đã nhóm thành {len(directories["directory_candidates"]):,} cặp thư mục có file giống trong mẫu.',
        "Các ví dụ lớn là thư mục thư viện Pygments trong uv cache/venv và bản backup; chưa chứng minh",
        "toàn bộ cây byte-identical hoặc không còn consumer. Danh sách đầy đủ ở private JSON, không tự xóa.","",
        "**Khuyến nghị:** chưa mua Challenge. Ưu tiên xác minh đường giá của danh sách 19 trường hợp",
        "giữ nguyên rule, nhất là EURUSD F5 và Gold; chưa mở thêm grid hay tối ưu weights/risk.",
        "Nếu không tìm được nguồn đủ chứng cứ thì giữ inconclusive, không gọi đó là economic fail toàn bộ.",
        "Việc này cần scope/source-path budget tiếp theo; V12 chốt tại các gate đã đăng ký.","",
        "Data flow: frozen source/index →observed bar paths →SL/P1/TP + cost legs →coverage/economics",
        "→component gate →stop. Account/validation chỉ mở sau gate và freeze đủ.",
        f'Private job `{JOB}`. JSON chứa registry, paired cohorts, source/hash, failed-attempt history,',
        "counts và oracle. Delivery receipt ghi PR/HEAD/CI thực tế sau bàn giao; không tự merge PR mới."]
    OUT.with_suffix(".md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    decision_out=dict(schema="V12-DECISION-v1",passed=False,K=0,composition=None,
        status="NO_QUALIFIED_ENSEMBLE",dual_positive_cells=len(duals),economic_but_path=len(repair),
        research_status=["DATA_PATH_INCOMPLETE","PROP_UNMEASURED"],
        validation_2024_2026="NOT_OPENED",lifecycle="CANCELED_FAILED_DEV_GATE",
        prop_status="PROP_UNMEASURED",independent_person_review=False,artifacts=artifacts)
    OUT.with_name("SL-ACTIVE-ENSEMBLE-V12-DECISION-20261115.json").write_text(
        json.dumps(decision_out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(dict(report=str(OUT.with_suffix(".md")),bytes=OUT.with_suffix(".json").stat().st_size))


if __name__=="__main__":
    run()
