//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: EURJPY_VOLCOMP_EXP75 (EURJPY)           |
//| Provenance: protocol=a9de160e0de9 | holdout=47b1b17cc1ef | GO    |
//| Rules: Causal Vol-Compression (R5/R20 < 0.85) -> Exp 0.75 ATR    |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.50;       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMaxVolRatio5_20   = 0.85;       // Causal prior-day Range5 / Range20 compression ceiling
input double InpTrigAtrMult       = 0.75;       // Daily-open expansion trigger (x prior D1 ATR14)
input double InpSlAtrMult         = 0.75;       // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input int    InpEntryStartHourUTC = 7;          // Entry window start (UTC)
input int    InpEntryEndHourUTC   = 17;         // Entry window end (UTC)
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = 20261128;   // Unique magic number (Registry E6)

int g_atrHandle = INVALID_HANDLE;

int OnInit()
{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   return false;
}

void CloseOwnPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(InpDryRunLogOnly || InpGuardDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }
   }
}

bool IsVolCompressedCausal()
{
   double sum5 = 0.0, sum20 = 0.0;
   for(int s = 1; s <= 20; s++)
   {
      double rng = iHigh(_Symbol, PERIOD_D1, s) - iLow(_Symbol, PERIOD_D1, s);
      if(rng <= 0.0) return false;
      sum20 += rng;
      if(s <= 5) sum5 += rng;
   }
   return ((sum5 / 5.0) / (sum20 / 20.0)) < InpMaxVolRatio5_20;
}

void OnTick()
{
   g_guard.OnNewTickHousekeeping();
   MqlDateTime utc;
   TimeToStruct(g_guard.NowUTC(), utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC) || g_guard.IsNearBrokerSessionClose())
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }
   if(g_guard.IsInsideRedNewsWindow())
   {
      if(g_guard.IsInRedNewsPreFlattenWindow() && HasOpenPosition())
         CloseOwnPositions("NEWS_PRE_FLATTEN");
      return;
   }
   if(g_guard.IsDailyLossBreached())
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_OR_KILLSWITCH");
      return;
   }

   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(g_guard.AlreadyTradedToday(todayStart) || HasOpenPosition()) return;
   if(utc.hour < InpEntryStartHourUTC || utc.hour >= InpEntryEndHourUTC) return;
   if(!g_guard.IsSpreadAndSessionSafe()) return;
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
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, ask - sl);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, true, lots, ask, sl, "Naqex_WB_VOLCOMP_BUY", InpDryRunLogOnly))
         g_guard.MarkTradedToday(todayStart);
   }
   else if(bid <= bot)
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, sl - bid);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, false, lots, bid, sl, "Naqex_WB_VOLCOMP_SELL", InpDryRunLogOnly))
         g_guard.MarkTradedToday(todayStart);
   }
}
