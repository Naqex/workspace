//+------------------------------------------------------------------+
//| Naqex_PropGuard.mqh                                              |
//| Shared Production Safety & Prop-Firm Compliance Guard (MQL5)     |
//|                                                                  |
//| Solves critical MT5 Backtest-to-Live & Prop Payout Review traps: |
//|   1. Auto-detected ORDER_FILLING_* (FOK/IOC/RETURN) in OnInit()  |
//|   2. Conservative lot sizing using SYMBOL_TRADE_TICK_VALUE_LOSS  |
//|   3. Per-symbol concurrent risk cap (guards FTMO 1% idea bundle) |
//|   4. Strategy-Tester-safe UTC clock (TimeGMT() tester shift fix) |
//|   5. SymbolInfoSessionTrade() holiday early-close auto-flatten   |
//|   6. Rollover blackout & spread-spike guard                      |
//|   7. CSV-driven causal +/-5m red-news entry block & pre-flatten  |
//|   8. GlobalVariable VPS-restart-safe daily equity & trade state  |
//|   9. Explicit TRADE_RETCODE_DONE execution check & DryRun gate   |
//+------------------------------------------------------------------+
#ifndef NAQEX_PROPGUARD_MQH
#define NAQEX_PROPGUARD_MQH

#include <Trade/Trade.mqh>

// Default safety inputs (can be overridden by host EA before #include if needed)
#ifndef NAQEX_CUSTOM_GUARD_INPUTS
input bool   InpGuardDryRunLogOnly     = true;    // SAFETY: true = log only, NO live OrderSend
input double InpGuardMaxDailyLossPct   = 2.50;    // Internal daily equity stop (< 5% prop limit)
input double InpGuardMaxSymbolRiskPct  = 1.00;    // Max concurrent open SL risk % per symbol (FTMO 1% idea guard)
input double InpGuardMaxSpreadPoints   = 35.0;    // Reject entry if spread exceeds this (points; 0 = disabled)
input int    InpGuardRolloverStartUTC  = 21;      // Rollover blackout start hour (UTC)
input int    InpGuardRolloverEndUTC    = 0;       // Rollover blackout end hour (UTC, exclusive; 0 = midnight)
input int    InpGuardEarlyCloseMin     = 10;      // Flatten N min before broker session close (US holiday half-day guard)
input int    InpGuardTesterUtcOffsetH  = 2;       // Server UTC offset used ONLY inside MT5 Strategy Tester
input bool   InpGuardEnableRedNews     = true;    // Enable +/-PadSec red-news guard from MQL5/Files CSV
input string InpGuardRedNewsCsvFile    = "naqex_red_news_utc.csv";
input int    InpGuardNewsPadSec        = 300;     // 300s = +/-5m (covers FTMO +/-2m and The5ers +/-2m)
input long   InpGuardMagicRangeMin     = 20261120;
input long   InpGuardMagicRangeMax     = 20261199;
#endif

struct NaqexRedNewsEvent
{
   datetime utc_ts;
   string   ccy;
};

class CNaqexPropGuard
{
private:
   string            m_symbol;
   long              m_magic;
   NaqexRedNewsEvent m_events[];
   int               m_eventCount;
   double            m_dayStartEquity;
   int               m_dayKey;
   datetime          m_lastTradedDay;

   string StateKey(const string suffix) const
   {
      return StringFormat("NQXG_%I64d_%s_%s", m_magic, m_symbol, suffix);
   }

   int BuildUtcDayKey(const datetime utcNow) const
   {
      MqlDateTime dt;
      TimeToStruct(utcNow, dt);
      return dt.year * 1000 + dt.day_of_year;
   }

   bool CurrencyMatchesSymbol(const string evCcy) const
   {
      if(evCcy == "ALL" || evCcy == "") return true;
      if(StringFind(m_symbol, evCcy) >= 0) return true;
      // US equity indices and gold react directly to USD macro events
      if(evCcy == "USD" && (StringFind(m_symbol, "US100") >= 0 ||
                            StringFind(m_symbol, "US500") >= 0 ||
                            StringFind(m_symbol, "XAU")   >= 0))
         return true;
      return false;
   }

public:
   CNaqexPropGuard() : m_symbol(""), m_magic(0), m_eventCount(0), m_dayStartEquity(0.0), m_dayKey(-1), m_lastTradedDay(0) {}

