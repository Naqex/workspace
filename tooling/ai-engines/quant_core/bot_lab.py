"""Bounded static evidence and log fingerprints. Samples are data, never code."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
import ast,csv,hashlib,io,json,math,re,tokenize,heapq

SOURCE={'.py','.mq4','.mq5','.cs','.pine'}
BINARY={'.ex4','.ex5','.dll','.pyc'}

@dataclass
class BotDNAProfile:
    schema:str
    sha256:str
    format:str
    indicators:list
    timeframes:list
    entry_logic:list
    exit_risk_logic:list
    session_filters:list
    sizing_logic:list
    findings:list
    analysis_scope:str
    admission:str='REVIEW_REQUIRED'

def safe_line(text):
    if re.search(r'password|secret|token|api.?key',text,re.I):return '[REDACTED_SENSITIVE_LINE]'
    return text.strip()[:240]

def indicators_in(code):
    return sorted(set(re.findall(r'\b(?:iMA|iATR|iRSI|iBands|iADX|iCCI|iMFI|iStochastic|iMACD|iSAR|iCustom|SMA|EMA|ATR|RSI|CCI|MFI|MACD|Donchian|SimpleMovingAverage|ExponentialMovingAverage|AverageTrueRange|RelativeStrengthIndex|BollingerBands|ta\.\w+)\b',code,re.I)))

def inspect_bytes(raw,suffix):
    if suffix in {".set",".ini",".chr",".htm",".html",".xml"}:
        from quant_core.mt_report_parser import PRESETS,preset_bytes,report_bytes
        return preset_bytes(raw,suffix) if suffix in PRESETS else report_bytes(raw,suffix)
    if suffix not in SOURCE|BINARY:raise ValueError('UNSUPPORTED_BOT_FORMAT')
    if len(raw)>16*1024*1024:raise ValueError('BOT_SIZE_LIMIT_16MIB')
    digest=hashlib.sha256(raw).hexdigest();findings=[]
    if suffix in BINARY:
        from quant_core.binary_bot_metadata import pe_imports
        strings=[s.decode('ascii',errors='replace') for s in re.findall(rb'[\x20-\x7e]{4,200}',raw)]
        strings += [s.decode('utf-16le',errors='replace') for s in re.findall(rb'(?:[\x20-\x7e]\x00){4,200}',raw)]
        names=sorted({n for s in strings for n in re.findall(r'(?:iMA|iATR|iRSI|iBands|iCustom|OrderSend|OrderClose|Buy|Sell|[A-Za-z0-9_]+\.dll)',s)})
        imports=pe_imports(raw)
        return dict(schema='BotBinaryForensics-v1',sha256=digest,format=suffix,bytes=len(raw),
            string_signatures=names[:256],PE_header=raw[:2]==b'MZ',python_magic_hex=raw[:4].hex() if suffix=='.pyc' else None,
            binary_imports=imports,symbol_imports_status=imports['status'],logic_recovery='UNAVAILABLE_FROM_STRINGS',
            admission='BINARY_ONLY_REVIEW_REQUIRED',execution_performed=False,confidence='LOW',
            limits=['Strings may be absent, dead or obfuscated; absence is not proof of safety.',
                'No original source recovery, DRM removal, DLL load or pyc deserialization.'])
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    if suffix=='.py':
        if len(raw)>1048576:raise ValueError('SOURCE_AST_SIZE_LIMIT_1MIB')
        tree=ast.parse(text)
        # Evidence from parsed nodes only; never import or evaluate the sample.
        lines=text.splitlines()
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type==tokenize.COMMENT:
                row,col=token.start;lines[row-1]=lines[row-1][:col]
        for node in ast.walk(tree):
            if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                for row in range(node.lineno-1,node.end_lineno):lines[row]=''
        code='\n'.join(lines)
    else:
        code=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S);lines=code.splitlines()
    def evidence(pattern):
        return [dict(line=i+1,text=safe_line(s)) for i,s in enumerate(lines) if re.search(pattern,s,re.I)][:32]
    indicators=indicators_in(code)
    timeframes=sorted(set(re.findall(r'\b(?:PERIOD_(?:M\d+|H\d+|D1|W1)|TimeFrame\.\w+|timeframe\.\w+)\b',code)))
    sizing=evidence(r'lot|volume|multiplier|qty|position_size')
    for row in sizing:
        i=row['line']-1;context='\n'.join(lines[max(0,i-8):min(len(lines),i+9)])
        multiply=re.search(r'\b(?:lot\w*|volume\w*|qty)\s*(?:\*=\s*|=\s*(?:lot\w*|volume\w*|qty)\s*\*\s*)(\d+(?:\.\d+)?|\.\d+|multiplier)\b',lines[i],re.I)
        multiply=bool(multiply and (multiply[1].casefold()=='multiplier' or float(multiply[1])>1))
        loss=re.search(r'(?:profit|pnl|unrealized)\w*\s*<\s*0|last_loss|after_loss|averaging_down',context,re.I)
        if multiply and loss:
            findings.append(dict(flag='MARTINGALE_GRID_TOXICITY',confidence='HIGH_STATIC_PATTERN',evidence=row,
                meaning='Loss/adverse context near escalating size; confirm reachability before labeling a vendor.'))
    dates=evidence(r'(?:year|month|TimeYear|TimeMonth)\s*(?:\([^)]*\))?\s*==\s*(?:19\d\d|20\d\d)|datetime\s*\(\s*20\d\d')
    if dates:findings.append(dict(flag='BACKTEST_CHEAT_HARDCODED_DATES',confidence='REVIEW_ONLY',evidence=dates,
        meaning='Date conditioning detected; may be a legitimate holiday rather than cheating.'))
    for row in evidence(r'OrderSend\s*\(|\.Buy\s*\(|\.Sell\s*\(|order_send\s*\('):
        s=lines[row['line']-1]
        no_stop=bool(re.search(r'[\"\']sl[\"\']\s*:\s*0\b',s))
        m=re.search(r'OrderSend\(([^()]*)\)',s)
        if m:
            args=m.group(1).split(',');no_stop=no_stop or len(args)>5 and args[5].strip() in ('0','0.0')
        if no_stop:findings.append(dict(flag='NO_STOP_LOSS_TOXICITY',confidence='LITERAL_ORDER_NO_SL',evidence=row))
    if re.search(r'(?:exec|eval|__import__|pickle\.loads|subprocess|WebRequest|DllImport)\s*\(',code):
        findings.append(dict(flag='DYNAMIC_OR_EXTERNAL_BEHAVIOR',confidence='REVIEW_ONLY',evidence=evidence(r'exec|eval|__import__|pickle|subprocess|WebRequest|DllImport')))
    profile=BotDNAProfile('BotDNAProfile-v1',digest,suffix,indicators,timeframes,
        evidence(r'\b(?:if|elif)\b|OrderSend|\.Buy\(|\.Sell\(|ExecuteMarket(?:Range)?Order|order_send|strategy\.entry'),
        evidence(r'stop.?loss|\bsl\b|take.?profit|\btp\b|trail|breakeven|strategy\.exit'),
        evidence(r'hour|session|weekday|dayofweek|calendar|TimeHour'),sizing,findings,
        'PYTHON_AST_AND_STRUCTURAL_EVIDENCE' if suffix=='.py' else 'STRUCTURAL_PATTERNS_NOT_FULL_COMPILER',
        'BLOCKED_OR_REVIEW_REQUIRED' if findings else 'NO_FLAGS_DETECTED_REVIEW_REQUIRED')
    return dict(asdict(profile),execution_performed=False,hard_SL_proven=False,
        quant_core_contract=dict(status='TRANSLATION_AND_CAUSAL_PARITY_REQUIRED',automatic_backtest_authorized=False),
        limits=['No detected flag is not safety, edge, FTMO qualification or complete control-flow recovery.'])

class Tables(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(''.join(self.cell).strip());self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row)

def log_rows(raw,suffix):
    if len(raw)>16*1024*1024:raise ValueError('LOG_SIZE_LIMIT_16MIB')
    if suffix in {'.htm','.html','.xml'}:
        from quant_core.mt_report_parser import decode
        s=decode(raw)
    else:
        s=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    if suffix=='.json':
        v=json.loads(s);return v['trades'] if isinstance(v,dict) else v
    if suffix in ('.html','.htm'):
        p=Tables();p.feed(s)
        for i,row in enumerate(p.rows):
            if 'open_time' in row:return [dict(zip(row,r)) for r in p.rows[i+1:] if len(r)==len(row)]
        from quant_core.mt_report_parser import report_bytes
        result=report_bytes(raw,suffix)
        if not result["clone_ready"]:raise ValueError("REPORT_PAIRING_OR_GEOMETRY_INCOMPLETE")
        return result["trades"]
    if suffix=='.xml':
        from quant_core.mt_report_parser import report_bytes
        result=report_bytes(raw,suffix)
        if not result["clone_ready"]:raise ValueError("REPORT_PAIRING_OR_GEOMETRY_INCOMPLETE")
        return result["trades"]
    if suffix!='.csv':raise ValueError('CSV_HTML_JSON_LOG_REQUIRED')
    dialect=csv.Sniffer().sniff(s[:4096],delimiters=',;\t');return list(csv.DictReader(io.StringIO(s),dialect=dialect))

def fingerprint(rows,*,timezone_name=None,market_bars=None):
    from zoneinfo import ZoneInfo
    if len(rows)>50000:raise ValueError('LOG_ROW_LIMIT_50000')
    hours={};geometry=[];pending=[];latest={};escalations=0;unknown_loss_context=0
    def clock(value):
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if d.tzinfo is None:
            if timezone_name is None:raise ValueError('LOG_TIMEZONE_REQUIRED_NO_SERVER_GUESS')
            d=d.replace(tzinfo=ZoneInfo(timezone_name))
            if d.replace(fold=0).utcoffset()!=d.replace(fold=1).utcoffset() or d.astimezone(timezone.utc).astimezone(d.tzinfo).replace(tzinfo=None)!=d.replace(tzinfo=None):raise ValueError('AMBIGUOUS_LOG_CLOCK')
        return d
    rows=sorted(rows,key=lambda r:clock(r['open_time']))
    for serial,r in enumerate(rows):
        at=datetime.fromisoformat(str(r['open_time']).replace('Z','+00:00'))
        if at.tzinfo is None:
            if timezone_name is None:raise ValueError('LOG_TIMEZONE_REQUIRED_NO_SERVER_GUESS')
            at=at.replace(tzinfo=ZoneInfo(timezone_name))
            # Reject ambiguous/nonexistent local timestamps rather than choose a fold.
            a=at.replace(fold=0);b=at.replace(fold=1)
            if a.utcoffset()!=b.utcoffset() or at.astimezone(timezone.utc).astimezone(ZoneInfo(timezone_name)).replace(tzinfo=None)!=at.replace(tzinfo=None):raise ValueError('AMBIGUOUS_LOG_CLOCK')
        stamp=int(at.timestamp()*1000);hour=at.astimezone(timezone.utc).hour;hours[hour]=hours.get(hour,0)+1
        price=float(r['price']);sl=float(r.get('sl') or 0);tp=float(r.get('tp') or 0)
        if not all(math.isfinite(v) for v in (price,sl,tp)) or price<=0:raise ValueError('INVALID_TRADE_GEOMETRY')
        volume=float(r.get('volume') or 0);profit=float(r.get('profit') or 0)
        if not all(math.isfinite(v) for v in (volume,profit)) or volume<0:raise ValueError('INVALID_LOG_VOLUME_OR_PROFIT')
        while pending and pending[0][0]<=stamp:
            end,_,item=heapq.heappop(pending);latest[item['symbol']]=item
        if r['symbol'] in latest:
            previous=latest[r['symbol']]
            if previous['profit']<0 and previous['volume']>0 and volume>previous['volume']*1.5:escalations+=1
        else:unknown_loss_context+=1
        g=dict(symbol=r['symbol'],entry_msc=stamp,SL_distance=abs(price-sl) if sl>0 else None,TP_distance=abs(tp-price) if tp>0 else None,
            market_features_status='MARKET_DATA_REQUIRED',causal_strategy_recovered=False)
        if market_bars is not None:
            g.update(market_bars(r['symbol'],stamp,price,sl,tp))
        geometry.append(g)
        if r.get('close_time'):
            end=int(clock(r['close_time']).timestamp()*1000)
            if end<stamp:raise ValueError('LOG_CLOSE_BEFORE_ENTRY')
            heapq.heappush(pending,(end,serial,dict(symbol=r['symbol'],close=end,volume=volume,profit=profit)))
    return dict(schema='TradeLogFingerprint-v1',trades=len(rows),session_hour_UTC=hours,geometry=geometry,
        size_escalations_after_loss=escalations,unknown_prior_closed_loss_context=unknown_loss_context,algorithm_identifiable=False,
        quant_core_contract='OBSERVED_LOG_REPLAY_ONLY_NOT_CAUSAL_ALPHA',
        automatic_2018_2026_backtest=False,limits=['Trade logs alone do not identify a unique signal, missed trades or counterfactual fills.'])
