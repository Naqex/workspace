"""Bounded V20 report; reports failures and unknowns without changing the experiment."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal, ROUND_FLOOR
import json
import numpy as np
from prop_v20_common import *
from prop_v20_campaign import verify

REPORT=Path("planning/research/VOLTARGET-SHADOW-V20-RESULTS-20261117")


def fmt(value,n=2):
    return "—" if value is None else f"{value:,.{n}f}".replace(",","_").replace(".",",").replace("_",".")


def table(headers,rows):
    return ["| "+" | ".join(headers)+" |","|"+"|".join("---" for _ in headers)+"|"]+[
        "| "+" | ".join(str(v).replace("|",r"\|") for v in row)+" |" for row in rows]


def economics(profiles):
    import prop_portfolio_accounts as portfolio
    from prop_v18_costs import cost_bindings
    from prop_v15_accounts import exact_quantity
    rows=[]
    for source in ("PRIMARY","STRICT"):
        trades=read(V19/f"Full-OLHC-{source}-trades.json")
        for pct in (100,150) if source=="PRIMARY" else (100,):
            for p in profiles:
                net=0.;skipped=0
                with cost_bindings(pct):
                    for t in trades:
                        weighted=(Decimal(150)*Decimal(str(p["weights"][t["id"]]))).quantize(Decimal(".01"),rounding=ROUND_FLOOR)
                        requested=float((weighted*Decimal(str(p["k"]))).quantize(Decimal(".01"),rounding=ROUND_FLOOR))
                        try:q=exact_quantity(t,requested)
                        except ValueError:skipped+=1;continue
                        net+=portfolio.trade_money(t,q,"SYM_FLAT",150)["net_usd"]
                rows.append(dict(profile=p["name"],source=source,friction=pct,net_USD=net,
                    net_R_base150=net/150,minlot_skips=skipped,reference_base_risk_USD=150,
                    no_house_money_or_account_admissions_in_unit_book=True))
    return rows


def collect():
    frozen=verify();fit=read(JOB/"fit.json")
    history=[];monte=[];dev_accounts=full_accounts=0
    for tag in ("OLHC","OHLC"):
        for mode,pct in (("PRIMARY",100),("PRIMARY",150),("STRICT",100)):
            prefix=f"Full-{tag}-{mode}-{pct}"
            audit=read(JOB/(prefix+"-audit.json"))
            if not audit["passed"] or audit["accounts"]!=318:raise ValueError("incomplete_full_account_audit")
            full_accounts+=audit["accounts"]
            books=read(JOB/(prefix+"-accounts.json.gz"))
            for value in read(JOB/(prefix+"-summary.json"))["cases"]:
                selected=[r for r in books if r["kind"]=="CHALLENGE" and r["profile"]==value["profile"] and r["start_msc"]>=DEV_END]
                history.append(dict(order=tag,mode=mode,friction=pct,**value,recent_starts=len(selected),
                    recent_completions=sum(any(p["phase"]==2 for p in r["phase_passes"]) for r in selected)))
        for p in fit["profiles"]:
            path=JOB/f"MC-{p['name']}-{tag}-summary.json";r=read(path)
            if r["paths"]!=5000 or r["accounts_fully_audited"]!=10000:raise ValueError("incomplete_MC_full_audit")
            monte.append(dict(**r,path=path.name,sha256=sha(path)))
    for tag in ("OLHC","OHLC"):
        for mode in ("PRIMARY","STRICT"):
            for pct in (100,150):
                a=read(JOB/f"Dev-{tag}-{mode}-{pct}-audit.json")
                if not a["passed"] or not a["V19_unscaled_parity"]["all_fields_equal_except_labels"]:
                    raise ValueError("Development_parity_not_verified")
                dev_accounts+=a["accounts"]
    parent=read("planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json")
    tests,smoke=read(JOB/"tests-final-matrix.json"),read(JOB/"smoke-final-results.json")
    if tests["preserved_V19_IDs"]!=1216 or not tests["zero_skip"]:raise ValueError("missing_baseline_tests")
    r=dict(schema="V20-results-v1",prop_qualified=False,actual_broker_orders=0,actual_payout_USD=0,
        decision="RESEARCH_ONLY_EXECUTION_AND_SOURCE_GATES_REMAIN_OPEN",merged_PR98="9fba6e006538fe933a11faaf0faf8e02a9e1b249",
        frozen=frozen,fit=fit,historical=history,monte=monte,economics=economics(fit["profiles"]),
        new_Development_full_audits=dev_accounts,new_historical_full_audits=full_accounts,
        new_MC_full_audits=sum(v["accounts_fully_audited"] for v in monte),
        parent_historical=[v for v in parent["historical"] if v["version"]=="V16"],
        parent_monte=[v for v in parent["monte"] if v["version"]=="V16" and v["mode"]=="PRIMARY" and v["friction"]==100],
        gap_localization=read(JOB/"gap-localization.json"),observer=dict(
            environment=read(JOB/"observer-environment-verified.json"),CLI=read(JOB/"observer-final-CLI-receipts.json"),
            generated_Development_replay=read(JOB/"Development-generated-replay-final-verification.json"),
            native_terminal_verified=False,MQL5_exporter_compiled_or_executed=False,
            spec_sessions_commission_and_native_news_not_verified=True,
            quickstart="planning/research/QUICKSTART-FTMO-FREE-TRIAL.md"),
        engineering=dict(tests=tests,smoke=smoke,storage=read(JOB/"storage-final-summary.json"),
            import_profile=dict(path="smoke-before.pstats",not_final_timing=True),
            indexed_import_diagnostics=read(JOB/"smoke-indexed-import-diagnostics.json"),
            temporary_root_diagnostics=read(JOB/"smoke-temp-diagnostics.json"),
            lean_startup_diagnostics=read(JOB/"smoke-lean-startup-diagnostics.json")),
        limits=["Historical validation already exposed; no clean OOS claim.",
            "Variance matching does not equal maximum drawdown matching. Actual k is formula-limited.",
            "No new historical observations; 32 source-uncertain trades retained.",
            "Bootstrap is conditional on historical quarter blocks and copied source clocks, not future probability.",
            "New MC matrix is PRIMARY100 only; source/cost stress measured in historical matrix, not every bootstrap cell.",
            "Both orderings are M1 scenarios; Ask proxy and fixed first-passage cost stress are not actual target fills.",
            "Separate oracle is same author/feed, not independent human review.",
            "Native terminal unavailable; replay is not broker execution or measured slippage.",
            "Payout split/timer remain inherited proxies, not current target-account contract.",
            "Compression preserves bytes, not source validity; snapshots logical/non-atomic, physical savings unmeasured."])
    text=json.dumps(r,indent=2,ensure_ascii=False)
    if len(text.encode())>1048576:raise ValueError("bounded_V20_result_over_1MiB")
    REPORT.with_suffix(".json").write_text(text,encoding="utf-8",newline="\n")
    write_report(r);event("V20_report_written",bytes=len(text.encode()),report=str(REPORT))


def write_report(r):
    fit=r["fit"];tests=r["engineering"]["tests"];smoke=r["engineering"]["smoke"]
    lines=["# V20 — đi vốn O2, dữ liệu thiếu, MT5 shadow và nén evidence","",
        "**Đã đo theo ngân sách; chưa đủ điều kiện Challenge hoặc gửi lệnh broker.** "
        "Các target tốc độ/tiết kiệm là kết quả cần đo, không tự được gắn PASS.","",
        "PR98/head `75edaa0` merge `9fba6e0`; nhánh V19 local/remote đã xóa. "
        "V20 đăng ký `1cee37d`, financial freeze `2dc7a1d`; PR99 để mở, không merge tự động. "
        "Giữ Trader pin, VI WIP, mọi nguồn/freezes/failed attempts. No Astra/broker orders.","",
        "## 1. Đi vốn theo phương sai và định vị 32 lệnh thiếu giá","",
        "O2 là nghiệm covariance có ràng buộc đã sửa đúng ở V19; không phải heuristic inverse-vol "
        "ban đầu bị bác. Giảm phương sai 44,53% không bảo đảm MaxDD giảm cùng tỷ lệ. "
        "8% là mục tiêu nội bộ, khác trần static 10% của hồ sơ quỹ. Yêu cầu cùng DD với V16 "
        "và đồng thời dưới 8,2% không được coi là tương đương với công thức hệ số.","",
        f"Theo công thức khóa trên tất cả tám Dev cases: `k_sigma` = **{fmt(fit['k_sigma'],6)}**, "
        f"`k_DD = 8 / {fmt(fit['source_Dev_worst_static'],4)}` = **{fmt(fit['k_DD'],6)}**; "
        f"hệ số cuối **{fmt(fit['k_vol'],6)}×**, chỉ thêm khoảng {fmt((fit['k_vol']-1)*100,3)}% risk yêu cầu. "
        "Không nâng lên 1,34× để cứu tốc độ. Actual MaxDD phải replay vì minlot/caps/rejects đổi đường vốn.","",
        "Unscaled O2 đã có cushion phase1 từ V19. `O2_VOL` tắt cushion để đo scale riêng; "
        "`O2_VOL_CUSHION` giữ cushion cũ, không thêm gamma/bonus mới. "
        f"{r['new_Development_full_audits']} Dev accounts audit đầy đủ; unscaled khớp mọi field kinh tế "
        "của V19, ngoại trừ tên version. Freeze trước full outcomes; Validation cũ đã exposed.",""]
    lines+=table(["Profile Dev","Worst static %","Worst daily %","Worst hai vòng"],[
        [v["profile"]["name"],fmt(v["worst_static"],4),fmt(v["worst_daily"],4),v["worst_completions"]]
        for v in r["frozen"]["Development"]])
    lines += ["","105 mốc bắt đầu chồng lấn; median chỉ trên các cửa sổ hoàn tất. "
        "Bảng OLHC; JSON giữ cả OHLC và ba kịch bản nguồn/phí. Không cộng Net R của các mốc "
        "tài khoản chồng nhau thành hiệu suất danh mục.",""]
    base=next(v for v in r["parent_historical"] if v["order"]=="OLHC" and v["mode"]=="PRIMARY" and v["friction_pct"]==100)
    lines+=table(["Profile / source / phí","Hai vòng/105","Median tháng","Daily %","Static %","Recent hai vòng"],
        [["V16 / PRIMARY / 1×",base["funded"],fmt(base["median_months"]),fmt(base["worst_daily"],4),fmt(base["worst_static"],4),f"{base['recent_completions']}/{base['recent_starts']}"]]+
        [[f"{v['profile']} / {v['mode']} / {v['friction']/100:g}×",v["funded"],fmt(v["median_months"]),
          fmt(v["worst_daily"],4),fmt(v["worst_static"],4),f"{v['recent_completions']}/{v['recent_starts']}"]
         for v in r["historical"] if v["order"]=="OLHC"])
    lines += ["","Sổ tham chiếu dùng 150USD × sleeve weight × k rồi lot floor; R dưới đây luôn "
        "quy về **150USD**, không đổi mẫu số để giấu tăng size. Cushion/account caps không áp trong "
        "unit book, nên hai bản VOL có cùng reference economics; lifecycle table mới xét cushion.",""]
    lines+=table(["Profile / source / phí","Net USD tham chiếu","Net R /150USD","Minlot skips"],[
        [f"{v['profile']} / {v['source']} / {v['friction']/100:g}×",fmt(v["net_USD"]),fmt(v["net_R_base150"]),v["minlot_skips"]]
        for v in r["economics"]])
    lines += ["","Cùng 5.000 draws/36 tháng, prefix12/18/24; không chọn lại quý/năm. "
        f"{r['new_MC_full_audits']} new MC ledgers và {r['new_historical_full_audits']} full historical ledgers "
        "qua oracle toàn bộ, cùng tác giả/feed. New MC chỉ PRIMARY100, cả hai ordering; "
        "historical matrix giữ cost/source stress. Tần suất resampling không là xác suất tương lai.",""]
    lines+=table(["Bản OLHC PRIMARY100","Hai vòng12/18/24/36 %","Median khi đậu","Funded riêng USD/năm","Sau Challenge USD/năm"],[
        ["V16","/".join(fmt(h["both_pct"]) for h in p["horizons"]),fmt(p["conditional_median_months"]),fmt(p["mean_annual_payout_USD"]),"chưa đo trong receipt này"]
        for p in r["parent_monte"] if p["order"]=="OLHC"]+
        [[v["profile"],"/".join(fmt(h["both_pct"]) for h in v["horizons"]),fmt(v["conditional_median_months"]),
          fmt(v["mean_annual_payout_USD"]),fmt(v["mean_post_challenge_payout_USD_per_elapsed_year"])]
         for v in r["monte"] if v["order"]=="OLHC"])
    lines += ["","Payout đều mô phỏng, giữ zeros và chưa trừ phí Challenge/retry/thuế/vận hành. "
        "Funded riêng giả định đã Funded từ ngày đầu; khác tiền rút sau hai vòng. Payout thực nhận0.",""]
    lines+=table(["Năm","Lệnh chưa xác minh/tổng","Tỷ lệ %","PRIMARY R","STRICT R"],[
        [v["year"],f"{v['unverified_trades']}/{v['signals']}",fmt(v["unverified_pct"]),fmt(v["primary_net_R"]),fmt(v["strict_net_R"])]
        for v in r["gap_localization"]["rows"]])
    lines+=table(["Giai đoạn","Unknown/tổng","PRIMARY R","STRICT R"],[
        [v["period"],f"{v['unverified']}/{v['signals']}",fmt(v["primary_net_R"]),fmt(v["strict_net_R"])]
        for v in r["gap_localization"]["periods"]])
    lines += ["","32 lệnh chia đều16/16 giữa hai giai đoạn; tỷ lệ gần đây thấp hơn nhưng chưa sạch. "
        "Giữ55 gap occurrences riêng, không nhầm với32 trade identities. Không xóa lệnh thiếu hoặc "
        "chọn bắt đầu năm2022 từ bảng này; không có quote mới/certificate mới.","",
        "## 2. MT5 read-only / shadow và quickstart","",
        "[Ba bước chạy](QUICKSTART-FTMO-FREE-TRIAL.md). Runtime observer riêng đã cài/khóa "
        "MetaTrader5, pyarrow, zstandard, NumPy/tzdata; smoke-test imports và Parquet roundtrip. "
        "Không có terminal64.exe đang chạy ở probe; **chưa attach tài khoản FTMO thật**.","",
        "`python -m tooling.ai_engines.ftmo_trial_runner --mode read-only` và `--mode shadow-paper` "
        "dùng cùng implementation hiện có. Không có terminal thì replay được gắn nhãn, không ngầm "
        "gọi là live. CLI có spec snapshot năm asset, parity diff, timestamped Parquet zstd9, "
        "quote/receive clocks và shadow ledger/journal. Account phải DEMO/TRIAL USD đúng FTMO; "
        "không login/restart/order_send/order_check.","",
        "Replay mặc định có intent fixture. Thêm replay Development sinh tín hiệu thật từ "
        "23.857 H1 đã đóng: guard chặn khi SL không thuộc tick-grid0,01; giữ failed attempt. "
        "Fixture grid nghiên cứu0,001 sau đó có một entry paper, không thay SL hay khẳng định "
        "broker dùng grid0,001. Đây là M1 OLHC scenario, không tick broker quan sát. "
        "Vị thế paper còn mở được giữ trong ledger khi process kết thúc, không ép đóng lấy số đẹp.","",
        "Session APIs đầy đủ cần MQL5 export bridge; exporter chưa compile/chạy trên terminal. "
        "Thiếu session/timezone/holiday/news/seed parity thì native shadow chặn, không suy unknown "
        "là phiên an toàn. Spec của ba asset ngoài danh mục chỉ được ghi nhận, không tự trade. "
        "MFE/MAE từ quote đã thấy; quote-only không đo slippage. Chưa EA/broker readiness.","",
        "## 3. Nén giữ nguyên bằng chứng V19","" ]
    c=r["engineering"]["storage"]["compaction"]
    lines += [f"Nén **{len(c['removed'])} files** JSON/JSONL/NPY bằng Zstandard9: "
        f"{fmt(c['original_bytes']/2**30,3)}GiB → {fmt(c['compressed_bytes']/2**30,3)}GiB; "
        f"payload giảm **{fmt(c['net_payload_bytes_saved']/2**30,3)}GiB**. "
        "Mọi bản gốc/bản nén có SHA256; giải nén kiểm100% byte trước unlink, preflight toàn bộ "
        "original identities/hashes trước xóa. Chỉ apply sau khi financial readers đã xong.","",
        "MANIFEST và APPLIED receipt ở private V19 job/evidence-zstd-v20. New reader đọc JSON/NPY "
        "trực tiếp từ archive và trả canonical original SHA. Legacy frozen consumer cần đường file "
        "gốc có lệnh restore chính xác; không sửa source pinned hoặc xóa negative attempts. "
        "Test corruption, scope escape, drift, collision, hash và numpy dtype/values đều giữ.",""]
    lines+=table(["Kho","Trước GiB","Sau GiB","Delta GiB","Delta files","Lỗi trước/sau"],[
        [k,fmt(v["before"]["bytes"]/2**30,3),fmt(v["after"]["bytes"]/2**30,3),fmt(v["delta"]["bytes"]/2**30,3),
         v["delta"]["files"],f"{len(v['before_errors'])}/{len(v['after_errors'])}"]
        for k,v in r["engineering"]["storage"]["roots"].items()])
    lines += ["","Snapshot toàn kho bao gồm runtime/evidence V20 mới, khác payload tiết kiệm riêng "
        "V19. Không gọi delta logical/non-atomic là physical bytes freed; giữ lỗi đọc VI và WIP.","",
        "## 4. Full suite, smoke và bàn giao","",
        f"Full suite **{tests['tests']} PASS/0skip**, giữ đủ **1.216 V19 IDs**, wall "
        f"**{fmt(tests['total_wall_seconds'],3)}s**; target<16s: **{'đạt' if tests['target_under16'] else 'chưa đạt'}**. "
        "Năm runtime groups overlap; base giữ bốn worker. Workload có regression mới, không gọi "
        "đây là tốc độ whole-machine hay cùng một bài backtest9năm.","",
        f"Smoke đúng10 fresh serial processes/cùng78IDs: **{smoke['below078']}/10 <0,78s**, "
        f"median **{fmt(smoke['wall_median'],3)}s**, max **{fmt(smoke['wall_max'],3)}s**. "
        f"Target10/10: **{'đạt' if smoke['all_ten_below078'] else 'chưa đạt'}**; "
        f"median0,55–0,65s: **{'đạt' if smoke['median_target_met'] else 'chưa đạt'}**. "
        "Giữ mọi mẫu, không retry chọn streak; startup/import/fixture IO vẫn trong wall.","",
        "Runner thực là unittest, không pytest plugin. cProfile/importtime chỉ ra import filesystem "
        "probes và fixture IO; không đủ trace để quy chính xác mọi jitter cho GC/AV/disk. "
        "Index chỉ các module local đã ưu tiên, vẫn SourceFileLoader/source/pyc cũ; không đổi "
        "assertions hoặc prewarm ngoài timer. Paired diagnostic, temp-root và -S thử nghiệm giữ riêng; "
        "-S không được dùng trong final benchmark. Fixture vẫn tạo/đọc/xóa trên đĩa thật.","",
        "PR99 để mở; exact-head3CI/downloaded IDs chốt trong private `ci-exact-head-reconciliation.json` "
        "và `completion-receipt.json` sau push, không sửa HEAD để tự đóng dấu. Không có "
        "Challenge purchase, account reset, broker order hoặc triển khai sản phẩm.","",
        f"[JSON]({REPORT.with_suffix('.json').name}) · private job `{JOB}`.",""]
    REPORT.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8",newline="\n")


if __name__=="__main__":collect()
