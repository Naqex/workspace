"""Seed-corpus static audit and bounded gate fixtures; never execute bot code."""
from pathlib import Path
import json,subprocess,time
from prop_v24_common import *
from quant_core.bot_lab import inspect_bytes
from quant_core.research_fast_fail import toxicity_scale

def run(label='final'):
    root=Path('research/bot_reverse_lab/controls');controls=[]
    for path in sorted(root.iterdir()):
        started=time.perf_counter();p=inspect_bytes(path.read_bytes(),path.suffix)
        gate=toxicity_scale(p,friction=.75,median_stop=8,retention=.8)
        controls.append(dict(name=path.name,profile=p,gate=gate,seconds=time.perf_counter()-started))
    flags={r['name']:{v['flag'] for v in r['profile']['findings']} for r in controls}
    assert 'MARTINGALE_GRID_TOXICITY' in flags['martingale_grid.py']
    assert 'NO_STOP_LOSS_TOXICITY' in flags['martingale_grid.py']
    assert 'BACKTEST_CHEAT_HARDCODED_DATES' in flags['hardcoded_dates.py']
    assert not flags['range_rejection.pine']
    rows=[];paths=subprocess.check_output(['git','ls-files','--','*.py','*.mq4','*.mq5','*.pine','*.cs'],text=True).splitlines()
    paths+=['projects/trader/'+v for v in subprocess.check_output(['git','-C','projects/trader','ls-files','--','*.py','*.mq4','*.mq5','*.pine','*.cs'],text=True).splitlines()]
    for name in paths:
        path=Path(name)
        if any(part in ('node_modules','.venv','vendor') for part in path.parts):continue
        if path.stat().st_size>262144:continue
        raw=path.read_bytes()
        # Locate strategy/order-bearing source rather than classify arbitrary product code as bots.
        signatures=(b'OrderSend',b'order_send(',b'strategy.entry',b'def generate',b'class Strategy',b'def signals',b'.Buy(',b'Backtest(',b'OnTick(')
        if not any(s in raw for s in signatures):continue
        try:
            p=inspect_bytes(raw,path.suffix);rows.append(dict(path=name,sha256=p['sha256'],indicators=p.get('indicators',[]),
                flags=[v['flag'] for v in p.get('findings',[])],admission=p['admission'],execution_performed=False))
        except (SyntaxError,ValueError,UnicodeError) as exc:rows.append(dict(path=name,status='PARSE_INCOMPLETE',error_type=type(exc).__name__))
    binding=compressed('seed-corpus-static-audit-'+label,dict(controls=controls,repository_sources=rows,
        parser_sha256=sha('tooling/ai-engines/quant_core/bot_lab.py'),binary_parser_sha256=sha('tooling/ai-engines/quant_core/binary_bot_metadata.py'),
        no_downloads_or_sample_execution=True,static_flags_not_vendor_scam_verdict=True))
    save('seed-corpus-summary-'+label+'.json',dict(controls=3,controls_expected_patterns_passed=True,repository_strategy_sources=len(rows),
        manifest=binding,Gate1_max_fixture_seconds=max(r['seconds'] for r in controls),real_world_recall_not_measured=True))
    print(dict(controls_passed=True,sources=len(rows)))

if __name__=='__main__':run()
