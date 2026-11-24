//+------------------------------------------------------------------+
//| Naqex_AccountOrchestrator.mq5                                    |
//| Account-Wide Risk Orchestrator, AMBER/RED/PROFIT_LOCK Brake,     |
//| Global Kill-Switch, Orphan Detector & JSON Heartbeat Writer      |
//| Attach to ONE chart on the MT5 terminal running the 8 Naqex EAs. |
//+------------------------------------------------------------------+
#property strict
#property version   "2.01"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          g_orchTrade;
CNaqexPropGuard g_orchGuard;

input bool   InpDryRunLogOnly      = true;       // SAFETY: true = monitor & log only, NO live flatten
input double InpInitialBalanceUSD  = 10000.0;    // Account initial size (e.g., 10000 FTMO / 5000 The5ers)
input double InpBasePhaseMult      = 1.00;       // Phase base risk mult (1.00 Funded / 2.67 P1 Balanced)
input double InpAmberDdPct         = 3.50;       // Overall DD % triggering AMBER brake
input double InpAmberMult          = 0.65;       // Risk mult under AMBER brake
input double InpRedDdPct           = 6.00;       // Overall DD % triggering RED brake
input double InpRedMult            = 0.40;       // Risk mult under RED brake
input double InpProfitLockPct      = 0.00;       // Profit % above initial balance to lock/de-risk (0.00 = disabled)
input double InpProfitLockMult     = 2.00;       // Risk mult cap when PROFIT_LOCK triggers
input double InpKillDailyDdPct     = 3.00;       // Daily DD % triggering GLOBAL KILL-SWITCH (< 5% prop limit)
input double InpKillStaticDdPct    = 7.50;       // Static DD % triggering GLOBAL KILL-SWITCH (< 10% prop limit)
input int    InpDailyResetMode     = 1;          // Daily anchor reset: 0=MT5 Server Midnight (The5ers), 1=Europe/Prague CET/CEST (FTMO), 2=UTC
input int    InpHeartbeatSec       = 15;         // Heartbeat JSON write interval (seconds)
input string InpHeartbeatFile      = "naqex_heartbeat.json";
input bool   InpAllowManualHaltFile = false;      // Opt-in bridge for 2-step covered Cockpit halt flag
input string InpManualHaltFile     = "naqex_manual_halt.flag";
input long   InpMagicRangeMin      = 20261120;
input long   InpMagicRangeMax      = 20261199;

int      g_dayKey         = -1;
double   g_dayAnchorEq    = 0.0;
double   g_dayAnchorBal   = 0.0;
bool     g_autoKillActive = false;
datetime g_lastHbWrite    = 0;

int LastSundayOfMonth(const int year, const int month)
{
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year;
   d.mon  = month;
   d.day  = 31;
   TimeToStruct(StructToTime(d), d);
   return 31 - d.day_of_week;
}

int PragueUtcOffsetHours(const MqlDateTime &utc)
{
   // EU DST (Europe/Prague): CEST (UTC+2) from last Sun Mar 01:00 UTC to last Sun Oct 01:00 UTC, else CET (UTC+1)
   if(utc.mon < 3 || utc.mon > 10) return 1;
   if(utc.mon > 3 && utc.mon < 10) return 2;
   int lastSun = LastSundayOfMonth(utc.year, utc.mon);
   if(utc.mon == 3)
      return (utc.day > lastSun || (utc.day == lastSun && utc.hour >= 1)) ? 2 : 1;
   return (utc.day < lastSun || (utc.day == lastSun && utc.hour < 1)) ? 2 : 1;
}

int CurrentResetDayKey()
{
   datetime refTs = 0;
   if(InpDailyResetMode == 0)
   {
      // The5ers: MT5 broker server midnight
      refTs = TimeCurrent();
   }
   else if(InpDailyResetMode == 1)
   {
      // FTMO: Europe/Prague midnight (CET/CEST), using tester-safe NowUTC()
      datetime nowUtc = g_orchGuard.NowUTC();
      MqlDateTime utc;
      TimeToStruct(nowUtc, utc);
      refTs = nowUtc + (datetime)(PragueUtcOffsetHours(utc) * 3600);
   }
   else
   {
      // Legacy mode 2: UTC midnight (tester-safe)
      refTs = g_orchGuard.NowUTC();
   }
   MqlDateTime dt;
   TimeToStruct(refTs, dt);
   return dt.year * 1000 + dt.day_of_year;
}

