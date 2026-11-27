"""Bounded V22 results: no post-outcome threshold rescue or invented winner."""
from collections import Counter
from datetime import datetime,timezone
import json
from prop_v22_common import *

REPORT=Path('planning/research/EXHAUSTION-H1-ALIGN-V22-RESULTS-20261117')


def table(headers,rows):
    return ['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+[
        '| '+' | '.join(str(v).replace('|',r'\|') for v in r)+' |' for r in rows]


def fmt(v,n=3):
    if v is None:return 'N/A'
    return f'{v:.{n}f}' if isinstance(v,float) else str(v)


def sleeve(row):
    return 'EUR F5' if row['family']=='F5' else 'Gold '+row['family']


def snapshot_table(rows):
    return table(['Ngày UTC','Nhánh/chiều','NetR','Day/ATR D1','Edge gap','Body/ATR H4','Range/ATR H4','Provisional'],[
        [datetime.fromtimestamp(r['entry_msc']/1000,timezone.utc).strftime('%Y-%m-%d %H:%M'),sleeve(r)+' '+r['side'],
         fmt(r['net_R']),fmt(r['day_range_ATR']),fmt(r['edge_distance'],5),fmt(r['signal_body_H4_ATR']),
         fmt(r['signal_range_H4_ATR']),r['source_provisional']] for r in rows])


