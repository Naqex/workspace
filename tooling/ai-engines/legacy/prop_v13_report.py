"""Publish compact V13 evidence; no financial rerun or validation-price access."""
from collections import Counter
from pathlib import Path
import json
import numpy as np
from prop_v13_campaign import JOB, V12, PROTOCOL, read
from prop_v10_source import sha

OUT=Path("planning/research/PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115")


def table(headers, rows):
    return ["| "+" | ".join(headers)+" |","|"+"|".join("---" for _ in headers)+"|"]+[
        "| "+" | ".join(str(v).replace("|",r"\|") for v in row)+" |" for row in rows]


def run():
    discovery, decision = (read(JOB/n) for n in ("discovery.json","decision.json"))
    if decision["passed"]:
        raise ValueError("This closure writer requires the registered failed Development gate")
    audit=read(JOB/"independent-audit.json")
    if not audit["passed"]:
        raise ValueError("Unresolved financial audit")
    storage=read(JOB/"storage-summary-final.json")
    dedup=read(JOB/"directory-dedup.json")
    tests=read(JOB/"tests-final-matrix.json")
    smoke=read(JOB/"smoke-performance-final.json")
    native_probe=read(JOB/"native-gap-probe.json")
    rows=discovery["rows"]
    forensic=read(JOB/"forensics.json")["rows"]
    gaps={}
    by_case=[]
    matrices={a:np.load(JOB/f"{a}-path-matrix.npz") for a in ("XAUUSD","EURUSD")}
    for number,(row,f) in enumerate(zip(rows,forensic),1):
        counts=Counter()
        unique={}
        for event in f["events"]:
            for gap in event["gaps"]:
                key=(row["asset"],gap["before"],gap["after"])
                gaps[key]=gap;unique[key]=gap
        for gap in unique.values(): counts.update(gap["minutes_by_kind"])
        z=matrices[row["asset"]];j=row["source_cell"];prefix=f"{j}:{row['mode']}:"
        invalid=[]
        for i in np.flatnonzero(~z[prefix+"valid"]):
            entry,at,deadline=(int(z[f"{j}:{k}"][i]) for k in ("entry_at","at","deadline"))
            why=[]
            if deadline<entry:why.append("ENTRY_AFTER_DAY_DEADLINE")
            if entry-at>60000:why.append("ENTRY_MORE_THAN_60S_AFTER_DECISION")
            if (entry//86400000+3)%7>=5:why.append("WEEKEND_ENTRY")
            if (entry//86400000+3)%7==4 and entry%86400000>=73800000:why.append("ENTRY_AFTER_FRIDAY_FLAT")
            invalid.append(dict(event=int(i),entry=entry,decision=at,deadline=deadline,reasons=why))
        by_case.append(dict(label=f"C{number:02d}",**row,original_block_minutes=dict(counts),
                            original_gap_count=len(unique),remaining_invalid_events=invalid))
    unique_minutes=Counter()
    for gap in gaps.values():unique_minutes.update(gap["minutes_by_kind"])
    focus=[r for r in by_case if r["only_path_before"]]
    files=["registration.json","session-calendar.json","forensics.json","discovery.json","decision.json",
           "independent-audit.json","timings.json","storage-summary.json","storage-summary-final.json","directory-dedup.json",
           "tests-final-matrix.json","smoke-performance.json","smoke-performance-final.json",
           "smoke-parallel-comparison.json","primary-sources/receipts.json",
           "native-gap-probe-registration.json","native-gap-probe.json",
           "XAUUSD-path-matrix.npz","EURUSD-path-matrix.npz",
           "storage-D-before.json","storage-D-after.json","storage-E-before.json","storage-E-after.json"]
    artifacts={n:dict(path=str(JOB/n),sha256=sha(JOB/n),bytes=(JOB/n).stat().st_size) for n in files}
    totals=dict(cases=28,focus_cases=19,focus_raw=sum(r["raw"] for r in focus),
        focus_priced=sum(r["priced"] for r in focus),old_priced=sum(r["old_priced"] for r in rows),
        new_priced=sum(r["priced"] for r in rows),raw=sum(r["raw"] for r in rows),
        old_unresolved=sum(r["raw"]-r["old_priced"] for r in rows),
        scenario_components=sum(r["admitted_component"] for r in rows),
        strict_source_verified_components=sum(r["source_verified_component"] for r in rows),
        unique_crossed_gaps=len(gaps),unique_missing_minutes_by_kind=dict(unique_minutes),
        gap_classes=dict(Counter("SCHEDULED_ONLY" if not g["source_uncertain"] else
            "SCHEDULED_PLUS_UNCLASSIFIED" if len(g["minutes_by_kind"])>1 else "UNCLASSIFIED_ONLY"
            for g in gaps.values())))
    report=dict(schema="V13-results-v1",decision=decision,totals=totals,cases=by_case,
        research_status=["CADENCE_OR_SAMPLE_SHORTFALL","DATA_PATH_INCOMPLETE","PROP_UNMEASURED"],
        source_path_certified=False,parent_selection_cells=2888,
        independent_audit={k:v for k,v in audit.items() if k not in ("examples","failures")},
        storage_summary=storage,dedup_summary={k:v for k,v in dedup.items() if k not in ("trees","pairs")},
        tests=tests,smoke=smoke,artifacts=artifacts,
        native_gap_probe={k:v for k,v in native_probe.items() if k!="rows"},
        validation_prices_opened=False,actual_account_replayed=False,
        disclosure="all profits are Development next-quote scenario estimates at reference risk, not payouts")
    OUT.with_suffix(".json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    OUT.with_name("PATH-RESOLUTION-AND-DEDUP-V13-DECISION-20261115.json").write_text(
        json.dumps(decision,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# V13 — Đã định giá lại; chưa đủ điều kiện mở Validation","",
        "**No-Go ở Development theo cổng đã đăng ký.** 19/19 cấu hình trọng tâm được định giá",
        f"đủ {totals['focus_priced']:,}/{totals['focus_raw']:,} lượt theo mô hình quote kế tiếp. Tổ hợp",
        "cơ học còn 3 nhánh, SYM +50,232R / ASYM +52,386R trong 2018–2023,",
        "nhưng 2018 có 43, 2019 có 47 tín hiệu, dưới sàn 50 **mỗi năm**.",
        "Không thay cổng sau khi thấy kết quả. 2024–2026 vẫn đóng; không chạy lifecycle 9 năm.",
        "Giá trị dương này có điều kiện: không có component nào chứng minh đủ đường giá nguồn.","",
        "[Protocol](PATH-RESOLUTION-AND-DEDUP-V13-PROTOCOL-20261115.md) freeze `5d0f7a5`;",
        "code trước outcome `edd5e46`. PR #91 merge `ad362ea`; branch V12 đã xóa.",
        f"Private job: `{JOB.as_posix()}`. Compact JSON cùng tên giữ IDs, annuals và SHA256.","",
        "## 1. Pháp y 28 cấu hình và 19 trường hợp trọng tâm","",
        f"V12: {totals['old_priced']:,}/{totals['raw']:,} lượt định giá; V13: "
        f"{totals['new_priced']:,}/{totals['raw']:,}. Khôi phục 450 lượt bị chặn.",
        "26/28 cells định giá toàn bộ; 2 EURUSD F5 H1/n10 còn 7 lượt sai clock mỗi cell:",
        "entry sau hạn đóng DAY; một lượt còn chậm qua cuối tuần. Không sửa tín hiệu để cứu chúng.",
        "Các số này đếm lượt theo cấu hình; nhiều mode dùng lại cùng tín hiệu, không phải mẫu độc lập.","",
        "28 cells đã được chọn sau khi xem V12 trên 2.888 cells. V13 không reset lịch sử",
        "lựa chọn này; positive point estimate không phải kiểm định edge sau multiple testing.","",
        f"Trong các đường V12 bị chặn: {len(gaps)} khoảng nghỉ/gap riêng, gồm 91 khoảng",
        "chỉ là giờ nghỉ đã khai báo; 24 khoảng sát giờ nghỉ còn thiếu 1–2 phút ngoài lịch;",
        "352 khoảng chỉ có phút nguồn không được xác minh. Tổng 434 phút chưa rõ + 6.900",
        "phút nghỉ hàng ngày của vàng. Không có gap lễ/early-close chưa khai báo trong chính",
        "cohort bị chặn này. Lịch 2018–2021 đã có guard từ V8; giả thuyết thiếu lịch là nguyên",
        "nhân chính không được số liệu ủng hộ. EURUSD không có giờ nghỉ CME hàng ngày.","",
        "Nguồn FTMO lịch sử truy cập trực tiếp bị TLS timeout; MT5 URL thử trả 404.",
        "Receipt được giữ. Giữ lịch guard đã đăng ký cùng correction 31/12/2021",
        "(normal hours; vẫn giữ guard bảo thủ 16:58), không gọi lịch này là FTMO-certified.","",
        "**Cách xử lý:** giữ nguyên entry/SL/mode; stop vượt gap khớp tại open bất lợi cộng",
        "phí stress. Hạn thoát thiếu quote chờ open kế tiếp; deadline trong giờ nghỉ vàng",
        "chờ giờ mở lại và tính swap. Guard holiday/Friday khóa từ trước, không lùi đến",
        "last quote bằng hindsight. Endpoint chỉ dùng open; không đọc high/low tương lai.",
        "P1 chỉ có hiệu lực từ bar sau trigger. Stop qua open ghi nhận ngay thời điểm open.","",
        "**Giới hạn:** nếu thiếu một phút giữa phiên, giá có thể chạm SL rồi hồi ngay trong",
        "phút đó. Open kế tiếp không chứng minh điều ngược lại và không là worst-case bound.",
        "Auditor xác nhận mô phỏng khớp hợp đồng; không tạo ra dữ liệu đã mất.","",
        "Kiểm thêm native tick cache, chỉ các giờ Development liên quan: 376 gap chưa rõ,",
        f'{native_probe["counts"].get("NO_QUOTES_IN_ADMITTED_TICK_HOURS",0)} gap có đầy đủ giờ tick đã admission '
        "và không có quote bên trong; "
        f'{native_probe["counts"].get("NO_ADMITTED_TICK_HOUR",0)} gap chưa có native tick hour trong manifest.',
        f'Đọc {native_probe["native_hours_decoded"]} giờ tick; không có trường hợp phát hiện tick '
        "bên trong gap M1 ở phần có giờ được admission.",
        "Không download thêm, không thay source/matrices hoặc chạy lại tài chính. No-quote",
        "trong cache được admission vẫn không chứng nhận feed broker chưa từng có giá khác.","",
        "`*` là 19 trường hợp chỉ vướng path ở V12. Cột phút = chưa xác minh / nghỉ đã khai báo.",
        "Full Config ID giữ cả asset/recipe/horizon/mode để đối soát.",""]
    lines+=table(["Case","Config ID","Tổng","V12 đủ","V13 đủ","Phút ? / nghỉ","Kết luận"],[
        [r["label"]+("*" if r["only_path_before"] else ""),f'`{r["id"]}`',r["raw"],r["old_priced"],r["priced"],
         f'{r["original_block_minutes"].get("UNCLASSIFIED_SOURCE_GAP",0)}/'
         f'{sum(v for k,v in r["original_block_minutes"].items() if k!="UNCLASSIFIED_SOURCE_GAP")}',
         "scenario component" if r["admitted_component"] else ", ".join(r["reasons"])] for r in by_case])
    lines+=["","Net R sau phí **SYM** từng năm, trên cohort cost-admitted được định giá:",
            "đây là kết quả theo giả định gap, chưa phải tiền trên tài khoản quỹ.",""]
    lines+=table(["Case","2018","2019","2020","2021","2022","2023"],[
        [r["label"]]+[f'{a["models"]["SYM"]["net_R"]:+.3f}' for a in r["annual"]] for r in by_case])
    lines+=["","Net R **ASYM** trên cùng các cohort:",""]
    lines+=table(["Case","2018","2019","2020","2021","2022","2023"],[
        [r["label"]]+[f'{a["models"]["ASYM"]["net_R"]:+.3f}' for a in r["annual"]] for r in by_case])
    lines+=["","Full annuals cũng có trong JSON; không loại SELL hoặc chọn mode",
        "theo một năm riêng. 16 component đủ cổng mô phỏng; **0** component đủ chứng nhận",
        "nguồn không còn phút chưa rõ. Đặc biệt 19/19 định giá được không đồng nghĩa 19/19 có edge.","",
        "## 2. Tổ hợp cơ học và trạng thái FTMO 9 năm","",
        "Medoid/overlap/correlation <0,25, tối đa 8, không search subset hay tối ưu trọng số.",
        "Equal risk giữ ba nhánh sau; không tăng risk để chữa thiếu cơ hội:",""]
    lines+=table(["Asset","Config được chọn"],[[r["asset"],f'`{r["id"]}`'] for r in by_case if r["id"] in decision["selected"]])
    lines+=["","Correlation ba cặp: −0,03465; −0,03018; +0,06914. Chỉ là correlation proxy",
        "daily MTM trên Development, không chứng nhận độc lập thống kê.",""]
    lines+=table(["Năm","Tín hiệu","SYM Net R","ASYM Net R","SYM DD đóng ngày (R)","Daily/static account loss"],[
        [a["year"],a["trades"],f'{a["models"]["SYM"]["net_R"]:+.3f}',f'{a["models"]["ASYM"]["net_R"]:+.3f}',
         f'{a["models"]["SYM"]["daily_MTM_R_DD"]:.3f}',"Chưa đo"] for a in decision["annual"]])
    lines+=["","Mean SYM +0,14774R/tín hiệu (340 lượt / 6 năm, trung bình 56,7/năm).",
        "Hai cụm SYM +19,901R / +30,331R; 4/6 năm dương; bỏ năm tốt nhất còn +13,034R.",
        "Đạt nhánh OR về ổn định đã đăng ký, nhưng 2023 đóng góp 74,05% tổng SYM.",
        "2019 và 2022 vẫn âm; chưa chứng minh thu nhập đều hoặc tốc độ vượt Challenge.",
        "Các cột DD là biến động đánh dấu **cuối ngày UTC**, không phải floating intraminute,",
        "Prague Daily Loss, static account loss hay shared-account replay.",
        "SL-Active không đồng nghĩa đã kiểm xong mọi luật FTMO.","",
        "| Hạng mục | Trạng thái |","|---|---|",
        "| 2024, 2025, 2026 YTD giá mới cho V13 | CLOSED — không được đọc |",
        "| Monthly 2-Step + biweekly payouts 2018–2026 | NOT RUN — Dev cadence fail |",
        "| Standalone Funded 50k / payout USD | NOT RUN / N/A |",
        "| Min lot, rounding sizing, margin, tin tức, path nguồn thật | Chưa được admission |","",
        "Không điền 0 payout như một kết quả mô phỏng. Nếu sau này được giao tiếp, dữ liệu thị",
        "trường 2024–2026 đã exposed từ chiến dịch trước; F5 chỉ là first evaluation của",
        "cơ chế trên dữ liệu đã exposed, không tự biến thành clean OOS.","",
        "## 3. Dung lượng và Merkle toàn cây","",
        "Tiền đề tăng 15GB không khớp snapshot cùng root/đơn vị:",""]
    lines+=table(["Mốc D","Logical bytes","GB thập phân","GiB"],[
        [name,row["bytes"],f'{row["bytes"]/1e9:.6f}',f'{row["bytes"]/1024**3:.6f}']
        for name,row in storage["D_history"].items()])
    lines+=["",f'V10 → V12 chỉ +{storage["V10_to_V12_bytes"]:,} bytes. 211,77 GB ≈197,22 GiB;',
        "sự khác đơn vị/scope không phải 15GB cache phình mới. Jobs/matrices V10–V13 ở E.",
        "JSON giữ delta theo nhóm để truy lại thay đổi thực tế; hai VI permission gaps vẫn unknown.","",
        f'Đã kiểm toàn bộ {dedup["whole_trees"]} cây của {dedup["input_directory_pairs"]} cặp directory,',
        f'bao phủ đủ {dedup["input_file_pairs"]} cặp file V12. {dedup["equal_tree_pairs"]} cặp',
        f'có Merkle toàn cây bằng nhau; {dedup["errors"]} cây không xác minh được.',
        "Hash gồm mọi file/relative path/size/SHA256 và empty directory, không sample.",
        "Không follow reparse/junction; giữ metadata hardlink và lỗi thay đổi file.",
        "Đây là toàn bộ cây của các candidates V12, không là chứng minh đã tìm hết mọi",
        "duplicate trên cả hai ổ.","",
        "**Không xóa bản nào:** các cây bằng nhau thuộc dependency/cache cài đặt, code/vendor",
        "đang dùng hoặc chưa chứng minh đã hết consumer, hay backup chưa rõ canonical/retirement.",
        "Import qua interpreter không bị loại chỉ vì không thấy executable trực tiếp trong cây.",
        "Hash bằng nhau không đủ chứng minh một bản cài đặt là thừa.",
        "Manifest/consumer evidence nằm ở private `directory-dedup.json` và `merkle-trees/`.",""]
    lines+=table(["Ổ/scope","Bytes xóa thực","Files xóa","Folders xóa","Delta snapshot bytes"],[
        [label,0,0,0,storage["observed_scope_delta"][label]["bytes"]] for label in ("D","E")])
    lines+=["","Delta snapshot gồm bằng chứng mới, cache/test/process khác; không gọi đó là",
        "physical space được giải phóng. **GB thu hồi được xác nhận: D=0, E=0.** Không đụng",
        "VI WIP, Trader pin, raw prices, frozen attempts hoặc backup duy nhất.","",
        "## 4. Auditor, tests, hiệu năng và bàn giao","",
        f'Auditor scalar/Decimal: **{audit["counts"]["paths"]:,} paths**, '
        f'**{audit["counts"]["cost_views"]:,} cost views / {audit["counts"]["cash_legs"]:,} cash legs**,',
        f'0 discrepancies. Kiểm mọi lượt valid của 28 cells, gồm {audit["counts"]["paths_with_source_uncertainty"]}',
        "lượt đi qua phút nguồn chưa rõ; giữ nhãn uncertainty. Auditor không import producer",
        "accounting/execution. Cùng implementer và cùng feed: không gọi là người review độc lập.",
        "Không kiểm toán account chưa chạy hoặc khẳng định giá thực thi broker.","",
        f'**{tests["unique_ids"]:,}/{tests["unique_ids"]:,} tests PASS**, 0 skip; giữ nguyên 1.072 IDs cũ, thêm 19.',
        f'Smoke 78 tests; phép đo sau tối ưu: median **{smoke["median_seconds"]:.6f}s**, '
        f'max **{smoke["max_seconds"]:.6f}s** trên {len(smoke["samples"])} lần.',
        f'{smoke["under_one_second"]}/{len(smoke["samples"])} lần dưới 1s. Mục tiêu median đạt, '
        "chưa bảo đảm mọi lần đều dưới 1s.",
        f'Lô serial cuối median {smoke["latest_batch_median"]:.6f}s / max {smoke["latest_batch_max"]:.6f}s.',
        "Thử A/B 5 cặp xen kẽ với runner 2 workers có sẵn; giữ serial vì parallel không",
        "cải thiện ổn định. Giữ đủ cả 2 batch serial và các mẫu parallel trong receipt.",
        "Giữ cả mẫu preflight 1,036s và mẫu 2,318s khi inventory/full IO chạy song song;",
        "không chọn mẫu nhanh nhất để báo. Đã profile thấy WMI qua numpy.testing import;",
        "dùng so sánh nguyên vẹn list/shape/tolerance thay lớp assert gây hardware-query.",
        "Giữ đủ 400 random first-passage queries và tất cả test IDs, không sửa kernel cho tốc độ.",
        "Không áp số đo smoke cho throughput lifecycle/full campaign.","",
        "V13 Development mất "+f'{read(JOB/"timings.json")["total"]:.3f}s'+
        " gồm source hash/load, gap index, 28 replays, profiles và write;",
        "khác workload 2.888-cell kernel V12 nên không báo speedup so với 36,9s.","",
        "Hậu kiểm: lỗi DirEntry.stat Windows trả inode/device=0 được phát hiện ở fixture",
        "Merkle trước production hash, đã đổi sang Path.stat cho file identity. Không retry",
        "financial batch; report đọc lại artifacts. Numerical attempts/seals V1–V12 giữ nguyên.",
        "Không thêm skill vì chưa có workflow mới cần một source of truth riêng; reuse quant",
        "core/deep_storage và skill hiện có. Không broker/paid/Astra/runtime promotion.","",
        "**Bước có cơ sở tiếp theo:** xác minh raw M1/tick cho các phút thiếu của ba nhánh",
        "được chọn trước khi bàn admission tài khoản. Không mở thêm grid, nâng risk hoặc",
        "đổi ngưỡng cadence trong cùng lô để ép qua gate. PR V13 để owner duyệt, không tự merge.",""]
    OUT.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")
    print(dict(report=str(OUT),json_bytes=OUT.with_suffix(".json").stat().st_size,totals=totals))


if __name__=="__main__":
    run()
