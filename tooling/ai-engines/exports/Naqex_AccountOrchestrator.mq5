//+------------------------------------------------------------------+
//| Naqex_AccountOrchestrator.mq5                                    |
//| Account-Wide Risk Orchestrator, AMBER/RED Phase Brake,           |
//| Global Kill-Switch, Orphan Detector & JSON Heartbeat Writer      |
//| Attach to ONE chart on the MT5 terminal running the 8 Naqex EAs. |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade g_orchTrade;

input bool   InpDryRunLogOnly      = true;       // SAFETY: true = monitor & log only, NO live flatten
input double InpInitialBalanceUSD  = 10000.0;    // Account initial size (e.g., 10000 FTMO / 5000 The5ers)
input double InpBasePhaseMult      = 1.00;       // Phase base risk mult (1.00 Funded / 2.50 P1 Sprint)
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

int      g_dayKey       = -1;
double   g_dayAnchorEq  = 0.0;
datetime g_lastHbWrite  = 0;

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
      // FTMO: Europe/Prague midnight (CET/CEST)
      datetime nowUtc = TimeGMT();
      MqlDateTime utc;
      TimeToStruct(nowUtc, utc);
      refTs = nowUtc + (datetime)(PragueUtcOffsetHours(utc) * 3600);
   }
   else
   {
      // Legacy mode 2: UTC midnight
      refTs = TimeGMT();
   }
   MqlDateTime dt;
   TimeToStruct(refTs, dt);
   return dt.year * 1000 + dt.day_of_year;
}

void RestoreOrInitDayAnchor()
{
   int today = CurrentResetDayKey();
   if(GlobalVariableCheck("NQXG_ACCT_DAYKEY") && (int)GlobalVariableGet("NQXG_ACCT_DAYKEY") == today && GlobalVariableCheck("NQXG_ACCT_DAYEQ"))
   {
      g_dayKey = today;
      g_dayAnchorEq = GlobalVariableGet("NQXG_ACCT_DAYEQ");
   }
   else
   {
      g_dayKey = today;
      g_dayAnchorEq = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
      GlobalVariableSet("NQXG_ACCT_DAYKEY", (double)g_dayKey);
      GlobalVariableSet("NQXG_ACCT_DAYEQ", g_dayAnchorEq);
      GlobalVariableSet("NQXG_GLOBAL_KILLSWITCH", 0.0);
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
      string sym = PositionGetString(POSITION_SYMBOL);
      if(InpDryRunLogOnly || InpGuardDryRunLogOnly)
         PrintFormat("[ORCH-DRYRUN] Would flatten ticket=%I64u sym=%s magic=%I64d reason=%s", ticket, sym, pm, reason);
      else
      {
         CNaqexPropGuard::ConfigureFillingMode(g_orchTrade, sym);
         g_orchTrade.PositionClose(ticket);
      }
   }
}

void EvaluatePortfolioState()
{
   int today = CurrentResetDayKey();
   if(today != g_dayKey)
      RestoreOrInitDayAnchor();

   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double dailyDdPct  = (g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0;
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
   GlobalVariableSet("NQXG_GLOBAL_RISK_MULT", riskMult);

   // Global Kill-Switch check (automatic DD limits + optional manual covered-button flag)
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

   bool killNow = (dailyDdPct >= InpKillDailyDdPct) || (staticDdPct >= InpKillStaticDdPct) || manualHalt;
   if(manualHalt)
      regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";
   if(killNow)
   {
      GlobalVariableSet("NQXG_GLOBAL_KILLSWITCH", 1.0);
      if(!manualHalt || manualFlatten)
         FlattenAllNaqexPositions(manualFlatten ? "MANUAL_COVERED_FLATTEN" : (dailyDdPct >= InpKillDailyDdPct ? "ORCH_KILL_DAILY_DD" : "ORCH_KILL_STATIC_DD"));
   }

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

   // Write structured JSON heartbeat for Python ops_monitor & Telegram alert bridge
   datetime nowUtc = TimeGMT();
   if(!MQLInfoInteger(MQL_TESTER) && (nowUtc - g_lastHbWrite) >= InpHeartbeatSec)
   {
      g_lastHbWrite = nowUtc;
      int fh = FileOpen(InpHeartbeatFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
      if(fh != INVALID_HANDLE)
      {
         string js = StringFormat(
            "{\"utc_ts\":%I64d,\"balance\":%.2f,\"equity\":%.2f,\"day_anchor_eq\":%.2f,"
            "\"daily_dd_pct\":%.3f,\"static_dd_pct\":%.3f,\"profit_pct\":%.3f,\"reset_mode\":%d,"
            "\"regime\":\"%s\",\"risk_mult\":%.3f,"
            "\"kill_switch\":%s,\"open_positions\":%d,\"orphan_no_sl\":%d,\"dry_run\":%s}\n",
            (long)nowUtc, bal, eq, g_dayAnchorEq, dailyDdPct, staticDdPct, profitPct, InpDailyResetMode,
            regime, riskMult,
            killNow ? "true" : "false", openCount, orphanCount,
            (InpDryRunLogOnly || InpGuardDryRunLogOnly) ? "true" : "false"
         );
         FileWriteString(fh, js);
         FileClose(fh);
      }
   }
}

int OnInit()
{
   RestoreOrInitDayAnchor();
   GlobalVariableSet("NQXG_GLOBAL_RISK_MULT", InpBasePhaseMult);
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
