//+------------------------------------------------------------------+
//| Naqex_Master_Prop7E.mq5 (v1.00 — Single Multi-Symbol Authority)  |
//| Round-3 Approved Architecture:                                   |
//|   - ONE Execution Authority per MT5 account (zero GV CAS races)  |
//|   - 7 Fixed Core Engines (E1..E7) across all phases + S6 shadow  |
//|   - In-memory atomic Per-Symbol + Directional Factor Cluster     |
//|     (USD / JPY / US100) + Total Account Open Risk Allocator      |
//|   - In-flight pending/unknown order ledger reconciled via        |
//|     OnTradeTransaction + HistoryDeals + PositionsTotal           |
//|   - Dual sizing benchmark: 0=STATIC_LOCK | 1=BARRIER_HEADROOM    |
//|   - Fail-closed defaults: DryRun=true, ShadowCompareMode=true    |
//+------------------------------------------------------------------+
#property strict
#property version     "1.00"
#property tester_file "naqex_red_news_utc.csv"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"
#include "Include/Naqex_Signals_7E.mqh"

//--- Safety & Mode Inputs (FAIL-CLOSED DEFAULTS)
input bool   InpDryRunLogOnly          = true;       // SAFETY: true = log only, NO live OrderSend
input bool   InpShadowCompareMode      = true;       // true = shadow-only compare alongside legacy EAs (no orders, separate heartbeat)
input bool   InpEnableS6Shadow         = true;       // Log S6_FX_USD_BSK intents shadow-only for 8E baseline comparison
input bool   InpWritePrimaryHeartbeat  = false;      // true ONLY when replacing legacy Orchestrator as sole authority

//--- Contract & Phase Inputs (Single-Spec FTMO Swing 10K / The5ers 5K)
input string InpContractSku            = "FTMO_SWING_10K_P1";
input double InpInitialBalanceUSD      = 10000.0;
input double InpTargetProfitPct        = 10.0;       // Phase profit target % (10% FTMO P1 / 8% The5ers P1 / 5% P2 / 0 Funded)
input double InpHardDailyDdPct         = 5.00;       // Firm hard daily DD %
input double InpHardStaticDdPct        = 10.00;      // Firm hard static DD %
input int    InpDailyResetMode         = 1;          // 0=Server Midnight (The5ers), 1=Europe/Prague DST (FTMO), 2=UTC
input int    InpSizingMode             = 0;          // 0=STATIC_PHASE_LOCK (frozen benchmark), 1=BARRIER_HEADROOM_MIN
input double InpBasePhaseMult          = 1.00;       // Phase risk mult (1.00 Funded / 2.00 P2 / 4.00 P1)
input double InpProfitLockPct          = 0.00;       // Profit % to step down to InpProfitLockMult (0 = disabled)
input double InpProfitLockMult         = 2.01;
input double InpAmberDdPct             = 3.50;
input double InpAmberMult              = 0.65;
input double InpRedDdPct               = 6.00;
input double InpRedMult                = 0.40;
input double InpKillDailyDdPct         = 3.00;
input double InpKillStaticDdPct        = 7.50;

//--- Per-Symbol + Directional Factor Cluster Caps (Astra R2-07 / Round-3)
input double InpMaxSymbolRiskPct       = 1.00;       // Per-symbol concurrent SL risk % cap
input double InpMaxUsdClusterPct       = 1.50;       // Max same-direction USD factor SL risk %
input double InpMaxJpyClusterPct       = 1.25;       // Max same-direction JPY factor SL risk % (USDJPY + EURJPY)
input double InpMaxIdxClusterPct       = 1.00;       // Max US100/US500 index cluster SL risk %
input double InpMaxAccountOpenRiskPct  = 2.00;       // Max total simultaneous open SL risk % across account

