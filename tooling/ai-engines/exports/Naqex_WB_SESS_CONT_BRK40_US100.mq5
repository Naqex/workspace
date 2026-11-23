//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: SESS_CONT_BRK_40 (US100.cash)
//| Provenance: protocol=52a53cb785a6 | spec_sha=4234835bcf7f1678 | tier=PROVISIONAL_ENGINE4_UNMEASURED_DEMO
//| Rules: NYSE Morning [09:30..11:30 ET) Drive -> Afternoon Breakout [11:30..15:55 ET)
//|        Hard Server SL, Hard Flat 15:55 ET (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.50;       // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinMorningMoveAtr = 0.40;       // Min directional morning drive (x prior D1 ATR14)
input double InpCloseOuterPct     = 0.70;       // Morning close in outer 30% of morning range
input double InpSlAtrMult         = 0.65;       // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261124;   // Unique magic number

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
{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}

// Exact US DST helper for America/New_York (EDT UTC-4: 2nd Sun Mar -> 1st Sun Nov, else EST UTC-5)
int NthSundayOfMonth(const int year, const int month, const int nth)
{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year; d.mon = month; d.day = 1;
   TimeToStruct(StructToTime(d), d);
   int firstSun = 1 + ((7 - d.day_of_week) % 7);
   return firstSun + (nth - 1) * 7;
}

int NewYorkUtcOffsetHours(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 11) return -5;
   if(utc.mon > 3 && utc.mon < 11) return -4;
   if(utc.mon == 3)
   {
      int s2 = NthSundayOfMonth(utc.year, 3, 2);
      return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5;
   }
   int s1 = NthSundayOfMonth(utc.year, 11, 1);
   return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
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

   int nyOff = NewYorkUtcOffsetHours(utc);
   datetime nowNy = nowUtc + nyOff * 3600;
   MqlDateTime ny;
   TimeToStruct(nowNy, ny);
   datetime nyDay = nowNy - (nowNy % 86400);
   int nyMins = ny.hour * 60 + ny.min;

   if(utc.day_of_year != g_lastEqDay)
   {
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }

   // Hard intraday flat at 15:55 ET (swap = 0)
   if(nyMins >= 15 * 60 + 55)
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_1555_ET_SWAP0");
      return;
   }

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }

   if(nyDay != g_sessDay)
   {
      g_sessDay = nyDay; g_mornInit = false; g_mornFrozen = false; g_mornDir = 0;
   }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   // Track NYSE cash morning range [09:30..11:30 ET)
   if(nyMins >= 9 * 60 + 30 && nyMins < 11 * 60 + 30)
   {
      if(!g_mornInit)
      {
         g_mornOpen = bid; g_mornHigh = bid; g_mornLow = bid; g_mornClose = bid; g_mornInit = true;
      }
      else
      {
         if(bid > g_mornHigh) g_mornHigh = bid;
         if(bid < g_mornLow)  g_mornLow  = bid;
         g_mornClose = bid;
      }
      return;
   }

   // Freeze morning qualification strictly at >= 11:30 ET using prior completed D1 ATR14
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

   if(g_mornDir == 0 || nyDay == g_lastTradedDay || HasOpenPosition()) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrD1;
   if(g_mornDir == 1 && ask >= g_mornHigh)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {
         g_lastTradedDay = nyDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.2f sl=%.2f mHi=%.2f", _Symbol, lots, ask, sl, g_mornHigh);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_SESS_CONT_BUY");
      }
   }
   else if(g_mornDir == -1 && bid <= g_mornLow)
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {
         g_lastTradedDay = nyDay;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.2f sl=%.2f mLo=%.2f", _Symbol, lots, bid, sl, g_mornLow);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_SESS_CONT_SELL");
      }
   }
}
