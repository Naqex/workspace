"""Causal cash-session pullback policies and native Nautilus offline execution.

M1 extrema are a stop-touch envelope, never observed synchronous quotes/ticks.
No TP or other intraminute decision is allowed in this registered model.
"""
from collections import Counter, deque
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
from fractions import Fraction as F

import nautilus_trader
from nautilus_trader.indicators import AverageTrueRange, SimpleMovingAverage
from nautilus_trader.indicators.averages import MovingAverageType
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.common.config import LoggingConfig
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.data import BookOrder, QuoteTick
from nautilus_trader.model.enums import AccountType, AssetClass, BookType, OmsType, OrderSide, OrderType, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import Cfd
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy

M = 60000
NS = 60000000000
PAIRS = ((10, 40), (20, 80), (40, 160))
ID = InstrumentId.from_str('US500.RESEARCH')
USD = Currency.from_str('USD')


def configurations():
    values = [dict(lane=lane, fast=20, slow=80, k=str(D(i)/100))
              for lane in 'ABC' for i in range(0, 31, 5)]
    values += [dict(lane=lane, fast=f, slow=s, k='0.1')
               for f, s in ((10, 40), (40, 160)) for lane in 'ABC']
    for i, value in enumerate(values, 96):
        value['id'] = f'R{i:03}'
    return values


def aggregate(rows):
    return dict(open=D(str(rows[0]['open'])), high=max(D(str(r['high'])) for r in rows),
                low=min(D(str(r['low'])) for r in rows), close=D(str(rows[-1]['close'])))


class Indicators:
    def __init__(self):
        self.reset()

    def reset(self):
        self.closes = deque(maxlen=161)
        self.smas = {p: SimpleMovingAverage(p) for p in (10, 20, 40, 80, 160)}
        self.atr = AverageTrueRange(14, ma_type=MovingAverageType.WILDER, use_previous=True)
        self.exact_atr = None
        self.previous_close = None
        self.last = None

    def update(self, bar, day, t):
        tr = bar['high']-bar['low']
        if self.previous_close is not None:
            tr = max(tr, abs(bar['high']-self.previous_close), abs(bar['low']-self.previous_close))
        self.exact_atr = tr if self.exact_atr is None else (13*self.exact_atr+tr)/14
        self.previous_close = bar['close']
        self.atr.update_raw(float(bar['high']), float(bar['low']), float(bar['close']))
        self.closes.append(bar['close'])
        means = {}
        for p, native in self.smas.items():
            native.update_raw(float(bar['close']))
            if len(self.closes) >= p:
                means[p] = sum(list(self.closes)[-p:], D(0))/p
                if abs(D(str(native.value))-means[p]) > D('.0000001'):
                    raise ValueError('native_SMA_decimal_parity')
        if abs(D(str(self.atr.value))-self.exact_atr) > D('.0000001'):
            raise ValueError('native_ATR_decimal_parity')
        previous = self.last
        self.last = dict(**bar, means=means, atr=self.exact_atr, day=day, t=t,
                         previous=previous and {k:v for k,v in previous.items() if k != 'previous'},
                         common_m15_ready=len(self.closes) >= 161)
        return self.last