//--- Multi-Symbol Broker Aliases & Telemetry
input string InpSymUSDJPY              = "USDJPY";
input string InpSymGBPUSD              = "GBPUSD";
input string InpSymEURJPY              = "EURJPY";
input string InpSymUS100               = "US100.cash";
input string InpSymUS500               = "US500.cash";
input string InpSymEURUSD              = "EURUSD";
input string InpSymAUDUSD              = "AUDUSD";
input string InpSymUSDCAD              = "USDCAD";
input double InpMaxIndexSpreadPoints   = 450.0;      // Max spread (pts) for US100/US500 indices (FTMO normal ~195 pts)
input double InpMaxEurJpySpreadPoints  = 45.0;       // Max spread (pts) for EURJPY cross (matches E6 preset)
input int    InpMaxBreakoutTickLagMs   = 5000;
input int    InpHeartbeatSec           = 15;
input string InpHeartbeatFile          = "naqex_master_heartbeat.json";
input string InpShadowCsvFile          = "naqex_master_shadow.csv";
input bool   InpAllowManualHaltFile    = false;
input string InpManualHaltFile         = "naqex_manual_halt.flag";
input long   InpMagicRangeMin          = 20261120;
input long   InpMagicRangeMax          = 20261199;

//--- In-flight order ledger (atomic single-process memory, zero GV CAS races!)
#define NAQEX_MAX_INFLIGHT 32
struct NaqexInFlightOrder
{
   bool     active;
   string   intent_id;
   long     magic;
   string   symbol;
   bool     is_buy;
   double   est_risk_pct;
   ulong    order_ticket;
   datetime sent_utc;
   bool     unknown_state;
};

CTrade           g_trade;
CNaqexPropGuard  g_guard;
CNaqexSignals7E  g_signals;
NaqexInFlightOrder g_inFlight[NAQEX_MAX_INFLIGHT];

int      g_dayKey            = -1;
double   g_dayAnchorEq       = 0.0;
double   g_dayAnchorBal      = 0.0;
bool     g_autoKillActive    = false;
bool     g_anchorUnrecovered = false;
datetime g_lastHbWrite       = 0;
long     g_lastTickLagMs     = 0;
long     g_maxTickLagMs      = 0;

int LastSundayOfMonthM(const int year, const int month)
{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 31;
   TimeToStruct(StructToTime(d), d);
   return 31 - d.day_of_week;
}

int PragueUtcOffsetHoursM(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 10) return 1;
   if(utc.mon > 3 && utc.mon < 10) return 2;
   int ls = LastSundayOfMonthM(utc.year, utc.mon);
   if(utc.mon == 3) return (utc.day > ls || (utc.day == ls && utc.hour >= 1)) ? 2 : 1;
   return (utc.day < ls || (utc.day == ls && utc.hour < 1)) ? 2 : 1;
}

int CurrentResetDayKeyM()
{
   datetime refTs = 0;
   if(InpDailyResetMode == 0)
      refTs = TimeCurrent();
   else if(InpDailyResetMode == 1)
   {
      datetime nowUtc = g_guard.NowUTC();
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      refTs = nowUtc + (datetime)(PragueUtcOffsetHoursM(utc) * 3600);
   }
   else
      refTs = g_guard.NowUTC();
   MqlDateTime dt; TimeToStruct(refTs, dt);
   return dt.year * 1000 + dt.day_of_year;
}

datetime CurrentResetStartServerTimeM()
{
   datetime srvNow = TimeCurrent();
   if(InpDailyResetMode == 0) return srvNow - (srvNow % 86400);
   datetime nowUtc = g_guard.NowUTC();
   long srvMinusUtc = (long)srvNow - (long)nowUtc;
   if(InpDailyResetMode == 1)
   {
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      int prgOff = PragueUtcOffsetHoursM(utc) * 3600;
      datetime prgNow = nowUtc + (datetime)prgOff;
      datetime prgMidUtc = (prgNow - (prgNow % 86400)) - (datetime)prgOff;
      return prgMidUtc + (datetime)srvMinusUtc;
   }
   return (nowUtc - (nowUtc % 86400)) + (datetime)srvMinusUtc;
}

