"""Join frozen V2 evidence into the owner report without reading prices."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prop_atlas_core import JOB, V1, PARENT
from prop_campaign_exits import funding_rate
from prop_campaign_report import aggregate, compact, date_text
from prop_campaign_source import digest, read, write_json
from xau_h1_stage0_scan import funding_events


OUT = Path("planning/research/PROP-ATLAS-V2-RESULTS-20261114")
DECISION = OUT.with_name("PROP-ATLAS-V2-DECISION-20261114.json")
MODELS = ("SYM_FLAT", "ASYM_FLAT")
ASSETS = ("XAUUSD", "EURUSD", "US500", "GBPUSD", "AUDUSD")


def reserve_diagnostic(cases):
    """Check whether a causal funding reserve would change any admission."""
    rows = []
    for model, accounts in cases.items():
        trades = read(JOB / f"system-{model}-trades.json")
        checked = changed = would_reject = 0
        lowest = None
        for case in accounts:
            prior = []
            for admission in case["accepted"]:
                trade = trades[admission["trade"]]
                entry_key = (trade["entry_msc"], trade["entry_quote_index"])
                prior = [
                    a for a in prior
                    if (trades[a["trade"]]["exit_msc"],
                        trades[a["trade"]]["exit_quote_index"]) > entry_key
                ]
                correction = 0
                for position in prior + [admission]:
                    old = trades[position["trade"]]
                    realized = sum(
                        e["multiplier"]
                        for e in funding_events(old["entry_msc"], old["exit_msc"])
                    )
                    deadline = sum(
                        e["multiplier"]
                        for e in funding_events(old["entry_msc"], old["deadline_msc"])
                    )
                    if deadline < realized:
                        raise ValueError("exit_after_registered_deadline")
                    correction += int(round(
                        min(0, funding_rate(old["side"], model))
                        * position["ounces"] * 1000 * (deadline - realized)
                    ))
                projected = (
                    admission["risk_state"]["projected_stop_milli_usd"] + correction
                )
                checked += 1
                changed += bool(correction)
                would_reject += projected <= 46500000
                lowest = projected if lowest is None else min(lowest, projected)
                prior.append(admission)
        rows.append(dict(
            model=model, entries_checked=checked,
            reserve_projection_changed=changed,
            conservative_deadline_would_reject=would_reject,
            minimum_projected_stop_equity_usd=lowest / 1000,
        ))
    result = dict(
        status="PASS_NO_OBSERVED_ADMISSION_CHANGE",
        scope="Post-run diagnostic; no strategy, policy or accounting rerun.",
        finding=(
            "Inherited reserve uses realized exit time for remaining funding, "
            "instead of the known pretrade deadline. It is not a causal live reserve."
        ),
        correction=(
            "Reprice every active position through its registered deadline, "
            "without relying on its future stop exit."
        ),
        rows=rows,
        action_equivalence=all(
            r["conservative_deadline_would_reject"] == 0 for r in rows
        ),
        source="Accepted ledgers and frozen deadlines only; no new prices.",
        implementation_sha256=digest(
            "tooling/ai-engines/prop_campaign_accounts.py"
        ),
    )
    if not result["action_equivalence"]:
        raise ValueError("causal_reserve_changes_admission_requires_replay")
    write_json(JOB / "reserve-horizon-diagnostic.json", result)
    return result


def build():
    diagnostic = read(JOB / "phase0-diagnostic.json")
    core = read(JOB / "core-comparison.json")
    freeze = read(JOB / "composition-freeze.json")
    release = read(JOB / "validation-release.json")
    atlas = read(JOB / "atlas-stage0.json")
    uncertainty = read(JOB / "atlas-uncertainty.json")
    old = read(PARENT / "attempt-2/result.json")
    annual = {m: read(JOB / f"annual-{m}.json") for m in MODELS}
    cases = {m: read(JOB / f"lifecycle-{m}.json") for m in MODELS}
    parity = {
        name: read(JOB / name) for name in (
            "phase0-parity.json", "core-parity.json",
            "atlas-parity.json", "lifecycle-parity.json",
        )
    }
    tests = read(JOB / "regression-tests.json")
    if not tests["passed"] or any(p["status"] != "PASS" for p in parity.values()):
        raise ValueError("report_requires_all_regression_and_numerical_checks")
    if (release["composition_sha256"] != digest(JOB / "composition-freeze.json")
            or datetime.fromisoformat(freeze["utc"])
            >= datetime.fromisoformat(release["utc"])):
        raise ValueError("composition_release_order_or_hash")
    for key, path in (
        ("atlas_sha256", JOB / "atlas-stage0.json"),
        ("core_decision_sha256", JOB / "core-decision.json"),
        ("source_resolution_sha256", JOB / "resolved-endpoint-review.json"),
        ("policy_sha256", Path("tooling/ai-engines/prop_atlas_policy.py")),
        ("protocol_sha256", Path(
            "planning/research/PROP-ATLAS-V2-PROTOCOL-20261114.md")),
    ):
        if freeze[key] != digest(path):
            raise ValueError("frozen_input_changed:" + key)
    if freeze["core"] != "A0" or freeze["sleeves"] or atlas["survivors"]:
        raise ValueError("report_assumes_observed_A0_without_sleeves")

    reserve = reserve_diagnostic(cases)
    # Publish the original bytes, retaining the true private freeze timestamp.
    # Publication after replay does not establish a pre-replay Git commit.
    DECISION.write_bytes((JOB / "composition-freeze.json").read_bytes())
    comparisons = []
    for model in MODELS:
        for risk in (150, 200):
            rows = [
                c for c in old["rolling"]
                if c["cell"] == model and c["risk_usd"] == risk
            ]
            comparisons.append(dict(
                version="PR78", policy=f"{risk / 500:.2f}% fixed", model=model,
                **aggregate(rows, True),
            ))
        comparisons.append(dict(
            version="PR79", policy=".50 -> .35 -> .25%", model=model,
            **aggregate(read(V1 / f"lifecycle-{model}.json")),
        ))
        comparisons.append(dict(
            version="V2", policy=".40 -> .40 -> .25%; throttle .30/.18",
            model=model, **aggregate(cases[model]),
        ))

    summary = []
    census = read(JOB / "atlas-census.json")
    for asset in ASSETS:
        cells = [c for c in atlas["cells"] if c["cell"]["asset"] == asset]
        incomplete = sum(
            any("DATA_ENDPOINT_INCOMPLETE" in a["reasons"] for a in c["annual"])
            for c in cells
        )
        summary.append(dict(
            asset=asset, cells=len(cells),
            stage0_pass=sum(c["stage0_pass"] for c in cells),
            endpoint_complete=len(cells) - incomplete,
            endpoint_incomplete=incomplete,
            net_positive_both_years_asym=sum(
                all(a["net_mean"]["ASYM_FLAT"] is not None
                    and a["net_mean"]["ASYM_FLAT"] > 0 for a in c["annual"])
                for c in cells
            ),
            raw_signal_views=census["counts"][asset],
        ))
    if (sum(s["endpoint_complete"] for s in summary) != 84
            or sum(s["endpoint_incomplete"] for s in summary) != 28):
        raise ValueError("source_coverage_totals_changed")
    reset_quality = {}
    for model, accounts in cases.items():
        resets = {
            (r["at"], r["age_ms"])
            for c in accounts for r in c["stale_midnight_marks"]
        }
        reset_quality[model] = dict(
            unique_open_position_reset_marks=len(resets),
            maximum_quote_age_ms=max((age for _, age in resets), default=0),
        )
    result = dict(
        schema="PROP-ATLAS-V2-v1", decision="NOT_CHALLENGE_READY",
        date="2026-11-14", report_created_utc=datetime.now(timezone.utc).isoformat(),
        preregistration_commit="6fcd3f3",
        pre_stage0_implementation="b3f64ea",
        pre_phase3_implementation="054d371", merged_pr79="a42fb9f",
        phase0=diagnostic,
        core={
            key: dict(unknown=value["unknown"],
                      annual=[compact(row) for row in value["annual"]])
            for key, value in core.items()
        },
        composition=freeze,
        validation_release=release,
        decision_publication=dict(
            file=DECISION.as_posix(), same_bytes_as_private_freeze=True,
            sha256=digest(DECISION), first_tracked_publication="after_phase3",
        ),
        protocol_deviations=[
            "Protocol/code were committed before Phase 3; composition JSON "
            "was privately frozen before release but not committed until reporting. "
            "This falls short of the protocol's committed-decision requirement."
        ],
        atlas=atlas, atlas_summary=summary, atlas_uncertainty=uncertainty,
        reserve_horizon_diagnostic=reserve, reset_quote_quality=reset_quality,
        annual={
            model: dict(source=book["source"],
                        rows=[compact(row) for row in book["rows"]])
            for model, book in annual.items()
        },
        comparisons=comparisons,
        lifecycle={m: [compact(c) for c in cs] for m, cs in cases.items()},
        continuous={m: compact(cs[0]) for m, cs in cases.items()},
        continuous_is_same_as_first_monthly_case=True,
        parity={
            name: {k: v for k, v in p.items()
                   if k != "records" and not (k == "accounts" and isinstance(v, list))}
            for name, p in parity.items()
        },
        regression=tests, source_inventory=read(JOB / "source-inventory.json"),
        execution_endpoint_resolution=dict(
            hours=len(read(JOB / "resolved-endpoint-review.json")["hours"]),
            purpose="Exact missing roles; no new alpha trial.",
        ),
        private_job=str(JOB), prices2025_2026_read=False,
        prop_qualified=False, broker_calls=0,
        artifacts=[
            dict(name=p.name, sha256=digest(p)) for p in sorted(JOB.glob("*.json"))
            if not p.name.startswith("failure")
        ],
        code=[
            dict(name=p.name, sha256=digest(p))
            for p in sorted(Path("tooling/ai-engines").glob("prop_atlas*.py"))
        ],
        review_scope=(
            "Same implementer; alternate computational oracle. "
            "Not independent human/model approval; no Astra review."
        ),
    )
    write_json(OUT.with_suffix(".json"), result)
    lines = [
        "# V2 — chẩn đoán năm 2024, quét Atlas và giảm rủi ro tài khoản",
        "",
        "**Đã hoàn tất chiến dịch; chưa đủ cơ sở để mua Challenge.** "
        "Năm 2024 yếu vì SELL mất phần lớn lợi nhuận BUY. Hai cách giảm carry không "
        "vượt đủ cổng lựa chọn. Trong 112 cấu hình Atlas, không có nhánh bổ sung "
        "đủ điều kiện. Hệ thống cuối giữ A gốc; risk thấp hơn giúp giảm lỗ dưới "
        "vốn đầu, đồng thời làm chậm tiến độ thi quỹ.",
        "",
        "Đây là kết quả kiểm định offline, không phải cam kết lợi nhuận hoặc quyền "
        "giao dịch. `prop_qualified=false`; chưa có trường hợp hoàn tất hai vòng "
        "hay nhận payout trong mô phỏng.",
        "",
        "Owner task `a2f3990c-8de8-4680-b5e0-87b2dc438462`, ngày 14/11/2026. "
        "PR #79 đã merge tại `a42fb9f`; nhánh cũ đã xóa. "
        "Giữ nguyên WIP VI Dubber; không gọi broker, model hoặc nhà cung cấp trả phí. "
        "Không giải mã giá năm 2025–2026.",
        "",
        "## 1. So sánh PR #78 → PR #79 → V2",
        "",
        "Mỗi hàng dùng 36 mốc bắt đầu tháng, từ tháng 1/2022 đến tháng 12/2024, "
        "kết thúc trước 01/01/2025. Các cửa sổ chồng lấn và có thời gian theo dõi "
        "khác nhau; số cửa sổ qua vòng không phải xác suất pass trong tương lai.",
        "",
        "| Phiên bản / risk | Phí | Qua vòng 1 | Qua cả hai | Trung vị vòng 1* | Lỗ ngày lớn nhất | Lỗ dưới vốn đầu | Sụt từ đỉnh | Vi phạm | Payout / USD trader |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in comparisons:
        duration = row["step1_median_months_completed_only"]
        duration_text = "N/A" if duration is None else f"{duration:.2f} tháng"
        name = row["version"]
        if name == "PR78":
            name += " / " + row["policy"]
        lines.append(
            f"| {name} | {row['model'].split('_')[0]} | {row['step1']}/36 "
            f"| {row['both']}/36 | {duration_text} "
            f"| {row['worst_daily_pct']:.3f}% | {row['worst_static_pct']:.3f}% "
            f"| {row['worst_peak_dd_pct']:.3f}% | {row['breaches']} "
            f"| {row['payouts']} / ${row['trader_payout_usd']:.2f} |"
        )
    lines += [
        "",
        "SYM = swap Gold −40/−40; ASYM = proxy −45/−5 USD/lot/rollover. "
        "*Trung vị chỉ tính các cửa sổ đã qua vòng 1. Chưa có trung vị hoàn tất "
        "hai vòng vì chưa cửa sổ nào đạt. Một tài khoản liên tục từ 01/01/2022 "
        "chính là cửa sổ tháng đầu tiên, không phải quan sát độc lập thứ 37.",
        "",
        "**Đánh đổi chính:** mức lỗ dưới vốn đầu lớn nhất giảm từ 9,321% xuống "
        "6,157% ở SYM, từ 8,899% xuống 6,083% ở ASYM. "
        "Số cửa sổ qua vòng 1 giảm từ 8 xuống 2 ở SYM, từ 13 xuống 5 ở ASYM. "
        "Giảm risk không tạo thêm lợi thế tín hiệu. Sụt giảm từ đỉnh vẫn có thể "
        "lớn hơn 7%; đó là thước đo khác với lỗ dưới vốn đầu.",
        "",
        "## 2. Vì sao 13 tài khoản cũ kẹt ở vòng 2?",
        "",
        "| Bắt đầu | Qua vòng 1 | Đỉnh equity vòng 2 | Đỉnh balance vòng 2 | Đỉnh khi đã đóng hết | Còn thiếu đến 5% từ đỉnh flat | Thiếu, R tham chiếu $175 | Balance cuối |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in diagnostic["accounts"]:
        lines.append(
            f"| {date_text(row['start_msc'])} | {date_text(row['step1_pass'])} "
            f"| {row['max_equity_profit_pct']:.3f}% "
            f"| {row['max_realized_profit_pct']:.3f}% "
            f"| {row['max_flat_profit_pct']:.3f}% "
            f"| {row['shortfall_from_best_flat_pct']:.3f} điểm % "
            f"| {row['shortfall_from_best_flat_reference175_R']:.3f}R "
            f"| ${row['terminal_balance_usd']:,.2f} |"
        )
    lines += [
        "",
        "**13/13 dừng vì hết dữ liệu (`TIME_CENSORED_AT_DATASET_END`); "
        "0/13 vi phạm drawdown.** Lãi equity cao nhất nằm trong khoảng "
        "+1,477% đến +4,034%; lãi cao nhất khi đã đóng hết vị thế là +0,767% "
        "đến +3,118%. Trường hợp gần nhất vẫn thiếu 1,882 điểm phần trăm, "
        "tức khoảng $941,18 hoặc 5,38R tham chiếu $175.",
        "",
        "Equity là balance cộng lãi/lỗ đang mở. Balance cao nhất có thể vẫn còn "
        "vị thế; chỉ mức khi đã đóng hết mới phù hợp điều kiện pass. "
        "Risk thực tế có lúc giảm về $125 nên $175 chỉ là đơn vị quy đổi. "
        "Hết dữ liệu chưa chứng minh chiến lược sẽ không bao giờ pass, cũng không "
        "chứng minh thêm vài tháng chắc chắn pass. Tập 2025–2026 tiếp tục đóng.",
        "",
        "## 3. Năm 2024: BUY kiếm tiền, SELL làm mất phần lớn",
        "",
        "Cùng risk danh nghĩa $150/lệnh, 1R = $150. Gross đã trừ spread, "
        "chưa trừ commission, slippage và swap.",
        "",
        "| Năm | Chiều | Lệnh | Gross R | Commission R | Slippage R | Swap R | Net nếu bỏ financing* | Net R trong mô hình |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in diagnostic["annual_side"]:
        lines.append(
            f"| {row['year']} | {row['side']} | {row['trades']} "
            f"| {row['gross_R']:+.3f} | {row['commission_R']:.3f} "
            f"| {row['slippage_R']:.3f} | {row['swap_R']:+.3f} "
            f"| {row['financing_free_net_R']:+.3f} | {row['net_R']:+.3f} |"
        )
    lines += [
        "",
        "*Bỏ financing chỉ để giải thích phần đóng góp chi phí, không phải "
        "kịch bản được dùng để lựa chọn. **BUY 2024 +14,689R; SELL −12,044R.** "
        "Swap BUY 2024 là −2,211R, còn nhỏ hơn −3,129R của năm 2023. "
        "Vì vậy, giả thuyết “BUY bị carry kéo hỏng năm 2024” không khớp bằng chứng. "
        "Không chuyển sang BUY-only dựa trên năm 2024 đã biết.",
        "",
        "Con số SELL 2022 khoảng +11,19R ở PR #77 là trước hiệu chỉnh lịch nghỉ. "
        "Baseline PR #78/#79 hiện dùng +6,934R; riêng đóng sớm ngày 04/07/2022 "
        "đã làm thay đổi khoảng 4,25R. Không trộn hai phiên bản lịch khi so sánh.",
        "",
        "## 4. Hai cách giảm carry: giữ A gốc",
        "",
        "CA1: BUY đóng lúc 20:30 UTC cùng ngày; SELL giữ quy tắc cũ. "
        "CA2: BUY đóng lúc 20:30 UTC thứ Tư nếu lãi ròng thanh lý chưa đạt 1,5R. "
        "Cả hai giữ nguyên tín hiệu vào và SL, chỉ thử trên Development 2022–2023.",
        "",
        "| Cấu hình | Phí | Net R 2022 / 2023 | Equity DD (R) 2022 / 2023 | Quyết định |",
        "|---|---|---:|---:|---|",
    ]
    baseline = read(V1 / "phase1-metrics.json")
    for policy in ("A0", "CA1", "CA2"):
        for model in MODELS:
            rows = (
                baseline[model + ":A0"]["annual"] if policy == "A0"
                else core[model + ":" + policy]["annual"]
            )
            a, b = rows
            verdict = "Giữ baseline" if policy == freeze["core"] else "Không đạt đủ cổng"
            lines.append(
                f"| {policy} | {model.split('_')[0]} "
                f"| {a['net_R']:+.3f} / {b['net_R']:+.3f} "
                f"| {a['max_equity_R_DD']:.3f} / {b['max_equity_R_DD']:.3f} "
                f"| {verdict} |"
            )
    lines += [
        "",
        "CA1 xóa được swap BUY bằng cách đóng lệnh thật, nhưng cũng mất phần "
        "giá đi tiếp sau 20:30. Net BUY giảm còn khoảng −2,06R / −6,97R ở "
        "2022/2023, kém A gốc. CA2 cải thiện tỷ lệ lợi nhuận/drawdown, nhưng "
        "Net R năm 2023 thấp hơn A gốc trong cả hai mô hình phí. "
        "CA2 có đánh đổi hữu ích, song không đạt yêu cầu đã khóa: cả Net R "
        "và Net R/DD phải tăng ở từng năm, từng mô hình. Không đổi cổng sau kết quả.",
        "",
        "Đây là hai lượt thử mới được phê duyệt trong V2, không phải hồi tố sửa "
        "kết quả E3 của V1. Mốc quyết định cần quote trong 60 giây; thiếu thì "
        "ghi unknown, không lấy nến giờ tiếp theo làm giá khớp.",
        "",
        "## 5. Atlas: 112 cấu hình, không có sleeve đủ điều kiện",
        "",
        "Danh mục đã đăng ký: 5 tài sản × 12 cấu hình quét rồi quay lại vùng "
        "(sweep) = 60; 4 tài sản ngoài Gold × 12 cấu hình phá vùng đi tiếp = 48; "
        "Gold có thêm 4 cấu hình BUY momentum. Tổng 112 cấu hình. "
        "Mỗi nhóm vùng dùng phiên Á 00:00–06:00 UTC hoặc ngày giao dịch trước; "
        "cửa sổ London 08:00–11:00 / New York 13:00–16:00 UTC; "
        "giữ đến 20:30 cùng ngày, +24h hoặc +48h có chặn lịch. "
        "Không thêm công thức sau khi thấy kết quả.",
        "",
        "| Tài sản | Cấu hình | Lượt tín hiệu thô (1) | ASYM dương cả hai năm (2) | Đủ endpoint | Thiếu endpoint | Qua Stage-0 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['asset']} | {row['cells']} | {row['raw_signal_views']} "
            f"| {row['net_positive_both_years_asym']} | {row['endpoint_complete']} "
            f"| {row['endpoint_incomplete']} | {row['stage0_pass']} |"
        )
    lines += [
        "",
        "**84 cấu hình có đủ endpoint nhưng không vượt toàn bộ cổng; "
        "28 cấu hình còn thiếu endpoint nên chưa kết luận được toàn mẫu.** "
        "Không gọi cả 112 cấu hình là thua lỗ kinh tế. "
        "(1) 14.947 lượt có trùng tín hiệu giữa các thời gian giữ, không phải "
        "14.947 lệnh độc lập. (2) Mean dương trên phần có giá chỉ là chẩn đoán "
        "nếu còn missing. Đủ endpoint cũng chưa chứng minh đủ đường SL.",
        "",
        "USDJPY chưa có nguồn H1/M1 liên tục đủ năm được chấp nhận, chỉ có "
        "một số ngày Tokyo fixing. Vì vậy USDJPY bị chặn ở mức sẵn sàng dữ liệu, "
        "không phải một ứng viên đã đo và thua.",
        "",
        "Cổng Stage-0 yêu cầu từng năm có ít nhất 40 tín hiệu, đủ giá/SL hợp lệ, "
        "ma sát trung vị/SL trung vị ≤15%, ít nhất 60% tín hiệu tự nhiên đạt "
        "ma sát/SL ≤15%; mean markout ròng phải dương và không nhỏ hơn mean "
        "ma sát thực thi trong cả hai mô hình phí. Chỉ ứng viên qua Stage-0 "
        "mới chạy Natural SL, kiểm tra ≥6R/năm và tương quan lãi/lỗ ngày <0,30 "
        "với A_Core. Không có ứng viên qua Stage-0 nên **Stage-1 và correlation "
        "là N/A**, không phải correlation bằng 0.",
        "",
        "Các trường hợp đáng chú ý, chỉ để giải thích kết quả:",
        "",
        "- Gold sweep vùng ngày trước, phiên London, giữ 48h: mean ASYM "
        "+3,861 / +4,181 USD/oz, nhưng chỉ 45,1% / 39,3% tín hiệu đạt cổng "
        "ma sát/SL. Không được nới SL hoặc lọc mất phần lớn tín hiệu để cứu.",
        "- Gold BUY momentum phiên New York có mean dương cả hai năm, nhưng "
        "chỉ 20–32 tín hiệu/năm với impulse và 29–32 với two-bar. Một số năm "
        "mean ròng còn nhỏ hơn ma sát. Chưa đủ số mẫu và tần suất đã yêu cầu.",
        "- EURUSD không cấu hình nào dương cả hai năm trong mô hình hiện tại. "
        "GBPUSD và AUDUSD mỗi tài sản có một cấu hình mean dương cả hai năm, "
        "nhưng biên độ chưa vượt đủ cổng sau phí.",
        "",
        "### Nguồn dữ liệu và phí",
        "",
        "Gold dùng spread quan sát được, commission 0,0007% notional/side, "
        "slippage 0,20 USD/oz/side; swap SYM −40/−40 hoặc ASYM −45/−5 "
        "USD/lot/rollover, mốc 22:00 UTC và thứ Tư ×3. "
        "FX giữ commission + slippage $5 + $4/lot mỗi vòng và swap bảo thủ "
        "−$40/lot/rollover hai chiều; đây là proxy, chưa xác minh swap FTMO thực tế. "
        "US500 giữ commission legacy $1/lot/vòng, slippage 0,75 point/side, "
        "funding $2/lot/ngày lịch; thiếu mô hình cổ tức đích nên cấu hình "
        "qua đêm không được chọn.",
        "",
        "Đã rà 693 giờ endpoint Gold, gồm 128 giờ tái dùng và 565 giờ bổ sung; "
        "sửa một bản M1 làm việc trước khi tính PnL, giữ nguyên bản gốc. "
        "Chặn việc dùng ngày chỉ có 12 nến H1 làm D1 hoàn chỉnh: loại 4 lượt "
        "tín hiệu trước Stage-0, không đổi 112 công thức.",
        "",
        "Lần chạy nguồn đầu được giữ tại `component-attempt-1/`. Sau đó bổ sung "
        "đúng 1.105 giờ endpoint còn thiếu: US500 224, GBPUSD 451, AUDUSD 430. "
        "Không đổi tín hiệu, phí hoặc thời gian giữ. Vẫn còn 28 cấu hình thiếu "
        "endpoint; không điền giá, loại mẫu hoặc tiếp tục tải để ép vượt cổng. "
        "H1/M1 proxy không đồng nghĩa tick khớp lệnh thực; bổ sung tick endpoint "
        "không biến toàn bộ đường giá thành tick đã kiểm chứng.",
        "",
        "### Độ bất định khi thử nhiều cấu hình",
        "",
        "JSON công khai giữ toàn bộ khoảng bootstrap: 50.000 lần lấy mẫu theo "
        "khối 5 ngày có tín hiệu, khoảng 95% thông thường và khoảng hiệu chỉnh "
        "Bonferroni trên 112 cấu hình cho từng năm/mô hình phí. Đây là chẩn đoán "
        "độ bất định; không phải bảo đảm ý nghĩa thống kê cho mọi cách nhìn. "
        "Thiếu endpoint thì không xuất khoảng tin cậy toàn mẫu.",
        "",
        "| Cấu hình Gold (ASYM) | Năm | Mean USD/oz | Khoảng bootstrap 95% | Khoảng Bonferroni 112* |",
        "|---|---:|---:|---:|---:|",
    ]
    examples = {
        "XAUUSD.SWEEP.PREVDAY.LONDON.48H",
        "XAUUSD.IMPULSE.D1H4.NY.DAY",
        "XAUUSD.TWOBAR.D1H4.NY.DAY",
    }
    for row in uncertainty["rows"]:
        if row["cell"] not in examples or row["model"] != "ASYM_FLAT":
            continue
        ordinary = row["ordinary95"]
        adjusted = row["bonferroni112_95_per_year_model"]
        lines.append(
            f"| {row['cell']} | {row['year']} | {row['mean']:+.3f} "
            f"| [{ordinary[0]:+.3f}; {ordinary[1]:+.3f}] "
            f"| [{adjusted[0]:+.3f}; {adjusted[1]:+.3f}] |"
        )
    lines += [
        "",
        "*Khoảng hiệu chỉnh chỉ áp dụng trong từng năm/mô hình; không là một "
        "bảo đảm toàn cục cho cả 448 cách nhìn. Bảng minh họa sau khi đo không "
        "được dùng để chọn lại sleeve.",
        "",
        "## 6. Risk Policy v2: an toàn hơn, chậm hơn",
        "",
        "Vòng 1 và 2 dùng 0,40% ($200/lệnh trên sổ $50.000); funded dùng 0,25%. "
        "Khi equity xuống dưới $48.750, risk lệnh mới tối đa 0,30%; dưới $47.750 "
        "tối đa 0,18%. Từ vốn đầu đến −2,5% vẫn giữ risk theo phase. "
        "Funded không tự tăng từ 0,25% lên 0,30%. Giữ giới hạn 0,25% sau khi "
        "lỗ đã thực hiện trong ngày vượt 1,8%, reset theo Prague. "
        "Risk phục hồi khi equity phục hồi; không thay size vị thế đang mở.",
        "",
        "Cổng dự trữ nội bộ từ chối toàn bộ lệnh mới nếu SL và chi phí dự kiến "
        "của các vị thế có thể làm equity chạm $46.500 (−7%). "
        "**Cổng này từ chối 0 lệnh trong lần chạy**, nên không được gán mức "
        "giảm drawdown quan sát được cho nó. Khác biệt kết quả đến từ risk theo "
        "phase thấp hơn và bậc giảm risk; chưa tách đóng góp riêng của từng phần "
        "bằng thử nghiệm ablation.",
        "",
        "| Phí | Tổng lượt vào trên 36 cửa sổ* | Bị chặn bởi cổng 7% | Số lượt risk $200 / $150 / $125 / $90 |",
        "|---|---:|---:|---|",
    ]
    for model, accounts in cases.items():
        buckets = Counter()
        for account in accounts:
            buckets.update(account["risk_buckets"])
        lines.append(
            f"| {model.split('_')[0]} | {sum(c['entries'] for c in accounts)} "
            f"| {sum(c['rejections'].get('INTERNAL_STATIC_7PCT_RESERVE', 0) for c in accounts)} "
            + "| " + " / ".join(str(buckets[str(k)]) for k in (200, 150, 125, 90)) + " |"
        )
    lines += [
        "",
        "*Là lượt vào của các tài khoản mô phỏng chồng lấn, không phải số lệnh "
        "thị trường độc lập. Risk 0,18% không bảo đảm không cháy: phí, gap, "
        "nhiều vị thế và thay đổi risk khiến số R còn chịu được không cố định.",
        "",
        "**Điểm cần sửa trước khi dùng cổng dự trữ ngoài nghiên cứu:** helper "
        "kế thừa đang dự trữ funding đến thời điểm thoát thực tế đã biết, thay "
        "vì hạn giữ lệnh đã biết lúc vào. Đây là lỗi tính nhân quả của cổng, "
        "không phải bằng chứng cổng đã sẵn sàng vận hành. Đã đối chiếu lại toàn "
        "bộ 11.334 lượt vào bằng hạn giữ lệnh khóa trước, gồm mọi vị thế đang mở: "
        "2.109 phép dự trữ mỗi mô hình thay đổi, nhưng vẫn 0 lệnh bị chặn. "
        "Equity dự trữ thấp nhất còn $46.766,78 / $46.809,90, trên $46.500. "
        "Vì vậy lỗi này không làm đổi đường lệnh/kết quả quan sát. Không sửa "
        "chính sách đã khóa hoặc tuyên bố helper hiện tại là pretrade causal.",
        "",
        "### Tài khoản liên tục từ 01/01/2022",
        "",
        "| Phí | Phase cuối | Balance cuối phase | Lượt vào | Lỗ ngày lớn nhất | Lỗ dưới vốn đầu |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, accounts in cases.items():
        row = accounts[0]
        lines.append(
            f"| {model.split('_')[0]} | {row['phase']} | ${row['balance_usd']:,.2f} "
            f"| {row['entries']} | {row['worst_daily_loss_pct']:.3f}% "
            f"| {row['static_loss_pct']:.3f}% |"
        )
    lines += [
        "",
        "Balance là số dư của phase đang chạy; khi qua vòng thi, sổ phase mới "
        "bắt đầu lại $50.000. Lợi nhuận vòng thi không phải tiền payout.",
        "",
        "Reward proxy giữ quy tắc 30 ngày, đã đóng hết vị thế và lãi đóng ≥$20; "
        "trừ 100% lợi nhuận khỏi account, chia trader 80% / firm 20%. "
        "Không bơm tiền, tự retry hoặc xóa lỗ bằng reset. Trong dữ liệu chưa có "
        "funded case, nên phần funded/reward chỉ được kiểm bằng fixtures. "
        "Chưa tính phí mua/retry Challenge và chi phí vận hành; không có payout thật.",
        "",
        "## 7. Kinh tế A gốc không thay đổi",
        "",
        "| Năm | Phí | Lệnh | Net R ở risk $150, trước = sau | Mean Net R/lệnh | Net R nếu bỏ top 3 lệnh |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for model, obj in annual.items():
        for row in obj["rows"]:
            lines.append(
                f"| {row['year']} | {model.split('_')[0]} | {row['entries']} "
                f"| {row['net_R']:+.3f} | {row['mean_net_R']:+.4f} "
                f"| {row['net_ex_top3_R']:+.3f} |"
            )
    lines += [
        "",
        "A_Core vẫn là A0 và chưa có sleeve, nên các sổ chiến lược risk cố định "
        "được tái dùng nguyên trạng từ PR #79. V2 chạy mới phần vòng đời với risk "
        "thay đổi trên tick; không gán việc thay size thành cải thiện alpha. "
        "Khi risk thay đổi, dùng USD/% tài khoản để so mục tiêu quỹ; tổng R là "
        "tổng net/risk đã cấp của từng lệnh.",
        "",
        "## 8. Kiểm chứng, quy trình và giới hạn",
        "",
        f"- {tests['tests']} tests hồi quy đạt, gồm 16 fixtures V2 về carry, "
        "thời điểm nến hoàn tất, ngân sách 112 cấu hình, bậc risk, reserve, "
        "lưới giá FX, bootstrap và kiểm tra tác động reserve theo deadline.",
        "- Phase 0: 13 tài khoản vòng 2 và 6 sổ theo chiều khớp phép tính đối chiếu.",
        f"- Carry: {parity['core-parity.json']['shortened_paths']} đường lệnh, "
        f"{parity['core-parity.json']['cost_bridges']} phép đối chiếu chi phí "
        "ở risk $90 / $125 / $150 / $200.",
        f"- Atlas: 112 cấu hình và {parity['atlas-parity.json']['unit_cost_bridges']} "
        "phép đối chiếu chi phí theo đơn vị khớp phép tính phân số chính xác.",
        f"- Vòng đời: {parity['lifecycle-parity.json']['accounts']} tài khoản "
        "khớp cash, equity, daily loss, drawdown và phase reset bằng một cách "
        "hạch toán khác: ghi funding vào cash thay vì giữ trong floating. "
        "Có đối chiếu ledger tại từng entry/exit; không reset theo năm mới.",
        "- Cùng một implementer, dùng công thức tính khác. Đây là đối soát "
        "số học, không phải review độc lập bởi người/model khác. Không gửi Astra.",
        "- Lỗi thiếu import ở bước freeze nguồn đã dừng trước PnL; không dùng "
        "output dang dở làm kết quả tài chính. Các lần nguồn thiếu và bản gốc "
        "được giữ; không lấp missing bằng giá tương lai.",
        "",
        "### Thời điểm khóa quyết định",
        "",
        "Protocol commit `6fcd3f3`, code trước Stage-0 `b3f64ea`, code trước "
        "replay Phase 3 `054d371`. Quyết định giữ A0/không sleeve và hash "
        "risk đã khóa trong private receipt trước khi chạy Phase 3:",
        "",
        f"- Freeze: `{freeze['utc']}`.",
        f"- Release Phase 3: `{release['utc']}`.",
        f"- Bản công khai nguyên byte: [{DECISION.name}]({DECISION.name}).",
        "",
        "**Sai lệch quy trình:** protocol yêu cầu commit decision JSON trước "
        "Phase 3; thực tế JSON chỉ được khóa ở private receipt trước replay "
        "và được commit khi xuất báo cáo. Protocol/code đã commit trước, "
        "nhưng điều đó không thay thế yêu cầu commit quyết định. "
        "Không backdate, không sửa lại protocol và không coi receipt riêng "
        "là bằng chứng quyết định đã nằm trên Git từ trước. Không có lựa chọn "
        "lại core/sleeve/risk sau kết quả Phase 3.",
        "",
        "Năm 2024 đã được xem ở các chiến dịch trước và Phase 0, chỉ gọi là "
        "Historical Validation. Reader Phase 1/2 chặn năm 2024; năm 2025–2026 "
        "không được mở. Không có clean OOS mới trong chiến dịch này.",
        "",
        "Có 222 mốc reset Prague riêng biệt khi đang có vị thế; phép đo dùng "
        "quote gần nhất, tuổi quote tối đa khoảng 60,42 phút. Các mốc/tuổi "
        "quote còn nguyên trong ledger riêng; không coi chúng là fresh quote "
        "hoặc lấy kết quả daily loss làm chứng nhận thực thi trên feed FTMO.",
        "",
        "Các phần chưa xác minh đủ để vận hành: swap/spec/margin/leverage đích, "
        "lịch tin hạn chế lịch sử, calendar/feed và khớp lệnh của tài khoản đích, "
        "cổng reserve causal, forward chưa thấy và bàn giao vận hành. "
        "CI hoặc dữ liệu nguồn đạt không đồng nghĩa chiến lược đủ điều kiện giao dịch.",
        "",
        f"Private job: `{JOB}`. Protocol, source admission, các lần freeze, "
        "JSON theo cấu hình, bootstrap, bốn bảng parity và 72 ledger giữ đủ "
        "định vị/hash. Báo cáo JSON kèm theo công khai toàn bộ 112 kết quả và "
        "448 hàng độ bất định; không upload raw tick/cache.",
        "",
        "**Quyết định:** giữ A0 làm benchmark nghiên cứu; chưa dùng cấu hình "
        "này để mua Challenge hoặc dựa vào thu nhập chính. Nhánh bổ sung "
        "chưa vượt cổng nên chưa có portfolio mới. Nghiên cứu tiếp cần giả thuyết "
        "kinh tế mới hoặc giải quyết bất định phí/nguồn có thể làm đổi quyết định. "
        "Không mở thêm giờ, nới SL hay tăng risk chỉ để sửa kết quả của 112 cấu hình.",
        "",
        "## Phụ lục — toàn bộ 112 cấu hình",
        "",
        "Cột nguyên nhân giữ nguyên mã máy để đối chiếu JSON. "
        "`CADENCE_LT40`: ít tín hiệu; `DATA_ENDPOINT_INCOMPLETE`: thiếu giá; "
        "`MEDIAN_SCALE_GT15` / `SCALE_RETENTION_LT60`: không hợp quy mô phí/SL; "
        "`NET_NONPOSITIVE_*`: có năm mean không dương; `NET_LT_FRICTION_*`: "
        "mean dương nhưng chưa lớn hơn ma sát; `DIVIDEND_CARRY_TARGET_UNVERIFIED`: "
        "chưa xác minh carry/cổ tức của sản phẩm đích. Các nguyên nhân có thể trùng.",
        "",
        "| Cấu hình | Tín hiệu 2022/23 | Có giá 2022/23 | Đạt phí/SL 15%, 2022/23 | Mean net ASYM 2022/23* | Nguyên nhân |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for cell in atlas["cells"]:
        a, b = cell["annual"]
        factor = 10000 if cell["cell"]["asset"] in (
            "EURUSD", "GBPUSD", "AUDUSD") else 1

        def value(number):
            return "N/A" if number is None else f"{number * factor:+.3f}"

        reasons = sorted(set(a["reasons"] + b["reasons"]))
        lines.append(
            f"| {cell['cell']['id']} | {a['raw']}/{b['raw']} "
            f"| {a['priced']}/{b['priced']} "
            f"| {a['pass15_fraction']:.1%}/{b['pass15_fraction']:.1%} "
            f"| {value(a['net_mean']['ASYM_FLAT'])}/{value(b['net_mean']['ASYM_FLAT'])} "
            f"| {', '.join(reasons) or 'STAGE0_PASS'} |"
        )
    lines += [
        "",
        "*Đơn vị: Gold USD/oz; FX pip; US500 index point. Mean trên nhóm "
        "có giá chưa đầy đủ không phải kết quả đủ điều kiện của toàn mẫu. "
        "JSON giữ cả kết quả âm, thiếu giá và các cổng không đạt.",
        "",
    ]
    OUT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(OUT.with_suffix(".md"), flush=True)


if __name__ == "__main__":
    build()