bool IsAccountSynced(const double bal, const double eq)
{
   if(!MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
      return false;
   return (bal > 0.0 && eq > 0.0);
}

void WriteHeartbeatJson(const datetime nowUtc, const double bal, const double eq,
                        const double dailyDdPct, const double staticDdPct, const double profitPct,
                        const string regime, const double riskMult,
                        const bool effectiveKill, const bool manualHalt,
                        const int openCount, const int orphanCount)
{
   if(MQLInfoInteger(MQL_TESTER) || (nowUtc - g_lastHbWrite) < InpHeartbeatSec)
      return;
   g_lastHbWrite = nowUtc;
   bool termConnected = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);
   long quoteTs = (long)SymbolInfoInteger(_Symbol, SYMBOL_TIME);
   long acctLogin = CNaqexPropGuard::CurrentAccountLogin();
   int fh = FileOpen(InpHeartbeatFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh != INVALID_HANDLE)
   {
      string js = StringFormat(
         "{\"utc_ts\":%I64d,\"account_login\":%I64d,\"terminal_connected\":%s,\"quote_ts\":%I64d,"
         "\"balance\":%.2f,\"equity\":%.2f,\"day_anchor_eq\":%.2f,\"day_anchor_bal\":%.2f,"
         "\"daily_dd_pct\":%.3f,\"static_dd_pct\":%.3f,\"profit_pct\":%.3f,\"reset_mode\":%d,"
         "\"regime\":\"%s\",\"risk_mult\":%.3f,"
         "\"kill_switch\":%s,\"manual_halt\":%s,\"open_positions\":%d,\"orphan_no_sl\":%d,\"dry_run\":%s}\n",
         (long)nowUtc, acctLogin, termConnected ? "true" : "false", quoteTs,
         bal, eq, g_dayAnchorEq, g_dayAnchorBal,
         dailyDdPct, staticDdPct, profitPct, InpDailyResetMode,
         regime, riskMult,
         effectiveKill ? "true" : "false", manualHalt ? "true" : "false",
         openCount, orphanCount,
         (InpDryRunLogOnly || InpGuardDryRunLogOnly) ? "true" : "false"
      );
      FileWriteString(fh, js);
      FileClose(fh);
   }
}

void RestoreOrInitDayAnchor()
{
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsAccountSynced(bal, eq))
      return;

   int today = CurrentResetDayKey();
   string kDay  = CNaqexPropGuard::AcctDayKeyName();
   string kEq   = CNaqexPropGuard::AcctDayEqKeyName();
   string kBal  = CNaqexPropGuard::AcctDayBalKeyName();
   string kAuto = CNaqexPropGuard::AcctAutoKillKey();
   if(GlobalVariableCheck(kDay) && (int)GlobalVariableGet(kDay) == today && GlobalVariableCheck(kEq) && GlobalVariableGet(kEq) > 0.0)
   {
      g_dayKey         = today;
      g_dayAnchorEq    = GlobalVariableGet(kEq);
      g_dayAnchorBal   = (GlobalVariableCheck(kBal) && GlobalVariableGet(kBal) > 0.0) ? GlobalVariableGet(kBal) : g_dayAnchorEq;
      g_autoKillActive = GlobalVariableCheck(kAuto) && (GlobalVariableGet(kAuto) >= 1.0);
   }
   else
   {
      g_dayKey         = today;
      g_dayAnchorBal   = bal;
      g_dayAnchorEq    = (InpDailyResetMode == 1) ? bal : MathMax(bal, eq);
      g_autoKillActive = false;
      GlobalVariableSet(kDay, (double)g_dayKey);
      GlobalVariableSet(kEq, g_dayAnchorEq);
      GlobalVariableSet(kBal, g_dayAnchorBal);
      GlobalVariableSet(kAuto, 0.0);
      GlobalVariableSet(CNaqexPropGuard::GlobalKillKey(), 0.0);
   }
}

void FlattenAllNaqexPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      g_orchGuard.ClosePositionChecked(g_orchTrade, ticket, reason, InpDryRunLogOnly);
   }
}

