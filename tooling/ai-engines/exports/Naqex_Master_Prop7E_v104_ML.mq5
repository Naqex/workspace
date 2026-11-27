//+------------------------------------------------------------------+
//| Naqex_Master_Prop7E_v104_ML.mq5 (v1.04 — Shield C + ML Filter)   |
//| Clean superset of immutable Naqex_Master_Prop7E_v103.mq5         |
//| importing immutable Naqex_PropGuard.mqh & Naqex_Signals_7E.mqh   |
//| plus Wave 4 W4-G05 Naqex_ML_Filter_v104.mqh (w4_09_lgbm_tf_d2).  |
//|                                                                  |
//| Wave 4 ML Meta-Labeling Filter (ONNX + Exact Pure-MQL5 Fallback):|
//|   - Model: w4_09_lgbm_tf_d2_n60 (60 depth-2 LightGBM trees,      |
//|     zipmap=False, 0 ZipMap nodes, Python==ORT<=5.80e-8)          |
//|   - Exact 8 strictly causal features from closed past bars ONLY: |
//|     [0] d1_range_over_atr14      (closed D1 shift=1 / ATR14[1])  |
//|     [1] parkinson_vol_10d        (closed D1 shifts=1..10)        |
//|     [2] prev_bar_close_loc       (closed M1 shift=1 IBS)         |
//|     [3] hour_sin_utc             (sin(2*pi*(utc%86400)/86400))   |
//|     [4] hour_cos_utc             (cos(2*pi*(utc%86400)/86400))   |
//|     [5] engine_id_code           (E1=1..E7=7, S6=8)              |
//|     [6] same_dir_concurrent_count (open+inflight same side)      |
//|     [7] rolling_dd_pct_causal    (closed-balance drawdown %)     |
//|   - Fail-closed defaults: InpDryRunLogOnly=true,                 |
//|     InpGuardDryRunLogOnly=true, InpShadowCompareMode=true.       |
//+------------------------------------------------------------------+
#property strict
#property version     "1.04"
#property tester_file "naqex_red_news_utc.csv"
#property tester_file "naqex_v104_lgbm.onnx"

#include <Trade/Trade.mqh>

//--- Custom PropGuard Inputs (override immutable Naqex_PropGuard.mqh defaults cleanly)
#define NAQEX_CUSTOM_GUARD_INPUTS
input bool   InpGuardDryRunLogOnly          = true;       // SAFETY: true = log only, NO live OrderSend
input double InpGuardMaxDailyLossPct        = 3.50;       // Internal daily equity stop (< 5.0% firm hard limit)
input double InpGuardMaxSymbolRiskPct       = 1.75;       // Max concurrent open SL risk % per symbol (1.75 P1/P2, 1.25 Funded)
input bool   InpGuardUseOrchestrator        = false;      // Single-process Master EA authority (no legacy GV Orchestrator)
input double InpGuardMaxSpreadPoints        = 35.0;       // Default FX SpreadGuard cap (pts; 0 = disabled)
input int    InpGuardRolloverStartUTC       = 21;         // Rollover blackout start hour (UTC)
input int    InpGuardRolloverEndUTC         = 0;          // Rollover blackout end hour (UTC, exclusive; 0 = midnight)
input int    InpGuardEarlyCloseMin          = 10;         // Flatten N min before broker session close (holiday half-day guard)
input int    InpGuardTesterUtcOffsetH       = 2;          // Server UTC offset used ONLY inside MT5 Strategy Tester
input bool   InpGuardEnableRedNews          = true;       // Shield B3: Red-news guard ON across ALL phases (P1/P2/Funded)
input string InpGuardRedNewsCsvFile         = "naqex_red_news_utc.csv";
input int    InpGuardNewsPadSec             = 600;        // Shield B3: 600s = ±10m 6-CCY window (300s = ±5m; BoJ EST03UTC auto ±3600s)
input int    InpGuardNewsHardBanSec         = 135;        // 135s = ±2m15s hard no-execution ban (protects ±2m FTMO/The5ers rule)
input string InpGuardTcaAuditCsvFile        = "naqex_exec_audit.csv";
input long   InpGuardMagicRangeMin          = 20261120;
input long   InpGuardMagicRangeMax          = 20261199;

#include "Include/Naqex_PropGuard.mqh"
#include "Include/Naqex_Signals_7E.mqh"
#include "Include/Naqex_ML_Filter_v104.mqh"

//--- Safety & Mode Inputs (FAIL-CLOSED DEFAULTS)
input bool   InpDryRunLogOnly               = true;       // SAFETY: true = log only, NO live OrderSend
input bool   InpShadowCompareMode           = true;       // true = shadow-only compare alongside v1.03 (0 live orders)
input bool   InpEnableS6Shadow              = false;      // Optional S6_FX_USD_BSK shadow logging
input bool   InpWritePrimaryHeartbeat       = false;      // true ONLY when explicitly promoted to sole account authority

//--- Wave 4 W4-G05 ML Meta-Labeling Filter Inputs (w4_09_lgbm_tf_d2_n60)
input bool               InpEnableMLFilter  = true;                       // Enable Wave 4 LightGBM toxic-entry filter
input double             InpMLThreshold     = 0.457952;                   // Promoted Fold-4 q20 threshold (block if p < thr)
input ENUM_NAQEX_ML_MODE InpMLMode          = ONNX_OR_PURE_MQL5_FALLBACK; // Primary OnnxRun + automatic pure-MQL5 tree fallback
input string             InpMLOnnxFile      = "naqex_v104_lgbm.onnx";     // ONNX model in MQL5/Files (0 ZipMap nodes)

//--- Contract & Phase Inputs (C10_NEWS_ON + Shield C + ML v1.04 Defaults)
input string InpContractSku                 = "FTMO_STD_10K_V104_ML_SHIELD_C";
input double InpInitialBalanceUSD           = 10000.0;
input double InpTargetProfitPct             = 10.0;       // Phase target % (10% FTMO P1 / 5% P2 / 0% Funded)
input double InpHardDailyDdPct              = 5.00;       // Firm hard daily DD %
input double InpHardStaticDdPct             = 10.00;      // Firm hard static DD %
input int    InpDailyResetMode              = 1;          // 0=Server Midnight (The5ers), 1=Europe/Prague DST (FTMO), 2=UTC
input int    InpSizingMode                  = 0;          // 0=STATIC_PHASE_LOCK, 1=BARRIER_HEADROOM_MIN
input double InpBasePhaseMult               = 4.00;       // Phase risk mult (1.25 Funded / 3.50 P2 / 4.00 P1)
input double InpProfitLockPct               = 7.00;       // Profit % to step down to InpProfitLockMult (0 = disabled)
input double InpProfitLockMult              = 2.50;
input double InpAmberDdPct                  = 3.50;
input double InpAmberMult                   = 0.65;
input double InpRedDdPct                    = 6.00;
input double InpRedMult                     = 0.40;
input double InpKillDailyDdPct              = 3.50;
input double InpKillStaticDdPct             = 8.00;