bool IsAccountSyncedM(const double bal, const double eq)
{
   if(!MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
      return false;
   return (bal > 0.0 && eq > 0.0);
}

void RestoreOrInitDayAnchorM()
{
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsAccountSyncedM(bal, eq)) return;
   int today = CurrentResetDayKeyM();
   if(today == g_dayKey && g_dayAnchorEq > 0.0) return;

   double reconstructedBal = bal;
   g_anchorUnrecovered = false;
   if(!MQLInfoInteger(MQL_TESTER))
   {
      datetime resetStart = CurrentResetStartServerTimeM();
      datetime srvNow = TimeCurrent();
      if(srvNow >= resetStart && HistorySelect(resetStart, srvNow + 60))
      {
         double todayRealized = 0.0;
         int nDeals = HistoryDealsTotal();
         for(int i = 0; i < nDeals; i++)
         {
            ulong dtk = HistoryDealGetTicket(i);
            if(dtk == 0) continue;
            long dtype = HistoryDealGetInteger(dtk, DEAL_TYPE);
            if(dtype == DEAL_TYPE_BUY || dtype == DEAL_TYPE_SELL)
               todayRealized += HistoryDealGetDouble(dtk, DEAL_PROFIT)
                              + HistoryDealGetDouble(dtk, DEAL_SWAP)
                              + HistoryDealGetDouble(dtk, DEAL_COMMISSION);
         }
         reconstructedBal = bal - todayRealized;
         if(reconstructedBal <= 0.0) reconstructedBal = bal;
      }
      else if(srvNow - resetStart > 600)
      {
         g_anchorUnrecovered = true;
      }
   }
   g_dayKey         = today;
   g_dayAnchorBal   = reconstructedBal;
   g_dayAnchorEq    = (InpDailyResetMode == 1) ? reconstructedBal : MathMax(reconstructedBal, eq);
   g_autoKillActive = false;
}

int CountActiveInFlight()
{
   int n = 0;
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active) n++;
   return n;
}

void ReconcileInFlightOrders(const datetime nowUtc)
{
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
      // Check if position already materialized on broker (match order_ticket or magic+symbol)
      bool posFound = false;
      for(int p = PositionsTotal() - 1; p >= 0; p--)
      {
         ulong ptk = PositionGetTicket(p);
         if(ptk == 0) continue;
         if((g_inFlight[i].order_ticket > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == g_inFlight[i].order_ticket) ||
            (PositionGetInteger(POSITION_MAGIC) == g_inFlight[i].magic && PositionGetString(POSITION_SYMBOL) == g_inFlight[i].symbol))
         {
            posFound = true;
            break;
         }
      }
      if(posFound)
      {
         g_inFlight[i].active = false;
         continue;
      }
      // If still in unknown_state, keep locked for 120s unless broker deal history confirms cancellation/fill
      if((long)nowUtc - (long)g_inFlight[i].sent_utc > 120)
         g_inFlight[i].active = false;
   }
}

void RegisterInFlight(const NaqexSignalIntent &it, const double estRiskPct, const ulong ordTicket, const bool isUnknown)
{
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active)
      {
         g_inFlight[i].active        = true;
         g_inFlight[i].intent_id     = it.intent_id;
         g_inFlight[i].magic         = it.magic;
         g_inFlight[i].symbol        = it.symbol;
         g_inFlight[i].is_buy        = it.is_buy;
         g_inFlight[i].est_risk_pct  = estRiskPct;
         g_inFlight[i].order_ticket  = ordTicket;
         g_inFlight[i].sent_utc      = it.signal_utc;
         g_inFlight[i].unknown_state = isUnknown;
         return;
      }
   }
}

bool HasOpenOrInFlightForMagic(const long magic)
{
   for(int p = PositionsTotal() - 1; p >= 0; p--)
      if(PositionGetTicket(p) > 0 && PositionGetInteger(POSITION_MAGIC) == magic)
         return true;
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].magic == magic)
         return true;
   return false;
}

double GetInFlightSymbolRisk(const string sym)
{
   double s = 0.0;
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].symbol == sym)
         s += g_inFlight[i].est_risk_pct;
   return s;
}

void GetInFlightFactorRisks(double &uL, double &uS, double &jL, double &jS, double &iL, double &iS, double &tot)
{
   uL = 0.0; uS = 0.0; jL = 0.0; jS = 0.0; iL = 0.0; iS = 0.0; tot = 0.0;
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
      tot += g_inFlight[i].est_risk_pct;
      CNaqexPropGuard::AccumulateDirectionalFactor(g_inFlight[i].symbol, g_inFlight[i].is_buy, g_inFlight[i].est_risk_pct,
                                                   uL, uS, jL, jS, iL, iS);
   }
}

