//+------------------------------------------------------------------+
//| Naqex_Master_Prop7E.mq5 (v1.01 — Single Multi-Symbol Authority)  |
//| Round-3 Approved Architecture + v1.01 Hardening (V101-01..07):   |
//|   - ONE Execution Authority per MT5 account (zero GV CAS races)  |
//|   - 7 Fixed Core Engines (E1..E7) across all phases + S6 shadow  |
//|   - Real per-engine magic + tk/pos TCA audit & restart hydration |
//|   - TimeTradeServer() + exact EU Prague DST midnight offset      |
//|   - 23-date NYSE calendar + ±135s hard-ban + Sunday gap flatten  |
//|   - Pending OrdersTotal() cancel + live-calibrated deviation pts |
//|   - REL+HEADROOM relative AMBER/RED brake + dailyHeadroom taper  |
//|   - Fail-closed defaults: DryRun=true, ShadowCompareMode=true    |
//+------------------------------------------------------------------+
#property strict
#property version     "1.01"
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
input int    InpMaxSlippagePointsFx    = 35;         // V101-06 SetDeviationInPoints for FX pairs (pts)
input int    InpMaxSlippagePointsIdx   = 450;        // V101-06 SetDeviationInPoints for US100/US500 (live-calibrated >= +370pt)
input int    InpMaxBreakoutTickLagMs   = 5000;
input int    InpHeartbeatSec           = 15;
input string InpHeartbeatFile          = "naqex_master_heartbeat.json";
input string InpShadowCsvFile          = "naqex_master_shadow.csv";
input bool   InpTesterEmitDecisionLog  = false;      // Opt-in Tester-only pre-decision audit CSV (0 behavior change)
input string InpTesterDecisionLogFile  = "naqex_tester_decisions.csv";
input int    InpProfitLockBasisMode      = 0;        // 0=v1.01 Equity ProfitLock (frozen control), 1=v1.02-A Realized Balance ProfitLock + MathMin(DD,PL)
input int    InpOpportunityLifecycleMode = 0;        // 0=v1.01 Per-Tick Intent (frozen control), 1=v1.02-B Stable opportunity_id + Setup-Validity Expiry + L653 Transition Log
input int    InpPostCloseRefreshMode     = 0;        // 0=v1.01/Step3 Cycle-Start Risk Snapshot (frozen control), 1=Q2 Refresh State After Confirmed Close(s) Before CollectIntents
input bool   InpAllowManualHaltFile      = false;
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
   datetime session_day_key;
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
datetime g_lastAnchorRetry   = 0;
datetime g_lastHydrateRetry  = 0;
datetime g_lastHbWrite       = 0;
long     g_lastTickLagMs     = 0;
long     g_maxTickLagMs      = 0;
NaqexPendingCloseEntry g_pendingCloses[NAQEX_MAX_PENDING_CLOSES];

//--- Opt-in Tester pre-decision observability state (read-only mirror, zero trading side effects)
int      g_testerLogHandle   = INVALID_HANDLE;
long     g_testerLogSeq      = 0;
double   g_curDailyDdPct     = 0.0;
double   g_curStaticDdPct    = 0.0;
double   g_curProfitPct      = 0.0;
string   g_curRegime         = "NORMAL";
double   g_curUnTaperedMult  = 1.0;
double   g_curDailyHeadroom  = 99.0;
double   g_curDailyScale     = 1.0;
double   g_curRiskMult       = 1.0;
string   g_prevLogRegime     = "";
double   g_prevLogMult       = -1.0;

