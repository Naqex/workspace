"""Build the single owner report from sealed campaign outputs, without prices."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean,median

from prop_campaign_source import JOB,PARENT,read,write_json,digest,DAY

REPORT=Path('planning/research/PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114')


def aggregate(cases,baseline=False):
    passes=lambda c:c['phase_passes']
    def months(which):
        values=[(passes(c)[which]['at']-c['start_msc'])/DAY/30.4375
                for c in cases if len(passes(c))>which]
        return median(values) if values else None
    return dict(starts=len(cases),step1=sum(len(passes(c))>=1 for c in cases),
        both=sum(len(passes(c))==2 for c in cases),
        step1_median_months_completed_only=months(0),both_median_months_completed_only=months(1),
        breaches=sum(c['first_breach'] is not None for c in cases),
        worst_daily_pct=max(c['worst_daily_loss_pct'] for c in cases),
        worst_static_pct=max(c['static_loss_pct'] for c in cases),
        worst_peak_dd_pct=max(c['peak_to_valley_pct'] if baseline else c['peak_dd_pct'] for c in cases),
        payouts=sum(len(c.get('payouts',[])) for c in cases),
        trader_payout_usd=sum(c.get('trader_payout_usd',0) for c in cases))


def compact(r):
    return {k:v for k,v in r.items() if k not in (
        'accepted','closed','stale_midnight_marks','daily_equity_marks')}


def date_text(at):
    return datetime.fromtimestamp(at/1000,timezone.utc).strftime('%Y-%m-%d') if at else '—'


def build():
    freeze=read(JOB/'composition-freeze.json')
    parity=read(JOB/'computational-parity.json')
    tests=read(JOB/'regression-tests.json')
    old=read(PARENT/'attempt-2/result.json')
    annual={c:read(JOB/f'frozen-system-{c}-annual.json') for c in ('SYM_FLAT','ASYM_FLAT')}
    cases={c:read(JOB/f'lifecycle-{c}.json') for c in annual}
    summaries=[]
    for cell in annual:
        for risk in (150,200):
            subset=[c for c in old['rolling'] if c['cell']==cell and c['risk_usd']==risk]
            summaries.append(dict(system='Anchor0',policy=f'fixed {risk/500:.2f}%',cell=cell,
                **aggregate(subset,True)))
        summaries.append(dict(system='Frozen A0',policy='.50% → .35% → .25%',cell=cell,
            **aggregate(cases[cell])))
    phase1=read(JOB/'phase1-metrics.json');forensics=read(JOB/'phase1-forensics.json')
    result=dict(schema='PROP-QUALIFICATION-CAMPAIGN-v1',date='2026-11-14',
        decision='NOT_CHALLENGE_READY',selected_exit=freeze['selected_exit'],
        selected_sleeves=freeze['selected_sleeves'],new_hypotheses=6,
        unused_sleeve_slot=1,baseline_merge='3307fae',protocol_freeze_commit='95e3709',
        implementation_and_decision_commit='2e713c1',selection=freeze,
        forensics=forensics,exit_comparison={k:dict(unknown_decisions=len(v['unknown']),
            annual=[compact(r) for r in v['annual']] if v['annual'] else None) for k,v in phase1.items()},
        annual={c:[compact(r) for r in v] for c,v in annual.items()},
        lifecycle_summary=summaries,lifecycle={c:[compact(r) for r in v] for c,v in cases.items()},
        computational_parity={k:v for k,v in parity.items() if k!='accounts'},
        regression=tests,prices2025_2026_read=False,broker_calls=0,prop_qualified=False,
        data_roles=dict(development='2022-2023',historical_validation='2024 already exposed',
                        reserved='2025-2026 never decoded'),
        reward_proxy=dict(min_days=30,minimum_profit_usd=20,account_debit_fraction=1,
            trader_fraction=.8,firm_fraction=.2,administrative_delay_days=0,
            official_source='https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/',
            actual_payout_received=False),
        blockers=['R_VELOCITY_BELOW_TARGET','TAIL_CONCENTRATION','NO_TWO_STEP_COMPLETION',
            'STATIC_BUFFER_TOO_THIN_AT_HIGHER_RISK','NO_PRISTINE_OOS',
            'TARGET_FEED_NEWS_MARGIN_AND_SWAP_NOT_VERIFIED','NO_FORWARD_VALIDATION'],
        private_job=str(JOB),
        artifact_pins={p.name:digest(p) for p in JOB.glob('*.json')
                       if not p.name.startswith('failure-')},
        code_pins={p.name:digest(p) for p in Path('tooling/ai-engines').glob('prop_campaign*.py')},
        review_identity='same implementer; separate numerical oracle, no Astra/agent review')
    write_json(REPORT.with_suffix('.json'),result)
    lines=[
        '# Kết quả chiến dịch exit → sleeves → vòng đời quỹ',
        '',
        '**Kết luận: đã hoàn tất chiến dịch, nhưng chưa đủ cơ sở để mua Challenge.** '
        'Không exit mới hoặc sleeve nào vượt cổng Development. Hệ thống cuối giữ A gốc; '
        'chính sách vốn mới giúp qua vòng 1 nhiều hơn, vẫn không hoàn tất hai vòng hoặc tạo payout.',
        '',
        'Owner: task `229f6d76-e9a1-4f58-bcf4-c1545bea757b`. Ngày 14/11/2026. '
        'PR78 đã merge `3307fae`; baseline/result vẫn bất biến. Protocol khóa tại `95e3709`; '
        'quyết định Development và code tại `2e713c1`, trước mở kết quả mới năm 2024. '
        '2025–2026 không được giải mã. Không broker, mua challenge, gọi model hay sửa VI Dubber.',
        '',
        '## 1. Trước và sau — 36 mốc xuất phát tháng',
        '',
        'Mỗi hàng dùng cùng 36 ngày bắt đầu từ 01/2022 đến 12/2024, kết thúc trước 01/01/2025. '
        'Mốc muộn có thời gian theo dõi ngắn hơn; các cửa sổ chồng lấn, không là 36 thử nghiệm độc lập. '
        'Các tỷ lệ là kết quả quan sát, không phải xác suất thắng tương lai. SYM = swap −40/−40; '
        'ASYM = proxy −45/−5 USD/lot/rollover.',
        '',
        '| Hệ thống / risk | Phí | Qua vòng 1 | Qua cả hai | Trung vị vòng 1* | Vi phạm | Worst daily | Worst static | Peak DD | Payout |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        duration=f"{r['step1_median_months_completed_only']:.2f} tháng" if r['step1_median_months_completed_only'] is not None else 'Chưa có'
        lines.append(f"| {r['system']} / {r['policy']} | {r['cell'].split('_')[0]} | {r['step1']}/36 | {r['both']}/36 | {duration} | {r['breaches']} | {r['worst_daily_pct']:.3f}% | {r['worst_static_pct']:.3f}% | {r['worst_peak_dd_pct']:.3f}% | {r['payouts']} / ${r['trader_payout_usd']:.2f} |")
    lines+=['',
        '*Trung vị chỉ tính các mốc đã đạt, không suy ra thời gian của 36 mốc còn lại. '
        'Không có trung vị hoàn tất cả hai vòng vì chưa có trường hợp hoàn tất.',
        '',
        'Risk mới cố định trước kết quả: vòng 1 0,50%, vòng 2 0,35%, funded 0,25%; '
        'giảm risk lệnh mới xuống 0,25% khi lỗ thực hiện trong ngày >1,8% hoặc equity dưới 95,5% vốn đầu. '
        'Vị thế cũ giữ size cũ. Có cổng dự trữ rủi ro chung theo SL, phí và funding; '
        'không chọn risk bằng cách thử nhiều mức trên kết quả.',
        '',
        'Worst static 9,32% để lại chỉ khoảng 0,68 điểm phần trăm trước giới hạn 10%; '
        '“không vi phạm trong mẫu” không đồng nghĩa đủ an toàn. Peak DD là sụt giảm từ đỉnh, '
        'khác static loss tính dưới vốn đầu. Daily 5% là ranh giới cấm, không là ngân sách cần dùng hết.',
        '',
        '## 2. Kinh tế tín hiệu không được cải thiện bởi tăng size',
        '',
        'Bảng dùng đúng $150 rủi ro danh nghĩa mỗi lệnh để tách thay đổi tín hiệu khỏi đi vốn. '
        'Trước/sau giống nhau vì mọi biến thể bị loại. Return (%) = Net R × 0,30%; '
        '1R = $150, không phải toàn bộ số dư tài khoản.',
        '',
        '| Năm | Phí | Lệnh | Net R trước = sau | Return | Equity DD (R) | Peak DD | Static loss | Worst daily | Net bỏ top 3 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cell,rows in annual.items():
        for r in rows:
            lines.append(f"| {r['year']} | {cell.split('_')[0]} | {r['entries']} | {r['net_R']:+.3f} | {r['net_R']*.3:+.3f}% | {r['max_equity_R_DD']:.3f} | {r['peak_dd_pct']:.3f}% | {r['static_loss_pct']:.3f}% | {r['worst_daily_loss_pct']:.3f}% | {r['net_ex_top3_R']:+.3f}R |")
    velocity=mean(r['net_R'] for r in annual['ASYM_FLAT'])
    lines+=['',f'ASYM trung bình chỉ **{velocity:.3f}R/năm**, vẫn thấp hơn mục tiêu 25–40R/năm; '
        'equity DD năm 2023 khoảng 20,9R, cũng vượt đích 12–15R. '
        'Bỏ ba lệnh thắng lớn nhất thì cả ba năm đều âm. Đây là phép đo độ tập trung; '
        'không tự bác trend-following chỉ vì lợi nhuận tập trung, nhưng chưa đủ biên an toàn cho mục tiêu thu nhập chính.',
        '',
        '## 3. Phase 1 — giải phẫu giveback và ba exit',
        '',
        '| Ngưỡng MFE ngày 1, sau phí | Đã đạt / 210 | Sau đó đóng âm (SYM / ASYM) | Mất ≥50% lãi đỉnh (SYM / ASYM) |',
        '|---|---:|---:|---:|']
    for threshold in ('1','1.5','2','3'):
        sy=[forensics['SYM_FLAT'][str(y)]['thresholds'][threshold] for y in (2022,2023)]
        ay=[forensics['ASYM_FLAT'][str(y)]['thresholds'][threshold] for y in (2022,2023)]
        lines.append(f"| ≥{threshold}R | {sum(r['reached'] for r in sy)} | {sum(r['final_negative'] for r in sy)} / {sum(r['final_negative'] for r in ay)} | {sum(r['gave_back_half'] for r in sy)} / {sum(r['gave_back_half'] for r in ay)} |")
    lines+=['','Các nhóm ngưỡng lồng nhau, không cộng thành số lệnh riêng.',
        '',
        '| Năm | Thanh lý trước rollover đầu | Phần thay đổi sau đó SYM | Phần thay đổi sau đó ASYM |',
        '|---|---:|---:|---:|']
    for year in ('2022','2023'):
        s=forensics['SYM_FLAT'][year];a=forensics['ASYM_FLAT'][year]
        lines.append(f"| {year} | {s['pre_rollover_sum_R']:+.3f}R | {s['post_rollover_increment_R']:+.3f}R | {a['post_rollover_increment_R']:+.3f}R |")
    lines+=['',
        'Đây là chênh lệch giữa các điểm thanh lý trên đường giữ lệnh thực, không phải chứng minh '
        'nhân quả cho “ngày 2”. Các lệnh đã SL/đóng sớm giữ đúng điểm đóng; giá trước 22UTC có thể cũ '
        'qua giờ bảo trì. Không biến carried mark thành giá mới có thể khớp.',
        '',
        '| Exit | Phí | Net R 2022 / 2023 | Equity DD R 2022 / 2023 | Bỏ top 3 R 2022 / 2023 | Quyết định |',
        '|---|---|---:|---:|---:|---|']
    for policy in ('A0','E1','E2','E3'):
        for cell in annual:
            r=phase1[cell+':'+policy]
            if r['annual']:
                a,b=r['annual'];decision='Giữ baseline' if policy=='A0' else 'Không đạt cổng cải thiện cả hai năm'
                lines.append(f"| {policy} | {cell.split('_')[0]} | {a['net_R']:+.3f} / {b['net_R']:+.3f} | {a['max_equity_R_DD']:.3f} / {b['max_equity_R_DD']:.3f} | {a['net_ex_top3_R']:+.3f} / {b['net_ex_top3_R']:+.3f} | {decision} |")
            else:
                lines.append(f"| {policy} | {cell.split('_')[0]} | N/A | N/A | N/A | {len(r['unknown'])}/210 mốc 21:30 không có giá mới; không chọn |")
    lines+=['',
        'E1 đóng 20:30 nếu chưa lãi ròng 1,5R; lệnh được giữ có stop dự phòng chi phí. '
        'E2 kích hoạt bảo vệ tại 1,5R rồi dùng nến H1 đóng qua SMA20 để thoát, không đặt trần TP. '
        'E3 dùng đệm phí carry lúc 21:30. E3 có 76 quyết định rơi trong giờ nghỉ thị trường: '
        'các đường parent giữ trong artifact chỉ phục vụ chẩn đoán, không được cộng thành kết quả E3 hợp lệ. '
        'Không đổi giờ E3 để cứu kết quả. Stop bảo vệ vẫn có thể lỗ khi gap/trượt giá.',
        '',
        '## 4. Phase 2 — ba sleeve, không dùng slot thứ tư',
        '',
        '| Sleeve | Năm | Tín hiệu / đủ giá | SL trung vị | Phí/SL | Qua cổng 12% | Net markout SYM / ASYM | Ma sát trung bình |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for name in ('S1','S2','S3'):
        for r in freeze['stage0'][name]['annual']:
            scale=10000 if name=='S3' else 1;unit=' pip' if name=='S3' else ' USD/oz'
            lines.append(f"| {name} | {r['year']} | {r['raw_signals']} / {r['priced']} | {r['natural_sl_median']*scale:.2f}{unit} | {100*r['scale_ratio']:.2f}% | {100*r['pass12_fraction']:.1f}% | {r['net_mean']['SYM_FLAT']*scale:+.3f} / {r['net_mean']['ASYM_FLAT']*scale:+.3f}{unit} | {r['mean_execution_friction']*scale:.3f}{unit} |")
    lines+=['',
        '- **S1:** H1 hồi rồi vượt nến trước theo H4, 12–16UTC, đóng 20:30. Năm 2022 '
        'dương +0,259 USD/oz nhưng nhỏ hơn ma sát 0,801: không qua Stage-0 đã khóa.',
        '- **S2:** H1 inside-bar rồi breakout theo H4, giữ 48h/chặn nghỉ lễ. Âm năm 2022; '
        'năm 2023 chỉ 37 tín hiệu và tỷ lệ quy mô 12,24% vượt ngưỡng 12% đã chọn.',
        '- **S3:** EURUSD H1 phá vùng Á theo H4, giữ 24h/chặn lịch. Quy mô SL phù hợp, '
        'nhưng âm cả hai năm. Dùng phí 9 USD/lot/vòng và swap stress −40 USD/lot/rollover cả hai chiều; '
        'đây là kịch bản bảo thủ được đăng ký, không biểu phí lịch sử FTMO đã xác minh.',
        '',
        '**Không sleeve nào được sang Stage-1**, nên không viết SL-active/đo tương quan hay ghép '
        'portfolio để cứu chúng. Tương quan là N/A, không giả bằng 0. Không chạy US500 hoặc '
        'dùng slot thứ tư chỉ để vét ngân sách. Không có portfolio đa nhánh đủ điều kiện trong chiến dịch này.',
        '',
        '## 5. Sổ 36 mốc tháng — chính sách vốn mới',
        '',
        '| Bắt đầu | SYM vòng 1 | SYM vòng cuối / balance | ASYM vòng 1 | ASYM vòng cuối / balance |',
        '|---|---|---:|---|---:|']
    for s,a in zip(cases['SYM_FLAT'],cases['ASYM_FLAT']):
        lines.append(f"| {date_text(s['start_msc'])} | {date_text(s['phase_passes'][0]['at']) if s['phase_passes'] else 'Chưa đạt'} | {s['phase']} / ${s['balance_usd']:,.2f} | {date_text(a['phase_passes'][0]['at']) if a['phase_passes'] else 'Chưa đạt'} | {a['phase']} / ${a['balance_usd']:,.2f} |")
    lines+=['',
        'Cả 72 trường hợp kết thúc do hết lịch sử quan sát, không phải bị xóa vì thua. '
        'Không tự retry/reset khi lỗ, không nối các sổ năm độc lập, không mang vị thế cũ sang tài khoản mới.',
        '',
        '## 6. Payout, chi phí và khoảng trống thực thi',
        '',
        'Reward proxy: chỉ tài khoản funded, flat, đã đủ 30 ngày từ lệnh funded đầu/chu kỳ trước '
        'và lãi đóng ≥20 USD mới xét. Trừ 100% lãi khỏi tài khoản; 80% quyền nhận của trader, 20% của firm. '
        'Không rút 80% rồi xóa thêm 20% không hạch toán; không bơm vốn vào tài khoản đang lỗ. '
        'Không có tài khoản funded nên funded policy/payout chỉ được kiểm bằng fixture, chưa có đường thực nghiệm. '
        'Không có tiền thật nhận về, chưa trừ phí mua/retry Challenge hay chi phí vận hành khỏi thu nhập.',
        '',
        'FAQ FTMO kiểm ngày 14/11/2026 cho phép yêu cầu từ ngày 14, account flat, '
        'min20USD bank/card (50USD crypto), mức chia thông thường 2-Step80%. Mô hình giữ mốc 30 ngày '
        'bảo thủ hơn, nhưng bỏ qua chờ xét duyệt/chi trả và giả định reset/new cycle tức thời. '
        'Nguồn: https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/',
        '',
        'Các assumption giữ nguyên: Bid/Ask lịch sử Dukascopy/QDM; vàng100oz/lot, min/step0,01lot; '
        'commission0,0007%notional/side; slippage0,20USD/oz/side; rollover22UTC, thứ Tư×3; '
        'lịch Friday20:30/holiday đã khóa. Đây không phải snapshot đầy đủ của tài khoản đích. '
        'Floating/cash giữ convention Anchor0: fee vào ghi balance, funding đang mở nằm floating, '
        'một leg slip trong floating, hai leg slip quyết toán khi đóng; cổng reserve tính cả hai. '
        'Giá cũ ở Prague reset và giờ nghỉ vẫn là carried mark. Margin/leverage, execution latency, '
        'historical news restrictions, actual swaps và lịch/feed đích chưa xác minh đủ; không được gắn prop_qualified=true.',
        '',
        '## 7. Kiểm chứng, lỗi phát hiện và tái hiện',
        '',
        f"- {tests['tests']} tests hồi quy đạt, gồm21 fixtures mới về exit/protection, fill clock, "
        'scope dữ liệu, rounding, phase risk/throttle, reserve, collision, daily reset, target, payout và censoring.',
        f"- Oracle Fraction độc lập công thức: {parity['rational_cost_bridges']} cost bridges ở risk125/150/175/250USD; "
        f"{parity['parent_paths_checked']} so khớp đường parent qua hai mô hình phí.",
        f"- {parity['lifecycle_accounts']} tài khoản được đối soát bằng sổ khác cách hạch toán: "
        'oracle ghi swap vào cash rồi phục hồi anchor thực hiện; so đúng cash, peak DD, static DD, daily loss và thời điểm breach. '
        f"{parity['native_terminal_checks']} terminal transitions đối chiếu primitive prop_session hiện có.",
        '- Đây là đối soát tính toán do cùng người triển khai, không gọi là review độc lập bởi agent/người khác. Không gửi Astra.',
        '- 108 giờ tick bổ sung được đối chiếu M1 trước outcome, không phát hiện mismatch. '
        'EURUSD half-hour endpoints được seek lại CSV gốc: đủ86/86 và94/94, không dùng giá đầu giờ thay20:30.',
        '- Parity bắt lỗi horizon dùng decision thay observed entry: sửa đồng hồ, giữ outcome trước sửa trong '
        '`clock-correction-attempt`; không thay tín hiệu, SL, chi phí hoặc ngưỡng lựa chọn. '
        'Lỗi E3 thiếu quote được giữ trong `phase1-attempt1`; chặn chọn thay vì bịa giá.',
        '',
        'Tái hiện bằng Python3.12.10, NumPy2.3.5 và dependencies của Trader đã pin. '
        'Nguồn local riêng không đẩy tick/CSV/cache lên GitHub. Các lệnh đã chạy:',
        '',
        '```powershell',
        '$env:PYTHONPATH="D:/ANNAM/TradingWorkspace/projects/trader/foundation_v2;D:/ANNAM/TradingWorkspace/tooling/ai-engines"',
        'python tooling/ai-engines/run_prop_campaign.py phase1',
        'python tooling/ai-engines/run_prop_campaign.py validation',
        'python tooling/ai-engines/prop_campaign_review.py',
        'python -m unittest discover -s tooling/ai-engines/tests -p test_prop_campaign.py',
        '```',
        '',
        f'Private job: `{JOB}`. `registration.json`, `implementation-freeze.json`, '
        '`composition-freeze.json`, `validation-release.json`, source reviews, per-trade paths, '
        '`lifecycle-*.json`, `computational-parity.json` và JSON cạnh báo cáo giữ hashes/locators. '
        'Không chạy lại study chỉ để đọc báo cáo. Source/preparation và những lần sửa clock/coverage '
        'được giữ riêng; thay numeric input/code phải tạo attempt mới, không ghi đè receipt đã đóng.',
        '',
        '## 8. Quyết định sau chiến dịch',
        '',
        '**Gác Challenge với A hiện tại và không tăng risk thêm.** Nút thắt vẫn là tốc độ tích lũy '
        'lợi nhuận và độ bền ngoài các lệnh đuôi lớn; sizing không tạo edge hoặc thêm mẫu độc lập. '
        'Nếu mở đợt nghiên cứu mới, cần một cơ chế có lý do kinh tế khác, khóa cadence/cost/markout trước '
        'và chỉ tiếp tục sau Stage-0; không tiếp tục vặn ba exit hoặc ba sleeve vừa bị loại. '
        'Một nhánh có lợi nhuận trong mẫu là benchmark hữu ích, chưa là nguồn thu nhập chính đã được chứng minh.',
        '',
        'Hậu kiểm engineering: giữ vectorized sufficient statistics vì đã khớp Anchor0 và oracle '
        'dòng tiền khác công thức; không tuyên bố speedup khi chưa có benchmark cùng workload. '
        'Lỗi clock và endpoint được sửa bằng guard/test; chưa có bằng chứng cần engine/framework mới. '
        'Không sửa skill thêm để lặp lại policy vốn đã có.',
        '']
    REPORT.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(str(REPORT.with_suffix('.md')),flush=True)


if __name__=='__main__':build()
