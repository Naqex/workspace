//+------------------------------------------------------------------+
//| Naqex White-Box Prop EA: EXP_DAILY_OPEN_080 (USDJPY)
//| Provenance: protocol=9bbf69c83241 | spec_sha=68dd7d42aa04e617 | tier=TIER_1_FTMO_READY
//| Rules: Zero-Grid, Zero-Martingale, Hard-SL, Intraday swap=0, DryRun default ON
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO OrderSend
input double InpRiskPercent       = 0.50;       // Fixed fractional risk % per trade
input double InpMaxDailyLossPct   = 2.50;       // Internal circuit breaker (< 5% FTMO daily limit)
input double InpTrigAtrMult       = 0.80;       // Expansion trigger from D1 open (x ATR14_D1)
input double InpSlAtrMult         = 0.75;       // Hard SL distance (x ATR14_D1)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 Wilder ATR period
input int    InpEntryStartHourUTC = 7;          // Entry window start (UTC)
input int    InpEntryEndHourUTC   = 17;         // Entry window end (UTC)
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = 20261123;   // Unique magic number

int      g_atrHandle = INVALID_HANDLE;
datetime g_lastTradedDay = 0;
double   g_dayStartEquity = 0.0;
int      g_lastEquityDay = -1;

int OnInit()
{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
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
   MqlDateTime utc;
   TimeToStruct(TimeGMT(), utc);
   if(utc.day_of_year != g_lastEquityDay)
   {
      g_lastEquityDay = utc.day_of_year;
      g_dayStartEquity = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   }

   // Hard intraday flat (swap = 0)
   if(utc.hour > InpFlatHourUTC || (utc.hour == InpFlatHourUTC && utc.min >= InpFlatMinUTC))
   {
      if(HasOpenPosition()) CloseOwnPositions("HARD_FLAT_SWAP0");
      return;
   }

   // Internal daily loss circuit breaker
   double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0.0 && ((g_dayStartEquity - curEq) / g_dayStartEquity) * 100.0 >= InpMaxDailyLossPct)
   {
      if(HasOpenPosition()) CloseOwnPositions("DAILY_LOSS_CIRCUIT_BREAKER");
      return;
   }

   // One trade max per UTC day, strictly within liquidity window
   datetime todayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(todayStart == g_lastTradedDay || HasOpenPosition()) return;
   if(utc.hour < InpEntryStartHourUTC || utc.hour >= InpEntryEndHourUTC) return;

   // Causal prior completed D1 ATR14 (shift = 1)
   double atrBuf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0) return;
   double atrD1 = atrBuf[0];
   double dayOpen = iOpen(_Symbol, PERIOD_D1, 0);
   if(dayOpen <= 0.0) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double top = dayOpen + InpTrigAtrMult * atrD1;
   double bot = dayOpen - InpTrigAtrMult * atrD1;
   double slDist = InpSlAtrMult * atrD1;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(ask >= top)
   {
      double sl = NormalizeDouble(ask - slDist, digits);
      double lots = ComputeLots(ask - sl);
      if(lots > 0.0)
      {
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] BUY %s lots=%.2f ask=%.5f sl=%.5f atr=%.5f", _Symbol, lots, ask, sl, atrD1);
         else
            trade.Buy(lots, _Symbol, ask, sl, 0.0, "Naqex_WB_EXP_BUY");
      }
   }
   else if(bid <= bot)
   {
      double sl = NormalizeDouble(bid + slDist, digits);
      double lots = ComputeLots(sl - bid);
      if(lots > 0.0)
      {
         g_lastTradedDay = todayStart;
         if(InpDryRunLogOnly)
            PrintFormat("[DRYRUN] SELL %s lots=%.2f bid=%.5f sl=%.5f atr=%.5f", _Symbol, lots, bid, sl, atrD1);
         else
            trade.Sell(lots, _Symbol, bid, sl, 0.0, "Naqex_WB_EXP_SELL");
      }
   }
}
