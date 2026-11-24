//+------------------------------------------------------------------+
//| Naqex_PropGuard.mqh (v3.0 — Full-Stack Fail-Closed Prop Guard)   |
//| Shared Production Safety, Atomic SymCap, Margin & TCA Logger     |
//|                                                                  |
//| Capabilities:                                                    |
//|   1. Auto-detected ORDER_FILLING_* (FOK/IOC/RETURN) in OnInit()  |
//|   2. Conservative lot sizing: TICK_VALUE_LOSS + 5% cost cushion  |
//|      + OrderCalcMargin free-margin cap (guards 5K & 1:30 Swing)  |
//|   3. Atomic per-symbol risk reservation (GlobalVariable CAS lock |
//|      prevents multi-EA race) + fail-closed on missing SL/tickVal |
//|   4. Account-login-scoped Orchestrator sync + 120s liveness gate |
//|   5. Strategy-Tester-safe UTC clock (TimeGMT() tester shift fix) |
//|   6. SymbolInfoSessionTrade() per-symbol holiday early-close     |
//|   7. Rollover blackout & spread-spike guard                      |
//|   8. Fail-closed CSV +/-5m red-news block & -5m..-2m15s flatten  |
//|   9. Account-scoped GV daily anchor + trade state persistence    |
//|  10. Tick-grid SL normalization, checked Buy/Sell & Close + TCA  |
//+------------------------------------------------------------------+
#ifndef NAQEX_PROPGUARD_MQH
#define NAQEX_PROPGUARD_MQH

#include <Trade/Trade.mqh>

