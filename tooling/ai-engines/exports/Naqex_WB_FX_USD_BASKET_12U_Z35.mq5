//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: FX_USD_BASKET_12U_Z35 (Multi-FX Sat)    |
//| Provenance: protocol=262d0e221e84 | holdout=47b1b17cc1ef | GO    |
//| Rules: Causal G6 USD Basket [07:00..12:00 UTC) -> 12:00 Strong   |
//|        Full Naqex_PropGuard.mqh + Orchestrator + TCA CSV Logging |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.50;       // Satellite P1 risk % (disable or set 0.25% in Funded)
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% prop daily limit)
input double InpMinUsdBasketZ     = 0.35;       // Min |USD basket factor| over lookback window
input double InpSlAtrMult         = 0.75;       // Hard SL distance (x prior completed D1 ATR14)
input int    InpEntryHourUTC      = 12;         // Decision hour (UTC)
input int    InpLookbackHours     = 5;          // Causal lookback hours prior to entry
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input long   InpMagicNumber       = 20261127;   // Unique magic number (Registry S6)

string   g_usdBasketSyms[5] = {"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"};
int      g_usdSigns[5]      = {1, 1, -1, -1, -1};
string   g_tradePool[4]     = {"GBPUSD", "EURUSD", "AUDUSD", "USDCAD"};
int      g_poolUsdBase[4]   = {-1, -1, -1, 1};
int      g_atrHandles[5];

int OnInit()
{
   for(int i = 0; i < 5; i++)
   {
      if(!SymbolSelect(g_usdBasketSyms[i], true)) return INIT_FAILED;
      g_atrHandles[i] = iATR(g_usdBasketSyms[i], PERIOD_D1, InpAtrPeriodD1);
      if(g_atrHandles[i] == INVALID_HANDLE) return INIT_FAILED;
   }
   g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct);
   EventSetTimer(15);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   for(int i = 0; i < 5; i++)
      if(g_atrHandles[i] != INVALID_HANDLE) IndicatorRelease(g_atrHandles[i]);
}

bool HasAnyOwnPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   return false;
}

void CloseOwnPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         g_guard.ClosePositionChecked(trade, ticket, reason, InpDryRunLogOnly);
   }
}

bool HasOwnPositionNearSessionClose()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(g_guard.IsNearBrokerSessionCloseFor(PositionGetString(POSITION_SYMBOL)))
            return true;
      }
   }
   return false;
}

bool HasOwnPositionInRedNews()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(g_guard.IsInsideRedNewsWindowFor(PositionGetString(POSITION_SYMBOL)))
            return true;
      }
   }
   return false;
}

bool HasOwnPositionInPreFlattenWindow()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(g_guard.IsInRedNewsPreFlattenWindowFor(PositionGetString(POSITION_SYMBOL)))
            return true;
      }
   }
   return false;
}

void CloseOwnPositionsInPreFlatten(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         string psym = PositionGetString(POSITION_SYMBOL);
         if(!g_guard.IsInRedNewsPreFlattenWindowFor(psym)) continue;
         g_guard.ClosePositionChecked(trade, ticket, reason, InpDryRunLogOnly);
      }
   }
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
   g_guard.OnNewTickHousekeeping();
   datetime nowUtc = g_guard.NowUTC();
   MqlDateTime utc; TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;

   datetime utcDay = nowUtc - (nowUtc % 86400);
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC) || g_guard.IsNearBrokerSessionClose() || HasOwnPositionNearSessionClose())
   {
      if(HasAnyOwnPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }
   if(g_guard.IsInsideRedNewsWindow() || HasOwnPositionInRedNews())
   {
      if(HasOwnPositionInPreFlattenWindow()) CloseOwnPositionsInPreFlatten("NEWS_PRE_FLATTEN");
      return;
   }
   if(g_guard.IsDailyLossBreached())
   {
      if(HasAnyOwnPosition()) CloseOwnPositions("DAILY_LOSS_OR_KILLSWITCH");
      return;
   }

   if(g_guard.AlreadyTradedToday(utcDay) || HasAnyOwnPosition()) return;
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

   if(MathAbs(usdFactor) < InpMinUsdBasketZ) return;
   int usdDir = (usdFactor > 0.0) ? 1 : -1;

   int mapIdx[4] = {3, 2, 4, 1};
   int bestPool = -1; double bestScore = -1e9; int bestSide = 0;
   for(int p = 0; p < 4; p++)
   {
      int side = usdDir * g_poolUsdBase[p];
      double score = side * zVals[mapIdx[p]];
      if(score > bestScore) { bestScore = score; bestPool = p; bestSide = side; }
   }
   if(bestPool < 0 || bestScore <= 0.0) return;

   string sym = g_tradePool[bestPool];
   if(g_guard.IsInsideRedNewsWindowFor(sym) || !g_guard.IsSpreadAndSessionSafeFor(sym)) return;
   double atrD1 = atrVals[mapIdx[bestPool]];
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0) return;

   double slDist = InpSlAtrMult * atrD1;
   if(bestSide == 1)
   {
      double sl = CNaqexPropGuard::NormalizePriceToTick(sym, ask - slDist);
      double lots = g_guard.ComputeSafeLotsFor(sym, InpRiskPercent, ask - sl, true);
      if(lots > 0.0 && g_guard.ExecuteCheckedFor(trade, sym, true, lots, ask, sl, "Naqex_WB_USDBSK_BUY", InpDryRunLogOnly))
         g_guard.MarkTradedToday(utcDay);
   }
   else
   {
      double sl = CNaqexPropGuard::NormalizePriceToTick(sym, bid + slDist);
      double lots = g_guard.ComputeSafeLotsFor(sym, InpRiskPercent, sl - bid, false);
      if(lots > 0.0 && g_guard.ExecuteCheckedFor(trade, sym, false, lots, bid, sl, "Naqex_WB_USDBSK_SELL", InpDryRunLogOnly))
         g_guard.MarkTradedToday(utcDay);
   }
}

void OnTimer()
{
   datetime nowUtc = g_guard.NowUTC();
   MqlDateTime utc; TimeToStruct(nowUtc, utc);
   if(utc.day_of_week == 0 || utc.day_of_week == 6) return;
   if(!HasAnyOwnPosition()) return;
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC) || g_guard.IsNearBrokerSessionClose() || HasOwnPositionNearSessionClose())
      CloseOwnPositions("HARD_FLAT_TIMER_SWAP0");
   else if(HasOwnPositionInPreFlattenWindow())
      CloseOwnPositionsInPreFlatten("NEWS_PRE_FLATTEN_TIMER");
   else if(g_guard.IsDailyLossBreached())
      CloseOwnPositions("DAILY_LOSS_TIMER");
}