void LogMasterShadowRow(const NaqexSignalIntent &it, const string evType, const double riskPct,
                        const double lots, const string reason)
{
   if(MQLInfoInteger(MQL_TESTER)) return;
   bool needHeader = !FileIsExist(InpShadowCsvFile);
   int fh = INVALID_HANDLE;
   for(int a = 0; a < 6; a++)
   {
      fh = FileOpen(InpShadowCsvFile, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
      if(fh != INVALID_HANDLE) break;
      Sleep(15);
   }
   if(fh == INVALID_HANDLE) return;
   FileSeek(fh, 0, SEEK_END);
   if(needHeader)
      FileWrite(fh, "utc_ts", "account_login", "intent_id", "engine_id", "magic", "symbol", "deal_side",
                "event_type", "signal_price", "sl_price", "risk_pct", "lots", "tick_lag_ms", "shadow_only", "reason");
   FileWrite(fh, (long)it.signal_utc, CNaqexPropGuard::CurrentAccountLogin(), it.intent_id, it.engine_id,
             it.magic, it.symbol, (it.is_buy ? "BUY" : "SELL"), evType,
             DoubleToString(it.signal_price, 6), DoubleToString(it.sl_price, 6),
             DoubleToString(riskPct, 3), DoubleToString(lots, 2), it.tick_lag_ms,
             it.shadow_only ? "true" : "false", reason);
   FileClose(fh);
}

double ComputePhaseRiskMultiplier(const double dailyDdPct, const double staticDdPct, const double profitPct, string &outRegime)
{
   double mult = InpBasePhaseMult;
   outRegime = "NORMAL";
   if(staticDdPct >= InpRedDdPct)
   {
      mult = MathMin(mult, InpRedMult);
      outRegime = "RED_BRAKE";
   }
   else if(staticDdPct >= InpAmberDdPct)
   {
      mult = MathMin(mult, InpAmberMult);
      outRegime = "AMBER_BRAKE";
   }
   else if(InpProfitLockPct > 0.0 && profitPct >= InpProfitLockPct)
   {
      mult = MathMin(mult, InpProfitLockMult);
      outRegime = "PROFIT_LOCK";
   }

   // SizingMode 1: BARRIER_HEADROOM_MIN (Astra Round-3 state-dependent control — ONLY tapers, NEVER boosts!)
   if(InpSizingMode == 1)
   {
      double dailyHeadroom  = MathMax(0.0, InpKillDailyDdPct - dailyDdPct);
      double staticHeadroom = MathMax(0.0, InpKillStaticDdPct - staticDdPct);
      // Scale smoothly down if headroom tightens below 2.0% daily or 3.5% static
      double ddScale = 1.0;
      if(dailyHeadroom < 2.0)  ddScale = MathMin(ddScale, MathMax(0.25, dailyHeadroom / 2.0));
      if(staticHeadroom < 3.5) ddScale = MathMin(ddScale, MathMax(0.25, staticHeadroom / 3.5));
      // Target-proximity taper when within last 35% of phase profit target
      if(InpTargetProfitPct > 0.0 && profitPct > 0.0)
      {
         double remToTarget = MathMax(0.0, InpTargetProfitPct - profitPct);
         double fracRem = remToTarget / InpTargetProfitPct;
         if(fracRem < 0.35)
            ddScale = MathMin(ddScale, MathMax(0.35, fracRem / 0.35));
      }
      mult = MathMin(mult, InpBasePhaseMult * ddScale);
      if(ddScale < 0.99 && outRegime == "NORMAL")
         outRegime = "BARRIER_TAPER";
   }
   return MathMax(0.0, mult);
}

void WriteMasterHeartbeat(const datetime nowUtc, const double bal, const double eq,
                          const double dailyDdPct, const double staticDdPct, const double profitPct,
                          const string regime, const double riskMult,
                          const bool effectiveKill, const bool manualHalt,
                          const string posState, const int openCount, const int totalAcctPos,
                          const int pendingCount, const int inFlightCount, const int orphanCount,
                          const string anchorState)
{
   if(MQLInfoInteger(MQL_TESTER) || (nowUtc - g_lastHbWrite) < InpHeartbeatSec) return;
   g_lastHbWrite = nowUtc;
   string fname = InpWritePrimaryHeartbeat ? "naqex_heartbeat.json" : InpHeartbeatFile;
   bool termConn = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);
   long quoteTs = (long)SymbolInfoInteger(g_signals.SymbolAt(SYM_USDJPY), SYMBOL_TIME);
   long login = CNaqexPropGuard::CurrentAccountLogin();
   string srv = AccountInfoString(ACCOUNT_SERVER);
   StringReplace(srv, "\"", "");

   double uL = 0.0, uS = 0.0, jL = 0.0, jS = 0.0, iL = 0.0, iS = 0.0;
   if(posState == "CONFIRMED")
      g_guard.ComputeAccountFactorRisk(uL, uS, jL, jS, iL, iS);

   int fh = FileOpen(fname, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh != INVALID_HANDLE)
   {
      string js = StringFormat(
         "{\"utc_ts\":%I64d,\"account_login\":%I64d,\"account_server\":\"%s\",\"build_version\":\"master-1.00\","
         "\"sku\":\"%s\",\"sizing_mode\":%d,\"shadow_compare\":%s,\"terminal_connected\":%s,\"quote_ts\":%I64d,"
         "\"positions_state\":\"%s\",\"anchor_state\":\"%s\","
         "\"balance\":%.2f,\"equity\":%.2f,\"day_anchor_eq\":%.2f,\"day_anchor_bal\":%.2f,"
         "\"daily_dd_pct\":%.3f,\"static_dd_pct\":%.3f,\"profit_pct\":%.3f,\"reset_mode\":%d,"
         "\"regime\":\"%s\",\"risk_mult\":%.3f,"
         "\"kill_switch\":%s,\"manual_halt\":%s,\"manual_halt_ack\":%s,"
         "\"open_positions\":%d,\"total_account_positions\":%d,\"pending_orders\":%d,\"in_flight_orders\":%d,"
         "\"orphan_no_sl\":%d,\"factor_usd_max_pct\":%.3f,\"factor_jpy_max_pct\":%.3f,\"factor_idx_max_pct\":%.3f,"
         "\"last_tick_lag_ms\":%I64d,\"max_tick_lag_ms\":%I64d,\"dry_run\":%s}\n",
         (long)nowUtc, login, srv, InpContractSku, InpSizingMode,
         InpShadowCompareMode ? "true" : "false", termConn ? "true" : "false", quoteTs,
         posState, anchorState,
         bal, eq, g_dayAnchorEq, g_dayAnchorBal,
         dailyDdPct, staticDdPct, profitPct, InpDailyResetMode,
         regime, riskMult,
         effectiveKill ? "true" : "false", manualHalt ? "true" : "false", manualHalt ? "true" : "false",
         openCount, totalAcctPos, pendingCount, inFlightCount,
         orphanCount, MathMax(uL, uS), MathMax(jL, jS), MathMax(iL, iS),
         g_lastTickLagMs, g_maxTickLagMs,
         (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly) ? "true" : "false"
      );
      FileWriteString(fh, js);
      FileClose(fh);
   }
}

