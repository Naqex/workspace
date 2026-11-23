//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: USDJPY_NY_RISK_FLOW_10ET (USDJPY)
//| Provenance: protocol=a9de160e0de9 | spec_sha=9d664c297574f4b6 | tier=TIER_1_FTMO_DEMO_SPEC_BOUND
//| Rules: Post-Macro 10:00 ET Decision (US100.cash [09:30..10:00 ET) + G6 USD Basket Aligned)
//|        Hard Server SL, Hard Flat 20:55 UTC (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpEquitySymbol      = "US100.cash";  // Equity lead symbol
input double InpRiskPercent       = 0.50;            // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinEquityMoveAtr  = 0.25;            // Min |z(US100)| over [09:30..10:00 ET)
input double InpMinUsdBasketZ     = 0.25;            // Min |G6 USD factor| over [07:00 UTC..10:00 ET)
input double InpSlAtrMult         = 0.75;            // Hard SL distance (x prior D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input int    InpFlatHourUTC       = 20;              // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;              // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = 20261129;        // Unique magic number

string   g_usdSyms[5]   = {"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"};
int      g_usdSigns[5]  = {1, 1, -1, -1, -1};
int      g_usdAtr[5];
int      g_eqAtrHandle  = INVALID_HANDLE;
datetime g_lastEvalDay  = 0;
datetime g_sessDay      = 0;
bool     g_eqOpenReady  = false;
double   g_eqOpen0930   = 0.0;
double   g_dayStartEq   = 0.0;
int      g_lastEqDay    = -1;

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
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
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
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else trade.PositionClose(ticket);
      }
   }
}

double ComputeLots(const double slDistancePrice)
{
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
}

void OnTick()
{
   datetime nowUtc = TimeGMT();
   MqlDateTime utc; TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.day_of_year != g_lastEqDay)
   {
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }

   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }

   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }

   int nyOff = NewYorkUtcOffsetHours(utc);
   datetime nowNy = nowUtc + nyOff * 3600;
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
   {
      double ab[1];
      if(CopyBuffer(g_usdAtr[i], 0, 1, 1, ab) != 1 || ab[0] <= 0.0) return;
      double p1 = iClose(g_usdSyms[i], PERIOD_M1, 1);
      double p0 = iClose(g_usdSyms[i], PERIOD_M1, 1 + lbMins);
      if(p1 <= 0.0 || p0 <= 0.0) return;
      usdSum += g_usdSigns[i] * ((p1 - p0) / ab[0]);
   }
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
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.3f sl=%.3f zEq=%.3f usdFac=%.3f", _Symbol, lots, ask, sl, zEq, usdFac);
         else trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_NY10ET_BUY");
      }
   }
   else
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly) PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.3f sl=%.3f zEq=%.3f usdFac=%.3f", _Symbol, lots, bid, sl, zEq, usdFac);
         else trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_NY10ET_SELL");
      }
   }
}
