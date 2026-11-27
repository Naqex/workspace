"""V5 evidence report; incomplete source and bootstrap gates remain explicit."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess
from prop_campaign_report import aggregate,compact
from prop_v5_common import *

OUT=Path("planning/research/PROP-OVERNIGHT-V5-RESULTS-20261115")


def date(at):
    return datetime.fromtimestamp(at/1000,timezone.utc).isoformat()


def brief(c):
    return {k:v for k,v in compact(c).items() if k not in
            ("entry_audit","operations","forced_closes")}


def path_count(cases):
    paths=set()
    for c in cases:
        if len(c["phase_passes"])<2:continue
        seq=[(r["trade"],r["at"],r["net_usd"]) for r in c["closed"] if r["phase"]==3]
        paths.add(hashlib.sha256(json.dumps(seq).encode()).hexdigest())
    return len(paths)


def coverage_intervals(days):
    groups=[];current=None
    for d in days:
        if d["weekday"]>=5:continue
        state="TIMESTAMP_MAIN_SESSION_OK" if d["main_session_timestamp_complete"] else "HOLIDAY_OR_GAP_UNRESOLVED"
        if current is None or current["status"]!=state:
            current=dict(first_day=d["day"],last_day=d["day"],status=state,weekdays=1)
            groups.append(current)
        else:current["last_day"]=d["day"];current["weekdays"]+=1
    return groups


def build():
    parity=read(JOB/"accounting-parity.json")
    tests=read(JOB/"regression-tests.json")
    stat=read(JOB/"bootstrap-parity.json")
    if parity["status"]!="PASS" or not tests["passed"]:
        raise ValueError("V5_report_requires_verification")
    d=read(DECISION);release=read(JOB/"validation-release.json")
    blob=subprocess.check_output(["git","show",release["commit"]+":"+DECISION.as_posix()])
    if json.loads(blob)!=d or hashlib.sha256(blob).hexdigest()!=release["git_blob_sha256"]:
        raise ValueError("V5_report_freeze_binding")
    for pin in d["pins"]:
        if digest(pin["path"])!=pin["sha256"]:raise ValueError("V5_frozen_pin_changed:"+pin["path"])
    cases=read(JOB/"validation-accounts.json")
    v4=read(Path("planning/research/PROP-COCORE-V4-RESULTS-20261114.json"))
    v3=read(Path("planning/research/PROP-PORTFOLIO-V3-RESULTS-20261114.json"))
    old=read(V4/"validation-accounts.json")
    third=read(JOB/"source-recovery.json")
    labels=["V3 ASYM","V4 ASYM","V4 SYM","V5 ASYM","V5 SYM","V5 + sleeve3"]
    compared=[
        v3["lifecycle_comparisons"]["ASYM_FLAT"][3],
        v4["reward_comparisons"]["ASYM_FLAT:14"],
        v4["reward_comparisons"]["SYM_FLAT:14"],
        aggregate([c for c in cases if c["cell"]=="ASYM_FLAT"]),
        aggregate([c for c in cases if c["cell"]=="SYM_FLAT"]),None]
    uniqueness=[
        path_count(read(V3/"lifecycle-ASYM_FLAT-PORTFOLIO.json")),
        path_count([c for c in old if c["cell"]=="ASYM_FLAT" and c["reward_interval_days"]==14]),
        path_count([c for c in old if c["cell"]=="SYM_FLAT" and c["reward_interval_days"]==14]),
        path_count([c for c in cases if c["cell"]=="ASYM_FLAT"]),
        path_count([c for c in cases if c["cell"]=="SYM_FLAT"]),None]
    dd=read(JOB/"eur-dd-diagnosis.json")
    forensic=read(JOB/"eur-dd-boundary-and-london-diagnostic.json")
    continuous=read(JOB/"continuous-selection-recheck.json")
    trials=read(JOB/"mechanism-decision.json")
    eurbooks=read(JOB/"mechanism-eur-books.json")
    source=read(JOB/"blind-holdout-audit.json")
    for asset in source["assets"]:
        asset["coverage_intervals"]=coverage_intervals(asset.get("days",[]))
    mc=read(JOB/"bootstrap-results.json")
    operation_summary={}
    for model in MODELS:
        rows=[c for c in cases if c["cell"]==model]
        operation_summary[model]=dict(
            events=dict(sum((Counter(o["kind"] for o in c["operations"]) for c in rows),Counter())),
            rejections=dict(sum((Counter(c["rejections"]) for c in rows),Counter())),
            parked_protected_phase1=sum(c["phase"]==1 and c["protected_floor_touched"] for c in rows),
            dynamic_closes=sum(len(c["forced_closes"]) for c in rows))
    result=dict(
        schema="PROP-OVERNIGHT-V5-RESULTS-v1",local_date="2026-11-15",
        created_utc=datetime.now(timezone.utc).isoformat(),
        decision="NO_GO_V5_PROMOTION; SOURCE_AND_EXACT_MC_GAPS_REMAIN",
        prop_qualified=False,exact_bootstrap_qualified=False,actual_payout_received=False,
        comparison=[dict(name=n,metrics=m,distinct_funded_paths=p)
                    for n,m,p in zip(labels,compared,uniqueness)],
        composition=d,release=release,source_recovery=third,
        additional_source_census=read(JOB/"workspace-additional-filename-census.json"),
        excluded_upstream_fixtures=read(JOB/"excluded-upstream-fixtures.json"),
        blind_holdout_audit=source,holdout_price_columns_parsed=0,
        holdout_strategy_signals=0,holdout_pnl_calculations=0,
        drawdown=dd,forensic=forensic,mechanism_trials=trials,
        continuous_selection_recheck=continuous,
        reference_books=[brief(b) for b in eurbooks],
        operation_summary=operation_summary,
        accounts=[brief(c) for c in cases],
        funded_rows=[brief(c) for c in cases if len(c["phase_passes"])==2],
        accounting_parity={k:v for k,v in parity.items() if k!="records"},
        bootstrap=mc,bootstrap_parity=stat,tests=tests,
        scope_completion=dict(
            ws0="MERGED_PR82_AND_BRANCH_CREATED",
            ws1="AUDIT_DONE;GBP2022_2024_M1_TICK_AND_17US500_ENDPOINTS_BLOCKED;NO_THIRD_SLEEVE",
            ws2="DIAGNOSED;D1_D2_TRIALS_REJECTED;PARENT_RETAINED",
            ws3="IMPLEMENTED_TESTED;NO_HISTORICAL_HARVEST_TRIGGER_OR_PAYOUT",
            ws4="72_TICK_ACCOUNTS_DONE;10000_PATHS_PER_MODEL_BLOCK_AND_MODE_PROXY_ONLY;EXACT_MC_NOT_QUALIFIED",
            ws5="ACCOUNTING_PARITY_AND_TESTS_PASS;PR_CI_IN_DELIVERY_RECEIPT"),
        review="same implementer alternate accounting and scalar/vector checks, no independent human/model reviewer",
        broker_calls=0,paid_provider_calls=0,model_provider_calls=0,
        private_job=str(JOB),
        artifacts=[dict(name=p.name,sha256=digest(p)) for p in sorted(JOB.glob("*.json"))
                   if p.name not in ("status.json","delivery-receipt.json")])
    write_json(OUT.with_suffix(".json"),result)
    lines=[
        "# V5 — không nâng cấp ứng viên Challenge; payout vẫn bằng 0",
        "",
        "**Kết quả:** V5 chỉ qua cả hai vòng ở 1/36 cửa sổ ASYM, 0/36 SYM, "
        "so với 3/36 và 2/36 của V4. Peak-to-valley vẫn khoảng 12,96% vốn đầu, "
        "chưa đạt mục tiêu < 8,5–9,5%. Sàn bảo vệ lợi nhuận giảm rủi ro trả lại "
        "lãi ở một số đường, nhưng làm nhiều tài khoản đứng lại trước đích.",
        "",
        "Đã thực thi các workstream trong phạm vi dữ liệu/công cụ hiện có, "
        "**không tuyên bố mọi acceptance đã đạt**: GBP không có M1/tick 2022–2024 "
        "để dựng ledger thật; một số nguồn vẫn thiếu; bootstrap 10.000 đường "
        "chỉ là stress surrogate theo ngày, chưa tương đương tick V5. "
        "Không chứng minh chiến lược có lãi bền, payout thật hoặc thu nhập chính.",
        "",
        "Task `36b050c6-aa94-4b8c-bb1d-8c5520b23a61`; PR82 đã merge `5beeb75`, "
        "xóa branch V4, làm trên `codex/prop-overnight-v5`. Ngày bàn giao "
        "15/11/2026 Asia/Saigon. Giữ VI Dubber WIP và Trader pin; không broker/model/"
        "paid-provider hoặc tải thêm lịch sử từ nguồn mới.",
        "",
        "## 1. Sáu cột so sánh 2022–2024",
        "",
        "| Chỉ tiêu | "+" | ".join(labels)+" |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for label,key,kind in (
        ("Qua vòng 1","step1","count"),("Qua cả hai vòng","both","count"),
        ("Trung vị hoàn tất hai vòng*","both_median_months_completed_only","months"),
        ("Số payout mô phỏng","payouts","int"),("USD trả trader trong mô hình","trader_payout_usd","usd"),
        ("Worst daily loss","worst_daily_pct","pct"),("Worst static loss","worst_static_pct","pct"),
        ("Peak-to-valley DD","worst_peak_dd_pct","pct"),("Modeled breaches","breaches","int")):
        cells=[]
        for c in compared:
            value=None if c is None else c[key]
            cells.append("N/A" if value is None else f"{value}/36" if kind=="count"
                         else f"{value:.2f} tháng" if kind=="months" else f"${value:,.2f}"
                         if kind=="usd" else f"{value:.3f}%" if kind=="pct" else str(value))
        lines.append("| "+label+" | "+" | ".join(cells)+" |")
    lines.append("| Đường funded riêng biệt | "+" | ".join("N/A" if v is None else str(v) for v in uniqueness)+" |")
    lines+=[
        "",
        "*Chỉ những cửa sổ đạt, không dự báo thời gian cho mọi tài khoản. "
        "Cửa sổ tháng chồng lấn và cùng dữ liệu tương lai; một đường funded "
        "riêng biệt cũng chưa là một phép thử thống kê độc lập. Cột sleeve3 "
        "N/A vì không có nguồn/ứng viên đạt, không sao chép số V5 để lấp cột. "
        "DD% trong bảng chia cho vốn đầu 50k; peak-to-valley khác static floor.",
        "",
        "V5 ASYM hoàn tất từ mốc 01/07/2023; funded cuối mẫu còn $49.683,57, "
        "không payout. V5 không cải thiện điểm nghẽn kinh tế bằng việc thêm "
        "bộ điều khiển. Không mở trial 3 hoặc giảm tiêu chí sau kết quả.",
        "",
        "## 2. GBPUSD và 28 cấu hình thiếu giá",
        "",
        "- Rà filenames ở backup E:, workspace D: và Trader worktree C:; QDM chỉ "
        "list EUR/XAU đang cache. GBP có H1 từ nghiên cứu cũ nhưng không có "
        "M1/tick 2022–2024 đủ phạm vi. Fixture upstream GBP chỉ tháng 02/2012, "
        "AUD tick chỉ 30–31/01/2020, USDJPY 2013/2019; loại vì sai thời kỳ, "
        "không dùng làm lịch sử thật. Không dựng M1 từ H1 hoặc bịa Ask.",
        "- 28 cấu hình ban đầu là **24 US500 + 4 AUDUSD**, không phải 28 chiến lược "
        "GBP. Tái dùng V3 đã sửa clock của US500: khôi phục 715/732 endpoint "
        "thiếu ban đầu; 17 còn unknown trên ngày lễ/đóng sớm. Không đếm thành "
        "715 giao dịch mới hoặc nhận công khôi phục đó cho V5.",
        "- Bốn AUD chỉ có nguồn H1 với các khoảng thiếu, chưa có M1/tick "
        "thay thế. US500 còn carry/dividend/spec và scale/retention chưa đủ; "
        "GBP chưa vượt cổng source nên chưa thể chạy Stage-0/1 chuẩn mới.",
        "",
        "**Không chọn sleeve #3.** `source-recovery.cells` trong JSON đối chiếu "
        "từng cấu hình với số raw/priced/fills/coverage cũ. Kết quả V2/V3 âm/"
        "unknown giữ nguyên. Đây là source blocker, không phải chứng minh GBP "
        "không có edge. Chưa hoàn tất yêu cầu dựng GBP M1/tick ledger thật.",
        "",
        "## 3. Blind holdout audit — chỉ timestamp",
        "",
        "| Asset | M1 records | Timestamp đầu/cuối | Ngày thường 07–21 UTC đủ timestamp* | Ngày thường còn gap/nghỉ chưa phân loại |",
        "|---|---:|---|---:|---:|"]
    for s in source["assets"]:
        lines.append(f"| {s['asset']} | {s.get('minutes','N/A')} | "
                     f"{s.get('first','N/A')} → {s.get('last','N/A')} | "
                     f"{s.get('weekdays_complete','N/A')} | {s.get('weekdays_unknown','N/A')} |")
    lines+=[
        "",
        "*Trong 478 ngày thường 01/01/2025–31/10/2026, đủ timestamp ở đây chỉ "
        "có nghĩa khoảng thiếu dài nhất trong 07–21 UTC <= 15 phút. Chưa phân biệt "
        "hết ngày lễ với lỗi nguồn; không tự gán ngày thiếu là nghỉ hợp lệ. "
        "Từng ngày, gap count và các khoảng liên tiếp được lưu trong JSON.",
        "",
        "QDM export chỉ DateTime, loader từ chối bất kỳ cột Bid/Ask/OHLC nào. "
        "Không tính indicator/tín hiệu/PnL và không update/download provider. "
        "Gold chỉ tới 13/10/2026, EUR tới 07/10; GBP chưa có nguồn. Không chứng "
        "nhận được khoảng nào có **đường Bid/Ask/tick đủ Stage-1** chỉ từ "
        "timestamp. Cần tick/M1 admission, feed/session/news/spec và exposure "
        "manifest riêng; không gọi holdout hoàn toàn sạch vì chưa chạy ở đây.",
        "",
        "## 4. Giải phẫu 35,76R và hai trial đã khóa",
        "",
        f"Đỉnh UTC `{date(dd['start'])}` ở ${dd['reference_peak_usd']:,.2f}; "
        f"đáy UTC `{date(dd['trough'])}` ở ${dd['reference_trough_usd']:,.2f}. "
        f"Risk tham chiếu $150; mức giảm 35,757R. Recovery trên tick sau đáy: "
        f"{date(forensic['exact_tick_recovery_time']) if forensic['exact_tick_recovery_time'] else 'chưa có đến cuối2023'}, "
        "không tự chốt ngày hết drawdown tại cuối năm.",
        "",
        f"Đối chiếu cả closed+floating tại hai đầu: BUY đóng góp "
        f"{forensic['drawdown_contribution_R']['BUY']:.3f}R, SELL "
        f"{forensic['drawdown_contribution_R']['SELL']:.3f}R, tổng khớp 35,757R. "
        "Không phải chỉ một chiều gây lỗ. Trong 63 tín hiệu mở giữa hai mốc, "
        "15 có biên Á > 2 ATR, tổng−6,254R; 44 đi khác H4, tổng−10,714R. Các nhóm "
        "có giao nhau và khác boundary floating, không cộng các khoản đó "
        "để gọi là tỷ lệ nguyên nhân nhân quả.",
        "",
        "| Vị thế vẫn mở 12 UTC | Số lệnh | Net R đánh dấu 12 UTC | Net R lúc thoát thật | Chênh sau 12 UTC |",
        "|---|---:|---:|---:|---:|"]
    for y,r in forensic["london_by_year"].items():
        lines.append(f"| {y} | {r['held_at12']} | {r['net_at12_R']:+.3f} "
                     f"| {r['actual_net_R']:+.3f} | {r['change_after12_R']:+.3f} |")
    lines+=[
        "",
        "Ở cohort còn sống đến 12 UTC, giữ tiếp thực tế cộng thêm lợi nhuận "
        "hai năm. Đây có survivor/SL conditioning, không phải backtest mới "
        "đóng mọi lệnh 12 UTC. Chưa có bằng chứng đơn giản rằng đóng hết London "
        "giải quyết drawdown; không mở biến thể exit thứ ba.",
        "",
        "| Cơ chế EUR | Net R Dev liên tục | Max DD(R) | Net R 2022/2023, giữ state qua năm | Quyết định |",
        "|---|---:|---:|---:|---|"]
    for mechanism in ("PARENT","D1","D2"):
        b=next(x for x in eurbooks if x["mechanism"]==mechanism and x["start_msc"]==START and x["end_msc"]==END)
        yr=continuous["annual_reference_net_R"][mechanism]
        reason="Giữ baseline" if mechanism=="PARENT" else "Không đạt các cổng đã khóa"
        lines.append(f"| {mechanism} | {b['net_R']:+.3f} | {b['max_equity_R_DD']:.3f} "
                     f"| {yr['2022']:+.3f}/{yr['2023']:+.3f} | {reason} |")
    lines+=[
        "",
        "D1 bỏ EUR khi biên Á > 2 ATR14H1 biết trước entry. D2 dùng shadow "
        "canonical closedNetR riêng từng sleeve: DD >= 8R giảm nửa risk, hồi 4R "
        "từ đáy hoặc đạt đỉnh cũ thì trả lại nominal. Shadow cập nhật chỉ tại "
        "exit thật của tín hiệu gốc; không đọc netR tương lai lúc vào lệnh. "
        "NetR sổ so sánh được chuẩn hóa về cùng $150, không cộng các R có "
        "risk khác nhau rồi gọi đó là cùng một mức lợi nhuận.",
        "",
        "D2 giảm EUR DD nhưng mất quá nhiều tốc độ 2023 và net danh mục; D1 "
        "làm 2022 âm và không giảm DD. Cổng yêu cầu giữ >= 80% net và giảm DD "
        "đã khóa trước đo, nên **chọn PARENT**, không ghép D1 + D2. Recheck sổ "
        "liên tục xác nhận cùng quyết định: annual standalone diagnostics "
        "khởi tạo cold state mới, không được dùng thay carried-state year cuts.",
        "",
        "## 5. Ratchet/harvester đã thay gì?",
        "",
        "- Vòng 1: equity/balance đạt +7% thì cap $125; rơi về +5% thì cap $90 "
        "và gửi yêu cầu đóng trên quote kế tiếp của từng tài sản. Lệnh mới "
        "phải giữ projected stop reserve trên +5%; không giả sàn được bảo đảm "
        "khi gap/slippage.",
        "- Vòng 2: đạt +3,5% thì cap $100. Giữ stop tự nhiên, phase/reset owner "
        "và cổng 8% / cap 1,6% của V4.",
        "- Funded: closed balance >= 50.500 trong 48h cuối chu kỳ 14 ngày thì "
        "freeze entry, đóng phiên trước due; >= 51.000 thì lock và thanh lý "
        "trên quote thật tiếp theo. Request chỉ khi đủ ngày, flat và lãi >= 20; "
        "debit toàn bộ profit, 80/20, không mô phỏng approval/chuyển khoản.",
        "",
        "| Model | Ratchet armed | Sàn +5% chạm | Đóng trên quote thật | Tài khoản phase 1 còn đứng ở sàn | Harvest freeze/lock |",
        "|---|---:|---:|---:|---:|---:|"]
    for model,s in operation_summary.items():
        e=s["events"]
        lines.append(f"| {model} | {e.get('RATCHET_ARMED',0)} | {e.get('PROTECTED_FLOOR',0)} "
                     f"| {s['dynamic_closes']} | {s['parked_protected_phase1']} "
                     f"| {e.get('PRE_PAYOUT_FREEZE',0)+e.get('PROFIT_LOCK_IDLE',0)} |")
    lines+=[
        "",
        "Đóng để giữ sàn có thể làm balance rơi hơi dưới 52.500 sau phí; "
        "khi flat gần sàn, không còn đủ room mở lệnh mà vẫn giữ projected floor. "
        "Vì thế nhiều tài khoản đứng lại. Tự bỏ sàn để tiếp tục sẽ là một "
        "trial khác; lượt này giữ đúng quy tắc, ghi failure rõ.",
        "",
        "Không có chu kỳ funded nào đạt ngưỡng freeze/lock trong 72 cửa sổ. "
        "Harvester đã được kiểm bằng fixtures nhưng **chưa có lịch sử "
        "payout thành công** để xác nhận vận hành. Đóng trước due không bảo "
        "đảm tiền còn dương, quỹ duyệt hoặc tiền về 100%. Daily < 5% / static < 10% "
        "trong model không đồng nghĩa tài khoản FTMO thật đạt mọi điều kiện "
        "news, margin, quote, commission/swap hoặc session profile.",
        "",
        "## 6. Block-bootstrap 10.000 đường — stress surrogate, chưa exact V5",
        "",
        "Mỗi model/mỗi block có 10.000 đường 12 tháng / 252 business days; cả rổ "
        "resample cùng block 20 ngày, sensitivity 5 ngày, seed 20261115. Giữ serial "
        "order trong block và thứ tự high/low ngày đã quan sát, không trộn "
        "hai asset độc lập. Funded-start là experiment riêng, không lấy "
        "payout conditional-funded làm tiền kỳ vọng từ lúc mua Challenge.",
        "",
        "**Giới hạn quyết định:** surrogate hiện thực hóa equity ngày thành "
        "cash flat cuối ngày, chưa tái tạo vị thế 48h/cap/reserve/lot/next-quote "
        "fill; chu kỳ 14 ngày xấp xỉ 10 business days. Nó có thể tạo payout mà "
        "exact engine không tạo. Không dùng các tỷ lệ dưới đây làm xác suất "
        "pass tương lai hoặc coi Workstream4 exact-MonteCarlo đã đạt.",
        "",
        "| Model/block | P1 trong proxy | Hai vòng <= 12 tháng proxy | Breach proxy | StaticDD P50/P75/P95 | Mean payout/năm nếu bắt đầu funded* |",
        "|---|---:|---:|---:|---|---:|"]
    for model,blocks in mc["results"].items():
        for block,r in blocks.items():
            c=r["challenge"];fund=r["funded_start"]
            pct="/".join(f"{v:.2f}%" for v in c["max_static_percentiles_pct"])
            lines.append(f"| {model}/{block} | {c['step1_rate']:.2%} "
                         f"| {c['both_12month_rate']:.2%} | {c['breach_rate']:.2%} "
                         f"| {pct} | ${fund['mean_trader_payout_usd']:,.2f} |")
    lines+=[
        "",
        "*Đây là output của mô hình daily-flat lý tưởng hóa, không lời hứa "
        "thu nhập, không trừ challenge/retry/vận hành/thuế, không thay cho "
        "exact historical payout 0. Từ challenge-start, mean payout nhỏ hơn; "
        "giữ riêng trong JSON. Đổi 20 → 5 day blocks đổi kết quả; seam không giữ "
        "được tự tương quan dài hơn block. Chỉ 3 năm dữ liệu đã exposed/selected "
        "không đủ chứng nhận tail risk tương lai.",
        "",
        "512 đường scalar đối chiếu vector đạt. Trên chuỗi lịch sử nguyên "
        "thứ tự, surrogate và exact Jan 2022 khác balance/DD "
        "(chi tiết`bootstrap_parity.historical_comparison`), nên **không "
        "claim model-equivalence**. Cần bootstrap từ event tape có carry "
        "state/quote fills và parity lifecycle trước khi dùng để qualification.",
        "",
        "## 7. Kiểm chứng, lỗi đã giữ và trạng thái cuối",
        "",
        f"- {tests['tests']} tests đạt; V5 có{tests['v5_tests']} fixtures "
        "cho causal cold-state, ratchet, freeze/lock, quote freshness/ordinal, "
        "reward full-debit, timestamps và bootstrap.",
        f"- Oracle{parity['accounts']} tài khoản: {parity['accepted']:,} "
        f"admissions,{parity['rejected']:,} rejections,{parity['money_bridges']:,} "
        f"cost bridges,{parity['dynamic_native_fills']} dynamic native fills; "
        f"{parity['joint_quotes']:,} quote updates đối chiếu timestamp. Hạch "
        "toán funding vào cash thay cho floating của producer; cash/DD/phase/"
        "payout khớp. Cùng implementer, không independent human/model reviewer.",
        f"- Composition commit `{release['commit']}` trước release `{release['utc']}` "
        "và lần traversal 2024; code/source/rule pins khớp. Chọn chỉ Dev; "
        "2024 đã exposed, không clean OOS.",
        "- Lỗi holiday`flat_utc=null` dừng trước output tài chính; sửa ở "
        "session owner và có fixture. Lượt reference đầu dùng nhầm prop "
        "reserve làm park signal curve: giữ nguyên dưới "
        "`development-attempt2-reference-admission-bug`, sửa reference "
        "admissions rồi chạy lại; không thêm threshold/trial. Hai output "
        "lỗi không được dùng chọn hoặc công bố như kết quả hợp lệ.",
        "- Year-carry audit dùng continuous closed-cash cuts xác nhận D1/D2 "
        "vẫn rớt, thay cách đọc annual standalone windows. Không che sai "
        "khác warm-start của các sổ chẩn đoán năm.",
        "",
        "**Quyết định:** No-Go nâng V5 thành ứng viên Challenge; không mua, "
        "không tăng risk, không mở holdout để cứu cấu hình đã yếu trong Dev/"
        "Historical Validation. Giữ V3/V4 làm benchmark. Chặng có ích tiếp "
        "theo là source admission GBP 2022–2024 và event-level bootstrap parity "
        "nếu được giao; không thêm lớp điều khiển vì kỳ vọng nó tự tạo alpha.",
        "",
        "V5 đã có kết quả/review cho từng workstream nhưng **source recovery "
        "GBP/những đoạn thiếu và exact 10.000-path V5 qualification còn chưa "
        "đạt**. Đó là giới hạn được bàn giao, không được đổi nhãn thành PASS "
        "chỉ vì code/test/CI xanh.",
        "",
        f"Private job: `{JOB}`. Full 72 ledgers, failed attempts, EUR minute "
        "extrema, raw timestamp exports/daily coverage, scalar paths và "
        "10.000 path outcomes giữ riêng. JSON tracked giữ summaries, source/"
        "freeze hashes, từng ngày coverage/intervals, trials và các blocker.",
        ""]
    OUT.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")
    print(OUT.with_suffix(".md"),flush=True)


if __name__=="__main__":build()
