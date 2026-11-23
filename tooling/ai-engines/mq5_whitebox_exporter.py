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
