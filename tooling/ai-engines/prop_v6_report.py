"""V6 report: distinguish cash eligibility, incomplete paths and independent trades."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import hashlib
import json
import re
from prop_portfolio_accounts import quantity_steps, trade_money
from prop_v6_common import *

OUT = Path("planning/research/PROP-V4-HARVEST-V6-RESULTS-20261115")


def date(at):
    return datetime.fromtimestamp(at / 1000, timezone.utc).isoformat() if at else None


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "|" + "|".join("---" for _ in headers) + "|"] +
                     ["| " + " | ".join(str(v) for v in r) + " |" for r in rows])


def n(value, places=2):
    return "N/A" if value is None else f"{value:,.{places}f}"


def readable_spacing(text):
    """Separate prose from numbers while preserving code, paths and domain IDs."""
    parts = re.split(r"(`[^`]*`)", text)
    letters = "A-Za-zÀ-ỹ"
    for i in range(0, len(parts), 2):
        value = parts[i].replace("BidM1", "Bid M1").replace("mốcJan", "mốc Jan")
        value = re.sub(rf"([{letters}]+)(?=\d)", lambda m:
                       m[0] if m[0] in ("V", "H", "M", "P", "Q", "D") else m[0] + " ", value)
        value = re.sub(rf"(\d)(?=[{letters}])", r"\1 ", value)
        value = re.sub(r"(?<=[^\s/])(?=\$)", " ", value)
        value = re.sub(r"\b([VHM]) (\d)\b", r"\1\2", value)
        value = re.sub(r"(\d) k\b", r"\1k", value)
        value = re.sub(r"(?<=[A-Za-z]):(?=\d)", ": ", value)
        for a, b in (("BidM", "Bid M"), ("minhọa", "minh họa"), ("fixtureV", "fixture V"),
                     ("dynamicfill", "dynamic fill"), ("failedattempts", "failed attempts"),
                     ("privatejob", "private job")):
            value = value.replace(a, b)
        parts[i] = value
    return "".join(parts)


def brief(a):
    keys = ("start_msc", "end_msc", "effective_end_msc", "requested_end_msc", "cell",
            "standalone_funded", "phase", "phase_passes", "first_breach", "entries",
            "closed_trades", "rejections", "balance_usd", "terminal_equity_usd",
            "peak_dd_pct", "static_loss_pct", "worst_daily_loss_pct", "payouts",
            "trader_payout_usd", "cash_bridge_verified", "open_positions",
            "path_censor", "status", "net_usd", "net_R", "mean_net_R", "max_equity_R_DD")
    return {k: a[k] for k in keys if k in a}


def aggregate(cases):
    funded_paths = set()
    for a in cases:
        if a["phase"] != 3:
            continue
        seq = [(r["trade"], r["at"], r["net_usd"]) for r in a["closed"] if r["phase"] == 3]
        funded_paths.add(hashlib.sha256(json.dumps(seq).encode()).hexdigest())
    payout = [a["trader_payout_usd"] for a in cases]
    elapsed1 = [(a["phase_passes"][0]["at"] - a["start_msc"]) / DAY / 30.4375
                for a in cases if a["phase_passes"]]
    elapsed2 = [(a["phase_passes"][1]["at"] - a["start_msc"]) / DAY / 30.4375
                for a in cases if len(a["phase_passes"]) == 2]
    return dict(starts=len(cases), passed1=sum(bool(a["phase_passes"]) for a in cases),
                passed2=sum(len(a["phase_passes"]) == 2 for a in cases),
                payout_windows=sum(bool(a["payouts"]) for a in cases),
                payout_events=sum(len(a["payouts"]) for a in cases),
                trader_usd_window_sum=sum(payout),
                trader_usd_window_min=min(payout), trader_usd_window_median=median(payout),
                trader_usd_window_max=max(payout),
                unique_funded_ledger_paths=len(funded_paths),
                modeled_breaches=sum(bool(a["first_breach"]) for a in cases),
                daily_breaches=sum(bool(a["first_breach"] and a["first_breach"]["daily"]) for a in cases),
                static_breaches=sum(bool(a["first_breach"] and a["first_breach"]["overall"]) for a in cases),
                max_daily_pct=max(a["worst_daily_loss_pct"] for a in cases),
                max_static_pct=max(a["static_loss_pct"] for a in cases),
                max_peak_pct=max(a["peak_dd_pct"] for a in cases),
                data_censored=sum(bool(a.get("path_censor")) for a in cases),
                measured_to_requested_end=sum(not a.get("path_censor") for a in cases),
                median_months_to_phase1_among_successes=median(elapsed1) if elapsed1 else None,
                median_months_to_both_among_successes=median(elapsed2) if elapsed2 else None)


def independent_cohorts(folder):
    trades = read(folder / "holdout-trades.json")
    raw = read(JOB / "gold-holdout-signals.json") + read(JOB / "eur-holdout-signals.json")
    out = []
    for asset in ("XAUUSD", "EURUSD"):
        for year in (2025, 2026):
            ts = [t for t in trades if t["asset"] == asset and t["day"].startswith(str(year))]
            known, invalid, unknown = [], [], []
            for t in ts:
                try:
                    q = quantity_steps(t, 125)
                except ValueError:
                    invalid.append(t)
                    continue
                if t["reason"] in ("CENSORED", "ENDPOINT_UNKNOWN_OPEN"):
                    unknown.append(t)
                else:
                    known.append((t, q))
            for model in MODELS:
                rs = [trade_money(t, q, model, 125)["net_R"] for t, q in known]
                out.append(dict(
                    asset=asset, year=year, model=model, signal_paths=len(ts),
                    signal_BUY=sum(t["side"] == "BUY" for t in ts),
                    signal_SELL=sum(t["side"] == "SELL" for t in ts),
                    min_lot_rejections=len(invalid), unresolved=len(unknown),
                    priced_closed=len(known), BUY=sum(t["side"] == "BUY" for t, _ in known),
                    SELL=sum(t["side"] == "SELL" for t, _ in known),
                    known_closed_net_R=sum(rs), mean_known_closed_net_R=mean(rs),
                    full_period_net_measured=not unknown, conditional_Gold_M1=asset == "XAUUSD"))
    return out


def mean(rows):
    return sum(rows) / len(rows) if rows else None


def build():
    check_freeze()
    tests = read(JOB / "final-tests.json")
    if tests["status"] != "PASS":
        raise ValueError("V6_tests_incomplete")
    solo = read(JOB / "standalone-funded-accounts.json")
    sp = read(JOB / "standalone-accounting-parity.json")
    scenarios = {}
    for order in read(DECISION)["m1_paths"]:
        f = JOB / order
        parity = read(f / "accounting-parity.json")
        if parity["status"] != "PASS":
            raise ValueError("V6_oracle_not_passed")
        old, fresh = read(f / "continuous-accounts.json"), read(f / "fresh-accounts.json")
        scenarios[order] = dict(
            old_summary={m: aggregate([c for c in old if c["cell"] == m]) for m in MODELS},
            fresh_summary={m: aggregate([c for c in fresh if c["cell"] == m]) for m in MODELS},
            independent_cohorts=independent_cohorts(f),
            path_books=[brief(c) | dict(asset=c["asset"], year=c["year"])
                        for c in read(f / "holdout-reference-books.json")],
            old_accounts=[brief(c) for c in old], fresh_accounts=[brief(c) for c in fresh],
            parity=parity)
    primary = scenarios["OPEN_LOW_HIGH_CLOSE"]
    standalone = {}
    for m in MODELS:
        rows = [r for r in solo if r["cell"] == m]
        jan = rows[0]
        yearly, quarterly, trading_net, year_end_balance = {}, {}, {}, {}
        cash = 50000
        for y in (2022, 2023, 2024):
            yearly[str(y)] = sum(p["trader_usd"] for p in jan["payouts"]
                                 if datetime.fromtimestamp(p["at"] / 1000, timezone.utc).year == y)
            trading_net[str(y)] = sum(c["net_usd"] for c in jan["closed"]
                                     if datetime.fromtimestamp(c["at"] / 1000, timezone.utc).year == y)
            removed = sum(p["gross_removed_usd"] for p in jan["payouts"]
                          if datetime.fromtimestamp(p["at"] / 1000, timezone.utc).year == y)
            cash += trading_net[str(y)] - removed
            year_end_balance[str(y)] = cash
            for q in range(1, 5):
                quarterly[f"{y}Q{q}"] = sum(p["trader_usd"] for p in jan["payouts"]
                    if datetime.fromtimestamp(p["at"] / 1000, timezone.utc).year == y
                    and (datetime.fromtimestamp(p["at"] / 1000, timezone.utc).month - 1) // 3 + 1 == q)
        standalone[m] = dict(
            windows=12, breaches=sum(bool(c["first_breach"]) for c in rows),
            max_daily_pct=max(c["worst_daily_loss_pct"] for c in rows),
            max_static_pct=max(c["static_loss_pct"] for c in rows),
            max_peak_pct=max(c["peak_dd_pct"] for c in rows),
            Jan2022=dict(payouts=len(jan["payouts"]), trader_usd=jan["trader_payout_usd"],
                         gross_profit_debited=sum(p["gross_removed_usd"] for p in jan["payouts"]),
                         per_year=jan["trader_payout_usd"] / 3,
                         per_quarter=jan["trader_payout_usd"] / 12,
                         per_month=jan["trader_payout_usd"] / 36,
                         ending_balance=jan["balance_usd"], year=yearly, quarter=quarterly,
                         annual_trading_net=trading_net, year_end_balance=year_end_balance),
            accounts=[brief(c) for c in rows])
    quality = read(JOB / "holdout-path-quality.json")
    for s in quality["scenarios"]:
        s["issues"] = [r for r in s.pop("evidence") if not r["complete_under_declared_path_model"]]
    frozen = read(DECISION)
    release = read(JOB / "holdout-release.json")
    oldrows = read(JOB / "historical-checkpoint-accounts.json")
    already = [dict(brief(a), after=[brief(b) for b in primary["old_accounts"]
                                    if b["cell"] == a["cell"] and b["start_msc"] == a["start_msc"]][0])
               for a in oldrows if len(a["phase_passes"]) == 2]
    result = dict(
        schema="PROP-V4-HARVEST-V6-RESULTS-v1", date="2026-11-15",
        verdict="NOT_QUALIFIED", freeze_commit=release["commit"],
        policy=frozen, holdout_end_exclusive=END,
        holdout_status="ONE_SHOT_EXPOSED; no tuning; incomplete Gold deadline path",
        standalone_funded=standalone, standalone_parity=sp, scenarios=scenarios,
        previously_funded_windows=already, quality=quality,
        v4_checkpoint_parity=read(JOB / "v4-checkpoint-parity.json"),
        generator_parity=read(JOB / "historical-signal-parity.json"),
        tests=tests, correction=read(JOB / "measurement-correction.json"),
        official_reference=read(JOB / "official-reference-check.json"),
        private_job=str(JOB), broker_executions=0, actual_rewards_received_usd=0,
        independent_reviewer=False, same_operator_alternate_accounting=True,
        future_profitability_or_pass_probability_claimed=False,
        code=[dict(path=p.as_posix(), sha256=digest(p)) for p in sorted(
            Path("tooling/ai-engines").glob("prop_v6_*.py"))])
    write_json(OUT.with_suffix(".json"), result)

    lines = [
        "# V6 — Kết quả V4_Harvest và sát hạch 2025–2026", "",
        "**Chưa đủ điều kiện Challenge/thu nhập chính.** EURUSD âm trên tick đầy đủ ở cả2025",
        "và2026YTD. Gold dương nhẹ ở các lệnh định giá được, nhưng BidM1/Ask giả định và",
        "một hạn thoát nghỉ lễ thiếu giá khiến phần2026 chưa hoàn chỉnh. Có payout mô phỏng",
        "ở một số mốc cũ; không có tiền thưởng thật nào được nhận trong công việc này.", "",
        "## Cấu hình và dữ liệu đã khóa", "",
        f"- PR83 đã merge `5a8dd69`; cấu hình khóa ở `{release['commit']}` trước mở giá holdout.",
        "- V4_Harvest: Gold A + EUR Asia/London sweep, cả hai$200/$175/$125 theo vòng;",
        "  cap mở$800, sàn dự phòng$46k; throttle48k/47k và halt lỗ ngày$1k giữ nguyên.",
        "- Bỏ D1/D2/Target Ratchet; harvester chỉ Funded. Không đổi tín hiệu/SL/chi phí",
        "  hoặc chọn tham số sau khi mở2025–2026. 2022–24 vẫn dùng ticks lịch sử đã duyệt.",
        f"- Gold:632.140 BidM1; Ask mô phỏng=Bid+{frozen['gold_m1_ask_proxy_spread_units']/1000:.3f}USD/oz",
        "  (trung vị spread vào lệnh Dev2022–23), khóa trước mở giá. Hai thứ tự OHLC là",
        "  kịch bản có điều kiện, không phải tick thật hoặc cận DD an toàn đã chứng nhận.",
        "- EUR:38.292.958 tick Bid/Ask gốc, gộp663.309M1; có cả08–13/10/2026.",
        "  Cache-only, không update/download. Cả hai kết thúc13/10/2026 UTC.",
        "- Đây là lần đánh giá đầu của chiến dịch V6 trên đoạn đó; chưa chứng nhận dữ liệu",
        "  này chưa từng bị dự án khác sử dụng. Từ nay đoạn2025–2026 đã có exposure.", "",
        "## Đính chính nguyên nhân lịch sử", "",
        "V4 qua P1 ngày29/09/2023, P2 ngày20/10/2023, đã Funded từ tháng10/2023.",
        "Số dư49.751,56USD là V3; V4 cuối2024 là49.789,71ASYM/49.634,27SYM.",
        "Vì vậy, lý do payout0 của V4 không đơn thuần là chỉ còn vài tuần cuối2024.",
        "Không thể cộng R hai nhánh rồi trừ42R để suy ra tiền còn rút: sizing từng vòng,",
        "lệnh bị từ chối, drawdown, thời điểm chuyển vòng và reset vốn đều ảnh hưởng.",
        "Đối soát72checkpoint V6 trước2025 khớp chính xác V4 về tiền, lệnh, DD và vòng.", "",
        "## Funded độc lập 2022–2024", "",
        "Jan2022 là mốc liên tục3năm và cũng là mốc đầu trong12quý, không phải mẫu thứ13.",
        "Risk Funded danh nghĩa0,25%; throttle/sàn dự phòng vẫn hoạt động.", "",
        table(["Phí", "Kỳ payout Jan22", "Gross trừ khỏi tài khoản", "Trader USD/3năm",
               "TB/năm", "TB/quý", "TB/tháng", "Max daily 12mốc", "Max static 12mốc", "Breach"],
              [[m, s["Jan2022"]["payouts"], n(s["Jan2022"]["gross_profit_debited"]),
                n(s["Jan2022"]["trader_usd"]), n(s["Jan2022"]["per_year"]),
                n(s["Jan2022"]["per_quarter"]), n(s["Jan2022"]["per_month"]),
                n(s["max_daily_pct"], 3)+"%", n(s["max_static_pct"], 3)+"%", s["breaches"]]
               for m, s in standalone.items()]), "",
        "Đây là tiền trader **mô phỏng sau chia80/20**, chưa trừ phí challenge/retry, thuế,",
        "vận hành hoặc thời gian duyệt/chi tiền. Bình quân chỉ khoảng102–107USD/tháng",
        "trên một tài khoản50k ở mốcJan2022, không đủ bằng chứng cho thu nhập ổn định.", "",
        table(["Start", "ASYM kỳ/USD", "ASYM Daily/Static", "SYM kỳ/USD", "SYM Daily/Static"],
              [[date(standalone["ASYM_FLAT"]["accounts"][i]["start_msc"])[:10],
                f'{len(standalone["ASYM_FLAT"]["accounts"][i]["payouts"])}/{n(standalone["ASYM_FLAT"]["accounts"][i]["trader_payout_usd"])}',
                f'{n(standalone["ASYM_FLAT"]["accounts"][i]["worst_daily_loss_pct"],3)}/{n(standalone["ASYM_FLAT"]["accounts"][i]["static_loss_pct"],3)}%',
                f'{len(standalone["SYM_FLAT"]["accounts"][i]["payouts"])}/{n(standalone["SYM_FLAT"]["accounts"][i]["trader_payout_usd"])}',
                f'{n(standalone["SYM_FLAT"]["accounts"][i]["worst_daily_loss_pct"],3)}/{n(standalone["SYM_FLAT"]["accounts"][i]["static_loss_pct"],3)}%']
               for i in range(12)]), "",
        "Thu nhập trader mô phỏng của riêng mốcJan2022:", "",
        table(["Năm", "ASYM USD", "SYM USD"], [[y, n(standalone["ASYM_FLAT"]["Jan2022"]["year"][str(y)]),
                    n(standalone["SYM_FLAT"]["Jan2022"]["year"][str(y)])] for y in (2022, 2023, 2024)]), "",
        "Ví dụ ASYM: cuối2023 balance còn48.616,36USD. Năm2024 giao dịch lãi1.127,84USD,",
        "nhưng cuối năm chỉ hồi lên49.744,20USD, vẫn dưới vốn gốc50k nên không có payout.",
        "**Một năm giao dịch có lãi khác với một năm rút được tiền.**", "",
        table(["Quý", "ASYM USD", "SYM USD"], [[q, n(standalone["ASYM_FLAT"]["Jan2022"]["quarter"][q]),
                    n(standalone["SYM_FLAT"]["Jan2022"]["quarter"][q])]
                    for q in standalone["ASYM_FLAT"]["Jan2022"]["quarter"]]), "",
        "Không cộng tiền12mốc thành thu nhập một tài khoản: chúng chồng lấn cùng lịch sử.", "",
        "## Từng nhánh trên holdout: số lệnh và R", "",
        "Bảng này đo từng tín hiệu độc lập ở risk tham chiếu125USD, không dùng harvester",
        "hoặc admission của tài khoản. BUY/SELL và MeanR chỉ tính các lệnh đóng định giá",
        "được. Gold2026 thiếu1lệnh thoát và có2tín hiệu không đạt lot tối thiểu ở125USD;",
        "tổng R còn lại là **known-cohort**, chưa phải tổng R trọn kỳ của chiến lược.", "",
        table(["Nhánh/năm/phí", "Paths (BUY/SELL)", "BUY/SELL đã đóng", "Lot reject/thiếu",
               "Net R đã biết", "Mean R đã biết", "Đủ kỳ?"],
              [[f'{r["asset"]}/{r["year"]}/{r["model"]}',
                f'{r["signal_paths"]} ({r["signal_BUY"]}/{r["signal_SELL"]})',
                f'{r["BUY"]}/{r["SELL"]}', f'{r["min_lot_rejections"]}/{r["unresolved"]}',
                n(r["known_closed_net_R"], 4), n(r["mean_known_closed_net_R"], 4),
                "Có trong mô hình nguồn" if r["full_period_net_measured"] else "Không"]
               for r in primary["independent_cohorts"]]), "",
        "DD cần đường vốn liên tục. Các sổ đo sau dừng trước điểm thiếu giá, không nối",
        "giá tương lai vào một vị thế chưa biết đã đóng hay chưa. Daily tính trên50k ở",
        "125USD/lệnh; DD R gồm floating và chi phí theo mô hình đã nêu.",
        "Riêng Gold2026: NetR của sổ dưới đây chỉ đến03/07; bảng known-cohort phía trên",
        "có thêm các lệnh định giá được sau03/07, nên hai tổng này khác phạm vi.", "",
        table(["Nhánh/năm/phí", "Lệnh vào/đóng", "Net closed R đến điểm đo", "Equity R-DD",
               "Worst daily", "Đo đến"],
              [[f'{r["asset"]}/{r["year"]}/{r["cell"]}', f'{r["entries"]}/{r["closed_trades"]}',
                n(r["net_R"],4), n(r["max_equity_R_DD"],4),
                n(r["worst_daily_loss_pct"],4)+"%", date(r.get("effective_end_msc",r["end_msc"]))]
               for r in primary["path_books"]]), "",
        "**EURUSD không tiếp tục dương:** năm2025 là -14,5963R;2026 là -3,5090R trên tick đầy đủ.",
        "Gold2025 khoảng+2,82R/+2,96R; Gold2026 known-cohort+1,70R/+2,04R nhưng thiếu",
        "đường thoát nên chưa kết luận dương trọn kỳ. Không chuyển sang Gold-only từ",
        "kết quả này rồi gọi lại cùng dữ liệu là OOS mới.", "",
        "## Các tài khoản chạy liên tục và mốc mới", "",
        "Dừng đo riêng tài khoản còn giữ lệnh Gold không định giá được tại03/07/2026",
        "17:00UTC. Tài khoản đã bỏ qua/đóng trước tín hiệu đó vẫn chạy tiếp đến13/10.",
        "Pass/payout dưới đây là những gì xảy ra **trước cutoff thực đo** của từng sổ.", "",
        table(["Nhóm/phí", "P1", "Cả2", "Sổ có payout", "Lần payout", "USD cộng sổ",
               "Censored", "Đủ đến13/10", "Breach đã đo"],
              [[f'{label}/{m}', f'{s["passed1"]}/{s["starts"]}', f'{s["passed2"]}/{s["starts"]}',
                s["payout_windows"], s["payout_events"], n(s["trader_usd_window_sum"]),
                s["data_censored"], s["measured_to_requested_end"], s["modeled_breaches"]]
               for label,key in (("36mốc cũ","old_summary"),("21mốc mới","fresh_summary"))
               for m,s in primary[key].items()]), "",
        "**USD cộng sổ là tổng của các mô phỏng chồng lấn**, không phải thu nhập một",
        "tài khoản, tiền thật hoặc xác suất payout. Các mốc mới chưa có pass trước điểm",
        "dừng;17/21 bị censor, vì vậy không tuyên bố đã kiểm đầy đủ21mốc đến13/10.", "",
        table(["Nhóm/phí", "Max daily", "Max static", "Max peak→valley",
               "Median tháng P1 / cả2 trong mẫu qua"],
              [[f'{label}/{m}',n(s["max_daily_pct"],4)+"%",n(s["max_static_pct"],4)+"%",
                n(s["max_peak_pct"],4)+"%",
                f'{n(s["median_months_to_phase1_among_successes"])}/{n(s["median_months_to_both_among_successes"])}']
               for label,key in (("36cũ","old_summary"),("21mới","fresh_summary"))
               for m,s in primary[key].items()]), "",
        "Không breach trên phần đã đo không chứng nhận an toàn phần bị thiếu. Sàn8%",
        "là reserve trước lệnh, không bảo đảm equity không bao giờ đi xuống hơn8%.",
        "Static so với50k khác peak-to-valley từ đỉnh cao trước đó.", "",
        "Các sổ đã Funded ngay tại checkpoint cuối2024:", "",
        table(["Start/phí", "Balance31/12/24", "Balance cuối phần đo", "Payout trader USD", "Censor?"],
              [[date(a["start_msc"])[:10]+"/"+a["cell"],n(a["balance_usd"]),
                n(a["after"]["balance_usd"]),n(a["after"]["trader_payout_usd"]),
                bool(a["after"].get("path_censor"))] for a in already]), "",
        "## Nhạy cảm thứ tự M1 và khoảng thiếu", "",
        table(["M1 order/phí","36cũ P1/cả2/payout events","21mới P1/cả2","Censor cũ/mới"],
              [[order+"/"+m,
                f'{s["old_summary"][m]["passed1"]}/{s["old_summary"][m]["passed2"]}/{s["old_summary"][m]["payout_events"]}',
                f'{s["fresh_summary"][m]["passed1"]}/{s["fresh_summary"][m]["passed2"]}',
                f'{s["old_summary"][m]["data_censored"]}/{s["fresh_summary"][m]["data_censored"]}']
               for order,s in scenarios.items() for m in MODELS]), "",
        "Hai thứ tự OHLC không đo được spread thật, đường tick trong phút hay cú nhảy",
        "giá tài khoản đích. Kết quả gần nhau cũng không biến M1 thành tick.", "",
        "Cả hai nguồn có442ngày thường không phải ngày lễ đủ timestamp07–21UTC;",
        "23ngày lễ/đóng sớm được phân loại riêng,186ngày cuối tuần. Đây là kiểm timestamp,",
        "không đồng nghĩa toàn bộ bid/ask và đường vốn được chứng nhận.",
        "Có320đường tín hiệu:152EUR ticks và168Gold có điều kiện.319/320đủ trong mô hình",
        "đường giá đã khai báo;1/320thiếu endpoint Gold02/07/2026→03/07/2026. Không",
        "sửa lịch thành một giờ có giá sau khi nhìn kết quả để lấp điểm này.", "",
        "## Kiểm chứng, sửa lỗi đo và giới hạn", "",
        f"- {tests['unique_tests']}test riêng biệt đã được đối chiếu qua các môi trường sẵn có;",
        " 11fixtureV6. Lượt Python mặc định895tests có15error do thiếuhttpx/statsmodels/",
        " Nautilus; chạy lại đúng module trong3venv đã có, tất cả đạt. Không bỏ test.",
        f"- Oracle tiền hữu tỷ:24sổ Funded độc lập +114sổ/scenario×2, tổng252sổ đạt.",
        " Cùng người triển khai, cách hạch toán khác; không phải reviewer/model độc lập.",
        "- Oracle chạy từ2022xuyên2026 xác nhận state nối checkpoint, admissions/rejects,",
        " phí/swap, phase/reward, DD và từng dynamicfill theo đúng nguồn tick/kịch bản.",
        "- Giữ attempt lỗi: timestamp pandas microsecond→millisecond; fixed-risk book",
        " chưa reject lot dưới tối thiểu; và post-gap exposure giữ quá hạn. Chỉ sửa parser/",
        " measurement boundary, không đổi candidate đã freeze. Outputs attempt1 không",
        " dùng nghiệm thu; không chạy lại historical batch vốn đã khớp.",
        "- FTMO FAQ hiện tại fetch lỗiTLS. Đoạn protocol ghi 'checked15/11' chỉ là lần",
        " thử truy cập, **không phải xác minh thành công**.14ngày/80:20/zero admin delay",
        " tiếp tục là proxy đã đăng ký. News/session đích, margin và chi tiền chưa xác minh.",
        "- Không broker execution, challenge purchase, nguồn trả phí, Astra hoặc subagent.",
        " VI Dubber WIP và Trader pin giữ nguyên. Toàn bộ252oracle không chứng minh giá",
        " Gold giả định đúng với sàn hoặc đã khép được endpoint bị thiếu.", "",
        "## Quyết định", "",
        "**NOT_QUALIFIED; không mua Challenge từ báo cáo này.** Đã chứng minh cơ chế Funded",
        "có thể tạo payout trong mô hình lịch sử, nhưng số tiền thấp và không đều; holdout",
        "EUR không giữ được lợi thế, Gold còn thiếu nguồn. Ưu tiên đóng gap dữ liệu/đặc tả",
        "thực thi bằng một scope mới trước mọi promote. Nếu đổi portfolio, đó là trial mới",
        "và cần dữ liệu prospective mới;2025–2026 này không còn là holdout chưa nhìn.", "",
        f"Full JSON: `{OUT.with_suffix('.json').name}`. Private job:`{JOB}`.",
        "Các sổ/ledger đầy đủ, logs và failedattempts ở privatejob; JSON public giữ kết quả",
        "từng mốc, payout ledger, source hashes, censor witnesses và receipts để đối soát.",
    ]
    OUT.with_suffix(".md").write_text(readable_spacing("\n".join(lines) + "\n"), encoding="utf-8")
    event("V6_report_built", status="NOT_QUALIFIED", oracle_accounts=252)


if __name__ == "__main__":
    build()
