"""Compact V10 delivery; private matrices and original failed attempts stay intact."""
from collections import Counter
from pathlib import Path
import json
from prop_v10_source import JOB, sha

OUT = Path("planning/research/ENTERPRISE-ALPHA-V10-RESULTS-20261115")


def read(name):
    return json.loads((JOB/name).read_text(encoding="utf-8-sig"))


def table(headers, rows):
    return ["| " + " | ".join(map(str, headers)) + " |",
            "|" + "|".join("---" for _ in headers) + "|"] + [
                "| " + " | ".join(map(str, row)) + " |" for row in rows]


def run():
    scan, oracle = read("discovery-reviewed.json"), read("oracle.json")
    tests, bench = read("tests-final-matrix.json"), read("signal-benchmark.json")
    correction = read("technical-correction-receipt.json")
    if scan["eligible"] or scan["economics_pass"]:
        raise ValueError("No-Go report must not suppress an eligible configuration")
    d0, d1 = read("storage-D-before.json"), read("storage-D-after.json")
    e0, e1 = read("storage-E-before.json"), read("storage-E-after.json")
    parts = {label:read(f"disjoint-{label}.json") for label in ("D","E")}
    plan = read("E-cleanup-dry-run-manifest.json")
    purged = read("D-generated-purge.json")
    archive = read("closed-clean-web-dist.MANIFEST.json")
    smoke = read("tests-smoke.json")
    storage = dict(D_before=d0["groups"]["/"],D_after=d1["groups"]["/"],
        D_observed_reduction={k:d0["groups"]["/"][k]-d1["groups"]["/"][k] for k in ("bytes","files","folders")},
        E_before=e0["groups"]["/"],E_after=e1["groups"]["/"],
        E_observed_change={k:e1["groups"]["/"][k]-e0["groups"]["/"][k] for k in ("bytes","files","folders")},
        errors=dict(D_before=d0["errors"],D_after=d1["errors"],E_before=e0["errors"],E_after=e1["errors"]),
        logical_bytes_only=True,partitions_reconcile_readable_totals=True,
        partitions={label:dict(
            top15_files=dict(sorted(p.items(),key=lambda x:-x[1]["files"])[:15]),
            top15_bytes=dict(sorted(p.items(),key=lambda x:-x[1]["bytes"])[:15]),
            full_map_path=str(JOB/f"disjoint-{label}.json"),
            full_map_sha256=sha(JOB/f"disjoint-{label}.json"))
                    for label,p in parts.items()},
        after_observed_utc=dict(D=d1["observed_utc"],E=e1["observed_utc"]),
        E_dry_run=dict(potential_bytes=plan["potential_bytes"],potential_files=plan["potential_files"],
                       executed=False,metadata_only=True,exact_duplicates_not_proven=True),
        generated_dependencies=purged,archive={k:v for k,v in archive.items() if k!="files"},
        deferred_archive=read("cold-package-store-deferred.json"),git_repack=read("git-repack.json"))
    reasons = dict(Counter(reason for row in scan["rows"] for reason in row["reasons"]))
    best_family = []
    for asset in ("XAUUSD","EURUSD"):
        for family in ("F1","F2","F3","F4"):
            rows = [r for r in scan["rows"] if r["asset"]==asset and r["family"]==family]
            if rows:
                best = max(rows,key=lambda r:(r["score"],sum(c["net"]["SYM"]["raw"] for c in r["clusters"])))
                best_family.append(dict(asset=asset,family=family,configurations=len(rows),
                    economic_pass=sum(r["economic_gate"] for r in rows),eligible=sum(r["eligible"] for r in rows),
                    positive_both_clusters=sum(all(c["net"]["SYM"]["raw"]>0 for c in r["clusters"]) for r in rows),
                    best=best))
    top = [dict(rank=i+1,**row) for i,row in enumerate(scan["top15"])]
    annual = [dict(year=y,stage0="DEVELOPMENT_MEASURED" if y<2024 else "NOT_OPENED_IN_V10",
                   strategy_stage1=None,portfolio=None,challenge_pass=None,payout=None)
              for y in range(2018,2027)]
    names = ("source-admission.json","discovery-registration.json","discovery.json","discovery-reviewed.json",
             "decision.json","raw-matrix.npz","raw-matrix-reviewed.npz","raw-signals.json",
             "technical-correction-registration.json","technical-correction-receipt.json",
             "postpersist-failure.json","oracle.json","signal-benchmark.json","tests-final-matrix.json",
             "storage-D-before.json","storage-D-after.json","storage-E-before.json","storage-E-after.json",
             "E-cleanup-dry-run-manifest.json","historical-seals-v10.json","admission-oracle.json",
             "source-scope-evidence.json")
    proof = {name:dict(path=str(JOB/name),sha256=sha(JOB/name)) for name in names}
    decision = dict(schema="ENTERPRISE-ALPHA-V10-DECISION-v1",trials=544,
        economic_pass=0,eligible=0,stage1="CANCELED_FAILED_STAGE0",
        validation_2024_2026="NOT_OPENED_IN_V10",portfolio=None,lifecycle="CANCELED_FAILED_STAGE0",
        clean_OOS=False,cutoff="2026-10-13",challenge_qualified=False,broker_authority=False,
        new_strategy_trials_after_outcomes=0,technical_recalculation=True,
        reason="No configuration meets the preregistered clustered economic/cadence/robustness gate.")
    output = dict(schema="ENTERPRISE-ALPHA-V10-v1",status="NO_NEW_CHALLENGE_CANDIDATE",
        parent_merge="97a44f2",branch="codex/enterprise-alpha-v10",private_job=str(JOB),
        storage=storage,tests=dict(tests,smoke=smoke),signal_benchmark=bench,
        discovery=dict(trials=544,recipes=136,raw_occurrences=244264,priced_occurrences=oracle["rational_priced_rows"],
            original_scan_seconds=scan["scan_seconds"],original_config_years_per_second=scan["config_years_per_second"],
            top15=top,families=best_family,failure_counts=reasons,
            costs_conditional=True,SL_active=False,statistics_approximate=True),
        verification=dict(oracle={k:v for k,v in oracle.items() if k!="changed_gate_rows"},
                          changed_gate_row_count=len(oracle["changed_gate_rows"]),
                          correction=correction,historical_seals=read("historical-seals-v10.json"),
                          admission=read("admission-oracle.json")),
        decision=decision,annual_lifecycle=annual,artifacts=proof,
        limitations=["Synthetic Ask: Gold0.338USD/oz and EUR1pip; not observed BidAsk.",
                     "Holiday guards/swaps are scenarios, not certified historical FTMO execution.",
                     "Raw endpoints ignore interim stops, concurrency, lot rounding and equity path.",
                     "All2018–2026 previously exposed; no claim of clean OOS.",
                     "No independent person review; rational oracle uses same implementer.",
                     "Two inaccessible VI directories excluded; no ACL change."])
    OUT.with_suffix(".json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    decision_path=OUT.with_name("ENTERPRISE-ALPHA-V10-DECISION-20261115.json")
    decision_path.write_text(json.dumps(decision,indent=2),encoding="utf-8")
    lines = [
        "# V10 — storage tầng sâu, scanner nhanh và atlas F1–F4",
        "",
        "**Đã hoàn tất quét và kiểm định kỹ thuật; chưa có chiến lược mới đủ để thi Challenge.**",
        "PR88 đã merge `97a44f2`. Nhánh `codex/enterprise-alpha-v10`; PR mới để owner duyệt, không tự merge.",
        "544 cấu hình = 136 công thức × 4 thời gian giữ. Có 0 cấu hình đạt cổng kinh tế và 0 đạt đủ Stage0.",
        "Vì vậy không ghép danh mục, không mở giá 2024–2026 và không chạy mô phỏng quỹ 9 năm.",
        "",
        "## 1. Dung lượng D và E",
        "",
        "Đây là logical bytes, không phải physical NTFS allocated space. Chỉ tổng phần đọc được;",
        "hai thư mục pytest của VI Dubber vẫn PermissionError, không thay ACL. Junction/symlink không được đi theo.",
        "",
    ]
    lines += table(["Ổ / thời điểm","Files","Folders","Bytes","GiB"],[
        [f"{label} {time}",r["files"],r["folders"],r["bytes"],f'{r["bytes"]/2**30:.3f}']
        for label,before,after in (("D",d0,d1),("E",e0,e1))
        for time,r in (("trước",before["groups"]["/"]),("sau",after["groups"]["/"]))])
    lines += ["",f'D giảm ròng {storage["D_observed_reduction"]["bytes"]:,} bytes / '
              f'{storage["D_observed_reduction"]["files"]:,} files tại snapshot sau.',
              "Số ròng có cả artifact/test/cache phát sinh; không đồng nhất với tổng bytes từng thao tác xóa.",
              ""]
    for label in ("D","E"):
        for key,title in (("files","số file"),("bytes","dung lượng")):
            ranked=sorted(parts[label].items(),key=lambda item:-item[1][key])
            selected=ranked[:15]
            rest={k:sum(v[k] for _,v in ranked[15:]) for k in ("bytes","files","folders")}
            lines += [f"### {label}: Top 15 theo {title} — trước dọn", ""]
            lines += table(["Partition không chồng lấn","Files","Folders","GiB"],
                [[f"`{p}`",v["files"],v["folders"],f'{v["bytes"]/2**30:.3f}'] for p,v in selected] +
                [["Phần còn lại",rest["files"],rest["folders"],f'{rest["bytes"]/2**30:.3f}']])
            lines += [""]
    lines += [
        "`@direct` là file trực tiếp/thư mục cha còn dư sau khi tách các nhánh con.",
        "Tổng mọi partition khớp 100% số đếm đọc được. Full maps ở private disjoint-D/E.json, có hash trong JSON báo cáo.",
        "",
        "E không phải bản mirror thuần của D: có workspace backup, nhiều snapshot build lịch sử,",
        "và `ai-engine-jobs` chứa nghiên cứu/nguồn duy nhất đang được pin path/hash. D còn VI Dubber lớn;",
        "vì vậy so chênh lệch tổng GB không cho biết phần nào là bản trùng có thể xóa.",
        "",
        "Các thao tác đã thực hiện:",
        "",
        "- Repack Git root và Trader: giữ refs/HEAD/unreachable, fsck connectivity trước/sau đạt;",
        "  không prune-now trên các checkout dùng chung.",
        "- Xóa đúng3 node_modules của UI QA tháng9 đã đóng:15.918 regular files /357.880.116 bytes,",
        "  cùng273 links. Không đi theo link target; giữ source/screenshots/manifests.",
        "- Cold ZIP một dist cũ:3files/1.028.734bytes →265.044bytes; SHA256 từng file,",
        "  roundtrip và rehash trước bỏ bản giải nén. Restore locator ở MANIFEST.",
        "- Một pnpm-store chưa nén vì có reparse descendant; guard dừng trước thay đổi, nguồn còn nguyên.",
        f'- E có plan **dry-run** cho {plan["potential_files"]:,}files /{plan["potential_bytes"]:,}bytes '
        f'({plan["potential_bytes"]/1e9:.2f}GB) build caches cũ.',
        "  **Chưa xóa phần này, chưa chứng minh duplicate bằng content hash.** Manifest là metadata từng file.",
        "",
        "Quy trình bảo trì dùng `tooling/WORKSPACE-MAINTENANCE.md`; không có daemon hoặc tự mirror/purge E.",
        "",
        "## 2. Engine, tốc độ và kiểm chứng",
        "",
        "Luồng chính: M1 đã kiểm hash → nến H1/H4/D1 đã đóng → 136 công thức → 4 endpoint",
        "→ spread/commission/slippage/directional swap → cổng theo năm/cụm → Holm và DSR proxy.",
        "Chỉ đủ Stage0 mới được xây SL-active/account simulation. Lượt này dừng trước bước đó.",
        "",
    ]
    lines += table(["Đo lường","Kết quả","Giới hạn"],[
        ["Scan nguyên bản544×6 config-years",f'{scan["scan_seconds"]:.3f}s; {scan["config_years_per_second"]:.1f}config-years/s',
         "M1 đã nạp; gồm signal/markout/statistics, chưa SL/account"],
        ["Tạo cùng136 công thức",f'{bench["medians"]["original"]:.3f}→{bench["medians"]["cached"]:.3f}s; {bench["speedup"]:.2f}×',
         "16 cặp xen kẽ; cùng at/side/stop/config; riêng signal phase"],
        ["Smoke",f'{smoke["tests"]}tests /{smoke["seconds"]:.3f}s',"Không thay full gate"],
        ["Base serial→2 process",f'{tests["base_serial_seconds"]:.3f}→{tests["base_parallel_seconds"]:.3f}s',
         f'{tests["base_speedup"]:.2f}×; cùng924IDs'],
        ["Full Windows matrix",f'{tests["tests"]}tests /{tests["total_partition_wall_seconds"]:.3f}s',
         "Cộng wall time các group,0skip; giữ đủ1013IDs cũ"],
        ["Fraction oracle",f'{oracle["rational_priced_rows"]:,}priced occurrences ×2fees',
         f'max error {oracle["max_abs_error"]:.3g}'],
    ])
    lines += [
        "",
        "Tối ưu là cache timing masks dùng lại trong cùng lần quét; không bỏ kiểm phí hoặc rủi ro.",
        "Benchmark signal giữ nguyên output. Lần scan8,58s là trước cache và trước correction;",
        "không gắn thời gian đó cho một lượt SL-active hoặc toàn chiến dịch đã sửa.",
        "CI chuyển sang full suite gồm native/statistical/worker, upload test IDs và timings.",
        "",
        "### Lỗi đã bắt và cách xử lý",
        "",
        "- Run đầu đã lưu xong số liệu nhưng lỗi stdout cuối (`stage` truyền trùng). Giữ attempt thất bại;",
        "  sửa event và có regression, không gọi run đầu exit-success.",
        "- Scalar oracle bắt DAY sau20:30 lấy giá thoát trước entry. Loại endpoint đi ngược thời gian;",
        "  đồng thời chặn entry thứSáu tại/sau20:30 khỏi bị giữ sang tuần sau.",
        f'  {len(correction["changed_cells"])}ô thay mask, {correction["invalidated"]}occurrences bị invalidated; '
        "không đổi at/side/SL/quotes hoặc grid.",
        "- Cổng SCALE sửa từ worst-year sang pooled cluster medians đúng protocol. Không đổi ngưỡng15%.",
        "- Technical registration trước tính lại; original source snapshots/pins/matrix/result giữ nguyên.",
        "  Sau đối soát, Top 15 không đổi và vẫn0 economic/eligible.",
        "",
        "Oracle khác arithmetic nhưng cùng người triển khai; không tự nhận independent person review.",
        "HAC5/Holm có phép đối soát riêng. DSR là proxy gần đúng; không là DSR được chứng nhận;",
        "trial budget544 không xóa được selection history của các chiến dịch trước.",
        "V8 exact Dev/release seals và V7 exact snapshot view được kiểm lại; không thay old pins.",
        "",
        "## 3. Alpha Atlas qua hai cụm chế độ",
        "",
        "F1: phá cấu trúc H4/D1. F2: hồi trong xu hướng H4 rồi H1 tiếp diễn.",
        "F3: nén NR/BB rồi bung. F4: xung lực phiên Mỹ/đầu tuần/đầu-cuối tháng.",
        "XAUUSD có 92 công thức và EURUSD có 44. US500/USDJPY/GBPUSD chưa được nhận vào vì chưa",
        "admission source M1/H1 toàn 2018–2023 kèm cost/spec. Không dùng H1 mẫu thay M1.",
        "",
        "Bảng dưới lấy cấu hình đứng đầu từng asset/family để nhìn hướng kết quả;",
        "không cộng lãi các cấu hình hoặc gọi cấu hình đứng đầu là chiến lược đạt.",
        "",
    ]
    lines += table(["Asset / họ","Số ô","Raw netR cụm18–20 /21–23 (SYM)","Số ô dương2cụm","Đạt kinh tế /đủgate"],
        [[f'{r["asset"]} {r["family"]}',r["configurations"],
          " / ".join(f'{c["net"]["SYM"]["raw"]:+.2f}' for c in r["best"]["clusters"]),
          r["positive_both_clusters"],f'{r["economic_pass"]}/{r["eligible"]}'] for r in best_family])
    lines += ["","### Top 15 gần đạt — vẫn No-Go",""]
    lines += table(["ID","Cấu hình /horizon","RawR cụm18–20 /21–23","AdmittedR cụm18–20 /21–23",
                    "N admitted 18–20 /21–23","Năm dương SYM"],
        [[f'T{r["rank"]:02}',f'{r["asset"]} `{r["recipe"]}` {r["horizon"]}',
          " / ".join(f'{c["net"]["SYM"]["raw"]:+.2f}' for c in r["clusters"]),
          " / ".join(f'{c["net"]["SYM"]["admitted"]:+.2f}' for c in r["clusters"]),
          " / ".join(str(c["admitted"]) for c in r["clusters"]),
          sum(a["economics"]["SYM"]["raw_net_R"]>0 for a in r["annual"])] for r in top])
    lines += ["","NetR ở đây là endpoint move sau phí chia naturalSL, chưa đặt SL chạy thật.",
              "244.264 raw occurrences là tổng cell-records;4 horizons và recipes có trùng tín hiệu,",
              "không phải244.264 lệnh độc lập. Các cột raw giữ cả tín hiệu trước cost filter.","",
              "### Top 15: netR SYM từng năm và lý do dừng",""]
    lines += table(["ID","2018","2019","2020","2021","2022","2023","Lý do"],
        [[f'T{r["rank"]:02}',*[f'{a["economics"]["SYM"]["raw_net_R"]:+.2f}' for a in r["annual"]],
          ", ".join(r["reasons"])] for r in top])
    lines += ["","Toàn bộ 544 ô có Holm p=1; DSRproxy lớn nhất chỉ "
              f'{max(r["statistics"]["DSR_proxy"] for r in scan["rows"]):.5f}. '
              f't-stat lớn nhất={max(r["statistics"]["t_stat"] for r in scan["rows"]):.3f}.',
              "Không cấu hình nào đã qua toàn cổng kinh tế trước thống kê; không thể đổ kết quả 0",
              "chỉ cho việc Holm bảo thủ. Counts lý do có chồng lấn, không cộng thành tổng 544.",""]
    lines += table(["Lý do","Số ô"],sorted(reasons.items(),key=lambda p:-p[1]))
    lines += [
        "",
        "Giá Ask là proxy (Gold0,338USD/oz; EUR1pip), swap là scenarios (GoldSYM−40/−40,",
        "ASYM−45/−5USD/lot; EUR−40USD/lot hai chiều). Không phải lịch sử phí FTMO đã chứng nhận.",
        "Không SL-active, grid lots, concurrency hoặc floating equity; không suy ra Worst Daily Loss",
        "từ bảng endpoint. Mọi2018–2026 đã exposed trước đây; validation sau này chỉ là reused historical.",
        "",
        "## 4. Challenge và payout 9 năm",
        "",
        "Không có composition đủ điều kiện nên lượt này không có con số pass, payout hay drawdown",
        "của danh mục V10. N/A khác tỷ lệ pass 0%. Không mượn danh mục V8 để điền thành tích V10.",
        "",
    ]
    lines += table(["Năm","Stage0","Stage1 /danh mục","Challenge /payout"],
        [[r["year"],r["stage0"],"N/A — failed Stage0","N/A — không chạy"] for r in annual])
    lines += [
        "",
        "Khuyến nghị: chốt No-Go lô 544 ô này, giữ scanner và source đã kiểm. Chưa tăng risk",
        "hoặc mua Challenge. Một chiến dịch tiếp theo cần cơ chế kinh tế khác và budget đăng ký",
        "mới, hoặc source/cost admission cho tài sản còn thiếu; không nới gate để cứu Top 15.",
        "",
        "### Hậu kiểm kỹ thuật và bàn giao",
        "",
        "| Mặt | Kết quả /quyết định |",
        "|---|---|",
        "| Correctness | Sửa backward DAY, post-Friday entry và cluster aggregation; giữ original attempts. |",
        "| Reliability | Event cuối không crash; regression và receipts; không tự rerun một financial job đã lưu. |",
        "| Performance | Timing-mask cache giữ output;2 process giữ đủ IDs; smoke cho vòng phát triển. |",
        "| Storage | Xóa generated dependencies đã đóng; E dry-run, giữ private research và VI WIP. |",
        "| Method | Không thêm grid sau outcome, không mở validation cho nhánh fail. |",
        "",
        "Không cần sửa skill/AGENTS: đây là lỗi engine và bằng chứng performance, đã đặt regression/runbook",
        "ở đúng owner; không tạo một lớp instruction trùng lặp. Không broker/runtime promotion/Astra/paid provider.",
        "",
        f"Private job: `{JOB}`. JSON có Top 15/annual/cluster/top-partitions/artifact SHA256.",
        "PR được giao với 3 CI đúng HEAD rồi dừng, không tự merge. Chi tiết terminal failures và",
        "các technical attempts vẫn có trong private job; không thay seal để làm đẹp.",
    ]
    OUT.with_suffix(".md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(dict(report=str(OUT.with_suffix(".md")),json_bytes=OUT.with_suffix(".json").stat().st_size))


if __name__=="__main__":
    run()
