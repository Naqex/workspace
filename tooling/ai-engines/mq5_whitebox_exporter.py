"""White-Box MQL5 (.mq5) exporter (FTMO-safe, zero-grid, hard-SL) and static open-source .mq5 intake auditor."""

import hashlib
import json
import re
from pathlib import Path

RED_FLAG_PATTERNS = {
    "DLL_IMPORT": re.compile(r"#import\s+[\"'][^\"']+\.dll[\"']", re.I),
    "WEB_REQUEST": re.compile(r"\bWebRequest\s*\(", re.I),
    "MARTINGALE_HINT": re.compile(r"(martingale|lot_?mult|recoverylot|doublelot)", re.I),
    "GRID_HINT": re.compile(r"(grid_?step|grid_?size|max_?grid|averaging|pyramid)", re.I),
    "ROLLOVER_SCALP_HINT": re.compile(r"(23:00|23:30).*(00:30|01:00)", re.I),
}
INPUT_RE = re.compile(r"^\s*(?:input|sinput)\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*=\s*([^;]+);", re.M)


def audit_open_source_mq5(source_text: str, *, filename: str = "unknown.mq5") -> dict:
    """Statically audit a plain-text open-source .mq5 file for FTMO red flags & extract input parameters.

    Strictly read-only static inspection; never executes or compiles untrusted source.
    """
    code_only = re.sub(r"/\*.*?\*/", "", source_text, flags=re.S)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    inputs = [
        {"type": m.group(1), "name": m.group(2), "default": m.group(3).strip()}
        for m in INPUT_RE.finditer(code_only)
    ]
    flags = [name for name, rx in RED_FLAG_PATTERNS.items() if rx.search(code_only)]
    has_sl = bool(re.search(r"(stoploss|stop_loss|\bsl\b|sl_?atr|inpsl)", code_only, re.I))
    if not has_sl:
        flags.append("NO_EXPLICIT_SL_TOKEN")
    verdict = "REJECT_PROP_RED_FLAGS" if flags else "CLEAN_FOR_PYTHON_REPLICATION"
    return {
        "filename": filename,
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:16],
        "lines": len(source_text.splitlines()),
        "input_count": len(inputs),
        "inputs": inputs[:40],
        "red_flags": flags,
        "intake_verdict": verdict,
    }


def export_exp_daily_open_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for a verified white-box Daily-Open Expansion spec.

    Safety invariants baked into generated code:
      - InpDryRunLogOnly defaults to TRUE (zero OrderSend until human enables explicitly on Demo/Paper)
      - Hard SL attached on every order (prior-day causal ATR14, zero lookahead)
      - Zero grid / zero martingale (max 1 position per magic/symbol per UTC day)
      - Intraday hard flat before rollover (swap = 0)
      - Prague/FTMO daily loss circuit breaker
    """
    symbol = str(spec["asset"])
    trig_atr = float(spec.get("trig_atr", 0.80))
    sl_atr = float(spec.get("sl_atr", 0.75))
    min_prev_rng_atr = float(spec.get("min_prev_range_atr", 0.0))
    risk_pct = float(spec.get("risk_pct", 0.50))
    start_h = int(spec.get("entry_start_utc_hour", 7))
    end_h = int(spec.get("entry_end_utc_hour", 17))
    flat_h = int(spec.get("flat_utc_hour", 20))
    flat_m = int(spec.get("flat_utc_min", 55))
    magic = int(spec.get("magic", 20261123))
    proto = str(spec.get("protocol_commit", "UNSPECIFIED"))
    tier = str(spec.get("tier", "TIER_2_PERSONAL_VAULT"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'EXP_DAILY_OPEN')} ({symbol})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Zero-Grid, Zero-Martingale, Hard-SL, Intraday swap=0, DryRun default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = {risk_pct:.2f};       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% FTMO daily limit)
input double InpTrigAtrMult       = {trig_atr:.2f};       // Expansion trigger from D1 open (x ATR14_D1)
input double InpSlAtrMult         = {sl_atr:.2f};       // Hard SL distance (x ATR14_D1)
input double InpMinPrevRangeAtr   = {min_prev_rng_atr:.2f};       // Causal prior-day range/ATR filter (0 = disabled)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input int    InpEntryStartHourUTC = {start_h};          // Entry window start (UTC)
input int    InpEntryEndHourUTC   = {end_h};         // Entry window end (UTC)
input int    InpFlatHourUTC       = {flat_h};         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = {flat_m};         // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = {magic};   // Unique magic number

int      g_atrHandle = INVALID_HANDLE;
datetime g_lastTradedDay = 0;
double   g_dayStartEquity = 0.0;
int      g_lastEquityDay = -1;

int OnInit()
{{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(PositionGetTicket(i) > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }}
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

void OnTick()
{{
   MqlDateTime utc;
   TimeToStruct(TimeGMT(), utc);
   if(utc.day_of_year != g_lastEquityDay)
   {{
      g_lastEquityDay = utc.day_of_year;
      g_dayStartEquity = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   // Hard intraday flat (swap = 0)
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }}

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0.0 && ((g_dayStartEquity - curEq) / g_dayStartEquity) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   // One trade max per UTC day, strictly within liquidity window
   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(todayStart == g_lastTradedDay || HasOpenPosition()) return;
   if(utc.hour < InpEntryStartHourUTC || utc.hour >= InpEntryEndHourUTC) return;

   // Causal prior completed D1 ATR14 (shift = 1)
   double atrBuf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return;
   double atrD1 = atrBuf[0];
   if(InpMinPrevRangeAtr > 0.0)
   {{
      double prevRng = iHigh(_Symbol, PERIOD_D1, 1) - iLow(_Symbol, PERIOD_D1, 1);
      if(prevRng < InpMinPrevRangeAtr * atrD1) return;
   }}
   double dayOpen = iOpen(_Symbol, PERIOD_D1, 0);
   if(dayOpen <= 0.0) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double top = dayOpen + InpTrigAtrMult * atrD1;
   double bot = dayOpen - InpTrigAtrMult * atrD1;
   double slDist = InpSlAtrMult * atrD1;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(ask >= top)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f atr=%.5f", _Symbol, lots, ask, sl, atrD1);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_EXP_BUY");
      }}
   }}
   else if(bid <= bot)
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f atr=%.5f", _Symbol, lots, bid, sl, atrD1);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_EXP_SELL");
      }}
   }}
}}
"""


