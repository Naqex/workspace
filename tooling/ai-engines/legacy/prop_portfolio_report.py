"""Single owner report from V3's frozen decisions and verified ledgers."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prop_campaign_report import aggregate, compact, date_text
from prop_portfolio_common import (
    JOB, ATLAS, V1, MODELS, DECISION, read, write_json, digest,
)
from prop_portfolio_accounts import quantity_steps, trade_money

OUT=Path("planning/research/PROP-PORTFOLIO-V3-RESULTS-20261114")


def trimmed_model(model):
    return {k:v for k,v in model.items() if k!="daily"}


def tables(comparisons):
    lines=[]
    for model,rows in comparisons.items():
        lines += [
            "", "### "+("ASYM: proxy swap −45/−5" if model.startswith("ASYM") else
                         "SYM: stress swap −40/−40"), "",
            "| Chỉ tiêu | PR #79: A / risk v1 | PR #80: A / risk v2 | V3: A / balanced | V3: A + EUR / balanced |",
            "|---|---:|---:|---:|---:|",
        ]
        metrics=[
            ("Qua vòng 1",lambda x:f"{x['step1']}/36"),
            ("Hoàn tất cả hai vòng",lambda x:f"{x['both']}/36"),
            ("Số payout / USD trader",lambda x:f"{x['payouts']} / ${x['trader_payout_usd']:.2f}"),
            ("Lỗ ngày lớn nhất",lambda x:f"{x['worst_daily_pct']:.3f}%"),
            ("Lỗ dưới vốn đầu lớn nhất",lambda x:f"{x['worst_static_pct']:.3f}%"),
            ("Sụt giảm từ đỉnh lớn nhất",lambda x:f"{x['worst_peak_dd_pct']:.3f}%"),
            ("Vi phạm trong mô hình",lambda x:str(x["breaches"])),
            ("Trung vị thời gian qua vòng 1*",lambda x:
             "N/A" if x["step1_median_months_completed_only"] is None else
             f"{x['step1_median_months_completed_only']:.2f} tháng"),
            ("Trung vị hoàn tất hai vòng*",lambda x:
             "N/A" if x["both_median_months_completed_only"] is None else
             f"{x['both_median_months_completed_only']:.2f} tháng"),
        ]
        for label,render in metrics:
            lines.append("| "+label+" | "+" | ".join(render(r) for r in rows)+" |")
    return lines


def build():
    decision=read(DECISION);release=read(JOB/"validation-release.json")
    parity={name:read(JOB/name) for name in (
        "lifecycle-parity.json","source-parity.json","stage1-parity.json","regime-parity.json")}
    tests=read(JOB/"regression-tests.json")
    if not tests["passed"] or any(v["status"]!="PASS" for v in parity.values()):
        raise ValueError("report_requires_all_checks")
    regimes=read(JOB/"regime-comparison.json")
    selected=read(JOB/"final-satellite-decision.json")
    atlas=read(JOB/"satellite-decision.json")
    recovery=read(JOB/"endpoint-recovery.json")
    funded=read(JOB/"funded-diagnostic.json")
    cases={m:{s:read(JOB/f"lifecycle-{m}-{s}.json") for s in ("SINGLE","PORTFOLIO")}
           for m in MODELS}
    comparisons={
        m:[aggregate(read(V1/f"lifecycle-{m}.json")),
           aggregate(read(ATLAS/f"lifecycle-{m}.json")),
           aggregate(cases[m]["SINGLE"]),aggregate(cases[m]["PORTFOLIO"])]
        for m in MODELS
    }
    trades=read(JOB/"system-trades.json")
    satellite=[t for t in trades if t["asset"]=="EURUSD"]
    economics=[]
    for year in (2022,2023,2024):
        cohort=[t for t in satellite if t["day"].startswith(str(year))]
        parts=[trade_money(t,quantity_steps(t,150),"SYM_FLAT",150) for t in cohort]
        values=[p["net_R"] for p in parts]
        economics.append(dict(
            year=year,trades=len(cohort),buy=sum(t["side"]=="BUY" for t in cohort),
            sell=sum(t["side"]=="SELL" for t in cohort),net_R=sum(values),
            gross_usd=sum(p["gross_usd"] for p in parts),
            commission_usd=sum(p["commission_usd"] for p in parts),
            slippage_usd=sum(p["slippage_usd"] for p in parts),
            swap_usd=sum(p["swap_usd"] for p in parts),
            mean_net_R=sum(values)/len(values),
            win_rate=sum(v>0 for v in values)/len(values),
            net_without_top3_R=sum(sorted(values,reverse=True)[3:]),
        ))
    compact_atlas=[
        dict(c,models={m:trimmed_model(v) for m,v in c["models"].items()})
        for c in atlas["cells"]
    ]
    portfolio_diagnostics={}
    for model in MODELS:
        cs=cases[model]["PORTFOLIO"]
        rejects=sum((Counter(c["rejections"]) for c in cs),Counter())
        portfolio_diagnostics[model]=dict(
            rejections=dict(rejects),
            maximum_open_stop_risk_pct=max(c["maximum_open_stop_risk_pct"] for c in cs),
            unique_step2_completion_times=sorted({
                c["phase_passes"][1]["at"] for c in cs if len(c["phase_passes"])==2}),
            risk_buckets=dict(sum((Counter(c["risk_buckets"]) for c in cs),Counter())),
        )
    result=dict(
        schema="PROP-PORTFOLIO-V3-v1",date="2026-11-14",
        report_created_utc=datetime.now(timezone.utc).isoformat(),
        decision="ELIGIBLE_FOR_BOUNDED_NEXT_STAGE_REVIEW_NOT_CHALLENGE_READY",
        core=decision["core"],satellites=decision["satellites"],
        merged_pr80="91dd2d5",composition=decision,validation_release=release,
        decision_git_blob_sha256=release["committed_decision_sha256"],
        core_trial={m:[compact(r) for r in rows] for m,rows in regimes.items()},
        satellite_native_confirmation={
            k:({m:{**v,"sleeve":trimmed_model(v["sleeve"]),
                        "core":trimmed_model(v["core"]),
                        "portfolio_half_budget":trimmed_model(v["portfolio_half_budget"])}
                for m,v in selected["comparison"].items()} if k=="comparison" else v)
            for k,v in selected.items()
        },
        atlas_cells=compact_atlas,top10=atlas["top10"],
        top10_source_complete=atlas["top10_source_complete"],
        endpoint_recovery=recovery,satellite_annual_reference150=economics,
        lifecycle_comparisons=comparisons,
        lifecycle={m:{s:[compact(c) for c in rows] for s,rows in bysystem.items()}
                   for m,bysystem in cases.items()},
        continuous={m:{s:compact(rows[0]) for s,rows in bysystem.items()}
                    for m,bysystem in cases.items()},
        continuous_is_first_monthly_case_not_independent=True,
        portfolio_diagnostics=portfolio_diagnostics,funded_diagnostic=funded,
        parity={n:{k:v for k,v in p.items() if k!="records"} for n,p in parity.items()},
        regression=tests,prices2025_2026_read=False,broker_calls=0,model_calls=0,
        prop_qualified=False,actual_payout_received=False,
        review_scope="same implementer; alternate arithmetic and raw-source checks; no Astra",
        validation_is_already_exposed_historical_2024=True,
        new_trial_history=dict(catalog_cells=112,D1_weighting_trials=1,
            selected_sleeve_tick_confirmation=1,
            invalid_ask_attempt="natural-attempt-1-invalid-ask-quote",
            repeat_for_correctness_not_new_parameters=True),
        private_job=str(JOB),
        artifacts=[dict(name=p.name,sha256=digest(p)) for p in sorted(JOB.glob("*.json"))
                   if p.name not in ("status.json","delivery-receipt.json")],
        code=[dict(path=p.as_posix(),sha256=digest(p))
              for p in sorted(Path("tooling/ai-engines").glob("prop_portfolio_*.py"))],
        blockers=["NO_PAYOUT","ONLY_ONE_DISTINCT_TWO_STEP_COMPLETION_PATH",
                  "SYMMETRIC_STRESS_NO_TWO_STEP_COMPLETION","INTERNAL_7PCT_BUFFER_TIGHT",
                  "TARGET_SPEC_NEWS_MARGIN_AND_FORWARD_NOT_VERIFIED","NO_PRISTINE_OOS"],
    )
    write_json(OUT.with_suffix(".json"),result)
    lines=[
        "# V3 — đã có một vệ tinh bổ sung, chưa đủ điều kiện mua Challenge",
        "",
        "**Có tiến bộ về thành tích:** A gốc + EURUSD đã tạo ra 15/36 cửa sổ qua "
        "vòng 1 và 2/36 cửa sổ hoàn tất cả hai vòng dưới proxy swap bất đối xứng. "
        "**Payout vẫn bằng 0.** Hai cửa sổ hoàn tất cùng đi vào một đường funded "
        "giống nhau; không coi là hai thành công độc lập hoặc xác suất pass tương lai.",
        "",
        "Đã hoàn tất Phase 0–4 của task `ded836a8-3f42-4204-9742-9fc0ad3c369e`. "
        "PR #80 đã merge `91dd2d5`, nhánh cũ xóa. Giữ WIP VI Dubber; không gọi "
        "broker/model/paid provider. Giá 2025–2026 tiếp tục đóng. "
        "`prop_qualified=false`; kết quả là mô phỏng offline, chưa là tài khoản quỹ thật.",
        "",
        "## 1. Bốn cấu hình so sánh trực tiếp",
        "",
        "Cùng 36 ngày bắt đầu tháng từ 01/2022 đến 12/2024, kết thúc trước "
        "01/01/2025. Các cửa sổ chồng lấn, cửa sổ muộn có ít thời gian theo dõi "
        "hơn. PR #79/#80 dùng kết quả đã khóa; hai cột V3 dùng cùng bộ máy tick "
        "ghép và cùng chính sách vốn, chỉ khác việc có thêm vệ tinh.",
    ]
    lines+=tables(comparisons)
    lines+=[
        "",
        "*Trung vị chỉ tính cửa sổ đã đạt, không phải thời gian dự báo cho "
        "mọi tài khoản. Cửa sổ liên tục từ 01/01/2022 chính là quan sát tháng "
        "đầu tiên, không cộng thành thử nghiệm độc lập thứ 37.",
        "",
        "SYM/ASYM là hai giả định swap Gold đã giữ nguyên: −40/−40 và −45/−5 "
        "USD/lot/rollover. **Hai vòng chỉ hoàn tất ở ASYM; SYM vẫn 0/36.** "
        "Vì vậy chưa thể gọi kết quả vượt challenge là vững dưới mọi kịch bản phí.",
        "",
        "## 2. Danh mục hiện tại làm gì?",
        "",
        "| Thành phần | Luật dễ hiểu | Vai trò |",
        "|---|---|---|",
        "| Core: XAUUSD A gốc | H1 phá biên phiên Á theo hướng H4, SL tự nhiên, không TP cứng; giữ tối đa 48h lịch, chặn cuối tuần/ngày đóng sớm | Theo nhịp giá đi tiếp |",
        "| Vệ tinh: EURUSD Asia/London sweep DAY | Trong 08:00–11:00 UTC, H1 quét qua đáy Á rồi đóng tăng trở lại trên đáy Á thì BUY; quét đỉnh Á rồi đóng giảm trở lại dưới đỉnh Á thì SELL | Khai thác cú quét rồi quay lại qua biên |",
        "",
        "Vùng Á dùng 00:00–06:00 UTC đã hoàn tất. EUR vào ở quote đầu tiên sau "
        "nến H1 xác nhận, tối đa một cơ hội đăng ký/ngày. SL ngoài cực trị nến "
        "tín hiệu, thêm 0,1 ATR14 H1 biết trước nến; không nới SL để qua cổng phí. "
        "Đóng khi chạm SL hoặc 20:30 UTC cùng ngày/ngày lễ sớm hơn. "
        "Không có TP cứng, trailing hay partial close mới. "
        "Chỉ nhận khi ma sát/SL ≤15%. Chiều BUY/SELL đều giữ, không chọn lại theo 2024.",
        "",
        "Phí EUR giữ commission $5 + slippage $4/lot/vòng, cộng spread Bid/Ask "
        "quan sát; không trừ spread hai lần. Swap EUR bằng 0 vì đóng thật trước "
        "rollover trong mô hình, không phải đặt biểu phí qua đêm bằng 0. "
        "Gold giữ spread quan sát, commission 0,0007% notional/side, slippage "
        "0,20 USD/oz/side và hai kịch bản swap cũ. Các mức này vẫn là profile "
        "nghiên cứu, chưa xác minh đủ spec tài khoản đích.",
        "",
        "### Kết quả EUR đã xác nhận bằng tick, ở risk tham chiếu $150",
        "",
        "| Năm | BUY / SELL | Tổng lệnh | Net R | Mean Net R/lệnh | Win rate | Net R bỏ top 3 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in economics:
        lines.append(
            f"| {row['year']} | {row['buy']} / {row['sell']} | {row['trades']} "
            f"| {row['net_R']:+.3f} | {row['mean_net_R']:+.4f} "
            f"| {row['win_rate']:.1%} | {row['net_without_top3_R']:+.3f} |")
    lines+=[
        "",
        "1R ở bảng này = $150 để so cơ chế tín hiệu. Trong tài khoản thi, "
        "EUR dùng ngân sách nhỏ hơn Core; không cộng thẳng các R tham chiếu "
        "để dự báo % lợi nhuận tài khoản. 2024 có 78 cơ hội thô, 67 lệnh vào "
        "và 11 cơ hội rớt cổng phí; tần suất thấp hơn 2022–2023 đã được giữ nguyên.",
        "",
        "Lợi nhuận vẫn tập trung ở ít lệnh thắng lớn: bỏ ba lệnh tốt nhất "
        "thì mỗi năm đều âm. Win rate thấp không tự bác chiến lược, nhưng "
        "các con số này chưa chứng minh nguồn thu đều hoặc lợi thế bền vững. "
        "Đó là lý do EUR chỉ được dùng ở ngân sách vệ tinh, không thay Core.",
        "",
        "Bản M1 ban đầu cho EUR khoảng +15,964R gộp Dev. Tick gốc cho "
        "**+14,334R**, thấp hơn khoảng 1,63R nhưng vẫn qua cổng. "
        "Không dùng số M1 đẹp hơn khi đã có số tick.",
        "",
        "## 3. Vì sao giữ A gốc thay vì D1 scaling?",
        "",
        "Chỉ thử một quy tắc: D1 SMA50 với độ dốc 5 ngày đã đóng; tín hiệu Core "
        "ngược xu hướng D1 giảm còn 0,5x risk. Nến D1 chưa đóng không được dùng. "
        "Không thử thêm SMA/ADX hoặc ngắt hẳn SELL sau khi thấy kết quả.",
        "",
        "| Phí | Cấu hình | Net R 2022 | Net R 2023 | Gộp hai năm | Equity DD gộp (R) | Net/DD |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for model,rows in regimes.items():
        for offset in (0,3):
            a,b,total=rows[offset:offset+3]
            lines.append(
                f"| {model.split('_')[0]} | {total['variant']} "
                f"| {a['reference_net_R']:+.3f} | {b['reference_net_R']:+.3f} "
                f"| {total['reference_net_R']:+.3f} | {total['max_equity_R_DD']:.3f} "
                f"| {total['reference_net_R']/total['max_equity_R_DD']:.3f} |")
    lines+=[
        "",
        "D1 scaling giúp 2022 nhưng cắt mất nhiều lợi nhuận 2023; tỷ số gộp "
        "giảm trong cả hai mô hình phí. Vì vậy chọn **A_Original** trước mở 2024. "
        "Không dùng SELL lỗ năm 2024 làm lý do hồi tố tắt SELL. Trên baseline "
        "đã sửa holiday, SELL 2022 là +6,934R, không còn số +11,19R của bản cũ.",
        "",
        "## 4. Top 10 và lý do chỉ chọn một vệ tinh",
        "",
        "V2 có 84 cấu hình đủ endpoint nhưng đã rớt Stage-0, chưa tới cổng "
        "+6R/năm. V3 là thí nghiệm mới được owner cho phép kiểm Natural SL và "
        "đóng góp danh mục trên cùng 112 công thức. "
        "Không sửa lại verdict cũ, không thêm tín hiệu/horizon sau kết quả.",
        "",
        "Bảng xếp hạng dùng mô hình có tổng Net R thấp hơn giữa SYM/ASYM. "
        "Các dòng H1/nguồn thiếu chỉ là screen có điều kiện, không phải ứng viên "
        "đã đủ điều kiện. Dòng EUR được cập nhật bằng tick; các dòng khác giữ "
        "bản screen đã đăng ký. DD screen là biên bảo thủ của M1/H1, khác DD "
        "tick chính xác ở bảng vòng đời. Đầy đủ hai mô hình và 112 cấu hình trong JSON.",
        "",
        "| # | Asset | Cơ chế / vùng / phiên | Giữ | Lệnh 2022/23 | Đạt phí 2022/23 | Net R 2022 | Net R 2023 | Tổng | Max R-DD | Corr với A | Nguồn / cổng chặn |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    byid={c["cell"]["id"]:c for c in atlas["cells"]}
    for rank,name in enumerate(atlas["top10"],1):
        cell=byid[name]
        model=min(MODELS,key=lambda m:cell["models"][m]["total_net_R"])
        out=cell["models"][model];correlation=out["correlation"]["pooled"]
        status="M1; xem cổng trong JSON" if cell["source_path_complete"] else "Nguồn/đường giá có điều kiện"
        if name==decision["satellites"][0]:
            out=selected["comparison"][model]["sleeve"]
            correlation=selected["comparison"][model]["correlation"]
            status="Tick đã xác nhận; được chọn"
        elif cell["cell"]["asset"] in ("GBPUSD","AUDUSD"):
            status="Chỉ H1; chưa đủ M1/tick"
        elif cell["cell"]["asset"]=="XAUUSD":
            status="Giữ chỉ 39–45% raw; thiếu ask/path"
        elif cell["cell"]["asset"]=="US500":
            status="Không đạt scale/retention; carry đích chưa đủ"
        a,b=cell["funnel"]["2022"],cell["funnel"]["2023"]
        spec=cell["cell"]
        mechanism="Quét" if spec["mechanism"]=="SWEEP" else "Phá đi tiếp"
        zone="Á" if spec["region"]=="ASIA" else "ngày trước"
        session="London" if spec["window"]=="LONDON" else "New York"
        holding="Ngày" if spec["horizon"]=="DAY" else "+"+spec["horizon"].lower()
        lines.append(
            f"| {rank} | {spec['asset']} | {mechanism} {zone} / {session} "
            f"| {holding} | {a['filled']}/{b['filled']} "
            f"| {a['friction_pass_rate']:.1%}/{b['friction_pass_rate']:.1%} "
            f"| {out['net_R']['2022']:+.3f} | {out['net_R']['2023']:+.3f} "
            f"| {out['total_net_R']:+.3f} | {out['max_R_DD']:.3f} "
            f"| {'N/A' if correlation is None else f'{correlation:.3f}'} | {status} |")
    lines+=[
        "",
        "SWEEP = quét qua biên rồi quay lại; CONT = phá biên đi tiếp; ASIA/PREVDAY "
        "= vùng phiên Á/ngày trước; DAY = đóng cùng ngày. "
        "Các horizon của cùng cohort không độc lập.",
        "",
        "EUR giữ 94,9% / 96,1% cơ hội qua cổng phí trong Dev. Bản tick có "
        "+3,771R / +10,562R, tổng ≥8R, hai năm đều dương, tương quan ngày khoảng "
        "0,10. Ghép ở ngân sách $75 so với Core $150 cải thiện Net/DD từ "
        "0,805 lên 0,982 ở SYM và 1,070 lên 1,232 ở ASYM. "
        "Không có vệ tinh thứ hai đạt đủ nguồn, scale, kinh tế và đóng góp biên.",
        "",
        "GBPUSD Asia/London sweep DAY có screen H1 dương đáng chú ý nhưng "
        "thiếu đường M1/tick; chưa được gọi là edge hoặc đưa vào portfolio. "
        "Các Gold sweep dương đã loại hơn một nửa tín hiệu bởi phí, nên không "
        "được cứu bằng nới SL. US500 còn vướng scale/retention và carry/cổ tức "
        "đích. USDJPY vẫn thiếu nguồn liên tục, không bị gán nhãn thua kinh tế.",
        "",
        f"Đã khôi phục {recovery['recovered']}/{recovery['original_missing_observations']} "
        "endpoint US500 cũ bằng nguồn đã có và clamp trước giờ nghỉ NY; "
        f"{len(recovery['unresolved'])} mốc còn thiếu được giữ unknown. "
        "Không lấy quote đầu tiên sau giờ nghỉ để làm giá đóng trước giờ nghỉ. "
        "Các khoảng thiếu AUDUSD không được lấp. Bản Natural-SL có 42 cấu hình "
        "đủ đường cho M1 scenario; phần còn lại có điều kiện, thiếu nguồn hoặc lot grid. "
        "Đủ endpoint và đủ đường giữ lệnh là hai việc khác nhau.",
        "",
        "## 5. Đi vốn, trần rủi ro và trade-off",
        "",
        "| Phase | Core | Vệ tinh EUR |",
        "|---|---:|---:|",
        "| Vòng 1 | 0,40% / $200 | 0,20% / $100 |",
        "| Vòng 2 | 0,35% / $175 | 0,20% / $100 |",
        "| Funded | 0,25% / $125 | 0,15% / $75 |",
        "",
        "Tổng rủi ro ban đầu đến SL của mọi vị thế ≤1% ($500). Không net rủi ro "
        "BUY/SELL hoặc khác tài sản để lách cap. Mức lỗ equity hiện tại so với "
        "vốn đầu đạt 4% hạ trần risk lệnh mới còn $150; đạt 6% còn $90; "
        "không nâng risk vệ tinh vì cap. "
        "Lỗ đã thực hiện trong ngày chạm −2% thì ngừng mở mới đến reset Prague. "
        "Vị thế cũ giữ size. Cổng reserve còn yêu cầu SL + phí + funding dự kiến "
        "không chạm mức equity $46.500. Cổng funding hiện chỉ dùng deadline "
        "khóa trước, không dùng thời điểm SL/thoát lệnh biết sau.",
        "",
        "| Phí | Open risk lớn nhất | Chặn bởi cap 1% | Chặn bởi reserve 7% | Chặn lỗ ngày 2% |",
        "|---|---:|---:|---:|---:|",
    ]
    for model,d in portfolio_diagnostics.items():
        r=d["rejections"]
        lines.append(
            f"| {model.split('_')[0]} | {d['maximum_open_stop_risk_pct']:.6f}% "
            f"| {r.get('OPEN_STOP_RISK_1PCT_CAP',0)} "
            f"| {r.get('INTERNAL_STATIC_7PCT_RESERVE',0)} "
            f"| {r.get('DAILY_REALIZED_2PCT_HALT',0)} |")
    lines+=[
        "",
        "Counts là tổng lượt trên các tài khoản chồng lấn, không là cơ hội thị "
        "trường độc lập. Reserve thực sự chặn nhiều lệnh trong V3; không gọi "
        "các lệnh đó là bị bỏ qua ngẫu nhiên. Cổng 7% có thể làm tài khoản "
        "giao dịch thưa hoặc chờ hồi phục. "
        "**Worst static khoảng 6,998% rất sát ngưỡng nội bộ 7%**, dù vẫn còn "
        "khoảng 3 điểm phần trăm tới trần overall 10% của profile. Gap, swap "
        "và khớp lệnh ngoài mô hình có thể làm mất buffer này. Không tăng risk "
        "hoặc đổi cổng sau khi nhìn kết quả.",
        "",
        "## 6. Vì sao đã qua hai vòng nhưng chưa có payout?",
        "",
        "Hai mốc bắt đầu 01/01/2022 và 01/02/2022 dưới ASYM cùng qua vòng 1 "
        "ngày 29/09/2023, qua vòng 2 ngày 10/11/2023. "
        "Từ phase funded trở đi chúng có cùng state/đường lệnh; chỉ có "
        "**một đường hoàn tất hai vòng riêng biệt**, không phải hai lần "
        "thành công độc lập.",
        "",
        "| Mốc bắt đầu | Vào funded* | Net funded cuối 2023 | Net funded năm 2024 | Balance cuối | Payout proxy |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in funded["rows"]:
        lines.append(
            f"| {date_text(row['start'])} | {date_text(row['first_funded_trade'])} "
            f"| ${row['funded_net_by_entry_year']['2023']:,.2f} "
            f"| ${row['funded_net_by_entry_year']['2024']:,.2f} "
            f"| ${row['final_balance_usd']:,.2f} | $0 |")
    lines+=[
        "",
        "*Ngày giao dịch funded đầu tiên; phase reset xảy ra ngày 10/11/2023. "
        "Lãi vòng thi được bỏ khỏi sổ khi sang phase mới, không phải tiền trả "
        "cho trader. Funded khởi đầu lại $50.000, lỗ $1.096,26 cuối 2023 rồi "
        "thu lại $847,82 trong 2024, cuối mẫu còn $49.751,56.",
        "",
        "Proxy reward giữ nguyên 30 ngày, đã đóng hết vị thế và lãi đóng ≥$20, "
        "trừ 100% lợi nhuận khỏi account rồi chia 80% trader/20% firm. "
        "Đây không phải xác minh lịch payout hiện hành của hãng. "
        "Chẩn đoán đọc sổ theo mốc 14 ngày cũng không tìm thấy thời điểm flat "
        "có lợi nhuận dương; không chạy lại chính sách rút tiền 14 ngày hoặc "
        "gán nó thành kết quả payout khác. Chưa tính phí mua/retry Challenge, "
        "chi phí vận hành và thuế. Chưa có tiền thật được nhận.",
        "",
        "## 7. Kiểm chứng và giới hạn còn lại",
        "",
        f"- {tests['tests']} tests hồi quy đạt, trong đó 21 fixtures V3 về D1 "
        "causal, funding theo deadline, Bid/Ask thiếu, SL gap, lot grid, "
        "cash book hai tài sản, daily halt, cap rủi ro và reward debit.",
        f"- {parity['regime-parity.json']['causal_decisions']} quyết định D1 "
        "được dựng lại từ prefix ngày đã đóng; 12 sổ D1 khớp oracle đường giá/cash.",
        f"- 112 Natural-SL screens, {parity['stage1-parity.json']['cost_bridges']} "
        "phép đối chiếu chi phí bằng phân số; giữ cả các screen âm/nguồn thiếu.",
        f"- {parity['source-parity.json']['ticks']:,} tick EURUSD / "
        f"{parity['source-parity.json']['hours']} giờ khớp từng dòng CSV gốc, "
        "bao gồm thứ tự bản ghi cùng millisecond.",
        f"- {parity['lifecycle-parity.json']['accounts']} tài khoản khớp cách "
        "hạch toán khác: oracle trả funding vào cash và tổng hợp exposure theo "
        "tài sản, trong khi producer giữ funding trong floating.",
        f"- Oracle kiểm {parity['lifecycle-parity.json']['accepted_decisions']:,} "
        "quyết định nhận và "
        f"{parity['lifecycle-parity.json']['rejected_decisions']:,} quyết định từ chối, "
        "không chỉ kiểm các lệnh đã vào; đối chiếu phase, loss floors và chi phí.",
        f"- {parity['lifecycle-parity.json']['source_quote_updates_independently_checked']:,} "
        "cập nhật quote ghép được kiểm lại bằng phép tìm timestamp của từng "
        "nguồn; không lấy giá tương lai của tài sản kia.",
        "",
        "**Cùng một implementer, dùng cách tính khác; không có reviewer "
        "người/model độc lập và không gửi Astra.** "
        "Không đổi data/rules để cứu một kết quả kiểm định không khớp.",
        "",
        "### Freeze và Historical Validation",
        "",
        f"Composition được commit tại `{release['decision_commit']}` trước "
        f"release `{release['utc']}`. Mọi tham số Core/Satellite/risk và "
        "code/rule hashes được kiểm lại trước Phase 3. "
        "Git LF và file Windows CRLF được bind bằng cả hash byte riêng và "
        "nội dung JSON; khác nội dung thì gate từ chối.",
        "",
        "2024 đã có exposure từ các đợt trước; ý tưởng D1 cũng được gợi bởi "
        "phân rã cũ năm 2024. V3 chỉ dùng 2022–2023 để chọn, commit trước lần "
        "replay mới, nhưng **2024 không trở thành clean OOS**. "
        "112 cấu hình, các horizon gần nhau và lịch sử thử trước đây gây "
        "selection bias. Tương quan thấp trong Dev không bảo đảm thấp trong tương lai.",
        "",
        "Các gate chưa đủ cho Challenge/funded thật: spec/commission/swap và "
        "margin/leverage đích, lịch tin hạn chế lịch sử, phiên/ngày đóng sớm "
        "đúng feed tài khoản, độ mới quote ở reset khi thị trường nghỉ, "
        "forward/shadow và bàn giao vận hành. Cùng timestamp UTC không chứng minh "
        "hai feed có cùng latency như broker. Account mode và các nguồn USD "
        "là assumptions đã khai báo. Không có quyền gửi lệnh từ báo cáo này.",
        "",
        "### Hậu kiểm kỹ thuật",
        "",
        "| Vấn đề | Đã xử lý và bằng chứng |",
        "|---|---|",
        "| Funding reserve nhìn exit tương lai | Dùng deadline biết trước; tests đổi exit không làm đổi reserve; oracle kiểm lại cả nhận/từ chối lệnh |",
        "| Gold M1 chỉ Bid nhưng bị đọc ô Ask=0 | Dừng/quarantine lượt đầu, cấm quote không hợp lệ, giá đóng Gold lấy paired ticks; không dùng kết quả invalid |",
        "| D1 có ngày thiếu dữ liệu | Chỉ dùng ngày đủ điều kiện đã đóng, prefix oracle kiểm causal; không biến ngày 12h thành D1 đầy đủ |",
        "| Freeze private chưa đủ bằng chứng Git | V3 commit quyết định trước mở 2024; lần preflight LF/CRLF bị chặn trước release, sửa semantic binding rồi commit lại, không đổi lựa chọn/risk |",
        "| M1 stop-fill khác tick | Xác nhận đúng một vệ tinh trên tick trước freeze; giữ số tick thấp hơn số screen |",
        "",
        "Các sửa lỗi có fixture cụ thể; không tạo thêm skill/process hoặc "
        "một bộ state tài khoản song song. Account hiện có tiếp tục sở hữu "
        "phase/reset/reward, adapter bổ sung units và quote của tài sản. "
        "Không đo quota/chi phí LLM hay tuyên bố speedup không có benchmark.",
        "",
        f"Private evidence: `{JOB}`. JSON đi kèm giữ 112 cấu hình, các quyết "
        "định, aggregate, 144 ledger rút gọn, source/code hashes và locators. "
        "Raw ticks/caches, lượt lỗi, full ledgers và source reviews giữ riêng.",
        "",
        "**Quyết định tiếp:** giữ A + EUR như một ứng viên có đóng góp danh mục "
        "trong profile đã kiểm, đủ cho bước review hữu hạn tiếp theo. "
        "Chưa mua Challenge hoặc dựa vào nó làm thu nhập chính: chưa payout, "
        "thành công hai vòng chưa vững dưới stress đối xứng, thời gian pass dài "
        "và chưa có clean OOS/forward. Ưu tiên xác minh profile đích/khả năng "
        "vận hành và kiểm định tiếp đã đăng ký, không thêm bot yếu hoặc tăng "
        "risk để ép payout. GBP giữ ở mức source-readiness, chưa được promote.",
        "",
        "## Phụ lục — toàn bộ 112 cấu hình",
        "",
        "| Cell | M1/H1 net R 2022/23 (ASYM) | Filled 2022/23 | Đủ đường scenario | Lý do chưa chọn |",
        "|---|---:|---:|---|---|",
    ]
    for cell in atlas["cells"]:
        name=cell["cell"]["id"];m=cell["models"]["ASYM_FLAT"]
        reasons=cell["satellite_reasons"]
        status="Đủ trong scenario" if cell["source_path_complete"] else "Có điều kiện/thiếu nguồn"
        lines.append(
            f"| {name} | {m['net_R']['2022']:+.3f}/{m['net_R']['2023']:+.3f} "
            f"| {cell['funnel']['2022']['filled']}/{cell['funnel']['2023']['filled']} "
            f"| {status} | {', '.join(reasons) or 'NATIVE_CONFIRMED_SELECTED'} |")
    lines+=["","Các số screen có điều kiện không thay thế số tick xác nhận của EUR ở phần chính.",""]
    OUT.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")
    print(OUT.with_suffix(".md"),flush=True)


if __name__=="__main__":
    build()
