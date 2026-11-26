"""Publish compact V9 summaries; full ledgers and storage maps stay private."""
from pathlib import Path
from statistics import median
import hashlib
import json
from prop_campaign_source import ROOT, read, write_json

JOB = ROOT / "system-and-alpha-v9-20261115"
OUT = Path("planning/research/SYSTEM-AND-ALPHA-V9-RESULTS-20261115")


def run():
    gold = read(JOB / "development-stage0.json")
    eur = read(JOB / "eurusd-stage0.json")
    before = [read(JOB / f"tests-before-{g}.json") for g in ("base", "native", "statistics", "worker")]
    after = [read(JOB / "tests-final-base-fast.json"), read(JOB / "tests-warm-base-historical.json")]
    after += [read(JOB / f"tests-warm-{g}-all.json") for g in ("native", "statistics", "worker")]
    old_ids = {t for r in before for t in r["timings"]}
    new_ids = {t for r in after for t in r["timings"]}
    if len(old_ids) != 995 or not old_ids <= new_ids or len(new_ids) != sum(r["tests"] for r in after):
        raise ValueError("test_ID_coverage_changed")
    if any(not r["passed"] or r["skipped"] for r in after):
        raise ValueError("test_matrix_not_passed")
    tests = dict(before=sum(r["tests"] for r in before), after=len(new_ids),
        original_IDs_retained=True, new_tests=len(new_ids - old_ids),
        before_seconds=sum(r["seconds"] for r in before),
        after_seconds=sum(r["seconds"] for r in after),
        fast_tests=after[0]["tests"], fast_seconds=after[0]["seconds"],
        historical_tests=sum(r["tests"] for r in after[1:]),
        warm_first_after_seconds=sum(read(p)["seconds"] for p in sorted(JOB.glob("tests-warm-*.json"))),
        cold_first_after_seconds=sum(read(p)["seconds"] for p in sorted(JOB.glob("tests-after-*.json"))),
        timings_are_single_runs=True)
    old_modules = {m: s for r in before for m, s in r["module_seconds"].items()}
    new_modules = {m: s for r in after for m, s in r["module_seconds"].items()}
    tests["top10_modules"] = [dict(module=m, before_seconds=s, after_seconds=new_modules[m])
                            for m, s in sorted(old_modules.items(), key=lambda r: -r[1])[:10]]
    regime_attribution = []
    for y in (2019, 2020, 2022, 2023):
        for regime in ("ASIA_EXPANSION", "ASIA_NORMAL_SWEEP"):
            values = [r["endpoints"]["DAY"]["costs"]["SYM_FLAT"]["net_per_oz"]
                      for r in gold["raw"] if r["id"] == "S2.DAY" and
                      r["day"].startswith(str(y)) and r["regime"] == regime]
            regime_attribution.append(dict(year=y, regime=regime, signals=len(values),
                mean_net_usd_oz=sum(values) / len(values) if values else None))
    d0, d1 = read(JOB / "storage-D-before-longpaths.json"), read(JOB / "storage-D-after.json")
    e0, e1 = read(JOB / "storage-E-before.json"), read(JOB / "storage-E-after.json")
    storage = dict(D_before=d0["groups"]["/"], D_after=d1["groups"]["/"],
        D_reduction={k: d0["groups"]["/"][k] - d1["groups"]["/"][k] for k in ("bytes", "files", "folders")},
        errors_before=d0["errors"], errors_after=d1["errors"],
        D_top_level={k: v for k, v in d0["groups"].items() if k != "/" and "/" not in k},
        D_top20_level2=dict(sorted(((k, v) for k, v in d0["groups"].items() if k != "/" and k.count("/") == 1),
                                  key=lambda r: -r[1]["files"])[:20]),
        E_initial_observed=e0["groups"]["/"], E_after_observed=e1["groups"]["/"],
        E_initial_errors=len(e0["errors"]), E_after_errors=len(e1["errors"]),
        E_top20_level2=dict(sorted(((k, v) for k, v in e1["groups"].items() if k != "/" and k.count("/") == 1),
                                  key=lambda r: -r[1]["bytes"])[:20]),
        backup_purged=False, logical_bytes_only=True,
        caches={k: v for k, v in read(JOB / "cache-purge.json").items() if k != "purged"},
        rust_incremental=read(JOB / "incremental-purge.json"),
        archives=[dict(path=p.name, bytes=p.stat().st_size,
                       files=len(read(p.with_suffix(p.suffix + ".MANIFEST.json"))["files"]))
                  for p in sorted(JOB.glob("old-clean-*.tar.gz"))])
    controls = []
    for rel in ("prop-gold-v8-20261115/calendar-corrected/backward/OPEN_LOW_HIGH_CLOSE/annual-economics.json",
                "prop-gold-v8-20261115/full/OPEN_LOW_HIGH_CLOSE/annual-economics.json"):
        rows = read(ROOT / rel)["BASELINE"]
        for y in sorted({r["year"] for r in rows}):
            selected = {r["model"]: r["budgets"]["150"] for r in rows if r["year"] == y}
            controls.append(dict(year=y, trades=selected["ASYM_FLAT"]["trades"],
                SYM_NetR=selected["SYM_FLAT"]["net_R"], ASYM_NetR=selected["ASYM_FLAT"]["net_R"],
                source=rel, V9_strategy=None, V9_status="NOT_RUN_FAILED_DEV"))
    artifacts = {}
    for name in ("development-stage0.json", "eurusd-stage0.json", "stage0-accounting-parity.json",
                 "eurusd-accounting-parity.json", "core-benchmark.json", "historical-seals.json",
                 "storage-D-before-longpaths.json", "storage-D-after.json", "storage-E-before.json",
                 "storage-E-after.json", "cache-purge.json", "backup-plan.json",
                 "research-registration.json", "eurusd-registration.json", "maintenance-cli-smoke.json"):
        p = JOB / name
        artifacts[name] = dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    output = dict(schema="SYSTEM-AND-ALPHA-V9-v1", status="NO_NEW_CHALLENGE_CANDIDATE",
        parent_merge="5f1b687", branch="codex/system-and-alpha-v9", storage=storage,
        tests=tests, benchmark=read(JOB / "core-benchmark.json"),
        gold=dict(annual=gold["summaries"], gates=gold["gates"], source=gold["source"],
                  S2_regime_attribution=regime_attribution),
        eurusd={k: v for k, v in eur.items() if k != "raw"}, annual_baseline_control=controls,
        audits=dict(gold=read(JOB / "stage0-accounting-parity.json"),
                    eur=read(JOB / "eurusd-accounting-parity.json"),
                    historical_seals=read(JOB / "historical-seals.json")),
        validation=dict(candidate_eligible=0, newly_decoded_2018_2021_validation=False,
                        newly_decoded_2024_2026_validation=False, portfolio=None,
                        nine_year_candidate_lifecycle="CANCELED_FAILED_STAGE0",
                        historical_labels="ALL_YEARS_PREVIOUSLY_EXPOSED",
                        cutoff="2026-10-13", independent_person_review=False),
        private_job=str(JOB), artifacts=artifacts)
    write_json(OUT.with_suffix(".json"), output)
    lines = [
        "# V9 — dọn storage, lõi dùng chung và kết quả tìm alpha",
        "",
        "**Kết quả: hạ tầng gọn hơn; chưa tìm được chiến lược mới đủ để thi Challenge.**",
        "PR87 đã merge `5f1b687`; nhánh `codex/system-and-alpha-v9`. PR V9 chờ owner duyệt.",
        "Giữ VI Dubber WIP, Trader pin, canonical QDM/raw và các seal; không broker/paid/Astra.",
        "",
        "## 1. Storage: đã dọn gì, giữ gì",
        "",
        "| D: phạm vi đọc được | Trước | Sau | Giảm |",
        "|---|---:|---:|---:|",
    ]
    for key, label in (("bytes", "Dung lượng GiB"), ("files", "File"), ("folders", "Folder")):
        values = [storage["D_before"][key], storage["D_after"][key], storage["D_reduction"][key]]
        show = [f"{v / 2**30:,.3f}" if key == "bytes" else f"{v:,}" for v in values]
        lines.append("| " + " | ".join([label, *show]) + " |")
    lines += [
        "",
        "GiB=2^30 bytes; giảm bytes ≈11,84GB thập phân. Đây là logical bytes, không allocated NTFS.",
        "Hai thư mục pytest dưới VI Dubber không có quyền đọc ở cả hai lần: không sửa ACL, không",
        "gọi là tổng tuyệt đối. Junction/symlink không được follow; map đầy đủ cấp1/2 ở private",
        "inventory có SHA trong JSON kèm theo. E initial scan còn9 lỗi long-path; E final hỗ trợ",
        "long path, không lấy chênh lệch hai lần đó làm số liệu cleanup E.",
        "",
        "- HOT: source active, VI Dubber (~129GiB), canonical QDM/tick/M1 và reports/seals giữ nguyên.",
        "- EPHEMERAL: 30.329 file cache/576.731.875 bytes và 6.524 file Rust incremental/",
        "  10.665.360.906 bytes đã xóa. Giữ executable, deps, source và runtime active.",
        "- COLD: hai `.venv` từ clean-setup fixture tháng10 đã archive vào E, roundtrip và",
        "  rehash trước bỏ bản giải nén (2.097 +5.551 file sau purge cache). MANIFEST SHA256",
        "  giữ từng file; không archive raw hay đổi path bằng chứng đang có seal.",
        "- D net giảm ít hơn tổng purge vì Python tái tạo cache khi kiểm thử, cùng source/report mới.",
        "- Không xóa venv/node_modules active, worktree thuộc chat khác hoặc log/evidence chỉ dựa tên.",
        "- E chỉ inventory và backup dry-run, không purge bản backup; E tăng thêm các receipt/archive",
        "  và cached EUR exports V9. Không `/MIR` hoặc `/PURGE`.",
        "",
        "Các thư mục cấp1 lớn trước cleanup:",
        "",
        "| Thư mục D | GiB | File | Folder |",
        "|---|---:|---:|---:|",
    ]
    for name, v in sorted(storage["D_top_level"].items(), key=lambda r: -r[1]["bytes"])[:10]:
        lines.append(f"| `{name}` | {v['bytes']/2**30:.3f} | {v['files']:,} | {v['folders']:,} |")
    lines += ["", "Cấp2 nhiều file nhất (không cộng lại với cấp1):", "",
              "| Thư mục | GiB | File |", "|---|---:|---:|"]
    for name, v in list(storage["D_top20_level2"].items())[:10]:
        lines.append(f"| `{name}` | {v['bytes']/2**30:.3f} | {v['files']:,} |")
    lines += ["", f"E final scan: **{storage['E_after_observed']['bytes']/2**30:.3f}GiB /",
              f"{storage['E_after_observed']['files']:,} files**,0 lỗi đọc; không purge E.",
              "Các thư mục cấp2 lớn nhất:", "",
              "| Thư mục E | GiB | File |", "|---|---:|---:|"]
    for name, v in list(storage["E_top20_level2"].items())[:8]:
        lines.append(f"| `{name}` | {v['bytes']/2**30:.3f} | {v['files']:,} |")
    lines += [
        "",
        "## 2. Lõi dùng chung, tests và hiệu năng",
        "",
        "`quant_core/market_data_store.py`: mmap read-only, seek timestamp, SHA256 từng file",
        "generation; reuse binary/offset manifests, không đẻ file mỗi giờ. `ftmo_execution_and_calendar`",
        "gom cửa vào fee/calendar, giữ uncertainty của holiday guards. `prop_lifecycle_and_parity`",
        "reuse V6/V7 harvester/oracle bằng adapter; synthetic replay đã đối soát cash.",
        "**Không rewrite V1–V8 đã seal; không tuyên bố đã xóa mọi duplication lịch sử.**",
        "Core là consumer contract cho lượt sau. Backend lifecycle vẫn fixed fee/risk scenarios;",
        "đổi phí không tự áp vào legacy backend nếu chưa có adapter/parity.",
        "",
        "| Kiểm thử | Số test | Giây local |",
        "|---|---:|---:|",
        f"| Trước, 4 runtime | 995 | {tests['before_seconds']:.3f} |",
        f"| Sau, đủ ID và thêm regression | {tests['after']} | {tests['after_seconds']:.3f} |",
        f"| Fast CI | {tests['fast_tests']} | {tests['fast_seconds']:.3f} |",
        f"| Historical, các runtime còn lại | {tests['historical_tests']} | {tests['after_seconds']-tests['fast_seconds']:.3f} |",
        "",
        "Không skip, không bỏ995 IDs cũ. Fast chứa mọi module CI cũ; historical là tập bù.",
        "Thời gian sau là tổng các receipt cuối đúng scope; không là một simultaneous capacity test.",
        "Lượt đầu sau purge cache lạnh mất55,70s; lượt warm đầu46,34s. Không giấu chi phí rebuild",
        "cache hoặc coi một mẫu timing là cam kết tốc độ. Shared capture fixture tạo một lần",
        "mỗi class, từng test dùng bản sao writable và kiểm fixture gốc bất biến.",
        "",
        "| Top10 module theo tổng thời gian test (không import/class setup) | Trước s | Sau s |",
        "|---|---:|---:|",
    ]
    for r in tests["top10_modules"]:
        lines.append(f"| `{r['module']}` | {r['before_seconds']:.3f} | {r['after_seconds']:.3f} |")
    bench = output["benchmark"]
    lines += [
        "",
        f"Benchmark16 cặp xen kẽ, cùng{bench['rows']:,} M1 tháng01/2022, parity từng field:",
        f"median {bench['medians']['before']*1000:.3f}ms → {bench['medians']['after']*1000:.3f}ms",
        f"(**{bench['speedup']:.2f}×** ở phép seek đã đo). Startup kiểm binary SHA mất",
        f"{bench['startup_binary_validation_seconds']:.3f}s; không quy9,8× thành tốc độ toàn chiến dịch.",
        "",
        "## 3. Alpha: S1/S2 không qua Stage-0 đa chế độ",
        "",
        "Dev=2019–20 +2022–23; các năm khác chỉ được đánh giá mới khi candidate đủ Dev.",
        "Toàn2018–2026 đã exposed. Dữ liệu giá mới ở V9 chỉ Dev và warmup trước mỗi cụm;",
        "đọc catalog hoặc hash opaque bytes không là mở outcome validation.",
        "",
        "S1: sweep high/low ngày trước vào London, SL extreme4H+0,1ATR trước nến.",
        "DAY và24H là hai exit horizons của cùng entry, không hai alpha độc lập.",
        "S2: ratio Asian width/median20 >1,5 dùng breakout/H4; phần còn lại dùng sweep",
        "quay lại hộp, SL4H. Đây chỉ proxy chế độ, chưa chứng minh macro expansion.",
        "",
        "Bảng sau là **raw endpoint markout**, chưa SL-active và chưa account PnL.",
        "Net là USD/oz sau stress SYM; SL là median trước lọc, retention ở cổng15%.",
        "Gold giữ commission0,0007% notional/side, slippage0,20USD/oz/side; swap",
        "SYM−40/−40 và ASYM−45/−5USD/lot/rollover (BUY/SELL),22UTC, thứ Tư×3.",
        "Đây là declared scenarios, không phải biểu phí FTMO live đã xác nhận.",
        "",
        "| Gold | Năm | Raw | Nhận | SL USD/oz | Giữ % | Net markout USD/oz |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in gold["summaries"]:
        value = r["markouts"][r["primary"]]["SYM_FLAT"]["mean_net_per_oz"]
        lines.append(f"| {r['candidate']} | {r['year']} | {r['raw']} | {r['admitted']} | {r['median_SL']:.3f} | {r['retention_pct']:.1f} | {value:+.4f} |")
    lines += [
        "",
        "S1 mở lại phễu2022/23 lên72,5%/55,4%, nhưng2019 chỉ16,3%; markout âm2019/20/23.",
        "Nới phạm vi cấu trúc stop không tạo ra directional edge. S2 cũng âm ở2019/20/22.",
        "Cả hai fail ngay cả tiêu chí tổng dương ở cả hai cụm, không chỉ fail một annual threshold.",
        "Không chọn lại side/horizon/regime threshold hoặc tune bằng validation để cứu.",
        "Gold dùng observed ticks khi có, M1 Bid +Ask proxy0,338 khi thiếu; source conditional",
        "không biến thành execution/prop certificate.973 rows gồm S1 hai horizons trùng entries;",
        "raw signal instances phân biệt là205 S1 và563 S2, không973 alpha độc lập.",
        "",
        "Attribution bên trong S2 (không dùng để chọn lại nhánh sau outcome):",
        "",
        "| Năm | Regime proxy | Raw | Net USD/oz |",
        "|---|---|---:|---:|",
    ]
    for r in regime_attribution:
        lines.append(f"| {r['year']} | {r['regime']} | {r['signals']} | {r['mean_net_usd_oz']:+.4f} |")
    lines += [
        "",
        "Cả expansion lẫn normal đều âm2019/20/22 ở proxy này; không có bằng chứng quy tắc",
        "đã tách được “ngày breakout thật” khỏi “ngày phá giả”. Không suy80% thị trường từ bảng.",
        "",
        "EURUSD có local M1/tick đủ Dev; đã export cached Bid M1, không download/update.",
        "Một S2.DAY conditional screen: Ask1pip, commission+slippage9USD/lot stress.",
        "Không giả nguồn Ask là observed, không gọi đây là FTMO live spec.",
        "",
        "| EURUSD S2 | Raw/định giá | Nhận | SL pips | Giữ % | Net USD/lot | Raw markout R |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in eur["annual"]:
        lines.append(f"| {r['year']} | {r['raw']}/{r['observed']} | {r['admitted']} | {r['median_SL_pips']:.2f} | {r['retention_pct']:.1f} | {r['mean_net_USD_lot']:+.2f} | {r['total_raw_markout_R']:+.2f} |")
    lines += [
        "",
        "EUR đủ retention, nhưng âm2019/22/23; cả tổng markout R2020 cũng âm dù mean USD/lot",
        "dương vì R chuẩn hóa theo SL khác nhau. Không lẫn hai cách weighting. US500 không có",
        "cached QDM series; nguồn component trước đây chưa admit đủ M1/tick2019–20 cùng",
        "cost/carry/calendar, nên không dựng synthetic raw hoặc tải provider mới để ép đủ bảng.",
        "",
        "### Bảng9 năm: chỉ baseline đã có, không mạo nhận V9 mới",
        "",
        "V9 không có ứng viên đạt, nên validation và lifecycle candidate bị hủy đúng protocol.",
        "Bảng dưới reuse control V8 fixed150USD; các cột V9=N/A. Không cộng hai lifecycle",
        "2018–21 và2022–26 thành một tài khoản chín năm.",
        "",
        "| Năm | Baseline lệnh | SYM NetR | ASYM NetR | V9 |",
        "|---|---:|---:|---:|---|",
    ]
    for r in controls:
        lines.append(f"| {r['year']} | {r['trades']} | {r['SYM_NetR']:+.4f} | {r['ASYM_NetR']:+.4f} | N/A: fail Dev |")
    lines += [
        "",
        "Baseline lifecycle đã có:0/48 monthly starts hoàn tất hai vòng ở2018–21;",
        "0/57 ở2022–26 mỗi fee model. Các cửa sổ chồng lấn, không future pass probability.",
        "Năm2026 trong bảng chỉ tới13/10/2026, không phải dữ liệu tới ngày báo cáo15/11.",
        "Không có **portfolio V9**, payout V9 hoặc9-year candidate lifecycle mới để báo.",
        "Không tăng risk hoặc ghép các nhánh fail để tạo danh mục có vẻ đạt.",
        "",
        "## 4. Workflow, kiểm chứng và lỗi đã giữ",
        "",
        "- Anti-bloat CI chặn changed JSON/JSONL/CSV >1MiB/file, >8MiB tổng hoặc>100 files;",
        "  raw/ledger và full storage maps giữ private, tracked JSON chỉ compact summary/pins.",
        "- Maintenance có inventory/purge có preflight, cold archive roundtrip, backup `/L`.",
        "  Một lệnh `maintain` kiểm tra, tùy chọn purge cache D và xuất backup preview; đã CLI smoke.",
        "  Không daemon, global config hoặc manager mới.",
        "- Gold:973 entries/1.946 endpoints/3.892 Fraction cost bridges PASS. EUR:562 lệnh/",
        "  1.124 quotes đọc trực tiếp từ CSV PASS. Khác implementation, **cùng implementer**;",
        "  không independent person/model review hoặc Astra.",
        "- Đã kiểm causal prefix, four-bar stop, checksum/tamper, lot/order-cost, holiday,",
        "  synthetic lifecycle/cash, cache protections, archive và absolute snapshot containment.",
        "- V8 development/release exact-byte seals PASS. V7 có newline seals khác trên shared",
        "  source:18 input/code records có exact-byte view riêng; không claim cả V7/V8 raw seals",
        "  cùng bind một working-tree representation. Không sửa frozen pins hoặc numerical content.",
        "",
        "Các failed/technical attempts vẫn giữ private: cleanup attempt1 có ancestor scan O(n²),",
        "dừng trước mutation (0 cache mất), thay bằng ancestor set; cleanup sau20,36s. Fixture",
        "class setup lần đầu sai receiver, sửa rồi toàn suite pass.",
        "CLI maintain smoke lần đầu gặp empty-root summary thiếu zero row; đã sửa và kiểm",
        "cả regression lẫn actual CLI (purge fixture, E preview giữ read-only).",
        "Checkout LF/CRLF có strict-hash failures đã giữ; restore chỉ khi exact registered SHA khớp.",
        "Một snapshot attempt ghép absolute source path sai đã ghi lại **cùng bytes** vào4",
        "private JSON inputs; SHA256 cả4 vẫn nguyên. Đã tạo view trong root riêng bằng helper",
        "có containment guard và regression kiểm source mtime/bytes không đổi. Không giấu lỗi này",
        "dưới nhãn read-only. Các attempt/result/seals gốc không được thay hash để ép pass.",
        "",
        "Đánh giá: engineering đã có kết quả đo và regression; alpha vẫn NO_GO. Không thể bảo",
        "đảm một workflow đúng sẽ tìm được edge. Chỉ mở cơ chế mới khi có hypothesis/budget mới;",
        "không mua Challenge từ các kết quả này.",
        "",
        f"Private evidence: `{JOB.as_posix()}`. JSON kèm theo giữ source hashes, inventory",
        "locators, top10 timings, benchmark samples, annual controls và từng gate/reason.",
        "Cách dùng: [maintenance](../../tooling/WORKSPACE-MAINTENANCE.md),",
        "[quant core](../../tooling/ai-engines/quant_core/README.md),",
        "[protocol](SYSTEM-AND-ALPHA-V9-PROTOCOL-20261115.md),",
        "[EUR admission](SYSTEM-AND-ALPHA-V9-EURUSD-ADMISSION-20261115.md).",
    ]
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(dict(report=str(OUT), tests=tests["after"], storage_reduction=storage["D_reduction"]))


if __name__ == "__main__":
    run()
