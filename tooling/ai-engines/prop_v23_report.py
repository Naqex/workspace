"""Four-part V23 report from pinned evidence, with no post-Dev reselection."""
import json
from prop_v23_common import *
from prop_v22_report import table,fmt

REPORT=Path('planning/research/SLEEVE-ABLATION-MT5-V23-RESULTS-20261117')


def label(identity):
    return 'EURUSD F5' if identity.startswith('EURUSD') else 'Gold '+identity.split('|')[1][:2]


def report():
    from prop_v23_campaign import verify
    frozen=verify();dev=read(JOB/'Dev-ablation-results.json');post=read(JOB/'post-freeze-attribution.json')
    h1=read(JOB/'H1-calendar-diagnosis.json');sessions=read(JOB/'H1-target-session-review.json')
    f5=read(JOB/'F5-transfer-results.json');tests=read(JOB/'tests-final-matrix.json');smoke=read(JOB/'smoke-final-results.json')
    integrity=read(JOB/'artifact-integrity-audit.json');assert integrity['passed']
    tail=read(JOB/'A1-tail-cadence-diagnostic.json')
    baseline=read('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')
    historical=[dict(scope=scope,**read(JOB/f'{scope}-{tag}-{mode}-{pct}-summary.json')) for scope in ('Dev','Full')
        for tag in ('OLHC','OHLC') for mode,pct in (('PRIMARY',100),('PRIMARY',150),('STRICT',100))]
    mc=[read(JOB/f'MC-{tag}-summary.json') for tag in ('OLHC','OHLC')]
    watch=read(JOB/'watch-native-timeout/WATCH_REPORT.json')
    result=dict(schema='V23-results-v1',selection=frozen,Development=dev,attribution=post,H1_price=h1,H1_sessions=sessions,
        F5_transfers=f5,historical=historical,monte=mc,baseline_history=baseline['historical'],
        baseline_monte=[v for v in baseline['monte'] if v['mode']=='PRIMARY' and v['friction']==100],
        tests=tests,smoke=smoke,watch=watch,integrity=integrity,A1_tail_cadence=tail,performance_AB=read(JOB/'smoke-AB-results.json'),
        incumbent='V16/V19 BASE_GUARD',A1_status='DEV_SCREEN_PASSED_BUT_NOT_INCUMBENT_REPLACEMENT',
        prop_qualified=False,actual_broker_orders=0,actual_payout_USD=0,
        limits=['Later 2024-2026 history already exposed; no clean OOS claim.',
            'Fixed150 unit-book attribution is not account lifecycle or real account performance.',
            'All proposed child profiles and three exact transfers are counted; no new weights or thresholds.',
            'Global top10 removal is descriptive; Dev selection used mean R/trade only.',
            'Original 32/494 source-uncertain paths remain unresolved; removed F3 does not repair source gaps.',
            'M1 ordering/Ask/cost/news/session proxies remain. H1 endpoints do not certify intrahour SL or equity.',
            'Target FTMO holiday session can be closed while vendor quote exists; price coverage is separate.',
            'Historical monthly starts overlap; conditional medians omit uncompleted starts.',
            'Quarter-block bootstrap reuses exposed joint history and is not a future probability.',
            'Standalone Funded payouts differ from post-Challenge payouts; neither is an actual payout.',
            'Native watcher success and real execution slippage are unverified with no target terminal present.',
            'Read-only observation never grants shadow/live execution or account submission.'],
        bindings=dict(protocol_sha256=sha(PROTOCOL),freeze_sha256=sha(FREEZE),
            baseline_report_sha256=sha('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    assert len(text.encode())<1048576
    REPORT.with_suffix('.json').write_text(text,encoding='utf-8',newline='\n')
    selected=next(r for r in dev['cases'] if r['passed']);m=selected['cases'][0]['candidate']
    lines=['# V23 — tách ba nhánh, thử loại F3 và kiểm watcher MT5','',
        '**Bỏ Gold F3 cải thiện Development, nhưng chưa đủ để thay V16/V19 BASE_GUARD. '
        'Ba phép chuyển F5 đều rớt; chưa có chiến lược đủ điều kiện mua Challenge.**','',
        'PR101/head `26de14c` đã merge `9309109`; nhánh V22 đã xóa. Nhánh V23 '
        '`codex/sleeve-ablation-and-mt5-v23`, freeze `d7e8150` trước khi tính thống kê mới trên lịch sử sau 2023. '
        'Lịch sử 2024–13/10/2026 đã exposed từ các chiến dịch trước, không gọi là OOS sạch. '
        'Không đổi signal, stop, risk, exit hoặc thử trọng số sau kết quả. PR102 để mở.','',
        '## 1. Đóng góp từng nhánh và phép loại trừ','',
        'Mỗi nhánh là một cơ chế giao dịch (sleeve). R ở bảng này = PnL ròng / 150 USD, '
        'có lot floor thực của model. Drawdown equity có floating theo đường M1 giả định; cashDD chỉ dùng lệnh đóng. '
        'Mỗi kỳ bắt đầu flat riêng. ExTop10 bỏ đúng 10 identity thắng lớn nhất toàn danh mục đã exposed; '
        'không bỏ 10 lệnh riêng của từng nhánh.','']
    lines+=table(['Kỳ','Nhánh','Lệnh','Win%','NetR','MeanR','EquityDD R','CashDD R','ExGlobalTop10 R'],[
        [r['period'],label(r['id']),r['trades'],fmt(100*r['winrate'],2),fmt(r['net_R']),fmt(r['mean_R']),
         fmt(r['equity_R_DD']),fmt(r['cash_R_DD']),fmt(r['ExGlobalTop10_R'])] for r in post['orders']['OLHC']['rows']])
    lines+=['','Cả hai thứ tự OLHC/OHLC có trong JSON. V22 G_L3_A **đã miễn EURUSD F5**; '
        '17,289R là mọi khoản lỗ tránh được, trong đó L3 chỉ 10,858R. Cả 17,813R lời bị bỏ đều thuộc Gold.','']
    lines+=table(['Nhánh','Lệnh chặn','Lỗ tránh R','Trong đó L3 R','Lời mất R','Delta NetR'],[
        [label(r['id']),r['rejected'],fmt(r['avoided_loss_R']),fmt(r['L3_loss_R']),fmt(r['lost_winner_R']),
         fmt(r['avoided_loss_R']-r['lost_winner_R'])] for r in dev['V22_A_attribution']])
    lines+=['','Ba trial Development đã đăng ký; cổng yêu cầu net tăng, equityDD giảm, daily không tăng và hai cụm ba năm dương trong cả hai ordering. '
        'Không có grid trọng số. A1 chọn F3 vì mean Dev R/lệnh thấp nhất, không chọn bằng top10 toàn kỳ.','']
    lines+=table(['Trial','Lệnh giữ','NetR','EquityDD R','Worst daily R','2018–20 R','2021–23 R','Gate'],[
        [r['profile']['name'],r['cases'][0]['retained'],fmt(r['cases'][0]['candidate']['net_R']),
         fmt(r['cases'][0]['candidate']['equity_R_DD']),fmt(r['cases'][0]['candidate']['worst_daily_R']),
         *[fmt(v) for v in r['cases'][0]['cluster_R']],'PASS' if r['passed'] else ', '.join(r['cases'][0]['reasons'])] for r in dev['cases']])
    lines+=['','Baseline Dev: +23,8524R / 12,2065R equityDD. A1: '
        f"+{m['net_R']:.4f}R / {m['equity_R_DD']:.4f}R; giữ nguyên risk hai nhánh còn lại, không phân bổ lại risk F3. "
        'Day-range/ATR là biến biết tại entry; L3 là nhãn sau outcome, không dùng làm tín hiệu trực tiếp.','',
        'Phân nhóm ngày biến động lớn sau đây chỉ mô tả Dev, không là bộ lọc mới hay bằng chứng nhân quả. '
        'Mẫu ngày lớn của F5 có thể không đồng nhất với mọi chế độ đảo chiều.','']
    lines+=table(['Nhánh','DayRange/ATR','Lệnh','NetR','MeanR'],[
        [label(r['id']),r['day_range_ATR_band'],r['count'],fmt(r['net_R']),fmt(r['mean_R'])] for r in post['Dev_regime_description']])
    lines+=['','Dữ liệu không xác nhận mệnh đề “F5 cần ngày đã chạy lớn”: Dev F5 ở DayRange/ATR≤0,9 đạt '
        '+24,602R / mean+0,172R, nhóm>0,9 chỉ +0,589R / mean+0,012R. Gold F3 âm trong cả hai nhóm; '
        'Gold F4 lại dương ở cả hai. Không suy causal regime hoặc mở filter mới từ bảng này. '
        'F3 đổi từ −9,701R Dev sang +10,226R kỳ sau; F4 đổi từ +8,362R sang −3,437R. '
        'Vì thế bỏ F3 có lợi trong tập chọn nhưng không tự bảo đảm bền qua chế độ thị trường.']
    lines+=['','## 2. Sáu quan sát H1 mỗi cặp và chuyển nguyên F5','',
        '**Giá đủ 100%: GBPUSD 2.288/2.288, AUDUSD 1.795/1.795.** Không thêm nến hoặc bịa early-close. '
        '12 quan sát (không phải 12 ngày khác nhau) bị `ok=false` do Gold holiday guard, đều có entry/endpoint đúng giờ. '
        'Bảng sau tách quyền giao dịch đích khỏi sự tồn tại giá.','']
    lines+=table(['Asset','Recipe','Ngày UTC','Giá entry/20:00','FTMO session evidence'],[
        [r['asset'],r['recipe'],r['date'],'Có / Có',r['status']] for r in sessions['rows']])
    lines+=['','Nguồn chính thức đã đối chiếu: '
        '[24/12/2021](https://ftmo.com/es/blog/trading-update-16-12-2021/), '
        '[15/04/2022](https://ftmo.com/it/blog/trading-update-07-04-2022-2/), '
        '[07/04/2023](https://ftmo.com/en/blog/trading-updates/trading-update-30-mar-2023/), '
        '[bảng Christmas 26/12/2022](https://ftmo.com/it/blog/trading-update-05-01-2023-2-2-2/). '
        'Ngày 26/12/2022 FX đóng: quote nguồn không được coi là lệnh đích hợp lệ. '
        '2018/2019/2021 Good Friday chưa có thông báo đúng ngày được xác minh; giữ unknown. '
        'Không lấy lịch broker khác thay FTMO. Các phép đo transfer dùng declared weekday scenario, chưa chứng nhận lịch đích.','',
        'F5 giữ H4 / vùng 5 ngày / ADX≤25 / buffer 0,1ATR / tín hiệu đầu tiên mỗi ngày UTC / naturalSL P0; '
        'không thêm parameter. FX dùng H1 thật để dựng H4, không tạo M1; deadline 20:00. Gold M1 dùng 20:30 và lịch guard đã khóa. '
        'Bảng này là raw markout sau phí stress trước stop, không phải account replay.','']
    lines+=table(['Asset','Raw/priced','Cost giữ%','Median SL','Friction/SL%','2018–20 R','2021–23 R','Dual/Stage0'],[
        [r['asset'],f"{r['raw']}/{r['priced']}",fmt(100*r['cost_only_retention'],2),
         fmt(r['median_natural']*(1e4 if r['asset']!='XAUUSD' else 1),2)+(' pip' if r['asset']!='XAUUSD' else ' USD/oz'),
         fmt(100*r['scale_ratio'],2),*[fmt(v) for v in r['cluster_net_R']],f"{r['dual_cluster_positive']} / {r['stage0_passed']}"] for r in f5['rows']])
    lines+=['','**0/3 qua Dual-Cluster; 0/3 qua Stage-0.** Không chạy SL/account cho losers. '
        'Tất cả còn thiếu cadence≥40 mỗi năm và ít nhất một năm âm/không bù ma sát.','',
        '## 3. A1: mô phỏng tài khoản thật về mặt model, chưa là giao dịch thật','',
        'Chỉ A1 qua Dev nên mới được chạy toàn kỳ. Reuse quote/event quarter tapes V19, bỏ đúng actions F3, '
        'giữ quotes/reset/session/cost/lot/shared risk/house-money. Mỗi case gồm 105 mốc mở Challenge hằng tháng '
        'và 1 sổ Standalone Funded, với oracle kiểm toàn ledger. Không cộng payout của các mốc chồng nhau thành thu nhập.','']
    rows=[]
    for r in baseline['historical']:
        if r['version']=='V19' and r['order']=='OLHC':
            rows.append(['V19',r['mode'],r['friction_pct'],r['phase1'],r['funded'],fmt(r['median_months'],2),fmt(r['worst_daily']),fmt(r['worst_static']),r['breaches']])
    for r in historical:
        if r['scope']=='Full' and r['order']=='OLHC':
            rows.append(['A1',r['source'],r['friction'],r['phase1'],r['funded'],fmt(r['median_months'],2),fmt(r['worst_daily']),fmt(r['worst_static']),r['breaches']])
    lines+=table(['Model','Path','Friction%','Vòng1/105','Hai vòng/105','Median tháng*','Daily%','Static%','Breach'],rows)
    lines+=['','*Median chỉ trên mốc đã hoàn tất; không chứng minh mốc mới sẽ pass nhanh hơn. '
        'A1 PRIMARY100 chỉ 63/105 hai vòng so với 71/105 V19; 33 mốc bắt đầu từ 2024 vẫn 0 hoàn tất. '
        'Giảm median có thể do thay nhóm đã pass, không đủ để promote. STRICT là stress nguồn thiếu, không sửa 32 path gốc. '
        'Dev72 starts và OHLC mọi case giữ đầy đủ trong JSON.','',
        f"A1 fixed150 toàn kỳ giữ {post['orders']['OLHC']['full_selected_count']}/494 lệnh, "
        f"NetR {post['orders']['OLHC']['full_selected_unit_metrics']['net_R']:.4f} so với baseline42,3917R. "
        f"Cadence khoảng {tail['annual_cadence']:.2f} lệnh/năm; ExGlobalTop10 còn {tail['ExGlobalTop10_R']:.4f}R "
        f"(baseline {tail['baseline_ExGlobalTop10_R']:.4f}R). A1 còn30/391 path source-uncertain "
        'so với32/494 gốc: loại F3 không khôi phục dữ liệu thiếu. Đây là sổ đơn vị, chưa phải đường vốn tài khoản adaptive.','',
        'Bootstrap: **5.000 cùng draw plans cho mỗi ordering**, mỗi draw có Challenge + Standalone Funded, '
        '36 tháng và prefixes 12/18/24, giữ tương quan giữa tài sản qua joint quarter blocks. '
        '10.000 draw-order evaluations / 20.000 ledgers đều audit. Đây là tần suất resampling lịch sử đã exposed, '
        'không phải xác suất tương lai.','']
    rows=[]
    for r in result['baseline_monte']:
        if 'OLHC' in r.get('path',''):
            rows.append([r['version'],'OLHC',*[fmt(h['both_pct'],2) for h in r['horizons']],fmt(r['mean_annual_payout_USD'],2)])
    for r in mc:
        rows.append(['A1',r['order'],*[fmt(h['both_pct'],2) for h in r['horizons']],fmt(r['mean_annual_payout_USD'],2)])
    lines+=table(['Model','Order','Hai vòng12m%','18m%','24m%','36m%','Standalone payout USD/năm'],rows)
    lines+=['','Payout cột cuối là model Funded ngay từ đầu mỗi draw, khác payout sau khi pass Challenge. '
        'JSON ghi riêng post-Challenge payout. Chưa tính đây là thu nhập owner hoặc tiền rút thật. '
        '**Giữ incumbent V16/V19 BASE_GUARD**; A1 là bằng chứng cấu trúc đáng giữ nhưng chưa giải quyết time-fit/robustness.','',
        '## 4. Watcher, kiểm toán, hiệu năng và storage','',
        'Lệnh mới (foreground, giới hạn chờ và capture; không cài service):','',
        '```powershell',
        'uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.ftmo_trial_runner --watch-mt5 --watch-timeout 300 --seconds 60',
        '```','',
        'Watcher dò terminal đã chạy → kiểm FTMO Demo/Trial USD và quote đủ mới → bind executable/account hash/server → '
        'snapshot spec + parity diff → lưu Bid/Ask/spread thành Zstd Parquet/SHA256. '
        'Nếu terminal mất hoặc account đổi, ghi failure; không tự chạy fixture. Không mở terminal/login/symbol_select hoặc gửi lệnh. '
        'Timeout/poll/capture đều hữu hạn; không tự chuyển shadow. Commission/lịch phiên/tin có thể vẫn unknown.','',
        f"CLI thực tế: `{watch['status']}`, {watch['attempts']} probes / {watch['total_wall_seconds']:.3f}s, "
        'không terminal đích và không broker orders. 15 regressions V23 gồm detect/capture giả lập, timeout, interrupt, '
        'terminal biến mất, replay giả, thiếu binding và account drift. Native capture thành công còn chưa kiểm trên terminal thật.','',
        f"Full suite **{tests['tests']} PASS / 0 skip**, giữ nguyên **1.280 V22 IDs**, wall **{tests['total_wall_seconds']:.3f}s**; "
        f"mục tiêu <13,2s: **{tests['target_under132']}**. Smoke 10 fresh serial processes/same78 IDs: "
        f"**{smoke['below072']}/10 <0,72s**, median **{smoke['median']:.3f}s**, max **{smoke['max']:.6f}s**. "
        'Giữ mọi outlier; không retry chọn streak. Startup và fixture I/O nằm trong timer.','',
        'Profile smoke cho thấy chi phí import/filesystem. Thử A/B 8 samples xen kẽ dedup import roots không cho cải thiện nhất quán; '
        'không đưa thay đổi đó vào source. MC workers cùng chạy trong A/B, nên không so absolute samples đó với final idle timing.','',
        f"{integrity['compressed_tables']} bảng Zstd9: {integrity['original_bytes']:,} → {integrity['compressed_bytes']:,} bytes; "
        'SHA256 compressed/original và roundtrip đã kiểm. Journals/checkpoints/raw logs giữ nguyên để đối soát/resume; '
        'small human-readable receipts giữ JSON, không nhân bản price cache hoặc xóa nguồn.','',
        'Kiểm toán độc lập agent tại `6d2df38`: không finding material trong ablation/calendar/watcher, '
        '15 tests xanh và29 manifests lúc review; không bao gồm final aggregates/CI chưa có lúc đó. '
        'Integrity audit cuối kiểm thêm toàn bộ ledgers/manifests. Không phải nguồn giá độc lập hay broker acceptance.','',
        '| Hậu kiểm | Kết luận |','|---|---|',
        '| Bỏ nhánh âm Dev vẫn làm ít mốc pass hơn | Diversification, account path và phase state khác cộng R; không promote bằng Dev tổng |',
        '| `ok=false` bị gọi là thiếu giá | Tách price availability và target-session eligibility; giữ V22 receipts, sửa active interpretation |',
        '| Cổng exhaustion gộp F3/F4 mất winner | Split đúng cơ chế vẫn phải qua net/DD; hai A2 đều fail |',
        '| Terminal có thể mất giữa probe/capture | Require native + executable/account binding; fail-closed, giữ report |',
        '| Benchmark nhiễu | Giữ samples, bác tối ưu không chứng minh được; không xóa tests hoặc chọn streak |','',
        'PR102 để mở; exact-head 3CI/downloaded test IDs chốt trong private '
        '`ci-exact-head-reconciliation.json` và `completion-receipt.json` sau push. '
        'Giữ Trader pin/VI Dubber WIP, không có broker execution/deploy/payout thật.','',
        '[Protocol](SLEEVE-ABLATION-MT5-V23-PROTOCOL-20261117.md) · '
        '[Freeze](SLEEVE-ABLATION-MT5-V23-FREEZE-20261117.json) · '
        '[JSON](SLEEVE-ABLATION-MT5-V23-RESULTS-20261117.json) · '
        '[Quickstart](QUICKSTART-FTMO-FREE-TRIAL.md)']
    REPORT.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    event('V23_report_complete',bytes=len(text.encode()))


if __name__=='__main__':report()