void OpenTesterDecisionLog()
{
   g_testerLogHandle = INVALID_HANDLE;
   g_testerLogSeq    = 0;
   g_prevLogRegime   = "";
   g_prevLogMult     = -1.0;
   if(!MQLInfoInteger(MQL_TESTER) || !InpTesterEmitDecisionLog) return;
   g_testerLogHandle = FileOpen(InpTesterDecisionLogFile, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(g_testerLogHandle != INVALID_HANDLE)
   {
      FileWriteString(
         g_testerLogHandle,
         "seq,server_ts,utc_ts,event_type,engine_id,magic,intent_id,symbol,side,"
         "signal_price,bid,ask,raw_sl,norm_sl,sl_dist,point,stops_level,tick_size,tick_value_loss,tick_value_raw,"
         "vol_min,vol_step,vol_max,balance,equity,free_margin,day_anchor_bal,day_anchor_eq,"
         "daily_dd_pct,static_dd_pct,profit_pct,regime,base_phase_mult,un_tapered_mult,daily_headroom,daily_scale,risk_mult,"
         "base_risk_pct,req_risk_pct,used_sym_pct,sym_headroom,factor_headroom,allowed_risk_pct,"
         "risk_money,raw_lots,margin_clamped_lots,final_lots,req_margin,max_allow_margin,"
         "deal_ticket,order_ticket,pos_ticket,fill_price,close_profit,retcode,reason\n"
      );
   }
}

void CloseTesterDecisionLog()
{
   if(g_testerLogHandle != INVALID_HANDLE)
   {
      FileFlush(g_testerLogHandle);
      FileClose(g_testerLogHandle);
      g_testerLogHandle = INVALID_HANDLE;
   }
}

void EmitTesterDecisionRow(const datetime nowUtc, const string evType, const string engId, const long magic,
                           const string intentId, const string sym, const string side,
                           const double sigPx, const double bid, const double ask,
                           const double rawSl, const double normSl, const double slDist,
                           const double pt, const long stopsLvl, const double tickSize,
                           const double tickValLoss, const double tickValRaw,
                           const double volMin, const double volStep, const double volMax,
                           const double bal, const double eq, const double freeMargin,
                           const double baseRiskPct, const double reqRiskPct, const double usedSymPct,
                           const double symHeadroom, const double factorHeadroom, const double allowedRiskPct,
                           const double riskMoney, const double rawLots, const double marginClampedLots,
                           const double finalLots, const double reqMargin, const double maxAllowM,
                           const ulong dealTk, const ulong ordTk, const ulong posTk,
                           const double fillPx, const double closeProfit, const uint retcode, const string reason)
{
   if(!MQLInfoInteger(MQL_TESTER) || !InpTesterEmitDecisionLog || g_testerLogHandle == INVALID_HANDLE) return;
   g_testerLogSeq++;
   string cleanReason = reason;
   StringReplace(cleanReason, ",", ";");
   StringReplace(cleanReason, "\n", " ");
   StringReplace(cleanReason, "\r", " ");
   string line = StringFormat(
      "%I64d,%I64d,%I64d,%s,%s,%I64d,%s,%s,%s,"
      "%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%I64d,%.8f,%.8f,%.8f,"
      "%.4f,%.4f,%.4f,%.6f,%.6f,%.6f,%.6f,%.6f,"
      "%.6f,%.6f,%.6f,%s,%.6f,%.6f,%.6f,%.6f,%.6f,"
      "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,"
      "%.6f,%.8f,%.8f,%.4f,%.6f,%.6f,"
      "%I64u,%I64u,%I64u,%.8f,%.6f,%u,%s\n",
      g_testerLogSeq, (long)CNaqexPropGuard::ServerNow(), (long)nowUtc, evType, engId, magic, intentId, sym, side,
      sigPx, bid, ask, rawSl, normSl, slDist, pt, stopsLvl, tickSize, tickValLoss, tickValRaw,
      volMin, volStep, volMax, bal, eq, freeMargin, g_dayAnchorBal, g_dayAnchorEq,
      g_curDailyDdPct, g_curStaticDdPct, g_curProfitPct, g_curRegime, InpBasePhaseMult,
      g_curUnTaperedMult, g_curDailyHeadroom, g_curDailyScale, g_curRiskMult,
      baseRiskPct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
      riskMoney, rawLots, marginClampedLots, finalLots, reqMargin, maxAllowM,
      dealTk, ordTk, posTk, fillPx, closeProfit, retcode, cleanReason
   );
   FileWriteString(g_testerLogHandle, line);
}

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

// V101-03: Exact UTC offset at 00:00 Prague local midnight (0-second error across all EU DST Sundays!)
int PragueMidnightUtcOffsetHoursM(const int year, const int month, const int day)
{
   if(month < 3 || month > 10) return 1;
   if(month > 3 && month < 10) return 2;
   int ls = LastSundayOfMonthM(year, month);
   if(month == 3) return (day > ls) ? 2 : 1;  // At 00:00 Prague on last Sun Mar, switch at 01:00 UTC has not occurred -> CET (+1)
   return (day <= ls) ? 2 : 1;                // At 00:00 Prague on last Sun Oct, switch at 01:00 UTC has not occurred -> CEST (+2)
}

int CurrentResetDayKeyM()
{
   datetime refTs = 0;
   if(InpDailyResetMode == 0)
      refTs = CNaqexPropGuard::ServerNow();
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
   datetime srvNow = CNaqexPropGuard::ServerNow();
   if(InpDailyResetMode == 0) return srvNow - (srvNow % 86400);
   datetime nowUtc = g_guard.NowUTC();
   long srvMinusUtc = (long)srvNow - (long)nowUtc;
   if(InpDailyResetMode == 1)
   {
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      int curOff = PragueUtcOffsetHoursM(utc) * 3600;
      datetime prgNow = nowUtc + (datetime)curOff;
      MqlDateTime prgDt; TimeToStruct(prgNow, prgDt);
      int midOff = PragueMidnightUtcOffsetHoursM(prgDt.year, prgDt.mon, prgDt.day) * 3600;
      datetime prgMidUtc = (prgNow - (prgNow % 86400)) - (datetime)midOff;
      return prgMidUtc + (datetime)srvMinusUtc;
   }
   return (nowUtc - (nowUtc % 86400)) + (datetime)srvMinusUtc;
}

void PersistAutoKillStateM(const int dayKey, const bool active)
{
   if(MQLInfoInteger(MQL_TESTER) || dayKey <= 0) return;
   GlobalVariableSet(CNaqexPropGuard::AcctDayKeyName(), (double)dayKey);
   GlobalVariableSet(CNaqexPropGuard::AcctAutoKillKey(), active ? 1.0 : 0.0);
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
   datetime nowUtc = g_guard.NowUTC();
   int today = CurrentResetDayKeyM();
   bool isNewDay = (today != g_dayKey);
   if(!isNewDay && g_dayAnchorEq > 0.0 && !g_anchorUnrecovered) return;
   // V101-02: Retry ANCHOR_UNRECOVERED every 15s instead of locking dead all day
   if(!isNewDay && g_anchorUnrecovered && (nowUtc - g_lastAnchorRetry) < 15) return;
   g_lastAnchorRetry = nowUtc;

   double reconstructedBal = bal;
   double reconstructedEq  = (InpDailyResetMode == 1) ? bal : MathMax(bal, eq);
   g_anchorUnrecovered = false;
   if(!MQLInfoInteger(MQL_TESTER))
   {
      datetime resetStart = CurrentResetStartServerTimeM();
      datetime srvNow = CNaqexPropGuard::ServerNow();
      bool histOk = (srvNow >= resetStart && HistorySelect(resetStart, srvNow + 60));
      NaqexReplayDeal deals[];
      int nDeals = 0;
      if(histOk)
      {
         int totDeals = HistoryDealsTotal();
         if(totDeals > 0)
         {
            ArrayResize(deals, totDeals);
            for(int i = 0; i < totDeals; i++)
            {
               ulong dtk = HistoryDealGetTicket(i);
               if(dtk == 0) continue;
               deals[nDeals].deal_srv_ts = (datetime)HistoryDealGetInteger(dtk, DEAL_TIME);
               deals[nDeals].deal_type   = HistoryDealGetInteger(dtk, DEAL_TYPE);
               deals[nDeals].profit      = HistoryDealGetDouble(dtk, DEAL_PROFIT);
               deals[nDeals].swap        = HistoryDealGetDouble(dtk, DEAL_SWAP);
               deals[nDeals].commission  = HistoryDealGetDouble(dtk, DEAL_COMMISSION);
               nDeals++;
            }
         }
      }
      CNaqexPropGuard::ReconstructDayAnchorFromFixture(
         bal, eq, InpDailyResetMode, resetStart, srvNow, histOk, deals, nDeals,
         reconstructedBal, reconstructedEq, g_anchorUnrecovered
      );
   }
   int prevDayKey   = g_dayKey;
   g_dayKey         = today;
   g_dayAnchorBal   = reconstructedBal;
   g_dayAnchorEq    = reconstructedEq;

   // V101-02: Restore persisted g_autoKillActive across mid-day restarts; reset cleanly on new day!
   if(!MQLInfoInteger(MQL_TESTER))
   {
      string dkKey = CNaqexPropGuard::AcctDayKeyName();
      string akKey = CNaqexPropGuard::AcctAutoKillKey();
      bool hasDk = GlobalVariableCheck(dkKey);
      bool hasAk = GlobalVariableCheck(akKey);
      int  gvDk  = hasDk ? (int)GlobalVariableGet(dkKey) : -1;
      double gvAk = hasAk ? GlobalVariableGet(akKey) : 0.0;
      bool shouldClear = false;
      g_autoKillActive = CNaqexPropGuard::RestoreAutoKillForDay(
         prevDayKey, today, hasDk, gvDk, hasAk, gvAk, g_autoKillActive, shouldClear
      );
      if(shouldClear)
         PersistAutoKillStateM(today, false);
   }
   else if(isNewDay)
   {
      g_autoKillActive = false;
   }
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
      ulong foundPosId = 0;
      double foundOpenPx = -1.0, foundSl = 0.0, foundVol = 0.0;
      for(int p = PositionsTotal() - 1; p >= 0; p--)
      {
         ulong ptk = PositionGetTicket(p);
         if(ptk == 0) continue;
         if((g_inFlight[i].order_ticket > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == g_inFlight[i].order_ticket) ||
            (PositionGetInteger(POSITION_MAGIC) == g_inFlight[i].magic && PositionGetString(POSITION_SYMBOL) == g_inFlight[i].symbol))
         {
            posFound    = true;
            foundPosId  = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
            foundOpenPx = PositionGetDouble(POSITION_PRICE_OPEN);
            foundSl     = PositionGetDouble(POSITION_SL);
            foundVol    = PositionGetDouble(POSITION_VOLUME);
            break;
         }
      }
      if(posFound)
      {
         // V101-05: Mark engine traded when TIMEOUT/PLACED unknown_state reconciles into a live position!
         if(g_inFlight[i].unknown_state)
         {
            g_signals.MarkEngineTraded(g_inFlight[i].magic, g_inFlight[i].session_day_key);
            g_guard.LogExecAuditFor(g_inFlight[i].symbol, g_inFlight[i].is_buy ? "BUY" : "SELL",
                                    "ORDER_FILL_RECONCILED", foundOpenPx, foundOpenPx, foundSl, foundVol, 0.0, TRADE_RETCODE_DONE,
                                    StringFormat("intent=%s|ord=%I64u|pos=%I64u|RECONCILED_FROM_UNKNOWN",
                                                 g_inFlight[i].intent_id, g_inFlight[i].order_ticket, foundPosId),
                                    g_inFlight[i].magic);
         }
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
   // V101-05: Deduplicate by magic or order_ticket before allocating a new slot
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
   {
      if(g_inFlight[i].active &&
         (g_inFlight[i].magic == it.magic || (ordTicket > 0 && g_inFlight[i].order_ticket == ordTicket)))
      {
         g_inFlight[i].intent_id       = it.intent_id;
         g_inFlight[i].symbol          = it.symbol;
         g_inFlight[i].is_buy          = it.is_buy;
         g_inFlight[i].est_risk_pct    = estRiskPct;
         g_inFlight[i].order_ticket    = ordTicket;
         g_inFlight[i].sent_utc        = it.signal_utc;
         g_inFlight[i].session_day_key = it.session_day_key;
         g_inFlight[i].unknown_state   = isUnknown;
         return;
      }
   }
   for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active)
      {
         g_inFlight[i].active          = true;
         g_inFlight[i].intent_id       = it.intent_id;
         g_inFlight[i].magic           = it.magic;
         g_inFlight[i].symbol          = it.symbol;
         g_inFlight[i].is_buy          = it.is_buy;
         g_inFlight[i].est_risk_pct    = estRiskPct;
         g_inFlight[i].order_ticket    = ordTicket;
         g_inFlight[i].sent_utc        = it.signal_utc;
         g_inFlight[i].session_day_key = it.session_day_key;
         g_inFlight[i].unknown_state   = isUnknown;
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

double ComputePhaseRiskMultiplier(const double dailyDdPct, const double staticDdPct,
                                  const double eqProfitPct, const double realizedProfitPct,
                                  string &outRegime)
{
   double mult = InpBasePhaseMult;
   outRegime = "NORMAL";
   double effProfitPct = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;
   if(InpProfitLockBasisMode == 1)
   {
      // v1.02-A: ProfitLock evaluates realized closed PnL (balance); AMBER/RED/headroom/kill STILL use live equity!
      // Combine independently via MathMin(ddBrakeMult, plMult) so BOTH fire cleanly when balance >= ProfitLock
      // AND live equity simultaneously breaches AMBER or RED!
      double ddBrakeMult = InpBasePhaseMult;
      string ddRegime = "";
      if(staticDdPct >= InpRedDdPct)
      {
         ddBrakeMult = InpBasePhaseMult * InpRedMult;
         ddRegime = "RED_BRAKE";
      }
      else if(staticDdPct >= InpAmberDdPct)
      {
         ddBrakeMult = InpBasePhaseMult * InpAmberMult;
         ddRegime = "AMBER_BRAKE";
      }
      double plMult = InpBasePhaseMult;
      bool plActive = (InpProfitLockPct > 0.0 && realizedProfitPct >= InpProfitLockPct);
      if(plActive)
         plMult = MathMin(plMult, InpProfitLockMult);
      mult = MathMin(ddBrakeMult, plMult);
      if(ddRegime != "" && plActive)
         outRegime = ddRegime + "+PROFIT_LOCK";
      else if(ddRegime != "")
         outRegime = ddRegime;
      else if(plActive)
         outRegime = "PROFIT_LOCK";
   }
   else
   {
      // V101-07 (REL+HEADROOM): Frozen v1.01 control (100% unchanged!)
      if(staticDdPct >= InpRedDdPct)
      {
         mult = MathMin(mult, InpBasePhaseMult * InpRedMult);
         outRegime = "RED_BRAKE";
      }
      else if(staticDdPct >= InpAmberDdPct)
      {
         mult = MathMin(mult, InpBasePhaseMult * InpAmberMult);
         outRegime = "AMBER_BRAKE";
      }
      else if(InpProfitLockPct > 0.0 && eqProfitPct >= InpProfitLockPct)
      {
         mult = MathMin(mult, InpProfitLockMult);
         outRegime = "PROFIT_LOCK";
      }
   }

   g_curUnTaperedMult = mult;
   // V101-07: Unconditional dailyHeadroom < 2.0% taper (even when InpSizingMode == 0) guarantees 0.0% daily DD breaches!
   double dailyHeadroom = MathMax(0.0, InpKillDailyDdPct - dailyDdPct);
   g_curDailyHeadroom = dailyHeadroom;
   g_curDailyScale    = 1.0;
   if(dailyHeadroom < 2.0)
   {
      double dailyScale = MathMax(0.25, dailyHeadroom / 2.0);
      g_curDailyScale = dailyScale;
      mult = MathMin(mult, InpBasePhaseMult * dailyScale);
      if(outRegime == "NORMAL")
         outRegime = "DAILY_HEADROOM_TAPER";
   }

   // SizingMode 1: BARRIER_HEADROOM_MIN (Astra Round-3 state-dependent control — ONLY tapers, NEVER boosts!)
   if(InpSizingMode == 1)
   {
      double staticHeadroom = MathMax(0.0, InpKillStaticDdPct - staticDdPct);
      double ddScale = 1.0;
      if(staticHeadroom < 3.5) ddScale = MathMin(ddScale, MathMax(0.25, staticHeadroom / 3.5));
      // Target-proximity taper when within last 35% of phase profit target
      if(InpTargetProfitPct > 0.0 && effProfitPct > 0.0)
      {
         double remToTarget = MathMax(0.0, InpTargetProfitPct - effProfitPct);
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
         "{\"utc_ts\":%I64d,\"account_login\":%I64d,\"account_server\":\"%s\",\"build_version\":\"master-1.01\","
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

int ClosePositionsByReason(const datetime nowUtc, const bool flattenAll, const string globalReason)
{
   bool isDry = (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly);
   int closedConfirmedCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      string psym = PositionGetString(POSITION_SYMBOL);
      ulong pIdPre = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
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
         // V101-04: Never execute non-emergency clock/session close inside +/-135s hard red-news ban!
         if(!flattenAll && g_guard.IsInsideRedNewsHardBanFor(psym))
            continue;
         bool emitLog = (MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE);
         double preBal = 0.0, preEq = 0.0, preFm = 0.0, psl = 0.0, pOpen = 0.0, pBid = 0.0, pAsk = 0.0;
         double pvol   = PositionGetDouble(POSITION_VOLUME);
         double volMin = SymbolInfoDouble(psym, SYMBOL_VOLUME_MIN);
         ulong pId = pIdPre;
         string pSide = "";
         if(emitLog)
         {
            preBal = AccountInfoDouble(ACCOUNT_BALANCE);
            preEq  = AccountInfoDouble(ACCOUNT_EQUITY);
            preFm  = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
            psl    = PositionGetDouble(POSITION_SL);
            pOpen  = PositionGetDouble(POSITION_PRICE_OPEN);
            pSide  = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "SELL" : "BUY";
            pBid   = SymbolInfoDouble(psym, SYMBOL_BID);
            pAsk   = SymbolInfoDouble(psym, SYMBOL_ASK);
            double reqPx = (pSide == "SELL") ? pBid : pAsk;
            EmitTesterDecisionRow(nowUtc, "CLOSE_REQUEST", "", pm, "", psym, pSide,
                                  reqPx, pBid, pAsk, psl, psl, MathAbs(pOpen - psl),
                                  SymbolInfoDouble(psym, SYMBOL_POINT), SymbolInfoInteger(psym, SYMBOL_TRADE_STOPS_LEVEL),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE_LOSS),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE),
                                  volMin,
                                  SymbolInfoDouble(psym, SYMBOL_VOLUME_STEP),
                                  SymbolInfoDouble(psym, SYMBOL_VOLUME_MAX),
                                  preBal, preEq, preFm,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, pvol, pvol, pvol, 0.0, 0.0,
                                  0, 0, pId, 0.0, 0.0, 0, reason);
         }
         g_trade.SetExpertMagicNumber(pm);
         bool okClose = g_guard.ClosePositionChecked(g_trade, tk, reason, isDry);
         uint cRet = g_trade.ResultRetcode();
         ulong cDeal = (ulong)g_trade.ResultDeal();
         double filledVol = g_trade.ResultVolume();
         if(filledVol <= 0.0 && cDeal > 0 && HistoryDealSelect(cDeal))
            filledVol = HistoryDealGetDouble(cDeal, DEAL_VOLUME);
         bool stillOpenAfter = PositionSelectByTicket(tk);
         double remVolAfter  = stillOpenAfter ? PositionGetDouble(POSITION_VOLUME) : 0.0;
         bool pcDirty = false;
         CNaqexPropGuard::ApplyCloseOutcomeToPendingTable(
            g_pendingCloses, isDry, okClose, cRet, pId, pm, psym,
            pvol, filledVol, volMin, stillOpenAfter, remVolAfter, reason, nowUtc,
            closedConfirmedCount, pcDirty
         );
         if(pcDirty && !MQLInfoInteger(MQL_TESTER))
            CNaqexPropGuard::SavePendingCloseState(g_pendingCloses);
         if(emitLog)
         {
            ulong cOrd  = (ulong)g_trade.ResultOrder();
            double cPx  = g_trade.ResultPrice();
            double cNet = 0.0;
            if(cDeal > 0 && HistoryDealSelect(cDeal))
            {
               if(cPx <= 0.0) cPx = HistoryDealGetDouble(cDeal, DEAL_PRICE);
               cNet = HistoryDealGetDouble(cDeal, DEAL_PROFIT)
                    + HistoryDealGetDouble(cDeal, DEAL_COMMISSION)
                    + HistoryDealGetDouble(cDeal, DEAL_SWAP);
            }
            string closeEv = okClose ? "CLOSE_FILL" : ((cRet == TRADE_RETCODE_DONE_PARTIAL && filledVol > 0.0) ? "CLOSE_PARTIAL_FILL" : "CLOSE_FAIL");
            EmitTesterDecisionRow(nowUtc, closeEv, "", pm, "", psym, pSide,
                                  (pSide == "SELL") ? pBid : pAsk,
                                  SymbolInfoDouble(psym, SYMBOL_BID), SymbolInfoDouble(psym, SYMBOL_ASK),
                                  psl, psl, MathAbs(pOpen - psl),
                                  SymbolInfoDouble(psym, SYMBOL_POINT), SymbolInfoInteger(psym, SYMBOL_TRADE_STOPS_LEVEL),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE_LOSS),
                                  SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE),
                                  volMin,
                                  SymbolInfoDouble(psym, SYMBOL_VOLUME_STEP),
                                  SymbolInfoDouble(psym, SYMBOL_VOLUME_MAX),
                                  AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY),
                                  AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, pvol, pvol, (filledVol > 0.0 ? filledVol : pvol), 0.0, 0.0,
                                  cDeal, cOrd, pId, cPx, cNet, cRet, reason);
         }
      }
   }
   return closedConfirmedCount;
}

