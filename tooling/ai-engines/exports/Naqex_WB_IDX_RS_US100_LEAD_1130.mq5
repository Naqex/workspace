//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: IDX_RS_US100_LEAD_1130 (US100.cash vs US500.cash)
//| Provenance: protocol=262d0e221e84 | spec_sha=a46c8cd9a415fdd2 | tier=TIER_1_FTMO_DEMO_SPEC_BOUND
//| Rules: Causal NYSE Morning RS [09:30..11:30 ET) -> 11:30 ET Market Entry on US100.cash
//|        Hard Server SL, Hard Flat 15:55 ET (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;            // SAFETY: true = log only, NO OrderSend
input string InpBenchmarkSymbol   = "US500.cash";  // Benchmark index for causal relative strength
input double InpRiskPercent       = 0.50;            // Fixed fractional risk % per trade (<= 1.0% cap)
input double InpMaxDailyLossPct   = 2.50;            // Internal circuit breaker (< 5% prop daily limit)
input double InpMinRsDiffAtr      = 0.25;            // Min |z(US100) - z(US500)| over [09:30..11:30 ET)
input double InpSlAtrMult         = 0.75;            // Hard SL distance (x prior completed D1 ATR14)
input int    InpAtrPeriodD1       = 14;              // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261126;        // Unique magic number

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
{
   if(!SymbolSelect(InpBenchmarkSymbol, true)) return INIT_FAILED;
   g_atrMainHandle  = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   g_atrBenchHandle = iATR(InpBenchmarkSymbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrMainHandle == INVALID_HANDLE || g_atrBenchHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrMainHandle  != INVALID_HANDLE) IndicatorRelease(g_atrMainHandle);
   if(g_atrBenchHandle != INVALID_HANDLE) IndicatorRelease(g_atrBenchHandle);
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
      g_sessDay = nyDay; g_openCaptured = false; g_mainOpen0930 = 0.0; g_benchOpen0930 = 0.0;
   }

   // Capture causal completed M1 bid close strictly before 09:30 ET
   if(!g_openCaptured && nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35)
   {
      double m0 = iClose(_Symbol, PERIOD_M1, 1);
      double b0 = iClose(InpBenchmarkSymbol, PERIOD_M1, 1);
      if(m0 > 0.0 && b0 > 0.0)
      {
         g_mainOpen0930 = m0; g_benchOpen0930 = b0; g_openCaptured = true;
      }
      return;
   }

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
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.2f sl=%.2f z100=%.3f z500=%.3f diff=%.3f", _Symbol, lots, ask, sl, zMain, zBench, rsDiff);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_IDX_RS_BUY");
      }
   }
   else
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.2f sl=%.2f z100=%.3f z500=%.3f diff=%.3f", _Symbol, lots, bid, sl, zMain, zBench, rsDiff);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_IDX_RS_SELL");
      }
   }
}
