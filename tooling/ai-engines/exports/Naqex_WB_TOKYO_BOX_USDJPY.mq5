//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: TOKYO_BOX_OCO (USDJPY)
//| Provenance: protocol=5eb0506089d1 | spec_sha=27a005dbc7c6a756 | tier=TIER_2_PERSONAL_VAULT_CORE_ENGINE1
//| Rules: Tokyo Box [00:00..03:00 UTC), First-Touch OCO [03:00..10:00 UTC),
//|        Hard SL opposite edge, Hard Flat 18:00 Europe/Helsinki (swap=0), DryRun ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly      = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent        = 0.30;       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct    = 2.50;       // Internal circuit breaker (< 5% FTMO daily limit)
input int    InpBoxStartHourUTC    = 0;          // Tokyo box build start (UTC)
input int    InpBoxEndHourUTC      = 3;          // Tokyo box build end / activation start (UTC)
input int    InpActEndHourUTC      = 10;         // OCO activation window end (UTC)
input int    InpFlatHourHelsinki   = 18;         // Hard intraday flat hour (Europe/Helsinki, swap=0)
input long   InpMagicNumber        = 20261101;   // Unique magic number

datetime g_lastTradedDay = 0;
datetime g_boxDay        = 0;
bool     g_boxReady      = false;
double   g_boxTop        = 0.0;
double   g_boxBottom     = 0.0;
double   g_dayStartEq    = 0.0;
int      g_lastEqDay     = -1;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

// Exact EU DST helper for Europe/Helsinki (UTC+3 from last Sunday of March 01:00 UTC to last Sunday of October 01:00 UTC, else UTC+2)
int LastSundayOfMonth(const int year, const int month)
{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year;
   d.mon  = month;
   d.day  = 31;
   datetime t = StructToTime(d);
   TimeToStruct(t, d);
   return 31 - d.day_of_week;
}

int HelsinkiUtcOffsetHours(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 10) return 2;
   if(utc.mon > 3 && utc.mon < 10) return 3;
   int lastSun = LastSundayOfMonth(utc.year, utc.mon);
   if(utc.mon == 3)
      return (utc.day > lastSun || (utc.day == lastSun && utc.hour >= 1)) ? 3 : 2;
   return (utc.day < lastSun || (utc.day == lastSun && utc.hour < 1)) ? 3 : 2;
}

bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }
   return false;
}

void CloseOwnPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 &&
         PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }
   }
}

double ComputeLots(const double slDistancePrice)
{
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
}

void OnTick()
{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc;
   TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   datetime utcDay = nowUtc - (nowUtc % 86400);
   if(utc.day_of_year != g_lastEqDay)
   {
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }

   // Hard intraday flat at 18:00 Europe/Helsinki (exact DST-aware, swap = 0)
   int helOffset = HelsinkiUtcOffsetHours(utc);
   int flatUtcHour = InpFlatHourHelsinki - helOffset;
   if(utc.hour >= flatUtcHour)
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_18H_HELSINKI_SWAP0");
      return;
   }

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }

   // Track Tokyo box live during [00:00..03:00 UTC) using exact mid-quote extrema
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;
   double mid = 0.5 * (ask + bid);

   if(utcDay != g_boxDay)
   {
      g_boxDay = utcDay;
      g_boxReady = false;
      g_boxTop = 0.0;
      g_boxBottom = 0.0;
   }

   if(utc.hour >= InpBoxStartHourUTC && utc.hour < InpBoxEndHourUTC)
   {
      if(!g_boxReady)
      {
         g_boxTop = mid;
         g_boxBottom = mid;
         g_boxReady = true;
      }
      else
      {
         if(mid > g_boxTop) g_boxTop = mid;
         if(mid < g_boxBottom) g_boxBottom = mid;
      }
      return;
   }

   // First-touch OCO activation strictly within [03:00..10:00 UTC), max 1 trade/day
   if(!g_boxReady || g_boxTop <= g_boxBottom) return;
   if(utcDay == g_lastTradedDay || HasOpenPosition()) return;
   if(utc.hour < InpBoxEndHourUTC || utc.hour >= InpActEndHourUTC) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(ask >= g_boxTop)
   {
      double sl = NormalizeDouble(g_boxBottom, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {
         g_lastTradedDay = utcDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f box=[%.5f, %.5f]", _Symbol, lots, ask, sl, g_boxBottom, g_boxTop);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_TOKYO_BUY");
      }
   }
   else if(bid <= g_boxBottom)
   {
      double sl = NormalizeDouble(g_boxTop, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {
         g_lastTradedDay = utcDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f box=[%.5f, %.5f]", _Symbol, lots, bid, sl, g_boxBottom, g_boxTop);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_TOKYO_SELL");
      }
   }
}
