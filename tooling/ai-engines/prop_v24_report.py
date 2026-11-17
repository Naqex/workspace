"""Truthful V24 closure: feature evidence and unmet performance targets separate."""
from pathlib import Path
import json
from prop_v24_common import *
from prop_v22_report import table,fmt

REPORT=Path('planning/research/PARETO-MT5-BOT-LAB-V24-RESULTS-20261117')

def report():
    tests=read(JOB/'tests-release-verified-summary.json');smoke=read(JOB/'smoke-release-summary.json')
    inventory=read(JOB/'connector-inventory-summary.json');lab=read(JOB/'seed-corpus-summary-final.json')
    decision=read(JOB/'P80-Development-decision.json');native=read(JOB/'actual-no-credentials-CLI.json')
    assert tests['passed'] and tests['tests']>=1310 and tests['preserved_V23_IDs']==1295
    assert not decision['passed'] and decision['new_historical_children']==decision['new_bootstrap_children']==0
    source_pins={str(p):sha(p) for p in [PROTOCOL,*Path('tooling/ai-engines').glob('prop_v24_*.py'),
        Path('tooling/ai-engines/ftmo_connection.py'),Path('tooling/ai-engines/ftmo_trial_runner.py'),
        *[Path('tooling/ai-engines/quant_core')/n for n in ('bot_lab.py','binary_bot_metadata.py','bot_market_fingerprint.py','research_fast_fail.py')]]}
    manifests=[]
    from prop_v21_common import unpack
    with bindings(compression,JOB=JOB):
        for p in sorted(JOB.glob('*-manifest.json')):
            m=read(p)
            if m.get('file','').endswith('.json.zst'):
                unpack(m['file'][:-9]);manifests.append(m)
    result=dict(schema='V24-results-v1',tests=tests,smoke=smoke,inventory=inventory,lab=lab,Development=decision,
        native_CLI=native,source_pins=source_pins,compressed_manifests=manifests,
        performance_targets_met=tests['wall']<12.5 and smoke['below065']==10,
        implemented=['New Trial env-file rotation using pinned product isolation/clock','Bounded static source/binary inspection',
            'Causal trade-log fingerprint with optional bound Bid market-store features','Prepared-input fast-fail evidence gates',
            'One Dev Pareto allocation trial','Complete runtime, six-worker option, preserved test IDs'],
        remaining=['Native new-credential login/capture and broker-clock parity not validated on actual MT5',
            'Automatic recovery of a unique causal strategy from opaque binary/log is not implemented or inferable from these inputs',
            'Static patterns are not full MQL/CSharp/Pine semantic analysis or a safety/FTMO certification',
            'Full<12.5s and smoke10/10<.65s not achieved; no true claim of <.55s',
            'Runtime/script shutdown fixtures do not establish operational native-terminal stability'],
        incumbent='V16/V19 BASE_GUARD',prop_qualified=False,actual_broker_orders=0,actual_payout_USD=0,
        baseline_PR102_merge='555c2bd',Trader_pin_unchanged=True,VI_WIP_preserved=True,
        full_weight_search_count=1,no_later_prices_used_for_selection=True,
        independent_review='Core/connector review found and corrected clock/binding/tree/causality/input-domain/fractional-multiplier issues')
    text=json.dumps(result,ensure_ascii=False,indent=2);assert len(text.encode())<1048576
    REPORT.with_suffix('.json').write_text(text,encoding='utf-8',newline='\n')
    lines=['# V24 — connector MT5, Bot Lab và phép thử Pareto','',
        '**P80_20 rớt Development; giữ V16/V19 BASE_GUARD. Connector và lab đã có implementation/fixtures, '
        'nhưng native login/capture chưa kiểm thực tế, chưa có causal clone tự động và chưa đạt mục tiêu tốc độ.**','',
        'PR102/head19bf58c đã merge555c2bd, nhánh V23 local/remote đã xóa. '
        'V24 đăng ký220550d trước kết quả, đúng một trial1,30/0,70/0,70, không grid hoặc tune theo2024+. '
        'Giữ Trader pin930fa768/VI WIP, không broker orders/deploy. PR103 để mở.','',
        '## 1. Kết nối MT5 cũ và rotation tài khoản mới','',
        'Connector product có sẵn, không mất: Python IPC được API owner quản lý bằng private portable terminal; '
        'secret DPAPI-sealed trong mt5_connections, không phải password plain text cần khôi phục. '
        'Owner cho biết account cũ hết hạn; V24 không query database hay xác nhận lại hạn dùng tài khoản.','']
    lines+=table(['Thành phần','Vị trí','Reuse/thay đổi'],[
        ['Product connector','projects/trader/foundation_v2/scripts/mt5_connector.py','prepare_terminal/verify_identity/error codes, không sửa submodule'],
        ['Secret/connection owner','projects/trader/foundation_v2/api-rust/src/mt5_connector.rs','DPAPI binding/mt5_connections; không decrypt secret cũ'],
        ['Broker clock','projects/trader/foundation_v2/scripts/mt5_clock.py','Exact FTMO-Demo2026→UTC; ticks/rates/deal envelopes'],
        ['Process tree','projects/trader/foundation_v2/trading_workspace_v2/nautilus_worker.py','Windows Job kill-on-close; launch suspended→assign→resume'],
        ['Legacy socket','projects/trader/archive/legacy/root/mt5_data.py','Historical reference; không khôi phục legacy runtime'],
        ['Trial integration','tooling/ai-engines/ftmo_connection.py + ftmo_trial_runner.py','Four-key parser/own terminal/account hash binding'],
        ['Private new credential file','config/ftmo_free_trial.env','Ignored; example tracked, no shell eval/password argv']])
    lines+=['',f"Inventory D/E: {inventory['candidate_files']:,} candidate files, {inventory['matches']:,} signature matches, "
        f"{inventory['bot_paths']} bot file paths, {inventory['errors']} recorded errors, "
        f"{inventory['skipped_large']} large candidate files skipped. Maxdepth18; generated folders pruned. "
        'Không gọi đây là toàn bộ nội dung mọi file/dependency. Full redacted list và Git-history metadata nằm trong Zstd private; '
        'không password/account values vào báo cáo hoặc Git. Lần Python walk đầu quá chậm được giữ receipt và thay bằng rg traversal.','',
        'Dùng `--credentials-file config/ftmo_free_trial.env` hoặc bốn environment keys. '
        'Đúng FTMO Demo/Trial USD mới được nhận; không đổi terminal Trader đang chạy. Lock theo account, '
        'process tree riêng tắt Experts/DLL. Snapshot/parity và ticks/rates/deals dùng clock helper product, '
        'account đổi giữa login/probe/capture thì fail. Không login bằng account saved cuối cùng khi credential thiếu.','',
        'Actual CLI không credentials: check exit2/no ready, watcher2s exit2/timeout; '
        'không tài khoản mới hoặc terminal đích để chứng nhận login/capture thành công. '
        'Fixture kiểm launch/Job/binding/clock/shutdown; actual Windows Job create/close smoke đã chạy. '
        'Shadow vẫn yêu cầu manifest, seed và session/news/spec parity; không suy từ login thành execution-ready. '
        '10giây là thao tác rotation sau prerequisites, không là cam kết cold/network timing.','',
        '## 2. Kiểm thử và fast-fail: đo lại premise, không giảm coverage','',
        'Runner thực tế là unittest, không phải pytest. Smoke8modules/78IDs, không66; '
        'nó chưa từng import tất cả23thế hệ chỉ vì filename collection. V22/V23 tests không chạy batch5.000 hoặc '
        'giải nén research archives trong từng test. Vì vậy không thêm cache phức tạp không có hotspot. '
        'Profile V24 cho thấy import/path/stat và fixture filesystem; tải concurrent inventory làm số đo trước đầu phiên không tương đương idle.','']
    before=read(JOB/'tests-unified-before-summary.json')
    lines+=table(['Phép đo','Tests','Wall','Scope'],[
        ['V23 receipt lịch sử',1295,'19,728s','5 runtime groups, khác thời điểm/tải'],
        ['V24 initial five groups',read(JOB/'tests-before-matrix.json')['tests'],fmt(read(JOB/'tests-before-matrix.json')['seconds'])+'s','Inventory concurrent; không dùng làm causal speedup'],
        ['Same-runtime baseline4shards',before['tests'],fmt(before['wall'])+'s','Cùng current tests, inventory paused'],
        ['RAM log buffering4shards',read(JOB/'tests-final-summary.json')['tests'],fmt(read(JOB/'tests-final-summary.json')['wall'])+'s','Không cải thiện; đã revert'],
        ['Final source6shards',tests['tests'],fmt(tests['wall'])+'s','Giữ mọi1295 IDs, không skip; sáu logical CPUs']])
    lines+=['',f"**{tests['tests']} PASS/0skip**, final source **{tests['wall']:.6f}s**, target<12,5s: **chưa đạt**. "
        'Six workers là lựa chọn explicit, CI vẫn4; không đổi dependency runtime product. '
        'Runtime test chung dùng exact pins CI và PyYAML từ worker lock; lần thiếu PyYAML được giữ nguyên lỗi, không skip tests.','',
        f"Smoke release10fresh processes, cùng78IDs: **{smoke['below055']}/10<0,55s; {smoke['below065']}/10<0,65s**, "
        f"median{smoke['median']:.6f}s/max{smoke['max']:.6f}s. Giữ các samples ban đầu, A/B và release; "
        'release đo lại vì source log buffering đã revert, không chọn nhanh nhất làm kết quả. '
        'Chưa đạt performance acceptance; không bảo đảm tốc độ trên tải/máy khác.','',
        'Fast-fail Gate1 pure toxicity+declared scale, không write artifact khi fail; chưa chứng minh hardSL/safety. '
        f"Ba controls Gate1 max{lab['Gate1_max_fixture_seconds']:.6f}s. Gate2 chỉ nhận Dev/causal/SL-active "
        'và so net/DD/static/daily/open risk với baseline; Gate3 đòi freeze thực sự nằm trong GitHEAD, source/input/decision '
        'hash và tính lại gate, không tin passed=True do caller cấp. '
        '<0,5s/<2s là prepared compute budget trên workload được đo, không universal runtime cap.','',
        '## 3. Bot Lab: capabilities đã có và phần chưa thể suy ra','',
        'Luồng: inbox file→bounded static parser→DNA/evidence/flags→prepared Gate1 nếu có scale→'
        'review causal recipe→Stage-0/Dev→Gate3. File lạ không được import/execute hoặc gửi lệnh. '
        'Source limit1MiB cho Python AST, binary/log16MiB, logs≤50.000rows; closed-loss lookup dùng heap theo thời gian/symbol.','']
    lines+=table(['Input','Có','Giới hạn'],[
        ['.py','AST/tokenizer + structural evidence','Không complete dataflow/call graph'],
        ['.mq4/.mq5/.cs/.pine','Indicator/timeframe/entry/exit/session/sizing patterns','Không compiler đầy đủ; dynamic/obfuscated logic unknown'],
        ['.ex4/.ex5/.dll/.pyc','ASCII/UTF16 + bounded PE import metadata khi có','Không decompile, loadDLL, marshal hoặc bypass khóa'],
        ['CSV/HTML/JSON log','UTC session signature, stop/target geometry, prior closed loss sizing','Cần canonical columns/timezone; không unique causal algorithm'],
        ['Optional MarketDataStore','ATR H1/H4,MA/RSI/Donchian/PDH-PDL/Asian causal Bid features','Ask/execution parity không có; source binding bắt buộcUTC']])
    lines+=['',f"Seed corpus: **3controls PASS** với expected patterns; **{lab['repository_strategy_sources']}** tracked strategy/order-bearing sources "
        'được inspect trong scope scanner, giữ SHA. Martingale fractional>1 trong loss context, literalSL0, date-condition review '
        'và friction ratio có flags. Không có ground truth corpus để tuyên bố100% real-world recall hoặc mọi bot không flag đều sạch. '
        'Hardcoded dates có thể là holiday hợp lệ, multiplier có thể là sizing hợp lệ; manual reachability/context vẫn cần.','',
        '**Chưa có engine tự khôi phục causal bot tương đương từ EX5/trade logs hoặc tự chạy9năm.** '
        'Đã có fingerprint/typed translation gate; thuật toán không định danh duy nhất từ các đầu vào này. '
        'Không ghi timestamp trades thành alpha giả hoặc lách Dev bằng outcome. '
        'Review hướng dẫn dùng tại [playbook](BOT-REVERSE-LAB-PLAYBOOK.md), có lệnhinspect/clone-log/market-store/credentials.','',
        '## 4. P80_20 và quyết định chốt','',
        'Protocol khóa EURF5×1,30, GoldF3×0,70, GoldF4×0,70 trước outcome. '
        'Đây không phải80% vốn vàoEUR, không tìm grid1,25–1,35. V23 lợi nhuận87,1% từF5 là attribution lịch sử, '
        'không tự suy weight tối ưu; “Vàng thấp/cao” cũng chưa được chứng minh là nguyên nhân regime. '
        'Giữ340 Dev trades, actual lot floor, stress cash fees, causal original SL-active paths cả hai ordering.','']
    rows=[]
    for case in decision['cases']:
        d=case['decision']
        for name,m in (('Baseline',d['baseline']),('P80_20',d['candidate'])):
            rows.append([case['order'],name,fmt(m['net_R']),fmt(m['equity_R_DD']),fmt(m['static_R_loss']),fmt(m['worst_daily_R']),fmt(m['max_open_risk_USD'],2),*[fmt(v) for v in m['cluster_R']]])
    lines+=table(['Order','Model','NetR','EquityDD R','Static loss R','Daily R UTC','Open stop risk USD','2018–20 R','2021–23 R'],rows)
    lines+=['',f"End-to-end data preparation+measurement **{decision['end_to_end_seconds']:.3f}s**; "
        'prepared two-book+gate compute mỗi ordering '+', '.join(f"{r['prepared_gate_seconds']:.3f}s" for r in decision['cases'])+'. '
        '**NO-GO**: equityDD14,673R>12,207R và maxopen314,52USD>312,80USD. '
        'Net32,278R cao hơn và static/daily tốt hơn không đủ pass toàn gate. '
        'Đây là fixed-unit marked book trước account admission, không giả là account compliance; '
        'fail sớm nên không chạy tiếp lifecycle để cứu kết quả.','',
        '**0 new historical105-start children /0 new bootstrap5.000-draw children.** '
        'Không dùng giá2024–2026 để chọn/đổi weights. Giữ V16/V19 BASE_GUARD; không mua Challenge, tăng risk hoặc promote bot.','',
        'Independent review đã phát hiện và sửa: clock toàn rates/deals, configured-account drift, terminal tree race, '
        'risk input domains, future-loss inference, fractional multiplier và log work bounds. '
        'Fixtures/source review khác successful native acceptance; final CI/IDs ghi private receipts sau push.','',
        'Artifacts mới dạng bảng dùng Zstd9+SHA256/roundtrip; small reports và test receipts JSON để đối chiếu. '
        'Không xóa raw source, old attempts hoặc duplicate price caches. Không đổi Trader gitlink/VIWIP.','',
        '[Protocol](PARETO-MT5-BOT-LAB-V24-PROTOCOL-20261117.md) · '
        '[JSON](PARETO-MT5-BOT-LAB-V24-RESULTS-20261117.json) · '
        '[Playbook](BOT-REVERSE-LAB-PLAYBOOK.md)']
    REPORT.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print(dict(report=str(REPORT),bytes=len(text.encode()),performance_targets_met=result['performance_targets_met']))

if __name__=='__main__':report()