def export_tokyo_box_oco_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for Engine #1 (USDJPY Tokyo-box OCO, Pass 6/7B).

    Faithful frozen rules:
      - Box build: [00:00..03:00 UTC) mid-extrema (mean of Bid and Ask high/low per M1 bar)
      - First-touch OCO activation window: [03:00..10:00 UTC), max 1 trade per UTC day
      - Structural hard SL placed at opposite box edge
      - Hard intraday flat at 18:00 Europe/Helsinki (exact EU DST-aware EET/EEST offset, swap = 0)
      - InpDryRunLogOnly defaults to TRUE (OrderSend = 0 until human explicitly enables on Demo/Paper)
      - Internal daily loss circuit breaker (2.5% < 5% FTMO limit), zero grid / zero martingale
    """
    symbol = str(spec.get("asset", "USDJPY"))
    risk_pct = float(spec.get("risk_pct", 0.30))
    box_start_h = int(spec.get("box_start_utc_hour", 0))
    box_end_h = int(spec.get("box_end_utc_hour", 3))
    act_end_h = int(spec.get("activation_end_utc_hour", 10))
    flat_hel_h = int(spec.get("flat_helsinki_hour", 18))
    magic = int(spec.get("magic", 20261101))
    proto = str(spec.get("protocol_commit", "UNSPECIFIED"))
    tier = str(spec.get("tier", "TIER_2_PERSONAL_VAULT"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'TOKYO_BOX_OCO')} ({symbol})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Tokyo Box [00:00..03:00 UTC), First-Touch OCO [03:00..10:00 UTC),
//|        Hard SL opposite edge, Hard Flat 18:00 Europe/Helsinki (swap=0), DryRun ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly      = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent        = {risk_pct:.2f};       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct    = 2.50;       // Internal circuit breaker (< 5% FTMO daily limit)
input int    InpBoxStartHourUTC    = {box_start_h};          // Tokyo box build start (UTC)
input int    InpBoxEndHourUTC      = {box_end_h};          // Tokyo box build end / activation start (UTC)
input int    InpActEndHourUTC      = {act_end_h};         // OCO activation window end (UTC)
input int    InpFlatHourHelsinki   = {flat_hel_h};         // Hard intraday flat hour (Europe/Helsinki, swap=0)
input long   InpMagicNumber        = {magic};   // Unique magic number

datetime g_lastTradedDay = 0;
datetime g_boxDay        = 0;
bool     g_boxReady      = false;
double   g_boxTop        = 0.0;
double   g_boxBottom     = 0.0;
double   g_dayStartEq    = 0.0;
int      g_lastEqDay     = -1;

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

// Exact EU DST helper for Europe/Helsinki (UTC+3 from last Sunday of March 01:00 UTC to last Sunday of October 01:00 UTC, else UTC+2)
int LastSundayOfMonth(const int year, const int month)
{{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year;
   d.mon  = month;
   d.day  = 31;
   datetime t = StructToTime(d);
   TimeToStruct(t, d);
   return 31 - d.day_of_week;
}}

int HelsinkiUtcOffsetHours(const MqlDateTime &utc)
{{
   if(utc.mon < 3 || utc.mon > 10) return 2;
   if(utc.mon > 3 && utc.mon < 10) return 3;
   int lastSun = LastSundayOfMonth(utc.year, utc.mon);
   if(utc.mon == 3)
      return (utc.day > lastSun || (utc.day == lastSun && utc.hour >= 1)) ? 3 : 2;
   return (utc.day < lastSun || (utc.day == lastSun && utc.hour < 1)) ? 3 : 2;
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(PositionGetTicket(i) > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }}
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

void OnTick()
{{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc;
   TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   datetime utcDay = nowUtc - (nowUtc % 86400);
   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   // Hard intraday flat at 18:00 Europe/Helsinki (exact DST-aware, swap = 0)
   int helOffset = HelsinkiUtcOffsetHours(utc);
   int flatUtcHour = InpFlatHourHelsinki - helOffset;
   if(utc.hour >= flatUtcHour)
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_18H_HELSINKI_SWAP0");
      return;
   }}

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   // Track Tokyo box live during [00:00..03:00 UTC) using exact mid-quote extrema
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;
   double mid = 0.5 * (ask + bid);

   if(utcDay != g_boxDay)
   {{
      g_boxDay = utcDay;
      g_boxReady = false;
      g_boxTop = 0.0;
      g_boxBottom = 0.0;
   }}

   if(utc.hour >= InpBoxStartHourUTC && utc.hour < InpBoxEndHourUTC)
   {{
      if(!g_boxReady)
      {{
         g_boxTop = mid;
         g_boxBottom = mid;
         g_boxReady = true;
      }}
      else
      {{
         if(mid > g_boxTop) g_boxTop = mid;
         if(mid < g_boxBottom) g_boxBottom = mid;
      }}
      return;
   }}

   // First-touch OCO activation strictly within [03:00..10:00 UTC), max 1 trade/day
   if(!g_boxReady || g_boxTop <= g_boxBottom) return;
   if(utcDay == g_lastTradedDay || HasOpenPosition()) return;
   if(utc.hour < InpBoxEndHourUTC || utc.hour >= InpActEndHourUTC) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(ask >= g_boxTop)
   {{
      double sl = NormalizeDouble(g_boxBottom, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         g_lastTradedDay = utcDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f box=[%.5f, %.5f]", _Symbol, lots, ask, sl, g_boxBottom, g_boxTop);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_TOKYO_BUY");
      }}
   }}
   else if(bid <= g_boxBottom)
   {{
      double sl = NormalizeDouble(g_boxTop, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         g_lastTradedDay = utcDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f box=[%.5f, %.5f]", _Symbol, lots, bid, sl, g_boxBottom, g_boxTop);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_TOKYO_SELL");
      }}
   }}
}}
"""


