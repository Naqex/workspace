//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: TOKYO_BOX_OCO (USDJPY)                  |
//| Provenance: protocol=5eb0506089d1 | holdout=47b1b17cc1ef | GO    |
//| Rules: Tokyo Box [00:00..03:00 UTC), First-Touch OCO [03:00..10) |
//|        Hard SL opposite edge, Hard Flat 18:00 Europe/Helsinki    |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly      = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent        = 0.16;       // Registry Cluster-A Inverse-DD base risk %
input double InpMaxDailyLossPct    = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input int    InpBoxStartHourUTC    = 0;          // Tokyo box build start (UTC)
input int    InpBoxEndHourUTC      = 3;          // Tokyo box build end / activation start (UTC)
input int    InpActEndHourUTC      = 10;         // OCO activation window end (UTC)
input int    InpFlatHourHelsinki   = 18;         // Hard intraday flat hour (Europe/Helsinki, swap=0)
input long   InpMagicNumber        = 20261122;   // Unique magic number (Registry E1)

datetime g_boxDay    = 0;
bool     g_boxReady  = false;
double   g_boxTop    = 0.0;
double   g_boxBottom = 0.0;

int OnInit()
{
   g_guard.Init(trade, _Symbol, InpMagicNumber);
   return INIT_SUCCEEDED;
}

int LastSundayOfMonth(const int year, const int month)
{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 31;
   TimeToStruct(StructToTime(d), d);
   return 31 - d.day_of_week;
}

int HelsinkiUtcOffsetHours(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 10) return 2;
   if(utc.mon > 3 && utc.mon < 10) return 3;
   int lastSun = LastSundayOfMonth(utc.year, utc.mon);
   if(utc.mon == 3) return (utc.day > lastSun || (utc.day == lastSun && utc.hour >= 1)) ? 3 : 2;
   return (utc.day < lastSun || (utc.day == lastSun && utc.hour < 1)) ? 3 : 2;
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
   MqlDateTime utc;
   TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   datetime utcDay = nowUtc - (nowUtc % 86400);
   int flatUtcHour = InpFlatHourHelsinki - HelsinkiUtcOffsetHours(utc);
   if(utc.hour >= flatUtcHour || g_guard.IsNearBrokerSessionClose())
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_18H_HELSINKI_SWAP0");
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

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;
   double mid = 0.5 * (ask + bid);

   if(utcDay != g_boxDay)
   {
      g_boxDay = utcDay; g_boxReady = false; g_boxTop = 0.0; g_boxBottom = 0.0;
   }
   if(utc.hour >= InpBoxStartHourUTC && utc.hour < InpBoxEndHourUTC)
   {
      if(!g_boxReady) { g_boxTop = mid; g_boxBottom = mid; g_boxReady = true; }
      else { if(mid > g_boxTop) g_boxTop = mid; if(mid < g_boxBottom) g_boxBottom = mid; }
      return;
   }

   if(!g_boxReady || g_boxTop <= g_boxBottom) return;
   if(g_guard.AlreadyTradedToday(utcDay) || HasOpenPosition()) return;
   if(utc.hour < InpBoxEndHourUTC || utc.hour >= InpActEndHourUTC) return;
   if(!g_guard.IsSpreadAndSessionSafe()) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(ask >= g_boxTop)
   {
      double sl = NormalizeDouble(g_boxBottom, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, ask - sl);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, true, lots, ask, sl, "Naqex_WB_TOKYO_BUY", InpDryRunLogOnly))
         g_guard.MarkTradedToday(utcDay);
   }
   else if(bid <= g_boxBottom)
   {
      double sl = NormalizeDouble(g_boxTop, digits);
      double lots = g_guard.ComputeSafeLots(InpRiskPercent, sl - bid);
      if(lots > 0.0 && g_guard.ExecuteChecked(trade, false, lots, bid, sl, "Naqex_WB_TOKYO_SELL", InpDryRunLogOnly))
         g_guard.MarkTradedToday(utcDay);
   }
}