void ClosePositionsByReason(const datetime nowUtc, const bool flattenAll, const string globalReason)
{
   bool isDry = (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      string psym = PositionGetString(POSITION_SYMBOL);
      string reason = "";
      if(flattenAll)
         reason = globalReason;
      else if(g_signals.ShouldClockFlattenMagic(pm, nowUtc, reason))
         {}
      else if(g_guard.IsNearBrokerSessionCloseFor(psym))
         reason = "HARD_FLAT_SESSION_CLOSE_SWAP0";
      else if(g_guard.IsInRedNewsPreFlattenWindowFor(psym))
         reason = "NEWS_PRE_FLATTEN";
      if(reason != "")
      {
         g_trade.SetExpertMagicNumber(pm);
         g_guard.ClosePositionChecked(g_trade, tk, reason, isDry);
      }
   }
}

double MaxSpreadCapForSymbol(const string sym)
{
   string u = sym;
   StringToUpper(u);
   if(StringFind(u, "US100") >= 0 || StringFind(u, "NAS100") >= 0 ||
      StringFind(u, "NDX")   >= 0 || StringFind(u, "USTEC")  >= 0 ||
      StringFind(u, "US500") >= 0 || StringFind(u, "SPX")    >= 0)
      return InpMaxIndexSpreadPoints;
   if(StringFind(u, "EURJPY") >= 0)
      return InpMaxEurJpySpreadPoints;
   return InpGuardMaxSpreadPoints;
}

