"""V4 delivery report from frozen decisions and verified account ledgers."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

from prop_campaign_report import aggregate, compact
from prop_portfolio_scan import corr
from prop_cocore_v4 import JOB, V3, V1, DECISION, read, write_json, digest

OUT = Path("planning/research/PROP-COCORE-V4-RESULTS-20261114")


def brief(row):
    return {k: v for k, v in compact(row).items() if k != "entry_audit"}


def date_text(at):
    return datetime.fromtimestamp(at / 1000, timezone.utc).strftime("%Y-%m-%d")


def asset_counts(cases, trades, cocore):
    result = {}
    for asset in ("XAUUSD", "EURUSD"):
        rejected = Counter()
        admitted = throttled = 0
        for c in cases:
            for a in c["entry_audit"]:
                if a["asset"] == asset and not a["accepted"]:
                    rejected[a["reason"]] += 1
            for a in c["accepted"]:
                if trades[a["trade"]]["asset"] != asset:
                    continue
                admitted += 1
                base = ((200, 175, 125) if cocore or asset == "XAUUSD"
                        else (100, 100, 75))[a["phase"] - 1]
                throttled += a["risk_usd"] < base
        result[asset] = dict(accepted=admitted, throttled=throttled,
                             rejects=dict(rejected))
    return result


def funded_details(cases, trades):
    result = []
    for c in cases:
        if len(c["phase_passes"]) != 2:
            continue
        closed = [r for r in c["closed"] if r["phase"] == 3]
        accepted = [a for a in c["accepted"] if a["phase"] == 3]
        fingerprint = hashlib.sha256(json.dumps(
            [(a["trade"], a["quantity_steps"], a["risk_usd"]) for a in accepted]
        ).encode()).hexdigest()
        result.append(dict(
            start=date_text(c["start_msc"]),
            step1=date_text(c["phase_passes"][0]["at"]),
            step2=date_text(c["phase_passes"][1]["at"]),
            first_funded_trade=date_text(min(a["at"] for a in accepted)) if accepted else None,
            final_balance_usd=c["balance_usd"], funded_closed=len(closed),
            funded_net_usd=sum(x["net_usd"] for x in closed),
            funded_peaks=c["funded_peaks"], funded_path_hash=fingerprint,
            payouts=c["payouts"]))
    return result


def build():
    parity = read(JOB / "accounting-parity.json")
    default = read(JOB / "v3-default-parity.json")
    tests = read(JOB / "regression-tests.json")
    if parity["status"] != "PASS" or default["status"] != "PASS" or not tests["passed"]:
        raise ValueError("V4_report_requires_checks")
    decision = read(DECISION)
    release = read(JOB / "validation-release.json")
    blob = subprocess.check_output([
        "git", "show", release["decision_commit"] + ":" + DECISION.as_posix()])
    if json.loads(blob) != decision:
        raise ValueError("decision_binding")
    for p in decision["code_and_rules"] + decision["input_pins"]:
        if digest(p["path"]) != p["sha256"]:
            raise ValueError("frozen_hash_changed:" + p["path"])
    cases = read(JOB / "validation-accounts.json")
    old = read(JOB / "v3-reproduced-accounts.json")
    trades = read(V3 / "system-trades.json")
    selections = {(m, days): [c for c in cases if c["cell"] == m and
                              c["reward_interval_days"] == days]
                  for m in ("SYM_FLAT", "ASYM_FLAT") for days in (14, 30)}
    summaries = {f"{m}:{days}": aggregate(cs) for (m, days), cs in selections.items()}
    v3report = read(Path("planning/research/PROP-PORTFOLIO-V3-RESULTS-20261114.json"))
    comparisons = [
        dict(name="PR79 A/risk v1 ASYM", **v3report["lifecycle_comparisons"]["ASYM_FLAT"][0]),
        dict(name="PR80 A/risk v2 ASYM", **v3report["lifecycle_comparisons"]["ASYM_FLAT"][1]),
        dict(name="V3 A+EUR ASYM", **v3report["lifecycle_comparisons"]["ASYM_FLAT"][3]),
        dict(name="V4 co-core ASYM/14d", **summaries["ASYM_FLAT:14"]),
        dict(name="V4 co-core SYM/14d", **summaries["SYM_FLAT:14"])]
    audit = read(JOB / "third-sleeve-audit.json")
    postmortem = read(JOB / "v3-postmortem.json")
    eur = read(JOB / "eur-development-books.json") + read(JOB / "eur-validation-book.json")
    combined = read(JOB / "eur-combined-books.json")
    native = read(V3 / "final-satellite-decision.json")
    correlations = {}
    for m, row in native["comparison"].items():
        correlations[m] = {
            str(y): corr(row["sleeve"]["daily"], row["core"]["daily"], y)
            for y in (2022, 2023)}
        correlations[m]["pooled"] = row["correlation"]
    counts = {}
    for m in ("SYM_FLAT", "ASYM_FLAT"):
        counts[m] = dict(
            V3=asset_counts([c for c in old if c["cell"] == m], trades, False),
            V4=asset_counts(selections[(m, 14)], trades, True))
    funded = {m: funded_details(selections[(m, 14)], trades)
              for m in ("SYM_FLAT", "ASYM_FLAT")}
    result = dict(
        schema="PROP-COCORE-V4-RESULTS-v1",
        created_utc=datetime.now(timezone.utc).isoformat(),
        local_delivery_date="2026-11-15", campaign_date_utc="2026-11-14",
        merged_pr81="5864d8b1ef431a93df80f66620f1629896abdc98",
        decision="CONDITIONAL_RESEARCH_PROGRESS_NO_PAYOUT_NOT_FINAL_HOLDOUT_READY",
        prop_qualified=False, prices2025_2026_read=False, broker_calls=0, model_calls=0,
        composition=decision, release=release, comparison=comparisons,
        reward_comparisons=summaries, third_sleeve=audit, v3_postmortem=postmortem,
        eur_reference_books=[brief(r) for r in eur],
        eur_combined_reference=[brief(r) for r in combined],
        correlation_dev=correlations, asset_admissions=counts, funded=funded,
        v3_funded_peak_diagnosis=[dict(start=c["start_msc"], peaks=c["funded_peaks"])
                                  for c in read(JOB / "v3-funded-paths.json")],
        holdout_readiness=read(JOB / "holdout-readiness.json"),
        official_reward_fetch=read(JOB / "ftmo-reward-primary.json"),
        accounting_parity={k: v for k, v in parity.items() if k != "records"},
        v3_default_parity=default, tests=tests,
        accounts=[brief(c) for c in cases],
        development=read(JOB / "risk-decision.json"),
        source_review_reused=dict(
            path=str(V3 / "source-parity.json"), sha256=digest(V3 / "source-parity.json"),
            status="PASS; no source changes; current tick loader rechecks each hour hash"),
        review="same implementer; alternate cash/funding arithmetic, no independent human/model reviewer",
        artifacts=[dict(name=p.name, sha256=digest(p)) for p in sorted(JOB.glob("*.json"))
                   if p.name not in ("status.json", "delivery-receipt.json")],
        private_job=str(JOB))
    write_json(OUT.with_suffix(".json"), result)
    lines = [
        "# V4 — tăng tốc hoàn tất hai vòng, vẫn chưa tạo payout",
        "",
        "**Đã hoàn tất V4:** chính sách song trụ tạo 3/36 cửa sổ hoàn tất hai vòng "
        "ở swap bất đối xứng và 2/36 ở swap đối xứng; **payout vẫn 0**. "
        "Sụt giảm từ đỉnh tăng lên khoảng 14,4%, còn lỗ dưới vốn đầu sát 8%. "
        "Không chọn thêm nhánh thứ ba và chưa đủ điều kiện mở ngay một bài thi "
        "holdout đầy đủ 01/2025–10/2026.",
        "",
        "Task `d6d78dc3-c7e9-40ee-a684-61490c368f27`; PR81 đã merge "
        "`5864d8b`, xóa nhánh V3. Campaign dùng ngày UTC 14/11; kiểm/bàn giao "
        "ngày địa phương 15/11/2026. WIP VI Dubber và Trader pin giữ nguyên. "
        "Không broker, provider/model call hoặc giải mã giá 2025–2026.",
        "",
        "## 1. Năm cột so sánh — cùng 36 mốc xuất phát tháng",
        "",
        "| Chỉ tiêu | PR79 A/v1 ASYM | PR80 A/v2 ASYM | V3 A+EUR ASYM | V4 ASYM/14 ngày | V4 SYM/14 ngày |",
        "|---|---:|---:|---:|---:|---:|"]
    for title, key, kind in [
        ("Qua vòng 1", "step1", "count"), ("Qua cả hai vòng", "both", "count"),
        ("Trung vị qua vòng 1*", "step1_median_months_completed_only", "months"),
        ("Trung vị hoàn tất hai vòng*", "both_median_months_completed_only", "months"),
        ("Số payout mô phỏng", "payouts", "integer"),
        ("USD trả trader trong mô hình", "trader_payout_usd", "usd"),
        ("Lỗ ngày lớn nhất", "worst_daily_pct", "pct"),
        ("Lỗ dưới vốn đầu lớn nhất", "worst_static_pct", "pct"),
        ("Sụt giảm từ đỉnh lớn nhất", "worst_peak_dd_pct", "pct"),
        ("Vi phạm trong mô hình", "breaches", "integer")]:
        def render(value):
            if value is None:
                return "N/A"
            return (f"{value}/36" if kind == "count" else f"{value:.2f} tháng"
                    if kind == "months" else f"${value:,.2f}" if kind == "usd"
                    else f"{value:.3f}%" if kind == "pct" else str(value))
        lines.append("| " + title + " | " + " | ".join(render(c[key]) for c in comparisons) + " |")
    lines += [
        "",
        "*Chỉ tính cửa sổ đã đạt; không phải dự báo thời gian cho mọi tài khoản. "
        "Các mốc chồng lấn, những mốc cuối mẫu có ít thời gian theo dõi hơn. "
        "V4 có ít cửa sổ qua vòng 1 hơn V3, nhưng nhiều cửa sổ hoàn tất vòng 2 "
        "hơn. Không được kết luận tăng risk chắc chắn tăng mọi chỉ tiêu.",
        "",
        "Các tỷ lệ lỗ/DD trong bảng đều chia cho vốn đầu $50.000. Sụt giảm "
        "từ đỉnh khác lỗ dưới vốn đầu: tài khoản có thể mất cả lợi nhuận đã "
        "tích lũy rồi xuống sát 46k, tạo peak-to-valley >10% vốn đầu nhưng "
        "chưa chạm static floor 45k. Đó vẫn là tổn thất lớn với người vận hành.",
        "",
        "Mỗi model V4 chỉ có **một đường funded riêng biệt**: các cửa sổ thành "
        "công cùng qua vòng 1 ngày 29/09/2023, vòng 2 ngày 20/10/2023 rồi trùng "
        "đường giao dịch funded. Ba cửa sổ ASYM không phải ba lần thành công độc lập.",
        "",
        "## 2. Đã thay gì và vì sao",
        "",
        "| Thành phần | V3 | V4 đã khóa |",
        "|---|---|---|",
        "| Gold risk P1/P2/Funded | $200/$175/$125 | Giữ nguyên |",
        "| EUR risk P1/P2/Funded | $100/$100/$75 | $200/$175/$125 |",
        "| Trần tổng initial-stop đang mở | $500 / 1% | $800 / 1,6% |",
        "| Cổng equity dự phóng sau SL/phí/funding | $46.500 / −7% | $46.000 / −8% |",
        "| Throttle theo equity hiện tại | Chạm −4%: cap $150; −6%: cap $90 | Giữ nguyên cho cả hai nhánh |",
        "| Cầu dao lỗ thực hiện ngày | −2%, nghỉ đến Prague reset | Giữ nguyên |",
        "| Reward proxy | 30 ngày | So sánh 14 và 30 ngày |",
        "",
        "Không đổi entry, natural SL, phía BUY/SELL, lịch đóng, phí hoặc swap. "
        "Không D1 filter mới, TP, trailing hay kéo SL. Chỉ một trial equal-risk "
        "trên 48 cửa sổ Dev; worst static 7,9359%, worst daily 1,34082%, không "
        "modeled breach. Không thử thêm trọng số hoặc nới cổng sau kết quả.",
        "",
        "ASYM giữ swap Gold BUY −45 / SELL −5 USD/lot/rollover; SYM −40/−40, "
        "thứ Tư nhân ba theo profile kế thừa. Gold commission 0,0007% "
        "notional/side, stress slippage 0,20 USD/oz/side; EUR commission $5 "
        "+ slippage $4/lot/vòng và spread Bid/Ask quan sát. EUR đóng trong "
        "ngày nên không phát sinh rollover. Đây là profile nghiên cứu, chưa "
        "là biểu phí lịch sử đã chứng nhận của tài khoản FTMO cụ thể.",
        "",
        f"Composition commit `{release['decision_commit']}` trước release "
        f"`{release['utc']}` và lần traversal 2024 mới. Code/rule/input hashes "
        "khớp bản đã khóa. 2024 đã exposed, chỉ Historical Validation, không clean OOS.",
        "",
        "**EUR không có đường vốn mượt:** nâng ngang hàng chỉ là trial owner "
        "cho phép, không phải kết luận EUR ít rủi ro hơn Gold. Corr ngày thấp "
        "không bảo đảm hai lệnh không cùng lỗ trong một giờ. Trần 1,6% vẫn cộng "
        "rủi ro tuyệt đối, không net BUY/SELL hoặc trừ theo correlation.",
        "",
        "## 3. Giải phẫu EUR riêng ở risk tham chiếu $150",
        "",
        "| Năm | Lệnh | Net R | Peak-to-valley DD (R) | Worst daily loss (R) |",
        "|---|---:|---:|---:|---:|"]
    for c in eur:
        lines.append(f"| {date_text(c['start_msc'])[:4]} | {c['entries']} | {c['net_R']:+.3f} "
                     f"| {c['max_equity_R_DD']:.3f} | {c['worst_daily_loss_pct']/.3:.3f} |")
    for c, label in zip(combined, ("2022–2023", "2022–2024")):
        lines.append(f"| {label} liên tục | {c['entries']} | {c['net_R']:+.3f} "
                     f"| {c['max_equity_R_DD']:.3f} | {c['worst_daily_loss_pct']/.3:.3f} |")
    lines += [
        "",
        "Đây là đường equity tick của EUR riêng, 1R=$150, không annual-reset "
        "để ghép sổ liên tục. DD gộp Dev 35,757R lớn hơn tổng lợi nhuận 14,334R; "
        "không gọi là ít drawdown chỉ vì cuối hai năm dương. Top3 lệnh thắng "
        "mỗi năm vẫn quyết định hơn toàn bộ lợi nhuận EUR năm đó theo V3.",
        "",
        "| Swap Gold | Corr ngày 2022 | Corr ngày 2023 | Corr gộp Dev |",
        "|---|---:|---:|---:|"]
    for m, v in correlations.items():
        lines.append(f"| {m} | {v['2022']:.3f} | {v['2023']:.3f} | {v['pooled']:.3f} |")
    lines += [
        "",
        "Dùng thay đổi equity cuối ngày Prague trên cùng business-day grid, "
        "có ngày 0. Đây là tương quan trong Development, không phải bảo đảm tương lai.",
        "",
        "## 4. Top10 và quyết định không thêm nhánh thứ ba",
        "",
        "Giữ thứ hạng screen V3: EUR là #6, không phải #1. Các con số còn lại "
        "là screen M1/H1 có điều kiện; EUR được thay bằng tick đã xác nhận. "
        "Bảng dùng ASYM; JSON giữ cả hai models và toàn bộ lý do loại.",
        "",
        "| # | Asset / cơ chế / giữ | Net R 2022 | Net R 2023 | Corr Gold | Corr EUR | Lý do chưa thêm |",
        "|---:|---|---:|---:|---:|---:|---|"]
    for r in audit["top10"]:
        m = r["models"]["ASYM_FLAT"]
        n = m["net_R"]
        cg, ce = m["correlation_gold"], m["correlation_eur"]
        if r["rank"] == 6:
            n = native["comparison"]["ASYM_FLAT"]["sleeve"]["net_R"]
            cg, ce = correlations["ASYM_FLAT"]["pooled"], 1.
        name = r["id"]
        reason = ("Đã là co-core" if r["rank"] == 6 else
                  "Thiếu M1/tick" if name.startswith("GBPUSD") else
                  "Retention/scale, Gold Ask/path" if name.startswith("XAUUSD") else
                  "Retention/scale và carry/cổ tức chưa xác minh")
        if any("ECONOMIC_GATE" in d["reasons"] for d in r["models"].values()) and r["rank"] != 6:
            reason += "; không ổn định kinh tế"
        lines.append(f"| {r['rank']} | {name} | {n['2022']:+.3f} | {n['2023']:+.3f} "
                     f"| {cg:.3f} | {ce:.3f} | {reason} |")
    lines += [
        "",
        "SWEEP = quét qua biên rồi quay lại; ASIA/PREVDAY = phiên Á/ngày trước; "
        "LONDON/NY = phiên London/New York; DAY = đóng trong ngày. DAY/24H/48H "
        "trên cùng cohort không phải ba nguồn lợi nhuận độc lập.",
        "",
        "GBPUSD Asia/London là hướng đáng kiểm chất lượng nguồn tiếp: dương "
        "hai năm, corr EUR khoảng 0,20 và corr Gold gần 0. Nhưng chỉ H1 không "
        "đủ kết luận SL fill/equity M1; QDM metadata hiện không có GBP cached "
        "dataset. Không lấy screen H1 đẹp để cấp vốn thật. Gold sweep mất hơn "
        "50% raw signals ở cổng phí; US500 thiếu carry/dividend và scale. "
        "Vì vậy **không thêm sleeve #3** trong ngân sách hiện tại.",
        "",
        "## 5. Lệnh bị chặn và giảm risk",
        "",
        "| Model / policy | Asset | Nhận | Risk bị throttle* | Chặn cap | Chặn reserve nội bộ | Chặn daily halt |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for model, policies in counts.items():
        for policy, assets in policies.items():
            for asset, v in assets.items():
                rejects = v["rejects"]
                cap = sum(x for k, x in rejects.items() if "OPEN_STOP_RISK" in k)
                reserve = sum(x for k, x in rejects.items() if "INTERNAL_STATIC" in k)
                halt = rejects.get("DAILY_REALIZED_2PCT_HALT", 0)
                lines.append(f"| {model} / {policy} | {asset} | {v['accepted']} "
                             f"| {v['throttled']} | {cap} | {reserve} | {halt} |")
    lines += [
        "",
        "*So với nominal risk riêng của nhánh/phase; lượng lot làm tròn xuống "
        "không tính là throttle. Cap từ chối nguyên lệnh, không tự giảm size để "
        "lách cap. Counts cộng trên 36 cửa sổ chồng lấn, không là số tín hiệu "
        "độc lập bị bỏ lỡ. JSON giữ cả phase/prestart/collision/lot rejects.",
        "",
        "V4 loại được cap rejects trong mẫu đã đo nhưng reserve chặn nhiều hơn "
        "vì EUR nhận vốn lớn hơn và đường vốn đi sát floor. Khi tài khoản đã "
        "flat sát floor, cổng này có thể chặn mọi cơ hội mới và tài khoản đứng "
        "lại dù chưa vi phạm luật hãng. Không gọi những cửa sổ đó là an toàn "
        "và chỉ cần chờ thêm chắc chắn sẽ hồi phục.",
        "",
        "## 6. Vì sao chưa payout dù từng có equity dương?",
        "",
        f"Trong 13 cửa sổ V3 chưa xong vòng 2, **{postmortem['phase2_positive']} dương "
        f"và {postmortem['phase2_negative']} âm** lúc hết mẫu. Các cửa sổ đều "
        "right-censored, nhưng không đồng nghĩa tất cả chỉ thiếu thời gian.",
        "",
        "Đường funded V3: equity cao nhất $50.379,30 (cũng xảy ra sau mốc "
        "14/30 ngày), nhưng closed balance cao nhất chỉ $50.000. Khi flat và "
        "đủ 14 hoặc 30 ngày, balance cao nhất $49.849,38. Equity dương khi "
        "còn giữ lệnh không phải lợi nhuận có thể rút; đóng cưỡng bức tại một "
        "đỉnh biết sau sẽ là một biến thể exit mới, không phải sửa lịch payout.",
        "",
        "| V4 / mốc bắt đầu | Pass P1 / P2 | Balance cuối funded | Max equity funded | Max balance flat ≥14d |",
        "|---|---|---:|---:|---:|"]
    for m, rows in funded.items():
        for r in rows:
            p = r["funded_peaks"]
            lines.append(f"| {m} / {r['start']} | {r['step1']} / {r['step2']} "
                         f"| ${r['final_balance_usd']:,.2f} | ${p['equity_usd']:,.2f} "
                         f"| ${p['flat_balance_after14_usd']:,.2f} |")
    lines += [
        "",
        "| Swap | Proxy | Qua P1 | Qua cả hai | Số payout | USD trader |",
        "|---|---:|---:|---:|---:|---:|"]
    for key, a in summaries.items():
        lines.append(f"| {key.split(':')[0]} | {key.split(':')[1]} ngày | "
                     f"{a['step1']}/36 | {a['both']}/36 | {a['payouts']} "
                     f"| ${a['trader_payout_usd']:,.2f} |")
    lines += [
        "",
        "**Đổi 30 sang 14 ngày không tạo payout trong mẫu này.** Có closed "
        "balance V4 trên 50k khi còn vị thế khác/đầu kỳ, nhưng không có lãi "
        "flat đủ điều kiện ở cửa sổ request được mô phỏng.",
        "",
        "14 ngày là mốc eligibility/request, không phải cam kết nhận tiền "
        "đều đặn mỗi hai tuần. Mô hình giữ cùng account, debit toàn bộ profit, "
        "chia 80/20, minimum $20, zero admin delay và đếm lại interval từ "
        "request trước; đây là assumptions của proxy. Không mô phỏng approval/"
        "chuyển khoản/thuế/phí challenge, thay tài khoản hay rút một phần.",
        "",
        "Lượt kiểm FAQ chính thức FTMO "
        "`https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/` không đọc được "
        "do lỗi TLS; không nâng bằng chứng lịch sử 12/11 thành xác minh điều "
        "khoản mới ngày 15/11. Historical source ở Gold cost audit vẫn giữ. "
        "14/30-day results là scenario có khai báo, không FTMO acceptance.",
        "",
        "## 7. Readiness cho 01/2025–10/2026",
        "",
        "Chỉ gọi QDM `-symbol action=list`, không export/update, không hash/"
        "giải mã nội dung giá holdout.",
        "",
        "| Dataset metadata hiện có | Ngày cuối quảng bá | Kết luận giới hạn |",
        "|---|---|---|"]
    ready = result["holdout_readiness"]
    for s in ready.get("symbols", []):
        lines.append(f"| {s['Symbol']} / {s['Timeframe']} | {s['Date to']} | "
                     "Có metadata, chưa kiểm từng ngày/giá |")
    lines += [
        "",
        "**Chưa sẵn sàng để bấm chạy ngay full window:** Gold M1 mới tới "
        "13/10/2026, EUR M1 tới 07/10; EUR tick quảng bá tới 01/11 nhưng chưa "
        "kiểm coverage. Không có XAUUSD tick dataset được list; paired Gold "
        "ticks 2025–2026 chưa được chứng nhận. Metadata không chứng minh nguồn "
        "hoàn toàn sạch OOS; các task khác có thể đã dùng dữ liệu đó.",
        "",
        "Trước một lần release holdout cần owner duyệt riêng: khóa một final "
        "policy/horizon/cost/stop criterion, seed causal, lịch holiday/session "
        "2025–2026 và news/spec profile; admission/coverage/raw integrity và "
        "exposure manifest cho đúng hai tài sản. Không đổi tham số sau khi mở "
        "hoặc dùng phần thiếu để chọn lại khoảng ngày. Không tự tải thêm/mở "
        "giá hoặc cam kết chỉ duyệt PR là đủ mọi gate.",
        "",
        "## 8. Kiểm chứng, hậu kiểm và quyết định",
        "",
        f"- {tests['tests']} tests đạt, gồm 12 fixtures V4 về co-core risk, "
        "throttle, default V3, cap/floor, reward 14/30/flat/full-debit và source gates.",
        "- 72 tài khoản V3 tái hiện khớp chính xác accepted/closed/rejections, "
        "cash, DD, phase và payout; không đổi kết quả lịch sử vì thêm policy hooks.",
        f"- {parity['accounts']} tài khoản V4 khớp oracle cash-posted funding: "
        f"{parity['accepted']:,} admissions, {parity['rejected']:,} rejections, "
        f"{parity['money_bridges']:,} cost bridges, "
        f"{parity['joint_quote_updates']:,} quote updates kiểm theo timestamp.",
        "- Reuse raw-source parity V3 (25.447.523 tick EUR khớp CSV); source "
        "không đổi, loader hiện tại kiểm hash từng giờ giá được đọc.",
        "- Cùng implementer dùng hạch toán khác; không độc lập người/model, "
        "không Astra. Chưa có live fills, forward, broker/model/provider call.",
        "- Target contract/lot/margin/leverage, swap thực tế, lịch tin hạn chế "
        "và phiên đúng feed chưa xác minh đủ. Carried quotes khi thị trường "
        "nghỉ không thành fresh reset quotes. Không modeled breach trong "
        "profile không phải chứng nhận account FTMO thực tế.",
        "",
        "| Hậu kiểm | Quyết định |",
        "|---|---|",
        "| Lịch payout30 từng bị xem là nguyên nhân chính | Kiểm proxy14: vẫn0, không có lãi flat đủ điều kiện |",
        "| Satellite ít risk có phải nút thắt duy nhất | Co-core tăng completion, nhưng peak DD tăng và payout0; không tiếp tục nới risk |",
        "| Correlation thấp bị hiểu thành an toàn đồng thời | Giữ gross cap và reserve, không net correlation |",
        "| V3 thiếu reject reasons theo tài sản | Reproduce72defaults và instrument reason; khớp archived outcomes |",
        "| Native source census đã có | Reuse source pins, không lặp fullCSVscan hoặc tạo engine/account state song song |",
        "",
        "V4 chưa đạt mục tiêu thu nhập chính. Dừng vòng tăng risk/đổi chu kỳ "
        "để ép payout ở đây. Giữ hai cơ chế làm research benchmark; GBP chỉ "
        "source-readiness, không thêm sleeve yếu. Một đợt kiểm tiếp phải giải "
        "quyết uncertainty đã nêu, không được gọi số cửa sổ pass là xác suất "
        "tương lai hoặc biến 2024 đã exposed thành OOS sạch.",
        "",
        f"Private evidence: `{JOB}`. Báo cáo JSON giữ composition/release, Top10, "
        "comparisons, 144 summary ledgers, EUR books, source/check hashes và "
        "readiness metadata; full ledgers và oracle records ở private job.",
        ""]
    OUT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(OUT.with_suffix(".md"), flush=True)


if __name__ == "__main__":
    build()
