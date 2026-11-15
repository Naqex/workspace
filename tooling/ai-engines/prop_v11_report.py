"""Four-part V11 report; full discovery and disk inventories remain private."""
from pathlib import Path
from collections import Counter
import json
from prop_campaign_source import ROOT
from prop_v10_source import sha

JOB=ROOT/"ensemble-and-storage-v11-20261115"
FINAL=JOB/"clock-corrected"
OUT=Path("planning/research/ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def table(headers,rows):
    return ["| "+" | ".join(map(str,headers))+" |",
            "|"+"|".join("---" for _ in headers)+"|"]+[
                "| "+" | ".join(map(str,row))+" |" for row in rows]


def run():
    atlas=read(FINAL/"component-atlas.json");decision=atlas["decision"]
    if decision["passed"]:raise ValueError("No-Go report must not suppress a passing ensemble")
    initial=read(JOB/"decision.json");oracle=read(FINAL/"independent-oracle.json")
    tests=read(JOB/"tests-final-matrix.json");purge=read(JOB/"E-cache-purge.json")
    health=read(JOB/"cross-drive-health-current.json")
    catalog=read(JOB/"source-catalog-summary.json")
    market=read(JOB/"market-file-inventory-v2.json")
    before={x:read(JOB/f"storage-{x}-before.json") for x in ("D","E")}
    after={x:read(JOB/f"storage-{x}-after.json") for x in ("D","E")}
    rows=sorted(atlas["dual_positive"],key=lambda r:r["id"])
    aliases={r["id"]:f"C{i+1:02}" for i,r in enumerate(rows)}
    selected=decision["selected"]
    registry=[]
    for r in rows:
        registry.append(dict(cid=aliases[r["id"]],id=r["id"],asset=r["asset"],family=r["family"],
            direction="BOTH",horizon=r["horizon"],origin=r["origin"],recipe=r["recipe"],
            years=[dict(year=a["year"],raw=a["raw"],priced=a["priced"],admitted=a["admitted"],
                        median_SL=a["median_SL"],scale_ratio=a["scale_ratio"],
                        raw_SYM_R=a["economics"]["SYM"]["raw_net_R"],
                        admitted_SYM_R=a["economics"]["SYM"]["admitted_net_R"],
                        admitted_ASYM_R=a["economics"]["ASYM"]["admitted_net_R"]) for a in r["annual"]],
            clusters=r["clusters"],mean_admitted_R={m:r["economics"][m]["mean_R"] for m in ("SYM","ASYM")},
            endpoint_R_DD={m:r["economics"][m]["endpoint_R_DD"] for m in ("SYM","ASYM")},
            trades_per_year=r["trades_per_year"],V10_reasons=r["V10_rejection_reasons"],
            V10_cadence_shortfall_per_year=[n/3 for n in r["missing_trades_for_V10"]],
            V10_missing_positive_years=r["SYM_missing_positive_years_for_V10"],
            V11_component_admitted=r["component_admitted"],V11_component_reasons=r["component_reasons"],
            selected=r["id"] in selected,V11_statistics=r["V11_statistics"]))
    top15=[dict(rank=i+1,id=r["id"],cid=aliases.get(r["id"]),V10_reasons=r["V10_rejection_reasons"])
           for i,r in enumerate(atlas["V10_top15"])]
    annual=[dict(a,mean_R={m:a["models"][m]["net_R"]/a["trades"] if a["trades"] else None
                          for m in ("SYM","ASYM")},actual_SL_PV_DD=None,
                 Worst_Daily_Loss_pct=None,Worst_Static_Loss_pct=None,source="Development endpoint proxy")
            for a in decision["annual"]]
    annual += [dict(year=y,trades=None,models=None,mean_R=None,actual_SL_PV_DD=None,
                   Worst_Daily_Loss_pct=None,Worst_Static_Loss_pct=None,
                   source="NOT_OPENED_IN_V11_FAILED_DEV_GATE") for y in (2024,2025,2026)]
    storage=dict(before={x:before[x]["groups"]["/"] for x in before},
        after={x:after[x]["groups"]["/"] for x in after},
        E_net_reduction={k:before["E"]["groups"]["/"][k]-after["E"]["groups"]["/"][k] for k in ("bytes","files","folders")},
        exact_purge=purge,read_errors={x:after[x]["errors"] for x in after},
        health={k:v for k,v in health.items() if k!="roots"},logical_bytes=True,
        snapshot_times={x:after[x]["observed_utc"] for x in after})
    artifacts={}
    for root,names in ((JOB,("E-cache-purge.json","E-cache-purge.journal.jsonl","process-target-preflight.json",
                            "storage-D-before.json","storage-D-after.json","storage-E-before.json","storage-E-after.json",
                            "source-admission-v11.json","source-catalog-summary.json","market-file-inventory-v2.json",
                            "cross-drive-health-current.json","tests-final-matrix.json","historical-seals-v11.json",
                            "decision.json","US500-endpoint-clock-audit.json")),
                       (FINAL,("selection-registration.json","component-atlas.json","native-hourly-matrix.npz",
                               "native-hourly-source-audit.json","independent-oracle.json","decision.json"))):
        for name in names:
            p=root/name;artifacts[str(p.relative_to(JOB))]=dict(path=str(p),sha256=sha(p))
    output=dict(schema="ENSEMBLE-AND-STORAGE-V11-v1",status="NO_QUALIFIED_ENSEMBLE",parent_merge="3dd35a7",
        branch="codex/ensemble-and-storage-v11",private_job=str(JOB),storage=storage,
        source_catalog=catalog,market_inventory=dict(files=len(market["files"]),errors=market["errors"],
            format_counts=dict(Counter(Path(r["path"]).suffix for r in market["files"])),
            metadata_only=True,quote_values_decoded=False),
        trials=atlas["trials"],dual_positive=len(rows),component_count=len(atlas["candidates"]),
        registry=registry,V10_top15=top15,selection=atlas["selection"],decision=decision,
        initial_attempt=initial,annual=annual,verification=oracle,tests=tests,artifacts=artifacts,
        full_account_simulation="CANCELED_FAILED_DEV_ENSEMBLE",funded_payouts=None,challenge_passes=None,
        clean_OOS=False,new_validation_prices_opened=False,actual_SL_path_tested=False,
        independence="same implementer, alternate arithmetic and source quote decoder")
    OUT.with_suffix(".json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    summary=dict(schema="V11-DECISION-v1",trials=atlas["trials"],dual_positive=len(rows),
        component_count=len(atlas["candidates"]),K=len(selected),passed=False,selected=selected,
        reasons=decision["reasons"],SL_active="CANCELED_FAILED_DEV_ENDPOINT_GATE",
        composition=None,validation_2024_2026="NOT_OPENED_IN_V11",lifecycle="CANCELED_FAILED_DEV_ENSEMBLE",
        GoldA_variant="NOT_RUN_BASE_ENSEMBLE_DID_NOT_PASS",clean_OOS=False,prop_status="PROP_UNMEASURED",
        broker_execution_authorized=False)
    OUT.with_name("ENSEMBLE-AND-STORAGE-V11-DECISION-20261115.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    lines=[
        "# V11 — dọn E, tìm lại nguồn dữ liệu và kiểm định ensemble",
        "",
        "**Đã xóa đúng 119,79 GB cache được duyệt và kiểm xong tổ hợp 6 nhánh; chưa đủ cơ sở thi Challenge.**",
        "Sau khi sửa lịch nguồn US500, có 42 cấu hình dương ở cả hai cụm năm. Trong đó, 33 cấu hình",
        "qua cổng thành phần; bộ ghép giữ 6 đại diện trung tâm (medoid), với mức risk bằng nhau.",
        "Tần suất đạt trung bình 86 tín hiệu/năm, nhưng chỉ dương 4/6 năm. Vì cổng Development",
        "chưa đạt, không mở giá 2024–2026, không chạy đường lệnh có SL hay mô phỏng tài khoản/payout.",
        "",
        "PR #89 đã merge tại `3dd35a7`, nhánh V10 đã xóa. Branch `codex/ensemble-and-storage-v11`;",
        "PR mới dự kiến #90 chờ owner duyệt, không tự merge. Giữ WIP của VI Dubber, Trader pin,",
        "dữ liệu gốc và các seal kiểm toán lịch sử.",
        "",
        "## 1. Storage D/E và dữ liệu tìm lại được",
        "",
        "Đã kiểm trước toàn bộ 17 thư mục: khớp manifest hash, danh sách file, size, mtime và số thư mục;",
        "không có reparse point, Git lồng, đuôi dữ liệu thị trường hoặc process tham chiếu target.",
        "Journal ghi ý định và kết quả từng lần xóa.",
        f'Đã xóa **{purge["bytes"]:,} bytes / {purge["files"]:,} files / {purge["folders"]:,} folders**.',
        "Đây là logical bytes; không đo allocated NTFS bytes hoặc suy ra toàn E là duplicate.",
        "",
    ]
    lines+=table(["Scope","Before files /folders","After files /folders","Before bytes","After bytes"],
        [[x,f'{storage["before"][x]["files"]:,} / {storage["before"][x]["folders"]:,}',
          f'{storage["after"][x]["files"]:,} / {storage["after"][x]["folders"]:,}',
          f'{storage["before"][x]["bytes"]:,}',f'{storage["after"][x]["bytes"]:,}'] for x in ("D","E")])
    lines+=["",f'E giảm ròng tại snapshot **{storage["E_net_reduction"]["bytes"]:,} bytes / '
            f'{storage["E_net_reduction"]["files"]:,} files**; chênh với lượng xóa chính xác do journal/code/job mới phát sinh.',
            "Snapshot sau purge có timestamp trong JSON; không đồng nhất nó với dung lượng sau mọi run về sau.",
            "D không purge thêm trong V11. Hai VI permission gaps vẫn unknown, không thay ACL.",""]
    lines+=table(["Target được duyệt trên E","Bytes xóa","Files","Folders"],
        [[r["path"].replace("E:\\BACKUP-TRADINGWORKSPACE\\",""),r["bytes"],r["files"],r["folders"]]
         for r in purge["completed"]])
    lines+=["","### Kiểm kê source, không lấy tên file làm chứng nhận dữ liệu","",
        f'Kiểm kê metadata D/E nhận diện {len(market["files"]):,} file có thể liên quan tới nguồn thị trường; có 2 lỗi quyền đọc.',
        "Không đi theo links hoặc quét nội dung OS/apps/games/dependency trees. Không parse giá validation.",
        "Full filename/size inventory và phạm vi bỏ qua nằm private; source index lưu path/hash, không copy raw.",""]
    lines+=table(["Asset","Nguồn/khung đã xác minh","Phạm vi và giới hạn"],[
        ["XAUUSD","QDM M1; ticks cho các phần đã được nhận","Metadata 2003–2026; V11 dùng lại 2018–2023. Full M1 dùng Ask proxy 0,338 USD/oz."],
        ["EURUSD","QDM M1 + 517.750.341 ticks","Metadata 2003–2026; V11 dùng lại 2018–2023. Full M1 dùng Ask proxy 1 pip."],
        ["GBPUSD / AUDUSD","H1 gốc có cả Bid/Ask, sealed books 2010–2024","Đủ 2018–2023 + warmup; thiếu M1, đường giá trong giờ, quote 20:30 và full 2025–2026."],
        ["US500","M1 Bid/Ask: nguồn dài 2013–2021, nguồn 2022–2024, metadata 2025–2026","Quét 2018–2023 + warmup; thiếu 3 request ASK năm 2020. Không dựng giá thay thế."],
        ["USDJPY","M1 pilot 10/01/2019 và 15/07/2022; sample/test data","Chưa đủ 6 năm; không coi fixture 2013 hoặc tick mô phỏng 2019 là lịch sử thị trường thật."],
        ["BTCUSD / BTCUSDT","D1 crypto và một số file mẫu/tick mô phỏng","Chưa có full H1/M1 đủ điều kiện; không tạo M1 từ D1."],
    ])
    lines+=["",
        "V10 mới admission QDM Gold/EUR; điều đó không chứng minh E thiếu mọi nguồn khác.",
        "V11 tìm lại H1 GBP/AUD và M1 US500 dài hạn thông qua sealed-books/native-source proofs.",
        "Đây là gap reuse/inventory đã sửa; không phải nguồn mới tải về hoặc một edge đã được xác nhận.",
        "",
        "`PairedHourlyStore`/`IndexedUs500Store` trong Quant Core đọc files gốc trên E theo index/hash.",
        "H1 dùng nến gốc, không nhân thành 60 nến M1 giả. Adapter cô lập giữ source V10 nguyên vẹn;",
        "test M1→H1 trên fixture giả lập xác nhận cùng at/side/stop/config. Không đổi system config.",
        "",
        "Health command phát hiện cả cache build mới, không chỉ 17 thư mục đã xóa:",
        "",
        "```powershell",
        "python tooling/workspace_maintenance.py cross-drive-audit --root D:/ANNAM/TradingWorkspace --other-root E:/BACKUP-TRADINGWORKSPACE --cache-manifest <V10-manifest> --output <private-health.json>",
        "```",
        f'Các thư mục nghi là build cache hiện đọc được {health["cache_known_bytes"]:,} bytes; budget 120.000.000.000 bytes; '
        f'exceeded={health["cache_budget_exceeded"]}, unknown={health["cache_unknown"]}.',
        "Candidate theo tên không là delete authority. Tool chỉ đọc/cảnh báo, không tự purge, không daemon;",
        "không thể bảo đảm cache không bao giờ mọc lại nếu không có lịch audit tương lai. Không tạo automation.",
        "",
        "## 2. Giải phẫu dual-cluster và bộ ghép",
        "",
        "Giữ 544 ô V10; thêm 176 GBPUSD + 176 AUDUSD + 368 US500 = **1.264 ô / 316 công thức tín hiệu**.",
        "Không mở grid mới: F1 phá H4/D1, F2 hồi theo trend H4, F3 nén rồi bung, F4 timing/momentum.",
        "Không đổi direction BOTH, naturalSL, horizons hoặc tối ưu trọng số.",
        "",
        "Chi phí: Gold/EUR giữ V10. GBP/AUD dùng proxy 9 USD/lot/vòng, swap −40 USD/lot/ngày thường,",
        "thứ Tư ×3. US500 dùng Atlas cũ: commission 1 USD/lot/vòng + slippage 1,5 points/vòng,",
        "funding −2 USD/lot/ngày lịch, contract 1 USD/point/lot. Spread lấy từ Bid/Ask quan sát được.",
        "Các proxy này chưa là biểu phí FTMO hiện hành được xác nhận; SYM/ASYM FX/US500 trùng scenario.",
        "",
        "Cổng V10 thực tế là ≥20 tín hiệu được nhận/năm trung bình mỗi cụm và ≥4/6 năm dương;",
        "không phải 80 lệnh hoặc dương mọi năm. V11 nới cổng thành phần theo owner, giữ nguyên verdict V10.",
        "Dual-positive chỉ tính phần có endpoint, không lấp giá thiếu. Component còn cần raw/admitted cluster",
        "dương, mean ≥0,04R, tỷ lệ qua ngưỡng phí 15% ≥50%/cụm, pooled scale ≤15% và đủ 100% endpoint.",
        "",
        "### Hai technical views được giữ riêng",
        "",
    ]
    lines+=table(["View","Dual-positive","Components","Selected K","Kết quả"],
        [["Ban đầu",36,19,initial["K"],"; ".join(initial["reasons"])],
         ["Sửa source clock",len(rows),len(atlas["candidates"]),len(selected),"; ".join(decision["reasons"])]])
    lines+=["",
        "Mốc 20:30 UTC của US500 rơi vào giờ nghỉ 16:15–18:00 New York trong mùa hè.",
        "Kiểm timestamp trên mọi ô US500 tìm thấy 45.738 bản ghi invalid thuộc giờ nghỉ này.",
        "Đã dùng lại `prop_portfolio_sources.deadline`: nếu hạn thoát nằm trong giờ nghỉ thì lấy",
        "16:00 New York cùng ngày, chỉ dời sớm hơn; không chọn giờ theo PnL hoặc lấp giá thiếu.",
        "Giữ attempt đầu, commit correction trước outcome mới; không đổi alpha rules/gates/costs.",
        "H1 FX vẫn thiếu giá 20:30: không dùng quote 21:00 hoặc nội suy để cứu coverage.",
        "",
        "### Toàn bộ 42 cấu hình dương hai cụm và giữ được ≥50% tín hiệu tại ngưỡng phí 15%",
        "",
        "N là số tín hiệu được nhận trước risk budget/lot grid/SL-active, chưa số lệnh thật.",
        "Mean/DD là admitted SYM **endpointR proxy**, ghi PnL theo ngày entry; không floating equity/account DD.",
        "N sáu năm theo thứ tự 2018/19/20/21/22/23. Pass% ghi cụm 2018–2020 / 2021–2023.",
        "",
    ]
    lines+=table(["ID","Asset /họ","Config /horizon","Direction","N6năm","Pass%","MeanR","Max endpointR-DD"],
        [[aliases[r["id"]],r["asset"]+" "+r["family"],f'`{r["recipe"]}` {r["horizon"]}',"BOTH",
          "/".join(str(a["admitted"]) for a in r["annual"]),
          "/".join(f'{c["retention"]*100:.1f}' for c in r["clusters"]),
          f'{r["economics"]["SYM"]["mean_R"]:+.4f}',f'{r["economics"]["SYM"]["endpoint_R_DD"]:.3f}'] for r in rows])
    lines+=["","Cột cluster dưới: rawR/admittedR; sáu cột năm dùng admitted SYM.",""]
    lines+=table(["ID","18–20 raw/admit","21–23 raw/admit","2018","2019","2020","2021","2022","2023"],
        [[aliases[r["id"]],*[f'{c["net"]["SYM"]["raw"]:+.2f}/{c["net"]["SYM"]["admitted"]:+.2f}' for c in r["clusters"]],
          *[f'{a["economics"]["SYM"]["admitted_net_R"]:+.2f}' for a in r["annual"]]] for r in rows])
    lines+=["","Lý do V10 và V11 được tách; US500 mới không bị gán là đã quét ở V10.",""]
    lines+=table(["ID","V10: thiếu cadence/năm cũ /mới; thiếu năm dương; lý do khác","V11 component /selection"],
        [[aliases[r["id"]],
          (f'{r["missing_trades_for_V10"][0]/3:.2f}/{r["missing_trades_for_V10"][1]/3:.2f}; '
           f'{r["SYM_missing_positive_years_for_V10"]}; '+", ".join(r["V10_rejection_reasons"]))
          if r["origin"]=="V10" else "Chưa source admission/chưa quét ở V10",
          ("SELECTED" if r["id"] in selected else "admitted, cùng cụm với medoid khác" if r["component_admitted"]
           else ", ".join(r["component_reasons"]))] for r in rows])
    lines+=["","### Top 15 V10 đối chiếu lại",""]
    lines+=table(["Rank V10","ID ở bảng trên","V11"],[
        [r["rank"],r["cid"],"SELECTED" if r["id"] in selected else "Xem component/medoid reason phía trên"]
        for r in top15])
    lines+=["",
        "42 cấu hình dương hai cụm gồm 24 Gold + 18 US500. Cổng thành phần giữ 19 Gold + 14 US500;",
        "các cặp FX mới không có thành phần đạt. Bộ ghép nối cùng asset/family nếu corr ≥0,30 hoặc",
        "trùng ≥50% thời điểm tín hiệu; chọn medoid trung tâm, hòa thì theo ID. Khác họ cũng cần corr <0,30.",
        "Không thử mọi tổ hợp, side hoặc trọng số. 33 thành phần → 6 đại diện, mỗi tín hiệu cược 1R.",
        "Correlation dùng endpoint proxy ghi theo ngày entry, không chứng nhận",
        "independent bets hoặc actual daily mark-to-market covariance. Equal weights vẫn có selection bias.",
        "",
        "## 3. Ensemble: Development và bảng 9 năm",
        "",
    ]
    selected_rows=[next(r for r in rows if r["id"]==k) for k in selected]
    lines+=table(["Sleeve","Asset /setup /exit","N/năm","Mean admittedR"],
        [[aliases[r["id"]],f'{r["asset"]} {r["recipe"]} /{r["horizon"]}',f'{r["trades_per_year"]:.2f}',
          f'{r["economics"]["SYM"]["mean_R"]:+.4f}'] for r in selected_rows])
    lines+=[""]
    lines+=table(["Năm","N tín hiệu","SYM NetR","ASYM NetR","SYM MeanR","SYM endpointR-DD","Worst daily/static loss%"],
        [[a["year"],a["trades"],f'{a["models"]["SYM"]["net_R"]:+.3f}',f'{a["models"]["ASYM"]["net_R"]:+.3f}',
          f'{a["mean_R"]["SYM"]:+.4f}',f'{a["models"]["SYM"]["endpoint_R_DD"]:.3f}',"N/A — chưa equity path"]
         if a["models"] else [a["year"],"N/A","N/A","N/A","N/A","N/A","Không mở validation"]
         for a in annual])
    total=sum(a["trades"] for a in decision["annual"])
    best=max(r["economics"]["SYM"]["net_R"]/r["economics"]["SYM"]["endpoint_R_DD"] for r in selected_rows)
    lines+=["",
        f'Sáu năm có {total} tín hiệu được nhận = {total/6:.2f}/năm. Hai cụm đạt 62,33 và 109,67/năm,',
        "nhưng 2018 chỉ có 23 tín hiệu. Chưa đạt 5/6 năm dương: 2021 và 2022 vẫn âm; hiện chỉ 4/6.",
        f'SYM tổng {decision["metrics"]["SYM"]["net_R"]:+.3f}R, endpointR-DD '
        f'{decision["metrics"]["SYM"]["endpoint_R_DD"]:.3f}R; ratio '
        f'{decision["metrics"]["SYM"]["netR_DD_ratio"]:.4f} thấp hơn sleeve tốt nhất {best:.4f}.',
        "Năm 2023 đạt +61,52R, lớn hơn tổng cả 6 năm; bỏ 2023 thì tổng còn âm. Tổng hai cụm",
        "có thể che giấu nhiều năm yếu, nên chưa đủ suy ra lợi thế đều hoặc thu nhập chính.",
        "",
        "Không đổi medoid sang highest-profit, bỏ năm xấu hoặc thêm filter/GoldA để cứu result.",
        "GoldA variant được đăng ký chỉ sau khi base ensemble qua Dev path gate; điều kiện chưa tới.",
        "IR=IC×sqrt(breadth) không có nghĩa thêm nhiều cấu hình tương quan thấp sẽ tự sinh IC dương bền.",
        "",
        "2024–2026 chưa đo cho V11 nhưng đã có exposure qua nghiên cứu trước: nếu mở sau này",
        "chỉ là kiểm định lịch sử tái sử dụng. Lượt này không mở giá đó; không gọi đây là clean OOS.",
        "",
        "## 4. Challenge/payout, kiểm chứng và chốt sổ",
        "",
    ]
    lines+=table(["Hạng mục yêu cầu","Trạng thái"],
        [["SL-active / ngân sách mở chung 800 USD / risk tham chiếu 150 USD","CANCELED — endpoint Dev gate chưa đạt"],
         ["Bắt đầu mỗi tháng: 2018–2021 (48), 2022–2024 (36), 2024–10/2026 (34)","Không chạy; cửa sổ chồng lấn, không giả độc lập"],
         ["FTMO 2-Step: mục tiêu 10%/5%, daily 5%/static 10% theo scenario","PROP_UNMEASURED; chưa có pass-rate mới"],
         ["Standalone Funded 50k / rút tiền mỗi hai tuần","Không chạy; Payout Count/USD = N/A, không phải 0"],
         ["Floating Peak-to-Valley /Worst Daily /Static loss","N/A; endpoint proxy không thay equity path"],
         ["Validation 2024/2025/2026 YTD","Chưa mở trong V11; không lấy đối chứng V8 làm hiệu suất V11"]])
    lines+=["",
        f'Full Windows matrix **{tests["tests"]}/{tests["tests"]}**, 0 skip, giữ đủ 1.030 IDs cũ;'
        f' group wall time {tests["total_group_seconds"]:.2f}s.',
        f'Smoke **{tests["smoke"]["tests"]} tests / {tests["smoke"]["seconds"]:.3f}s**, vẫn <1s.',
        "Timings là từng lượt quan sát, không benchmark capacity hoặc so host CI với local.",
        f'Oracle: {oracle["configurations"]} cấu hình / {oracle["annual_cells"]} ô năm, '
        f'{oracle["new_source_priced_rows"]:,} bản ghi nguồn mới có giá × 2 chế độ phí; '
        f'{oracle["source_quote_sample_records"]:,} quote nguồn được kiểm mẫu; sai số tối đa {oracle["max_abs_error"]:.3g}.',
        "Scalar/Fraction kiểm fees/funding/netR, source JSON decoder riêng đối chiếu entry/exit/spread,",
        "scalar graph/medoid chọn đúng 6 nhánh; tổng từng ngày, từng năm và endpoint DD đều khớp.",
        "Cùng implementer, khác arithmetic/code path; không tự nhận independent person review hoặc feed.",
        "V10 source/matrix/old oracle bindings và V8 exact/V7 snapshot seals đã kiểm lại.",
        "",
        "### Bài học và bước tiếp",
        "",
        "- Storage: đã thực hiện purge được giao; mọi target khác chỉ được health-audit read-only.",
        "- Data: source discovery phải đi qua E/source proofs, không dừng ở QDM symbol list.",
        "- Engine: port lịch source đã có trước khi gán missing-price thành thiếu alpha; giữ cả failed attempt.",
        "- Method: giảm cadence gate ở sleeve đã làm đúng mục đích; ensemble vẫn có thể không đều qua năm.",
        "- Decision: **No-Go V11**, chưa tăng risk hoặc mua Challenge. Đợt sau cần hypothesis/source-path",
        "  budget mới, không tiếp tục tìm subset/weights trong cùng lô cho tới khi đẹp.",
        "",
        "Không sửa skill/AGENTS hoặc thêm daemon; thay đổi nằm ở engine/helper/tests/runbook đúng owner.",
        "Data flow: source index read-only →closed bars →registered recipes →cost/coverage gate →medoid",
        "→equal-risk endpoint screen →stop. SL-active/validation/account chỉ mở khi các gate trước đạt.",
        "",
        f"Private job `{JOB}`. JSON báo cáo có registry 42 cấu hình, Top 15 cũ, correlation/overlap,",
        "lịch sử các lần chạy, trạng thái 9 năm và artifact path/SHA256. Delivery receipt ghi PR/HEAD/3 CI",
        "thực tế sau khi checks đạt. Không tự merge PR mới, không broker/Astra/paid/provider calls.",
    ]
    OUT.with_suffix(".md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(dict(report=str(OUT.with_suffix(".md")),json_bytes=OUT.with_suffix(".json").stat().st_size))


if __name__=="__main__":
    run()
