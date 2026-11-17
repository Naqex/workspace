"""Inspect untrusted bot files/logs without executing them. JSON goes to stdout."""
import argparse,json,time
from pathlib import Path
from quant_core.bot_lab import inspect_bytes,log_rows,fingerprint

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--inspect',type=Path);g.add_argument('--clone-log',type=Path)
    p.add_argument('--log-timezone');p.add_argument('--market-store',type=Path)
    p.add_argument('--friction',type=float);p.add_argument('--natural-sl',type=float);p.add_argument('--retention',type=float)
    a=p.parse_args();started=time.perf_counter();path=a.inspect or a.clone_log
    try:
        if not path.is_file() or path.is_symlink():raise ValueError('REGULAR_SAMPLE_FILE_REQUIRED')
        if path.stat().st_size>16*1024*1024:raise ValueError('INPUT_SIZE_LIMIT_16MIB')
        raw=path.read_bytes()
        if a.inspect:
            r=inspect_bytes(raw,path.suffix.lower())
            from quant_core.research_fast_fail import toxicity_scale
            r['prepared_scale_gate']=toxicity_scale(r,friction=a.friction,median_stop=a.natural_sl,retention=a.retention)
        else:
            market=None
            if a.market_store:
                from quant_core.bot_market_fingerprint import MarketFingerprint
                market=MarketFingerprint(a.market_store)
            r=fingerprint(log_rows(raw,path.suffix.lower()),timezone_name=a.log_timezone,market_bars=market)
        print(json.dumps(dict(r,inspection_seconds=time.perf_counter()-started),ensure_ascii=False));return 0
    except (ValueError,KeyError,SyntaxError,UnicodeError,OSError) as exc:
        print(json.dumps(dict(status='INSPECTION_INCOMPLETE',error_type=type(exc).__name__,reason=str(exc) if type(exc) is ValueError else 'INPUT_SCHEMA_OR_ACCESS_ERROR',execution_performed=False)));return 2

if __name__=='__main__':raise SystemExit(main())