def export_sess_cont_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO/The5ers-safe MQL5 (.mq5) EA for US100 Cross-Session Morning->Afternoon Continuation.

    Faithful Pass 24 rules (SESS_CONT_BRK_40 US100, swap = 0):
      - NYSE Cash Morning Window: [09:30..11:30 America/New_York) with exact US DST helper (EDT UTC-4 / EST UTC-5)
      - Directional qualification at 11:30 ET: |close - open| >= 0.40 * ATR14_D1 and close in outer 30% of morning range
      - Afternoon breakout continuation strictly inside [11:30..15:55 ET), max 1 trade/day
      - Hard server-side SL (0.65 * prior D1 ATR14), hard intraday flat 15:55 ET (swap = 0)
      - InpDryRunLogOnly = true by default (OrderSend = 0), 2.5% internal daily loss circuit breaker, zero grid/martingale
    """
    symbol = str(spec.get("asset", "US100.cash"))
    min_move_atr = float(spec.get("min_move_atr", 0.40))
    close_pct = float(spec.get("close_pct", 0.70))
    sl_atr = float(spec.get("sl_atr", 0.65))
    risk_pct = float(spec.get("risk_pct", 0.50))
    magic = int(spec.get("magic", 20261124))
    proto = str(spec.get("protocol_commit", "UNSPECIFIED"))
    tier = str(spec.get("tier", "PROVISIONAL_ENGINE4_UNMEASURED_DEMO"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'SESS_CONT_BRK_40')} ({symbol})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: NYSE Morning [09:30..11:30 ET) Drive -> Afternoon Breakout [11:30..15:55 ET)
//|        Hard Server SL, Hard Flat 15:55 ET (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = {risk_pct:.2f};       // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinMorningMoveAtr = {min_move_atr:.2f};       // Min directional morning drive (x prior D1 ATR14)
input double InpCloseOuterPct     = {close_pct:.2f};       // Morning close in outer 30% of morning range
input double InpSlAtrMult         = {sl_atr:.2f};       // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = {magic};   // Unique magic number

int      g_atrHandle     = INVALID_HANDLE;
datetime g_lastTradedDay = 0;
datetime g_sessDay       = 0;
bool     g_mornInit      = false;
bool     g_mornFrozen    = false;
double   g_mornOpen      = 0.0;
double   g_mornHigh      = 0.0;
double   g_mornLow       = 0.0;
double   g_mornClose     = 0.0;
int      g_mornDir       = 0;
double   g_dayStartEq    = 0.0;
int      g_lastEqDay     = -1;

int OnInit()
{{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}}

// Exact US DST helper for America/New_York (EDT UTC-4: 2nd Sun Mar -> 1st Sun Nov, else EST UTC-5)
int NthSundayOfMonth(const int year, const int month, const int nth)
{{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year; d.mon = month; d.day = 1;
   TimeToStruct(StructToTime(d), d);
   int firstSun = 1 + ((7 - d.day_of_week) % 7);
   return firstSun + (nth - 1) * 7;
}}

int NewYorkUtcOffsetHours(const MqlDateTime &utc)
{{
   if(utc.mon < 3 || utc.mon > 11) return -5;
   if(utc.mon > 3 && utc.mon < 11) return -4;
   if(utc.mon == 3)
   {{
      int s2 = NthSundayOfMonth(utc.year, 3, 2);
      return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5;
   }}
   int s1 = NthSundayOfMonth(utc.year, 11, 1);
   return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(PositionGetTicket(i) > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }}
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

void OnTick()
{{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc;
   TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   int nyOff = NewYorkUtcOffsetHours(utc);
   datetime nowNy = nowUtc + nyOff * 3600;
   MqlDateTime ny;
   TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   // Hard intraday flat at 15:55 ET (swap = 0)
   if(nyMins >= 15 * 60 + 55)
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_1555_ET_SWAP0");
      return;
   }}

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   if(nyDay != g_sessDay)
   {{
      g_sessDay = nyDay; g_mornInit = false; g_mornFrozen = false; g_mornDir = 0;
   }}

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   // Track NYSE cash morning range [09:30..11:30 ET)
   if(nyMins >= 9 * 60 + 30 && nyMins < 11 * 60 + 30)
   {{
      if(!g_mornInit)
      {{
         g_mornOpen = bid; g_mornHigh = bid; g_mornLow = bid; g_mornClose = bid; g_mornInit = true;
      }}
      else
      {{
         if(bid > g_mornHigh) g_mornHigh = bid;
         if(bid < g_mornLow)  g_mornLow  = bid;
         g_mornClose = bid;
      }}
      return;
   }}

   // Freeze morning qualification strictly at >= 11:30 ET using prior completed D1 ATR14
   double atrBuf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return;
   double atrD1 = atrBuf[0];

   if(!g_mornFrozen && nyMins >= 11 * 60 + 30)
   {{
      g_mornFrozen = true;
      double mrng = g_mornHigh - g_mornLow;
      if(g_mornInit && mrng > 0.0 && MathAbs(g_mornClose - g_mornOpen) >= InpMinMorningMoveAtr * atrD1)
      {{
         double pos = (g_mornClose - g_mornLow) / mrng;
         if(g_mornClose > g_mornOpen && pos >= InpCloseOuterPct) g_mornDir = 1;
         else if(g_mornClose < g_mornOpen && pos <= (1.0 - InpCloseOuterPct)) g_mornDir = -1;
      }}
   }}

   if(g_mornDir == 0 || nyDay == g_lastTradedDay || HasOpenPosition()) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrD1;
   if(g_mornDir == 1 && ask >= g_mornHigh)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         g_lastTradedDay = nyDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.2f sl=%.2f mHi=%.2f", _Symbol, lots, ask, sl, g_mornHigh);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_SESS_CONT_BUY");
      }}
   }}
   else if(g_mornDir == -1 && bid <= g_mornLow)
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         g_lastTradedDay = nyDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.2f sl=%.2f mLo=%.2f", _Symbol, lots, bid, sl, g_mornLow);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_SESS_CONT_SELL");
      }}
   }}
}}
"""


