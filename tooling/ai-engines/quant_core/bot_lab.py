"""Bounded static evidence and log fingerprints. Samples are data, never code."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
import ast,csv,hashlib,io,json,math,re,tokenize

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

def inspect_bytes(raw,suffix):
    if suffix not in SOURCE|BINARY:raise ValueError('UNSUPPORTED_BOT_FORMAT')
    if len(raw)>16*1024*1024:raise ValueError('BOT_SIZE_LIMIT_16MIB')
    digest=hashlib.sha256(raw).hexdigest();findings=[]
    if suffix in BINARY:
        strings=[s.decode('ascii',errors='replace') for s in re.findall(rb'[\x20-\x7e]{4,200}',raw)]
        strings += [s.decode('utf-16le',errors='replace') for s in re.findall(rb'(?:[\x20-\x7e]\x00){4,200}',raw)]
        names=sorted({n for s in strings for n in re.findall(r'(?:iMA|iATR|iRSI|iBands|iCustom|OrderSend|OrderClose|Buy|Sell|[A-Za-z0-9_]+\.dll)',s)})
        return dict(schema='BotBinaryForensics-v1',sha256=digest,format=suffix,bytes=len(raw),
            string_signatures=names[:256],PE_header=raw[:2]==b'MZ',python_magic_hex=raw[:4].hex() if suffix=='.pyc' else None,
            symbol_imports_status='NOT_PARSED',logic_recovery='UNAVAILABLE_FROM_STRINGS',
            admission='BINARY_ONLY_REVIEW_REQUIRED',execution_performed=False,confidence='LOW',
            limits=['Strings may be absent, dead or obfuscated; absence is not proof of safety.',
                'No original source recovery, DRM removal, DLL load or pyc deserialization.'])
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    if suffix=='.py':
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
    indicators=sorted(set(re.findall(r'\b(?:iMA|iATR|iRSI|iBands|iADX|iCustom|SMA|EMA|ATR|RSI|Donchian|SimpleMovingAverage|ExponentialMovingAverage|AverageTrueRange|RelativeStrengthIndex|BollingerBands|ta\.\w+)\b',code,re.I)))
    timeframes=sorted(set(re.findall(r'\b(?:PERIOD_(?:M\d+|H\d+|D1|W1)|TimeFrame\.\w+|timeframe\.\w+)\b',code)))
    sizing=evidence(r'lot|volume|multiplier|qty|position_size')
    for row in sizing:
        i=row['line']-1;context='\n'.join(lines[max(0,i-8):min(len(lines),i+9)])
        multiply=re.search(r'\b(?:lot\w*|volume\w*|qty)\s*(?:\*=\s*(?:[2-9]\d*(?:\.\d+)?|multiplier)|=\s*(?:lot\w*|volume\w*|qty)\s*\*\s*(?:[2-9]\d*|multiplier))',lines[i],re.I)
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
        evidence(r'\b(?:if|elif)\b|OrderSend|\.Buy\(|\.Sell\(|order_send|strategy\.entry'),
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
    s=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    if suffix=='.json':
        v=json.loads(s);return v['trades'] if isinstance(v,dict) else v
    if suffix in ('.html','.htm'):
        p=Tables();p.feed(s)
        for i,row in enumerate(p.rows):
            if 'open_time' in row:return [dict(zip(row,r)) for r in p.rows[i+1:] if len(r)==len(row)]
        raise ValueError('HTML_CANONICAL_TRADE_TABLE_REQUIRED')
    if suffix!='.csv':raise ValueError('CSV_HTML_JSON_LOG_REQUIRED')
    dialect=csv.Sniffer().sniff(s[:4096],delimiters=',;\t');return list(csv.DictReader(io.StringIO(s),dialect=dialect))

def fingerprint(rows,*,timezone_name=None,market_bars=None):
    from zoneinfo import ZoneInfo
    hours={};geometry=[];lots=[];previous=None;escalations=0
    for r in rows:
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
        if previous is not None and float(previous.get('profit') or 0)<0 and float(r.get('volume') or 0)>float(previous.get('volume') or 0)*1.5:escalations+=1
        g=dict(symbol=r['symbol'],entry_msc=stamp,SL_distance=abs(price-sl) if sl>0 else None,TP_distance=abs(tp-price) if tp>0 else None,
            market_features_status='MARKET_DATA_REQUIRED',causal_strategy_recovered=False)
        if market_bars is not None:
            g.update(market_bars(r['symbol'],stamp,price,sl,tp))
        geometry.append(g);previous=r
    return dict(schema='TradeLogFingerprint-v1',trades=len(rows),session_hour_UTC=hours,geometry=geometry,
        size_escalations_after_loss=escalations,algorithm_identifiable=False,
        quant_core_contract='OBSERVED_LOG_REPLAY_ONLY_NOT_CAUSAL_ALPHA',
        automatic_2018_2026_backtest=False,limits=['Trade logs alone do not identify a unique signal, missed trades or counterfactual fills.'])