void ProcessIntentAtomically(const NaqexSignalIntent &it, const double riskMult)
{
   bool isShadowOrDry = (it.shadow_only || InpShadowCompareMode || InpDryRunLogOnly || InpGuardDryRunLogOnly);
   if(HasOpenOrInFlightForMagic(it.magic)) return;
   if(g_guard.IsInsideRedNewsWindowFor(it.symbol))
   {
      LogMasterShadowRow(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, "INSIDE_RED_NEWS_OR_EXPIRED_CALENDAR");
      return;
   }
   if(!g_guard.IsSpreadAndSessionSafeFor(it.symbol, MaxSpreadCapForSymbol(it.symbol)))
   {
      LogMasterShadowRow(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, "SPREAD_OR_ROLLOVER_GUARD");
      return;
   }

   double normSl = CNaqexPropGuard::NormalizePriceToTick(it.symbol, it.sl_price);
   double stopLoss = normSl;
   double slDist = MathAbs(it.signal_price - stopLoss);
   if(slDist <= 0.0 || stopLoss <= 0.0) return;
   double pt = SymbolInfoDouble(it.symbol, SYMBOL_POINT);
   long stopsLvl = SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(pt > 0.0 && stopsLvl > 0 && slDist < (double)stopsLvl * pt)
   {
      LogMasterShadowRow(it, "ORDER_BLOCKED_STOPS", 0.0, 0.0, "SL_BELOW_BROKER_STOPS_LEVEL");
      return;
   }

   // Atomic single-process risk allocation: min(requested, sym_headroom, factor_cluster_headroom)
   double reqRiskPct = it.base_risk_pct * riskMult;
   double usedSymPct = g_guard.GetOpenSymbolRiskPctFor(it.symbol) + GetInFlightSymbolRisk(it.symbol);
   double symHeadroom = (InpMaxSymbolRiskPct > 0.0) ? MathMax(0.0, InpMaxSymbolRiskPct - usedSymPct) : 999.0;

   double fUL, fUS, fJL, fJS, fIL, fIS, fTot;
   GetInFlightFactorRisks(fUL, fUS, fJL, fJS, fIL, fIS, fTot);
   double factorHeadroom = g_guard.ComputeFactorHeadroomPct(
      it.symbol, it.is_buy,
      InpMaxUsdClusterPct, InpMaxJpyClusterPct, InpMaxIdxClusterPct, InpMaxAccountOpenRiskPct,
      fUL, fUS, fJL, fJS, fIL, fIS, fTot
   );

   double allowedRiskPct = MathMin(reqRiskPct, MathMin(symHeadroom, factorHeadroom));
   if(allowedRiskPct <= 0.01)
   {
      string why = (factorHeadroom <= symHeadroom) ? "ORDER_BLOCKED_FACTOR" : "ORDER_BLOCKED_SYMCAP";
      LogMasterShadowRow(it, why, reqRiskPct, 0.0,
                         StringFormat("symRem=%.2f|facRem=%.2f", symHeadroom, factorHeadroom));
      return;
   }

   // Compute safe lots with 5% commission cushion + fail-closed OrderCalcMargin <= 85%
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickSize = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickVal <= 0.0) tickVal = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE);
   double volMin  = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN);
   double volMax  = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX);
   double volStep = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP);
   if(bal <= 0.0 || tickSize <= 0.0 || tickVal <= 0.0 || volStep <= 0.0) return;

   double lossPerLot = (slDist / tickSize) * tickVal;
   if(lossPerLot <= 0.0) return;
   double riskMoney = bal * (allowedRiskPct / 100.0) * 0.95;
   double lots = MathFloor((riskMoney / lossPerLot) / volStep) * volStep;
   if(lots < volMin) return;
   lots = MathMin(lots, volMax);

   ENUM_ORDER_TYPE ordType = it.is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double reqMargin = 0.0;
   if(freeMargin <= 0.0 || !OrderCalcMargin(ordType, it.symbol, lots, it.signal_price, reqMargin) || reqMargin < 0.0)
   {
      LogMasterShadowRow(it, "ORDER_BLOCKED_MARGIN", allowedRiskPct, 0.0, "FAIL_CLOSED_MARGIN_CHECK");
      return;
   }
   double maxAllowM = freeMargin * 0.85;
   if(reqMargin > maxAllowM && reqMargin > 0.0)
   {
      lots = MathFloor((lots * (maxAllowM / reqMargin)) / volStep) * volStep;
      if(lots < volMin) return;
      lots = MathMin(lots, volMax);
   }

   // Always record shadow intent in shadow/dry-run mode (ZERO OrderSend!)
   if(isShadowOrDry)
   {
      LogMasterShadowRow(it, it.shadow_only ? "SHADOW_INTENT" : "DRYRUN_SIGNAL", allowedRiskPct, lots, it.tag);
      g_signals.MarkEngineTraded(it.magic, it.session_day_key);
      return;
   }

   double actualRiskPct = (((slDist / tickSize) * tickVal * lots) / bal) * 100.0;
   g_trade.SetExpertMagicNumber(it.magic);
   CNaqexPropGuard::ConfigureFillingMode(g_trade, it.symbol);

   ulong t0 = GetMicrosecondCount();
   bool ok = it.is_buy ? g_trade.Buy(lots, it.symbol, it.signal_price, normSl, 0.0, it.tag)
                       : g_trade.Sell(lots, it.symbol, it.signal_price, normSl, 0.0, it.tag);
   double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
   uint ret = g_trade.ResultRetcode();
   string sideStr = it.is_buy ? "BUY" : "SELL";

   if(ret == TRADE_RETCODE_TIMEOUT || ret == TRADE_RETCODE_PLACED)
   {
      RegisterInFlight(it, actualRiskPct, g_trade.ResultOrder(), true);
      g_guard.LogExecAuditFor(it.symbol, sideStr, "FILL_UNRESOLVED", it.signal_price, -1.0, normSl, lots, latMs, ret,
                              StringFormat("%s|intent=%s|ord=%I64u|UNKNOWN_INFLIGHT", it.tag, it.intent_id, (ulong)g_trade.ResultOrder()));
      return;
   }
   if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
   {
      g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_REJECT", it.signal_price, g_trade.ResultPrice(), normSl, lots, latMs, ret,
                              StringFormat("%s|intent=%s|%s", it.tag, it.intent_id, g_trade.ResultRetcodeDescription()));
      return;
   }

   RegisterInFlight(it, actualRiskPct, g_trade.ResultOrder(), false);
   double execLots = (g_trade.ResultVolume() > 0.0) ? g_trade.ResultVolume() : lots;
   double fillPx = g_guard.ResolveExecutedFillPrice(g_trade, it.symbol, -1.0);
   g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_FILL", it.signal_price, fillPx, normSl, execLots, latMs, ret,
                           StringFormat("%s|intent=%s|deal=%I64u|ord=%I64u%s",
                                        it.tag, it.intent_id, (ulong)g_trade.ResultDeal(), (ulong)g_trade.ResultOrder(),
                                        (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : ""));
   g_signals.MarkEngineTraded(it.magic, it.session_day_key);
}