def export_idx_rs_lead_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for Engine #5 (IDX_RS_US100_LEAD_1130, Pass 26).

    Faithful causal rules:
      - Computes prior completed D1 ATR14 for both primary US100.cash and benchmark US500.cash (shift=1)
      - Measures NYSE morning [09:30..11:30 ET) ATR-normalized returns z100 and z500 using completed M1 bars
      - At 11:30 ET (window 11:30..11:40 ET, max 1 trade/day): if |z100 - z500| >= thr and z100 agrees with (z100 - z500),
        enters US100.cash in direction of lead (BUY if z100 > z500 and z100 > 0, SELL if z100 < z500 and z100 < 0)
      - Hard server-side SL (0.75 * prior D1 ATR14 of US100), hard intraday flat 15:55 ET (swap = 0)
      - InpDryRunLogOnly = true by default (OrderSend = 0), 2.5% internal daily loss circuit breaker, zero grid/martingale
    """
    symbol = str(spec.get("asset", "US100.cash"))
    bench = str(spec.get("benchmark", "US500.cash"))
    thr = float(spec.get("thr", 0.25))
    sl_atr = float(spec.get("sl_atr", 0.75))
    risk_pct = float(spec.get("risk_pct", 0.50))
    magic = int(spec.get("magic", 20261126))
    proto = str(spec.get("protocol_commit", "6b5938e7f087"))
    tier = str(spec.get("tier", "PROVISIONAL_ENGINE5"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'IDX_RS_US100_LEAD_1130')} ({symbol} vs {bench})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Causal NYSE Morning RS [09:30..11:30 ET) -> 11:30 ET Market Entry on {symbol}
//|        Hard Server SL, Hard Flat 15:55 ET (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpBenchmarkSymbol   = "{bench}";  // Benchmark index for causal relative strength
input double InpRiskPercent       = {risk_pct:.2f};            // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinRsDiffAtr      = {thr:.2f};            // Min |z(US100) - z(US500)| over [09:30..11:30 ET)
input double InpSlAtrMult         = {sl_atr:.2f};            // Hard SL distance (x prior completed D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = {magic};        // Unique magic number

int      g_atrMainHandle  = INVALID_HANDLE;
int      g_atrBenchHandle = INVALID_HANDLE;
datetime g_lastTradedDay  = 0;
datetime g_sessDay        = 0;
bool     g_openCaptured   = false;
double   g_mainOpen0930   = 0.0;
double   g_benchOpen0930  = 0.0;
double   g_dayStartEq     = 0.0;
int      g_lastEqDay      = -1;

int OnInit()
{{
   if(!SymbolSelect(InpBenchmarkSymbol, true)) return INIT_FAILED;
   g_atrMainHandle  = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   g_atrBenchHandle = iATR(InpBenchmarkSymbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrMainHandle == INVALID_HANDLE || g_atrBenchHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_atrMainHandle  != INVALID_HANDLE) IndicatorRelease(g_atrMainHandle);
   if(g_atrBenchHandle != INVALID_HANDLE) IndicatorRelease(g_atrBenchHandle);
}}

// Exact US DST helper for America/New_York (EDT UTC-4: 2nd Sun Mar -> 1st Sun Nov, else EST UTC-5)
int NthSundayOfMonth(const int year, const int month, const int nth)
{{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year; d.mon = month; d.day = 1;
   TimeToStruct(StructToTime(d), d);
   int firstSun = 1 + ((7 - d.day_of_week) % 7);
   return firstSun + (nth - 1) * 7;
}}

int NewYorkUtcOffsetHours(const MqlDateTime &utc)
{{
   if(utc.mon < 3 || utc.mon > 11) return -5;
   if(utc.mon > 3 && utc.mon < 11) return -4;
   if(utc.mon == 3)
   {{
      int s2 = NthSundayOfMonth(utc.year, 3, 2);
      return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5;
   }}
   int s1 = NthSundayOfMonth(utc.year, 11, 1);
   return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(PositionGetTicket(i) > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }}
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

void OnTick()
{{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc;
   TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   int nyOff = NewYorkUtcOffsetHours(utc);
   datetime nowNy = nowUtc + nyOff * 3600;
   MqlDateTime ny;
   TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   // Hard intraday flat at 15:55 ET (swap = 0)
   if(nyMins >= 15 * 60 + 55)
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_1555_ET_SWAP0");
      return;
   }}

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   if(nyDay != g_sessDay)
   {{
      g_sessDay = nyDay; g_openCaptured = false; g_mainOpen0930 = 0.0; g_benchOpen0930 = 0.0;
   }}

   // Capture causal completed M1 bid close strictly before 09:30 ET
   if(!g_openCaptured && nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35)
   {{
      double m0 = iClose(_Symbol, PERIOD_M1, 1);
      double b0 = iClose(InpBenchmarkSymbol, PERIOD_M1, 1);
      if(m0 > 0.0 && b0 > 0.0)
      {{
         g_mainOpen0930 = m0; g_benchOpen0930 = b0; g_openCaptured = true;
      }}
      return;
   }}

   // Evaluate strictly inside [11:30..11:40 ET), max 1 trade per day
   if(!g_openCaptured || nyDay == g_lastTradedDay || HasOpenPosition()) return;
   if(nyMins < 11 * 60 + 30 || nyMins >= 11 * 60 + 40) return;

   double atrMain[1], atrBench[1];
   if(CopyBuffer(g_atrMainHandle, 0, 1, 1, atrMain) != 1 || atrMain[0] <= 0.0) return;
   if(CopyBuffer(g_atrBenchHandle, 0, 1, 1, atrBench) != 1 || atrBench[0] <= 0.0) return;

   // Causal completed M1 close prior to 11:30 ET (shift = 1)
   double m1 = iClose(_Symbol, PERIOD_M1, 1);
   double b1 = iClose(InpBenchmarkSymbol, PERIOD_M1, 1);
   if(m1 <= 0.0 || b1 <= 0.0) return;

   double zMain  = (m1 - g_mainOpen0930)  / atrMain[0];
   double zBench = (b1 - g_benchOpen0930) / atrBench[0];
   double rsDiff = zMain - zBench;

   // Mark day evaluated even if no trade triggers (strictly single 11:30 ET decision)
   g_lastTradedDay = nyDay;
   if(MathAbs(rsDiff) < InpMinRsDiffAtr || (zMain * rsDiff) <= 0.0) return;

   int side = (rsDiff > 0.0) ? 1 : -1;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrMain[0];
   if(side == 1)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.2f sl=%.2f z100=%.3f z500=%.3f diff=%.3f", _Symbol, lots, ask, sl, zMain, zBench, rsDiff);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_IDX_RS_BUY");
      }}
   }}
   else
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.2f sl=%.2f z100=%.3f z500=%.3f diff=%.3f", _Symbol, lots, bid, sl, zMain, zBench, rsDiff);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_IDX_RS_SELL");
      }}
   }}
}}
"""


