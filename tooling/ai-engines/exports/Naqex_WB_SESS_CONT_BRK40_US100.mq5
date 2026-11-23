//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: SESS_CONT_BRK_40 (US100.cash)           |
//| Provenance: protocol=262d0e221e84 | holdout=47b1b17cc1ef | GO    |
//| Rules: NYSE Morning [09:30..11:30 ET) Drive -> Breakout [11:30+) |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.50;       // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinMorningMoveAtr = 0.40;       // Min directional morning drive (x prior D1 ATR14)
input double InpCloseOuterPct     = 0.70;       // Morning close in outer 30% of morning range
input double InpSlAtrMult         = 0.65;       // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261124;   // Unique magic number (Registry E4)

int      g_atrHandle  = INVALID_HANDLE;
datetime g_sessDay    = 0;
bool     g_mornInit   = false;
bool     g_mornFrozen = false;
double   g_mornOpen   = 0.0;
double   g_mornHigh   = 0.0;
double   g_mornLow    = 0.0;
double   g_mornClose  = 0.0;
int      g_mornDir    = 0;

int OnInit()
{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   g_guard.Init(trade, _Symbol, InpMagicNumber);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
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

   if(nyDay != g_sessDay) { g_sessDay = nyDay; g_mornInit = false; g_mornFrozen = false; g_mornDir = 0; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   if(nyMins >= 9 * 60 + 30 && nyMins < 11 * 60 + 30)
   {
      if(!g_mornInit) { g_mornOpen = bid; g_mornHigh = bid; g_mornLow = bid; g_mornClose = bid; g_mornInit = true; }
      else { if(bid > g_mornHigh) g_mornHigh = bid; if(bid < g_mornLow) g_mornLow = bid; g_mornClose = bid; }
      return;
   }

   double atrBuf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return;
   double atrD1 = atrBuf[0];

   if(!g_mornFrozen && nyMins >= 11 * 60 + 30)
   {
      g_mornFrozen = true;
      double mrng = g_mornHigh - g_mornLow;
      if(g_mornInit && mrng > 0.0 && MathAbs(g_mornClose - g_mornOpen) >= InpMinMorningMoveAtr * atrD1)
      {
         double pos = (g_mornClose - g_mornLow) / mrng;
         if(g_mornClose > g_mornOpen && pos >= InpCloseOuterPct) g_mornDir = 1;
         else if(g_mornClose < g_mornOpen && pos <= (1.0 - InpCloseOuterPct)) g_mornDir = -1;
      }
   }

   if(g_mornDir == 0 || g_guard.AlreadyTradedToday(nyDay) || HasOpenPosition()) return;
   if(!g_guard.IsSpreadAndSessionSafe()) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrD1;
   if(g_mornDir == 1 && ask >= g_mornHigh)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, ask - sl);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, true, lots, ask, sl, "Naqex_WB_SESS_CONT_BUY", InpDryRunLogOnly))
         g_guard.MarkTradedToday(nyDay);
   }
   else if(g_mornDir == -1 && bid <= g_mornLow)
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, sl - bid);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, false, lots, bid, sl, "Naqex_WB_SESS_CONT_SELL", InpDryRunLogOnly))
         g_guard.MarkTradedToday(nyDay);
   }
}