// V101-05: Cancel pending orders in our magic range on Kill-Switch, ManualFlatten, Red-News Pre-Flatten, or Hard-Flat
void CancelPendingOrdersByReason(const datetime nowUtc, const bool cancelAll, const string globalReason)
{
   bool isDry = (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly);
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ot = OrderGetTicket(i);
      if(ot == 0) continue;
      long om = OrderGetInteger(ORDER_MAGIC);
      if(om < InpMagicRangeMin || om > InpMagicRangeMax) continue;
      string osym = OrderGetString(ORDER_SYMBOL);
      string reason = "";
      if(cancelAll)
         reason = globalReason;
      else if(g_signals.ShouldClockFlattenMagic(om, nowUtc, reason))
         {}
      else if(g_guard.IsNearBrokerSessionCloseFor(osym))
         reason = "HARD_FLAT_SESSION_CLOSE_SWAP0";
      else if(g_guard.IsInRedNewsPreFlattenWindowFor(osym))
         reason = "NEWS_PRE_FLATTEN";
      if(reason == "") continue;
      if(!cancelAll && g_guard.IsInsideRedNewsHardBanFor(osym))
         continue;
      double op   = OrderGetDouble(ORDER_PRICE_OPEN);
      double osl  = OrderGetDouble(ORDER_SL);
      double ovol = OrderGetDouble(ORDER_VOLUME_CURRENT);
      long otype  = OrderGetInteger(ORDER_TYPE);
      string sideStr = (otype == ORDER_TYPE_BUY_LIMIT || otype == ORDER_TYPE_BUY_STOP || otype == ORDER_TYPE_BUY_STOP_LIMIT) ? "BUY" : "SELL";
      if(isDry)
      {
         PrintFormat("[DRYRUN-CANCEL] ord=%I64u magic=%I64d sym=%s vol=%.2f reason=%s", ot, om, osym, ovol, reason);
         continue;
      }
      g_trade.SetExpertMagicNumber(om);
      ulong t0 = GetMicrosecondCount();
      bool ok = g_trade.OrderDelete(ot);
      double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
      uint ret = g_trade.ResultRetcode();
      g_guard.LogExecAuditFor(osym, sideStr, ok ? "ORDER_CANCEL" : "CANCEL_REJECT", op, -1.0, osl, ovol, latMs, ret,
                              StringFormat("%s|ord=%I64u|%s", reason, ot, g_trade.ResultRetcodeDescription()),
                              om);
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
   if(HasOpenOrInFlightForMagic(it.magic))
   {
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "OPEN_OR_INFLIGHT_POSITION:SKIP", blkCnt, evCnt);
      }
      return;
   }
   bool emitLog = (MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE);
   string sideStrLog = it.is_buy ? "BUY" : "SELL";
   double preBid = emitLog ? SymbolInfoDouble(it.symbol, SYMBOL_BID) : 0.0;
   double preAsk = emitLog ? SymbolInfoDouble(it.symbol, SYMBOL_ASK) : 0.0;
   double preBal = emitLog ? AccountInfoDouble(ACCOUNT_BALANCE) : 0.0;
   double preEq  = emitLog ? AccountInfoDouble(ACCOUNT_EQUITY) : 0.0;
   double preFm  = emitLog ? AccountInfoDouble(ACCOUNT_MARGIN_FREE) : 0.0;

   if(g_guard.IsInsideRedNewsWindowFor(it.symbol))
   {
      string whyNews = "INSIDE_RED_NEWS_OR_EXPIRED_CALENDAR";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "NEWS", "RED_NEWS_WINDOW:ORDER_BLOCKED_NEWS", blkCnt, evCnt);
         whyNews = StringFormat("root=RED_NEWS_WINDOW|outcome=ORDER_BLOCKED_NEWS|opp=%s|eval=%d|blk=%d",
                                it.opportunity_id, it.opp_eval_count, blkCnt);
         if(logTrans)
            LogMasterShadowRow(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      }
      else
         LogMasterShadowRow(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_NEWS", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, 0.0, 0.0,
                               SymbolInfoDouble(it.symbol, SYMBOL_POINT), SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                               preBal, preEq, preFm,
                               it.base_risk_pct, it.base_risk_pct * riskMult, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whyNews);
      return;
   }
   if(!g_guard.IsSpreadAndSessionSafeFor(it.symbol, MaxSpreadCapForSymbol(it.symbol)))
   {
      string whySpr = "SPREAD_OR_ROLLOVER_GUARD";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "SPREAD", "SPREAD_OR_ROLLOVER_GUARD:ORDER_BLOCKED_SPREAD", blkCnt, evCnt);
         whySpr = StringFormat("root=SPREAD_OR_ROLLOVER_GUARD|outcome=ORDER_BLOCKED_SPREAD|opp=%s|eval=%d|blk=%d",
                               it.opportunity_id, it.opp_eval_count, blkCnt);
         if(logTrans)
            LogMasterShadowRow(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
      }
      else
         LogMasterShadowRow(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_SPREAD", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, 0.0, 0.0,
                               SymbolInfoDouble(it.symbol, SYMBOL_POINT), SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                               preBal, preEq, preFm,
                               it.base_risk_pct, it.base_risk_pct * riskMult, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whySpr);
      return;
   }

   double normSl = CNaqexPropGuard::NormalizePriceToTick(it.symbol, it.sl_price);
   double stopLoss = normSl;
   double slDist = MathAbs(it.signal_price - stopLoss);
   if(slDist <= 0.0 || stopLoss <= 0.0)
   {
      string whyBadSl = "SL_DIST_OR_SL_LE_0";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "INVALID_SL:SL_DIST_OR_SL_LE_0", blkCnt, evCnt);
         whyBadSl = StringFormat("root=INVALID_SL|outcome=SL_DIST_OR_SL_LE_0|opp=%s|eval=%d|blk=%d",
                                 it.opportunity_id, it.opp_eval_count, blkCnt);
      }
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_BAD_SL", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               SymbolInfoDouble(it.symbol, SYMBOL_POINT), SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                               preBal, preEq, preFm,
                               it.base_risk_pct, it.base_risk_pct * riskMult, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whyBadSl);
      return;
   }
   double pt = SymbolInfoDouble(it.symbol, SYMBOL_POINT);
   long stopsLvl = SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL);
   // V101-06: Verify STOPS_LEVEL against actual liquidation price (Bid - SL for BUY, SL - Ask for SELL)
   double liqPx = it.is_buy ? SymbolInfoDouble(it.symbol, SYMBOL_BID) : SymbolInfoDouble(it.symbol, SYMBOL_ASK);
   if(liqPx <= 0.0) liqPx = it.signal_price;
   double stopsGap = it.is_buy ? (liqPx - stopLoss) : (stopLoss - liqPx);
   if(pt > 0.0 && stopsLvl > 0 && stopsGap < (double)stopsLvl * pt)
   {
      string whyStops = "SL_BELOW_BROKER_STOPS_LEVEL";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "BROKER_STOPS_LEVEL:ORDER_BLOCKED_STOPS", blkCnt, evCnt);
         whyStops = StringFormat("root=BROKER_STOPS_LEVEL|outcome=ORDER_BLOCKED_STOPS|opp=%s|eval=%d|blk=%d",
                                 it.opportunity_id, it.opp_eval_count, blkCnt);
         if(logTrans)
            LogMasterShadowRow(it, "ORDER_BLOCKED_STOPS", 0.0, 0.0, whyStops);
      }
      else
         LogMasterShadowRow(it, "ORDER_BLOCKED_STOPS", 0.0, 0.0, whyStops);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_STOPS", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl,
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                               SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                               SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                               preBal, preEq, preFm,
                               it.base_risk_pct, it.base_risk_pct * riskMult, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whyStops);
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
      if(InpOpportunityLifecycleMode == 1)
      {
         string rootCause = (factorHeadroom <= symHeadroom) ? "LOW_FACTOR_HEADROOM" : "LOW_SYM_HEADROOM";
         string blkKey = rootCause + ":" + why;
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "CAP", blkKey, blkCnt, evCnt);
         string structWhy = StringFormat("root=%s|outcome=%s|opp=%s|eval=%d|blk=%d|symRem=%.4f|facRem=%.4f",
                                         rootCause, why, it.opportunity_id, it.opp_eval_count, blkCnt, symHeadroom, factorHeadroom);
         if(logTrans)
            LogMasterShadowRow(it, why, reqRiskPct, 0.0, structWhy);
         if(emitLog)
            EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_CAP", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                                  it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                                  pt, stopsLvl,
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                                  preBal, preEq, preFm,
                                  it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0, 0, 0, 0.0, 0.0, 0, structWhy);
      }
      else
      {
         LogMasterShadowRow(it, why, reqRiskPct, 0.0,
                            StringFormat("symRem=%.2f|facRem=%.2f", symHeadroom, factorHeadroom));
         if(emitLog)
            EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_CAP", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                                  it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                                  pt, stopsLvl,
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE),
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS),
                                  SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP),
                                  SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX),
                                  preBal, preEq, preFm,
                                  it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0, 0, 0, 0.0, 0.0, 0, why);
      }
      return;
   }

   // Compute safe lots with 5% commission cushion + volDigits rounding + fail-closed OrderCalcMargin <= 85% (V101-06)
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickSize = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValLoss = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double tickValRaw  = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickVal  = (tickValLoss > 0.0) ? tickValLoss : tickValRaw;
   double volMin  = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN);
   double volMax  = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX);
   double volStep = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP);
   if(bal <= 0.0 || tickSize <= 0.0 || tickVal <= 0.0 || volStep <= 0.0)
   {
      string whySpec = "INVALID_SYMBOL_OR_BAL_SPEC";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "INVALID_SPEC:INVALID_SYMBOL_OR_BAL_SPEC", blkCnt, evCnt);
         whySpec = StringFormat("root=INVALID_SPEC|outcome=INVALID_SYMBOL_OR_BAL_SPEC|opp=%s|eval=%d|blk=%d",
                                it.opportunity_id, it.opp_eval_count, blkCnt);
      }
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_BAD_SPEC", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, preFm,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whySpec);
      return;
   }

   double lossPerLot = (slDist / tickSize) * tickVal;
   if(lossPerLot <= 0.0)
   {
      string whyLpl = "LOSS_PER_LOT_LE_0";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "INVALID_SPEC:LOSS_PER_LOT_LE_0", blkCnt, evCnt);
         whyLpl = StringFormat("root=INVALID_SPEC|outcome=LOSS_PER_LOT_LE_0|opp=%s|eval=%d|blk=%d",
                               it.opportunity_id, it.opp_eval_count, blkCnt);
      }
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_BAD_SPEC", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, preFm,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, whyLpl);
      return;
   }
   double riskMoney = bal * (allowedRiskPct / 100.0) * 0.95;
   double rawLots = riskMoney / lossPerLot;
   double lots = CNaqexPropGuard::RoundVolumeDownToStep(rawLots, volStep, volMin, volMax);
   if(lots < volMin)
   {
      if(InpOpportunityLifecycleMode == 1)
      {
         string rootCause = "BASE_RISK_OR_SL_TOO_WIDE";
         if(allowedRiskPct < reqRiskPct - 1e-9)
            rootCause = (factorHeadroom <= symHeadroom) ? "LOW_FACTOR_HEADROOM" : "LOW_SYM_HEADROOM";
         else if(g_curDailyHeadroom < 2.0 && g_curRiskMult < g_curUnTaperedMult - 1e-9)
            rootCause = "DAILY_HEADROOM_TAPER";
         string outcome = "RAW_LOTS_BELOW_VOLMIN";
         string blkKey  = rootCause + ":" + outcome;
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "LMIN", blkKey, blkCnt, evCnt);
         string structWhy = StringFormat("root=%s|outcome=%s|opp=%s|eval=%d|blk=%d|symRem=%.4f|facRem=%.4f",
                                         rootCause, outcome, it.opportunity_id, it.opp_eval_count, blkCnt, symHeadroom, factorHeadroom);
         // Live transition-only log (fixes silent L653 blind spot without 24k per-tick spam!)
         if(logTrans)
            LogMasterShadowRow(it, "ORDER_BLOCKED_LOT_MIN", allowedRiskPct, 0.0, structWhy);
         if(emitLog)
            EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_LOT_MIN", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                                  it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                                  pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                                  bal, preEq, preFm,
                                  it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                                  riskMoney, rawLots, lots, 0.0, 0.0, 0.0,
                                  0, 0, 0, 0.0, 0.0, 0, structWhy);
      }
      else if(emitLog)
      {
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_LOT_MIN", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, preFm,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, lots, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, "RAW_LOTS_BELOW_VOLMIN");
      }
      return;
   }

   ENUM_ORDER_TYPE ordType = it.is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double reqMargin = 0.0;
   if(freeMargin <= 0.0 || !OrderCalcMargin(ordType, it.symbol, lots, it.signal_price, reqMargin) || reqMargin <= 0.0)
   {
      string whyMargin = "FAIL_CLOSED_MARGIN_CHECK";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "MARGIN_CALC_FAIL:ORDER_BLOCKED_MARGIN", blkCnt, evCnt);
         whyMargin = StringFormat("root=MARGIN_CALC_FAIL|outcome=ORDER_BLOCKED_MARGIN|opp=%s|eval=%d|blk=%d",
                                  it.opportunity_id, it.opp_eval_count, blkCnt);
         if(logTrans)
            LogMasterShadowRow(it, "ORDER_BLOCKED_MARGIN", allowedRiskPct, 0.0, whyMargin);
      }
      else
         LogMasterShadowRow(it, "ORDER_BLOCKED_MARGIN", allowedRiskPct, 0.0, whyMargin);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_MARGIN_CALC", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, lots, 0.0, reqMargin, freeMargin * 0.85,
                               0, 0, 0, 0.0, 0.0, 0, whyMargin);
      return;
   }
   double maxAllowM = freeMargin * 0.85;
   double preMarginLots = lots;
   bool marginClamped = false;
   if(reqMargin > maxAllowM)
   {
      marginClamped = true;
      lots = CNaqexPropGuard::RoundVolumeDownToStep(lots * (maxAllowM / reqMargin), volStep, volMin, volMax);
      if(lots < volMin)
      {
         if(InpOpportunityLifecycleMode == 1)
         {
            int blkCnt = 0, evCnt = 0;
            bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "LMIN", "LOW_FREE_MARGIN:MARGIN_CLAMP_BELOW_VOLMIN", blkCnt, evCnt);
            string structWhy = StringFormat("root=LOW_FREE_MARGIN|outcome=MARGIN_CLAMP_BELOW_VOLMIN|opp=%s|eval=%d|blk=%d",
                                            it.opportunity_id, it.opp_eval_count, blkCnt);
            if(logTrans)
               LogMasterShadowRow(it, "ORDER_BLOCKED_MARGIN_LOT_MIN", allowedRiskPct, 0.0, structWhy);
            if(emitLog)
               EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_MARGIN_LOT_MIN", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                                     it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                                     pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                                     bal, preEq, freeMargin,
                                     it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                                     riskMoney, rawLots, lots, 0.0, reqMargin, maxAllowM,
                                     0, 0, 0, 0.0, 0.0, 0, structWhy);
         }
         else if(emitLog)
         {
            EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_MARGIN_LOT_MIN", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                                  it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                                  pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                                  bal, preEq, freeMargin,
                                  it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                                  riskMoney, rawLots, lots, 0.0, reqMargin, maxAllowM,
                                  0, 0, 0, 0.0, 0.0, 0, "MARGIN_CLAMP_BELOW_VOLMIN");
         }
         return;
      }
   }

   if(emitLog)
   {
      string taperWhy = "";
      if(g_curDailyHeadroom < 2.0 && g_curRiskMult < g_curUnTaperedMult - 1e-9) taperWhy += "DAILY_HEADROOM_TAPER";
      if(allowedRiskPct < reqRiskPct - 1e-9) taperWhy += (taperWhy == "" ? "" : "|") + "CAP_CLAMP";
      if(marginClamped && lots < preMarginLots - 1e-9) taperWhy += (taperWhy == "" ? "" : "|") + "MARGIN_CLAMP";
      if(taperWhy != "")
         EmitTesterDecisionRow(it.signal_utc, "LOT_TAPER", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, preMarginLots, lots, reqMargin, maxAllowM,
                               0, 0, 0, 0.0, 0.0, 0, taperWhy);
   }

   // Always record shadow intent in shadow/dry-run mode (ZERO OrderSend!)
   if(isShadowOrDry)
   {
      LogMasterShadowRow(it, it.shadow_only ? "SHADOW_INTENT" : "DRYRUN_SIGNAL", allowedRiskPct, lots, it.tag);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_ACCEPT_DRYRUN", it.engine_id, it.magic, it.intent_id, it.symbol, sideStrLog,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, preMarginLots, lots, reqMargin, maxAllowM,
                               0, 0, 0, 0.0, 0.0, 0, it.tag);
      g_signals.MarkEngineTraded(it.magic, it.session_day_key);
      return;
   }

   double actualRiskPct = (((slDist / tickSize) * tickVal * lots) / bal) * 100.0;
   g_trade.SetExpertMagicNumber(it.magic);
   CNaqexPropGuard::ConfigureFillingMode(g_trade, it.symbol);
   // V101-06: Live-calibrated per-asset slippage tolerance (35 pts FX / 450 pts US100.cash >= +370pt live spike!)
   ulong devPts = CNaqexPropGuard::RecommendedDeviationPoints(it.symbol,
                                                              (ulong)MathMax(0, InpMaxSlippagePointsFx),
                                                              (ulong)MathMax(0, InpMaxSlippagePointsIdx));
   g_trade.SetDeviationInPoints(devPts);

   ulong t0 = GetMicrosecondCount();
   bool ok = it.is_buy ? g_trade.Buy(lots, it.symbol, it.signal_price, normSl, 0.0, it.tag)
                       : g_trade.Sell(lots, it.symbol, it.signal_price, normSl, 0.0, it.tag);
   double latMs = (double)(GetMicrosecondCount() - t0) / 1000.0;
   uint ret = g_trade.ResultRetcode();
   string sideStr = it.is_buy ? "BUY" : "SELL";

   if(ret == TRADE_RETCODE_TIMEOUT || ret == TRADE_RETCODE_PLACED)
   {
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "ORDER_UNRESOLVED:UNKNOWN_INFLIGHT", blkCnt, evCnt);
      }
      RegisterInFlight(it, actualRiskPct, g_trade.ResultOrder(), true);
      g_guard.LogExecAuditFor(it.symbol, sideStr, "FILL_UNRESOLVED", it.signal_price, -1.0, normSl, lots, latMs, ret,
                              StringFormat("%s|intent=%s|ord=%I64u|UNKNOWN_INFLIGHT", it.tag, it.intent_id, (ulong)g_trade.ResultOrder()),
                              it.magic);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_UNRESOLVED", it.engine_id, it.magic, it.intent_id, it.symbol, sideStr,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, preMarginLots, lots, reqMargin, maxAllowM,
                               0, (ulong)g_trade.ResultOrder(), 0, -1.0, 0.0, ret, "UNKNOWN_INFLIGHT");
      return;
   }
   if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
   {
      string whyBroker = g_trade.ResultRetcodeDescription();
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "BROKER_REJECT:" + whyBroker, blkCnt, evCnt);
         whyBroker = StringFormat("root=BROKER_REJECT|outcome=%s|opp=%s|eval=%d|blk=%d",
                                  whyBroker, it.opportunity_id, it.opp_eval_count, blkCnt);
      }
      g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_REJECT", it.signal_price, g_trade.ResultPrice(), normSl, lots, latMs, ret,
                              StringFormat("%s|intent=%s|%s", it.tag, it.intent_id, g_trade.ResultRetcodeDescription()),
                              it.magic);
      if(emitLog)
         EmitTesterDecisionRow(it.signal_utc, "INTENT_REJECT_BROKER", it.engine_id, it.magic, it.intent_id, it.symbol, sideStr,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, preMarginLots, lots, reqMargin, maxAllowM,
                               0, (ulong)g_trade.ResultOrder(), 0, g_trade.ResultPrice(), 0.0, ret, whyBroker);
      return;
   }

   ulong dealId = (ulong)g_trade.ResultDeal();
   ulong ordId  = (ulong)g_trade.ResultOrder();
   ulong posId  = ordId;
   if(dealId > 0 && HistoryDealSelect(dealId))
   {
      long dPos = HistoryDealGetInteger(dealId, DEAL_POSITION_ID);
      if(dPos > 0) posId = (ulong)dPos;
   }

   // V101-05: Only register g_inFlight if the broker has NOT already synchronously materialized the position
   bool alreadyInPositions = false;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
   {
      ulong ptk = PositionGetTicket(p);
      if(ptk == 0) continue;
      if((posId > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == posId) ||
         (PositionGetInteger(POSITION_MAGIC) == it.magic && PositionGetString(POSITION_SYMBOL) == it.symbol))
      {
         alreadyInPositions = true;
         break;
      }
   }
   if(!alreadyInPositions)
      RegisterInFlight(it, actualRiskPct, ordId, false);

   double execLots = (g_trade.ResultVolume() > 0.0) ? g_trade.ResultVolume() : lots;
   double fillPx = g_guard.ResolveExecutedFillPrice(g_trade, it.symbol, -1.0);
   // V101-01: Log real per-engine it.magic + tk=/pos= so prop_challenge_tracker matches 7/7 engines!
   g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_FILL", it.signal_price, fillPx, normSl, execLots, latMs, ret,
                           StringFormat("%s|intent=%s|deal=%I64u|ord=%I64u|tk=%I64u|pos=%I64u%s",
                                        it.tag, it.intent_id, dealId, ordId, ordId, posId,
                                        (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : ""),
                           it.magic);
   if(emitLog)
   {
      string fillWhy = it.tag;
      if(InpOpportunityLifecycleMode == 1 && it.opportunity_id != "")
      {
         int oEval = 0, oBlk = 0; string oLastBlk = ""; string oBy = "";
         g_signals.GetOpportunityStats(it.magic, oEval, oBlk, oLastBlk, oBy);
         fillWhy = StringFormat("%s|opp=%s|eval=%d|blk=%d%s", it.tag, it.opportunity_id, oEval, oBlk,
                                (oBy != "" ? ("|blk_by=" + oBy) : ""));
         string accWhy = StringFormat("ACCEPTED|opp=%s|eval=%d|blk=%d%s%s",
                                      it.opportunity_id, oEval, oBlk,
                                      (oBy != "" ? ("|blk_by=" + oBy) : ""),
                                      (oLastBlk != "" ? ("|prev_blk=" + oLastBlk) : ""));
         EmitTesterDecisionRow(it.signal_utc, "OPP_ACCEPTED", it.engine_id, it.magic, it.opportunity_id, it.symbol, sideStr,
                               it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                               pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                               bal, preEq, freeMargin,
                               it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                               riskMoney, rawLots, preMarginLots, execLots, reqMargin, maxAllowM,
                               dealId, ordId, posId, fillPx, 0.0, ret, accWhy);
      }
      EmitTesterDecisionRow(it.signal_utc, "INTENT_ACCEPT_FILL", it.engine_id, it.magic, it.intent_id, it.symbol, sideStr,
                            it.signal_price, preBid, preAsk, it.sl_price, normSl, slDist,
                            pt, stopsLvl, tickSize, tickValLoss, tickValRaw, volMin, volStep, volMax,
                            bal, preEq, freeMargin,
                            it.base_risk_pct, reqRiskPct, usedSymPct, symHeadroom, factorHeadroom, allowedRiskPct,
                            riskMoney, rawLots, preMarginLots, execLots, reqMargin, maxAllowM,
                            dealId, ordId, posId, fillPx, 0.0, ret, fillWhy);
   }
   else if(InpOpportunityLifecycleMode == 1 && it.opportunity_id != "")
   {
      int oEval = 0, oBlk = 0; string oLastBlk = ""; string oBy = "";
      g_signals.GetOpportunityStats(it.magic, oEval, oBlk, oLastBlk, oBy);
      if(oBlk > 0)
         LogMasterShadowRow(it, "OPP_ACCEPTED", allowedRiskPct, execLots,
                            StringFormat("opp=%s|eval=%d|blk=%d%s|prev_blk=%s", it.opportunity_id, oEval, oBlk,
                                         (oBy != "" ? ("|blk_by=" + oBy) : ""), oLastBlk));
   }
   g_signals.MarkEngineTraded(it.magic, it.session_day_key);
}