def export_fx_usd_basket_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for Satellite #6 (FX_USD_BASKET_12U_Z35, Pass 26).

    Faithful causal rules:
      - Computes prior completed D1 ATR14 across 7 G6 FX majors (USDJPY, GBPUSD, EURUSD, GBPJPY, AUDUSD, USDCAD, EURJPY)
      - Measures causal 5-hour [07:00..12:00 UTC) ATR-normalized return per pair from completed M1 closes
      - Decomposes USD macro basket factor = mean(z_USDJPY, z_USDCAD, -z_EURUSD, -z_GBPUSD, -z_AUDUSD)
      - At 12:00 UTC (window 12:00..12:10 UTC, max 1 trade/day): if |USD_factor| >= 0.35, picks strongest aligned
        non-JPY USD major among (GBPUSD, EURUSD, AUDUSD, USDCAD) and enters market with hard server SL (0.75 * D1 ATR14)
      - Hard intraday flat at 20:55 UTC (swap = 0), InpDryRunLogOnly = true by default, 2.5% internal daily circuit breaker
    """
    min_z = float(spec.get("min_z", 0.35))
    sl_atr = float(spec.get("sl_atr", 0.75))
    risk_pct = float(spec.get("risk_pct", 0.25))
    entry_h = int(spec.get("entry_h", 12))
    lb_h = int(spec.get("lb_h", 5))
    flat_h = int(spec.get("flat_utc_hour", 20))
    flat_m = int(spec.get("flat_utc_min", 55))
    magic = int(spec.get("magic", 20261127))
    proto = str(spec.get("protocol_commit", "6b5938e7f087"))
    tier = str(spec.get("tier", "TIER_2_SATELLITE_DEMO_BOUND"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'FX_USD_BASKET_12U_Z35')} (Multi-FX USD Basket Satellite)
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Causal G6 USD Basket [07:00..12:00 UTC) -> 12:00 UTC Strongest Aligned Non-JPY USD Major
//|        Hard Server SL, Hard Flat 20:55 UTC (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = {risk_pct:.2f};       // Satellite risk % per trade (recommended 0.25% core / 0.50% P1 boost)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinUsdBasketZ     = {min_z:.2f};       // Min |USD basket factor| over lookback window
input double InpSlAtrMult         = {sl_atr:.2f};       // Hard SL distance (x prior completed D1 ATR14)
input int    InpEntryHourUTC      = {entry_h};         // Decision hour (UTC)
input int    InpLookbackHours     = {lb_h};          // Causal lookback hours prior to entry
input int    InpFlatHourUTC       = {flat_h};         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = {flat_m};         // Intraday forced flat minute (UTC)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = {magic};   // Unique magic number

string   g_usdBasketSyms[5] = {{"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"}};
int      g_usdSigns[5]      = {{1, 1, -1, -1, -1}};
string   g_tradePool[4]     = {{"GBPUSD", "EURUSD", "AUDUSD", "USDCAD"}};
int      g_poolUsdBase[4]   = {{-1, -1, -1, 1}}; // +1 if USD is base (USDCAD), -1 if USD is quote
int      g_atrHandles[5];
int      g_lastEvaluatedDay = -1;
double   g_dayStartEq       = 0.0;
int      g_lastEqDay        = -1;

int OnInit()
{{
   for(int i = 0; i < 5; i++)
   {{
      if(!SymbolSelect(g_usdBasketSyms[i], true)) return INIT_FAILED;
      g_atrHandles[i] = iATR(g_usdBasketSyms[i], PERIOD_D1, InpAtrPeriodD1);
      if(g_atrHandles[i] == INVALID_HANDLE) return INIT_FAILED;
   }}
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   for(int i = 0; i < 5; i++)
      if(g_atrHandles[i] != INVALID_HANDLE) IndicatorRelease(g_atrHandles[i]);
}}

bool HasAnyOwnPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(PositionGetTicket(i) > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }}
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLotsForSymbol(const string sym, const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

bool CausalZReturn(const string sym, const int atrHandle, const int lookbackHours, double &outZ, double &outAtr)
{{
   double atrBuf[1];
   if(CopyBuffer(atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return false;
   outAtr = atrBuf[0];
   int lbBars = lookbackHours * 60;
   double p1 = iClose(sym, PERIOD_M1, 1);
   double p0 = iClose(sym, PERIOD_M1, 1 + lbBars);
   if(p1 <= 0.0 || p0 <= 0.0) return false;
   outZ = (p1 - p0) / outAtr;
   return true;
}}

void OnTick()
{{
   MqlDateTime utc;
   TimeToStruct(TimeGMT(), utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   // Hard intraday flat (swap = 0)
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {{
      if(HasAnyOwnPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }}

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasAnyOwnPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   // Single decision strictly at [InpEntryHourUTC:00 .. InpEntryHourUTC:10)
   if(utc.day_of_year == g_lastEvaluatedDay || HasAnyOwnPosition()) return;
   if(utc.hour != InpEntryHourUTC || utc.min >= 10) return;

   double zVals[5], atrVals[5];
   double usdSum = 0.0;
   for(int i = 0; i < 5; i++)
   {{
      if(!CausalZReturn(g_usdBasketSyms[i], g_atrHandles[i], InpLookbackHours, zVals[i], atrVals[i]))
         return;
      usdSum += g_usdSigns[i] * zVals[i];
   }}
   double usdFactor = usdSum / 5.0;
   g_lastEvaluatedDay = utc.day_of_year;

   if(MathAbs(usdFactor) < InpMinUsdBasketZ) return;
   int usdDir = (usdFactor > 0.0) ? 1 : -1;

   // Map tradePool indices into g_usdBasketSyms: GBPUSD=3, EURUSD=2, AUDUSD=4, USDCAD=1
   int mapIdx[4] = {{3, 2, 4, 1}};
   int bestPool = -1;
   double bestScore = -1e9;
   int bestSide = 0;
   for(int p = 0; p < 4; p++)
   {{
      int side = usdDir * g_poolUsdBase[p];
      double score = side * zVals[mapIdx[p]];
      if(score > bestScore)
      {{
         bestScore = score; bestPool = p; bestSide = side;
      }}
   }}
   if(bestPool < 0 || bestScore <= 0.0) return;

   string sym = g_tradePool[bestPool];
   double atrD1 = atrVals[mapIdx[bestPool]];
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrD1;
   if(bestSide == 1)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLotsForSymbol(sym, ask - sl);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f usdFac=%.3f score=%.3f", sym, lots, ask, sl, usdFactor, bestScore);
         else
            trade.Buy(lots, sym, ask, sl, 0.0, "Naqex_WB_USDBSK_BUY");
      }}
   }}
   else
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLotsForSymbol(sym, sl - bid);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f usdFac=%.3f score=%.3f", sym, lots, bid, sl, usdFactor, bestScore);
         else
            trade.Sell(lots, sym, bid, sl, 0.0, "Naqex_WB_USDBSK_SELL");
      }}
   }}
}}
"""


