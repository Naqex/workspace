"""Bounded V21 audit/report, keeping missing evidence and unsuccessful trials."""
from collections import Counter
import json
import numpy as np
from prop_v21_common import *
from quant_core.trade_forensics_classifier import summarize,LABELS

REPORT=Path('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117')


def audit():
    from prop_v15_accounts import exact_quantity
    from independent_ledger_auditor import v14_parts
    from prop_v21_forensics import Context
    for p,digest in read(JOB/'Development-decision.json')['final_forensics_code'].items():
        assert sha(p)==digest,'Frozen forensics code drift'
    all_checks=[]
    for dev in (True,False):
        scope='Dev' if dev else 'Full';context=Context(dev)
        for tag in ('OLHC','OHLC'):
            rows=unpack(f'{scope}-{tag}-forensics');trades=read(V19/f'{scope}-{tag}-PRIMARY-trades.json')
            assert len(rows)==len(trades)==(340 if dev else 494)
            assert len({r['trade_key'] for r in rows})==len(rows)
            for r,t in zip(rows,trades):
                assert r['id']==t['id'] and r['entry_msc']==t['entry_msc']
                q=exact_quantity(t,150);cash=v14_parts(t,q,'SYM_FLAT')['net']/150000
                assert abs(r['net_R']-cash)<1e-10
                # Separate direct extrema calculation, with the stop minute
                # truncated at the actual modeled fill, not its later wick.
                prices=context.reader(t['asset'],tag).points(t['entry_msc'],t['exit_msc'])
                px=prices['b' if t['side']=='BUY' else 'a'].astype(float)
                sign=1 if t['side']=='BUY' else -1
                path=sign*(np.r_[px,t['exit_price_units']]-t['entry_price_units'])/abs(t['entry_price_units']-t['stop_units'])
                assert abs(r['MFE_R']-max(0,float(path.max())))<1e-10
                assert abs(r['MAE_R']-max(0,float(-path.min())))<1e-10
            all_checks.append(dict(scope=scope,order=tag,trades=len(rows),separate_cash_and_extrema_verified=True))
    full=read(JOB/'Full-forensics-summary.json')
    parent=read('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')
    net=next(v['reference_net_R'] for v in parent['reference_economics'] if v['version']=='V19' and v['source']=='PRIMARY' and v['friction']==100)
    assert abs(full['OLHC']['total']['net_R']-net)<1e-10
    # Check every compressed table, including corrected and original trials.
    import zstandard as zstd,hashlib
    n=0
    for manifest in JOB.rglob('*-manifest.json'):
        m=read(manifest);p=manifest.parent/m['file'];raw=zstd.ZstdDecompressor().decompress(p.read_bytes())
        assert sha(p)==m['compressed_sha256'] and len(raw)==m['original_bytes'] and hashlib.sha256(raw).hexdigest()==m['original_sha256'];n+=1
    save('forensics-independent-arithmetic-audit.json',dict(passed=True,cases=all_checks,compressed_tables=n,
        canonical_net_R=net,same_author_and_feed=True,independent_human_review=False))
    event('V21_audit_complete',trades=sum(r['trades'] for r in all_checks),compressed_tables=n)


def table(head,rows):
    return ['| '+' | '.join(head)+' |','|'+'|'.join('---' for _ in head)+'|']+[
        '| '+' | '.join(str(v).replace('|',r'\|') for v in r)+' |' for r in rows]


def admission_report(behavior):
    """Separate cost acceptance from endpoint availability using saved Dev arrays."""
    import zstandard as zstd
    checks=[]
    for r in behavior['rows']:
        folder=JOB if r['family']=='B3' else JOB/'behavioral-corrected-v2'
        name=r['asset']+'-'+r['recipe'].replace(':','_')+'-raw'
        manifest=read(folder/(name+'-manifest.json'));p=folder/manifest['file']
        assert sha(p)==manifest['compressed_sha256']
        m=json.loads(zstd.ZstdDecompressor().decompress(p.read_bytes()))
        count=sum(v<=.12 for v in m['ratio']);retention=count/r['raw'] if r['raw'] else 0.
        r['cost_eligible']=count;r['cost_only_retention']=retention
        r['priced_and_cost_retention']=r['retention']
        # Original scanner's retention mixed coverage and cost acceptance.
        # Correct the publication, retain original receipts and reject flags
        # from every other gate. No quote replay or threshold change occurs.
        r['reasons']=[v for v in r['reasons'] if v!='RETENTION_BELOW50' or retention<.5]
        corrected=not r['reasons']
        assert corrected==r['stage0_passed'],'Admission correction changes frozen selection'
        checks.append(dict(asset=r['asset'],recipe=r['recipe'],source_manifest_sha256=sha(folder/(name+'-manifest.json')),
            cost_eligible=count,priced_and_cost_eligible=r['retained'],frozen_verdict_unchanged=True))
    receipt=dict(passed=True,reason='Publication separates Friction/SL acceptance from missing endpoints; original scanner retention combined both.',
        cases=checks,no_quotes_replayed=True,no_thresholds_changed=True,all_frozen_verdicts_unchanged=True)
    p=JOB/'admission-cost-vs-coverage-reconciliation.json'
    if not p.exists():save(p.name,receipt)
    else:assert read(p)==receipt
    return behavior