void EmitOppTransitionsToLogs(const datetime nowUtc, const double bal, const double eq, const double fm)
{
   if(InpOpportunityLifecycleMode != 1) return;
   NaqexOppTransition evs[NAQEX_MAX_OPP_EVENTS];
   int nEv = g_signals.DrainOppTransitions(evs);
   if(nEv <= 0) return;
   bool emitLog = (MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE);
   for(int i = 0; i < nEv; i++)
   {
      string byStr = CNaqexSignals7E::FormatTransitionBlockBreakdown(evs[i]);
      string why = StringFormat("%s|opp=%s|eval=%d|blk=%d%s%s",
                                evs[i].reason, evs[i].opp_id, evs[i].eval_count, evs[i].block_count,
                                (byStr != "" ? ("|blk_by=" + byStr) : ""),
                                (evs[i].last_block_key != "" ? ("|last_blk=" + evs[i].last_block_key) : ""));
      if(emitLog)
      {
         double b = (evs[i].symbol != "") ? SymbolInfoDouble(evs[i].symbol, SYMBOL_BID) : 0.0;
         double a = (evs[i].symbol != "") ? SymbolInfoDouble(evs[i].symbol, SYMBOL_ASK) : 0.0;
         EmitTesterDecisionRow(evs[i].utc_ts, evs[i].event_type, evs[i].engine_id, evs[i].magic,
                               evs[i].opp_id, evs[i].symbol, evs[i].is_buy ? "BUY" : "SELL",
                               evs[i].signal_price, b, a, 0.0, 0.0, 0.0,
                               0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               bal, eq, fm,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, why);
      }
      if(!MQLInfoInteger(MQL_TESTER) && evs[i].event_type == "OPP_EXPIRED" && evs[i].block_count > 0)
      {
         NaqexSignalIntent tmp;
         tmp.intent_id = evs[i].opp_id; tmp.opportunity_id = evs[i].opp_id;
         tmp.opp_eval_count = evs[i].eval_count; tmp.opp_is_new = false;
         tmp.engine_id = evs[i].engine_id; tmp.magic = evs[i].magic; tmp.symbol = evs[i].symbol;
         tmp.is_buy = evs[i].is_buy; tmp.signal_price = evs[i].signal_price; tmp.sl_price = 0.0;
         tmp.base_risk_pct = 0.0; tmp.signal_utc = evs[i].utc_ts; tmp.tick_lag_ms = 0;
         tmp.shadow_only = false; tmp.session_day_key = 0; tmp.tag = "";
         LogMasterShadowRow(tmp, "OPP_EXPIRED", 0.0, 0.0, why);
      }
   }
}