//--- Shield A & Shield B1: Total Open-Account Risk + Per-Symbol + Directional Factor Cluster Caps
input double InpMaxTotalOpenRiskPct         = 3.00;       // Shield A: Hard total simultaneous open SL risk %
input double InpHardTotalOpenCeilingPct     = 3.00;       // Fail-closed absolute ceiling (never exceeds 3.00%)
input double InpMaxSymbolRiskPct            = 1.75;       // Per-symbol concurrent SL risk % cap
input double InpMaxUsdClusterPct            = 2.25;       // Shield B1: Max same-direction USD factor SL risk %
input double InpMaxJpyClusterPct            = 2.00;       // Shield B1: Max same-direction JPY factor SL risk %
input double InpMaxIdxClusterPct            = 1.75;       // Shield B1: Max US100/US500 index cluster SL risk %

//--- Shield B2 & B3: Real M1-Calibrated SpreadGuard + 6-CCY ±10m Red-News Option
input bool   InpEnableSpreadGuard           = true;       // Shield B2: Block entries during flash-crash liquidity vacuums
input double InpMaxUsdJpySpreadPoints       = 25.0;       // Causal Cluster-A (2018-2020) USDJPY cap
input double InpMaxGbpUsdSpreadPoints       = 35.0;       // Causal Cluster-A (2018-2020) GBPUSD cap
input double InpMaxEurJpySpreadPoints       = 25.0;       // Causal Cluster-A (2018-2020) EURJPY cap
input double InpMaxIndexSpreadPoints        = 350.0;      // FTMO-live broker-feed cap for US100/US500
input bool   InpUse6CcyNewsPad10m           = true;       // Shield B3: true requires InpGuardNewsPadSec >= 600s

//--- Multi-Symbol Broker Aliases & Telemetry
input string InpSymUSDJPY                   = "USDJPY";
input string InpSymGBPUSD                   = "GBPUSD";
input string InpSymEURJPY                   = "EURJPY";
input string InpSymUS100                    = "US100.cash";
input string InpSymUS500                    = "US500.cash";
input string InpSymEURUSD                   = "EURUSD";
input string InpSymAUDUSD                   = "AUDUSD";
input string InpSymUSDCAD                   = "USDCAD";
input int    InpMaxSlippagePointsFx         = 35;         // SetDeviationInPoints for FX pairs (pts)
input int    InpMaxSlippagePointsIdx        = 450;        // SetDeviationInPoints for US100/US500 (pts)
input int    InpMaxBreakoutTickLagMs        = 5000;
input int    InpHeartbeatSec                = 15;
input string InpHeartbeatFile               = "naqex_master_v104_ml_heartbeat.json";
input string InpShadowCsvFile               = "naqex_master_v104_ml_shadow.csv";
input int    InpProfitLockBasisMode         = 0;          // 0=Equity ProfitLock, 1=Realized Balance ProfitLock
input int    InpOpportunityLifecycleMode    = 1;          // 1=Stable opportunity_id + transition-only block logging
input int    InpPostCloseRefreshMode        = 1;          // 1=Refresh risk snapshot after confirmed close before CollectIntents
input bool   InpAllowManualHaltFile         = false;
input string InpManualHaltFile              = "naqex_manual_halt.flag";
input long   InpMagicRangeMin               = 20261120;
input long   InpMagicRangeMax               = 20261199;

//--- In-flight order ledger (atomic single-process memory, zero GV CAS races)
#define NAQEX_V104_MAX_INFLIGHT 32
struct NaqexV104InFlightOrder
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

CTrade                 g_trade;
CNaqexPropGuard        g_guard;
CNaqexSignals7E        g_signals;
CNaqexMLFilterV104     g_mlFilter;
NaqexV104InFlightOrder g_inFlight[NAQEX_V104_MAX_INFLIGHT];
NaqexPendingCloseEntry g_pendingCloses[NAQEX_MAX_PENDING_CLOSES];
int                    g_mlAtrHandles[NAQEX_SYM_COUNT];

int      g_dayKey            = -1;
double   g_dayAnchorEq       = 0.0;
double   g_dayAnchorBal      = 0.0;
double   g_mlPeakClosedBal   = 0.0;
bool     g_autoKillActive    = false;
bool     g_anchorUnrecovered = false;
datetime g_lastAnchorRetry   = 0;
datetime g_lastHydrateRetry  = 0;
datetime g_lastHbWrite       = 0;
long     g_lastTickLagMs     = 0;
long     g_maxTickLagMs      = 0;

//--- Effective Shield A hard total open-account risk cap (fail-closed: never exceeds 3.00%!)
double EffectiveTotalOpenRiskCapPctV104()
{
   double ceilPct = (InpHardTotalOpenCeilingPct > 0.0) ? MathMin(InpHardTotalOpenCeilingPct, 3.00) : 3.00;
   if(InpMaxTotalOpenRiskPct <= 0.0)
      return ceilPct;
   return MathMin(InpMaxTotalOpenRiskPct, ceilPct);
}

//--- Effective Shield B2 per-symbol SpreadGuard threshold (FTMO broker points)
double MaxSpreadCapForSymbolV104(const string sym)
{
   if(!InpEnableSpreadGuard)
      return 0.0;
   string u = sym;
   StringToUpper(u);
   if(StringFind(u, "US100") >= 0 || StringFind(u, "NAS100") >= 0 ||
      StringFind(u, "NDX")   >= 0 || StringFind(u, "USTEC")  >= 0 ||
      StringFind(u, "US500") >= 0 || StringFind(u, "SPX")    >= 0)
      return InpMaxIndexSpreadPoints;
   if(StringFind(u, "EURJPY") >= 0)
      return InpMaxEurJpySpreadPoints;
   if(StringFind(u, "USDJPY") >= 0)
      return InpMaxUsdJpySpreadPoints;
   if(StringFind(u, "GBPUSD") >= 0)
      return InpMaxGbpUsdSpreadPoints;
   return InpGuardMaxSpreadPoints;
}

