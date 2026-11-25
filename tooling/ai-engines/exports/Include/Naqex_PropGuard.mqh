//+------------------------------------------------------------------+
//| Naqex_PropGuard.mqh (v3.1 — Full-Stack Fail-Closed Prop Guard)   |
//| Shared Production Safety, Atomic SymCap, Margin & TCA Logger     |
//| v1.01 Hardened: ServerNow(), 23-date NYSE calendar, ±135s hard   |
//| ban helper, live-calibrated SetDeviationInPoints, safe volDigits |
//| rounding, reqMargin <= 0 fail-closed, magicOverride TCA audit    |
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
   string   label;
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
   datetime          m_maxEventTsUsd;
   datetime          m_maxEventTsEur;
   datetime          m_maxEventTsGbp;
   datetime          m_maxEventTsJpy;
   datetime          m_maxEventTsAud;
   datetime          m_maxEventTsCad;
   double            m_dayStartEquity;
   int               m_dayKey;
   datetime          m_lastTradedDay;

   string StateKey(const string suffix) const
   {
      return StringFormat("NQXG_%I64d_%u_%I64d_%s_%s", CurrentAccountLogin(), CurrentAccountServerHash(), m_magic, m_symbol, suffix);
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

   static string SymResLockKey(const string sym) { return StringFormat("NQXG_RLOCK_%I64d_%u_%s", CurrentAccountLogin(), CurrentAccountServerHash(), sym); }
   static string SymResPctKey(const string sym)  { return StringFormat("NQXG_RPCT_%I64d_%u_%s",  CurrentAccountLogin(), CurrentAccountServerHash(), sym); }
   static string SymResTsKey(const string sym)   { return StringFormat("NQXG_RTS_%I64d_%u_%s",   CurrentAccountLogin(), CurrentAccountServerHash(), sym); }
   static string SymResLockTsKey(const string sym){ return StringFormat("NQXG_RLTS_%I64d_%u_%s", CurrentAccountLogin(), CurrentAccountServerHash(), sym); }

   bool AcquireSymbolLock(const string sym) const
   {
      string lk = SymResLockKey(sym);
      string ltk = SymResLockTsKey(sym);
      long nowTs = (long)NowUTC();
      for(int attempt = 0; attempt < 25; attempt++)
      {
         // Atomic creation/acquire: only initialize to 0 if truly absent, then CAS 0 -> 1
         if(!GlobalVariableCheck(lk))
            GlobalVariableSetOnCondition(lk, 0.0, 0.0);
         if(GlobalVariableSetOnCondition(lk, 1.0, 0.0))
         {
            GlobalVariableSet(ltk, (double)nowTs);
            return true;
         }
         // Break ONLY mutex lock if stale > 15s (NEVER clears active unknown-state risk reservation!)
         if(GlobalVariableCheck(ltk))
         {
            long prevLockTs = (long)GlobalVariableGet(ltk);
            if(nowTs - prevLockTs > 15)
            {
               if(GlobalVariableSetOnCondition(lk, 0.0, 1.0) && GlobalVariableSetOnCondition(lk, 1.0, 0.0))
               {
                  GlobalVariableSet(ltk, (double)nowTs);
                  return true;
               }
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
      // Hold unconfirmed/unknown-state reservations up to 120s so slow broker ACKs cannot double-spend risk (R2-02)
      if(age < 0 || age > 120)
         return 0.0;
      return MathMax(0.0, GlobalVariableGet(pk));
   }

public:
   CNaqexPropGuard() : m_symbol(""), m_magic(0), m_eaMaxDailyLossPct(0.0), m_eventCount(0), m_maxEventTs(0),
                       m_maxEventTsUsd(0), m_maxEventTsEur(0), m_maxEventTsGbp(0), m_maxEventTsJpy(0),
                       m_maxEventTsAud(0), m_maxEventTsCad(0), m_dayStartEquity(0.0), m_dayKey(-1), m_lastTradedDay(0) {}

   // Account-login + server-hash scoped GlobalVariable keys (R2-02: prevents cross-server login collision)
   static long CurrentAccountLogin()
   {
      return AccountInfoInteger(ACCOUNT_LOGIN);
   }
   static uint CurrentAccountServerHash()
   {
      string srv = AccountInfoString(ACCOUNT_SERVER);
      uint h = 2166136261;
      int n = StringLen(srv);
      for(int i = 0; i < n; i++)
      {
         h ^= (uint)StringGetCharacter(srv, i);
         h *= 16777619;
      }
      return h;
   }
   static string GlobalKillKey()    { return StringFormat("NQXG_GLOBAL_KILLSWITCH_%I64d_%u", CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string GlobalMultKey()    { return StringFormat("NQXG_GLOBAL_RISK_MULT_%I64d_%u",  CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string OrchTsKey()        { return StringFormat("NQXG_ORCH_TS_%I64d_%u",           CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string AcctDayKeyName()   { return StringFormat("NQXG_ACCT_DAYKEY_%I64d_%u",       CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string AcctDayEqKeyName() { return StringFormat("NQXG_ACCT_DAYEQ_%I64d_%u",        CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string AcctDayBalKeyName(){ return StringFormat("NQXG_ACCT_DAYBAL_%I64d_%u",       CurrentAccountLogin(), CurrentAccountServerHash()); }
   static string AcctAutoKillKey()  { return StringFormat("NQXG_ACCT_AUTOKILL_%I64d_%u",     CurrentAccountLogin(), CurrentAccountServerHash()); }

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

   // 1b. Safe lot rounding & live-calibrated SetDeviationInPoints (V101-06)
   static int ComputeVolumeDigits(const double volStep)
   {
      if(volStep <= 0.0) return 2;
      int digits = 0;
      double scaled = volStep;
      while(digits < 8 && MathAbs(scaled - MathRound(scaled)) > 1e-7)
      {
         scaled *= 10.0;
         digits++;
      }
      return digits;
   }

   static double RoundVolumeDownToStep(const double rawLots, const double volStep, const double volMin, const double volMax)
   {
      if(rawLots <= 0.0 || volStep <= 0.0) return 0.0;
      int volDigits = ComputeVolumeDigits(volStep);
      double lots = NormalizeDouble(MathFloor((rawLots + 1e-9) / volStep) * volStep, volDigits);
      if(lots < volMin) return 0.0;
      return NormalizeDouble(MathMin(lots, volMax), volDigits);
   }

   static bool IsIndexSymbol(const string sym)
   {
      string u = sym;
      StringToUpper(u);
      return (StringFind(u, "US100")  >= 0 || StringFind(u, "NAS100") >= 0 ||
              StringFind(u, "NDX")    >= 0 || StringFind(u, "USTEC")  >= 0 ||
              StringFind(u, "US500")  >= 0 || StringFind(u, "SPX")    >= 0 ||
              StringFind(u, "US30")   >= 0 || StringFind(u, "GER40")  >= 0 ||
              StringFind(u, "DE40")   >= 0 || StringFind(u, "DAX")    >= 0 ||
              StringFind(u, "UK100")  >= 0 || StringFind(u, "FTSE")   >= 0);
   }

   static ulong RecommendedDeviationPoints(const string sym, const ulong fxPts = 35, const ulong idxPts = 450, const ulong metalPts = 80)
   {
      if(IsIndexSymbol(sym)) return idxPts;
      string u = sym;
      StringToUpper(u);
      if(StringFind(u, "XAU") >= 0 || StringFind(u, "XAG") >= 0) return metalPts;
      return fxPts;
   }

   static void ConfigureDeviationPoints(CTrade &tr, const string sym, const ulong fxPts = 35, const ulong idxPts = 450, const ulong metalPts = 80)
   {
      tr.SetDeviationInPoints(RecommendedDeviationPoints(sym, fxPts, idxPts, metalPts));
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
            PrintFormat("[PROPGUARD-WARN] Red-news CSV '%s' missing or empty (loaded=%d err=%d) — entries FAIL-CLOSED blocked!", InpGuardRedNewsCsvFile, loaded, GetLastError());
         else
            PrintFormat("[PROPGUARD-OK] Loaded %d red-news events from '%s' (max_ts=%I64d)", loaded, InpGuardRedNewsCsvFile, (long)m_maxEventTs);
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

   static int NthWeekdayOfMonth(const int year, const int month, const int targetDow, const int nth)
   {
      MqlDateTime d;
      ZeroMemory(d);
      d.year = year; d.mon = month; d.day = 1;
      TimeToStruct(StructToTime(d), d);
      return 1 + ((targetDow - d.day_of_week + 7) % 7) + (nth - 1) * 7;
   }

   static int LastWeekdayOfMonth(const int year, const int month, const int targetDow)
   {
      MqlDateTime d;
      ZeroMemory(d);
      d.year = (month == 12) ? (year + 1) : year;
      d.mon  = (month == 12) ? 1 : (month + 1);
      d.day  = 1;
      datetime lastDayTs = StructToTime(d) - 86400;
      TimeToStruct(lastDayTs, d);
      return d.day - ((d.day_of_week - targetDow + 7) % 7);
   }

   static void GregorianEasterSunday(const int year, int &outMon, int &outDay)
   {
      int a = year % 19;
      int b = year / 100;
      int c = year % 100;
      int d = b / 4;
      int e = b % 4;
      int f = (b + 8) / 25;
      int g = (b - f + 1) / 3;
      int h = (19 * a + b - d - g + 15) % 30;
      int i = c / 4;
      int k = c % 4;
      int l = (32 + 2 * e + 2 * i - h - k) % 7;
      int m = (a + 11 * h + 22 * l) / 451;
      outMon = (h + l - 7 * m + 114) / 31;
      outDay = ((h + l - 7 * m + 114) % 31) + 1;
   }

   static bool MatchesObservedFixedHoliday(const MqlDateTime &ny, const int holMon, const int holDay)
   {
      MqlDateTime h;
      ZeroMemory(h);
      h.year = ny.year; h.mon = holMon; h.day = holDay;
      datetime hTs = StructToTime(h);
      TimeToStruct(hTs, h);
      if(h.day_of_week == 6)      hTs -= 86400; // Saturday -> observed Friday
      else if(h.day_of_week == 0) hTs += 86400; // Sunday -> observed Monday
      TimeToStruct(hTs, h);
      return (ny.mon == h.mon && ny.day == h.day);
   }

   static bool IsUsEquityHolidayOrHalfDayNY(const MqlDateTime &ny)
   {
      // Full NYSE holiday & 13:00 ET early-close calendar (V101-04: covers all 23 dates in 2026-2027)
      // 1. New Year's Day (observed, including Dec 31 if Jan 1 next year falls on Saturday)
      if(MatchesObservedFixedHoliday(ny, 1, 1)) return true;
      if(ny.mon == 12 && ny.day == 31)
      {
         MqlDateTime nyNext; ZeroMemory(nyNext); nyNext.year = ny.year + 1; nyNext.mon = 1; nyNext.day = 1;
         TimeToStruct(StructToTime(nyNext), nyNext);
         if(nyNext.day_of_week == 6) return true;
      }
      // 2. MLK Day (3rd Mon Jan) & Presidents' Day (3rd Mon Feb)
      if(ny.mon == 1 && ny.day == NthWeekdayOfMonth(ny.year, 1, 1, 3)) return true;
      if(ny.mon == 2 && ny.day == NthWeekdayOfMonth(ny.year, 2, 1, 3)) return true;
      // 3. Good Friday (Easter Sunday - 2 days via Anonymous Gregorian algorithm)
      if(ny.mon == 3 || ny.mon == 4)
      {
         int eMon = 0, eDay = 0;
         GregorianEasterSunday(ny.year, eMon, eDay);
         MqlDateTime gf; ZeroMemory(gf); gf.year = ny.year; gf.mon = eMon; gf.day = eDay;
         TimeToStruct(StructToTime(gf) - 2 * 86400, gf);
         if(ny.mon == gf.mon && ny.day == gf.day) return true;
      }
      // 4. Memorial Day (Last Mon May) & Juneteenth (June 19 observed)
      if(ny.mon == 5 && ny.day == LastWeekdayOfMonth(ny.year, 5, 1)) return true;
      if(MatchesObservedFixedHoliday(ny, 6, 19)) return true;
      // 5. Independence Day (July 4 observed) + July 3 early close when July 4 is Tue..Fri
      if(MatchesObservedFixedHoliday(ny, 7, 4)) return true;
      if(ny.mon == 7 && ny.day == 3)
      {
         MqlDateTime j4; ZeroMemory(j4); j4.year = ny.year; j4.mon = 7; j4.day = 4;
         TimeToStruct(StructToTime(j4), j4);
         if(j4.day_of_week >= 2 && j4.day_of_week <= 5) return true;
      }
      // 6. Labor Day (1st Mon Sep)
      if(ny.mon == 9 && ny.day == NthWeekdayOfMonth(ny.year, 9, 1, 1)) return true;
      // 7. Thanksgiving (4th Thu Nov) & Black Friday early close (day after Thanksgiving)
      if(ny.mon == 11)
      {
         int tgDay = NthWeekdayOfMonth(ny.year, 11, 4, 4);
         if(ny.day == tgDay || ny.day == tgDay + 1) return true;
      }
      // 8. Christmas Day (Dec 25 observed) + Christmas Eve early close (weekday Dec 24)
      if(MatchesObservedFixedHoliday(ny, 12, 25)) return true;
      if(ny.mon == 12 && ny.day == 24 && ny.day_of_week >= 1 && ny.day_of_week <= 5) return true;
      return false;
   }

   static bool IsUsEquityHalfDayNY(const MqlDateTime &ny)
   {
      return IsUsEquityHolidayOrHalfDayNY(ny);
   }

   // V101-03: Use TimeTradeServer() when live (never freezes on quiet ticks); TimeCurrent() inside MQL_TESTER
   static datetime ServerNow()
   {
      if(MQLInfoInteger(MQL_TESTER)) return TimeCurrent();
      datetime ts = TimeTradeServer();
      return (ts > 0) ? ts : TimeCurrent();
   }

   datetime NowUTC() const
   {
      if(MQLInfoInteger(MQL_TESTER))
      {
         datetime srvNow = ServerNow();
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

   // 7. Rollover blackout & spread spike filter (supports wrap-around, same-day windows & per-symbol spread override)
   bool IsSpreadAndSessionSafeFor(const string sym, const double maxSpreadOverridePts = -1.0) const
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
      double effMaxSpread = (maxSpreadOverridePts >= 0.0) ? maxSpreadOverridePts : InpGuardMaxSpreadPoints;
      if(effMaxSpread > 0.0)
      {
         double spreadPts = (double)SymbolInfoInteger(sym, SYMBOL_SPREAD);
         if(spreadPts > effMaxSpread)
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
      datetime srvNow = ServerNow();
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
   //    R2-05: tracks per-currency expiry & expands unfixed BoJ EST03UTC window to +/-3600s!
   int LoadRedNewsCsv(const string fileName)
   {
      m_eventCount = 0;
      m_maxEventTs = 0;
      m_maxEventTsUsd = 0; m_maxEventTsEur = 0; m_maxEventTsGbp = 0;
      m_maxEventTsJpy = 0; m_maxEventTsAud = 0; m_maxEventTsCad = 0;
      ArrayResize(m_events, 0);
      int fh = INVALID_HANDLE;
      for(int attempt = 0; attempt < 10; attempt++)
      {
         fh = FileOpen(fileName, FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
         if(fh != INVALID_HANDLE) break;
         Sleep(25);
      }
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
         string uCcy = colCcy;
         StringToUpper(uCcy);
         ArrayResize(m_events, m_eventCount + 1, 64);
         m_events[m_eventCount].utc_ts = (datetime)ts;
         m_events[m_eventCount].ccy    = uCcy;
         m_events[m_eventCount].label  = colEv;
         if((datetime)ts > m_maxEventTs) m_maxEventTs = (datetime)ts;
         if(uCcy == "USD" && (datetime)ts > m_maxEventTsUsd) m_maxEventTsUsd = (datetime)ts;
         if(uCcy == "EUR" && (datetime)ts > m_maxEventTsEur) m_maxEventTsEur = (datetime)ts;
         if(uCcy == "GBP" && (datetime)ts > m_maxEventTsGbp) m_maxEventTsGbp = (datetime)ts;
         if(uCcy == "JPY" && (datetime)ts > m_maxEventTsJpy) m_maxEventTsJpy = (datetime)ts;
         if(uCcy == "AUD" && (datetime)ts > m_maxEventTsAud) m_maxEventTsAud = (datetime)ts;
         if(uCcy == "CAD" && (datetime)ts > m_maxEventTsCad) m_maxEventTsCad = (datetime)ts;
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

   bool IsRedNewsCalendarHealthyFor(const string sym) const
   {
      if(!IsRedNewsCalendarHealthy()) return false;
      if(!InpGuardEnableRedNews || MQLInfoInteger(MQL_TESTER)) return true;
      datetime nowUtc = NowUTC();
      // Every active currency matched by `sym` must itself have non-expired schedule coverage (R2-05)
      if(CurrencyMatchesSymbolFor(sym, "USD") && (m_maxEventTsUsd <= 0 || nowUtc > m_maxEventTsUsd + 86400)) return false;
      if(CurrencyMatchesSymbolFor(sym, "EUR") && (m_maxEventTsEur <= 0 || nowUtc > m_maxEventTsEur + 86400)) return false;
      if(CurrencyMatchesSymbolFor(sym, "GBP") && (m_maxEventTsGbp <= 0 || nowUtc > m_maxEventTsGbp + 86400)) return false;
      if(CurrencyMatchesSymbolFor(sym, "JPY") && (m_maxEventTsJpy <= 0 || nowUtc > m_maxEventTsJpy + 86400)) return false;
      if(CurrencyMatchesSymbolFor(sym, "AUD") && (m_maxEventTsAud <= 0 || nowUtc > m_maxEventTsAud + 86400)) return false;
      if(CurrencyMatchesSymbolFor(sym, "CAD") && (m_maxEventTsCad <= 0 || nowUtc > m_maxEventTsCad + 86400)) return false;
      return true;
   }

   bool IsInsideRedNewsWindowFor(const string sym) const
   {
      if(!InpGuardEnableRedNews) return false;
      // FAIL-CLOSED: missing, empty, or per-currency expired calendar blocks new entries!
      if(!IsRedNewsCalendarHealthyFor(sym)) return true;
      datetime nowUtc = NowUTC();
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbolFor(sym, m_events[i].ccy)) continue;
         int effPad = (StringFind(m_events[i].label, "EST03UTC") >= 0) ? MathMax(InpGuardNewsPadSec, 3600) : InpGuardNewsPadSec;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= effPad)
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
      if(!InpGuardEnableRedNews || !IsRedNewsCalendarHealthyFor(sym)) return false;
      datetime nowUtc = NowUTC();
      bool inPreFlatten = false;
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbolFor(sym, m_events[i].ccy)) continue;
         int effPad = (StringFind(m_events[i].label, "EST03UTC") >= 0) ? MathMax(InpGuardNewsPadSec, 3600) : InpGuardNewsPadSec;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= InpGuardNewsHardBanSec)
            return false;
         if(diff > InpGuardNewsHardBanSec && diff <= effPad)
            inPreFlatten = true;
      }
      return inPreFlatten;
   }

   bool IsInRedNewsPreFlattenWindow() const
   {
      return IsInRedNewsPreFlattenWindowFor(m_symbol);
   }

   // V101-04: True inside hard +/-InpGuardNewsHardBanSec (+/-135s) no-execution ban zone
   // Blocks non-emergency clock-flatten closes from violating FTMO/The5ers +/-2m rule!
   bool IsInsideRedNewsHardBanFor(const string sym) const
   {
      if(!InpGuardEnableRedNews || !IsRedNewsCalendarHealthyFor(sym)) return false;
      datetime nowUtc = NowUTC();
      for(int i = 0; i < m_eventCount; i++)
      {
         if(!CurrencyMatchesSymbolFor(sym, m_events[i].ccy)) continue;
         long diff = (long)m_events[i].utc_ts - (long)nowUtc;
         if(MathAbs(diff) <= InpGuardNewsHardBanSec)
            return true;
      }
      return false;
   }

   bool IsInsideRedNewsHardBan() const
   {
      return IsInsideRedNewsHardBanFor(m_symbol);
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

      double clampedLots = RoundVolumeDownToStep(riskMoney / lossPerLot, volStep, volMin, volMax);
      if(clampedLots < volMin) return 0.0;

      // Free-margin safety check via OrderCalcMargin — STRICTLY FAIL-CLOSED (R2-04 + V101-06: reqMargin <= 0.0)!
      // Missing quote, non-positive free margin, or OrderCalcMargin failure/0 MUST return 0.0 (NEVER raw lots).
      ENUM_ORDER_TYPE ordType = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double refPx = isBuy ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      double reqMargin = 0.0;
      if(refPx <= 0.0 || freeMargin <= 0.0) return 0.0;
      if(!OrderCalcMargin(ordType, sym, clampedLots, refPx, reqMargin) || reqMargin <= 0.0) return 0.0;
      double maxAllowedMargin = freeMargin * 0.85;
      if(reqMargin > maxAllowedMargin)
      {
         clampedLots = RoundVolumeDownToStep(clampedLots * (maxAllowedMargin / reqMargin), volStep, volMin, volMax);
         if(clampedLots < volMin) return 0.0;
      }
      return clampedLots;
   }

   // 11b. Directional Factor Cluster Risk Accounting (Astra R2-07 / Round-3: USD, JPY, US100 clusters)
   static void AccumulateDirectionalFactor(const string sym, const bool isBuy, const double riskPct,
                                           double &usdLong, double &usdShort,
                                           double &jpyLong, double &jpyShort,
                                           double &idxLong, double &idxShort)
   {
      if(riskPct <= 0.0) return;
      string u = sym;
      StringToUpper(u);
      int dir = isBuy ? 1 : -1;
      if(StringFind(u, "US100") >= 0 || StringFind(u, "NAS100") >= 0 || StringFind(u, "NDX") >= 0 ||
         StringFind(u, "USTEC") >= 0 || StringFind(u, "US500") >= 0 || StringFind(u, "SPX") >= 0)
      {
         if(dir > 0) idxLong += riskPct; else idxShort += riskPct;
         return;
      }
      int posUsd = StringFind(u, "USD");
      if(posUsd == 0)
      {
         if(dir > 0) usdLong += riskPct; else usdShort += riskPct;
      }
      else if(posUsd >= 3)
      {
         if(dir > 0) usdShort += riskPct; else usdLong += riskPct;
      }
      int posJpy = StringFind(u, "JPY");
      if(posJpy == 0)
      {
         if(dir > 0) jpyLong += riskPct; else jpyShort += riskPct;
      }
      else if(posJpy >= 3)
      {
         if(dir > 0) jpyShort += riskPct; else jpyLong += riskPct;
      }
   }

   double ComputeAccountFactorRisk(double &usdLong, double &usdShort,
                                   double &jpyLong, double &jpyShort,
                                   double &idxLong, double &idxShort) const
   {
      usdLong = 0.0; usdShort = 0.0;
      jpyLong = 0.0; jpyShort = 0.0;
      idxLong = 0.0; idxShort = 0.0;
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal <= 0.0) return 999.0;
      double totalPct = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         string psym = PositionGetString(POSITION_SYMBOL);
         double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
         double slPx   = PositionGetDouble(POSITION_SL);
         double vol    = PositionGetDouble(POSITION_VOLUME);
         if(vol <= 0.0) continue;
         if(slPx <= 0.0) return 999.0; // FAIL-CLOSED on orphan no-SL position!
         double tSize = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE);
         double tVal  = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE_LOSS);
         if(tVal <= 0.0) tVal = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE);
         if(tSize <= 0.0 || tVal <= 0.0) return 999.0;
         double rPct = (((MathAbs(openPx - slPx) / tSize) * tVal * vol) / bal) * 100.0;
         totalPct += rPct;
         bool pBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         AccumulateDirectionalFactor(psym, pBuy, rPct, usdLong, usdShort, jpyLong, jpyShort, idxLong, idxShort);
      }
      return totalPct;
   }

   double ComputeFactorHeadroomPct(const string sym, const bool isBuy,
                                   const double maxUsdClusterPct, const double maxJpyClusterPct,
                                   const double maxIdxClusterPct, const double maxTotalOpenPct,
                                   const double extraUsdLong = 0.0, const double extraUsdShort = 0.0,
                                   const double extraJpyLong = 0.0, const double extraJpyShort = 0.0,
                                   const double extraIdxLong = 0.0, const double extraIdxShort = 0.0,
                                   const double extraTotal = 0.0) const
   {
      double uL, uS, jL, jS, iL, iS;
      double tot = ComputeAccountFactorRisk(uL, uS, jL, jS, iL, iS);
      if(tot >= 900.0) return 0.0;
      uL += extraUsdLong; uS += extraUsdShort;
      jL += extraJpyLong; jS += extraJpyShort;
      iL += extraIdxLong; iS += extraIdxShort;
      tot += extraTotal;

      double headroom = (maxTotalOpenPct > 0.0) ? MathMax(0.0, maxTotalOpenPct - tot) : 999.0;
      double dUL = 0.0, dUS = 0.0, dJL = 0.0, dJS = 0.0, dIL = 0.0, dIS = 0.0;
      AccumulateDirectionalFactor(sym, isBuy, 1.0, dUL, dUS, dJL, dJS, dIL, dIS);
      if(maxUsdClusterPct > 0.0)
      {
         if(dUL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxUsdClusterPct - uL));
         if(dUS > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxUsdClusterPct - uS));
      }
      if(maxJpyClusterPct > 0.0)
      {
         if(dJL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxJpyClusterPct - jL));
         if(dJS > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxJpyClusterPct - jS));
      }
      if(maxIdxClusterPct > 0.0)
      {
         if(dIL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxIdxClusterPct - iL));
         if(dIS > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxIdxClusterPct - iS));
      }
      return MathMax(0.0, headroom);
   }

   double ComputeSafeLots(const double requestedRiskPct, const double slDistancePrice, const bool isBuy = true) const
   {
      return ComputeSafeLotsFor(m_symbol, requestedRiskPct, slDistancePrice, isBuy);
   }

   // 12. Structured CSV execution audit logger (feeds Python quant_factory.tca_reconcile; V101-01 magicOverride!)
   void LogExecAuditFor(const string sym, const string side, const string evType, const double sigPx, const double fillPx,
                        const double slPx, const double lots, const double latencyMs, const uint retcode, const string note,
                        const long magicOverride = -1) const
   {
      if(MQLInfoInteger(MQL_TESTER)) return;
      bool needHeader = !FileIsExist(InpGuardTcaAuditCsvFile);
      int fh = INVALID_HANDLE;
      for(int attempt = 0; attempt < 8; attempt++)
      {
         fh = FileOpen(InpGuardTcaAuditCsvFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
         if(fh != INVALID_HANDLE) break;
         Sleep(20);
      }
      if(fh == INVALID_HANDLE)
      {
         PrintFormat("[PROPGUARD-AUDIT-ERR] Failed to open '%s' err=%d ev=%s sym=%s", InpGuardTcaAuditCsvFile, GetLastError(), evType, sym);
         return;
      }
      FileSeek(fh, 0, SEEK_END);
      if(needHeader)
         FileWrite(fh, "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price", "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "comment");
      double spPts = (double)SymbolInfoInteger(sym, SYMBOL_SPREAD);
      long effMagic = (magicOverride > 0) ? magicOverride : m_magic;
      FileWrite(fh, (long)NowUTC(), effMagic, sym, side, evType,
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

   // 12b. Resolve actual broker-executed fill price (R2-02: exact order/deal match ONLY — NEVER fallback to unrelated open pos!)
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
      ulong ord = tr.ResultOrder();
      if(ord > 0)
      {
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            ulong tk = PositionGetTicket(i);
            if(tk == 0) continue;
            if((ulong)PositionGetInteger(POSITION_IDENTIFIER) == ord && PositionGetString(POSITION_SYMBOL) == sym)
            {
               double opx = PositionGetDouble(POSITION_PRICE_OPEN);
               if(opx > 0.0) return opx;
            }
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
      // V101-06: Check STOPS_LEVEL against actual liquidation price (Bid for BUY, Ask for SELL)
      double liqPx = isBuy ? SymbolInfoDouble(sym, SYMBOL_BID) : SymbolInfoDouble(sym, SYMBOL_ASK);
      if(liqPx <= 0.0) liqPx = entryPrice;
      double stopsGap = isBuy ? (liqPx - normSl) : (normSl - liqPx);
      if(pt > 0.0 && stopsLvl > 0 && stopsGap < (double)stopsLvl * pt)
      {
         PrintFormat("[PROPGUARD-ERR] %s SL too close to stops_level=%I64d", sym, stopsLvl);
         return false;
      }

      ConfigureFillingMode(tr, sym);
      ConfigureDeviationPoints(tr, sym);
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

      // R2-02: ONLY release reservation when broker confirmed a definite terminal outcome!
      // On TIMEOUT or PLACED (unknown final fill state), KEEP reservation locked so concurrent EAs cannot double-spend!
      bool isUnknownInFlight = (ret == TRADE_RETCODE_TIMEOUT || ret == TRADE_RETCODE_PLACED);
      if(!isUnknownInFlight)
         ReleaseSymbolRiskFor(sym, estRiskPct);

      if(isUnknownInFlight)
      {
         PrintFormat("[PROPGUARD-UNKNOWN] %s %s retcode=%u — keeping risk reservation held until reconciled!", sideStr, sym, ret);
         LogExecAuditFor(sym, sideStr, "FILL_UNRESOLVED", entryPrice, -1.0, normSl, lots, latMs, ret,
                         StringFormat("%s|ord=%I64u|UNKNOWN_INFLIGHT", comment, (ulong)tr.ResultOrder()));
         return false;
      }
      if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
      {
         double rejPx = tr.ResultPrice();
         PrintFormat("[PROPGUARD-ERR] %s %s failed retcode=%u desc=%s", sideStr, sym, ret, tr.ResultRetcodeDescription());
         LogExecAuditFor(sym, sideStr, "ORDER_REJECT", entryPrice, rejPx, normSl, lots, latMs, ret, tr.ResultRetcodeDescription());
         return false;
      }
      double execLots = tr.ResultVolume();
      if(execLots <= 0.0 && tr.ResultDeal() > 0 && HistoryDealSelect(tr.ResultDeal()))
         execLots = HistoryDealGetDouble(tr.ResultDeal(), DEAL_VOLUME);
      bool volUnresolved = (execLots <= 0.0);
      if(volUnresolved) execLots = lots;
      double fillPx   = ResolveExecutedFillPrice(tr, sym, -1.0);
      string noteStr  = StringFormat("%s|deal=%I64u|ord=%I64u%s%s",
                                     comment, (ulong)tr.ResultDeal(), (ulong)tr.ResultOrder(),
                                     (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : "",
                                     volUnresolved ? "|VOL_UNRESOLVED" : "");
      LogExecAuditFor(sym, sideStr, "ORDER_FILL", entryPrice, fillPx, normSl, execLots, latMs, ret, noteStr);
      return true;
   }

   bool ExecuteChecked(CTrade &tr, const bool isBuy, const double lots, const double entryPrice, const double slPrice,
                       const string comment, const bool eaDryRun = true) const
   {
      return ExecuteCheckedFor(tr, m_symbol, isBuy, lots, entryPrice, slPrice, comment, eaDryRun);
   }

   // 14. Checked position close wrapper (R2-02 + V101-01/06: verifies remaining volume == 0, logs real magic + tk/pos!)
   bool ClosePositionChecked(CTrade &tr, const ulong ticket, const string reason, const bool eaDryRun = true) const
   {
      if(!PositionSelectByTicket(ticket)) return false;
      string psym  = PositionGetString(POSITION_SYMBOL);
      long pmagic  = PositionGetInteger(POSITION_MAGIC);
      ulong posId  = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      double pvol  = PositionGetDouble(POSITION_VOLUME);
      double psl   = PositionGetDouble(POSITION_SL);
      long ptype   = PositionGetInteger(POSITION_TYPE);
      string sideStr = (ptype == POSITION_TYPE_BUY) ? "SELL" : "BUY";
      double sigPx = (ptype == POSITION_TYPE_BUY) ? SymbolInfoDouble(psym, SYMBOL_BID) : SymbolInfoDouble(psym, SYMBOL_ASK);

      if(eaDryRun || InpGuardDryRunLogOnly)
      {
         PrintFormat("[DRYRUN-CLOSE] ticket=%I64u pos=%I64u magic=%I64d sym=%s vol=%.2f reason=%s", ticket, posId, pmagic, psym, pvol, reason);
         return true;
      }
      ConfigureFillingMode(tr, psym);
      ConfigureDeviationPoints(tr, psym);
      ulong t0 = GetMicrosecondCount();
      bool ok = tr.PositionClose(ticket);
      double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
      uint ret = tr.ResultRetcode();
      if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
      {
         PrintFormat("[PROPGUARD-CLOSE-ERR] ticket=%I64u pos=%I64u sym=%s ret=%u desc=%s reason=%s",
                     ticket, posId, psym, ret, tr.ResultRetcodeDescription(), reason);
         LogExecAuditFor(psym, sideStr, "CLOSE_REJECT", sigPx, tr.ResultPrice(), psl, pvol, latMs, ret,
                         StringFormat("%s|tk=%I64u|pos=%I64u|%s", reason, ticket, posId, tr.ResultRetcodeDescription()),
                         pmagic);
         return false;
      }
      double closePx = tr.ResultPrice();
      if(closePx <= 0.0 && tr.ResultDeal() > 0 && HistoryDealSelect(tr.ResultDeal()))
         closePx = HistoryDealGetDouble(tr.ResultDeal(), DEAL_PRICE);
      double closedVol = tr.ResultVolume();
      if(closedVol <= 0.0 && tr.ResultDeal() > 0 && HistoryDealSelect(tr.ResultDeal()))
         closedVol = HistoryDealGetDouble(tr.ResultDeal(), DEAL_VOLUME);
      if(closedVol <= 0.0) closedVol = pvol;

      // Verify whether position is actually fully flat or partially remaining (R2-02)
      bool stillOpen = PositionSelectByTicket(ticket);
      double remVol = stillOpen ? PositionGetDouble(POSITION_VOLUME) : 0.0;
      string evType = (stillOpen && remVol > 0.0) ? "PARTIAL_EXIT" : "ORDER_CLOSE";
      LogExecAuditFor(psym, sideStr, evType, sigPx, (closePx > 0.0 ? closePx : -1.0), psl, closedVol, latMs, ret,
                      StringFormat("%s|tk=%I64u|pos=%I64u|deal=%I64u|rem=%.2f%s",
                                   reason, ticket, posId, (ulong)tr.ResultDeal(), remVol,
                                   (closePx <= 0.0) ? "|FILL_UNRESOLVED" : ""),
                      pmagic);
      return !(stillOpen && remVol > 0.0);
   }
};

#endif // NAQEX_PROPGUARD_MQH