int ReconcilePendingCloses()
{
   if(MQLInfoInteger(MQL_TESTER)) return 0;
   bool dirty = false;
   int disappearedCnt = 0;
   for(int i = 0; i < NAQEX_MAX_PENDING_CLOSES; i++)
   {
      if(!g_pendingCloses[i].active || g_pendingCloses[i].pos_id == 0) continue;
      bool stillOpen = false;
      double curVol = 0.0;
      for(int p = PositionsTotal() - 1; p >= 0; p--)
      {
         if(PositionGetTicket(p) > 0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER) == g_pendingCloses[i].pos_id)
         {
            stillOpen = true;
            curVol = PositionGetDouble(POSITION_VOLUME);
            break;
         }
      }
      if(!stillOpen)
      {
         CNaqexPropGuard::ResetPendingCloseEntry(g_pendingCloses[i]);
         dirty = true;
         disappearedCnt++;
      }
      else if(curVol > 0.0 && MathAbs(curVol - g_pendingCloses[i].remain_vol) > 1e-6)
      {
         g_pendingCloses[i].remain_vol = curVol;
         dirty = true;
      }
   }
   if(dirty)
      CNaqexPropGuard::SavePendingCloseState(g_pendingCloses);
   return disappearedCnt;
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
   // V101-02: Retry traded-day history hydration every 5s if initial OnInit HistorySelect failed
   if(!g_signals.IsTradedDayHydrated() && (nowUtc - g_lastHydrateRetry) >= 5)
   {
      g_lastHydrateRetry = nowUtc;
      g_signals.HydrateTradedDaysFromHistory(nowUtc);
   }
   ReconcileInFlightOrders(nowUtc);

   long lag = g_signals.PollSymbolTicks();
   g_lastTickLagMs = lag;
   if(lag > g_maxTickLagMs) g_maxTickLagMs = lag;

   double dailyDdPct = (InpDailyResetMode == 1)
      ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
      : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
   double staticDdPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double eqProfitPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double realizedProfitPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((bal - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double profitPct         = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;

   string regime = "NORMAL";
   double riskMult = ComputePhaseRiskMultiplier(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, regime);
   g_curDailyDdPct  = dailyDdPct;
   g_curStaticDdPct = staticDdPct;
   g_curProfitPct   = profitPct;
   g_curRegime      = regime;
   g_curRiskMult    = riskMult;
   if(MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE)
   {
      if(regime != g_prevLogRegime || MathAbs(riskMult - g_prevLogMult) > 1e-9)
      {
         string chgReason = StringFormat("prev=%s@%.4f->%s@%.4f", g_prevLogRegime, g_prevLogMult, regime, riskMult);
         EmitTesterDecisionRow(nowUtc, "REGIME_OR_TAPER_CHANGE", "", 0, "", "", "",
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               bal, eq, AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0, chgReason);
         g_prevLogRegime = regime;
         g_prevLogMult   = riskMult;
      }
   }

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
   {
      if(!g_autoKillActive)
      {
         g_autoKillActive = true;
         PersistAutoKillStateM(g_dayKey, true);
         if(MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE)
         {
            string kWhy = (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD";
            EmitTesterDecisionRow(nowUtc, "KILL_ACTIVATED", "", 0, "", "", "",
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  bal, eq, AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0, 0, 0, 0.0, 0.0, 0, kWhy);
         }
      }
   }
   bool effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
   if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
   if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";

   // Exits, pending order cancellations & risk protection ALWAYS execute before any new intent evaluation
   int closedConfirmedCount = 0;
   if(g_autoKillActive)
   {
      string killWhy = (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD";
      CancelPendingOrdersByReason(nowUtc, true, killWhy);
      closedConfirmedCount = ClosePositionsByReason(nowUtc, true, killWhy);
   }
   else if(manualFlatten)
   {
      CancelPendingOrdersByReason(nowUtc, true, "MASTER_MANUAL_FLATTEN");
      closedConfirmedCount = ClosePositionsByReason(nowUtc, true, "MASTER_MANUAL_FLATTEN");
   }
   else
   {
      CancelPendingOrdersByReason(nowUtc, false, "");
      closedConfirmedCount = ClosePositionsByReason(nowUtc, false, "");
   }

   // Reconcile any persisted pending-close entries once broker confirms position is gone (or volume updated)
   closedConfirmedCount += ReconcilePendingCloses();

   // Q2 (opt-in InpPostCloseRefreshMode == 1): Refresh ONE consistent post-close risk snapshot ONLY after
   // >= 1 confirmed close has already been booked into ACCOUNT_BALANCE, BEFORE CollectIntents()!
   // Pending/unconfirmed/dry-run closes leave closedConfirmedCount == 0 and NEVER flip ProfitLock prematurely!
   if(InpPostCloseRefreshMode == 1 && closedConfirmedCount > 0)
   {
      bal = AccountInfoDouble(ACCOUNT_BALANCE);
      eq  = AccountInfoDouble(ACCOUNT_EQUITY);
      dailyDdPct = (InpDailyResetMode == 1)
         ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
         : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
      staticDdPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
      eqProfitPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      realizedProfitPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((bal - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      profitPct         = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;

      regime = "NORMAL";
      riskMult = ComputePhaseRiskMultiplier(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, regime);
      g_curDailyDdPct  = dailyDdPct;
      g_curStaticDdPct = staticDdPct;
      g_curProfitPct   = profitPct;
      g_curRegime      = regime;
      g_curRiskMult    = riskMult;
      if(MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE)
      {
         if(regime != g_prevLogRegime || MathAbs(riskMult - g_prevLogMult) > 1e-9)
         {
            string chgReason = StringFormat("POST_CLOSE_REFRESH|closed=%d|prev=%s@%.4f->%s@%.4f",
                                            closedConfirmedCount, g_prevLogRegime, g_prevLogMult, regime, riskMult);
            EmitTesterDecisionRow(nowUtc, "REGIME_OR_TAPER_CHANGE", "", 0, "", "", "",
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  bal, eq, AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0, 0, 0, 0.0, 0.0, 0, chgReason);
            g_prevLogRegime = regime;
            g_prevLogMult   = riskMult;
         }
      }
      if(dailyDdPct >= InpKillDailyDdPct || staticDdPct >= InpKillStaticDdPct)
      {
         if(!g_autoKillActive)
         {
            g_autoKillActive = true;
            PersistAutoKillStateM(g_dayKey, true);
            if(MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE)
            {
               string kWhy = (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD";
               EmitTesterDecisionRow(nowUtc, "KILL_ACTIVATED", "", 0, "", "", "",
                                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                     0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                     bal, eq, AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                     0, 0, 0, 0.0, 0.0, 0, kWhy);
            }
         }
      }
      effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
      if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
      if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";
   }

   // Collect and allocate intents ONLY when healthy, unlocked, and traded-day history hydrated (V101-02)
   if(!effectiveKill && g_signals.IsTradedDayHydrated())
   {
      NaqexSignalIntent intents[NAQEX_MAX_INTENTS];
      int nIntents = g_signals.CollectIntents(nowUtc, intents);
      datetime nyAncUtc = 0; double nyU100 = 0.0, nyU500 = 0.0;
      if(g_signals.ConsumeNyAnchorJustLocked(nyAncUtc, nyU100, nyU500) &&
         MQLInfoInteger(MQL_TESTER) && InpTesterEmitDecisionLog && g_testerLogHandle != INVALID_HANDLE)
      {
         EmitTesterDecisionRow(nyAncUtc, "NY_ANCHOR_LOCKED", "", 0, "", "US100.cash|US500.cash", "",
                               nyU100, nyU100, nyU500, 0.0, 0.0, 0.0,
                               0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_MARGIN_FREE),
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               0, 0, 0, 0.0, 0.0, 0,
                               StringFormat("us100_0930=%.5f|us500_0930=%.5f", nyU100, nyU500));
      }
      EmitOppTransitionsToLogs(nowUtc, AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_MARGIN_FREE));
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
   CNaqexPropGuard::ResetPendingCloseTable(g_pendingCloses);
   if(!g_signals.Init(InpSymUSDJPY, InpSymGBPUSD, InpSymEURJPY, InpSymUS100, InpSymUS500,
                      InpSymEURUSD, InpSymAUDUSD, InpSymUSDCAD, InpMaxBreakoutTickLagMs, InpEnableS6Shadow,
                      InpOpportunityLifecycleMode))
      return INIT_FAILED;
   g_guard.Init(g_trade, g_signals.SymbolAt(SYM_USDJPY), InpMagicRangeMin, InpKillDailyDdPct);
   OpenTesterDecisionLog();
   RestoreOrInitDayAnchorM();
   g_signals.HydrateTradedDaysFromHistory(g_guard.NowUTC());
   if(!MQLInfoInteger(MQL_TESTER))
   {
      if(InpOpportunityLifecycleMode == 1)
         g_signals.RestoreOppStateOnce();
      int loadedPending = 0;
      CNaqexPropGuard::LoadPendingCloseState(g_pendingCloses, loadedPending);
   }
   PrintFormat("[MASTER-7E-INIT] v1.01 sku=%s sizing=%d pl_mode=%d opp_mode=%d refresh_mode=%d shadow=%s dry_run=%s hydrated=%s login=%I64d",
               InpContractSku, InpSizingMode, InpProfitLockBasisMode, InpOpportunityLifecycleMode, InpPostCloseRefreshMode,
               InpShadowCompareMode ? "true" : "false",
               (InpDryRunLogOnly || InpGuardDryRunLogOnly) ? "true" : "false",
               g_signals.IsTradedDayHydrated() ? "true" : "false",
               CNaqexPropGuard::CurrentAccountLogin());
   EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1); // 1s live CopyTicksRange + reconciliation; 60s in Tester
   RunMasterCycle();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   CloseTesterDecisionLog();
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
   // Lightweight handler (queue limit = 1024): clear confirmed/rejected in-flight slots & mark reconciled fills (V101-05)
   if(trans.order == 0) return;
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD ||
      (trans.type == TRADE_TRANSACTION_ORDER_DELETE && trans.order_state != ORDER_STATE_FILLED))
   {
      for(int i = 0; i < NAQEX_MAX_INFLIGHT; i++)
      {
         if(g_inFlight[i].active && g_inFlight[i].order_ticket == trans.order)
         {
            if(trans.type == TRADE_TRANSACTION_DEAL_ADD && g_inFlight[i].unknown_state)
            {
               g_signals.MarkEngineTraded(g_inFlight[i].magic, g_inFlight[i].session_day_key);
               g_guard.LogExecAuditFor(g_inFlight[i].symbol, g_inFlight[i].is_buy ? "BUY" : "SELL",
                                       "ORDER_FILL_RECONCILED", trans.price, trans.price, trans.price_sl, trans.volume, 0.0, TRADE_RETCODE_DONE,
                                       StringFormat("intent=%s|deal=%I64u|ord=%I64u|pos=%I64u|TX_RECONCILED",
                                                    g_inFlight[i].intent_id, (ulong)trans.deal, (ulong)trans.order, (ulong)trans.position),
                                       g_inFlight[i].magic);
            }
            g_inFlight[i].active = false;
            break;
         }
      }
   }
}