bool IsDryRunFailClosedV104()
{
   return (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly);
}

int SymbolIndexForV104(const string sym)
{
   for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      if(g_signals.SymbolAt(s) == sym)
         return s;
   return -1;
}

//--- Strictly causal closed-bar D1 ATR(14) (shift=1 ONLY; zero shift=0 lookahead!)
bool ReadClosedD1AtrV104(const int symIdx, double &outAtr)
{
   outAtr = 0.0;
   if(symIdx < 0 || symIdx >= NAQEX_SYM_COUNT || g_mlAtrHandles[symIdx] == INVALID_HANDLE)
      return false;
   double buf[1];
   if(CopyBuffer(g_mlAtrHandles[symIdx], 0, 1, 1, buf) != 1)
      return false;
   if(!MathIsValidNumber(buf[0]) || buf[0] <= 0.0)
      return false;
   outAtr = buf[0];
   return true;
}

//--- Count currently open + active in-flight Naqex positions sharing candidate entry direction
int CountSameDirectionConcurrentV104(const bool isBuy)
{
   int cnt = 0;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
   {
      ulong ptk = PositionGetTicket(p);
      if(ptk == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool posIsBuy = (ptype == POSITION_TYPE_BUY);
      if(posIsBuy == isBuy)
         cnt++;
   }
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
   {
      if(g_inFlight[i].active && g_inFlight[i].is_buy == isBuy)
         cnt++;
   }
   return MathMin(100, cnt);
}

//--- Build the exact 8 strictly causal features for w4_09_lgbm_tf_d2_n60 (closed past bars ONLY!)
bool BuildCausalMLFeaturesV104(const NaqexSignalIntent &it, const double curBal, double &outFeat[])
{
   ArrayResize(outFeat, NAQEX_V104_ML_N_FEATURES);
   const double eps = 1e-12;
   int symIdx = SymbolIndexForV104(it.symbol);

   // [0] d1_range_over_atr14 = clip((High_D1[1] - Low_D1[1]) / ATR14_D1[1], 0.0, 15.0)
   double f0 = 1.0;
   double atr14 = 0.0;
   if(ReadClosedD1AtrV104(symIdx, atr14) && atr14 > eps)
   {
      double d1High = iHigh(it.symbol, PERIOD_D1, 1);
      double d1Low  = iLow(it.symbol, PERIOD_D1, 1);
      if(d1High > 0.0 && d1Low > 0.0 && d1High >= d1Low)
         f0 = (d1High - d1Low) / atr14;
   }
   f0 = MathMax(0.0, MathMin(15.0, f0));

   // [1] parkinson_vol_10d = clip(sqrt(mean_{s=1..cnt}(ln(max(H_s/L_s, 1))^2) / (4*ln(2))), 0.0, 1.0)
   double sumLogSq = 0.0;
   int parkCnt = 0;
   for(int s = 1; s <= 10; s++)
   {
      double hs = iHigh(it.symbol, PERIOD_D1, s);
      double ls = iLow(it.symbol, PERIOD_D1, s);
      if(hs > 0.0 && ls > 0.0 && hs >= ls)
      {
         double ratio = MathMax(hs / MathMax(ls, eps), 1.0);
         double lg = MathLog(ratio);
         sumLogSq += lg * lg;
         parkCnt++;
      }
   }
   double f1 = 0.0;
   if(parkCnt > 0)
   {
      double denom = 4.0 * MathLog(2.0) * (double)parkCnt;
      f1 = MathSqrt(MathMax(0.0, sumLogSq / denom));
   }
   f1 = MathMax(0.0, MathMin(1.0, f1));

   // [2] prev_bar_close_loc = clip((Close_M1[1] - Low_M1[1]) / (High_M1[1] - Low_M1[1]), 0.0, 1.0)
   double f2 = 0.5;
   double m1High  = iHigh(it.symbol, PERIOD_M1, 1);
   double m1Low   = iLow(it.symbol, PERIOD_M1, 1);
   double m1Close = iClose(it.symbol, PERIOD_M1, 1);
   double m1Rng   = m1High - m1Low;
   if(m1High > 0.0 && m1Low > 0.0 && m1Rng > eps)
      f2 = (m1Close - m1Low) / m1Rng;
   f2 = MathMax(0.0, MathMin(1.0, f2));

   // [3] hour_sin_utc & [4] hour_cos_utc from strictly causal entry UTC clock
   long secOfDay = (((long)it.signal_utc % 86400) + 86400) % 86400;
   double angleH = 2.0 * M_PI * ((double)secOfDay / 86400.0);
   double f3 = MathSin(angleH);
   double f4 = MathCos(angleH);

   // [5] engine_id_code (E1=1..E7=7, S6=8 matching ml_features_24.py ENGINE_ID_CODES)
   int eIdx = CNaqexSignals7E::EngineIndexFromMagic(it.magic);
   double f5 = (eIdx >= 0) ? (double)(eIdx + 1) : 0.0;

   // [6] same_dir_concurrent_count (open + active in-flight positions matching entry direction)
   double f6 = (double)CountSameDirectionConcurrentV104(it.is_buy);

   // [7] rolling_dd_pct_causal = clip(100 * (peakClosedBal - curBal) / peakClosedBal, 0.0, 100.0)
   if(curBal > g_mlPeakClosedBal)
      g_mlPeakClosedBal = curBal;
   double f7 = 0.0;
   if(g_mlPeakClosedBal > eps && curBal > 0.0)
      f7 = 100.0 * MathMax(0.0, (g_mlPeakClosedBal - curBal) / g_mlPeakClosedBal);
   f7 = MathMax(0.0, MathMin(100.0, f7));

   outFeat[0] = f0;
   outFeat[1] = f1;
   outFeat[2] = f2;
   outFeat[3] = f3;
   outFeat[4] = f4;
   outFeat[5] = f5;
   outFeat[6] = f6;
   outFeat[7] = f7;

   return CNaqexMLFilterV104::ValidateFeatures(outFeat);
}

int LastSundayOfMonthV104(const int year, const int month)
{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 31;
   TimeToStruct(StructToTime(d), d);
   return 31 - d.day_of_week;
}

int PragueUtcOffsetHoursV104(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 10) return 1;
   if(utc.mon > 3 && utc.mon < 10) return 2;
   int ls = LastSundayOfMonthV104(utc.year, utc.mon);
   if(utc.mon == 3) return (utc.day > ls || (utc.day == ls && utc.hour >= 1)) ? 2 : 1;
   return (utc.day < ls || (utc.day == ls && utc.hour < 1)) ? 2 : 1;
}