def prepare(sessions, pairs, progress=None):
    """Only completed prefixes affect a snapshot. No full-day quality lookahead."""
    indicators = Indicators()
    h1 = deque(maxlen=20)
    native_h1 = SimpleMovingAverage(20)
    bias = None
    snapshots, minute_context, missing = {}, {}, []
    previous_day = None
    counts = Counter()
    for number, (day, expected) in enumerate(sessions.items(), 1):
        blocked = False
        for i, t in enumerate(expected):
            close_t = t+M
            pair = pairs.get(t)
            minute_context[t] = dict(day=day, slot=i, blocked=blocked)
            if pair is None:
                blocked = True
                missing.append(t)
                counts['missing_minutes'] += 1
            minute_context[t]['blocked'] = blocked
            if (i+1) % 5:
                continue
            event = dict(day=day, slot=i+1, t=close_t, blocked=blocked,
                         full_session=len(expected)==390, m15=None, m5=None)
            fives = [pairs.get(x) for x in expected[i-4:i+1]]
            if all(fives):
                event['m5'] = aggregate([p[0] for p in fives])
            if (i+1) % 60 == 0:
                hours = [pairs.get(x) for x in expected[i-59:i+1]]
                if all(hours):
                    hb = aggregate([p[0] for p in hours])
                    h1.append(hb['close'])
                    native_h1.update_raw(float(hb['close']))
                    if len(h1)==20:
                        mean = sum(h1, D(0))/20
                        if abs(D(str(native_h1.value))-mean)>D('.0000001'):
                            raise ValueError('native_H1_SMA_decimal_parity')
                        bias = dict(day=day, t=close_t, close=hb['close'], mean=mean,
                                    side='BUY' if hb['close']>mean else 'SELL' if hb['close']<mean else 'NEUTRAL')
                else:
                    h1.clear()
                    native_h1.reset()
                    bias = None
                    counts['missing_h1'] += 1
            if (i+1) % 15 == 0:
                fifteens = [pairs.get(x) for x in expected[i-14:i+1]]
                if all(fifteens):
                    event['m15'] = indicators.update(aggregate([p[0] for p in fifteens]), day, close_t)
                else:
                    indicators.reset()
                    counts['missing_m15'] += 1
            allowed_bias = bias if bias and bias['day'] in (day, previous_day) else None
            event['bias'] = allowed_bias
            event['ready'] = bool(indicators.last and indicators.last['common_m15_ready'] and allowed_bias)
            if event['m15'] and event['ready']:
                counts['common_ready_m15'] += 1
            snapshots[close_t] = event
        previous_day = day
        if progress and number % 25 == 0:
            progress('preparing', done=number, total=len(sessions))
    return dict(snapshots=snapshots, minutes=minute_context, missing=set(missing), counts=dict(counts))


def direction(bar, fast, slow):
    if not bar or fast not in bar['means'] or slow not in bar['means']:
        return None
    a, b = bar['means'][fast], bar['means'][slow]
    return 'BUY' if a>b else 'SELL' if a<b else None


class Policy:
    def __init__(self, config):
        self.config, self.day, self.attempted, self.arm = config, None, False, None
        self.events = []

    def event(self, e, *, active=None, pending=False):
        c = self.config
        if self.day != e['day']:
            self.day, self.attempted, self.arm = e['day'], False, None
        m = e['m15']
        if active:
            if not pending and (e['slot']==150 or (m and direction(m,c['fast'],c['slow'])!=active)):
                return dict(action='exit', t=e['t'], reason='noon' if e['slot']==150 else 'trend_lost')
            return None
        if pending:
            return None
        if e['blocked']:
            if self.arm:
                self.events.append(dict(kind='cancel_gap', t=e['t']))
            self.arm = None
            return None
        if self.arm:
            arm = self.arm
            if m and direction(m,c['fast'],c['slow']) != arm['side']:
                self.events.append(dict(kind='cancel_trend', t=e['t']))
                self.arm = None
                return None
            bar = e['m5'] if c['lane']=='C' else m
            sign = D(1) if arm['side']=='BUY' else D(-1)
            threshold = arm['level']+sign*D(c['k'])*arm['atr']
            beyond=bar and int(sign)*(F(bar['close'])-F(arm['level'])-int(sign)*F(D(c['k']))*F(arm['atr']))>0
            if beyond and arm['t']<e['t']<=arm['expiry']:
                self.arm = None
                decision = dict(action='entry', t=e['t'], **{k:v for k,v in arm.items() if k!='t'},
                                arm_time=arm['t'], threshold=threshold)
                self.events.append(dict(kind='confirm', **decision))
                return decision
            if e['t']>=arm['expiry']:
                self.events.append(dict(kind='expire', t=e['t']))
                self.arm = None
            return None
        if self.attempted or not m or not e['ready'] or not e['full_session'] or e['slot'] not in (30,45,60,75):
            return None
        prev = m['previous']
        side = direction(m,c['fast'],c['slow'])
        if not side or not prev or prev['day']!=e['day'] or direction(prev,c['fast'],c['slow'])!=side:
            return None
        sign = D(1) if side=='BUY' else D(-1)
        if sign*(prev['close']-prev['means'][c['fast']])<=0 or sign*(m['close']-m['means'][c['fast']])>0 or m['atr']<=0:
            return None
        self.attempted = True
        if c['lane']!='A' and e['bias']['side']!=side:
            self.events.append(dict(kind='reject_h1', t=e['t'], side=side))
            return None
        self.arm = dict(side=side, level=m['high'] if side=='BUY' else m['low'], atr=m['atr'],
                        t=e['t'], expiry=min(e['t']+60*M, e['t']+(90-e['slot'])*M), bias=e['bias'])
        self.events.append(dict(kind='arm', **self.arm))
        return None