void EvaluatePortfolioState()
{
   datetime nowUtc = g_orchGuard.NowUTC();
   GlobalVariableSet(CNaqexPropGuard::OrchTsKey(), (double)nowUtc);

   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);

   // Fail-closed pause while broker disconnected or account balance/equity not yet synced:
   // NEVER compute fake 100% static DD or latch sticky g_autoKillActive on startup before login!
   if(!IsAccountSynced(bal, eq))
   {
      GlobalVariableSet(CNaqexPropGuard::GlobalKillKey(), 1.0);
      WriteHeartbeatJson(nowUtc, bal, eq, 0.0, 0.0, 0.0, "DISCONNECTED", 0.0, true, false, 0, 0);
      return;
   }

   int today = CurrentResetDayKey();
   if(today != g_dayKey || g_dayAnchorEq <= 0.0)
      RestoreOrInitDayAnchor();

   // Exact firm-specific daily drawdown formula:
   //   Mode 1 (FTMO Prague): (Midnight Prague Balance - Equity) / InitialBalance
   //   Mode 0 (The5ers Server): (Max(Bal, Eq) at 00:00 Server - Equity) / Max(Bal, Eq)
   double dailyDdPct = 0.0;
   if(InpDailyResetMode == 1)
      dailyDdPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
   else
      dailyDdPct = (g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0;

   double staticDdPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double profitPct   = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;

   // Compute AMBER / RED / PROFIT_LOCK dynamic risk multiplier
   double riskMult = InpBasePhaseMult;
   string regime   = "NORMAL";
   if(staticDdPct >= InpRedDdPct)
   {
      riskMult = MathMin(riskMult, InpRedMult);
      regime   = "RED_BRAKE";
   }
   else if(staticDdPct >= InpAmberDdPct)
   {
      riskMult = MathMin(riskMult, InpAmberMult);
      regime   = "AMBER_BRAKE";
   }
   else if(InpProfitLockPct > 0.0 && profitPct >= InpProfitLockPct && staticDdPct < InpAmberDdPct)
   {
      riskMult = MathMin(riskMult, InpProfitLockMult);
      regime   = "PROFIT_LOCK";
   }
   GlobalVariableSet(CNaqexPropGuard::GlobalMultKey(), riskMult);

   // Separate sticky auto-kill (latched until daily reset) vs reversible manual halt flag
   bool manualHalt = false;
   bool manualFlatten = false;
   if(InpAllowManualHaltFile && !MQLInfoInteger(MQL_TESTER) && FileIsExist(InpManualHaltFile))
   {
      int mf = FileOpen(InpManualHaltFile, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(mf != INVALID_HANDLE)
      {
         string payload = FileReadString(mf);
         FileClose(mf);
         manualHalt = true;
         if(StringFind(payload, "FLATTEN_ALL") >= 0)
            manualFlatten = true;
      }
   }

   bool autoKillNow = (dailyDdPct >= InpKillDailyDdPct) || (staticDdPct >= InpKillStaticDdPct);
   if(autoKillNow)
   {
      g_autoKillActive = true;
      GlobalVariableSet(CNaqexPropGuard::AcctAutoKillKey(), 1.0);
   }

   bool effectiveKill = g_autoKillActive || manualHalt;
   GlobalVariableSet(CNaqexPropGuard::GlobalKillKey(), effectiveKill ? 1.0 : 0.0);

   if(manualHalt)
      regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";
   if(g_autoKillActive)
      FlattenAllNaqexPositions((dailyDdPct >= InpKillDailyDdPct) ? "ORCH_KILL_DAILY_DD" : "ORCH_KILL_STATIC_DD");
   else if(manualFlatten)
      FlattenAllNaqexPositions("MANUAL_COVERED_FLATTEN");

   // Count open Naqex positions & detect orphans (missing SL)
   int openCount = 0;
   int orphanCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      openCount++;
      double sl = PositionGetDouble(POSITION_SL);
      if(sl <= 0.0)
      {
         orphanCount++;
         PrintFormat("[ORCH-ALERT] ORPHAN NO-SL position detected ticket=%I64u magic=%I64d", ticket, pm);
      }
   }

   // Write structured JSON heartbeat (includes broker connectivity, quote_ts, login & persistent kill_switch)
   WriteHeartbeatJson(nowUtc, bal, eq, dailyDdPct, staticDdPct, profitPct,
                      regime, riskMult, effectiveKill, manualHalt, openCount, orphanCount);
}

int OnInit()
{
   g_orchGuard.Init(g_orchTrade, _Symbol, InpMagicRangeMin, InpKillDailyDdPct);
   RestoreOrInitDayAnchor();
   GlobalVariableSet(CNaqexPropGuard::GlobalMultKey(), InpBasePhaseMult);
   GlobalVariableSet(CNaqexPropGuard::OrchTsKey(), (double)g_orchGuard.NowUTC());
   PrintFormat("[ORCH-INIT] v2.01 login=%I64d connected=%s reset_mode=%d dry_run=%s",
               CNaqexPropGuard::CurrentAccountLogin(),
               (TerminalInfoInteger(TERMINAL_CONNECTED) != 0) ? "true" : "false",
               InpDailyResetMode,
               (InpDryRunLogOnly || InpGuardDryRunLogOnly) ? "true" : "false");
   EventSetTimer(5);
   EvaluatePortfolioState();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   EvaluatePortfolioState();
}

void OnTick()
{
   EvaluatePortfolioState();
}