int PragueMidnightUtcOffsetHoursV104(const int year, const int month, const int day)
{
   if(month < 3 || month > 10) return 1;
   if(month > 3 && month < 10) return 2;
   int ls = LastSundayOfMonthV104(year, month);
   if(month == 3) return (day > ls) ? 2 : 1;
   return (day <= ls) ? 2 : 1;
}

int CurrentResetDayKeyV104()
{
   datetime refTs = 0;
   if(InpDailyResetMode == 0)
      refTs = CNaqexPropGuard::ServerNow();
   else if(InpDailyResetMode == 1)
   {
      datetime nowUtc = g_guard.NowUTC();
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      refTs = nowUtc + (datetime)(PragueUtcOffsetHoursV104(utc) * 3600);
   }
   else
      refTs = g_guard.NowUTC();
   MqlDateTime dt; TimeToStruct(refTs, dt);
   return dt.year * 1000 + dt.day_of_year;
}

datetime CurrentResetStartServerTimeV104()
{
   datetime srvNow = CNaqexPropGuard::ServerNow();
   if(InpDailyResetMode == 0) return srvNow - (srvNow % 86400);
   datetime nowUtc = g_guard.NowUTC();
   long srvMinusUtc = (long)srvNow - (long)nowUtc;
   if(InpDailyResetMode == 1)
   {
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      int curOff = PragueUtcOffsetHoursV104(utc) * 3600;
      datetime prgNow = nowUtc + (datetime)curOff;
      MqlDateTime prgDt; TimeToStruct(prgNow, prgDt);
      int midOff = PragueMidnightUtcOffsetHoursV104(prgDt.year, prgDt.mon, prgDt.day) * 3600;
      datetime prgMidUtc = (prgNow - (prgNow % 86400)) - (datetime)midOff;
      return prgMidUtc + (datetime)srvMinusUtc;
   }
   return (nowUtc - (nowUtc % 86400)) + (datetime)srvMinusUtc;
}

void PersistAutoKillStateV104(const int dayKey, const bool active)
{
   if(MQLInfoInteger(MQL_TESTER) || dayKey <= 0) return;
   GlobalVariableSet(CNaqexPropGuard::AcctDayKeyName(), (double)dayKey);
   GlobalVariableSet(CNaqexPropGuard::AcctAutoKillKey(), active ? 1.0 : 0.0);
}

bool IsAccountSyncedV104(const double bal, const double eq)
{
   if(!MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
      return false;
   return (bal > 0.0 && eq > 0.0);
}

void RestoreOrInitDayAnchorV104()
{
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsAccountSyncedV104(bal, eq)) return;
   if(bal > g_mlPeakClosedBal) g_mlPeakClosedBal = bal;
   datetime nowUtc = g_guard.NowUTC();
   int today = CurrentResetDayKeyV104();
   bool isNewDay = (today != g_dayKey);
   if(!isNewDay && g_dayAnchorEq > 0.0 && !g_anchorUnrecovered) return;
   if(!isNewDay && g_anchorUnrecovered && (nowUtc - g_lastAnchorRetry) < 15) return;
   g_lastAnchorRetry = nowUtc;

   double reconstructedBal = bal;
   double reconstructedEq  = (InpDailyResetMode == 1) ? bal : MathMax(bal, eq);
   g_anchorUnrecovered = false;
   if(!MQLInfoInteger(MQL_TESTER))
   {
      datetime resetStart = CurrentResetStartServerTimeV104();
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
   int prevDayKey = g_dayKey;
   g_dayKey       = today;
   g_dayAnchorBal = reconstructedBal;
   g_dayAnchorEq  = reconstructedEq;

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
         PersistAutoKillStateV104(today, false);
   }
   else if(isNewDay)
   {
      g_autoKillActive = false;
   }
}

int CountActiveInFlightV104()
{
   int n = 0;
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active) n++;
   return n;
}

void ReconcileInFlightOrdersV104(const datetime nowUtc)
{
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
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
      if((long)nowUtc - (long)g_inFlight[i].sent_utc > 120)
         g_inFlight[i].active = false;
   }
}

void RegisterInFlightV104(const NaqexSignalIntent &it, const double estRiskPct, const ulong ordTicket, const bool isUnknown)
{
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
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
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
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

bool HasOpenOrInFlightForMagicV104(const long magic)
{
   for(int p = PositionsTotal() - 1; p >= 0; p--)
      if(PositionGetTicket(p) > 0 && PositionGetInteger(POSITION_MAGIC) == magic)
         return true;
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].magic == magic)
         return true;
   return false;
}

double GetInFlightSymbolRiskV104(const string sym)
{
   double s = 0.0;
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].symbol == sym)
         s += g_inFlight[i].est_risk_pct;
   return s;
}

void GetInFlightFactorRisksV104(double &uL, double &uS, double &jL, double &jS, double &iL, double &iS, double &tot)
{
   uL = 0.0; uS = 0.0; jL = 0.0; jS = 0.0; iL = 0.0; iS = 0.0; tot = 0.0;
   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
      tot += g_inFlight[i].est_risk_pct;
      CNaqexPropGuard::AccumulateDirectionalFactor(g_inFlight[i].symbol, g_inFlight[i].is_buy, g_inFlight[i].est_risk_pct,
                                                   uL, uS, jL, jS, iL, iS);
   }
}

