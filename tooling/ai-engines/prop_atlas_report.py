"""Single owner report joining V2 diagnostics, atlas and account results."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from statistics import median
from prop_atlas_core import JOB,V1,PARENT
from prop_campaign_source import read,write_json,digest,DAY
from prop_campaign_report import aggregate,compact,date_text

OUT=Path('planning/research/PROP-ATLAS-V2-RESULTS-20261114')


def build():
    d=read(JOB/'phase0-diagnostic.json');core=read(JOB/'core-comparison.json')
    f=read(JOB/'composition-freeze.json');atlas=read(JOB/'atlas-stage0.json')
    old0=read(PARENT/'attempt-2/result.json')
    annual={m:read(JOB/f'annual-{m}.json') for m in ('SYM_FLAT','ASYM_FLAT')}
    cases={m:read(JOB/f'lifecycle-{m}.json') for m in annual}
    comparisons=[]
    for m in annual:
        for risk in (150,200):
            rows=[c for c in old0['rolling'] if c['cell']==m and c['risk_usd']==risk]
            comparisons.append(dict(version='PR78',policy=f'{risk/500:.2f}% fixed',model=m,**aggregate(rows,True)))
        comparisons.append(dict(version='PR79',policy='.50→.35→.25%',model=m,
            **aggregate(read(V1/f'lifecycle-{m}.json'))))
        comparisons.append(dict(version='V2',policy='.40→.40→.25%; throttle .30/.18; reserve7%',model=m,
            **aggregate(cases[m])))
    parity={n:read(JOB/n) for n in ('phase0-parity.json','core-parity.json','atlas-parity.json','lifecycle-parity.json')}
    tests=read(JOB/'regression-tests.json')
    summary=[]
    for asset in ('XAUUSD','EURUSD','US500','GBPUSD','AUDUSD'):
        cs=[c for c in atlas['cells'] if c['cell']['asset']==asset]
        summary.append(dict(asset=asset,cells=len(cs),stage0_pass=sum(c['stage0_pass'] for c in cs),
            endpoint_incomplete=sum(any('DATA_ENDPOINT_INCOMPLETE' in a['reasons'] for a in c['annual']) for c in cs),
            net_positive_both_years_asym=sum(all(a['net_mean']['ASYM_FLAT'] is not None and a['net_mean']['ASYM_FLAT']>0
                                               for a in c['annual']) for c in cs),
            raw_signal_views=read(JOB/'atlas-census.json')['counts'][asset]))
    j=dict(schema='PROP-ATLAS-V2-v1',decision='NOT_CHALLENGE_READY',date='2026-11-14',
        preregistration_commit='6fcd3f3',pre_stage0_implementation='b3f64ea',
        merged_pr79='a42fb9f',phase0=d,core=core,composition=f,
        atlas=atlas,atlas_summary=summary,
        annual=annual,comparisons=comparisons,
        lifecycle={m:[compact(c) for c in cs] for m,cs in cases.items()},
        continuous={m:compact(cs[0]) for m,cs in cases.items()},
        continuous_is_same_as_first_monthly_case=True,
        parity={n:{k:v for k,v in r.items() if k not in ('accounts','records')} for n,r in parity.items()},
        regression=tests,source_inventory=read(JOB/'source-inventory.json'),
        execution_endpoint_resolution=dict(hours=len(read(JOB/'resolved-endpoint-review.json')['hours']),
            purpose='exact missing role, not a new alpha trial'),
        private_job=str(JOB),prices2025_2026_read=False,prop_qualified=False,
        artifacts=[dict(name=p.name,sha256=digest(p)) for p in JOB.glob('*.json')
                   if not p.name.startswith('failure')],
        code=[dict(name=p.name,sha256=digest(p)) for p in Path('tooling/ai-engines').glob('prop_atlas*.py')],
        review_scope='same operator; alternate computational oracle; not independent human/model approval')
    write_json(OUT.with_suffix('.json'),j)
    lines=['# V2 — tìm nút thắt 2024, Atlas và chính sách vốn an toàn hơn','',
        '**Đã hoàn thành phép đo; chưa đủ cơ sở mua Challenge.** '
        'Năm 2024 yếu chủ yếu vì SELL âm, không phải BUY bị swap làm mất lợi thế. '
        'Hai cấu hình carry không đạt đầy đủ cổng lựa chọn; Atlas không tạo sleeve đủ điều kiện. '
        'Hệ thống cuối giữ A gốc cùng Risk Policy v2, không phải portfolio nhiều chiến lược đã được chứng minh.','',
        'Owner task `a2f3990c-8de8-4680-b5e0-87b2dc438462`. PR79 đã merge `a42fb9f`, '
        'nhánh cũ đã xóa. Protocol khóa `6fcd3f3`, implementation trước Stage0 `b3f64ea`. '
        'Giữ WIP VI Dubber; không broker, model, paid provider hoặc mở giá2025–2026.','',
        '## 1. PR78 → PR79 → V2: cùng36 mốc tháng','',
        '| Phiên bản | Phí | Qua vòng1 | Qua cả hai | Trung vị vòng1 đã đạt | Worst daily | Worst static | Peak DD | Breach | Payout trader |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:
        duration='N/A' if r['step1_median_months_completed_only'] is None else f"{r['step1_median_months_completed_only']:.2f} tháng"
        name=r['version']+(' '+r['policy'] if r['version']=='PR78' else '')
        lines.append(f"| {name} | {r['model'].split('_')[0]} | {r['step1']}/36 | {r['both']}/36 | {duration} | {r['worst_daily_pct']:.3f}% | {r['worst_static_pct']:.3f}% | {r['worst_peak_dd_pct']:.3f}% | {r['breaches']} | {r['payouts']} / ${r['trader_payout_usd']:.2f} |")
    lines+=['',
        'SYM: swapGold−40/−40; ASYM: proxy−45/−5USD/lot/rollover. 36cửa sổ chồng lấn, '
        'độ dài theo dõi khác nhau; không là36thử nghiệm độc lập hoặc xác suất pass. '
        'Trung vị chỉ tính người đã đạt; chưa có trung vị hoàn tất2vòng. Continuous2022–24 '
        'là đúng cửa sổ bắt đầu01/01/2022, được ghi riêng nhưng không cộng thành quan sát37.','',
        '## 2. Vì sao13 tài khoản kẹt vòng2?','',
        '| Bắt đầu | Qua vòng1 | Đỉnh floating equity P2 | Đỉnh balance P2 | Đỉnh khi flat | Thiếu từ đỉnh flat đến5% | Thiếu, R tham chiếu175USD | Kết thúc balance |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in d['accounts']:
        lines.append(f"| {date_text(r['start_msc'])} | {date_text(r['step1_pass'])} | {r['max_equity_profit_pct']:.3f}% | {r['max_realized_profit_pct']:.3f}% | {r['max_flat_profit_pct']:.3f}% | {r['shortfall_from_best_flat_pct']:.3f} điểm% | {r['shortfall_from_best_flat_reference175_R']:.3f}R | ${r['terminal_balance_usd']:,.2f} |")
    lines+=['',
        '**13/13 TIME_CENSORED_AT_DATASET_END,0/13 vi phạm drawdown.** Đỉnh equity chỉ '
        '+1,477%đến+4,034%; đỉnh flat+0,767%đến+3,118%. Trường hợp gần nhất khi flat '
        'vẫn thiếu khoảng1,882điểm%≈941USD≈5,38Rthamchiếu175USD. Risk thực tế có lúc125USD '
        'do throttle, nên không gọi mọi lệnh là175USD. Target chạm lúc đang có floating không '
        'đủ điều kiện pass; reset phase/4ngày/flat vẫn phải thỏa.','',
        'Hết dữ liệu không chứng minh chiến lược sẽ không bao giờ pass, cũng không cho phép '
        'ngoại suy rằng thêm vài tháng chắc chắn pass. Không mở2025–2026 để biết đáp án.','',
        '## 3. 2024: BUY đang kiếm tiền, SELL làm mất phần lớn','',
        'Cùng risk150USD/lệnh,1R=150USD. Gross đã chứa spread, chưa trừ commission/slippage/swap.','',
        '| Năm | Chiều | Lệnh | Gross R | Commission R | Slippage R | Swap R | Net không financing* | Net R thực trong mô hình |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in d['annual_side']:
        lines.append(f"| {r['year']} | {r['side']} | {r['trades']} | {r['gross_R']:+.3f} | {r['commission_R']:.3f} | {r['slippage_R']:.3f} | {r['swap_R']:+.3f} | {r['financing_free_net_R']:+.3f} | {r['net_R']:+.3f} |")
    lines+=['',
        '*Cột bỏ financing là phân rã kế toán, không phải cho phép chạy phí0. '
        '**BUY2024+14,689R, SELL−12,044R**. SwapBUY2024−2,211R còn ít hơn2023−3,129R; '
        'thủ phạm chính của suy giảm2024 là chiều SELL, không phải carryBUY tăng lên. '
        'Không biến chẩn đoán này thành SELL-only/BUY-only chọn theo hindsight.','',
        'Các số SELL2022≈11,19R được nhắc từPR77 là trước hiệu chỉnh holiday. '
        'V2 dùng AnchorPR78/79: SELL2022+6,934R; riêng đóng sớm04July đã thay đổi khoảng4,25R. '
        'Không trộn các baseline khác lịch vào cùng phép so sánh.','',
        '## 4. Hai cấu hình carry đã thử, giữ nguyên entry/SL','',
        '| Core | Phí | NetR2022 /2023 | EquityDD R2022 /2023 | Chọn? |',
        '|---|---|---:|---:|---|']
    baseline=read(V1/'phase1-metrics.json')
    for policy in ('A0','CA1','CA2'):
        for m in annual:
            rows=baseline[m+':A0']['annual'] if policy=='A0' else core[m+':'+policy]['annual']
            a,b=rows
            lines.append(f"| {policy} | {m.split('_')[0]} | {a['net_R']:+.3f} /{b['net_R']:+.3f} | {a['max_equity_R_DD']:.3f} /{b['max_equity_R_DD']:.3f} | {'Giữ baseline' if policy==f['core'] else 'Không đạt toàn bộ gate'} |")
    lines+=['',
        'CA1 đóng BUY20:30 cùng ngày, SELLgiữ48h/clamp; swapBUYđược xóa bằng việc đóng thật, '
        'đồng thời phần lợi nhuận sau20:30 cũng mất. NetBUYCA1 khoảng−2,06R/−6,97R '
        'ở2022/23, tệ hơn A gốc. CA2 đóng BUYtrước triple-swap nếu netbuffer<1,5R; '
        'nó cải thiện Return/DD nhưng Net2023thấp hơn baseline, nên không qua điều kiện '
        'NetR và Return/DD cùng tăng trong từng năm/model. Không đổi gate sau kết quả. '
        'CA1/CA2là trialV2được duyệt, không sửa lại lịch sử E3cũ.','',
        '## 5. Atlas — phạm vi, dữ liệu và kết quả','',
        '112ô=5assets×12sweep +4nonGold×12continuation +4Goldmomentum. '
        'Hai vùng: Á00–06UTC và ngày giao dịch trước; London08–11/NY13–16UTC; '
        'horizons20:30cùng ngày/24h/48hchặn lịch. MomentumBUYGold có D1/H4đồng thuận, '
        'một trong hai trigger đã khóa; không thêm ngưỡng/horizon/symbol sau khi thấy outcome.','',
        '| Tài sản | Ô đã đăng ký | Views tín hiệu thô | NetAS Y2022&2023 dương** | Còn thiếu endpoint | QuaStage0 |',
        '|---|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['asset']} | {r['cells']} | {r['raw_signal_views']} | {r['net_positive_both_years_asym']} | {r['endpoint_incomplete']} | {r['stage0_pass']} |")
    lines+=['',
        '**Mean dương trên phần có giá chỉ là diagnostic nếu còn missing, không được promote. '
        'Views trùng tín hiệu giữa các horizons và cửa sổ, không là lệnh độc lập. '
        'USDJPY chỉ có nguồn M1các ngày fixing được admit, không continuousH1đủ năm; '
        'giữ readiness-blocked, không coi là alphaâm.','',
        'Gate: mỗi năm>=40rawsignals, fullrequiredroles, medianfriction/medianSL<=15%, '
        '>=60%signals đạt15%; netmarkout dương và>=meanexecutionfriction ở cả hai stress models. '
        'Chỉ survivors mới dùng SL tự nhiên, >=6NetR/năm,>=40entries và dailycorr<0,30 '
        'theo từng năm/model. Không có survivor nên Stage1/correlation là **N/A**, '
        'không giả correlation0 hoặc dựng rổ bằng nhánh chưa đạt.','',
        'GoldNYpureBUY có những mean dương, nhưng chỉ17–32signals/năm trong các ô momentum; '
        'sweepGoldvùng ngày trước có48hmean dương nhưng chỉ khoảng39–45%signals đạt scale. '
        'Không bỏ D1/H4filter, nớiSL hoặc hạ phí để cứu cadence/scale.','',
        'FXgiữ phí5+4USD/lotRT và stressswap−40USD/lot/rollover cả hai chiều; '
        'đây là giả định bảo thủ, chưa xác minh swapđích. US500giữ legacycommission1USD/lotRT, '
        'slip0,75point/side, funding2USD/lot/calendar-day; overnightcells còn dividendunknown '
        'nên không đủ để select. H1/M1openproxy không là jointtick; bổ sungendpointtick không '
        'biến toàn bộ history hoặc đườngSL thành tickverified.','',
        '## 6. Risk Policy v2 và trade-off','',
        'Step1/Step2base0,40%,funded0,25%. Equity<−2,5%initial cap0,30%; '
        '<−4,5%cap0,18%; từ0đến−2,5%giữbase. Min với phasebase nên funded không tự '
        'tăng từ0,25%lên0,30%. Giữ dailysoftcap0,25%sau realizedloss>1,8%, resetPrague. '
        'Chỉ đổi size lệnh mới, không thu nhỏ vị thế cũ.','',
        'Ngoài throttle, có **internal7%projected-stop reserve**: từ chối toàn bộ lệnh mới '
        'nếu tổng SL/fees/slip/negativefunding của mọi vị thế có thể chạm93%vốn đầu. '
        'Đây là một guard bổ sung đã đăng ký từ đầu, nên kết quả V2 không được gán hết '
        'cho riêng ba bậc risk. Gap/chi phí ngoài mô hình vẫn có thể vượt floor.','',
        '| Phí | Entries cộng trên36cửa sổ* | Từ chối internal7% | Risk200/150/125/90USD |',
        '|---|---:|---:|---|']
    for m,cs in cases.items():
        buckets=Counter()
        for c in cs:buckets.update(c['risk_buckets'])
        lines.append(f"| {m.split('_')[0]} | {sum(c['entries'] for c in cs)} | {sum(c['rejections'].get('INTERNAL_STATIC_7PCT_RESERVE',0) for c in cs)} | "+' /'.join(str(buckets[str(k)]) for k in (200,150,125,90))+' |')
    lines+=['',
        '*Đếm admissions của các tài khoản khởi đầu khác nhau, có overlap, không là số '
        'lệnh thị trường độc lập. Guard an toàn có thể làm tài khoản nằm im/chậm hồi phục; '
        'đó là trade-off phải báo, không xóa các skippedintents khỏi audit. '
        '0,18%không bảo đảm “gần như không thể cháy”; sốRthua tiếp không cố định khi có '
        'phí, gap, nhiều vị thế và riskthay đổi.','',
        'Rewardproxy giữ30ngày, flat và lãi đóng>=20USD; accountdebit100%profit, '
        'trader80%/firm20%; không reset loss thành vốn mới, không injectcash hoặc autoretry. '
        'Payout trong bảng là eligibleproxy, không phải tiền thật; không có fundedcase nên '
        'phần funded/reward chỉ có fixtureproof. Chưa tính phí mua/retryChallenge/chi phí vận hành.','',
        '## 7. Annual economics và mức độ kết luận','',
        '| Năm | Phí | Số lệnh | NetR150USD trước = sau | MeanNetR/trade | Bỏ top3 |',
        '|---|---|---:|---:|---:|---:|']
    for m,obj in annual.items():
        for r in obj['rows']:
            lines.append(f"| {r['year']} | {m.split('_')[0]} | {r['entries']} | {r['net_R']:+.3f} | {r['mean_net_R']:+.4f} | {r['net_ex_top3_R']:+.3f} |")
    lines+=['',
        'A_Core vẫn A0 và không sleeve nên annualstrategytrước/sau đúng là như nhau; '
        'reuse pinned annualbooks thay vì tạo một backtest mới giả. V2risklifecycle là '
        'phép chạy mới trên tick. R dưới variablepolicy là net/allocatedrisk từng lệnh; '
        'USD/%của toàn tài khoản là chuẩn khi so mục tiêu quỹ.','',
        '2024đãexposedtrong các đợt trước và Phase0diagnostic; chỉ gọi HistoricalValidation. '
        'Phase2readers chặn2024, composition/riskkhóa trước Phase3; không chứng minh '
        'đây là cleanOOS hoặc đã tìm ra edge có ý nghĩa thống kê. Bootstrapped5signal-day '
        'blocks,50.000replications và Bonferroni112cellintervals giữ trong JSONprivate; '
        'đó là uncertaintydiagnostic theo từng năm/model, không guarantee chung mọiview.','',
        '## 8. Kiểm chứng và evidence','',
        f"- {tests['tests']} tests hồi quy đạt, gồm14fixturesV2 về carryclock, candlecausality, "
        'catalog112, riskthreshold/recovery, reserve, FXgrid và bootstrap.',
        '- Phase0:13peakaccounts và6sidebooks khớp oracle hạch toán riêng/Fraction.',
        f"- Core: {parity['core-parity.json']['shortened_paths']} paths giữ entry/SL, "
        f"{parity['core-parity.json']['cost_bridges']} cost bridges ở4sizes.",
        f"- Atlas:112cells và{parity['atlas-parity.json']['unit_cost_bridges']} per-unit cost bridges khớp Fraction.",
        f"- Lifecycle:{parity['lifecycle-parity.json']['accounts']} accounts khớp cash/equity/dd/daily bằng oracle "
        'ghi funding vào cash và phục hồi realizedanchor, khác producer giữ funding trong floating. '
        'Sổ tiền tự đối chiếu từng entry/exit, phase reset, withdrawals; no-new-year reset.',
        '- Cùng implementer, công thức khác; không gọi là independenthuman/agentreview. Không gửi Astra.',
        '- 693goldendpoint hours được kiểm trướcPnL,1workingM1revision, original giữ nguyên. '
        'GuardD1không dùng ngày12H1bars làm D1đã đủ20bars: bắt4signalviews trướcStage0, '
        'không đổi112recipes. First source-freeze helper thiếu importdatetime đã dừng trướcPnL, '
        'không dùng outputdangdở làm financialresult.',
        '- Partialcomponent attempt giữ nguyên trước khi bổ sung1.105endpoint hours. '
        'Chỉ thiếu role mới dùng rawticks; không thay missing bằng giá nến tương lai. '
        'FXdecoder tái dùng integerdelta decoder đã có bằng phép đổi basegrid chính xác, giữsame-msordinal.',
        '',
        f'Privatejob:`{JOB}`; protocol,source/admission,stage0-input/compositionfreeze, '
        'percellJSON,bootstrap,phase0/core/atlas/lifecycleparity,72caseledgers và '
        'JSONcạnh báo cáo giữ exactlocators/hashes. Không upload rawticks/caches.','',
        'Giới hạn còn lại: actualswap/spec/margin/leverage, historicalnews restrictions, '
        'targetcalendar/feed/execution, stalePraguemidnight marks, unseenforward và ownerhandover. '
        '`prop_qualified=false`; không được lấy source/CIpass làm quyền giao dịch.','',
        '**Quyết định:** giữ A0làm benchmark, gác Challenge/thu nhập chính với cấu hình này. '
        'V2giảm rủi ro theo mô hình nhưng không tạo tốc độ lợi nhuận mới. Không tiếp tục '
        'mở rộng giờ/SL/horizon hoặc tăng risk sau khi nhìn kết quả của112ô. '
        'Nghiên cứu tiếp cần câu hỏi mới có lý do kinh tế hoặc giải quyết uncertainty về phí/nguồn, '
        'không cộng thêm bot yếu để gọi là portfolio.','',
        '## Phụ lục — toàn bộ112ô, không chỉ các ô dương','',
        '| Cell | Raw2022/23 | Priced2022/23 | Keep15%2022/23 | Mean net ASYM2022/23* | Trạng thái/causes |',
        '|---|---:|---:|---:|---:|---|']
    for c in atlas['cells']:
        a,b=c['annual'];asset=c['cell']['asset'];factor=10000 if asset in ('EURUSD','GBPUSD','AUDUSD') else 1
        def val(x):return 'N/A' if x is None else f'{x*factor:+.3f}'
        reasons=sorted(set(a['reasons']+b['reasons']))
        lines.append(f"| {c['cell']['id']} | {a['raw']}/{b['raw']} | {a['priced']}/{b['priced']} | {a['pass15_fraction']:.1%}/{b['pass15_fraction']:.1%} | {val(a['net_mean']['ASYM_FLAT'])}/{val(b['net_mean']['ASYM_FLAT'])} | {', '.join(reasons) or 'STAGE0_PASS'} |")
    lines+=['','*Đơn vị GoldUSD/oz; FXpip; US500indexpoint. Mean trên partialpricedcohort '
        'không phải meanfullsample đủđiềukiện. Mọi cell/negative/missing vẫn giữ trongJSON.','']
    OUT.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(OUT.with_suffix('.md'),flush=True)


if __name__=='__main__':build()