def instrument():
    return Cfd(instrument_id=ID, raw_symbol=Symbol('US500'), asset_class=AssetClass.INDEX,
               quote_currency=USD, price_precision=3, size_precision=2,
               price_increment=Price.from_str('0.001'), size_increment=Quantity.from_str('0.01'),
               min_quantity=Quantity.from_str('0.01'), max_quantity=Quantity.from_str('50.00'),
               margin_init=D('.1'), margin_maint=D('.1'), maker_fee=D(0), taker_fee=D(0), ts_event=0, ts_init=0)


def quote_data(pairs):
    inst = instrument()
    size = Quantity.from_str('1000000.00')
    values = []
    for t, (b,a) in sorted(pairs.items()):
        for phase, bid, ask in ((1,b['open'],a['open']), (NS-2,b['low'],a['high']), (NS,b['close'],a['close'])):
            stamp=t*1000000+phase
            values.append(QuoteTick(instrument_id=ID,bid_price=inst.make_price(bid),ask_price=inst.make_price(ask),
                                    bid_size=size,ask_size=size,ts_event=stamp,ts_init=stamp))
    return values


class AdverseFill(FillModel):
    """Native matching triggers stops; modeled envelope touch fills at stop, gaps at open."""
    def __init__(self, slip):
        super().__init__(prob_slippage=0, random_seed=0)
        self.slip, self.clock, self.strategy = D(slip), None, None

    def get_orderbook_for_fill_simulation(self, instrument, order, best_bid, best_ask):
        bid, ask = best_bid.as_decimal(), best_ask.as_decimal()
        ns=self.clock.timestamp_ns()
        if ns%NS==1 and self.strategy.position:
            p=self.strategy.position
            if p['last_minute']+M!=(ns-1)//1000000:
                p['unresolved']=True
        if order.order_type==OrderType.STOP_MARKET and self.clock.timestamp_ns()%NS==NS-2:
            # Bid.low/Ask.high say a barrier was reached, not what fill price existed then.
            bid = ask = order.trigger_price.as_decimal()
        bid -= self.slip
        ask += self.slip
        book = OrderBook(instrument_id=ID, book_type=BookType.L2_MBP)
        for n, side, px in ((1,OrderSide.BUY,bid),(2,OrderSide.SELL,ask)):
            book.add(BookOrder(side=side,price=instrument.make_price(px),size=Quantity.from_str('1000000.00'),order_id=n),0,0)
        return book