void LogMasterShadowRowV104(const NaqexSignalIntent &it, const string evType, const double riskPct,
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

double ComputePhaseRiskMultiplierV104(const double dailyDdPct, const double staticDdPct,
                                      const double eqProfitPct, const double realizedProfitPct,
                                      string &outRegime)
{
   double mult = InpBasePhaseMult;
   outRegime = "NORMAL";
   double effProfitPct = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;
   if(InpProfitLockBasisMode == 1)
   {
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

   double dailyHeadroom = MathMax(0.0, InpKillDailyDdPct - dailyDdPct);
   if(dailyHeadroom < 2.0)
   {
      double dailyScale = MathMax(0.25, dailyHeadroom / 2.0);
      mult = MathMin(mult, InpBasePhaseMult * dailyScale);
      if(outRegime == "NORMAL")
         outRegime = "DAILY_HEADROOM_TAPER";
   }

   if(InpSizingMode == 1)
   {
      double staticHeadroom = MathMax(0.0, InpKillStaticDdPct - staticDdPct);
      double ddScale = 1.0;
      if(staticHeadroom < 3.5) ddScale = MathMin(ddScale, MathMax(0.25, staticHeadroom / 3.5));
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

void WriteMasterHeartbeatV104(const datetime nowUtc, const double bal, const double eq,
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

   double uL = 0.0, uS = 0.0, jL = 0.0, jS = 0.0, iL = 0.0, iS = 0.0, totOpenPct = 0.0;
   if(posState == "CONFIRMED")
      totOpenPct = g_guard.ComputeAccountFactorRisk(uL, uS, jL, jS, iL, iS);

   int fh = FileOpen(fname, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh != INVALID_HANDLE)
   {
      string js = StringFormat(
         "{\"utc_ts\":%I64d,\"account_login\":%I64d,\"account_server\":\"%s\",\"build_version\":\"master-1.04-ml-shield-c\","
         "\"sku\":\"%s\",\"sizing_mode\":%d,\"shadow_compare\":%s,\"terminal_connected\":%s,\"quote_ts\":%I64d,"
         "\"positions_state\":\"%s\",\"anchor_state\":\"%s\","
         "\"balance\":%.2f,\"equity\":%.2f,\"day_anchor_eq\":%.2f,\"day_anchor_bal\":%.2f,"
         "\"daily_dd_pct\":%.3f,\"static_dd_pct\":%.3f,\"profit_pct\":%.3f,\"reset_mode\":%d,"
         "\"regime\":\"%s\",\"risk_mult\":%.3f,"
         "\"kill_switch\":%s,\"manual_halt\":%s,\"manual_halt_ack\":%s,"
         "\"open_positions\":%d,\"total_account_positions\":%d,\"pending_orders\":%d,\"in_flight_orders\":%d,"
         "\"orphan_no_sl\":%d,\"open_total_risk_pct\":%.3f,\"max_total_open_risk_pct\":%.2f,"
         "\"factor_usd_max_pct\":%.3f,\"factor_jpy_max_pct\":%.3f,\"factor_idx_max_pct\":%.3f,"
         "\"spread_guard_enabled\":%s,\"news_pad_sec\":%d,\"news_6ccy_10m\":%s,"
         "\"ml_enabled\":%s,\"ml_threshold\":%.6f,\"ml_onnx_ready\":%s,\"ml_backend\":\"%s\","
         "\"ml_passed\":%I64d,\"ml_blocked\":%I64d,"
         "\"last_tick_lag_ms\":%I64d,\"max_tick_lag_ms\":%I64d,\"dry_run\":%s}\n",
         (long)nowUtc, login, srv, InpContractSku, InpSizingMode,
         InpShadowCompareMode ? "true" : "false", termConn ? "true" : "false", quoteTs,
         posState, anchorState,
         bal, eq, g_dayAnchorEq, g_dayAnchorBal,
         dailyDdPct, staticDdPct, profitPct, InpDailyResetMode,
         regime, riskMult,
         effectiveKill ? "true" : "false", manualHalt ? "true" : "false", manualHalt ? "true" : "false",
         openCount, totalAcctPos, pendingCount, inFlightCount,
         orphanCount, (totOpenPct >= 900.0 ? -1.0 : totOpenPct), EffectiveTotalOpenRiskCapPctV104(),
         MathMax(uL, uS), MathMax(jL, jS), MathMax(iL, iS),
         InpEnableSpreadGuard ? "true" : "false", InpGuardNewsPadSec, InpUse6CcyNewsPad10m ? "true" : "false",
         InpEnableMLFilter ? "true" : "false", InpMLThreshold,
         g_mlFilter.IsOnnxReady() ? "true" : "false", g_mlFilter.LastBackend(),
         g_mlFilter.PassedCount(), g_mlFilter.BlockedCount(),
         g_lastTickLagMs, g_maxTickLagMs,
         IsDryRunFailClosedV104() ? "true" : "false"
      );
      FileWriteString(fh, js);
      FileClose(fh);
   }
}

int ClosePositionsByReasonV104(const datetime nowUtc, const bool flattenAll, const string globalReason)
{
   bool isDry = IsDryRunFailClosedV104();
   int closedConfirmedCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long pm = PositionGetInteger(POSITION_MAGIC);
      if(pm < InpMagicRangeMin || pm > InpMagicRangeMax) continue;
      string psym = PositionGetString(POSITION_SYMBOL);
      ulong pId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      string reason = "";
      if(flattenAll)
         reason = globalReason;
      else if(g_signals.ShouldClockFlattenMagic(pm, nowUtc, reason))
         {}
      else if(g_guard.IsNearBrokerSessionCloseFor(psym))
         reason = "HARD_FLAT_SESSION_CLOSE_SWAP0";
      else if(g_guard.IsInRedNewsPreFlattenWindowFor(psym))
         reason = "NEWS_PRE_FLATTEN_6CCY";
      if(reason == "") continue;
      if(!flattenAll && g_guard.IsInsideRedNewsHardBanFor(psym))
         continue;

      double pvol   = PositionGetDouble(POSITION_VOLUME);
      double volMin = SymbolInfoDouble(psym, SYMBOL_VOLUME_MIN);
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
   }
   return closedConfirmedCount;
}

void CancelPendingOrdersByReasonV104(const datetime nowUtc, const bool cancelAll, const string globalReason)
{
   bool isDry = IsDryRunFailClosedV104();
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
         reason = "NEWS_PRE_FLATTEN_6CCY";
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
         PrintFormat("[DRYRUN-V104-CANCEL] ord=%I64u magic=%I64d sym=%s vol=%.2f reason=%s", ot, om, osym, ovol, reason);
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

void ProcessIntentAtomicallyV104(const NaqexSignalIntent &it, const double riskMult)
{
   bool isShadowOrDry = (it.shadow_only || IsDryRunFailClosedV104());
   if(HasOpenOrInFlightForMagicV104(it.magic))
   {
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "OPEN_OR_INFLIGHT_POSITION:SKIP", blkCnt, evCnt);
      }
      return;
   }

   // Shield B3: 6-CCY Red-News window check (fail-closed if calendar missing/expired)
   if(g_guard.IsInsideRedNewsWindowFor(it.symbol))
   {
      string whyNews = StringFormat("RED_NEWS_6CCY_PAD_%ds", InpGuardNewsPadSec);
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "NEWS", "RED_NEWS_WINDOW:ORDER_BLOCKED_NEWS", blkCnt, evCnt);
         if(logTrans)
            LogMasterShadowRowV104(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      }
      else
         LogMasterShadowRowV104(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      return;
   }

   // Shield B2: Real M1-calibrated per-symbol SpreadGuard + rollover blackout
   double spreadCapPts = MaxSpreadCapForSymbolV104(it.symbol);
   if(!g_guard.IsSpreadAndSessionSafeFor(it.symbol, spreadCapPts))
   {
      double obsSpread = (double)SymbolInfoInteger(it.symbol, SYMBOL_SPREAD);
      string whySpr = StringFormat("SPREAD_GUARD|obs=%.1f|cap=%.1f", obsSpread, spreadCapPts);
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "SPREAD", "SPREAD_GUARD:ORDER_BLOCKED_SPREAD", blkCnt, evCnt);
         if(logTrans)
            LogMasterShadowRowV104(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
      }
      else
         LogMasterShadowRowV104(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
      return;
   }

   // Hard Stop-Loss validation + tick-grid normalization + broker STOPS_LEVEL guard
   double normSl = CNaqexPropGuard::NormalizePriceToTick(it.symbol, it.sl_price);
   double stopLoss = normSl;
   double slDist = MathAbs(it.signal_price - stopLoss);
   if(slDist <= 0.0 || stopLoss <= 0.0)
      return;

   double pt = SymbolInfoDouble(it.symbol, SYMBOL_POINT);
   long stopsLvl = SymbolInfoInteger(it.symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double liqPx = it.is_buy ? SymbolInfoDouble(it.symbol, SYMBOL_BID) : SymbolInfoDouble(it.symbol, SYMBOL_ASK);
   if(liqPx <= 0.0) liqPx = it.signal_price;
   double stopsGap = it.is_buy ? (liqPx - stopLoss) : (stopLoss - liqPx);
   if(pt > 0.0 && stopsLvl > 0 && stopsGap < (double)stopsLvl * pt)
   {
      LogMasterShadowRowV104(it, "ORDER_BLOCKED_STOPS", 0.0, 0.0, "SL_BELOW_BROKER_STOPS_LEVEL");
      return;
   }

   // Wave 4 W4-G05 ML Meta-Labeling Toxic-Entry Filter (strictly causal closed past bars ONLY!)
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double mlProb = 1.0;
   string mlBackend = "ML_DISABLED";
   if(InpEnableMLFilter)
   {
      double mlFeat[];
      bool featOk = BuildCausalMLFeaturesV104(it, bal, mlFeat);
      bool mlAllowed = featOk && g_mlFilter.ShouldAllowTrade(mlFeat, mlProb, mlBackend);
      if(!mlAllowed)
      {
         string whyMl = StringFormat("ML_TOXIC_FILTER|p=%.6f|thr=%.6f|backend=%s|feat_ok=%s",
                                     mlProb, InpMLThreshold, mlBackend, featOk ? "true" : "false");
         if(InpOpportunityLifecycleMode == 1)
         {
            int blkCnt = 0, evCnt = 0;
            bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "ML_TOXIC_FILTER:ORDER_BLOCKED_ML_TOXIC", blkCnt, evCnt);
            if(logTrans)
               LogMasterShadowRowV104(it, "ORDER_BLOCKED_ML_TOXIC", 0.0, 0.0, whyMl);
         }
         else
            LogMasterShadowRowV104(it, "ORDER_BLOCKED_ML_TOXIC", 0.0, 0.0, whyMl);
         // W4G05-F01: Lock out engine for this session (1-shot toxic filter; prevents late re-entry chases)
         g_signals.MarkEngineTraded(it.magic, it.session_day_key);
         return;
      }
   }

   // Shield A + Shield B1 atomic risk allocation
   double reqRiskPct = it.base_risk_pct * riskMult;
   double usedSymPct = g_guard.GetOpenSymbolRiskPctFor(it.symbol) + GetInFlightSymbolRiskV104(it.symbol);
   double symHeadroom = (InpMaxSymbolRiskPct > 0.0) ? MathMax(0.0, InpMaxSymbolRiskPct - usedSymPct) : 999.0;

   double fUL, fUS, fJL, fJS, fIL, fIS, fTot;
   GetInFlightFactorRisksV104(fUL, fUS, fJL, fJS, fIL, fIS, fTot);
   double effTotalOpenCap = EffectiveTotalOpenRiskCapPctV104();
   double factorAndTotalHeadroom = g_guard.ComputeFactorHeadroomPct(
      it.symbol, it.is_buy,
      InpMaxUsdClusterPct, InpMaxJpyClusterPct, InpMaxIdxClusterPct, effTotalOpenCap,
      fUL, fUS, fJL, fJS, fIL, fIS, fTot
   );

   double allowedRiskPct = MathMin(reqRiskPct, MathMin(symHeadroom, factorAndTotalHeadroom));
   if(allowedRiskPct <= 0.01)
   {
      string whyCap = (factorAndTotalHeadroom <= symHeadroom) ? "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP" : "ORDER_BLOCKED_SYMCAP";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "CAP", whyCap, blkCnt, evCnt);
         if(logTrans)
            LogMasterShadowRowV104(it, whyCap, reqRiskPct, 0.0,
                                   StringFormat("symRem=%.2f|facTotRem=%.2f|totCap=%.2f", symHeadroom, factorAndTotalHeadroom, effTotalOpenCap));
      }
      else
         LogMasterShadowRowV104(it, whyCap, reqRiskPct, 0.0,
                                StringFormat("symRem=%.2f|facTotRem=%.2f|totCap=%.2f", symHeadroom, factorAndTotalHeadroom, effTotalOpenCap));
      return;
   }

   // Conservative lot sizing (TICK_VALUE_LOSS + 5% cushion + fail-closed OrderCalcMargin <= 85%)
   double tickSize = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValLoss = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double tickValRaw  = SymbolInfoDouble(it.symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickVal  = (tickValLoss > 0.0) ? tickValLoss : tickValRaw;
   double volMin   = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MIN);
   double volMax   = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_MAX);
   double volStep  = SymbolInfoDouble(it.symbol, SYMBOL_VOLUME_STEP);
   if(bal <= 0.0 || tickSize <= 0.0 || tickVal <= 0.0 || volStep <= 0.0)
      return;

   double lossPerLot = (slDist / tickSize) * tickVal;
   if(lossPerLot <= 0.0)
      return;

   double riskMoney = bal * (allowedRiskPct / 100.0) * 0.95;
   double lots = CNaqexPropGuard::RoundVolumeDownToStep(riskMoney / lossPerLot, volStep, volMin, volMax);
   if(lots < volMin)
      return;

   ENUM_ORDER_TYPE ordType = it.is_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double reqMargin = 0.0;
   if(freeMargin <= 0.0 || !OrderCalcMargin(ordType, it.symbol, lots, it.signal_price, reqMargin) || reqMargin <= 0.0)
   {
      LogMasterShadowRowV104(it, "ORDER_BLOCKED_MARGIN", allowedRiskPct, 0.0, "FAIL_CLOSED_MARGIN_CHECK");
      return;
   }
   double maxAllowM = freeMargin * 0.85;
   if(reqMargin > maxAllowM)
   {
      lots = CNaqexPropGuard::RoundVolumeDownToStep(lots * (maxAllowM / reqMargin), volStep, volMin, volMax);
      if(lots < volMin)
         return;
   }

   // Fail-closed DryRun / ShadowCompare gate — ZERO OrderSend when armed in dry-run!
   if(isShadowOrDry)
   {
      string dryNote = StringFormat("%s|ml_p=%.6f|ml_be=%s", it.tag, mlProb, mlBackend);
      LogMasterShadowRowV104(it, it.shadow_only ? "SHADOW_INTENT" : "DRYRUN_SIGNAL_V104_ML", allowedRiskPct, lots, dryNote);
      g_signals.MarkEngineTraded(it.magic, it.session_day_key);
      return;
   }

   double actualRiskPct = (((slDist / tickSize) * tickVal * lots) / bal) * 100.0;
   double effectiveHeadroom = MathMin(symHeadroom, factorAndTotalHeadroom);
   if(actualRiskPct > effectiveHeadroom + 1e-6)
   {
      LogMasterShadowRowV104(it, "ORDER_BLOCKED_POST_ROUND_CAP", actualRiskPct, lots, "EXCEEDS_HEADROOM");
      return;
   }

   g_trade.SetExpertMagicNumber(it.magic);
   CNaqexPropGuard::ConfigureFillingMode(g_trade, it.symbol);
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
      RegisterInFlightV104(it, actualRiskPct, g_trade.ResultOrder(), true);
      g_guard.LogExecAuditFor(it.symbol, sideStr, "FILL_UNRESOLVED", it.signal_price, -1.0, normSl, lots, latMs, ret,
                              StringFormat("%s|v104ml|ml_p=%.4f|intent=%s|ord=%I64u|UNKNOWN_INFLIGHT",
                                           it.tag, mlProb, it.intent_id, (ulong)g_trade.ResultOrder()),
                              it.magic);
      return;
   }
   if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
   {
      g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_REJECT", it.signal_price, g_trade.ResultPrice(), normSl, lots, latMs, ret,
                              StringFormat("%s|v104ml|ml_p=%.4f|intent=%s|%s",
                                           it.tag, mlProb, it.intent_id, g_trade.ResultRetcodeDescription()),
                              it.magic);
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
      RegisterInFlightV104(it, actualRiskPct, ordId, false);

   double execLots = (g_trade.ResultVolume() > 0.0) ? g_trade.ResultVolume() : lots;
   double fillPx = g_guard.ResolveExecutedFillPrice(g_trade, it.symbol, -1.0);
   g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_FILL", it.signal_price, fillPx, normSl, execLots, latMs, ret,
                           StringFormat("%s|v104ml|ml_p=%.4f|ml_be=%s|intent=%s|deal=%I64u|ord=%I64u|tk=%I64u|pos=%I64u%s",
                                        it.tag, mlProb, mlBackend, it.intent_id, dealId, ordId, ordId, posId,
                                        (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : ""),
                           it.magic);
   g_signals.MarkEngineTraded(it.magic, it.session_day_key);
}