def export_volcomp_exp_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for Engine #6 (EURJPY_VOLCOMP_EXP75, Pass 28).

    Faithful causal rules:
      - Computes strictly completed prior 5-day vs 20-day D1 range ratio (shift 1..5 vs 1..20)
      - Only arms when vol_ratio < 0.85 (volatility compression regime)
      - Daily-open breakout +/- 0.75 * prior completed D1 ATR14 inside [07:00..17:00 UTC), hard server SL 0.75 * ATR14
      - Hard intraday flat at 20:55 UTC (swap = 0), InpDryRunLogOnly = true default, 2.5% internal daily breaker
    """
    symbol = str(spec.get("asset", "EURJPY"))
    trig_atr = float(spec.get("trig_atr", 0.75))
    sl_atr = float(spec.get("sl_atr", 0.75))
    max_vr = float(spec.get("max_vol_ratio", 0.85))
    risk_pct = float(spec.get("risk_pct", 0.50))
    magic = int(spec.get("magic", 20261128))
    proto = str(spec.get("protocol_commit", "a9de160e0de9"))
    tier = str(spec.get("tier", "TIER_1_FTMO_DEMO_SPEC_BOUND"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'EURJPY_VOLCOMP_EXP75')} ({symbol})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Causal Vol-Compression (R5/R20 < {max_vr:.2f}) -> Daily-Open Expansion ({trig_atr:.2f} ATR)
//|        Hard Server SL, Hard Flat 20:55 UTC (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = {risk_pct:.2f};       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMaxVolRatio5_20   = {max_vr:.2f};       // Causal prior-day Range5 / Range20 compression ceiling
input double InpTrigAtrMult       = {trig_atr:.2f};       // Daily-open expansion trigger (x prior D1 ATR14)
input double InpSlAtrMult         = {sl_atr:.2f};       // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input int    InpEntryStartHourUTC = 7;          // Entry window start (UTC)
input int    InpEntryEndHourUTC   = 17;         // Entry window end (UTC)
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = {magic};   // Unique magic number

int      g_atrHandle     = INVALID_HANDLE;
datetime g_lastTradedDay = 0;
double   g_dayStartEq    = 0.0;
int      g_lastEqDay     = -1;

int OnInit()
{{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

bool IsVolCompressedCausal()
{{
   double sum5 = 0.0, sum20 = 0.0;
   for(int s = 1; s <= 20; s++)
   {{
      double rng = iHigh(_Symbol, PERIOD_D1, s) - iLow(_Symbol, PERIOD_D1, s);
      if(rng <= 0.0) return false;
      sum20 += rng;
      if(s <= 5) sum5 += rng;
   }}
   return ((sum5 / 5.0) / (sum20 / 20.0)) < InpMaxVolRatio5_20;
}}

void OnTick()
{{
   MqlDateTime utc;
   TimeToStruct(TimeGMT(), utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }}

   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(todayStart == g_lastTradedDay || HasOpenPosition()) return;
   if(utc.hour < InpEntryStartHourUTC || utc.hour >= InpEntryEndHourUTC) return;
   if(!IsVolCompressedCausal()) return;

   double atrBuf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return;
   double atrD1 = atrBuf[0];
   double dayOpen = iOpen(_Symbol, PERIOD_D1, 0);
   if(dayOpen <= 0.0) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double top = dayOpen + InpTrigAtrMult * atrD1;
   double bot = dayOpen - InpTrigAtrMult * atrD1;
   double slDist = InpSlAtrMult * atrD1;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(ask >= top)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.3f sl=%.3f", _Symbol, lots, ask, sl);
         else trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_VOLCOMP_BUY");
      }}
   }}
   else if(bid <= bot)
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.3f sl=%.3f", _Symbol, lots, bid, sl);
         else trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_VOLCOMP_SELL");
      }}
   }}
}}
"""