def short_reason(r):
    if r['asset']=='GBPUSD':return 'Thiếu endpoint20:30/M1; chưa đủ dữ liệu kết luận kinh tế'
    years=[str(a['year']) for a in r['annual'] if a['mean_net_units'] is None or a['mean_net_units']<=0]
    tags=['âm/thiếu: '+','.join(years)] if years else []
    if any('MARKOUT_NOT_ABOVE_FRICTION' in s for s in r['reasons']):tags.append('biên net chưa vượt phí')
    for key,label in (('SCALE_FAIL','SL nhỏ so phí'),('RETENTION_BELOW50','giữ<50% vì phí'),('CADENCE_BELOW40','thưa'),('ENDPOINT_INCOMPLETE','thiếu endpoint')):
        if key in r['reasons']:tags.append(label)
    return '; '.join(tags)


def report():
    dev=read(JOB/'Dev-forensics-summary.json');full=read(JOB/'Full-forensics-summary.json')
    b1=read(JOB/'B1-result.json');behavior=admission_report(read(JOB/'behavioral-corrected-v2/behavioral-results.json'))
    decision=read(JOB/'Development-decision.json');assert decision['selected'] is None
    rows=unpack('Full-OLHC-forensics');other=unpack('Full-OHLC-forensics')
    cross={}
    for identity in sorted({r['id'] for r in rows}):
        for label,early in (('2018-2023',True),('2024-2026YTD',False)):
            cross[identity+' / '+label]=summarize([r for r in rows if r['id']==identity and (r['year']<=2023)==early])
    delta=[];parents=unpack('Dev-OLHC-forensics');children=unpack('B1-OLHC-forensics');lookup={r['trade_key']:r for r in parents}
    for r in children:
        p=lookup[r['trade_key']]
        if p['exit_msc']!=r['exit_msc']:delta.append(dict(trade_key=r['trade_key'],parent_R=p['net_R'],child_R=r['net_R'],delta_R=r['net_R']-p['net_R']))
    parent=read('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json')
    result=dict(schema='V21-results-v1',decision=decision,prop_qualified=False,actual_broker_orders=0,
        actual_payout_USD=0,Dev=dev,Full=full,sleeve_period=cross,B1=b1,behavioral=behavior,
        B1_changes=dict(count=len(delta),improvement_R=sum(r['delta_R'] for r in delta if r['delta_R']>0),
            deterioration_R=sum(r['delta_R'] for r in delta if r['delta_R']<0)),
        taxonomy_order_disagreements=sum(a['label']!=b['label'] for a,b in zip(rows,other)),
        open_path_unknown=sum(r['open_path_unknown'] for r in rows),
        post_path_unknown_SL=sum(r['post_path_unknown'] and r['reason']=='SL' for r in rows),
        post_stop_2R=sum(r['reason']=='SL' and r['post_MFE_R']>=2 for r in rows),
        W2_flags={k:dict(count=sum(r['label']=='W2' and r['flags'][k] for r in rows),net_R=sum(r['net_R'] for r in rows if r['label']=='W2' and r['flags'][k])) for k in ('near_death','late_windfall','open_path_unknown')},
        giveback_by_mode_and_bucket={mode:{bucket:dict(count=sum(r['mode']==mode and r['net_R']<=0 and r['giveback_bucket']==bucket for r in rows),
            net_R=sum(r['net_R'] for r in rows if r['mode']==mode and r['net_R']<=0 and r['giveback_bucket']==bucket)) for bucket in ('0.80–<1.00','1.00–<1.50','>=1.50')} for mode in ('P0','P1')},
        audit=read(JOB/'forensics-independent-arithmetic-audit.json'),tests=read(JOB/'tests-final-matrix.json'),
        smoke=read(JOB/'smoke-final-results.json'),storage=read(JOB/'storage-final.json'),
        baseline_history=parent['historical'],baseline_monte=[r for r in parent['monte'] if r['mode']=='PRIMARY' and r['friction']==100],
        baseline_reused_not_new_V21_simulation=True,new_accounts=0,new_MC_paths=0,
        limits=['Labels describe modeled price geometry, not true skill/luck or manipulation.',
            '32 open paths remain source-uncertain; post-stop uncertainty adds provisional labels.',
            'M1 orderings, proxy Ask and inherited cost/calendar scenarios are not broker fills.',
            'ATR/day ranges derived from admitted M1; historical context/feed/news not independently certified.',
            'Later history already exposed; no clean OOS or new prospective validation.',
            'GBP primary20:30 endpoint mostly unavailable in H1-only source; no economic family rejection from missing data.',
            'One registered B1 diagnostic; no additional anti-exhaustion variant or wider-stop search.',
            'Original dual-sweep bug attempt retained;24 B2 corrections,4 B3 results reused; no thresholds retuned.',
            'Fixed150 marked path is not an adaptive Challenge account. Tail removal is descriptive only.'])
    raw=json.dumps(result,ensure_ascii=False,indent=2)
    if len(raw.encode())>1048576:raise ValueError('Bounded report exceeds1MiB')
    REPORT.with_suffix('.json').write_text(raw,encoding='utf-8',newline='\n')
    total=full['OLHC']['total'];conc=full['OLHC']['concentration'];f=lambda v:f'{v:.3f}' if isinstance(v,float) else str(v)
    lines=['# V21 — giải phẫu494 lệnh và kiểm định hành vi','',
        '**Không có ứng viên V21 vượt Development; giữ V16/V19 BASE_GUARD, chưa đủ điều kiện Challenge.**',
        '', 'PR99/head `c9075fb` merge `a2d9c86`, nhánh V20 đã xóa. Protocol `ed96cc0`, implementation `b20fdde`, '
        'correction `9986876`, freeze Dev `ec26e5c` trước Full taxonomy. PR100 để mở; giữ Trader pin/VI WIP/nguồn/freezes/negatives.',
        '', '## 1. Sáu nhóm lệnh — mô tả đường giá, chưa chứng minh skill/luck',
        '', 'Canonical book là V19 PRIMARY stress SYM, fixed150USD với lot floor. V16 có cùng494 signals '
        'nhưng hai timeout exits khác; V16 +42,30347R, V19 +42,39167R. Không trộn hai sổ. '
        'MFE/MAE chia natural SL, NetR chia150USD. W1/W2 tên theo yêu cầu; không suy tác nhân/quỹ/retail từ OHLC.', '']
    lines+=table(['Nhãn','Số lệnh','%494','NetR đóng góp','Provisional'],[[r['label'],r['count'],f(r['pct']),f(r['net_R']),r['provisional']] for r in total['groups']])
    lines+=['',f"494/494 rows có nhãn; **{total['provisional']} nhãn provisional**, gồm32 open paths thiếu và các post-stop/context chưa đủ. "
        f"Hai ordering khác nhãn ở{result['taxonomy_order_disagreements']} lệnh; cùng kết quả OHLC không chứng minh đúng tick thực.",
        '', 'Ưu tiên W2 trước W1; với loss ưu tiên L1>L2>L3>L4. Flags vẫn giữ chồng lấn: '
        f"L2 thực có{total['overlapping_loss_flags']['L2']['count']} lệnh/{f(total['overlapping_loss_flags']['L2']['loss_R'])}R lỗ, khác hàng L2 độc quyền. "
        f"Có{total['overlapping_loss_flags']['L1']['count']} stop rồi hồi>=1R, trong đó{result['post_stop_2R']} hồi>=2R. "
        'Đây là cơ hội sau khi đã thua, không chứng minh rộng SL hoặc vào lại sẽ có lãi.', '',
        f"Bỏ top5 winner: **{conc['without_top5']:.3f}R**; bỏ top10: **{conc['without_top10']:.3f}R**. "
        'Lợi nhuận phụ thuộc đuôi phải. Trend/range strategies có thể cần đuôi phải; điều này chưa tự chứng minh may mắn hoặc lý do xóa các lệnh đó.', '',
        'W2 flags có thể chồng nhau: '+str(result['W2_flags']), '',
        '### Tách theo nhánh và giai đoạn', '']
    for key,s in cross.items():
        lines+=['',f'**{key}** — {s["trades"]} lệnh / {s["net_R"]:.3f}R.','']
        lines+=table(['Nhãn','Lệnh','% nhóm','NetR','Provisional'],[[r['label'],r['count'],f(r['pct']),f(r['net_R']),r['provisional']] for r in s['groups']])
    lines+=['','Giveback theo mode / MFE trước thoát (bảng chồng flags, không cộng lại với sáu nhóm):','']
    lines+=table(['Mode','MFE band','Lệnh','NetR'],[[mode,bucket,r['count'],f(r['net_R'])] for mode,bs in result['giveback_by_mode_and_bucket'].items() for bucket,r in bs.items()])
    lines+=['','## 2. B1–B3: ngân sách và kết quả Development','',
        '29 recipes logic:1 B1 +24 B2 +4 B3. B1 chỉ dùng Dev taxonomy; L2 loss13,492R > L3 loss10,858R nên '
        'chọn thêm bảo vệ net hòa vốn sau net+1R trên P0, active từ M1 kế tiếp; giữ F4 P1. Không thử thêm exhaustion gate sau kết quả.', '']
    lines+=table(['B1 OLHC','Baseline','Child'],[[k,f(b1['cases'][0]['base'][k]),f(b1['cases'][0]['child'][k])] for k in ('net_R','equity_R_DD','worst_daily_pct','Calmar')])
    lines+=['',f"W1/all giảm từ{dev['OLHC']['total']['W1_share']*100:.2f}% xuống{b1['cases'][0]['taxonomy']['W1_share']*100:.2f}%. "
        f"{len(delta)} exits đổi; cải thiện ở nhóm được lợi+{result['B1_changes']['improvement_R']:.3f}R, "
        f"thiệt hại ở nhóm bị cắt sớm{result['B1_changes']['deterioration_R']:.3f}R. "
        'DD/Calmar cải thiện nhưng net/W1 không đạt; cả hai orderings bị bác. Fixed150 marked equity, không là Daily DD của adaptive account.', '',
        '28 B2/B3 raw screens: **0 Stage-0 survivors**. Raw net phải dương từng năm, vượt ma sát cùng đơn vị, '
        'dual-positive, scale<=12%, retention>=50%, cadence>=40/năm. Không viết thêm SL/TP hoặc chạy validation để cứu losers.', '']
    lines+=table(['Asset','Recipe','Raw/6năm','ĐủF/R / cógiá+F/R','Median natural','F/SL median','Lý do'],[
        [r['asset'],r['recipe'],r['raw'],f"{r['cost_eligible']} / {r['retained']}",f(r['median_natural']),f(r['scale_ratio']),short_reason(r)] for r in behavior['rows']])
    lines+=['', 'Chi tiết từng năm/raw/priced/net units trong JSON và các raw Zstd tables. Gold đơn vịUSD/oz, FX là giá tỷ giá, US500 points; '
        'không so trực tiếp tổng unit khác asset. GBP chỉ có pairedH1; thiếu endpoint20:30 nên giữ DATA_PATH_INCOMPLETE, '
        'không gọi mean missing là thua hay phí0. Một vài endpoint early-guard có giá không đại diện cả kỳ.', '',
        'Audit publication tách cost-only retention khỏi priced+cost retention: scanner đầu gộp cả hai vào trường retention. '
        'Đã đối chiếu28 raw arrays đã lưu, sửa cột lý do/giữ mẫu do phí; cả28 verdict không đổi. Receipt '
        '`admission-cost-vs-coverage-reconciliation.json` giữ nguồn và delta; không replay quotes hoặc đổi ngưỡng.', '',
        'Self-review phát hiện B2 hai-sided sweep: phải abstain trước khi áp close-direction, thay vì kiểm hai directional triggers '
        'vốn không thể cùng true. Giữ attempt đầu, registration sửa trước đo lại24 B2;4 B3 không đổi được reuse. '
        '53 cell evaluations thực tế gồm29 đầu +24 sửa lỗi, không giấu exposure hoặc biến thành53 hypotheses độc lập.', '',
        '## 3. Quyết định và lifecycle','',
        'Không có child qua Dev nên **không mở backtest V21 mới trên2024–2026, không chạy105 starts/5.000 bootstrap mới**. '
        'Chỉ Full taxonomy của baseline được mở sau freeze. Dùng lại baseline history/MC có binding từ V19 để đối chiếu; '
        'các cửa sổ overlap, bootstrap là resampling frequency, không là xác suất tương lai.', '']
    hist=[r for r in parent['historical'] if r['order']=='OLHC' and r['mode']=='PRIMARY' and r['friction_pct']==100]
    lines+=table(['Baseline đã có','Hai vòng/105','Median tháng có điều kiện','Worst daily%','Worst static%'],[[r['version'],r['funded'],f(r['median_months']),f(r['worst_daily']),f(r['worst_static'])] for r in hist])
    lines+=['']+table(['Baseline MC OLHC /5.000','Hai vòng12/18/24/36%'],[[r['version'],' / '.join(f(h['both_pct']) for h in r['horizons'])] for r in result['baseline_monte'] if r['order']=='OLHC'])
    lines+=['', 'Bước tiếp có ích là prospective account/feed reconciliation hoặc một giả thuyết mới có nguồn/cơ chế rõ và budget riêng. '
        'Không có căn cứ từ V21 để tăng risk, bỏ SL hay mua Challenge.', '',
        '## 4. Engineering, storage và bàn giao','',
        f"**{result['tests']['tests']} tests PASS/0skip**, giữ đủ1.239 V20 IDs; full wall{result['tests']['total_wall_seconds']:.3f}s. "
        f"Target<15s:{result['tests']['target_under15']}; stretch<14s:{result['tests']['stretch_under14']}.", '',
        f"Smoke đúng10 fresh serial processes/cùng78 IDs: {result['smoke']['below078']}/10 <0,78s; "
        f"{result['smoke']['below070']}/10 <0,70s; median{result['smoke']['median']:.3f}s, max{result['smoke']['max']:.3f}s. "
        'Startup/import/disk fixture IO nằm trong timer; giữ outliers, không retry chọn streak.', '',
        f"{result['storage']['compressed_tables']} bảng Zstd9: {result['storage']['original_table_bytes']:,} → "
        f"{result['storage']['compressed_table_bytes']:,} bytes; SHA/roundtrip mọi bảng, giữ cả attempt lỗi. "
        f"Job riêng khoảng{result['storage']['own_job_bytes']/2**20:.2f}MiB tại snapshot. Không tạo price cache mới/xóa nguồn.", '']
    lines+=table(['Kho logical','V20 baseline GiB','Sau GiB','Delta GiB','Read errors'],[[k,f(v['before']['bytes']/2**30),f(v['after']['bytes']/2**30),f(v['delta_bytes']/2**30),len(v['after_errors'])] for k,v in result['storage']['roots'].items()])
    lines+=['','Baseline inventory tái dùng snapshot cuốiV20; non-atomic, có thể gồm hoạt động khác. Không là physical free bytes. '
        'D giữ hai lỗi đọc VI; không sửa quyền hoặc WIP của dự án đó.', '',
        'Audit riêng arithmetic cash/extrema đủ340 Dev +494 Full ở hai ordering; cùng tác giả/feed, chưa independent human review. '
        'Tests gồm stop-minute truncation, post-stop side/time, unknown/provisional, overlap, DST, nonempty causal prefix, '
        'dual-sweep abstention, early protection next-minute và gate DD. Skill/workflow hiện có đủ bao phủ; không tạo policy/skill mới từ nhãn hồi tố.', '',
        'PR100 để mở; exact-head3CI và downloaded test IDs chốt trong private `ci-exact-head-reconciliation.json`/`completion-receipt.json` '
        'sau push. Không broker orders/account/login/provider/deploy/Astra/memory updates.', '',
        '[Protocol](TRADE-FORENSICS-BEHAVIORAL-V21-PROTOCOL-20261117.md) · '
        '[Freeze](TRADE-FORENSICS-BEHAVIORAL-V21-FREEZE-20261117.json) · '
        '[JSON](TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json)', '',
        'Research primary: [NY Fed stop cascades](https://www.newyorkfed.org/research/staff_reports/sr150.html), '
        '[Bank of Canada fixing returns](https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/), '
        '[LSEG WMR clock](https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks). '
        'Các nguồn hỗ trợ nghiên cứu cơ chế; không chứng minh các recipe này có edge.', '']
    REPORT.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    event('V21_report_written',bytes=len(raw.encode()),decision=decision['decision'])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('audit','report'));a=p.parse_args();globals()[a.stage]()