class Pullback(Strategy):
    def __init__(self, config, prepared, pairs, slip, progress=None, null=False):
        super().__init__(StrategyConfig(log_events=False,log_commands=False))
        self.policy, self.prepared, self.pairs = Policy(config), prepared, pairs
        self.slip, self.progress, self.null = D(slip), progress, null
        self.pending = self.position = self.stop_order = None
        self.fills, self.trades, self.rejections, self.gaps = [], [], [], []
        self.context = {}
        self.marks, self.balance, self.peak, self.dd = 0, D(10000), D(10000), D(0)
        self.noon_count = 0

    def on_start(self):
        self.subscribe_quote_ticks(ID)

    def submit_leg(self, side, qty, role, context, stop=None):
        args=dict(instrument_id=ID,order_side=OrderSide.BUY if side=='BUY' else OrderSide.SELL,
                  quantity=Quantity.from_str(f'{qty:.2f}'),reduce_only=role!='entry')
        if stop is None:
            order=self.order_factory.market(**args,time_in_force=TimeInForce.IOC)
        else:
            order=self.order_factory.stop_market(**args,trigger_price=Price.from_str(f'{stop:.3f}'))
            self.stop_order=order
        self.context[str(order.client_order_id)]=dict(role=role,**context)
        self.submit_order(order)

    def mark(self, bid, ask):
        equity=self.balance
        if self.position:
            p=self.position
            px=bid-self.slip if p['side']=='BUY' else ask+self.slip
            equity+=(px-p['entry'])*p['quantity']*(1 if p['side']=='BUY' else -1)
        self.peak=max(self.peak,equity)
        self.dd=max(self.dd,self.peak-equity)
        self.marks+=1

    def on_quote_tick(self, quote):
        ns=int(quote.ts_event)
        phase=ns%NS
        t=ns//1000000
        if phase==1:
            t=(ns-1)//1000000
            if self.position and self.position['last_minute']+M!=t:
                self.position['unresolved']=True
                self.gaps.append(dict(t=t,kind='held_path_gap'))
            if self.position:
                self.position['last_minute']=t
            if self.pending and t>=self.pending['t']+M:
                pending,self.pending=self.pending,None
                if t!=pending['t']+M:
                    self.rejections.append(dict(kind='missing_exact_fill',**pending))
                    if self.position:
                        self.position['unresolved']=True
                elif pending['action']=='entry' and not self.position:
                    if any(x in self.prepared['missing'] for x in range(pending['t'],t+1,M)):
                        self.rejections.append(dict(kind='entry_prefix_gap',**pending))
                        return
                    b,a=self.pairs[t]
                    side=pending['side']
                    fill=D(str(a['open']))+self.slip if side=='BUY' else D(str(b['open']))-self.slip
                    stop=fill-2*pending['atr'] if side=='BUY' else fill+2*pending['atr']
                    stop=(stop/D('.001')).to_integral_value(rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING)*D('.001')
                    distance=abs(fill-stop)+self.slip
                    qty=min(D(50),(D(25)/distance/D('.01')).to_integral_value(rounding=ROUND_FLOOR)*D('.01'))
                    if qty<D('.01') or fill*qty/10>self.balance or (side=='BUY' and stop>=D(str(b['open']))) or (side=='SELL' and stop<=D(str(a['open']))):
                        self.rejections.append(dict(kind='risk_or_margin',**pending))
                    else:
                        context=dict(decision=pending,stop=stop,expected_fill=fill,fill_time=t,planned_risk=qty*distance)
                        self.submit_leg(side,qty,'entry',context)
                elif pending['action']=='exit' and self.position:
                    if self.stop_order and not self.stop_order.is_closed:
                        self.cancel_order(self.stop_order)
                    self.submit_leg('SELL' if self.position['side']=='BUY' else 'BUY',self.position['quantity'],'exit',dict(reason=pending['reason']))
        if phase!=NS-2:
            self.mark(quote.bid_price.as_decimal(),quote.ask_price.as_decimal())
        if phase==0:
            e=self.prepared['snapshots'].get(t)
            if e:
                if self.position and any(x in self.prepared['missing'] for x in range(self.position['last_minute']+M,t,M)):
                    self.position['unresolved']=True
                decision=self.policy.event(e,active=self.position and self.position['side'],pending=self.pending is not None)
                if decision and not (self.null and decision['action']=='entry'):
                    self.pending=decision
                if e['slot']==150:
                    self.noon_count+=1
                    if self.progress and self.noon_count%25==0:
                        self.progress('simulating',done=self.noon_count,total=253)

    def on_order_filled(self, event):
        context=self.context[str(event.client_order_id)]
        price,qty=event.last_px.as_decimal(),event.last_qty.as_decimal()
        self.fills.append(dict(role=context['role'],side=event.order_side.name,price=price,quantity=qty,timestamp_ns=int(event.ts_event),
                               commission=event.commission.as_decimal()))
        if context['role']=='entry':
            if price!=context['expected_fill']:
                raise ValueError('native_entry_model_parity')
            self.position=dict(side=event.order_side.name,entry=price,quantity=qty,stop=context['stop'],entry_time=context['fill_time'],
                               last_minute=context['fill_time'],unresolved=False,planned_risk=context['planned_risk'],decision=context['decision'])
            self.submit_leg('SELL' if self.position['side']=='BUY' else 'BUY',qty,'stop',dict(reason='stop'),stop=context['stop'])
        else:
            if not self.position:
                raise ValueError('native_exit_without_position')
            p=self.position
            net=(price-p['entry'])*qty*(1 if p['side']=='BUY' else -1)
            rounded=net.quantize(D('.01'),rounding=ROUND_HALF_EVEN)
            self.balance+=rounded
            self.trades.append(dict(**p,exit=price,exit_ns=int(event.ts_event),reason=context['reason'],net=net,cash_net=rounded))
            self.position=None
            self.stop_order=None

    def on_order_rejected(self,event):
        raise ValueError('native_order_rejected:'+str(event.reason))

    def on_order_denied(self,event):
        raise ValueError('native_order_denied:'+str(event.reason))


