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
    process=None;initialized=False
    try:
        terminal,config=product.prepare_terminal(root,str(key),trading=False)
        sdk=sdk or __import__('MetaTrader5')
        startup=None
        if sys.platform=='win32':
            startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        process=subprocess.Popen([str(terminal),'/portable',f'/config:{config}'],cwd=terminal.parent,
            startupinfo=startup,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
        finally:lock.unlink(missing_ok=True)

def quote_utc_msc(value,server):return int(product_module('mt5_clock').utc_msc(value,server))

class ClockReader:
    def __init__(self,reader):self.inner=reader;self.clock=product_module('mt5_clock')
    def __getattr__(self,name):return getattr(self.inner,name)
    def ticks(self,asset,first,end):
        from datetime import datetime,timezone
        server=self.inner.account()['server']
        lo,hi=self.clock.history_range(datetime.fromtimestamp(first/1000,timezone.utc),datetime.fromtimestamp(end/1000,timezone.utc),server)
        raw=self.inner.ticks(asset,int(lo.timestamp()*1000),int(hi.timestamp()*1000))
        out=[]
        for r in raw:
            at=int(self.clock.utc_msc(r['time_msc'],server))
            if first<=at<end:out.append(dict(r,time_msc=at,source_time_msc=r['time_msc']))
        return out