#ifndef NAQEX_CUSTOM_GUARD_INPUTS
input bool   InpGuardDryRunLogOnly     = true;    // SAFETY: true = log only, NO live OrderSend
input double InpGuardMaxDailyLossPct   = 2.50;    // Internal daily equity stop (< 5% prop limit)
input double InpGuardMaxSymbolRiskPct  = 1.00;    // Max concurrent open SL risk % per symbol (FTMO 1% idea guard)
input bool   InpGuardUseOrchestrator   = true;    // Sync risk mult & Kill-Switch from Naqex_AccountOrchestrator
input double InpGuardMaxSpreadPoints   = 35.0;    // Reject entry if spread exceeds this (points; 0 = disabled)
input int    InpGuardRolloverStartUTC  = 21;      // Rollover blackout start hour (UTC)
input int    InpGuardRolloverEndUTC    = 0;       // Rollover blackout end hour (UTC, exclusive; 0 = midnight)
input int    InpGuardEarlyCloseMin     = 10;      // Flatten N min before broker session close (US holiday half-day guard)
input int    InpGuardTesterUtcOffsetH  = 2;       // Server UTC offset used ONLY inside MT5 Strategy Tester
input bool   InpGuardEnableRedNews     = true;    // Enable +/-PadSec red-news guard from MQL5/Files CSV
input string InpGuardRedNewsCsvFile    = "naqex_red_news_utc.csv";
input int    InpGuardNewsPadSec        = 300;     // 300s = +/-5m (covers FTMO +/-2m and The5ers +/-2m)
input int    InpGuardNewsHardBanSec    = 135;     // 135s = +/-2m15s hard no-execution zone (protects +/-2m FTMO/The5ers ban)
input string InpGuardTcaAuditCsvFile   = "naqex_exec_audit.csv";
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
   double            m_eaMaxDailyLossPct;
   NaqexRedNewsEvent m_events[];
   int               m_eventCount;
   datetime          m_maxEventTs;
   double            m_dayStartEquity;
   int               m_dayKey;
   datetime          m_lastTradedDay;

   string StateKey(const string suffix) const
   {
      return StringFormat("NQXG_%I64d_%I64d_%s_%s", CurrentAccountLogin(), m_magic, m_symbol, suffix);
   }

   int BuildUtcDayKey(const datetime utcNow) const
   {
      MqlDateTime dt;
      TimeToStruct(utcNow, dt);
      return dt.year * 1000 + dt.day_of_year;
   }

   bool CurrencyMatchesSymbolFor(const string sym, const string evCcy) const
   {
      string uSym = sym;
      string uCcy = evCcy;
      StringToUpper(uSym);
      StringToUpper(uCcy);
      if(uCcy == "ALL" || uCcy == "") return true;
      if(StringFind(uSym, uCcy) >= 0) return true;
      if(uCcy == "USD" && (StringFind(uSym, "US100")  >= 0 ||
                           StringFind(uSym, "NAS100") >= 0 ||
                           StringFind(uSym, "NDX")    >= 0 ||
                           StringFind(uSym, "USTEC")  >= 0 ||
                           StringFind(uSym, "US500")  >= 0 ||
                           StringFind(uSym, "SPX")    >= 0 ||
                           StringFind(uSym, "US30")   >= 0 ||
                           StringFind(uSym, "XAU")    >= 0 ||
                           StringFind(uSym, "BTC")    >= 0))
         return true;
      if(uCcy == "EUR" && (StringFind(uSym, "GER40") >= 0 ||
                           StringFind(uSym, "DE40")  >= 0 ||
                           StringFind(uSym, "DAX")   >= 0))
         return true;
      if(uCcy == "GBP" && (StringFind(uSym, "UK100") >= 0 ||
                           StringFind(uSym, "FTSE")  >= 0))
         return true;
      return false;
   }

   bool CurrencyMatchesSymbol(const string evCcy) const
   {
      return CurrencyMatchesSymbolFor(m_symbol, evCcy);
   }

   static string SymResLockKey(const string sym) { return StringFormat("NQXG_RLOCK_%I64d_%s", CurrentAccountLogin(), sym); }
   static string SymResPctKey(const string sym)  { return StringFormat("NQXG_RPCT_%I64d_%s",  CurrentAccountLogin(), sym); }
   static string SymResTsKey(const string sym)   { return StringFormat("NQXG_RTS_%I64d_%s",   CurrentAccountLogin(), sym); }

   bool AcquireSymbolLock(const string sym) const
   {
      string lk = SymResLockKey(sym);
      string tk = SymResTsKey(sym);
      if(!GlobalVariableCheck(lk))
         GlobalVariableSet(lk, 0.0);
      long nowTs = (long)NowUTC();
      for(int attempt = 0; attempt < 25; attempt++)
      {
         if(GlobalVariableSetOnCondition(lk, 1.0, 0.0))
            return true;
         // Break stale lock older than 15s (e.g., crash mid-order)
         if(GlobalVariableCheck(tk))
         {
            long prevTs = (long)GlobalVariableGet(tk);
            if(nowTs - prevTs > 15)
            {
               GlobalVariableSet(lk, 0.0);
               GlobalVariableSet(SymResPctKey(sym), 0.0);
               if(GlobalVariableSetOnCondition(lk, 1.0, 0.0))
                  return true;
            }
         }
         if(!MQLInfoInteger(MQL_TESTER))
            Sleep(5);
      }
      return false;
   }

   void ReleaseSymbolLock(const string sym) const
   {
      GlobalVariableSet(SymResLockKey(sym), 0.0);
   }

   double GetReservedSymbolRiskPctFor(const string sym) const
   {
      string pk = SymResPctKey(sym);
      string tk = SymResTsKey(sym);
      if(!GlobalVariableCheck(pk) || !GlobalVariableCheck(tk))
         return 0.0;
      long age = (long)NowUTC() - (long)GlobalVariableGet(tk);
      if(age < 0 || age > 15)
         return 0.0;
      return MathMax(0.0, GlobalVariableGet(pk));
   }