def execute(config, prepared, pairs, quotes, slip, progress=None, null=False):
    if nautilus_trader.__version__!='1.231.0':
        raise ValueError('native_runtime_pin')
    engine=BacktestEngine(config=BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True),run_analysis=False))
    fill=AdverseFill(slip)
    strategy=Pullback(config,prepared,pairs,slip,progress,null)
    try:
        engine.add_venue(venue=Venue('RESEARCH'),oms_type=OmsType.NETTING,account_type=AccountType.MARGIN,
                         starting_balances=[Money(10000,USD)],base_currency=USD,default_leverage=D(10),
                         fill_model=fill,reject_stop_orders=False,bar_execution=False,trade_execution=False)
        engine.add_instrument(instrument())
        engine.add_strategy(strategy)
        fill.clock=strategy.clock
        fill.strategy=strategy
        engine.add_data(quotes)
        engine.run()
        account=engine.cache.account_for_venue(Venue('RESEARCH'))
        native_cash=account.balance_total(USD).as_decimal()
        native_realized=[p.realized_pnl.as_decimal() for p in engine.cache.positions() if p.is_closed]
        # Native Money converts through binary float at half-cent boundaries.
        # Validate each closed position separately; never hide a cash drift in a big tolerance.
        if len(native_realized)!=len(strategy.trades):
            raise ValueError('native_closed_position_census')
        if any(abs(a-t['cash_net'])>D('.01') for a,t in zip(native_realized,strategy.trades)):
            raise ValueError('native_per_position_money_reconciliation')
        if abs(native_cash-(D(10000)+sum(native_realized,D(0))))>D('.01'):
            raise ValueError('native_cash_decimal_reconciliation')
        return dict(config=config,native_version=nautilus_trader.__version__,null=null,slippage=D(slip),
                    trades=strategy.trades,fills=strategy.fills,policy_events=strategy.policy.events,
                    rejections=strategy.rejections,gaps=strategy.gaps,position=strategy.position,pending=strategy.pending,
                    native_cash=native_cash,decimal_cash=strategy.balance,endpoint_equity_dd=strategy.dd,
                    native_realized=native_realized,native_rounding_delta=native_cash-strategy.balance,
                    marks=strategy.marks,native_open_positions=len(engine.cache.positions_open()),
                    native_open_orders=len(engine.cache.orders_open()))
    finally:
        engine.dispose()
