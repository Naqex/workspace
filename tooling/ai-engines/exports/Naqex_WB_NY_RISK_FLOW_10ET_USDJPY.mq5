//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: USDJPY_NY_RISK_FLOW_10ET (USDJPY)       |
//| Provenance: protocol=a9de160e0de9 | holdout=47b1b17cc1ef | GO    |
//| Rules: Post-Macro 10:00 ET (US100.cash + G6 USD Basket Aligned)  |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpEquitySymbol      = "US100.cash";    // Equity lead symbol
input double InpRiskPercent       = 0.50;            // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinEquityMoveAtr  = 0.25;            // Min |z(US100)| over [09:30..10:00 ET)
input double InpMinUsdBasketZ     = 0.25;            // Min |G6 USD factor| over [07:00 UTC..10:00 ET)
input double InpSlAtrMult         = 0.75;            // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input int    InpFlatHourUTC       = 20;              // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;              // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = 20261129;        // Unique magic number (Registry E7)

string   g_usdSyms[5]   = {"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"};
int      g_usdSigns[5]  = {1, 1, -1, -1, -1};
int      g_usdAtr[5];
int      g_eqAtrHandle  = INVALID_HANDLE;
datetime g_sessDay      = 0;
bool     g_eqOpenReady  = false;
double   g_eqOpen0930   = 0.0;

int OnInit()
{
   if(!SymbolSelect(InpEquitySymbol, true)) return INIT_FAILED;
   g_eqAtrHandle = iATR(InpEquitySymbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_eqAtrHandle == INVALID_HANDLE) return INIT_FAILED;
   for(int i = 0; i < 5; i++)
   {
      if(!SymbolSelect(g_usdSyms[i], true)) return INIT_FAILED;
      g_usdAtr[i] = iATR(g_usdSyms[i], PERIOD_D1, InpAtrPeriodD1);
      if(g_usdAtr[i] == INVALID_HANDLE) return INIT_FAILED;
   }
   g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_eqAtrHandle != INVALID_HANDLE) IndicatorRelease(g_eqAtrHandle);
   for(int i = 0; i < 5; i++)
      if(g_usdAtr[i] != INVALID_HANDLE) IndicatorRelease(g_usdAtr[i]);
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

   datetime nowNy = nowUtc + NewYorkUtcOffsetHours(utc) * 3600;
   MqlDateTime ny; TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(nyDay != g_sessDay) { g_sessDay = nyDay; g_eqOpenReady = false; g_eqOpen0930 = 0.0; }
   if(!g_eqOpenReady && nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35)
   {
      double eq0 = iClose(InpEquitySymbol, PERIOD_M1, 1);
      if(eq0 > 0.0) { g_eqOpen0930 = eq0; g_eqOpenReady = true; }
      return;
   }

   if(!g_eqOpenReady || g_guard.AlreadyTradedToday(nyDay) || HasOpenPosition()) return;
   if(nyMins < 10 * 60 || nyMins >= 10 * 60 + 10) return;
   if(!g_guard.IsSpreadAndSessionSafe()) return;

   double eqAtr[1], jpyAtr[1];
   if(CopyBuffer(g_eqAtrHandle, 0, 1, 1, eqAtr) != 1 || eqAtr[0] <= 0.0) return;
   if(CopyBuffer(g_usdAtr[0], 0, 1, 1, jpyAtr) != 1 || jpyAtr[0] <= 0.0) return;
   double eq1 = iClose(InpEquitySymbol, PERIOD_M1, 1);
   if(eq1 <= 0.0) return;
   double zEq = (eq1 - g_eqOpen0930) / eqAtr[0];

   int lbMins = MathMax(60, (utc.hour - 7) * 60 + utc.min);
   double usdSum = 0.0;
   for(int i = 0; i < 5; i++)
   {
      double ab[1];
      if(CopyBuffer(g_usdAtr[i], 0, 1, 1, ab) != 1 || ab[0] <= 0.0) return;
      double p1 = iClose(g_usdSyms[i], PERIOD_M1, 1);
      double p0 = iClose(g_usdSyms[i], PERIOD_M1, 1 + lbMins);
      if(p1 <= 0.0 || p0 <= 0.0) return;
      usdSum += g_usdSigns[i] * ((p1 - p0) / ab[0]);
   }
   double usdFac = usdSum / 5.0;
   g_guard.MarkTradedToday(nyDay);

   if(MathAbs(zEq) < InpMinEquityMoveAtr || MathAbs(usdFac) < InpMinUsdBasketZ || (zEq * usdFac) <= 0.0) return;
   int side = (usdFac > 0.0) ? 1 : -1;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * jpyAtr[0];
   if(side == 1)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, ask - sl);
      if(lots > 0.0) g_guard.ExecuteChecked(trade, true, lots, ask, sl, "Naqex_WB_NY10ET_BUY", InpDryRunLogOnly);
   }
   else
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, sl - bid);
      if(lots > 0.0) g_guard.ExecuteChecked(trade, false, lots, bid, sl, "Naqex_WB_NY10ET_SELL", InpDryRunLogOnly);
   }
}