int ReconcilePendingClosesV104()
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

void RunMasterCycleV104()
{
   datetime nowUtc = g_guard.NowUTC();
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);

   if(!IsAccountSyncedV104(bal, eq))
   {
      WriteMasterHeartbeatV104(nowUtc, bal, eq, 0.0, 0.0, 0.0, "DISCONNECTED", 0.0, true, false,
                               "UNKNOWN", -1, -1, -1, CountActiveInFlightV104(), -1, "UNSYNCED");
      return;
   }

   if(bal > g_mlPeakClosedBal) g_mlPeakClosedBal = bal;
   RestoreOrInitDayAnchorV104();
   if(!g_signals.IsTradedDayHydrated() && (nowUtc - g_lastHydrateRetry) >= 5)
   {
      g_lastHydrateRetry = nowUtc;
      g_signals.HydrateTradedDaysFromHistory(nowUtc);
   }
   ReconcileInFlightOrdersV104(nowUtc);

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
   double riskMult = ComputePhaseRiskMultiplierV104(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, regime);

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
         PersistAutoKillStateV104(g_dayKey, true);
      }
   }
   bool effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
   if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
   if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";

   int closedConfirmedCount = 0;
   if(g_autoKillActive)
   {
      string killWhy = (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD";
      CancelPendingOrdersByReasonV104(nowUtc, true, killWhy);
      closedConfirmedCount = ClosePositionsByReasonV104(nowUtc, true, killWhy);
   }
   else if(manualFlatten)
   {
      CancelPendingOrdersByReasonV104(nowUtc, true, "MASTER_MANUAL_FLATTEN");
      closedConfirmedCount = ClosePositionsByReasonV104(nowUtc, true, "MASTER_MANUAL_FLATTEN");
   }
   else
   {
      CancelPendingOrdersByReasonV104(nowUtc, false, "");
      closedConfirmedCount = ClosePositionsByReasonV104(nowUtc, false, "");
   }
   closedConfirmedCount += ReconcilePendingClosesV104();

   if(InpPostCloseRefreshMode == 1 && closedConfirmedCount > 0)
   {
      bal = AccountInfoDouble(ACCOUNT_BALANCE);
      eq  = AccountInfoDouble(ACCOUNT_EQUITY);
      if(bal > g_mlPeakClosedBal) g_mlPeakClosedBal = bal;
      dailyDdPct = (InpDailyResetMode == 1)
         ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
         : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
      staticDdPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
      eqProfitPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      realizedProfitPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((bal - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      profitPct         = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;
      regime = "NORMAL";
      riskMult = ComputePhaseRiskMultiplierV104(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, regime);
      if(dailyDdPct >= InpKillDailyDdPct || staticDdPct >= InpKillStaticDdPct)
      {
         if(!g_autoKillActive)
         {
            g_autoKillActive = true;
            PersistAutoKillStateV104(g_dayKey, true);
         }
      }
      effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
      if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
      if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";
   }

   if(!effectiveKill && g_signals.IsTradedDayHydrated())
   {
      NaqexSignalIntent intents[NAQEX_MAX_INTENTS];
      int nIntents = g_signals.CollectIntents(nowUtc, intents);
      for(int i = 0; i < nIntents; i++)
         ProcessIntentAtomicallyV104(intents[i], riskMult);
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

   WriteMasterHeartbeatV104(nowUtc, bal, eq, dailyDdPct, staticDdPct, profitPct,
                            regime, riskMult, effectiveKill, manualHalt,
                            "CONFIRMED", openNaqex, totalPos, pendingCnt, CountActiveInFlightV104(), orphanCnt,
                            g_anchorUnrecovered ? "UNRECOVERED_AFTER_GAP" : "SYNCED");
}

int OnInit()
{
   // Fail-closed Shield A hard ceiling check
   if(InpHardTotalOpenCeilingPct <= 0.0 || InpHardTotalOpenCeilingPct > 3.00)
   {
      PrintFormat("[MASTER-V104-ERR] InpHardTotalOpenCeilingPct must be in (0.0, 3.00] (got %.2f)", InpHardTotalOpenCeilingPct);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Fail-closed Shield B3 parameter consistency checks
   if(InpGuardEnableRedNews && InpGuardNewsPadSec < InpGuardNewsHardBanSec)
   {
      PrintFormat("[MASTER-V104-ERR] InpGuardNewsPadSec (%d) must be >= InpGuardNewsHardBanSec (%d)",
                  InpGuardNewsPadSec, InpGuardNewsHardBanSec);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpGuardEnableRedNews && InpUse6CcyNewsPad10m && InpGuardNewsPadSec < 600)
   {
      PrintFormat("[MASTER-V104-ERR] InpUse6CcyNewsPad10m=true requires InpGuardNewsPadSec >= 600 (got %d)", InpGuardNewsPadSec);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Fail-closed ML threshold check
   if(InpEnableMLFilter && (!MathIsValidNumber(InpMLThreshold) || InpMLThreshold <= 0.0 || InpMLThreshold >= 1.0))
   {
      PrintFormat("[MASTER-V104-ERR] InpMLThreshold must be strictly inside (0, 1) (got %.6f)", InpMLThreshold);
      return INIT_PARAMETERS_INCORRECT;
   }

   for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++) g_inFlight[i].active = false;
   for(int s = 0; s < NAQEX_SYM_COUNT; s++) g_mlAtrHandles[s] = INVALID_HANDLE;
   CNaqexPropGuard::ResetPendingCloseTable(g_pendingCloses);

   if(!g_signals.Init(InpSymUSDJPY, InpSymGBPUSD, InpSymEURJPY, InpSymUS100, InpSymUS500,
                      InpSymEURUSD, InpSymAUDUSD, InpSymUSDCAD, InpMaxBreakoutTickLagMs, InpEnableS6Shadow,
                      InpOpportunityLifecycleMode))
      return INIT_FAILED;

   for(int s = 0; s < NAQEX_SYM_COUNT; s++)
   {
      g_mlAtrHandles[s] = iATR(g_signals.SymbolAt(s), PERIOD_D1, 14);
      if(g_mlAtrHandles[s] == INVALID_HANDLE)
      {
         PrintFormat("[MASTER-V104-ERR] ML D1 iATR handle failed for %s", g_signals.SymbolAt(s));
         return INIT_FAILED;
      }
   }

   if(InpEnableMLFilter)
   {
      if(!g_mlFilter.InitFromFile(InpMLOnnxFile, InpMLMode, InpMLThreshold))
      {
         PrintFormat("[MASTER-V104-ERR] ML filter init failed (mode=%d file=%s err=%d)",
                     (int)InpMLMode, InpMLOnnxFile, g_mlFilter.LastOnnxError());
         return INIT_FAILED;
      }
   }

   g_mlPeakClosedBal = MathMax(InpInitialBalanceUSD, AccountInfoDouble(ACCOUNT_BALANCE));
   g_guard.Init(g_trade, g_signals.SymbolAt(SYM_USDJPY), InpMagicRangeMin, InpKillDailyDdPct);
   RestoreOrInitDayAnchorV104();
   g_signals.HydrateTradedDaysFromHistory(g_guard.NowUTC());
   if(!MQLInfoInteger(MQL_TESTER))
   {
      if(InpOpportunityLifecycleMode == 1)
         g_signals.RestoreOppStateOnce();
      int loadedPending = 0;
      CNaqexPropGuard::LoadPendingCloseState(g_pendingCloses, loadedPending);
   }
   PrintFormat("[MASTER-V104-ML-INIT] sku=%s ml_enabled=%s ml_thr=%.6f ml_onnx_ready=%s ml_backend=%s tot_open_cap=%.2f%% dry_run=%s",
               InpContractSku, InpEnableMLFilter ? "true" : "false", InpMLThreshold,
               g_mlFilter.IsOnnxReady() ? "true" : "false", g_mlFilter.LastBackend(),
               EffectiveTotalOpenRiskCapPctV104(), IsDryRunFailClosedV104() ? "true" : "false");
   EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1);
   RunMasterCycleV104();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   g_mlFilter.Deinit();
   for(int s = 0; s < NAQEX_SYM_COUNT; s++)
   {
      if(g_mlAtrHandles[s] != INVALID_HANDLE)
      {
         IndicatorRelease(g_mlAtrHandles[s]);
         g_mlAtrHandles[s] = INVALID_HANDLE;
      }
   }
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
   RunMasterCycleV104();
}

void OnTimer()
{
   RunMasterCycleV104();
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.order == 0) return;
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD ||
      (trans.type == TRADE_TRANSACTION_ORDER_DELETE && trans.order_state != ORDER_STATE_FILLED))
   {
      for(int i = 0; i < NAQEX_V104_MAX_INFLIGHT; i++)
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
