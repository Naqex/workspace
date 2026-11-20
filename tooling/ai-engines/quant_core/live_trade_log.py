"""Normalize finite, untrusted trade-log fields without inventing fills or costs."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from zoneinfo import ZoneInfo

from quant_core.mt_report_parser import decode, extract_rows, key, report_bytes

SUFFIXES = frozenset({'.csv', '.html', '.htm', '.xml'})
ALIASES = {
    'open_time': ('opentime','opendate','entrytime','entrydate','openingtimestamp','openingtime','openingdate',
                  'entrytimestamp','timeopen','dateopen','entrydatetime','openingdatetime'),
    'close_time': ('closetime','closedate','exittime','exitdate','closingtimestamp','closingtime','closingdate',
                   'exittimestamp','timeclose','dateclose','exitdatetime','closingdatetime'),
    'symbol': ('symbol','pair','instrument','ticker','asset','market'),
    'direction': ('direction','action','side','type','position','tradedirection','buysell'),
    'lots': ('lots','lot','lotssize','lotsize','volumelots','sizeinlots','quantitylots'),
    'volume': ('volume','size','quantity','units','amount'),
    'open_price': ('openprice','entryprice','openingprice','priceopen','entryfillprice','price'),
    'sl': ('sl','stoploss','stoplossprice'),
    'initial_sl': ('initialsl','initialstop','initialstoploss','initialstoplossprice'),
    'tp': ('tp','takeprofit','takeprofitprice'),
    'close_price': ('closeprice','exitprice','closingprice','priceclose','exitfillprice'),
    'commission': ('commission','commissionusd','commissions'),
    'swap': ('swap','swapusd','financing','rollover'),
    'fee': ('fee','fees','tax','taxes'),
    'profit': ('profit','profitusd','pnl','pl','realizedpnl','realisedpnl','grossprofit','grosspnl','grossusd'),
    'net_profit': ('netprofit','netpnl','netpl','netprofitusd','netusd'),
    'currency': ('currency','accountcurrency','profitcurrency','pnlcurrency'),
    'pips': ('pips','netpips','profitpips'),
    'reported_r': ('r','rmultiple','realizedr','realisedr','netr','rr'),
    'outcome': ('wr','outcome','result'),
    'exit_reason': ('exitreason','closereason'),
    'journal_time': ('tradedate',),
}
CANON = {alias: name for name, aliases in ALIASES.items() for alias in aliases}
SYMBOL_ALIASES = {'US500':'US500.cash','SPX500':'US500.cash','US100':'USTEC','NAS100':'USTEC',
                  'USTEC.CASH':'USTEC','US100.CASH':'USTEC','GER40':'GER40','XAUUSD':'XAUUSD',
                  'US500.CASH':'US500.cash'}
UNKNOWN = {'','-','—','n/a','na','null','none','unknown','hidden','***'}
NON_TRADES = {'balance','credit','deposit','withdrawal','transfer','bonus','total','summary','adjustment'}
RECORD_LIMIT = 50_000


@dataclass(frozen=True)
class Trade:
    row: int
    symbol: str
    direction: str | None
    open_time: int | None = None
    close_time: int | None = None
    open_date: str | None = None
    close_date: str | None = None
    open_precision: str | None = None
    close_precision: str | None = None
    time_basis: str = 'reported_fill'
    lots: float | None = None
    open_price: float | None = None
    sl: float | None = None
    initial_sl: float | None = None
    tp: float | None = None
    close_price: float | None = None
    commission: float | None = None
    swap: float | None = None
    fee: float | None = None
    profit: float | None = None
    net_profit: float | None = None
    profit_currency: str | None = None
    pips: float | None = None
    reported_r: float | None = None
    outcome: str | None = None
    exit_reason: str | None = None

    @property
    def has_execution_clock(self):
        return self.time_basis == 'reported_fill' and self.open_time is not None and self.close_time is not None


def numeric(value, decimal_mark):
    value = str(value or '').strip().replace('\N{MINUS SIGN}','-') if value != 0 else '0'
    if value.lower() in UNKNOWN:
        return None
    sep = re.escape(decimal_mark)
    if not re.fullmatch(rf'[+-]?(?:\d+(?:{sep}\d+)?|{sep}\d+)', value):
        return None
    number = float(value.replace(decimal_mark,'.'))
    return number if isfinite(number) else None


def timestamp(value, timezone_name=None, date_order=None):
    s = str(value or '').strip()
    if s.lower() in UNKNOWN:
        return None, None, None
    s = re.sub(r'\s*\(GMT([+-])(\d{1,2})(?::(\d\d))?\)$',
               lambda m:f"{m[1]}{int(m[2]):02d}:{m[3] or '00'}",s,flags=re.I)
    s = re.sub(r'^\d{4}[./]\d\d[./]\d\d',
               lambda m:m[0].replace('.','-').replace('/','-'),s)
    if m := re.match(r'^(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?=$|[ T])',s):
        if date_order is None:
            # A leading month/day is accepted automatically only when unambiguous.
            a,b = int(m[1]),int(m[2])
            order = 'dmy' if a>12>=b else 'mdy' if b>12>=a else None
            if order is None:
                return None,None,None
        else:
            order=date_order
        d,mth=(int(m[1]),int(m[2])) if order=='dmy' else (int(m[2]),int(m[1]))
        s=f'{m[3]}-{mth:02d}-{d:02d}'+s[m.end():]
    s = re.sub(r'(?<=[ T])(\d)(?=:\d\d)',r'0\1',s).replace('Z','+00:00')
    try:
        d=datetime.fromisoformat(s)
    except ValueError:
        return None,None,None
    time_pattern = re.search(r'[ T]\d\d:(\d\d)(?::\d\d(?:\.(\d+))?)?',s)
    if time_pattern is None:
        return None,d.date().isoformat(),'day'
    precision = 'millisecond' if time_pattern[2] else 'second' if time_pattern[0].count(':')==2 else 'minute'
    if d.tzinfo is None:
        if timezone_name is None:
            return None,d.date().isoformat(),'local_'+precision
        z=ZoneInfo(timezone_name)
        first=d.replace(tzinfo=z,fold=0)
        second=d.replace(tzinfo=z,fold=1)
        if first.utcoffset()!=second.utcoffset() or (
                first.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)!=d):
            return None,d.date().isoformat(),'ambiguous_local_'+precision
        d=first
    return int(d.timestamp()*1000),d.date().isoformat(),precision


def header_keys(headers):
    names=[CANON.get(key(x)) for x in headers]
    if 'open_price' in names and names.count('open_price')==2 and 'close_price' not in names:
        j=len(names)-1-names[::-1].index('open_price')
        names[j]='close_price'
    clocks=[i for i,x in enumerate(headers) if key(x)=='time']
    if len(clocks)==2:
        names[clocks[0]],names[clocks[1]]='open_time','close_time'
    return names


def table(raw, suffix):
    if suffix=='.csv':
        s=decode(raw)
        sample=s.splitlines()
        if not sample:
            raise ValueError('EMPTY_TRADE_LOG')
        try:
            dialect=csv.Sniffer().sniff(sample[0],delimiters=',;\t')
        except csv.Error as exc:
            raise ValueError('TRADE_LOG_CSV_DELIMITER_UNKNOWN') from exc
        csv_rows=csv.reader(io.StringIO(s),dialect=dialect)
        headers=next(csv_rows)
        rows=list(csv_rows)
        return headers,rows,False,[],None
    if suffix not in SUFFIXES:
        raise ValueError('TRADE_LOG_FORMAT_REQUIRED')
    tables,_=extract_rows(raw,suffix)
    # Preserve true MT position/deal pairing and its incomplete-report warnings.
    mt=report_bytes(raw,suffix)
    if mt['trades'] and (mt['deals'] or any(
            {'type','volume','price','profit'} <= {key(h) for h in row} and
            bool({'ticket','position','order'} & {key(h) for h in row})
            for row in tables)):
        rows=mt['trades']
        headers=['Symbol','Side','Open Time','Close Time','Lots','Open Price','Close Price',
                 'SL','Initial SL','TP','Profit','Net Profit','Commission','Swap','Fee']
        names=('symbol','side','open_time','close_time','volume','price','close_price','audit_sl','audit_initial_sl','audit_tp',
               'gross_profit','audit_net_profit','commission','swap','fee')
        records=[[row.get(k) for k in names] for row in rows]
        return headers,records,True,mt['warnings'],'MT4_MT5_PAIRED'
    for i,headers in enumerate(tables):
        cols=set(header_keys(headers))
        if 'symbol' not in cols or not {'open_time','journal_time'}&cols:
            continue
        if not {'direction','profit','net_profit','reported_r'}&cols:
            continue
        rows=[]
        for row in tables[i+1:]:
            if len(row)!=len(headers):
                break
            rows.append(row)
        return headers,rows,False,mt['warnings'],None
    if mt['recognized_tables']:
        return [],[],True,mt['warnings'] or ['NO_RECONCILABLE_MT_POSITIONS'],'MT4_MT5_PAIRED'
    raise ValueError('TRADE_TABLE_HEADER_UNRECOGNIZED')


def normalize(raw, suffix, *, timezone_name=None, date_order=None, decimal_mark='.', volume_lots=False,
              stop_is_initial=False, profit_basis='reported', currency=None):
    headers, raw_rows, mt, warnings, layout=table(raw,suffix)
    if len(raw_rows)>RECORD_LIMIT:
        raise ValueError('TRADE_LOG_ROW_LIMIT_50000')
    names=header_keys(headers)
    journal={'journal_time','reported_r','outcome'}<=set(names) and 'open_time' not in names
    if journal:
        date_order=date_order or 'dmy'
        layout='PERFORMANCE_JOURNAL'
    if layout is None:
        layout='FLAT_TRADE_TABLE'
    if headers and 'symbol' not in names:
        raise ValueError('TRADE_LOG_SYMBOL_HEADER_REQUIRED')
    inferred_currency='USD' if any(key(h) in {'profitusd','netprofitusd','grossusd'} for h in headers) else None
    trades=[]
    rejects=Counter()
    for row_id, row in enumerate(raw_rows,1):
        if not any(row):
            continue
        if len(row)!=len(names):
            rejects['ROW_COLUMN_COUNT_MISMATCH']+=1
            continue
        data={}
        for col,value in zip(names,row):
            if col and value is not None and str(value).strip():
                if col in data and data[col]!=value:
                    data[col]=None
                    continue
                data[col]=value
        side=str(data.get('direction') or '').strip().casefold()
        if side in NON_TRADES:
            rejects['NON_TRADE_OR_CASH_FLOW']+=1
            continue
        raw_sym=str(data.get('symbol') or '').strip()
        compact=raw_sym.upper().replace('/','').replace(' ','')
        if not compact or compact in ('TOTAL','SUMMARY'):
            rejects['NO_TRADE_SYMBOL']+=1
            continue
        symbol=SYMBOL_ALIASES.get(compact,compact)
        if not re.fullmatch(r'[\w.+#-]{1,32}',symbol):
            rejects['UNSUPPORTED_SYMBOL_TEXT']+=1
            continue
        direction={'buy':'BUY','long':'BUY','sell':'SELL','short':'SELL'}.get(side)
        at,ad,ap=timestamp(data.get('journal_time' if journal else 'open_time'),timezone_name,date_order)
        end,ed,ep=timestamp(data.get('close_time'),timezone_name,date_order)
        if at is not None and end is not None and end<at:
            rejects['CLOSE_PRECEDES_OPEN']+=1
            continue
        nums={f:numeric(data.get(f),decimal_mark) for f in ('lots','volume','open_price','sl','initial_sl','tp',
                 'close_price','commission','swap','fee','profit','net_profit','pips','reported_r')}
        lots=nums['lots'] if nums['lots'] is not None else nums['volume'] if volume_lots or mt else None
        if lots is not None and lots<=0:
            lots=None
        sl=nums['sl'] if nums['sl'] is not None else nums['initial_sl']
        initial=nums['initial_sl'] if nums['initial_sl'] is not None else sl if stop_is_initial else None
        pnl=nums['profit']
        net=nums['net_profit']
        if net is None and profit_basis=='net':
            net=pnl
        if (net is None and (mt or profit_basis=='gross') and
                all(nums[k] is not None for k in ('profit','commission','swap'))):
            net=pnl+nums['commission']+nums['swap']+(nums['fee'] or 0.)
        cur=str(data.get('currency') or currency or inferred_currency or '').strip().upper()
        cur=cur if re.fullmatch(r'[A-Z]{3}',cur) else None
        out={'win':'WIN','loss':'LOSS','be':'BE','break even':'BE','breakeven':'BE'}.get(
            str(data.get('outcome') or '').strip().casefold())
        trade=Trade(row_id,symbol,direction,at,end,ad,ed,ap,ep,'journal_timestamp' if journal else 'reported_fill',
            lots,nums['open_price'] if nums['open_price'] and nums['open_price']>0 else None,sl,initial,nums['tp'],
            nums['close_price'] if nums['close_price'] and nums['close_price']>0 else None,
            nums['commission'],nums['swap'],nums['fee'],pnl,net,cur,nums['pips'],nums['reported_r'],out,
            'CALENDAR_CUTOFF' if key(data.get('exit_reason') or '') in {
               'calendarcutoff','fridaycutoff','holidaycutoff','sessionclose','hardflat'} else None)
        trades.append(trade)
    unknown={k:sum(getattr(t,k) is None for t in trades) for k in (
        'open_time','close_time','direction','lots','open_price','sl','initial_sl','tp','close_price',
        'commission','swap','profit','net_profit','profit_currency','pips','reported_r')}
    meta=dict(layout=layout, columns=[str(h)[:96] for h in headers], source_rows=len(raw_rows), accepted=len(trades),
              rejected=dict(rejects), unknown_counts=unknown, warnings=warnings,
              row_data_scope='OBSERVED_LOG_ONLY')
    return trades,meta
