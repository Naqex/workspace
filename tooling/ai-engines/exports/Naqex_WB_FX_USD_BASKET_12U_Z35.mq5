//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: FX_USD_BASKET_12U_Z35 (Multi-FX USD Basket Satellite)
//| Provenance: protocol=262d0e221e84 | spec_sha=15619b39562132b5 | tier=TIER_2_SATELLITE_DEMO_BOUND
//| Rules: Causal G6 USD Basket [07:00..12:00 UTC) -> 12:00 UTC Strongest Aligned Non-JPY USD Major
//|        Hard Server SL, Hard Flat 20:55 UTC (swap=0), Zero-Grid, DryRun Default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.25;       // Satellite risk % per trade (recommended 0.25% core / 0.50% P1 boost)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinUsdBasketZ     = 0.35;       // Min |USD basket factor| over lookback window
input double InpSlAtrMult         = 0.75;       // Hard SL distance (x prior completed D1 ATR14)
input int    InpEntryHourUTC      = 12;         // Decision hour (UTC)
input int    InpLookbackHours     = 5;          // Causal lookback hours prior to entry
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261127;   // Unique magic number

string   g_usdBasketSyms[5] = {"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"};
int      g_usdSigns[5]      = {1, 1, -1, -1, -1};
string   g_tradePool[4]     = {"GBPUSD", "EURUSD", "AUDUSD", "USDCAD"};
int      g_poolUsdBase[4]   = {-1, -1, -1, 1}; // +1 if USD is base (USDCAD), -1 if USD is quote
int      g_atrHandles[5];
int      g_lastEvaluatedDay = -1;
double   g_dayStartEq       = 0.0;
int      g_lastEqDay        = -1;

int OnInit()
{
   for(int i = 0; i < 5; i++)
   {
      if(!SymbolSelect(g_usdBasketSyms[i], true)) return INIT_FAILED;
      g_atrHandles[i] = iATR(g_usdBasketSyms[i], PERIOD_D1, InpAtrPeriodD1);
      if(g_atrHandles[i] == INVALID_HANDLE) return INIT_FAILED;
   }
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   for(int i = 0; i < 5; i++)
      if(g_atrHandles[i] != INVALID_HANDLE) IndicatorRelease(g_atrHandles[i]);
}

bool HasAnyOwnPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }
   return false;
}

void CloseOwnPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] Would close ticket=%I64u reason=%s", ticket, reason);
         else
            trade.PositionClose(ticket);
      }
   }
}

double ComputeLotsForSymbol(const string sym, const double slDistancePrice)
{
   if(slDistancePrice <= 0.0) return 0.0;
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney  = balance * (InpRiskPercent / 100.0);
   double tickSize   = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double volMin     = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double volMax     = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double volStep    = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;
   double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(rawLots < volMin) return 0.0;
   return MathMin(rawLots, volMax);
}

bool CausalZReturn(const string sym, const int atrHandle, const int lookbackHours, double &outZ, double &outAtr)
{
   double atrBuf[1];
   if(CopyBuffer(atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return false;
   outAtr = atrBuf[0];
   int lbBars = lookbackHours * 60;
   double p1 = iClose(sym, PERIOD_M1, 1);
   double p0 = iClose(sym, PERIOD_M1, 1 + lbBars);
   if(p1 <= 0.0 || p0 <= 0.0) return false;
   outZ = (p1 - p0) / outAtr;
   return true;
}

void OnTick()
{
   MqlDateTime utc;
   TimeToStruct(TimeGMT(), utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   if(utc.day_of_year != g_lastEqDay)
   {
      g_lastEqDay = utc.day_of_year;
      g_dayStartEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }

   // Hard intraday flat (swap = 0)
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {
      if(HasAnyOwnPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEq > 0.0 && ((g_dayStartEq - curEq) / g_dayStartEq) * 100.0 >= InpMaxDailyLossPct)
   {
      if(HasAnyOwnPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }

   // Single decision strictly at [InpEntryHourUTC:00 .. InpEntryHourUTC:10)
   if(utc.day_of_year == g_lastEvaluatedDay || HasAnyOwnPosition()) return;
   if(utc.hour != InpEntryHourUTC || utc.min >= 10) return;

   double zVals[5], atrVals[5];
   double usdSum = 0.0;
   for(int i = 0; i < 5; i++)
   {
      if(!CausalZReturn(g_usdBasketSyms[i], g_atrHandles[i], InpLookbackHours, zVals[i], atrVals[i]))
         return;
      usdSum += g_usdSigns[i] * zVals[i];
   }
   double usdFactor = usdSum / 5.0;
   g_lastEvaluatedDay = utc.day_of_year;

   if(MathAbs(usdFactor) < InpMinUsdBasketZ) return;
   int usdDir = (usdFactor > 0.0) ? 1 : -1;

   // Map tradePool indices into g_usdBasketSyms: GBPUSD=3, EURUSD=2, AUDUSD=4, USDCAD=1
   int mapIdx[4] = {3, 2, 4, 1};
   int bestPool = -1;
   double bestScore = -1e9;
   int bestSide = 0;
   for(int p = 0; p < 4; p++)
   {
      int side = usdDir * g_poolUsdBase[p];
      double score = side * zVals[mapIdx[p]];
      if(score > bestScore)
      {
         bestScore = score; bestPool = p; bestSide = side;
      }
   }
   if(bestPool < 0 || bestScore <= 0.0) return;

   string sym = g_tradePool[bestPool];
   double atrD1 = atrVals[mapIdx[bestPool]];
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double slDist = InpSlAtrMult * atrD1;
   if(bestSide == 1)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLotsForSymbol(sym, ask - sl);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f usdFac=%.3f score=%.3f", sym, lots, ask, sl, usdFactor, bestScore);
         else
            trade.Buy(lots, sym, ask, sl, 0.0, "Naqex_WB_USDBSK_BUY");
      }
   }
   else
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLotsForSymbol(sym, sl - bid);
      if(lots > 0.0)
      {
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f usdFac=%.3f score=%.3f", sym, lots, bid, sl, usdFactor, bestScore);
         else
            trade.Sell(lots, sym, bid, sl, 0.0, "Naqex_WB_USDBSK_SELL");
      }
   }
}