public:
   CNaqexPropGuard() : m_symbol(""), m_magic(0), m_eaMaxDailyLossPct(0.0), m_eventCount(0), m_maxEventTs(0), m_dayStartEquity(0.0), m_dayKey(-1), m_lastTradedDay(0) {}

   // Account-login-scoped GlobalVariable keys (prevents cross-account pollution on shared terminal)
   static long CurrentAccountLogin()
   {
      return AccountInfoInteger(ACCOUNT_LOGIN);
   }
   static string GlobalKillKey()    { return StringFormat("NQXG_GLOBAL_KILLSWITCH_%I64d", CurrentAccountLogin()); }
   static string GlobalMultKey()    { return StringFormat("NQXG_GLOBAL_RISK_MULT_%I64d",  CurrentAccountLogin()); }
   static string OrchTsKey()        { return StringFormat("NQXG_ORCH_TS_%I64d",           CurrentAccountLogin()); }
   static string AcctDayKeyName()   { return StringFormat("NQXG_ACCT_DAYKEY_%I64d",       CurrentAccountLogin()); }
   static string AcctDayEqKeyName() { return StringFormat("NQXG_ACCT_DAYEQ_%I64d",        CurrentAccountLogin()); }
   static string AcctDayBalKeyName(){ return StringFormat("NQXG_ACCT_DAYBAL_%I64d",       CurrentAccountLogin()); }
   static string AcctAutoKillKey()  { return StringFormat("NQXG_ACCT_AUTOKILL_%I64d",     CurrentAccountLogin()); }

   // Tick-grid price normalizer (prevents invalid-stops on indices with tick_size > point)
   static double NormalizePriceToTick(const string sym, const double px)
   {
      double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      if(ts > 0.0)
         return NormalizeDouble(MathRound(px / ts) * ts, digits);
      return NormalizeDouble(px, digits);
   }

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
   bool Init(CTrade &tr, const string sym, const long magic, const double eaMaxDailyLossPct = 0.0)
   {
      m_symbol            = sym;
      m_magic             = magic;
      m_eaMaxDailyLossPct = eaMaxDailyLossPct;
      tr.SetExpertMagicNumber(magic);
      ConfigureFillingMode(tr, sym);
      LoadPersistedState();
      if(InpGuardEnableRedNews)
      {
         int loaded = LoadRedNewsCsv(InpGuardRedNewsCsvFile);
         if(loaded <= 0)
            PrintFormat("[PROPGUARD-WARN] Red-news CSV '%s' missing or empty (loaded=%d) — entries FAIL-CLOSED blocked!", InpGuardRedNewsCsvFile, loaded);
      }
      return true;
   }

   // 3. Strategy-Tester-safe UTC timestamp (TimeGMT() equals TimeCurrent() inside MT5 Tester!)
   //    Auto-applies NY+7 US DST (+1h during 2nd Sun Mar -> 1st Sun Nov) for standard NY-close brokers (FTMO/The5ers)
   static int NthSundayOfMonth(const int year, const int month, const int nth)
   {
      MqlDateTime d;
      ZeroMemory(d);
      d.year = year; d.mon = month; d.day = 1;
      TimeToStruct(StructToTime(d), d);
      return 1 + ((7 - d.day_of_week) % 7) + (nth - 1) * 7;
   }

   static bool IsUsDstUtc(const datetime utcTs)
   {
      MqlDateTime utc;
      TimeToStruct(utcTs, utc);
      if(utc.mon < 3 || utc.mon > 11) return false;
      if(utc.mon > 3 && utc.mon < 11) return true;
      if(utc.mon == 3)
      {
         int s2 = NthSundayOfMonth(utc.year, 3, 2);
         return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7));
      }
      int s1 = NthSundayOfMonth(utc.year, 11, 1);
      return (utc.day < s1 || (utc.day == s1 && utc.hour < 6));
   }

   static bool IsUsEquityHalfDayNY(const MqlDateTime &ny)
   {
      // NYSE 13:00 ET early-close holiday half-days (prevents holding US100/US500 across holiday rollover!)
      if(ny.mon == 7 && ny.day == 3 && ny.day_of_week >= 1 && ny.day_of_week <= 4)
         return true; // Independence Day Eve
      if(ny.mon == 11 && ny.day_of_week == 5 && ny.day >= 23 && ny.day <= 29)
         return true; // Black Friday (Friday after 4th Thursday of November)
      if(ny.mon == 12 && ny.day == 24 && ny.day_of_week >= 1 && ny.day_of_week <= 5)
         return true; // Christmas Eve
      return false;
   }

   datetime NowUTC() const
   {
      if(MQLInfoInteger(MQL_TESTER))
      {
         datetime srvNow = TimeCurrent();
         int offH = InpGuardTesterUtcOffsetH;
         if(offH == 2)
         {
            // NY-close broker convention (FTMO/The5ers): UTC+3 during US EDT, UTC+2 during US EST
            datetime candEdt = srvNow - (datetime)(3 * 3600);
            if(IsUsDstUtc(candEdt))
               return candEdt;
         }
         return (srvNow - (datetime)(offH * 3600));
      }
      return TimeGMT();
   }

   // 4. Account-scoped Orchestrator GlobalVariable sync (Kill-Switch, liveness & dynamic multiplier)
   bool IsOrchestratorAlive(const int maxAgeSec = 120) const
   {
      if(!InpGuardUseOrchestrator || MQLInfoInteger(MQL_TESTER)) return true;
      string tk = OrchTsKey();
      if(!GlobalVariableCheck(tk)) return false;
      long diff = MathAbs((long)NowUTC() - (long)GlobalVariableGet(tk));
      return (diff <= maxAgeSec);
   }

   bool IsGlobalKillSwitchActive() const
   {
      if(!InpGuardUseOrchestrator) return false;
      string kk = GlobalKillKey();
      if(GlobalVariableCheck(kk))
         return (GlobalVariableGet(kk) >= 1.0);
      return false;
   }

   double GetGlobalRiskMultiplier() const
   {
      if(!InpGuardUseOrchestrator) return 1.0;
      string mk = GlobalMultKey();
      if(GlobalVariableCheck(mk))
      {
         double m = GlobalVariableGet(mk);
         if(m >= 0.20 && m <= 3.50) return m;
      }
      return 1.0;
   }

   // 5. VPS-restart-safe account-scoped GlobalVariable persistence for daily equity & last traded day
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

   // 6. Internal daily equity circuit breaker (syncs Orchestrator account-scoped anchor when live)
   bool IsDailyLossBreached() const
   {
      if(IsGlobalKillSwitchActive()) return true;
      double anchorEq = m_dayStartEquity;
      if(InpGuardUseOrchestrator && !MQLInfoInteger(MQL_TESTER) && GlobalVariableCheck(AcctDayEqKeyName()))
      {
         double orchAnchor = GlobalVariableGet(AcctDayEqKeyName());
         if(orchAnchor > 0.0)
            anchorEq = orchAnchor;
      }
      if(anchorEq <= 0.0) return false;
      double effLimit = InpGuardMaxDailyLossPct;
      if(m_eaMaxDailyLossPct > 0.0 && (effLimit <= 0.0 || m_eaMaxDailyLossPct < effLimit))
         effLimit = m_eaMaxDailyLossPct;
      if(effLimit <= 0.0) return false;
      double curEq = AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct = ((anchorEq - curEq) / anchorEq) * 100.0;
      return (ddPct >= effLimit);
   }

   // 7. Rollover blackout & spread spike filter (supports wrap-around and same-day windows)
   bool IsSpreadAndSessionSafeFor(const string sym) const
   {
      MqlDateTime utc;
      TimeToStruct(NowUTC(), utc);
      if(utc.day_of_week == 0 || utc.day_of_week == 6) return false;
      if(InpGuardRolloverStartUTC > InpGuardRolloverEndUTC)
      {
         if(utc.hour >= InpGuardRolloverStartUTC || utc.hour < InpGuardRolloverEndUTC)
            return false;
      }
      else if(InpGuardRolloverStartUTC < InpGuardRolloverEndUTC)
      {
         if(utc.hour >= InpGuardRolloverStartUTC && utc.hour < InpGuardRolloverEndUTC)
            return false;
      }
      if(InpGuardMaxSpreadPoints > 0.0)
      {
         double spreadPts = (double)SymbolInfoInteger(sym, SYMBOL_SPREAD);
         if(spreadPts > InpGuardMaxSpreadPoints)
            return false;
      }
      return true;
   }

   bool IsSpreadAndSessionSafe() const
   {
      return IsSpreadAndSessionSafeFor(m_symbol);
   }

   // 8. Broker session early-close detector (per-symbol, prevents holding through holiday half-days!)
   bool IsNearBrokerSessionCloseFor(const string sym) const
   {
      if(InpGuardEarlyCloseMin <= 0) return false;
      datetime srvNow = TimeCurrent();
      MqlDateTime srv;
      TimeToStruct(srvNow, srv);
      ENUM_DAY_OF_WEEK dow = (ENUM_DAY_OF_WEEK)srv.day_of_week;
      int secOfDay = srv.hour * 3600 + srv.min * 60 + srv.sec;

      datetime sFrom = 0, sTo = 0;
      int lastCloseSec = -1;
      for(uint idx = 0; idx < 8; idx++)
      {
         if(!SymbolInfoSessionTrade(sym, dow, idx, sFrom, sTo))
            break;
         int toSec = (int)sTo;
         if(toSec > lastCloseSec)
            lastCloseSec = toSec;
      }
      if(lastCloseSec <= 0) return false;
      int remainSec = lastCloseSec - secOfDay;
      return (remainSec >= 0 && remainSec <= InpGuardEarlyCloseMin * 60);
   }

   bool IsNearBrokerSessionClose() const
   {
      return IsNearBrokerSessionCloseFor(m_symbol);
   }

   // 9. Fail-closed CSV-driven +/-PadSec red-news guard (format: utc_ts,ccy,event)
   int LoadRedNewsCsv(const string fileName)
   {
      m_eventCount = 0;
      m_maxEventTs = 0;
      ArrayResize(m_events, 0);
      int fh = FileOpen(fileName, FILE_READ | FILE_CSV | FILE_ANSI, ',');
      if(fh == INVALID_HANDLE)
         return 0;

      while(!FileIsEnding(fh))
      {
         string colTs  = FileReadString(fh);
         string colCcy = FileIsLineEnding(fh) ? "" : FileReadString(fh);
         string colEv  = FileIsLineEnding(fh) ? "" : FileReadString(fh);
         while(!FileIsLineEnding(fh) && !FileIsEnding(fh))
            FileReadString(fh);
         if(colTs == "" || colTs == "utc_ts") continue;
         long ts = StringToInteger(colTs);
         if(ts <= 0) continue;
         ArrayResize(m_events, m_eventCount + 1, 64);
         m_events[m_eventCount].utc_ts = (datetime)ts;
         m_events[m_eventCount].ccy    = colCcy;
         if((datetime)ts > m_maxEventTs)
            m_maxEventTs = (datetime)ts;
         m_eventCount++;
      }
      FileClose(fh);
      return m_eventCount;
   }

   bool IsRedNewsCalendarHealthy() const
   {
      if(!InpGuardEnableRedNews) return true;
      if(m_eventCount <= 0) return false;
      if(!MQLInfoInteger(MQL_TESTER) && m_maxEventTs > 0 && NowUTC() > (m_maxEventTs + 86400))
         return false;
      return true;
   }

   bool IsInsideRedNewsWindowFor(const string sym) const
   {
      if(!InpGuardEnableRedNews) return false;
      // FAIL-CLOSED: missing, empty, or expired calendar blocks new entries!
      if(!IsRedNewsCalendarHealthy()) return true;
      datetime nowUtc = NowUTC();
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbolFor(sym, m_events[i].ccy)) continue;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= InpGuardNewsPadSec)
            return true;
      }
      return false;
   }

   bool IsInsideRedNewsWindow() const
   {
      return IsInsideRedNewsWindowFor(m_symbol);
   }

   // Safe pre-flatten window strictly BEFORE hard +/-2m15s no-execution ban (-5m .. -2m15s).
   // Returns false inside ANY matching event's +/-InpGuardNewsHardBanSec zone or missing calendar.
   bool IsInRedNewsPreFlattenWindowFor(const string sym) const
   {
      if(!InpGuardEnableRedNews || !IsRedNewsCalendarHealthy()) return false;
      datetime nowUtc = NowUTC();
      bool inPreFlatten = false;
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbolFor(sym, m_events[i].ccy)) continue;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= InpGuardNewsHardBanSec)
            return false;
         if(diff > InpGuardNewsHardBanSec && diff <= InpGuardNewsPadSec)
            inPreFlatten = true;
      }
      return inPreFlatten;
   }

   bool IsInRedNewsPreFlattenWindow() const
   {
      return IsInRedNewsPreFlattenWindowFor(m_symbol);
   }

   // 10. Fail-closed per-symbol open + reserved SL risk % across ALL positions on same symbol
   double GetOpenSymbolRiskPctFor(const string sym) const
   {
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal <= 0.0) return 999.0;
      double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double tickVal  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickVal <= 0.0) tickVal = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      if(tickSize <= 0.0 || tickVal <= 0.0) return 999.0;

      double totalRiskMoney = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != sym) continue;

         double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
         double slPx   = PositionGetDouble(POSITION_SL);
         double vol    = PositionGetDouble(POSITION_VOLUME);
         if(vol <= 0.0) continue;
         // FAIL-CLOSED: any open position on this symbol without SL blocks additional risk!
         if(slPx <= 0.0) return 999.0;
         double slDist = MathAbs(openPx - slPx);
         totalRiskMoney += (slDist / tickSize) * tickVal * vol;
      }
      double openPct = (totalRiskMoney / bal) * 100.0;
      return openPct + GetReservedSymbolRiskPctFor(sym);
   }

   double GetOpenSymbolRiskPct() const
   {
      return GetOpenSymbolRiskPctFor(m_symbol);
   }

   bool ReserveSymbolRiskFor(const string sym, const double addRiskPct) const
   {
      if(InpGuardMaxSymbolRiskPct <= 0.0 || addRiskPct <= 0.0) return true;
      if(!AcquireSymbolLock(sym)) return false;
      double currentUsed = GetOpenSymbolRiskPctFor(sym);
      bool ok = (currentUsed + addRiskPct <= InpGuardMaxSymbolRiskPct + 1e-6);
      if(ok)
      {
         double prevRes = GetReservedSymbolRiskPctFor(sym);
         GlobalVariableSet(SymResPctKey(sym), prevRes + addRiskPct);
         GlobalVariableSet(SymResTsKey(sym), (double)NowUTC());
      }
      ReleaseSymbolLock(sym);
      return ok;
   }

   void ReleaseSymbolRiskFor(const string sym, const double relRiskPct) const
   {
      if(relRiskPct <= 0.0) return;
      if(!AcquireSymbolLock(sym)) return;
      double prevRes = GetReservedSymbolRiskPctFor(sym);
      double nextRes = MathMax(0.0, prevRes - relRiskPct);
      GlobalVariableSet(SymResPctKey(sym), nextRes);
      if(nextRes <= 1e-9)
         GlobalVariableSet(SymResTsKey(sym), 0.0);
      ReleaseSymbolLock(sym);
   }

   // 11. Conservative lot sizing: Orchestrator liveness + TICK_VALUE_LOSS + 5% cost cushion + OrderCalcMargin + SYMCAP
   double ComputeSafeLotsFor(const string sym, const double requestedRiskPct, const double slDistancePrice, const bool isBuy = true) const
   {
      if(slDistancePrice <= 0.0 || requestedRiskPct <= 0.0) return 0.0;
      if(IsGlobalKillSwitchActive()) return 0.0;
      if(!IsOrchestratorAlive(120)) return 0.0;

      double effRiskPct = requestedRiskPct * GetGlobalRiskMultiplier();
      if(InpGuardMaxSymbolRiskPct > 0.0)
      {
         double usedPct = GetOpenSymbolRiskPctFor(sym);
         double remPct  = MathMax(0.0, InpGuardMaxSymbolRiskPct - usedPct);
         effRiskPct = MathMin(effRiskPct, remPct);
      }
      if(effRiskPct <= 0.0) return 0.0;

      double bal       = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal <= 0.0) return 0.0;
      // Reserve 5% cushion for commission/spread/minor slip inside risk budget
      double riskMoney = bal * (effRiskPct / 100.0) * 0.95;
      double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickValue <= 0.0) tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);

      double volMin  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
      double volMax  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
      double volStep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
      if(tickSize <= 0.0 || tickValue <= 0.0 || volStep <= 0.0) return 0.0;

      double lossPerLot = (slDistancePrice / tickSize) * tickValue;
      if(lossPerLot <= 0.0) return 0.0;

      double rawLots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
      if(rawLots < volMin) return 0.0;
      double clampedLots = MathMin(rawLots, volMax);

      // Free-margin safety check via OrderCalcMargin (prevents margin-call rejects on 5K / 1:30 Swing!)
      ENUM_ORDER_TYPE ordType = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double refPx = isBuy ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      double reqMargin = 0.0;
      if(refPx > 0.0 && freeMargin > 0.0 && OrderCalcMargin(ordType, sym, clampedLots, refPx, reqMargin))
      {
         double maxAllowedMargin = freeMargin * 0.85;
         if(reqMargin > maxAllowedMargin && reqMargin > 0.0)
         {
            double scaledLots = MathFloor((clampedLots * (maxAllowedMargin / reqMargin)) / volStep) * volStep;
            if(scaledLots < volMin) return 0.0;
            clampedLots = MathMin(scaledLots, volMax);
         }
      }
      return clampedLots;
   }

   double ComputeSafeLots(const double requestedRiskPct, const double slDistancePrice, const bool isBuy = true) const
   {
      return ComputeSafeLotsFor(m_symbol, requestedRiskPct, slDistancePrice, isBuy);
   }

   // 12. Structured CSV execution audit logger (feeds Python quant_factory.tca_reconcile)
   void LogExecAuditFor(const string sym, const string side, const string evType, const double sigPx, const double fillPx,
                        const double slPx, const double lots, const double latencyMs, const uint retcode, const string note) const
   {
      if(MQLInfoInteger(MQL_TESTER)) return;
      bool needHeader = !FileIsExist(InpGuardTcaAuditCsvFile);
      int fh = FileOpen(InpGuardTcaAuditCsvFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
      if(fh == INVALID_HANDLE)
      {
         PrintFormat("[PROPGUARD-AUDIT-ERR] Failed to open '%s' err=%d ev=%s sym=%s", InpGuardTcaAuditCsvFile, GetLastError(), evType, sym);
         return;
      }
      FileSeek(fh, 0, SEEK_END);
      if(needHeader)
         FileWrite(fh, "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price", "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "comment");
      double spPts = (double)SymbolInfoInteger(sym, SYMBOL_SPREAD);
      FileWrite(fh, (long)NowUTC(), m_magic, sym, side, evType,
                DoubleToString(sigPx, 6), DoubleToString(fillPx, 6), DoubleToString(slPx, 6),
                DoubleToString(lots, 2), DoubleToString(spPts, 1), DoubleToString(latencyMs, 2),
                (long)retcode, note);
      FileClose(fh);
   }

   void LogExecAudit(const string side, const string evType, const double sigPx, const double fillPx,
                     const double slPx, const double lots, const double latencyMs, const uint retcode, const string note) const
   {
      LogExecAuditFor(m_symbol, side, evType, sigPx, fillPx, slPx, lots, latencyMs, retcode, note);
   }

   // 12b. Resolve actual broker-executed fill price (NEVER silently fabricates signal price as fill!)
   double ResolveExecutedFillPrice(CTrade &tr, const string sym, const double fallbackPx) const
   {
      double px = tr.ResultPrice();
      if(px > 0.0) return px;
      ulong deal = tr.ResultDeal();
      if(deal > 0 && HistoryDealSelect(deal))
      {
         double dpx = HistoryDealGetDouble(deal, DEAL_PRICE);
         if(dpx > 0.0) return dpx;
      }
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetInteger(POSITION_MAGIC) == m_magic && PositionGetString(POSITION_SYMBOL) == sym)
         {
            double opx = PositionGetDouble(POSITION_PRICE_OPEN);
            if(opx > 0.0) return opx;
         }
      }
      return fallbackPx;
   }

   // 13. Checked execution wrapper (DryRun default ON + Atomic SYMCAP reservation + Tick-grid SL + TCA audit)
   bool ExecuteCheckedFor(CTrade &tr, const string sym, const bool isBuy, const double lots, const double entryPrice, const double slPrice,
                          const string comment, const bool eaDryRun = true) const
   {
      if(lots <= 0.0 || slPrice <= 0.0) return false;
      double normSl = NormalizePriceToTick(sym, slPrice);
      double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
      long stopsLvl = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
      if(pt > 0.0 && stopsLvl > 0 && MathAbs(entryPrice - normSl) < (double)stopsLvl * pt)
      {
         PrintFormat("[PROPGUARD-ERR] %s SL too close to stops_level=%I64d", sym, stopsLvl);
         return false;
      }

      ConfigureFillingMode(tr, sym);
      string sideStr = isBuy ? "BUY" : "SELL";
      if(eaDryRun || InpGuardDryRunLogOnly)
      {
         PrintFormat("[DRYRUN-GUARD] %s %s lots=%.2f price=%.5f sl=%.5f mult=%.2f tag=%s",
                     sideStr, sym, lots, entryPrice, normSl, GetGlobalRiskMultiplier(), comment);
         LogExecAuditFor(sym, sideStr, "DRYRUN_SIGNAL", entryPrice, entryPrice, normSl, lots, 0.0, 0, comment);
         return true;
      }

      // Compute exact SL risk % and acquire atomic per-symbol reservation before sending order
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double tickVal  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tickVal <= 0.0) tickVal = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      double estRiskPct = (bal > 0.0 && tickSize > 0.0 && tickVal > 0.0)
                          ? (((MathAbs(entryPrice - normSl) / tickSize) * tickVal * lots) / bal) * 100.0
                          : 999.0;
      if(!ReserveSymbolRiskFor(sym, estRiskPct))
      {
         PrintFormat("[PROPGUARD-RACE-BLOCK] %s %s estRisk=%.2f%% exceeds atomic SYMCAP=%.2f%%", sideStr, sym, estRiskPct, InpGuardMaxSymbolRiskPct);
         LogExecAuditFor(sym, sideStr, "ORDER_BLOCKED_SYMCAP", entryPrice, -1.0, normSl, lots, 0.0, 0, comment);
         return false;
      }

      ulong t0 = GetMicrosecondCount();
      bool ok = isBuy ? tr.Buy(lots, sym, entryPrice, normSl, 0.0, comment)
                      : tr.Sell(lots, sym, entryPrice, normSl, 0.0, comment);
      double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
      uint ret = tr.ResultRetcode();
      ReleaseSymbolRiskFor(sym, estRiskPct);

      if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
      {
         double rejPx = tr.ResultPrice();
         PrintFormat("[PROPGUARD-ERR] %s %s failed retcode=%u desc=%s", sideStr, sym, ret, tr.ResultRetcodeDescription());
         LogExecAuditFor(sym, sideStr, "ORDER_REJECT", entryPrice, rejPx, normSl, lots, latMs, ret, tr.ResultRetcodeDescription());
         return false;
      }
      double execLots = (tr.ResultVolume() > 0.0) ? tr.ResultVolume() : lots;
      double fillPx   = ResolveExecutedFillPrice(tr, sym, -1.0);
      string noteStr  = StringFormat("%s|deal=%I64u|ord=%I64u%s",
                                     comment, (ulong)tr.ResultDeal(), (ulong)tr.ResultOrder(),
                                     (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : "");
      LogExecAuditFor(sym, sideStr, "ORDER_FILL", entryPrice, fillPx, normSl, execLots, latMs, ret, noteStr);
      return true;
   }

   bool ExecuteChecked(CTrade &tr, const bool isBuy, const double lots, const double entryPrice, const double slPrice,
                       const string comment, const bool eaDryRun = true) const
   {
      return ExecuteCheckedFor(tr, m_symbol, isBuy, lots, entryPrice, slPrice, comment, eaDryRun);
   }

   // 14. Checked position close wrapper (verifies TRADE_RETCODE_DONE & logs ORDER_CLOSE / CLOSE_REJECT)
   bool ClosePositionChecked(CTrade &tr, const ulong ticket, const string reason, const bool eaDryRun = true) const
   {
      if(!PositionSelectByTicket(ticket)) return false;
      string psym = PositionGetString(POSITION_SYMBOL);
      double pvol = PositionGetDouble(POSITION_VOLUME);
      double psl  = PositionGetDouble(POSITION_SL);
      long ptype  = PositionGetInteger(POSITION_TYPE);
      string sideStr = (ptype == POSITION_TYPE_BUY) ? "SELL" : "BUY";
      double sigPx = (ptype == POSITION_TYPE_BUY) ? SymbolInfoDouble(psym, SYMBOL_BID) : SymbolInfoDouble(psym, SYMBOL_ASK);

      if(eaDryRun || InpGuardDryRunLogOnly)
      {
         PrintFormat("[DRYRUN-CLOSE] ticket=%I64u sym=%s vol=%.2f reason=%s", ticket, psym, pvol, reason);
         return true;
      }
      ConfigureFillingMode(tr, psym);
      ulong t0 = GetMicrosecondCount();
      bool ok = tr.PositionClose(ticket);
      double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
      uint ret = tr.ResultRetcode();
      if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
      {
         PrintFormat("[PROPGUARD-CLOSE-ERR] ticket=%I64u sym=%s ret=%u desc=%s reason=%s",
                     ticket, psym, ret, tr.ResultRetcodeDescription(), reason);
         LogExecAuditFor(psym, sideStr, "CLOSE_REJECT", sigPx, tr.ResultPrice(), psl, pvol, latMs, ret,
                         StringFormat("%s|tk=%I64u|%s", reason, ticket, tr.ResultRetcodeDescription()));
         return false;
      }
      double closePx = tr.ResultPrice();
      if(closePx <= 0.0 && tr.ResultDeal() > 0 && HistoryDealSelect(tr.ResultDeal()))
         closePx = HistoryDealGetDouble(tr.ResultDeal(), DEAL_PRICE);
      double closedVol = (tr.ResultVolume() > 0.0) ? tr.ResultVolume() : pvol;
      LogExecAuditFor(psym, sideStr, "ORDER_CLOSE", sigPx, (closePx > 0.0 ? closePx : -1.0), psl, closedVol, latMs, ret,
                      StringFormat("%s|tk=%I64u|deal=%I64u", reason, ticket, (ulong)tr.ResultDeal()));
      return true;
   }
};

#endif // NAQEX_PROPGUARD_MQH