   // 1. Auto-configure broker-supported filling mode (prevents retcode 10030)
   static bool ConfigureFillingMode(CTrade &tr, const string sym)
   {
      long fillFlags = SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
      if((fillFlags & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      {
         tr.SetTypeFilling(ORDER_FILLING_FOK);
         return true;
      }
      if((fillFlags & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      {
         tr.SetTypeFilling(ORDER_FILLING_IOC);
         return true;
      }
      tr.SetTypeFilling(ORDER_FILLING_RETURN);
      return true;
   }

   // 2. Initialize guard, configure filling, load CSV news calendar & restore VPS-restart state
   bool Init(CTrade &tr, const string sym, const long magic)
   {
      m_symbol = sym;
      m_magic  = magic;
      tr.SetExpertMagicNumber(magic);
      ConfigureFillingMode(tr, sym);
      LoadPersistedState();
      if(InpGuardEnableRedNews)
         LoadRedNewsCsv(InpGuardRedNewsCsvFile);
      return true;
   }

   // 3. Strategy-Tester-safe UTC timestamp (TimeGMT() equals TimeCurrent() inside MT5 Tester!)
   datetime NowUTC() const
   {
      if(MQLInfoInteger(MQL_TESTER))
         return (TimeCurrent() - (datetime)(InpGuardTesterUtcOffsetH * 3600));
      return TimeGMT();
   }

   // 4. VPS-restart-safe GlobalVariable persistence for daily equity & last traded day
   void LoadPersistedState()
   {
      datetime nowUtc = NowUTC();
      int todayKey = BuildUtcDayKey(nowUtc);
      string kDay  = StateKey("DAYKEY");
      string kEq   = StateKey("DAYEQ");
      string kTrd  = StateKey("LASTTRD");

      if(GlobalVariableCheck(kDay) && (int)GlobalVariableGet(kDay) == todayKey && GlobalVariableCheck(kEq))
      {
         m_dayKey = todayKey;
         m_dayStartEquity = GlobalVariableGet(kEq);
      }
      else
      {
         m_dayKey = todayKey;
         m_dayStartEquity = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
         GlobalVariableSet(kDay, (double)m_dayKey);
         GlobalVariableSet(kEq, m_dayStartEquity);
      }

      if(GlobalVariableCheck(kTrd))
         m_lastTradedDay = (datetime)GlobalVariableGet(kTrd);
      else
         m_lastTradedDay = 0;
   }

   void OnNewTickHousekeeping()
   {
      datetime nowUtc = NowUTC();
      int todayKey = BuildUtcDayKey(nowUtc);
      if(todayKey != m_dayKey)
      {
         m_dayKey = todayKey;
         m_dayStartEquity = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
         GlobalVariableSet(StateKey("DAYKEY"), (double)m_dayKey);
         GlobalVariableSet(StateKey("DAYEQ"), m_dayStartEquity);
      }
   }

   bool AlreadyTradedToday(const datetime todayBarOpen) const
   {
      return (m_lastTradedDay == todayBarOpen);
   }

   void MarkTradedToday(const datetime todayBarOpen)
   {
      m_lastTradedDay = todayBarOpen;
      GlobalVariableSet(StateKey("LASTTRD"), (double)todayBarOpen);
   }

   // 5. Internal daily equity circuit breaker
   bool IsDailyLossBreached() const
   {
      if(m_dayStartEquity <= 0.0) return false;
      double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct = ((m_dayStartEquity - curEq) / m_dayStartEquity) * 100.0;
      return (ddPct >= InpGuardMaxDailyLossPct);
   }

   // 6. Rollover blackout & spread spike filter
   bool IsSpreadAndSessionSafe() const
   {
      MqlDateTime utc;
      TimeToStruct(NowUTC(), utc);
      if(utc.day_of_week == 0 || utc.day_of_week == 6) return false;
      if(InpGuardRolloverStartUTC > InpGuardRolloverEndUTC)
      {
         if(utc.hour >= InpGuardRolloverStartUTC || utc.hour < InpGuardRolloverEndUTC)
            return false;
      }
      if(InpGuardMaxSpreadPoints > 0.0)
      {
         double spreadPts = (double)SymbolInfoInteger(m_symbol, SYMBOL_SPREAD);
         if(spreadPts > InpGuardMaxSpreadPoints)
            return false;
      }
      return true;
   }

   // 7. Broker session early-close detector (prevents holding through US holiday half-days!)
   bool IsNearBrokerSessionClose() const
   {
      if(InpGuardEarlyCloseMin <= 0) return false;
      datetime srvNow = TimeCurrent();
      MqlDateTime srv;
      TimeToStruct(srvNow, srv);
      ENUM_DAY_OF_WEEK dow = (ENUM_DAY_OF_WEEK)srv.day_of_week;

      datetime dayStart = srvNow - (srv.hour * 3600 + srv.min * 60 + srv.sec);
      int secOfDay = srv.hour * 3600 + srv.min * 60 + srv.sec;

      datetime sFrom = 0, sTo = 0;
      int lastCloseSec = -1;
      for(uint idx = 0; idx < 8; idx++)
      {
         if(!SymbolInfoSessionTrade(m_symbol, dow, idx, sFrom, sTo))
            break;
         int toSec = (int)sTo;
         if(toSec > lastCloseSec)
            lastCloseSec = toSec;
      }
      if(lastCloseSec <= 0) return false;
      int remainSec = lastCloseSec - secOfDay;
      return (remainSec >= 0 && remainSec <= InpGuardEarlyCloseMin * 60);
   }

   // 8. CSV-driven +/-PadSec red-news guard (format: utc_ts,ccy,event)
   int LoadRedNewsCsv(const string fileName)
   {
      m_eventCount = 0;
      ArrayResize(m_events, 0);
      int fh = FileOpen(fileName, FILE_READ | FILE_CSV | FILE_ANSI, ',');
      if(fh == INVALID_HANDLE)
         return 0;

      while(!FileIsEnding(fh))
      {
         string colTs  = FileReadString(fh);
         string colCcy = FileReadString(fh);
         string colEv  = FileReadString(fh);
         if(colTs == "" || colTs == "utc_ts") continue;
         long ts = StringToInteger(colTs);
         if(ts <= 0) continue;
         ArrayResize(m_events, m_eventCount + 1, 64);
         m_events[m_eventCount].utc_ts = (datetime)ts;
         m_events[m_eventCount].ccy    = colCcy;
         m_eventCount++;
      }
      FileClose(fh);
      return m_eventCount;
   }

   bool IsInsideRedNewsWindow() const
   {
      if(!InpGuardEnableRedNews || m_eventCount == 0) return false;
      datetime nowUtc = NowUTC();
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbol(m_events[i].ccy)) continue;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= InpGuardNewsPadSec)
            return true;
      }
      return false;
   }

   // 9. Per-symbol open SL risk % across ALL Naqex EAs on same symbol (guards FTMO 1% trade-idea bundle)
   double GetOpenSymbolRiskPct() const
   {
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal <= 0.0) return 0.0;
      double tickSize = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickVal  = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickVal <= 0.0) tickVal = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_VALUE);
      if(tickSize <= 0.0 || tickVal <= 0.0) return 0.0;

      double totalRiskMoney = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != m_symbol) continue;
         long pmagic = PositionGetInteger(POSITION_MAGIC);
         if(pmagic < InpGuardMagicRangeMin || pmagic > InpGuardMagicRangeMax) continue;

         double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
         double slPx   = PositionGetDouble(POSITION_SL);
         double vol    = PositionGetDouble(POSITION_VOLUME);
         if(slPx <= 0.0 || vol <= 0.0) continue;
         double slDist = MathAbs(openPx - slPx);
         totalRiskMoney += (slDist / tickSize) * tickVal * vol;
      }
      return (totalRiskMoney / bal) * 100.0;
   }

   // 10. Conservative lot sizing with SYMBOL_TRADE_TICK_VALUE_LOSS + per-symbol concurrent risk cap
   double ComputeSafeLots(const double requestedRiskPct, const double slDistancePrice) const
   {
      if(slDistancePrice <= 0.0 || requestedRiskPct <= 0.0) return 0.0;
      double effRiskPct = requestedRiskPct;
      if(InpGuardMaxSymbolRiskPct > 0.0)
      {
         double usedPct = GetOpenSymbolRiskPct();
         double remPct  = MathMax(0.0, InpGuardMaxSymbolRiskPct - usedPct);
         effRiskPct = MathMin(effRiskPct, remPct);
      }
      if(effRiskPct <= 0.0) return 0.0;

      double bal       = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskMoney = bal * (effRiskPct / 100.0);
      double tickSize  = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickValue <= 0.0) tickValue = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_VALUE);

      double volMin  = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
      double volMax  = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MAX);
      double volStep = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP);
      if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;

      double lossPerLot = (slDistancePrice / tickSize) * tickValue;
      if(lossPerLot <= 0.0) return 0.0;

      double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
      if(rawLots < volMin) return 0.0;
      return MathMin(rawLots, volMax);
   }

   // 11. Checked execution wrapper (DryRun default ON + TRADE_RETCODE_DONE verification)
   bool ExecuteChecked(CTrade &tr, const bool isBuy, const double lots, const double entryPrice, const double slPrice, const string comment) const
   {
      if(lots <= 0.0 || slPrice <= 0.0) return false;
      if(InpGuardDryRunLogOnly)
      {
         PrintFormat("[DRYRUN-GUARD] %s %s lots=%.2f price=%.5f sl=%.5f tag=%s",
                     isBuy ? "BUY" : "SELL", m_symbol, lots, entryPrice, slPrice, comment);
         return true;
      }
      bool ok = isBuy ? tr.Buy(lots, m_symbol, entryPrice, slPrice, 0.0, comment)
                      : tr.Sell(lots, m_symbol, entryPrice, slPrice, 0.0, comment);
      uint ret = tr.ResultRetcode();
      if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
      {
         PrintFormat("[PROPGUARD-ERR] %s %s failed retcode=%u desc=%s",
                     isBuy ? "BUY" : "SELL", m_symbol, ret, tr.ResultRetcodeDescription());
         return false;
      }
      return true;
   }
};

#endif // NAQEX_PROPGUARD_MQH