def report():
    decision=read(JOB/'Development-decision.json');assert decision['selected'] is None
    for path,digest in decision['code_pins'].items():assert sha(path)==digest
    gates=read(JOB/'Dev-gate-results.json');behavior=read(JOB/'H1-behavioral-results.json')
    anatomy=read(JOB/'anatomy-summary.json');tests=read(JOB/'tests-final-matrix.json');smoke=read(JOB/'smoke-final-results.json')
    checker=read(JOB/'preflight-CLI-receipt.json');storage=read(JOB/'storage-final.json');audit=read(JOB/'independent-audit.json')
    assert audit['passed'] and checker['source_sha256']==sha('tooling/ai-engines/ftmo_trial_runner.py')
    parent=read('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')
    devrows=unpack('Dev-OLHC-forensics',V21);snap=unpack('Dev-entry-snapshots');by_key={r['trade_key']:r for r in snap}
    from quant_core.exhaustion_gate import accept
    for g in gates['cases']:
        rejected=[r for r in devrows if not accept(by_key[r['trade_key']],g['gate'],decision['thresholds'])]
        g['rejected_detail']=dict(L3_count=sum(r['label']=='L3' for r in rejected),L3_net_R=sum(r['net_R'] for r in rejected if r['label']=='L3'),
            other_losers_net_R=sum(r['net_R'] for r in rejected if r['net_R']<=0 and r['label']!='L3'),
            winners_count=sum(r['net_R']>0 for r in rejected))
    h1summary={}
    inherited=read('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json')['behavioral']['rows']
    prior_GBP=[r for r in inherited if r['asset']=='GBPUSD']
    for asset in ('GBPUSD','AUDUSD'):
        rows=[r for r in behavior['rows'] if r['asset']==asset]
        h1summary[asset]=dict(cells=len(rows),raw=sum(r['raw'] for r in rows),priced=sum(r['priced'] for r in rows),
            coverage_pct=100*sum(r['priced'] for r in rows)/sum(r['raw'] for r in rows),
            missing=sum(r['raw']-r['priced'] for r in rows),count_is_recipe_observations_not_unique_signals=True,
            Stage0_passed=sum(r['stage0_passed'] for r in rows))
    w=anatomy['top10'];l3=anatomy['L3']
    result=dict(schema='V22-results-v1',decision=decision,anatomy=anatomy,gates=gates,behavioral=behavior,H1_summary=h1summary,
        tests=tests,smoke=smoke,preflight=checker,storage=storage,audit=audit,
        global_top10_sleeves=dict(Counter(sleeve(r) for r in w)),
        Dev_top10_sleeves=dict(Counter(sleeve(r) for r in anatomy['Dev_top10'])),
        baseline_history=parent['historical'],baseline_MC=[v for v in parent['monte'] if v['mode']=='PRIMARY' and v['friction']==100],
        baseline_reused_not_new_V22_validation=True,prop_qualified=False,actual_broker_orders=0,actual_payout_USD=0,
        new_Full_child_backtests=0,new_historical_accounts=0,new_MC_paths=0,
        source_bindings={name:sha(path) for name,path in (
            ('baseline_report',Path('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')),
            ('V21_report',Path('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json')),
            ('protocol',PROTOCOL),('freeze',FREEZE))},
        limits=['L3 is retrospective: its outcome/MFE cannot be known at entry.',
            'Global top10 and later historical evidence already exposed; not clean OOS.',
            'Tail retention alone is not promotion, and one BE failure does not disprove all trailing exits.',
            'ATR is a scale estimate, not a remaining daily movement budget.',
            'M1 Ask/order/source-calendar proxies remain; source gaps not repaired.',
            'H1 exact grid alignment does not certify quote/tick completeness or intrahour stop/DD.',
            'H1 clamp changes the registered exit policy; V21 results are preserved separately.',
            'Zero modeled same-day swap does not imply zero live fees or blanket FTMO compliance.',
            'Preflight last ping is terminal-reported, not new RTT; no terminal present so live attach unverified.',
            'Independent arithmetic is same author/feed, not independent human review.',
            'Storage inventories are logical, non-atomic and include unrelated activity.'])
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if len(text.encode())>1048576:raise ValueError('V22 bounded JSON exceeded1MiB')
    REPORT.with_suffix('.json').write_text(text,encoding='utf-8',newline='\n')
    base=gates['cases'][0]['cases'][0];lines=['# V22 — cổng exhaustion, H1 20:00 và MT5 preflight','',
        '**Hai cổng G_L3 đều rớt Development; H120:00 khôi phục phần lớn endpoint nhưng chưa có breadth booster đủ điều kiện. '
        'Giữ V16/V19 BASE_GUARD, chưa đủ căn cứ mua Challenge.**','',
        'PR100/head `1118904` merge `ec0cbe7`, nhánh V21 đã xóa. Protocol `98dd4ec`, '
        'implementation `5236af1`, Dev freeze `f0b823a` trước Full anatomy; PR101 để mở. '
        'Giữ source/freezes/negative attempts, Trader pin và VI WIP; không broker/account/provider/deploy/Astra/memory.','',
        '## 1. Top10 so với L3: giữ siêu lệnh vẫn chưa đủ','',
        'Global top10 có **9 EURUSD F5 và1 Gold F4**; Dev-only top10 có **8 EURUSD F5 và2 Gold F4**. '
        'G_L3 chỉ chặn F3/F4 nên phần lớn siêu lệnh EUR được giữ sẵn theo scope. '
        'Không có Gold F3 trong hai danh sách top10 này; không suy rằng F3 sẽ không có tail lớn trong tương lai.','',
        'Các tỷ lệ dùng high/low ngàyUTC từ M1 đóng trước decision và D1 Wilder ATR14 đã đóng. '
        'Signal F4 dùng H1, F3/F5 dùng H4; mẫu số Body/Range là ATR H4 đã biết. Edge gap là khoảng '
        'từ executable entry đến biên cùng chiều của ngày: GoldUSD/oz, FX tỷ giá; số âm có thể là entry vượt biên cũ, '
        'không phải dư địa lợi nhuận bảo đảm. Source/context vẫn có assumptions.','',
        '### Global top10 đã exposed từ V21 (chỉ anatomy sau freeze)','']
    lines+=snapshot_table(w)
    lines+=['','### Top10 riêng Development dùng cho cửa giữ>=90%','']+snapshot_table(anatomy['Dev_top10'])
    lines+=['','### Tất cả45 L3, tách giai đoạn','']
    for label,early in (('Development2018–2023',True),('Lịch sử2024–2026YTD đã exposed',False)):
        rows=[r for r in l3 if (r['year']<=2023)==early]
        lines+=['',f'**{label}: {len(rows)} lệnh / {sum(r["net_R"] for r in rows):.3f}R.**','']+snapshot_table(rows)
    lines+=['','L3 đòi cả net<=0 và MFE<0,25R sau entry, nên việc L3 có Day/ATR cao là một phần định nghĩa đã chọn. '
        'Phân bố L3-vs-winner không là bằng chứng độc lập rằng tỷ lệ này dự báo loss. '
        'L3 cũng không phải pool lỗ lớn nhất: L4 ở V21 đóng góp−99,86R.','',
        '### Hai biến thể tiên nghiệm, khóa trước outcome','',
        '- A: F3/F4, chặn Day/ATR>0,90; F5 giữ nguyên.',
        '- B: F3/F4, chặn vượt phân vị90% Dev theo sleeve: F3='+fmt(decision['thresholds'][next(k for k in decision['thresholds'] if '|F3:' in k)])+
        ', F4='+fmt(decision['thresholds'][next(k for k in decision['thresholds'] if '|F4:' in k)])+'. Fit chỉ covariates, không labels/returns.',
        '- Giữ>=9/10 Dev top10, tăng net/ExTop10, giảm equityDD, worst daily không tăng. Không chỉnh SL/exit/risk.','']
    lines+=table(['Dev OLHC','Lệnh','NetR','EquityDD R','Worst day%','ExTop5 R','ExTop10 R','DevTop10 giữ'],[
        ['BASE_GUARD',340,fmt(base['base']['net_R']),fmt(base['base']['equity_R_DD']),fmt(base['base']['worst_daily_pct']),
         fmt(base['base_concentration']['without_top5']),fmt(base['base_concentration']['without_top10']),'10/10']]+[
        [g['gate'],g['cases'][0]['trades'],fmt(g['cases'][0]['candidate']['net_R']),fmt(g['cases'][0]['candidate']['equity_R_DD']),
         fmt(g['cases'][0]['candidate']['worst_daily_pct']),fmt(g['cases'][0]['concentration']['without_top5']),
         fmt(g['cases'][0]['concentration']['without_top10']),str(g['cases'][0]['top10_retained'])+'/10'] for g in gates['cases']])
    lines+=['','Equity metrics là fixed150USD marked book, không adaptive-account Daily DD. Cả hai M1 orderings '
        'cùng verdict. ExTop10 loại từng candidate own top10; JSON còn cột loại original baseline top10 identities.','']
    lines+=table(['Gate','Bỏ lệnh','Bỏ winners','WinnerR mất','LoserR tránh','Trong đó L3','Lý do rớt'],[
        [g['gate'],g['cases'][0]['rejected_trades'],g['cases'][0]['rejected_winners'],fmt(g['cases'][0]['rejected_winner_R']),
         fmt(g['cases'][0]['rejected_loser_R']),f"{g['rejected_detail']['L3_count']} / {g['rejected_detail']['L3_net_R']:.3f}R",'; '.join(g['cases'][0]['reasons'])] for g in gates['cases']])
    lines+=['','A chặn được toàn27 L3 Dev nhưng đồng thời bỏ các lệnh thắng; giữ10 siêu lệnh vẫn làm phần nền yếu hơn. '
        'B cũng bỏ winner nhiều hơn loss tránh được. **Không chọn ngưỡng thứ ba**, không dùng body/edge của bảng Full '
        'để cứu hai gates. Target−20,73R là pool hindsight toàn kỳ, không là khoản thu hồi được biết trước.','',
        '## 2. H1 20:00: hết lệch lưới, chưa hết missing hoặc economic failure','',
        'Đã reuse22 M1 cases không đổi, tính lại6 GBP B2, thêm6 AUD B2 riêng:34 cases báo cáo, '
        '12 cases mới đo. B3 giữ4 Gold/US500 cases; không tự thêm B3 FX để đổi budget. '
        'Threshold sweep/ATR/side/stop không đổi. H1 cut=floor_hour(min20:30, early guard), thường20:00; '
        'M1 vẫn20:30 và US500/session clamp cũ. H1 fills dùng observed opens đúng boundary, '
        'không forward-fill hoặc chọn last quote trước gap. Đây là exit-policy mới có registration, không sửa V21.','']
    lines+=table(['Asset (cộng recipe observations)','Raw','Có endpoint','Coverage%','Missing','Stage0'],[
        [a,r['raw'],r['priced'],fmt(r['coverage_pct']),r['missing'],r['Stage0_passed']] for a,r in h1summary.items()])
    lines+=['',f"Các recipe có tín hiệu chồng nhau nên bảng này không đếm unique trades. GBP V21 chỉ{sum(r['priced'] for r in prior_GBP)}/{sum(r['raw'] for r in prior_GBP)} "
        f"recipe observations được định giá ở mốc cũ; V22 có{h1summary['GBPUSD']['priced']}/{h1summary['GBPUSD']['raw']}, vẫn{h1summary['GBPUSD']['missing']} missing. "
        'Giờ đúng lưới không đồng nghĩa100% dữ liệu hoặc an toàn tuyệt đối.','']
    lines+=table(['Asset / recipe','Raw/priced','Cost đủ%','2018 pip','2019','2020','2021','2022','2023'],[
        [r['asset']+' / '+r['recipe'],f"{r['raw']}/{r['priced']}",fmt(r['cost_only_retention']*100,1)]+[
            fmt(a['mean_net_units']*10000,2) if a['mean_net_units'] is not None else 'N/A' for a in r['annual']]
        for r in behavior['rows'] if r['asset'] in ('GBPUSD','AUDUSD')])
    lines+=['','Cột từng năm là mean raw net stress/trade theo pip, chưa SL-Active. FX model gồm Bid/Ask đã chứa spread, '
        'commission7USD/lot và slippage2USD/lot roundtrip; modeled swap0 vì same-day. Cost-only retention '
        'tách coverage; không gọi missing net0. Tất cả12 H1 recipes đều có ít nhất một năm âm; '
        'các biên dương lớn riêng năm2022 không được dùng để chọn subgroup. **0/34 qua đủ Stage-0**. '
        'Không chạy SL-Active cho losers; nguồn H1 cũng chưa đủ intrahour equity/DD.', '',
        '## 3. Không có child đi tiếp: lifecycle baseline reuse','',
        'Dev freeze có selected=null trước Full entry snapshots. Không chạy mới child trên2024–2026, '
        'không105 monthly starts/5.000 bootstrap child. Full chỉ bảng anatomy baseline. Sau đây là receipts lịch sử '
        'V16/V19 đã có, không phải kết quả mới V22; monthly starts overlap, median có điều kiện chỉ nhóm hoàn tất.','']
    hist=[r for r in parent['historical'] if r['order']=='OLHC' and r['mode']=='PRIMARY' and r['friction_pct']==100]
    lines+=table(['Baseline','Hai vòng/105','Median tháng','Daily%','Static%'],[[r['version'],r['funded'],fmt(r['median_months']),fmt(r['worst_daily']),fmt(r['worst_static'])] for r in hist])
    lines+=['']+table(['MC OLHC PRIMARY100 /5.000','Hai vòng24 tháng%','Hai vòng36 tháng%'],[
        [r['version'],fmt(next(h['both_pct'] for h in r['horizons'] if h['months']==24)),fmt(next(h['both_pct'] for h in r['horizons'] if h['months']==36))]
        for r in result['baseline_MC'] if r['order']=='OLHC'])
    lines+=['','Bootstrap frequencies không là xác suất tương lai; source/cost stress và32 paths chưa xác minh còn nguyên. '
        'Không kết luận đã giải quyết time-fit hoặc đủ payout. Giữ baseline thay vì ép một winner.', '',
        '## 4. MT5 preflight, hiệu năng và storage','',
        'Lệnh mới: `python -m tooling.ai_engines.ftmo_trial_runner --check-mt5-ready` '
        '(dùng observer runtime trong quickstart). Output private MT5_PREFLIGHT.json; exit2 khi chưa sẵn sàng, '
        'không fallback replay trong diagnostic này. Kiểm đã thấy terminal trước initialize, FTMO DEMO/TRIAL USD, '
        'connected, last reported pingµs→ms, symbol info/quote age. Không symbol_select/login/order_check/order_send.','',
        f"Máy hiện có **{checker['result']['terminals_seen']} terminal**; verdict `{checker['result']['reason']}`. "
        f"Probe {checker['result']['probe_wall_ms']:.1f}ms; whole fresh CLI **{checker['whole_process_wall_seconds']:.3f}s**, "
        f"target1s:{checker['whole_process_under1']}. Đây chỉ ca không có terminal; attach/network live chưa kiểm. "
        'Không bịa ping, không coi terminal-reported ping là RTT mới; shadow vẫn cần session/news/seeds/spec parity.', '',
        f"Full suite **{tests['tests']} PASS/0skip**, giữ1.261 V21 IDs; wall **{tests['total_wall_seconds']:.3f}s**. "
        f"Hard<=13,5s:{tests['target_under135']}; stretch<13,2s:{tests['stretch_under132']}.", '',
        f"Smoke10 fresh serial processes/same78 IDs: **{smoke['below075']}/10 <0,75s**, "
        f"stretch<0,72s:{smoke['below072']}/10; median **{smoke['median']:.3f}s**, max **{smoke['max']:.6f}s**. "
        'Giữ tất cả mẫu, không retry streak; startup/import/fixture IO nằm trong wall. Stretch không tự gắn PASS khi thiếu dù chỉ0,1ms.', '',
        f"{storage['compressed_tables']} tables Zstd9: {storage['original_bytes']:,}→{storage['compressed_bytes']:,} bytes, "
        f"SHA256/roundtrip mọi bảng. Job riêng {storage['own_job_bytes']/2**20:.2f}MiB tại inventory, không cache giá mới/xóa nguồn. "
        'Small reports/freeze trong Git; audit/feed source vẫn read-only.', '']
    lines+=table(['Kho logical','V21 baseline GiB','Sau GiB','DeltaGiB','Errors'],[[k,fmt(v['before']['bytes']/2**30),fmt(v['after']['bytes']/2**30),fmt(v['delta_bytes']/2**30),len(v['after_errors'])] for k,v in storage['roots'].items()])
    lines+=['','Non-atomic inventories có thể gồm hoạt động khác; không gọi delta là physical bytes freed. '
        'D giữ2 read errors VI, không thay quyền/WIP. Audit riêng kiểm retained identities, Decimal cash, '
        'Dev/Full covariate parity,22 M1 results reuse,12 H1 source endpoints/net legs và every compressed hash. '
        'Cùng tác giả/feed, không independent human review.', '',
        '| Hậu kiểm | Quyết định |','|---|---|',
        '| Giữ top10 nhưng net/DD tệ hơn | Bác cả A/B; top-tail retention là điều kiện cần, chưa đủ |',
        '| H1 giờ lẻ làm mất endpoint | Clamp20:00 có đăng ký, giữ missing thật; không tạo M1 giả |',
        '| MT5 preflight dễ bị hiểu là execution-ready | Tách read-only readiness, live attach unknown, shadow vẫn gated |',
        '| Smoke stretch hụt sát ngưỡng | Giữ exact sample và verdict; không rerun chọn streak |', '',
        'PR101 để mở; three exact-head CI và downloaded IDs chốt sau push trong private '
        '`ci-exact-head-reconciliation.json` / `completion-receipt.json`. Chưa broker orders hoặc payout thật.', '',
        '[Protocol](EXHAUSTION-H1-ALIGN-V22-PROTOCOL-20261117.md) · [Freeze](EXHAUSTION-H1-ALIGN-V22-FREEZE-20261117.json) · '
        '[JSON](EXHAUSTION-H1-ALIGN-V22-RESULTS-20261117.json) · [Quickstart](QUICKSTART-FTMO-FREE-TRIAL.md)', '',
        'Primary docs: [MQL5 Python initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py), '
        '[terminal information](https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py), '
        '[FTMO holding rules](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/). '
        'Các nguồn không thay account-specific snapshot/session/news còn thiếu.', '']
    REPORT.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    event('V22_report_written',bytes=len(text.encode()),selected=None)


if __name__=='__main__':report()
