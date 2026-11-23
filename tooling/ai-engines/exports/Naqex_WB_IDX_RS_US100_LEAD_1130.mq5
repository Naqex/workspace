//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: IDX_RS_US100_LEAD_1130                  |
//| Provenance: protocol=262d0e221e84 | holdout=47b1b17cc1ef | GO    |
//| Rules: Causal NYSE Morning RS [09:30..11:30 ET) -> 11:30 Entry   |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpBenchmarkSymbol   = "US500.cash";    // Benchmark index for causal relative strength
input double InpRiskPercent       = 0.50;            // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinRsDiffAtr      = 0.25;            // Min |z(US100) - z(US500)| over [09:30..11:30 ET)
input double InpSlAtrMult         = 0.75;            // Hard SL distance (x prior completed D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261126;        // Unique magic number (Registry E5)

int      g_atrMainHandle  = INVALID_HANDLE;
int      g_atrBenchHandle = INVALID_HANDLE;
datetime g_sessDay        = 0;
bool     g_openCaptured   = false;
double   g_mainOpen0930   = 0.0;
double   g_benchOpen0930  = 0.0;

int OnInit()
{
   if(!SymbolSelect(InpBenchmarkSymbol, true)) return INIT_FAILED;
   g_atrMainHandle  = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   g_atrBenchHandle = iATR(InpBenchmarkSymbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrMainHandle == INVALID_HANDLE || g_atrBenchHandle == INVALID_HANDLE) return INIT_FAILED;
   g_guard.Init(trade, _Symbol, InpMagicNumber);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrMainHandle  != INVALID_HANDLE) IndicatorRelease(g_atrMainHandle);
   if(g_atrBenchHandle != INVALID_HANDLE) IndicatorRelease(g_atrBenchHandle);
}

int NthSundayOfMonth(const int year, const int month, const int nth)
{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 1;
   TimeToStruct(StructToTime(d), d);
   return 1 + ((7 - d.day_of_week) % 7) + (nth - 1) * 7;
}

int NewYorkUtcOffsetHours(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 11) return -5;
   if(utc.mon > 3 && utc.mon < 11) return -4;
   if(utc.mon == 3) { int s2 = NthSundayOfMonth(utc.year, 3, 2); return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5; }
   int s1 = NthSundayOfMonth(utc.year, 11, 1);
   return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
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

void OnTick()
{
   g_guard.OnNewTickHousekeeping();
   datetime nowUtc = g_guard.NowUTC();
   MqlDateTime utc; TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   datetime nowNy = nowUtc + NewYorkUtcOffsetHours(utc) * 3600;
   MqlDateTime ny; TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(nyMins >= 15 * 60 + 55 || g_guard.IsNearBrokerSessionClose())
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_1555_ET_SWAP0");
      return;
   }
   if(g_guard.IsInsideRedNewsWindow())
   {
      if(HasOpenPosition()) CloseOwnPositions("NEWS_PRE_FLATTEN");
      return;
   }
   if(g_guard.IsDailyLossBreached())
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_OR_KILLSWITCH");
      return;
   }

   if(nyDay != g_sessDay) { g_sessDay = nyDay; g_openCaptured = false; g_mainOpen0930 = 0.0; g_benchOpen0930 = 0.0; }

   if(!g_openCaptured && nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35)
   {
      double m0 = iClose(_Symbol, PERIOD_M1, 1);
      double b0 = iClose(InpBenchmarkSymbol, PERIOD_M1, 1);
      if(m0 > 0.0 && b0 > 0.0) { g_mainOpen0930 = m0; g_benchOpen0930 = b0; g_openCaptured = true; }
      return;
   }

   if(!g_openCaptured || g_guard.AlreadyTradedToday(nyDay) || HasOpenPosition()) return;
   if(nyMins < 11 * 60 + 30 || nyMins >= 11 * 60 + 40) return;
   if(!g_guard.IsSpreadAndSessionSafe()) return;

   double atrMain[1], atrBench[1];
   if(CopyBuffer(g_atrMainHandle, 0, 1, 1, atrMain) != 1 || atrMain[0] <= 0.0) return;
   if(CopyBuffer(g_atrBenchHandle, 0, 1, 1, atrBench) != 1 || atrBench[0] <= 0.0) return;

   double m1 = iClose(_Symbol, PERIOD_M1, 1);
   double b1 = iClose(InpBenchmarkSymbol, PERIOD_M1, 1);
   if(m1 <= 0.0 || b1 <= 0.0) return;

   double zMain  = (m1 - g_mainOpen0930)  / atrMain[0];
   double zBench = (b1 - g_benchOpen0930) / atrBench[0];
   double rsDiff = zMain - zBench;

   g_guard.MarkTradedToday(nyDay);
   if(MathAbs(rsDiff) < InpMinRsDiffAtr || (zMain * rsDiff) <= 0.0) return;

   int side = (rsDiff > 0.0) ? 1 : -1;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrMain[0];
   if(side == 1)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, ask - sl);
      if(lots > 0.0) g_guard.ExecuteChecked(trade, true, lots, ask, sl, "Naqex_WB_IDX_RS_BUY", InpDryRunLogOnly);
   }
   else
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, sl - bid);
      if(lots > 0.0) g_guard.ExecuteChecked(trade, false, lots, bid, sl, "Naqex_WB_IDX_RS_SELL", InpDryRunLogOnly);
   }
}
