"""Summarize existing V7 ledgers; never launch another economic experiment."""
from prop_v6_report import aggregate, brief, table, n
from prop_v7_common import *

OUT = Path("planning/research/PROP-GOLD-V7-RESULTS-20261115")


def year(at):
    return datetime.fromtimestamp(at / 1000, timezone.utc).year


def funded_summary(cases):
    first = min(cases, key=lambda a: a["start_msc"])
    yearly, quarterly = {}, {}
    for y in range(2022, 2027):
        payouts = [p for p in first["payouts"] if year(p["at"]) == y]
        yearly[str(y)] = dict(events=len(payouts),
                             trader_usd=sum(p["trader_usd"] for p in payouts))
        for q in range(1, 5):
            if y == 2026 and q == 4:
                label = "2026Q4_to_Oct13"
            else:
                label = f"{y}Q{q}"
            ps = [p for p in payouts if
                  (datetime.fromtimestamp(p["at"] / 1000, timezone.utc).month - 1) // 3 + 1 == q]
            quarterly[label] = dict(events=len(ps),
                                   trader_usd=sum(p["trader_usd"] for p in ps))
    return dict(starts=len(cases), modeled_breaches=sum(bool(a["first_breach"]) for a in cases),
                max_daily_pct=max(a["worst_daily_loss_pct"] for a in cases),
                max_static_pct=max(a["static_loss_pct"] for a in cases),
                Jan2022=brief(first) | dict(yearly=yearly, quarterly=quarterly),
                all_starts=[brief(a) for a in cases])


def build():
    verify()
    tests = read(JOB / "tests.json")
    if tests["status"] != "PASS":
        raise ValueError("V7_tests_not_passed")
    archived = read("planning/research/PROP-V4-HARVEST-V6-RESULTS-20261115.json")
    scenarios, bindings = {}, []
    for order in ORDERS:
        folder = JOB / order
        cases = read(folder / "accounts.json")
        funded = read(folder / "funded-accounts.json")
        refs = read(folder / "annual-reference.json")
        parity = read(folder / "accounting-parity.json")
        pricing = read(folder / "calendar-repricing.json")
        if parity["status"] != "PASS" or parity["cases"] != 402:
            raise ValueError("V7_accounting_incomplete")
        if (len(cases), len(funded), len(refs)) != (342, 30, 30):
            raise ValueError("V7_case_count")
        if any(a["open_positions"] or a.get("path_censor") for a in cases + funded + refs):
            raise ValueError("V7_unfinished_path")
        if any(a["end_msc"] != END for a in cases + funded):
            raise ValueError("V7_early_account_end")
        if pricing["unresolved"] or pricing["priced_exits"] != pricing["total_trades"]:
            raise ValueError("V7_pricing_incomplete")
        groups = {}
        for policy in POLICIES:
            groups[policy] = {}
            for model in MODELS:
                selected = [a for a in cases if a["policy_id"] == policy and a["cell"] == model]
                old = [a for a in selected if a["start_msc"] < stamp("2025-01-01")]
                fresh = [a for a in selected if a["start_msc"] >= stamp("2025-01-01")]
                if (len(old), len(fresh)) != (36, 21):
                    raise ValueError("V7_rolling_cohorts")
                groups[policy][model] = dict(
                    old=aggregate(old), fresh=aggregate(fresh),
                    funded=funded_summary([a for a in funded if a["policy_id"] == policy and a["cell"] == model]),
                    rolling_accounts=[brief(a) for a in selected])
        annual = []
        for a in refs:
            annual.append(brief(a) | dict(year=year(a["start_msc"]), side=a["reference_side"]))
        forensics = read(folder / "gold-forensics.json")
        for row in forensics["annual"]:
            for model in MODELS:
                a = next(a for a in annual if a["year"] == row["year"] and a["cell"] == model and a["side"] == "BOTH")
                if abs(a["net_R"] - row["models"][model]["net_R"]) > 1e-9:
                    raise ValueError("V7_annual_forensic_bridge")
        scenarios[order] = dict(
            policies=groups, annual_reference=annual, gold_structure=forensics["annual"],
            calendar=pricing, parity=parity)
        for name in ("accounts.json", "funded-accounts.json", "annual-reference.json",
                     "accounting-parity.json", "calendar-repricing.json", "gold-forensics.json",
                     "system-trades.json"):
            path = folder / name
            bindings.append(dict(path=path.as_posix(), sha256=digest(path)))
    for path in (JOB / "tests.json", JOB / "top10-Gold-no-EUR-audit.json",
                 JOB / ORDERS[0] / "2025-budget-normalization.json"):
        bindings.append(dict(path=path.as_posix(), sha256=digest(path)))
    deltas = []
    for policy in POLICIES:
        for model in MODELS:
            for group in ("old", "fresh"):
                a, b = [scenarios[o]["policies"][policy][model][group] for o in ORDERS]
                deltas += [dict(policy=policy, model=model, group=group, metric=k,
                                primary=a[k], secondary=b[k])
                           for k in a if a[k] != b[k]]
    result = dict(
        schema="PROP-GOLD-V7-RESULTS-v1", date="2026-11-15", scope_label=LABEL,
        verdict="NOT_QUALIFIED", main_income_proven=False, clean_OOS=False,
        freeze_commit=read(JOB / "run-release.json")["commit"],
        merged_PR85_commit="70b9ba169b4a9a0d6a7fdab273fc8a728b70e4b2",
        price_end_exclusive=END, data_censored_cases=0,
        eurusd_active=False, eurusd_counterfactual_only=True,
        scenarios=scenarios,
        OHLC_sensitivity_summary_differences=deltas,
        archived_V6={o: {k: archived["scenarios"][o][k] for k in ("old_summary", "fresh_summary")}
                     for o in ORDERS},
        archived_V6_funded=archived["standalone_funded"],
        top10=read(JOB / "top10-Gold-no-EUR-audit.json"),
        budget_normalization=read(JOB / ORDERS[0] / "2025-budget-normalization.json"),
        tests={k: v for k, v in tests.items() if k != "matrix"} |
              dict(matrix=[{k: v for k, v in x.items() if k != "ids"} for x in tests["matrix"]]),
        calendar_source=read(JOB / "calendar-source-receipt.json"),
        evidence_bindings=bindings, private_job=JOB.as_posix(),
        reporting_and_review_code=[
            dict(path=p.as_posix(), sha256=digest(p))
            for p in sorted(Path("tooling/ai-engines").glob("prop_v7_*.py"))],
        broker_executions=0, actual_rewards_received_usd=0,
        independent_person_or_model_review=False, same_implementer_alternate_accounting=True,
        source_limitations=[
            "Gold 2025-26 Bid M1, fixed Ask spread 0.338 USD/oz, two artificial OHLC orders",
            "11 target holiday dates verified; remaining dates use declared conservative guards",
            "historical news restrictions and broker-specific swap/quote history not fully certified",
            "overlapping rolling windows are not independent trials or pass probabilities",
            "harvester rewards are modeled eligibility with zero administrative delay, not received cash"],
        decision=dict(
            retain_as_research_reference="XAUUSD A BOTH original 48h/no hard TP",
            promote_Gold_scaled=False, add_top10_sleeve=False, select_24h_exit=False,
            next_step="Resolve target quote/cost/news evidence and preregister a bounded test on genuinely new data; no challenge purchase or new tuning in V7"))
    write_json(OUT.with_suffix(".json"), result)
    render(result)
    event("V7_report_complete", cases=804, tests=tests["unique_tests"], verdict=result["verdict"])


def render(r):
    p = r["scenarios"][ORDERS[0]]
    sections = [
        "# V7 — Gold A sau sửa lịch và giải phẫu 2022–2026",
        "Ngày 15/11/2026. **Kết luận: chưa đủ điều kiện Challenge hoặc làm nguồn thu nhập chính.** "
        "Đã sửa được việc dừng đo ngày 03/07/2026, nhưng bỏ EURUSD và tăng risk chưa giải quyết được tốc độ hoàn tất hai vòng. "
        "Gold năm 2025 cũng không dương ổn định giữa hai mức sizing đã dùng.",
        "**Phạm vi:** Post-Holdout Diagnostic / Full-Sample 2022–2026 Audit; giá chỉ đến hết "
        "13/10/2026. Dữ liệu 2025–2026 đã được xem ở V6; V7 không phải clean OOS. "
        "PR #85 đã merge tại `70b9ba1`; V7 dùng branch `codex/prop-gold-v7-audit`, không tự merge PR mới.",
        "## 1. Đã sửa gì và dữ liệu đi qua đâu?",
        "Giữ nguyên tín hiệu Asian Breakout theo H4, cả BUY/SELL, entry và Natural SL. "
        "Chỉ sửa deadline nghỉ lễ từ 2025, rồi chạy lại đường giá → admission/risk → cash/equity "
        "→ hai vòng Challenge → Funded/harvester. EURUSD bị chặn ở admission của hai policy Gold; "
        "vẫn giữ trong cột đối chứng và lịch sử.",
        "FTMO Trading Update 25/06/2026 ghi Metals đóng ngày 03/07/2026 lúc 20:00 MT5 GMT+3, "
        "tức 17:00 UTC. V6 tìm quote từ đúng giờ đóng. V7 đã khóa trước phép đo: flat trước 2 phút so với "
        "`min(guard nghỉ lễ cũ, giờ đóng đích đã xác minh)`, nên ngày đó thoát lúc **16:58 UTC**. "
        "Friday thường vẫn 20:30 UTC. Không dùng quote cũ tùy ý để lấp khoảng thiếu.",
    ]
    c = p["calendar"]
    changes = c["changes"]
    exits_changed = sum(a["before"]["exit_msc"] != a["after"]["exit_msc"] for a in changes)
    sections += [
        f"**Độ phủ:** {c['priced_exits']}/{c['total_trades']} đường lệnh được định giá, "
        f"gồm {c['holdout_trades']} đường lệnh 2025–2026. Có {len(changes)} hồ sơ đổi deadline, "
        f"trong đó {exits_changed} hồ sơ đổi thời điểm thoát; entry/SL/side bảo toàn. "
        "476/476 tín hiệu Gold có điểm thoát. Mỗi policy/phí có đủ 57 cửa sổ đến cutoff, 0 data censor, 0 vị thế mở.",
        "**Giới hạn lịch:** đã liệt kê các ngày nghỉ 2025–2026; 11 ngày có giờ đóng đích kiểm được từ FTMO. "
        "Các ngày còn lại vẫn dùng guard bảo thủ có nhãn chưa xác minh, không được gọi toàn bộ lịch đã certified. "
        "Đủ endpoint không chứng minh đường tick của broker hoặc mọi luật hãng đã được kiểm.",
        "## 2. Bốn cột so sánh đúng cùng câu hỏi",
        "SYM = swap BUY/SELL −40/−40 USD/lot/rollover; ASYM = proxy −45/−5. "
        "Các cột mới đều giữ SL tự nhiên, không TP cứng, tối đa 48 giờ lịch, Friday/holiday flat. "
        "Cột V6 cũ bị dừng vì thiếu đường giá nên thời gian phơi nhiễm ngắn hơn.",
        "Risk P1/P2/Funded: co-core sửa lịch và Gold V4 = **200/175/125 USD**; Gold tăng risk = "
        "**250/200/150 USD** trên vốn đầu 50.000 USD. Cả hai giữ cap open-stop 800 USD, "
        "reserve nội bộ 46.000 USD, giảm risk khi equity ≤48k/47k, daily realized halt 1.000 USD. "
        "Reserve 8% là chốt nội bộ, khác giới hạn overall 10% của profile.",
        "Profile mô phỏng: FTMO Standard 2-Step 50k, mục tiêu P1 +10% / P2 +5%, "
        "daily/static limits 5%/10% theo reset Prague. Gold commission 0,0007% notional/side, "
        "stress slippage 0,20 USD/oz/side; không hard TP. Swap tính theo lịch rollover đã pin, "
        "có ngày hệ số ba. Đây là cấu hình nghiên cứu, chưa phải bản xác nhận lịch sử đầy đủ từ tài khoản đích.",
    ]
    headers = ["Chỉ số", "V6 co-core dừng sớm", "Co-core sửa lịch", "Gold V4", "Gold tăng risk"]
    for model in MODELS:
        old = r["archived_V6"][ORDERS[0]]["old_summary"][model]
        cols = [old] + [p["policies"][policy][model]["old"] for policy in POLICIES]
        rows = []
        for label, key in (("Qua P1 /36", "passed1"), ("Qua cả 2 /36", "passed2"),
                           ("Cửa sổ có payout /36", "payout_windows"), ("Sự kiện payout", "payout_events"),
                           ("Data-censored /36", "data_censored")):
            rows.append([label] + [x[key] for x in cols])
        for label, key in (("Tổng trader USD, cửa sổ chồng lấn", "trader_usd_window_sum"),
                           ("Daily loss cao nhất %", "max_daily_pct"),
                           ("Static loss cao nhất %", "max_static_pct"),
                           ("Peak-to-valley cao nhất % vốn đầu", "max_peak_pct"),
                           ("Tháng tới cả 2, median trong số thành công", "median_months_to_both_among_successes")):
            rows.append([label] + [n(x[key], 3 if "pct" in key else 2) for x in cols])
        sections += [f"### 36 mốc khởi đầu 2022–2024 — {model}", table(headers, rows)]
    rows = []
    for model in MODELS:
        old = r["archived_V6"][ORDERS[0]]["fresh_summary"][model]
        cols = [old] + [p["policies"][policy][model]["fresh"] for policy in POLICIES]
        rows += [[f"{model}: P1 / cả 2 /21"] + [f"{x['passed1']} / {x['passed2']}" for x in cols],
                 [f"{model}: data-censored /21"] + [x["data_censored"] for x in cols]]
    sections += ["### 21 mốc mới 01/2025–09/2026", table(headers, rows),
                 "Các mốc mới **0/21 qua P1** ở cả ba policy và hai phí. Những mốc gần cutoff có ít thời gian; "
                 "đây là kết quả lịch sử có giới hạn thời gian, không phải xác suất thất bại tương lai. "
                 "Các cửa sổ chồng lấn dùng chung tín hiệu nên không cộng payout thành thu nhập một tài khoản. "
                 "`RIGHT_CENSORED` còn xuất hiện khi vòng đời chưa đạt mục tiêu trước cutoff; khác `path_censor` do thiếu giá, nay bằng 0.",
                 "**Bỏ EURUSD giảm rủi ro nhưng làm số mốc hoàn tất hai vòng giảm trong mẫu này.** "
                 "Không thể lấy −18,11R EUR rồi cộng ngược vào danh mục: admission, lot, throttle, "
                 "thời điểm đổi phase và rút lợi nhuận đều thay đổi theo đường vốn.",
                 "### Standalone Funded: khởi đầu 01/2022, nối đến 13/10/2026",
                 "Sổ này giả định đã có Funded ngay từ đầu, không chứng minh vượt Challenge. "
                 "Tiền dưới đây là phần thưởng mô phỏng sau chia 80/20, chưa trừ phí mua/retry/vận hành, "
                 "không phải khoản đã nhận. V6 cũ Jan2022 chỉ đo 2022–2024 nên khác thời lượng."]
    rows = []
    for model in MODELS:
        old = r["archived_V6_funded"][model]["Jan2022"]
        old_account = r["archived_V6_funded"][model]["accounts"][0]
        rows.append(["V6 co-core chỉ 2022–2024", model, old["payouts"], n(old["trader_usd"]),
                     n(old["ending_balance"]), n(old_account["worst_daily_loss_pct"], 3),
                     n(old_account["static_loss_pct"], 3)])
        for policy in POLICIES:
            a = p["policies"][policy][model]["funded"]["Jan2022"]
            rows.append([policy, model, len(a["payouts"]), n(a["trader_payout_usd"]),
                         n(a["balance_usd"]), n(a["worst_daily_loss_pct"], 3), n(a["static_loss_pct"], 3)])
    sections += [table(["Policy", "Phí", "Payout", "Trader USD", "Balance cuối", "Daily %", "Static %"], rows)]
    rows = []
    for model in MODELS:
        for policy in POLICIES:
            a = p["policies"][policy][model]["funded"]["Jan2022"]
            rows.append([policy, model] + [f"{a['yearly'][str(y)]['events']} / {n(a['yearly'][str(y)]['trader_usd'])}"
                                          for y in range(2022, 2027)])
    sections += [table(["Policy", "Phí", "2022 lần/USD", "2023", "2024", "2025", "2026 tới cutoff"], rows),
                 "JSON kèm đủ 5 mốc Funded 01/2022…01/2026 và payout theo quý của sổ 01/2022. "
                 "Không mô hình nào ghi nhận breach trên đường đã dựng; chưa thành bảo đảm an toàn broker. "
                 "Gold tăng risk cho nhiều tiền mô phỏng hơn ở một số sổ Funded, nhưng **không được chọn để promote** "
                 "vì challenge time-fit vẫn yếu và static loss ở nhóm rolling cũ đã gần reserve nội bộ 8%.",
                 "## 3. Gold A từng năm ở cùng budget 150 USD/lệnh",
                 "1R ở bảng này = 150 USD, tức 0,30% vốn đầu 50k. Đây là sổ tham chiếu annual, không áp "
                 "throttle/harvester của lifecycle. BUY và SELL là phân rã, không chọn phía tốt sau kết quả. "
                 "2026 là YTD đến 13/10, không phải cả năm."]
    rows = []
    for a in p["gold_structure"]:
        rows.append([a["year"], f"{a['BUY']}/{a['SELL']}", a["signals"], a["signals"] - a["minlot_rejected"],
                     f"{a['priced_exits']}/{a['signals']}",
                     n(a["models"]["SYM_FLAT"]["net_R"], 4), n(a["models"]["ASYM_FLAT"]["net_R"], 4)])
    sections += [table(["Năm", "BUY/SELL thô", "Tín hiệu", "Thực thi", "Có giá thoát", "Net R SYM", "Net R ASYM"], rows),
                 "Năm 2026 có **72 tín hiệu có giá, 71 lệnh thực thi**: 1 tín hiệu vượt budget ở minimum lot. "
                 "Không tự tăng risk để ép tín hiệu đó thành lệnh."]
    for model in MODELS:
        rows = []
        for a in p["gold_structure"]:
            m = a["models"][model]
            ref = next(x for x in p["annual_reference"] if x["year"] == a["year"] and x["cell"] == model and x["side"] == "BOTH")
            rows.append([a["year"], n(m["sides"]["BUY"]["net_R"], 3), n(m["sides"]["SELL"]["net_R"], 3),
                         n(m["mean_net_R"], 4), n(ref["max_equity_R_DD"], 3), n(ref["peak_dd_pct"], 3),
                         n(ref["static_loss_pct"], 3), n(ref["worst_daily_loss_pct"], 3)])
        sections += [f"### Phân rã {model}",
                     table(["Năm", "BUY R", "SELL R", "Mean R/lệnh", "Peak-valley R", "Peak % vốn đầu", "Static %", "Daily %"], rows)]
    sections += [
        "### Hiệu chỉnh kết luận “Gold dương bốn năm liên tiếp”",
        "V6 đo Gold 2025 tại risk 125 USD; bảng annual V7 dùng 150 USD để nhất quán với 2022–2024. "
        "Cùng tập 96 tín hiệu, số ounce phải làm tròn xuống theo minimum/step 0,01 lot = 1 oz. "
        "Tăng budget có thể tăng lượng ở lệnh thua mà chưa tăng ở lệnh thắng; tổng R không bất biến theo sizing.",
    ]
    rows = []
    for m in r["budget_normalization"]["models"]:
        old = m["cases"]["V6_same_entries_old_calendar"]
        fixed = m["cases"]["V7_same_entries_fixed_calendar"]
        rows.append([m["model"], n(old["125"]["net_R"], 4), n(old["150"]["net_R"], 4),
                     n(fixed["125"]["net_R"], 4), n(fixed["150"]["net_R"], 4)])
    sections += [table(["Phí", "Lịch cũ $125", "Lịch cũ $150", "Lịch sửa $125", "Lịch sửa $150"], rows),
                 "**Vì vậy không thể coi Gold dương bền bốn năm ở cùng cách thực thi.** "
                 "Hiệu ứng sửa lịch chỉ khoảng −0,01R; phần chênh lớn là trọng số khối lượng. "
                 "Hai budget đã thuộc policy được giao; phép đối chiếu để giải thích, không chọn 125 USD để cứu năm 2025.",
                 "## 4. Vì sao Gold chậm lại?"]
    rows = []
    for a in p["gold_structure"]:
        rows.append([a["year"], n(a["median_entry_price"]), n(a["median_asian_range"]),
                     n(a["median_natural_sl"]), n(a["median_stop_ATR"]), n(a["median_stop_price_pct"]),
                     n(a["median_budget_utilization_pct"])])
    sections += [table(["Năm", "Giá entry median", "Asia range USD/oz", "SL USD/oz", "SL/ATR", "SL/giá %", "Dùng budget %"], rows),
                 "Vùng Á và stop tăng không chỉ vì giá vàng cao hơn: SL/giá tăng từ 0,64% lên 1,28%; "
                 "SL/ATR cũng thay đổi. Cùng một quãng đi tiếp bằng USD nay đem lại ít R hơn khi stop lớn; "
                 "minimum lot làm sizing thô hơn. Đây là mô tả đo được, chưa chứng minh một nguyên nhân duy nhất. "
                 "Sự đổi vai BUY/SELL cũng rõ: SELL tạo phần lớn lãi 2022–2023, nhưng mất khoảng 12R năm 2024; "
                 "BUY bù lại. Không suy rằng cứ chọn BUY là sẽ giải quyết được.",
                 "### MFE và markout 24 giờ so với kết quả giữ tối đa 48 giờ",
                 "MFE là mức lãi nổi lớn nhất sau spread trên đường lệnh còn sống, trước commission/slip/swap. "
                 "Ngày 1 ≤24h, ngày 2 >24h. Mark24 lấy giá tại min(entry+24h, actual exit), có phí; "
                 "lệnh đã SL không được giả định tiếp tục sống."]
    rows = []
    for a in p["gold_structure"]:
        m = a["models"]["ASYM_FLAT"]
        rows.append([a["year"], f"{a['MFE_day1_count']}/{a['MFE_day2_count']}", a["second_day_trades"],
                     n(m["mark24_R"], 3), n(m["day2_increment_R"], 3), n(m["net_R"], 3)])
    sections += [table(["Năm", "MFE ngày 1/2", "Còn sống sang ngày 2", "Mark24 R ASYM", "Ngày 2 thêm R", "Final R"], rows),
                 "MFE thường ở ngày 1 **không chứng minh thoát 24h tốt hơn**. Ngày 2 cứu lợi nhuận ở 2022–2024, "
                 "nhưng lấy bớt lợi nhuận ở 2025–2026. Đây là chẩn đoán trên dữ liệu đã xem; "
                 "không đăng ký/thử một policy 24h mới và không chọn horizon sau khi thấy bảng.",
                 "## 5. Các cấu hình Gold có sẵn trong Top 10 PR #80"]
    rows = []
    for c in r["top10"]["cells"]:
        m = c["models"]["ASYM_FLAT"]
        rows.append([c["id"], "/".join(n(v, 2) for v in m["own_full_budget_annual_net_R"].values()),
                     n(m["correlation_gold"], 3), n(m["without_EUR_combined_net_R"]),
                     n(m["without_EUR_combined_DD_R"]), c["source_complete"]])
    sections += [table(["Cell cũ", "Own R 2022/23", "Tương quan Gold", "Gold+cell Net R", "DD R", "Source complete"], rows),
                 "Tái dùng đúng curves Development 2022–2023, Gold risk 150 USD + sleeve 75 USD, không EUR. "
                 "Ba cell là cùng ý tưởng sweep với ba horizon, không phải ba alpha độc lập. "
                 "Ví dụ DAY cải thiện sơ bộ ASYM từ 22,36R/DD20,89R thành 35,63R/DD18,82R.",
                 "**Chưa thêm cell nào:** source path chưa hoàn chỉnh; natural SL median 4,83/4,52 USD/oz, "
                 "phí/SL 16,2%/16,7%, chỉ giữ 23/51 và 22/56 tín hiệu (45,1%/39,3%). "
                 "Không đạt scale/retention gate. Chưa đo mới 2024–2026 cho các cell này; không gọi là winner ngoài mẫu.",
                 "## 6. Kiểm chứng, hậu kiểm kỹ thuật và giới hạn"]
    rows = []
    for o in ORDERS:
        a = r["scenarios"][o]["parity"]
        rows.append([o, a["status"], a["cases"], a["admissions"], a["rejects"], a["cost_bridges"], a["dynamic_fills"]])
    sections += [table(["Thứ tự OHLC", "Oracle", "Sổ", "Admissions", "Rejects", "Cost bridges", "Dynamic fills"], rows),
                 f"**{r['tests']['unique_tests']} tests riêng biệt PASS**, gồm 11 fixtures V7; "
                 "matrix dùng bốn môi trường dependency sẵn có. Alternate accounting dùng phân số hữu tỷ, cash-posted, "
                 "đối chiếu admission/lot/risk, swap/commission/slip, phase/reward và DD cho 402 sổ mỗi thứ tự "
                 "(342 rolling +30 Funded +30 reference). Cùng implementer, không có reviewer độc lập.",
                 "Gold 2025–2026 vẫn là **Bid M1 + Ask proxy 0,338 USD/oz**; hai thứ tự OHLC giả định là kiểm độ nhạy, "
                 "không phải tick thật và không bao hết mọi intraminute path. Hai thứ tự cho cùng kết quả annual; "
                 "số mốc pass/payout/breach cũng không đổi. Chênh aggregate là peak-DD co-core nhóm mới "
                 "0,0005 điểm phần trăm và thời điểm P1 Gold ở cấp giây; JSON giữ riêng toàn bộ lifecycle/sensitivity. "
                 "Peak-to-valley co-core nhóm mới có thể vượt 14% vốn đầu dù static loss chưa chạm giới hạn: "
                 "hai thước đo có mốc gốc khác nhau. Phí/swap là scenarios, lịch tin và thông số đích lịch sử chưa certified đầy đủ.",
                 table(["Phần", "Phát hiện", "Xử lý / kiểm chứng", "Còn hạn chế"], [
                     ["Verifier", "Đến ngưỡng harvest giữa hai clock events", "Observe threshold ngay trước admission; 2 regression; oracle 804 sổ PASS", "Cùng người viết; không independent person review"],
                     ["Source/lịch", "Quote được yêu cầu đúng lúc holiday đóng", "Rule trước 2 phút đã freeze; 0 endpoint thiếu", "Chỉ 11 ngày có giờ FTMO đã xác minh"],
                     ["Reuse", "Đã có đủ ledgers/Top10 và test environments", "Tái dùng artifacts; không rerun producer sau sửa verifier", "Không đo speedup/quota tiết kiệm"],
                     ["Skill/workflow", "Rule hiện có đã yêu cầu giữ attempt và kiểm transition", "Giữ failed attempts; cập nhật report/context, không thêm skill/config", "Không mở vòng tối ưu mới"],
                 ]),
                 "Hai lần oracle đầu thất bại được giữ trong `parity-primary.log`, `parity-secondary.log`, "
                 "`oracle-attempt1.json`. Lỗi ở verifier: chưa observe ngưỡng harvest đến hạn tại thời điểm entry; "
                 "đã sửa verifier, không sửa producer hoặc số liệu giao dịch để pass.",
                 "## 7. Quyết định và bước tiếp",
                 "**EURUSD Sweep đã decommission khỏi ứng viên active. Gold A BOTH giữ làm baseline nghiên cứu, "
                 "chưa promote Gold tăng risk, chưa thêm sleeve và chưa đổi sang exit 24h.** "
                 "Nút thắt hiện tại là lợi nhuận không đều, quá chậm so với mục tiêu Challenge/payout, "
                 "nhạy sizing và thiếu bằng chứng execution đích; chưa phải do chạm trần Daily Loss trong các đường mô phỏng.",
                 "Bước hợp lý tiếp theo là chốt khoảng thiếu về quote/cost/news của tài khoản đích và đăng ký "
                 "một kiểm định hữu hạn trên dữ liệu thực sự mới khi có; không tiếp tục chỉnh trên 2025–2026 "
                 "rồi gọi đó là kiểm định độc lập. V7 không mua Challenge, không gửi broker order, không nhận tiền thực.",
                 "## Bằng chứng và tái hiện",
                 f"- Freeze trước outcome: `{r['freeze_commit']}`.",
                 "- Protocol: `PROP-GOLD-V7-PROTOCOL-20261115.md`; decision: `PROP-GOLD-V7-DECISION-20261115.json`; calendar: `PROP-V7-SESSION-CALENDAR-20261115.json`.",
                 "- Báo cáo JSON cùng tên giữ 4 cột theo model/path, annual/side, rolling/Funded summaries, payout quý và hashes của ledgers đầy đủ.",
                 f"- Full private ledgers/tests/failed attempts: `{JOB.as_posix()}`.",
                 "- Chỉ dựng lại báo cáo từ artifact: `python tooling/ai-engines/prop_v7_report.py` với PYTHONPATH hiện có; không chạy lại backtest.",
                 "- Nguồn FTMO/CME đã kiểm ở lượt sửa lịch, receipt: `calendar-source-receipt.json`. Các URL:",
                 *[f"  - {url}" for url in r["calendar_source"]["sources"]],
                 f"  - {r['calendar_source']['CME']}",
                 ]
    OUT.with_suffix(".md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