void RunMasterCycle()
{
   datetime nowUtc = g_guard.NowUTC();
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);

   if(!IsAccountSyncedM(bal, eq))
   {
      WriteMasterHeartbeat(nowUtc, bal, eq, 0.0, 0.0, 0.0, "DISCONNECTED", 0.0, true, false,
                           "UNKNOWN", -1, -1, -1, CountActiveInFlight(), -1, "UNSYNCED");
      return;
   }

   RestoreOrInitDayAnchorM();
   ReconcileInFlightOrders(nowUtc);

   long lag = g_signals.PollSymbolTicks();
   g_lastTickLagMs = lag;
   if(lag > g_maxTickLagMs) g_maxTickLagMs = lag;

   double dailyDdPct = (InpDailyResetMode == 1)
      ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
      : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
   double staticDdPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double profitPct   = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;

   string regime = "NORMAL";
   double riskMult = ComputePhaseRiskMultiplier(dailyDdPct, staticDdPct, profitPct, regime);

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
         if(StringFind(payload, "FLATTEN_ALL") >= 0) manualFlatten = true;
      }
   }

   if(dailyDdPct >= InpKillDailyDdPct || staticDdPct >= InpKillStaticDdPct)
      g_autoKillActive = true;
   bool effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
   if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
   if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";

   // Exits & risk protection ALWAYS execute before any new intent evaluation
   if(g_autoKillActive)
      ClosePositionsByReason(nowUtc, true, (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD");
   else if(manualFlatten)
      ClosePositionsByReason(nowUtc, true, "MASTER_MANUAL_FLATTEN");
   else
      ClosePositionsByReason(nowUtc, false, "");

   // Collect and allocate intents ONLY when healthy & unlocked
   if(!effectiveKill)
   {
      NaqexSignalIntent intents[NAQEX_MAX_INTENTS];
      int nIntents = g_signals.CollectIntents(nowUtc, intents);
      for(int i = 0; i < nIntents; i++)
         ProcessIntentAtomically(intents[i], riskMult);
   }

   int openNaqex = 0, orphanCnt = 0;
   int totalPos = PositionsTotal();
   int pendingCnt = OrdersTotal();
   for(int i = totalPos - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      openNaqex++;
      if(PositionGetDouble(POSITION_SL) <= 0.0) orphanCnt++;
   }

   WriteMasterHeartbeat(nowUtc, bal, eq, dailyDdPct, staticDdPct, profitPct,
                        regime, riskMult, effectiveKill, manualHalt,
                        "CONFIRMED", openNaqex, totalPos, pendingCnt, CountActiveInFlight(), orphanCnt,
                        g_anchorUnrecovered ? "UNRECOVERED_AFTER_GAP" : "SYNCED");
}

int OnInit()
{
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++) g_inFlight[i].active = false;
   if(!g_signals.Init(InpSymUSDJPY, InpSymGBPUSD, InpSymEURJPY, InpSymUS100, InpSymUS500,
                      InpSymEURUSD, InpSymAUDUSD, InpSymUSDCAD, InpMaxBreakoutTickLagMs, InpEnableS6Shadow))
      return INIT_FAILED;
   g_guard.Init(g_trade, g_signals.SymbolAt(SYM_USDJPY), InpMagicRangeMin, InpKillDailyDdPct);
   RestoreOrInitDayAnchorM();
   PrintFormat("[MASTER-7E-INIT] v1.00 sku=%s sizing=%d shadow=%s dry_run=%s login=%I64d",
               InpContractSku, InpSizingMode,
               InpShadowCompareMode ? "true" : "false",
               (InpDryRunLogOnly || InpGuardDryRunLogOnly) ? "true" : "false",
               CNaqexPropGuard::CurrentAccountLogin());
   EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1); // 1s live CopyTicksRange + reconciliation; 60s in Tester
   RunMasterCycle();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   g_signals.Deinit();
}

void OnTick()
{
   if(MQLInfoInteger(MQL_TESTER))
   {
      static datetime s_lastTesterSec = 0;
      datetime cur = TimeCurrent();
      if(cur == s_lastTesterSec) return;
      s_lastTesterSec = cur;
   }
   RunMasterCycle();
}

void OnTimer()
{
   RunMasterCycle();
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   // Lightweight handler (queue limit = 1024): clear confirmed/rejected in-flight slots promptly
   if(trans.order == 0) return;
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD ||
      (trans.type == TRADE_TRANSACTION_ORDER_DELETE && trans.order_state != ORDER_STATE_FILLED))
   {
      for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
      {
         if(g_inFlight[i].active && g_inFlight[i].order_ticket == trans.order)
         {
            g_inFlight[i].active = false;
            break;
         }
      }
   }
}
