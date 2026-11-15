"""Compact V14 evidence publication from completed immutable job receipts."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from statistics import median
import hashlib
import json
from prop_v14_source import JOB,FIRST,END,read,sha

OUT=Path("planning/research/EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115")
PERIODS={"2018–2021":(2018,2021),"2022–2024":(2022,2024),"2024–2026":(2024,2026),"2018–2026":(2018,2026)}


def year(t):return datetime.fromtimestamp(t/1000,timezone.utc).year


def table(head,rows):
    return ["| "+" | ".join(head)+" |","|"+"|".join("---" for _ in head)+"|"]+[
        "| "+" | ".join(str(v).replace("|",r"\|") for v in row)+" |" for row in rows]


def unique_funded(rows):
    paths={}
    for r in rows:
        if len(r["phase_passes"])<2:continue
        accepted=[p for p in r["accepted"] if p["phase"]==3]
        if not accepted:continue
        closed=[p for p in r["closed"] if p["phase"]==3]
        key=json.dumps([accepted,closed,r["payouts"]],sort_keys=True)
        # Pretrade states after a phase reset can contain different dates only
        # through the funded entry stream; retain complete quantity/cash ledger.
        paths.setdefault(hashlib.sha256(key.encode()).hexdigest(),r)
    return list(paths.values())


def lifecycle(rows):
    windows=[r for r in rows if r["kind"]=="CHALLENGE"]
    result={}
    for name,(lo,hi) in PERIODS.items():
        chosen=[r for r in windows if lo<=year(r["start_msc"])<=hi]
        phase1=[r for r in chosen if len(r["phase_passes"])>=1]
        passed=[r for r in chosen if len(r["phase_passes"])==2]
        unique=unique_funded(passed)
        months=[(r["phase_passes"][1]["at"]-r["start_msc"])/(86400000*365.25/12) for r in passed]
        result[name]=dict(windows=len(chosen),phase1=len(phase1),phase1_pct=100*len(phase1)/len(chosen),
            funded_windows=len(passed),funded_pct=100*len(passed)/len(chosen),unique_funded_traded_paths=len(unique),
            funded_windows_without_trade=sum(not any(t["phase"]==3 for t in r["accepted"]) for r in passed),
            median_months_to_two_phases=median(months) if months else None,
            payout_count_windows=sum(len(r["payouts"]) for r in chosen),
            modeled_trader_payout_windows_usd=sum(r["trader_payout_usd"] for r in chosen),
            payout_count_deduplicated_funded_paths=sum(len(r["payouts"]) for r in unique),
            modeled_trader_payout_deduplicated_paths_usd=sum(r["trader_payout_usd"] for r in unique),
            worst_daily_pct=max(r["worst_daily_loss_pct"] for r in chosen),
            worst_static_pct=max(r["static_loss_pct"] for r in chosen),
            breaches=sum(bool(r["first_breach"]) for r in chosen),
            censored_phase1=sum(r["phase"]==1 and not r["first_breach"] for r in chosen),
            censored_phase2=sum(r["phase"]==2 and not r["first_breach"] for r in chosen))
    return result


def run():
    cfg=read(JOB/"candidate-freeze.json");dev=read(JOB/"development.json")
    evidence=read(JOB/"path-evidence.json");storage=read(JOB/"dedup-receipt.json")
    tests=read(JOB/"tests-final-matrix.json");smoke=read(JOB/"smoke-ten-results.json")
    if not tests["passed"] or not smoke["no_failures_or_skips"]:raise ValueError("V14_tests_unresolved")
    cases=[];audits=[];all_trades={}
    for tag in ("OLHC","OHLC"):
        trades=read(JOB/f"{tag}-strategy-trades.json");all_trades[tag]=trades
        path_audit=read(JOB/f"{tag}-independent-path-audit.json")
        if not path_audit["passed"]:raise ValueError("V14_path_audit_not_passed")
        audits.append(dict(tag=tag,kind="PATH",paths=len(path_audit["paths"])))
        for candidate in ("A","B"):
            for view in ("NEXT_QUOTE","CLEAN_COHORT"):
                ledger=read(JOB/f"{tag}-{candidate}-{view}-accounts.json")
                audit=read(JOB/f"{tag}-{candidate}-{view}-independent-account-audit.json")
                if not audit["passed"]:raise ValueError("V14_account_audit_not_passed")
                audits.append(dict(tag=tag,candidate=candidate,view=view,kind="ACCOUNT",accounts=audit["accounts"]))
                selected=[t for t in trades if t["id"] in cfg["candidate_"+candidate] and
                    (view=="NEXT_QUOTE" or not t["source_uncertain"])]
                for model in ("SYM","ASYM"):
                    account_rows=[r for r in ledger if r["cell"].startswith(model)]
                    annual=[]
                    for y in range(2018,2027):
                        events=[t for t in selected if year(t["decision_msc"])==y]
                        closed=[t for t in events if not t["censored"]]
                        book=next(r for r in account_rows if r["kind"]=="ANNUAL_REFERENCE" and r["year"]==y)
                        raw=sum(t["reference"][model]["net_R"] for t in closed)
                        annual.append(dict(year=y,signals=len(events),BUY=sum(t["side"]=="BUY" for t in events),
                            SELL=sum(t["side"]=="SELL" for t in events),by_sleeve=dict(Counter(t["id"] for t in events)),
                            source_uncertain=sum(t["source_uncertain"] for t in events),censored=len(events)-len(closed),
                            unit_net_R=raw,mean_unit_net_R=raw/len(closed) if closed else None,
                            actual_quantity_book_net_R=book["net_R"],book_closed=book["closed_trades"],
                            book_entries=book["entries"],
                            book_by_sleeve=dict(Counter(selected[a["trade"]]["id"] for a in book["accepted"])),
                            book_lot_grid_rejected=book["rejections"].get("LOT_GRID_MIN_MAX",0),
                            book_mean_net_R=book["mean_net_R"],book_R_DD=book["max_equity_R_DD"],
                            book_daily_pct=book["worst_daily_loss_pct"],book_static_pct=book["static_loss_pct"],
                            book_peak_dd_pct=book["peak_dd_pct"],
                            book_open_at_year_end=len(book["open_positions"])))
                    standalone=next(r for r in account_rows if r["kind"]=="STANDALONE_FULL")
                    summary={k:standalone[k] for k in ("entries","closed_trades","balance_usd","terminal_equity_usd",
                        "trader_payout_usd","worst_daily_loss_pct","static_loss_pct","peak_dd_pct","first_breach")}
                    summary.update(payout_count=len(standalone["payouts"]),open_positions=len(standalone["open_positions"]))
                    cases.append(dict(order=tag,candidate=candidate,view=view,model=model,annual=annual,
                        validation_unit_R=sum(r["unit_net_R"] for r in annual if r["year"]>=2024),
                        validation_positive_years=sum(r["unit_net_R"]>0 for r in annual if r["year"]>=2024),
                        lifecycle=lifecycle(account_rows),standalone=summary))
    index={}
    for p in sorted(JOB.glob("*")):
        if p.is_file() and p.suffix in (".json",".jsonl",".npz",".bin"):
            index[p.name]=dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
    core_rows=[r for identity in cfg["candidate_A"] for r in dev["rows"] if r["id"]==identity]
    result=dict(schema="V14-results-v1",candidates={k:cfg["candidate_"+k] for k in ("A","B")},
        release=read(JOB/"longitudinal-release.json"),development=dev["candidates"],
        core_dossiers=[dict(r,direction="BOTH") for r in core_rows],complete_26_cells=[
            {k:r[k] for k in ("id","raw","priced","admitted","source_uncertain","complete_path","reasons")}
            for r in dev["rows"]],
        source_evidence={k:evidence[k] for k in ("core_signals","core_uncertain","core_unique_gaps",
            "all_unique_gaps","raw_quotes_found")},
        source_dev=read(JOB/"source-dev-admission.json")["assets"],
        native_tail=read(JOB/"longitudinal-native-tail-backfill.json"),
        storage={k:storage[k] for k in ("logical_bytes","files","folders","physical_bytes_freed","removed")},
        storage_held=len(storage["held"]),broad_reference_scan=read(JOB/"dedup-broad-reference-followup.json"),
        tests=tests,smoke=smoke,audits=audits,scenarios=cases,artifacts=index,
        challenge_readiness="NOT_READY_TIME_FIT_AND_SOURCE_SENSITIVITY",
        source_path_certified=False,prop_qualified=False,actual_broker_orders=0,actual_payout_usd=0,
        interpretation="conditional M1 scenarios; CLEAN_COHORT is future-dependent ex-post sensitivity; post-exposure historical validation")
    OUT.with_suffix(".json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    if OUT.with_suffix(".json").stat().st_size>1024*1024:raise ValueError("compact_report_exceeds_1MiB")
    a_next=next(c for c in cases if (c["order"],c["candidate"],c["view"],c["model"])==("OLHC","A","NEXT_QUOTE","SYM"))
    a_clean=next(c for c in cases if (c["order"],c["candidate"],c["view"],c["model"])==("OLHC","A","CLEAN_COHORT","SYM"))
    lines=["# V14 — Bằng chứng gốc, A/B và vòng đời tài khoản 2018–2026","",
        "**Chưa nên mua Challenge.** A có lợi nhuận tổng Validation tốt hơn B, nhưng thời gian pass còn quá dài",
        f'và phụ thuộc giả định dữ liệu: A/SYM pass {a_next["lifecycle"]["2018–2026"]["funded_windows"]}/105 cửa sổ,',
        f'trung vị {a_next["lifecycle"]["2018–2026"]["median_months_to_two_phases"]:.1f} tháng; CLEAN_COHORT chỉ',
        f'{a_clean["lifecycle"]["2018–2026"]["funded_windows"]}/105. Không coi cổng tần suất đạt là cổng time-fit đạt.',
        "Standalone Funded giả định được cấp sẵn vốn, không phải chứng minh có thể thi quỹ nhanh hoặc có thu nhập chính ổn định.","",
        "PR #92 đã merge `65bf0c2`; A/B và mã tính khóa tại `ae575b7` trước khi mở giá 2024–2026.",
        "Giữ nguyên ba nhánh A và thêm đúng hai nhánh độc lập theo thứ tự đã đăng ký cho B; không tìm subset/weights mới.",
        "Toàn bộ kết quả dưới đây là mô phỏng offline, chưa đủ chứng nhận Challenge hoặc payout thực.","",
        "## 1. Bằng chứng M1/tick và tổ hợp Development","",
        f"A: 340 tín hiệu, **44** đường đi qua **111** gap chưa xác minh. Danh sách timestamp đầy đủ trong JSON báo cáo và `path-evidence.json`.",
        "Đã quét metadata 1.104.021 file D/E; 46.675 file có dấu hiệu nguồn phù hợp, 158 ZIP khớp. 256 lỗi được giữ",
        "(253 FileNotFound, 2 VI PermissionError, 1 BadZipFile). Không coi những định dạng/archive chưa giải mã là đã tìm hết.",
        "Tìm được 106 tick gốc trong phút EURUSD 16/11/2020 10:23 UTC: bổ sung 1 M1 vào MarketDataStore phiên bản mới.",
        "Gold thêm 0 thanh; probe cả CSV Date/Time tách cột. Không lấp gap bằng giá giả, không thay input V1–V13.",
        "EUR 2024–2026 ban đầu hết 07/10/2026; đã nối đúng 5.723 phút sau đó từ M1 dựng bằng tick native QDM đã có hash ở V6, đến hết 13/10.",
        "Giữ Ask proxy Gold 0,338 USD/oz và EUR 1 pip; không gọi toàn bộ nguồn là bid/ask tick thực.","",
        "Ba nhánh gốc (BUY và SELL, không chọn lại chiều sau kết quả):",""]
    lines+=table(["Nhánh","Định danh","Horizon / Mode","SYM 2018→2023"],[
        [i+1,r["id"],r["horizon"]+" / "+r["mode"],
         " / ".join(f'{a["models"]["SYM"]["net_R"]:+.2f}' for a in r["annual"])] for i,r in enumerate(core_rows)])
    lines+=["","F3 BB = breakout nén Bollinger; F4 = impulse theo lịch tháng; EUR F5 = rejection đã đăng ký ở H4.",
        "P0 giữ SL gốc, P1 chỉ nâng stop bảo vệ sau khi đủ ngưỡng; không mở biến thể mới.",
        "B thêm EUR F3 NR14/multiple1/DAY/P1 và Gold F3 NR14/multiple2/48H/P0.",""]
    lines+=table(["Dev","Lệnh/năm 2018→2023","Trung bình","SYM tổng / bỏ năm tốt nhất"],[
        [k," / ".join(str(a["trades"]) for a in v["annual"]),f'{v["mean_annual_cadence"]:.2f}',
         f'{v["models"]["SYM"]["net_R"]:+.2f} / {v["models"]["SYM"]["ex_best_R"]:+.2f}R']
        for k,v in dev["candidates"].items()])
    lines+=["","Cổng trung bình >=50/năm là thay đổi được owner duyệt cho V14; không sửa lại verdict V13.",
        "B có nhiều lệnh hơn nhưng tổng Dev SYM thấp hơn A; không mặc định nhiều nhánh tốt hơn.","",
        "## 2. Chín năm và Challenge/Funded","",
        "Bảng chính: NEXT_QUOTE, thứ tự M1 O–L–H–C. Net R đơn vị cộng theo năm phát tín hiệu, trước lot floor thực tế;",
        "DD và lỗ ngày/static lấy từ sổ tham chiếu riêng từng năm risk 150 USD, lot thực tế. Có exposure qua giao năm",
        "nên Net R đơn vị và PnL cash của sổ năm không đồng nhất; toàn bộ cột đối soát nằm trong JSON.",
        "2026 là YTD đến hết 13/10, không phải cả năm. Dữ liệu 2024–2026 đã từng có exposure lịch sử, không gọi pristine OOS.",""]
    primary=[c for c in cases if c["order"]=="OLHC" and c["view"]=="NEXT_QUOTE"]
    rows=[]
    for candidate in ("A","B"):
        sym=next(c for c in primary if c["candidate"]==candidate and c["model"]=="SYM")
        asym=next(c for c in primary if c["candidate"]==candidate and c["model"]=="ASYM")
        for a,b in zip(sym["annual"],asym["annual"]):
            rows.append([candidate,a["year"],f'{a["signals"]} ({a["BUY"]}/{a["SELL"]})',
                f'{a["unit_net_R"]:+.2f} / {b["unit_net_R"]:+.2f}',
                f'{a["mean_unit_net_R"]:+.3f}',f'{a["book_R_DD"]:.2f}',
                f'{a["book_daily_pct"]:.3f} / {a["book_static_pct"]:.3f}'])
    lines+=table(["Ứng viên","Năm","N (BUY/SELL)","Net R SYM/ASYM","Mean SYM","R-DD sổ","Daily/static % SYM"],rows)
    lines+=["","So sánh toàn bộ 16 tổ hợp mô hình (CLEAN_COHORT dùng thông tin đường giá tương lai để loại lệnh,",
        "**chỉ là sensitivity sau thực tế, không phải bộ lọc có thể chạy live**; cả hai thứ tự M1 đều không phải biên toán học):",""]
    lines+=table(["A/B","Order / view / phí","R 2024–26","Dương / 3 năm","P1 / 105","Cả 2 / 105",
        "Funded paths có trade","Median tháng","Standalone payout USD / số lần"],[
        [c["candidate"],f'{c["order"]} / {c["view"]} / {c["model"]}',f'{c["validation_unit_R"]:+.2f}',
         c["validation_positive_years"],c["lifecycle"]["2018–2026"]["phase1"],
         c["lifecycle"]["2018–2026"]["funded_windows"],c["lifecycle"]["2018–2026"]["unique_funded_traded_paths"],
         f'{c["lifecycle"]["2018–2026"]["median_months_to_two_phases"]:.1f}' if c["lifecycle"]["2018–2026"]["median_months_to_two_phases"] is not None else "N/A",
         f'{c["standalone"]["trader_payout_usd"]:.2f} / {c["standalone"]["payout_count"]}'] for c in cases])
    lines+=["","Chi tiết theo nhóm tháng bắt đầu — bảng chính O–L–H–C / NEXT_QUOTE. 2024 xuất hiện trong hai nhóm",
        "nên các nhóm có chồng lấn; 105 cửa sổ không phải 105 đường giá độc lập. Cửa sổ chưa pass được giữ là censored.",
        "Payout dưới đây là **tổng giả định của các cửa sổ chồng nhau**, không phải thu nhập có thể cộng lại hoặc xác suất thành công.",""]
    rows=[]
    for c in primary:
        for period,r in c["lifecycle"].items():
            rows.append([c["candidate"]+"/"+c["model"],period,r["windows"],
                f'{r["phase1"]} ({r["phase1_pct"]:.1f}%)',f'{r["funded_windows"]} ({r["funded_pct"]:.1f}%)',
                r["unique_funded_traded_paths"],
                f'{r["median_months_to_two_phases"]:.1f}' if r["median_months_to_two_phases"] is not None else "N/A",
                f'{r["payout_count_windows"]} / {r["modeled_trader_payout_windows_usd"]:.2f}',
                f'{r["worst_daily_pct"]:.3f}/{r["worst_static_pct"]:.3f}',r["breaches"]])
    lines+=table(["A/B/phí","Start cohort","N","P1","Cả 2","Funded paths","Tháng median",
        "Payout lần / USD chồng lấn","Daily/static %","Breach"],rows)
    lines+=["","Standalone Funded 50k từ 01/2018 (không cần pass Challenge):",""]
    lines+=table(["A/B / phí","Entries","Payout lần / USD","Balance cuối","Daily/static/peak DD %","Breach"],[
        [c["candidate"]+"/"+c["model"],c["standalone"]["entries"],
         f'{c["standalone"]["payout_count"]} / {c["standalone"]["trader_payout_usd"]:.2f}',
         f'{c["standalone"]["balance_usd"]:.2f}',
         "/".join(f'{c["standalone"][k]:.3f}' for k in ("worst_daily_loss_pct","static_loss_pct","peak_dd_pct")),
         bool(c["standalone"]["first_breach"])] for c in primary])
    lines+=["","**Hạn chế còn chặn việc dùng tiền thật:** dữ liệu thiếu và proxy Ask; thứ tự M1 giả định; tin tức/historical",
        "broker calendar chưa chứng nhận; chưa shadow/demo/owner handover; challenge fee/retry, admin delay, thay đổi spec",
        "và điều kiện nhận payout thực tế chưa mô phỏng. Reference R không bằng % lợi nhuận tài khoản.",
        "Risk giữ đúng V4 200/175/125 USD, throttle/cap/reserve và V6 harvester; không dùng ratchet phase1/2 V5.",
        "Payout 80%, debit 100% gross profit, kỳ 14 ngày là giả định hợp đồng nghiên cứu; không có chuyển tiền thật.","",
        "## 3. Dọn 106 cặp directory","",
        f"106 cặp quy về 51 E targets. Đã xóa **4 cây**, **{storage['files']} file**, **{storage['folders']} thư mục**,",
        f"**{storage['logical_bytes']:,} bytes = {storage['logical_bytes']/1e9:.8f} GB** logic; giữ **{len(storage['held'])} cây**.",
        "Không gọi bytes logic là bytes vật lý đã giải phóng. D canonical được hash trước/sau, có manifest SHA256 từng file và hướng dẫn restore.",
        "Giữ package/cache subtree để không phá metadata môi trường; giữ Git backup, references và các trường hợp không chứng minh được an toàn.",
        "Không xóa dữ liệu nghiên cứu cũ hoặc VI WIP. Reference scan ban đầu gồm tracked superproject/submodules + process;",
        "scan bổ sung bao gồm cả ignored/untracked text/config. Lỗi đọc và giới hạn dynamic references giữ trong receipt, không tuyên bố scan tuyệt đối.",""]
    lines+=table(["Bản E đã xóa","Bytes","File/thư mục"],[
        [r["target"],r["bytes"],f'{r["files"]}/{r["folders"]}'] for r in storage["removed"]])
    lines+=["","## 4. Kiểm toán, kiểm thử và hiệu năng","",
        f"Decimal oracle kiểm **{sum(a.get('paths',0) for a in audits)} paths** và **{sum(a.get('accounts',0) for a in audits)} account ledgers**.",
        "Kiểm riêng entry/cost/grid/reserve, first-hit/P1 timing, Prague reset, equity DD, phase passes, forced-close next quote và payout cash bridge.",
        "Không import accounting producer trong `independent_ledger_auditor.py`; đây là phép tính riêng cùng implementer/feed, không phải reviewer/người hay nguồn giá độc lập.",
        f"**{tests['tests']} tests PASS**, **0 skip**; giữ nguyên **{tests['preserved']}/{tests['old']} IDs** và thêm **{len(tests['added'])}** regressions.",
        "Smoke giữ đúng 78 bài (đề bài ghi 66 là baseline cũ). Profile đầu lượt: suite 0,660s, import 0,241s;",
        "không có một test 150–200ms: test lâu nhất khoảng 71ms, tổng I/O fixtures là phần lớn thời gian.",
        f"10 lần fresh-process đã đăng ký trước: median suite **{smoke['median_seconds']:.3f}s**, max **{smoke['max_seconds']:.3f}s**;",
        f"median wall **{smoke['median_wall']:.3f}s**, max wall **{smoke['max_wall']:.3f}s**.",
        f"10/10 suite <0,85s: **{smoke['all_suite_under_085']}**; 10/10 wall <0,85s: **{smoke['all_wall_under_085']}**.",
        "Giữ mọi outlier, không retry để kiếm streak đẹp; không giảm test/case/assertion. Đo đủ rồi dừng, không refactor vòng đời chỉ để đổi số benchmark.",
        "Exact-head CI và artifact ID reconciliation được lưu trong receipt CI sau khi PR chạy.","",
        "## Kết luận sử dụng","",
        "A/B đã được chạy đến lifecycle theo quyền V14, không dừng ở gate tần suất cũ. Xem các bảng trên để phân biệt",
        "dương tổng, ổn định từng năm, tốc độ pass, và payout. Không tự tăng risk hay chọn lại nhánh sau Validation.",
        "Giữ A làm ứng viên nghiên cứu ưu tiên nếu so sánh nhất quán; B là đối chứng thêm tần suất, không mặc định được promote.",
        "Cần owner xem kết quả và phê duyệt giai đoạn kiểm chứng tiếp; PR V14 mở để review, **không merge**.","",
        f"Nguồn máy đọc + hash toàn bộ receipts: `{OUT.name}.json`. Private job: `{JOB}`.",
        "Mã chạy/flow: source admission → frozen recipes → two M1 paths → V4/V6 reused lifecycle → standalone Decimal audit → report.",
        "Erratum-01: sổ tham chiếu bỏ lệnh không vừa lot tối thiểu thay vì crash, không nới risk. Chỉ B chưa xong được resume;",
        "giữ bốn kết quả A và hai log thất bại. Erratum-02 chỉ mở rộng kiểm toán nguồn/chi phí và thứ tự event cùng timestamp.",
        "Giữ freeze, nguồn cũ, thử nghiệm âm và các lần rehearsal không đạt; không xóa lịch sử lựa chọn."]
    OUT.with_suffix(".md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(dict(report=str(OUT),scenarios=len(cases),accounts=sum(a.get("accounts",0) for a in audits)),flush=True)


if __name__=="__main__":run()