def export_ny_risk_flow_10et_mq5(spec: dict) -> str:
    """Generate clean, auditable, FTMO-safe MQL5 (.mq5) EA source for Engine #7 (USDJPY_NY_RISK_FLOW_10ET, Pass 28).

    Faithful causal rules:
      - Strictly post-08:30/10:00 ET US macro news: evaluates at 10:00 ET (10:00..10:10 ET window, max 1 trade/day)
      - Measures US100 [09:30..10:00 ET) ATR-normalized move z_US100 and G6 USD Basket [07:00 UTC..10:00 ET)
      - Enters USDJPY in direction of aligned (z_US100 >= 0.25 and USD_factor >= 0.25, same sign)
      - Hard server SL 0.75 * prior D1 ATR14, hard flat 20:55 UTC (swap = 0), InpDryRunLogOnly = true default
    """
    symbol = str(spec.get("asset", "USDJPY"))
    eq_sym = str(spec.get("equity_symbol", "US100.cash"))
    thr = float(spec.get("thr", 0.25))
    usd_thr = float(spec.get("usd_thr", 0.25))
    sl_atr = float(spec.get("sl_atr", 0.75))
    risk_pct = float(spec.get("risk_pct", 0.50))
    magic = int(spec.get("magic", 20261129))
    proto = str(spec.get("protocol_commit", "a9de160e0de9"))
    tier = str(spec.get("tier", "TIER_1_FTMO_DEMO_SPEC_BOUND"))
    spec_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    return f"""//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: {spec.get('strategy', 'USDJPY_NY_RISK_FLOW_10ET')} ({symbol})
//| Provenance: protocol={proto[:12]} | spec_sha={spec_sha} | tier={tier}
//| Rules: Post-Macro 10:00 ET Decision ({eq_sym} [09:30..10:00 ET) + G6 USD Basket Aligned)
//|        Hard Server SL, Hard Flat 20:55 UTC (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpEquitySymbol      = "{eq_sym}";  // Equity lead symbol
input double InpRiskPercent       = {risk_pct:.2f};            // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinEquityMoveAtr  = {thr:.2f};            // Min |z(US100)| over [09:30..10:00 ET)
input double InpMinUsdBasketZ     = {usd_thr:.2f};            // Min |G6 USD factor| over [07:00 UTC..10:00 ET)
input double InpSlAtrMult         = {sl_atr:.2f};            // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input int    InpFlatHourUTC       = 20;              // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;              // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = {magic};        // Unique magic number

string   g_usdSyms[5]   = {{"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"}};
int      g_usdSigns[5]  = {{1, 1, -1, -1, -1}};
int      g_usdAtr[5];
int      g_eqAtrHandle  = INVALID_HANDLE;
datetime g_lastEvalDay  = 0;
datetime g_sessDay      = 0;
bool     g_eqOpenReady  = false;
double   g_eqOpen0930   = 0.0;
double   g_dayStartEq   = 0.0;
int      g_lastEqDay    = -1;

int OnInit()
{{
   if(!SymbolSelect(InpEquitySymbol, true)) return INIT_FAILED;
   g_eqAtrHandle = iATR(InpEquitySymbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_eqAtrHandle == INVALID_HANDLE) return INIT_FAILED;
   for(int i = 0; i < 5; i++)
   {{
      if(!SymbolSelect(g_usdSyms[i], true)) return INIT_FAILED;
      g_usdAtr[i] = iATR(g_usdSyms[i], PERIOD_D1, InpAtrPeriodD1);
      if(g_usdAtr[i] == INVALID_HANDLE) return INIT_FAILED;
   }}
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_eqAtrHandle != INVALID_HANDLE) IndicatorRelease(g_eqAtrHandle);
   for(int i = 0; i < 5; i++)
      if(g_usdAtr[i] != INVALID_HANDLE) IndicatorRelease(g_usdAtr[i]);
}}

int NthSundayOfMonth(const int year, const int month, const int nth)
{{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 1;
   TimeToStruct(StructToTime(d), d);
   return 1 + ((7 - d.day_of_week) % 7) + (nth - 1) * 7;
}}

int NewYorkUtcOffsetHours(const MqlDateTime &utc)
{{
   if(utc.mon < 3 || utc.mon > 11) return -5;
   if(utc.mon > 3 && utc.mon < 11) return -4;
   if(utc.mon == 3) {{ int s2 = NthSundayOfMonth(utc.year, 3, 2); return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5; }}
   int s1 = NthSundayOfMonth(utc.year, 11, 1);
   return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
}}

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   return false;
}}

void CloseOwnPositions(const string reason)
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {{
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else trade.PositionClose(ticket);
      }}
   }}
}}

double ComputeLots(const double slDistancePrice)
{{
   if(slDistancePrice <= 0.0) return 0.0;
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double volMax    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double volStep   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}}

void OnTick()
{{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc; TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.day_of_year != g_lastEqDay)
   {{
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }}

   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {{
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }}

   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {{
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }}

   int nyOff = NewYorkUtcOffsetHours(utc);
   datetime nowNy = nowUtc + nyOff * 3600;
   MqlDateTime ny; TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(nyDay != g_sessDay) {{ g_sessDay = nyDay; g_eqOpenReady = false; g_eqOpen0930 = 0.0; }}
   if(!g_eqOpenReady && nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35)
   {{
      double eq0 = iClose(InpEquitySymbol, PERIOD_M1, 1);
      if(eq0 > 0.0) {{ g_eqOpen0930 = eq0; g_eqOpenReady = true; }}
      return;
   }}

   // Single decision strictly inside [10:00..10:10 ET) (post-08:30 & post-10:00 US macro)
   if(!g_eqOpenReady || nyDay == g_lastEvalDay || HasOpenPosition()) return;
   if(nyMins < 10 * 60 || nyMins >= 10 * 60 + 10) return;

   double eqAtr[1], jpyAtr[1];
   if(CopyBuffer(g_eqAtrHandle, 0, 1, 1, eqAtr) != 1 || eqAtr[0] <= 0.0) return;
   if(CopyBuffer(g_usdAtr[0], 0, 1, 1, jpyAtr) != 1 || jpyAtr[0] <= 0.0) return;
   double eq1 = iClose(InpEquitySymbol, PERIOD_M1, 1);
   if(eq1 <= 0.0) return;
   double zEq = (eq1 - g_eqOpen0930) / eqAtr[0];

   int lbMins = MathMax(60, (utc.hour - 7) * 60 + utc.min);
   double usdSum = 0.0;
   for(int i = 0; i < 5; i++)
   {{
      double ab[1];
      if(CopyBuffer(g_usdAtr[i], 0, 1, 1, ab) != 1 || ab[0] <= 0.0) return;
      double p1 = iClose(g_usdSyms[i], PERIOD_M1, 1);
      double p0 = iClose(g_usdSyms[i], PERIOD_M1, 1 + lbMins);
      if(p1 <= 0.0 || p0 <= 0.0) return;
      usdSum += g_usdSigns[i] * ((p1 - p0) / ab[0]);
   }}
   double usdFac = usdSum / 5.0;
   g_lastEvalDay = nyDay;

   if(MathAbs(zEq) < InpMinEquityMoveAtr || MathAbs(usdFac) < InpMinUsdBasketZ || (zEq * usdFac) <= 0.0) return;
   int side = (usdFac > 0.0) ? 1 : -1;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * jpyAtr[0];
   if(side == 1)
   {{
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.3f sl=%.3f zEq=%.3f usdFac=%.3f", _Symbol, lots, ask, sl, zEq, usdFac);
         else trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_NY10ET_BUY");
      }}
   }}
   else
   {{
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {{
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.3f sl=%.3f zEq=%.3f usdFac=%.3f", _Symbol, lots, bid, sl, zEq, usdFac);
         else trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_NY10ET_SELL");
      }}
   }}
}}
"""


