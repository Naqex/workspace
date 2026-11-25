"""Explicit new Trial credentials with pinned Trader isolation and clock helpers."""
from contextlib import contextmanager
from pathlib import Path
from functools import lru_cache
import hashlib,importlib.util,json,os,subprocess,sys,uuid

ROOT=Path(__file__).resolve().parents[2]
KEYS=('FTMO_MT5_LOGIN','FTMO_MT5_PASSWORD','FTMO_MT5_SERVER','FTMO_MT5_TERMINAL_PATH')

@lru_cache(maxsize=2)
def product_module(name):
    path=ROOT/'projects/trader/foundation_v2/scripts'/f'{name}.py'
    spec=importlib.util.spec_from_file_location('_ftmo_product_'+name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

def credentials(path=None,environ=None):
    values=dict(os.environ if environ is None else environ)
    if path:
        p=Path(path)
        if p.stat().st_size>8192:raise ValueError('CREDENTIAL_FILE_TOO_LARGE')
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            key,sep,value=line.partition('=')
            if not sep or key.strip() not in KEYS:raise ValueError('ONLY_FOUR_FTMO_KEYS_ALLOWED')
            value=value.strip()
            if value[:1] in ('\"',"'"):
                if len(value)<2 or value[-1]!=value[0]:raise ValueError('UNBALANCED_ENV_QUOTES')
                value=value[1:-1]
            values[key.strip()]=value
    if not path and not any(values.get(k) for k in KEYS[:3]):return None
    if not all(values.get(k) for k in KEYS[:3]):raise ValueError('COMPLETE_NEW_TRIAL_CREDENTIALS_REQUIRED')
    if not values[KEYS[0]].isdigit() or int(values[KEYS[0]])<=0:raise ValueError('POSITIVE_TRIAL_LOGIN_REQUIRED')
    if not values[KEYS[2]].casefold().startswith('ftmo'):raise ValueError('FTMO_SERVER_REQUIRED')
    if not values.get(KEYS[3]):
        values[KEYS[3]]=str(product_module('mt5_connector').terminal_source())
    return {k:values[k] for k in KEYS}

@contextmanager
def trial_session(values,*,sdk=None,product=None,inventory=None):
    """Never rotates an existing terminal: own portable instance, no EAs/DLLs."""
    if values is None:yield None;return
    from ftmo_trial_runner import terminal_inventory
    product=product or product_module('mt5_connector')
    key=uuid.uuid5(uuid.NAMESPACE_URL,values[KEYS[0]]+'|'+values[KEYS[2]])
    root=ROOT/'.runtime/ftmo-trial-readonly-v24';folder=root/str(key)
    running=terminal_inventory() if inventory is None else inventory
    if any(t.get('ExecutablePath') and Path(t['ExecutablePath']).resolve().parent==folder.resolve() for t in running):
        raise ValueError('OWNED_TRIAL_TERMINAL_ALREADY_RUNNING_RECONCILE_FIRST')
    root.mkdir(parents=True,exist_ok=True);lock=root/(str(key)+'.lock')
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('OWNED_TRIAL_SESSION_LOCKED') from None
    os.close(fd)
    previous=os.environ.get('TW_V2_MT5_TERMINAL');os.environ['TW_V2_MT5_TERMINAL']=values[KEYS[3]]
    process=None;initialized=False;job=None
    try:
        terminal,config=product.prepare_terminal(root,str(key),trading=False)
        sdk=sdk or __import__('MetaTrader5')
        startup=None
        if sys.platform=='win32':
            startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        sys.path.insert(0,str(ROOT/'projects/trader/foundation_v2'))
        from trading_workspace_v2.nautilus_worker import _WorkerOwnedJob
        job=_WorkerOwnedJob()
        process=subprocess.Popen([str(terminal),'/portable',f'/config:{config}'],cwd=terminal.parent,
            startupinfo=startup,creationflags=0x4,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        job.assign(process)
        import ctypes
        resume=ctypes.WinDLL('ntdll').NtResumeProcess
        resume.argtypes=[ctypes.c_void_p];resume.restype=ctypes.c_long
        if resume(int(process._handle))!=0:raise ValueError('OWNED_PROCESS_RESUME_FAILED')
        if not sdk.initialize(str(terminal),login=int(values[KEYS[0]]),password=values[KEYS[1]],
                server=values[KEYS[2]],timeout=10000,portable=True):raise ValueError(product.initialization_error(sdk))
        initialized=True;account=product.verify_identity(sdk,dict(login=values[KEYS[0]],server=values[KEYS[2]]))
        info=sdk.terminal_info()
        if (account.trade_mode!=0 or account.currency!='USD' or 'ftmo' not in (account.server+getattr(account,'company','')).casefold()):raise ValueError('FTMO_DEMO_USD_ONLY')
        if Path(info.path).resolve()!=terminal.parent.resolve() or Path(info.data_path).resolve()!=terminal.parent.resolve():raise ValueError('ISOLATED_TERMINAL_IDENTITY_REQUIRED')
        yield str(terminal)
    except Exception:raise ValueError('TRIAL_CONNECTION_OR_IDENTITY_FAILED_SANITIZED') from None
    finally:
        if previous is None:os.environ.pop('TW_V2_MT5_TERMINAL',None)
        else:os.environ['TW_V2_MT5_TERMINAL']=previous
        try:
            if initialized:
                try:sdk.shutdown()
                except Exception:pass
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        finally:
            if job is not None:job.close()
            lock.unlink(missing_ok=True)

def quote_utc_msc(value,server):return int(product_module('mt5_clock').utc_msc(value,server))

class ClockSDK:
    """Normalize every price/history clock before inherited causal checks run."""
    def __init__(self,sdk,server):self.raw,self.server,self.clock=sdk,server,product_module('mt5_clock')
    def __getattr__(self,name):return getattr(self.raw,name)
    def rates(self,rows):
        if rows is None:return None
        return [dict(zip(r.dtype.names,r))|{'time':int(self.clock.utc_seconds(r['time'],self.server))} for r in rows]
    def copy_rates_from_pos(self,*args):return self.rates(self.raw.copy_rates_from_pos(*args))
    def copy_rates_range(self,asset,tf,first,end):
        lo,hi=self.clock.history_range(first,end,self.server)
        rows=self.rates(self.raw.copy_rates_range(asset,tf,lo,hi))
        return None if rows is None else [r for r in rows if first.timestamp()<=r['time']<=end.timestamp()]
    def history_deals_get(self,first,end):
        lo,hi=self.clock.history_range(first,end,self.server);rows=self.raw.history_deals_get(lo,hi)
        if rows is None:return None
        out=[]
        for r in rows:
            at=self.clock.utc_seconds(r.time,self.server)
            if first.timestamp()<=at<=end.timestamp():out.append(r._replace(time=int(at)))
        return out
    def copy_ticks_range(self,asset,first,end,flags):
        from datetime import datetime,timezone
        lo,hi=self.clock.history_range(first,end,self.server);raw=self.raw.copy_ticks_range(asset,lo,hi,flags)
        if raw is None:return None
        out=[]
        for r in raw:
            at=int(self.clock.utc_msc(r['time_msc'],self.server))
            if first.timestamp()*1000<=at<=end.timestamp()*1000:
                out.append(dict(time_msc=at,bid=r['bid'],ask=r['ask'],flags=r['flags']))
        return out

class ClockReader:
    def __init__(self,reader):
        self.inner=reader
        from ftmo_free_trial_adapter import NativeMT5Reader
        self.normalized=NativeMT5Reader.__new__(NativeMT5Reader)
        self.normalized.sdk=ClockSDK(reader.sdk,reader.account()['server'])
    def __getattr__(self,name):return getattr(self.normalized,name)

    def latest_quote(self, asset):
        tick = self.inner.sdk.symbol_info_tick(asset)
        if tick is None or not tick.time_msc:
            return None
        return dict(asset=asset, time_msc=quote_utc_msc(tick.time_msc, self.normalized.sdk.server),
                    bid=tick.bid, ask=tick.ask, flags=tick.flags)
