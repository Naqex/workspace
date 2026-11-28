//+------------------------------------------------------------------+
//| Naqex_Master_Modular_v105.mq5 (Wave 5 W5-G10 / W5-G12 / W5-G15)  |
//| Modular 16-Slot Master EA integrating:                           |
//|   - Immutable Naqex_PropGuard.mqh (Shield A/B1/B2/B3 + TCA)      |
//|   - Immutable Naqex_Signals_7E.mqh (7 core engines, 0 edits)     |
//|   - Modular Naqex_EngineSlotRegistry.mqh (16 slots + EUR/GBP/AUD)|
//|   - Aligned Naqex_ML_Filter_v105.mqh (W4-RT1-P1-01 closure,      |
//|     ONNX CPU EP zipmap=False + Exact Pure-MQL5 + Shadow1x DD)    |
//|   - Anti-Martingale 6-tier Bellman DP risk schedule (W5-G13)     |
//|                                                                  |
//| Clean Mode Switches:                                             |
//|   1. 7E-Compat Mode (InpUseV105ML=false, InpUseBellmanDP=false): |
//|      Reproduces Naqex_Master_Prop7E_v103.mq5 to the exact cent.  |
//|   2. v1.05-ML ONNX (InpUseV105ML=true, InpMLUseOnnx=true) and    |
//|      v1.05-ML Pure-MQL5 (InpMLUseOnnx=false), with 1-shot        |
//|      MarkEngineTraded() on !mlAllowed (closes W4G05-F01).        |
//|   3. Tester-only live feature dump (InpDumpMLFeaturesCsv=true,   |
//|      active ONLY inside MQL_TESTER) for <=1e-4 Python parity.    |
//|   4. Bellman DP 6-tier anti-martingale P1/P2 schedule            |
//|      (InpUseBellmanDP=true, Shield A <= 3.00% enforced).         |
//|   5. Fail-closed defaults: InpDryRunLogOnly=true,                |
//|      InpGuardDryRunLogOnly=true, InpShadowCompareMode=true.      |
//+------------------------------------------------------------------+
#property strict
#property version     "1.05"
#property tester_file "naqex_red_news_utc.csv"
#property tester_file "naqex_v105_lgbm.onnx"

#include <Trade/Trade.mqh>

//--- Custom PropGuard Inputs (override immutable Naqex_PropGuard.mqh defaults cleanly)
#define NAQEX_CUSTOM_GUARD_INPUTS
input bool   InpGuardDryRunLogOnly          = true;       // SAFETY: true = log only, NO live OrderSend
input double InpGuardMaxDailyLossPct        = 3.50;       // Internal daily equity stop (< 5.0% firm hard limit)
input double InpGuardMaxSymbolRiskPct       = 1.75;       // Max concurrent open SL risk % per symbol
input bool   InpGuardUseOrchestrator        = false;      // Single-process Master EA authority
input double InpGuardMaxSpreadPoints        = 35.0;       // Default FX SpreadGuard cap (pts; 0 = disabled)
input int    InpGuardRolloverStartUTC       = 21;         // Rollover blackout start hour (UTC)
input int    InpGuardRolloverEndUTC         = 0;          // Rollover blackout end hour (UTC, exclusive; 0 = midnight)
input int    InpGuardEarlyCloseMin          = 10;         // Flatten N min before broker session close
input int    InpGuardTesterUtcOffsetH       = 2;          // Server UTC offset used ONLY inside MT5 Strategy Tester
input bool   InpGuardEnableRedNews          = true;       // Shield B3: Red-news guard ON across ALL phases
input string InpGuardRedNewsCsvFile         = "naqex_red_news_utc.csv";
input int    InpGuardNewsPadSec             = 600;        // Shield B3: 600s = +/-10m 6-CCY window
input int    InpGuardNewsHardBanSec         = 135;        // 135s = +/-2m15s hard no-execution ban
input string InpGuardTcaAuditCsvFile        = "naqex_exec_audit.csv";
input long   InpGuardMagicRangeMin          = 20261120;
input long   InpGuardMagicRangeMax          = 20261199;

#include "Include/Naqex_PropGuard.mqh"
#include "Include/Naqex_Signals_7E.mqh"
#include "Include/Naqex_EngineSlotRegistry.mqh"
#include "Include/Naqex_ML_Filter_v105.mqh"

//--- Safety & Mode Inputs (FAIL-CLOSED DEFAULTS)
input bool   InpDryRunLogOnly               = true;       // SAFETY: true = log only, NO live OrderSend
input bool   InpShadowCompareMode           = true;       // true = shadow-only compare (0 live orders)
input bool   InpEnableS6Shadow              = false;      // Optional S6_FX_USD_BSK shadow logging
input bool   InpWritePrimaryHeartbeat       = false;      // true ONLY when promoted to sole account authority

//--- Wave 5 v1.05-ML Filter Inputs (W5-G10 / W5-G12)
input bool   InpUseV105ML                   = false;      // false = 7E-Compat mode; true = v1.05-ML toxic filter
input bool   InpMLUseOnnx                   = true;       // true = ONNX CPU EP (+fallback); false = Pure-MQL5 trees only
input bool   InpMLFailClosedOnnxOnly        = false;      // true = require OnnxRun without fallback (when InpMLUseOnnx=true)
input double InpMLThreshold                 = NAQEX_V105_ML_DEFAULT_THRESHOLD; // Fold-4 q20 threshold (0.448872)
input string InpMLOnnxFile                  = NAQEX_V105_ML_ONNX_FILE_DEFAULT; // ONNX model in MQL5/Files
input bool   InpDumpMLFeaturesCsv           = false;      // TESTER ONLY: dump live OnTick() features + p_win to CSV
input string InpDumpMLFeaturesFile          = "wave5_mt5_live_features_2024.csv";

//--- Wave 5 Bellman DP 6-Tier Anti-Martingale Schedule Inputs (W5-G13)
input bool   InpUseBellmanDP                = false;      // false = 7E-Compat static/barrier mult; true = 6-tier Bellman DP
input int    InpBellmanDPPhase              = 1;          // 1 = P1 (10% target), 2 = P2 (5% target)
input string InpBellmanDPScheduleFile       = "";         // Optional CSV schedule override in MQL5/Files (empty = built-in SSOT)

//--- Modular 16-Slot Core 7E Weight Controls (1.0=ACTIVE, 0.5=HALVED, 0.0=RETIRED)
input double InpSlot0Weight                 = 1.00;       // Slot 0: E1_USDJPY_TOKYO
input double InpSlot1Weight                 = 1.00;       // Slot 1: E2_USDJPY_EXP80
input double InpSlot2Weight                 = 1.00;       // Slot 2: E3_GBPUSD_VH
input double InpSlot3Weight                 = 1.00;       // Slot 3: E4_US100_SESS40
input double InpSlot4Weight                 = 1.00;       // Slot 4: E5_US100_RS1130
input double InpSlot5Weight                 = 1.00;       // Slot 5: E6_EURJPY_VOLCOMP
input double InpSlot6Weight                 = 1.00;       // Slot 6: E7_USDJPY_NY10ET

//--- Contract & Phase Inputs (Compatible 1:1 with FTMO_Std10K_v103_*.set)
input string InpContractSku                 = "FTMO_STD_10K_V105_MODULAR";
input double InpInitialBalanceUSD           = 10000.0;
input double InpTargetProfitPct             = 10.0;       // Phase target % (10% P1 / 5% P2 / 0% Funded)
input double InpHardDailyDdPct              = 5.00;       // Firm hard daily DD %
input double InpHardStaticDdPct             = 10.00;      // Firm hard static DD %
input int    InpDailyResetMode              = 1;          // 0=Server Midnight, 1=Europe/Prague DST (FTMO), 2=UTC
input int    InpSizingMode                  = 0;          // 0=STATIC_PHASE_LOCK, 1=BARRIER_HEADROOM_MIN
input double InpBasePhaseMult               = 4.00;       // Phase risk mult (1.0/1.25 Funded / 3.50 P2 / 4.00 P1)
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
input double InpMaxEurClusterPct            = 2.00;       // P2-3: Max same-direction EUR cluster SL risk % (0 = disabled)
input double InpMaxGbpClusterPct            = 2.00;       // P2-3: Max same-direction GBP cluster SL risk % (0 = disabled)
input double InpMaxAudClusterPct            = 2.00;       // P2-3: Max same-direction AUD cluster SL risk % (0 = disabled)

//--- Shield B2 & B3: Real M1-Calibrated SpreadGuard + 6-CCY +/-10m Red-News Option
input bool   InpEnableSpreadGuard           = true;       // Shield B2: Block entries during liquidity vacuums
input double InpMaxUsdJpySpreadPoints       = 25.0;
input double InpMaxGbpUsdSpreadPoints       = 35.0;
input double InpMaxEurJpySpreadPoints       = 25.0;
input double InpMaxIndexSpreadPoints        = 350.0;
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
input int    InpMaxSlippagePointsFx         = 35;
input int    InpMaxSlippagePointsIdx        = 450;
input int    InpMaxBreakoutTickLagMs        = 5000;
input int    InpHeartbeatSec                = 15;
input string InpHeartbeatFile               = "naqex_master_v105_modular_heartbeat.json";
input string InpShadowCsvFile               = "naqex_master_v105_modular_shadow.csv";
input int    InpProfitLockBasisMode         = 0;          // 0=Equity ProfitLock, 1=Realized Balance ProfitLock
input int    InpOpportunityLifecycleMode    = 1;          // 1=Stable opportunity_id + transition-only block logging
input int    InpPostCloseRefreshMode        = 1;          // 1=Refresh risk snapshot after confirmed close before CollectIntents
input bool   InpAllowManualHaltFile         = false;
input string InpManualHaltFile              = "naqex_manual_halt.flag";
input long   InpMagicRangeMin               = 20261120;
input long   InpMagicRangeMax               = 20261199;

//--- In-flight order ledger
#define NAQEX_V105_MAX_INFLIGHT 32
struct NaqexV105InFlightOrder
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

//--- Open position Shadow1x closed-R tracker ledger (exact init_risk_usd for phase-invariant net_R)
#define NAQEX_V105_MAX_SHADOW_POS 32
struct NaqexV105ShadowPosTrack
{
   bool   active;
   ulong  pos_id;
   long   magic;
   string symbol;
   bool   is_buy;
   double entry_price;
   double lots;
   double init_risk_usd;
};

//--- Bellman DP 6-tier anti-martingale risk schedule entry (W5-G13)
#define NAQEX_V105_MAX_DP_TIERS 6
struct NaqexBellmanDPTier
{
   int    tier_rank;
   string tier_id;
   double eq_min_pct;
   double eq_max_pct;
   double dd_min_pct;
   double dd_max_pct;
   double risk_mult;
};

CTrade                    g_trade;
CNaqexPropGuard           g_guard;
CNaqexSignals7E           g_signals;
CNaqexEngineSlotRegistry  g_registry;
CNaqexMLFilterV105        g_mlFilter;
NaqexV105InFlightOrder    g_inFlight[NAQEX_V105_MAX_INFLIGHT];
NaqexPendingCloseEntry    g_pendingCloses[NAQEX_MAX_PENDING_CLOSES];
NaqexV105ShadowPosTrack   g_shadowPos[NAQEX_V105_MAX_SHADOW_POS];
NaqexBellmanDPTier        g_dpTiers[NAQEX_V105_MAX_DP_TIERS];
int                       g_dpTierCount = 0;
int                       g_mlAtrHandles[NAQEX_SYM_COUNT];

int      g_dayKey            = -1;
double   g_dayAnchorEq       = 0.0;
double   g_dayAnchorBal      = 0.0;
double   g_peakEquity        = 0.0;
bool     g_autoKillActive    = false;
bool     g_anchorUnrecovered = false;
datetime g_lastAnchorRetry   = 0;
datetime g_lastHydrateRetry  = 0;
datetime g_lastHbWrite       = 0;
long     g_lastTickLagMs     = 0;
long     g_maxTickLagMs      = 0;
int      g_featDumpFh        = INVALID_HANDLE;
long     g_featDumpSeq       = 0;
datetime g_lastTesterSec     = 0;

//--- Effective Shield A hard total open-account risk cap (fail-closed: never exceeds 3.00%!)
double EffectiveTotalOpenRiskCapPctV105()
{
   return CNaqexEngineSlotRegistry::EnforceShieldACapPct(InpMaxTotalOpenRiskPct, InpHardTotalOpenCeilingPct);
}

//--- Effective Shield B2 per-symbol SpreadGuard threshold (FTMO broker points)
double MaxSpreadCapForSymbolV105(const string sym)
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

bool IsDryRunFailClosedV105()
{
   return (InpDryRunLogOnly || InpShadowCompareMode || InpGuardDryRunLogOnly);
}

int SymbolIndexForV105(const string sym)
{
   for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      if(g_signals.SymbolAt(s) == sym)
         return s;
   return -1;
}

//--- Load built-in or CSV-overridden 6-tier Anti-Martingale Bellman DP schedule (matches bellman_dp_schedule.json!)
bool LoadBellmanDPScheduleV105()
{
   g_dpTierCount = 0;
   if(InpBellmanDPScheduleFile != "")
   {
      int fh = FileOpen(InpBellmanDPScheduleFile, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
      if(fh == INVALID_HANDLE)
      {
         PrintFormat("[MASTER-V105-ERR] Failed to open Bellman DP CSV '%s' err=%d", InpBellmanDPScheduleFile, GetLastError());
         return false;
      }
      bool first = true;
      while(!FileIsEnding(fh) && g_dpTierCount < NAQEX_V105_MAX_DP_TIERS)
      {
         string line = FileReadString(fh);
         StringTrimLeft(line);
         StringTrimRight(line);
         if(line == "") continue;
         if(first)
         {
            first = false;
            if(StringFind(line, "tier_rank") == 0) continue;
         }
         string cols[];
         if(StringSplit(line, ',', cols) < 7) continue;
         double rm = StringToDouble(cols[6]);
         if(!MathIsValidNumber(rm) || rm < 0.0 || rm > 4.50)
         {
            FileClose(fh);
            PrintFormat("[MASTER-V105-ERR] Invalid Bellman DP tier mult=%.3f", rm);
            return false;
         }
         g_dpTiers[g_dpTierCount].tier_rank  = (int)StringToInteger(cols[0]);
         g_dpTiers[g_dpTierCount].tier_id    = cols[1];
         g_dpTiers[g_dpTierCount].eq_min_pct = StringToDouble(cols[2]);
         g_dpTiers[g_dpTierCount].eq_max_pct = StringToDouble(cols[3]);
         g_dpTiers[g_dpTierCount].dd_min_pct = StringToDouble(cols[4]);
         g_dpTiers[g_dpTierCount].dd_max_pct = StringToDouble(cols[5]);
         g_dpTiers[g_dpTierCount].risk_mult  = rm;
         g_dpTierCount++;
      }
      FileClose(fh);
      return (g_dpTierCount > 0 && g_dpTierCount <= NAQEX_V105_MAX_DP_TIERS);
   }

   if(InpBellmanDPPhase == 2)
   {
      // Canonical Wave 5 P2 6-tier anti-martingale schedule (bellman_dp_schedule.json)
      g_dpTiers[0].tier_rank = 1; g_dpTiers[0].tier_id = "P2_T1_HOUSE_MONEY_CRUISE"; g_dpTiers[0].eq_min_pct =  2.25; g_dpTiers[0].eq_max_pct =  3.9999; g_dpTiers[0].dd_min_pct = 0.0; g_dpTiers[0].dd_max_pct = 10.0; g_dpTiers[0].risk_mult = 2.0;
      g_dpTiers[1].tier_rank = 2; g_dpTiers[1].tier_id = "P2_T2_FINISH_LINE_TAPER";  g_dpTiers[1].eq_min_pct =  4.00; g_dpTiers[1].eq_max_pct = 100.00;  g_dpTiers[1].dd_min_pct = 0.0; g_dpTiers[1].dd_max_pct = 10.0; g_dpTiers[1].risk_mult = 2.0;
      g_dpTiers[2].tier_rank = 3; g_dpTiers[2].tier_id = "P2_T3_NORMAL_BASE";        g_dpTiers[2].eq_min_pct = -1.50; g_dpTiers[2].eq_max_pct =  2.2499; g_dpTiers[2].dd_min_pct = 0.0; g_dpTiers[2].dd_max_pct = 10.0; g_dpTiers[2].risk_mult = 2.0;
      g_dpTiers[3].tier_rank = 4; g_dpTiers[3].tier_id = "P2_T4_SHALLOW_LOSS_BRAKE"; g_dpTiers[3].eq_min_pct = -4.50; g_dpTiers[3].eq_max_pct = -1.5001; g_dpTiers[3].dd_min_pct = 0.0; g_dpTiers[3].dd_max_pct = 10.0; g_dpTiers[3].risk_mult = 1.5;
      g_dpTiers[4].tier_rank = 5; g_dpTiers[4].tier_id = "P2_T5_AMBER_LOSS_BRAKE";   g_dpTiers[4].eq_min_pct = -6.50; g_dpTiers[4].eq_max_pct = -4.5001; g_dpTiers[4].dd_min_pct = 0.0; g_dpTiers[4].dd_max_pct = 10.0; g_dpTiers[4].risk_mult = 1.0;
      g_dpTiers[5].tier_rank = 6; g_dpTiers[5].tier_id = "P2_T6_RED_SURVIVAL_FLOOR"; g_dpTiers[5].eq_min_pct = -100.0; g_dpTiers[5].eq_max_pct = -6.5001; g_dpTiers[5].dd_min_pct = 0.0; g_dpTiers[5].dd_max_pct = 10.0; g_dpTiers[5].risk_mult = 0.5;
      g_dpTierCount = 6;
      return true;
   }

   // Canonical Wave 5 P1 6-tier anti-martingale schedule (bellman_dp_schedule.json)
   g_dpTiers[0].tier_rank = 1; g_dpTiers[0].tier_id = "P1_T1_HOUSE_MONEY_CRUISE"; g_dpTiers[0].eq_min_pct =  4.50; g_dpTiers[0].eq_max_pct =  7.9999; g_dpTiers[0].dd_min_pct = 0.0; g_dpTiers[0].dd_max_pct = 10.0; g_dpTiers[0].risk_mult = 3.0;
   g_dpTiers[1].tier_rank = 2; g_dpTiers[1].tier_id = "P1_T2_FINISH_LINE_TAPER";  g_dpTiers[1].eq_min_pct =  8.00; g_dpTiers[1].eq_max_pct = 100.00;  g_dpTiers[1].dd_min_pct = 0.0; g_dpTiers[1].dd_max_pct = 10.0; g_dpTiers[1].risk_mult = 2.0;
   g_dpTiers[2].tier_rank = 3; g_dpTiers[2].tier_id = "P1_T3_NORMAL_BASE";        g_dpTiers[2].eq_min_pct = -1.50; g_dpTiers[2].eq_max_pct =  4.4999; g_dpTiers[2].dd_min_pct = 0.0; g_dpTiers[2].dd_max_pct = 10.0; g_dpTiers[2].risk_mult = 2.5;
   g_dpTiers[3].tier_rank = 4; g_dpTiers[3].tier_id = "P1_T4_SHALLOW_LOSS_BRAKE"; g_dpTiers[3].eq_min_pct = -4.50; g_dpTiers[3].eq_max_pct = -1.5001; g_dpTiers[3].dd_min_pct = 0.0; g_dpTiers[3].dd_max_pct = 10.0; g_dpTiers[3].risk_mult = 2.0;
   g_dpTiers[4].tier_rank = 5; g_dpTiers[4].tier_id = "P1_T5_AMBER_LOSS_BRAKE";   g_dpTiers[4].eq_min_pct = -6.50; g_dpTiers[4].eq_max_pct = -4.5001; g_dpTiers[4].dd_min_pct = 0.0; g_dpTiers[4].dd_max_pct = 10.0; g_dpTiers[4].risk_mult = 1.0;
   g_dpTiers[5].tier_rank = 6; g_dpTiers[5].tier_id = "P1_T6_RED_SURVIVAL_FLOOR"; g_dpTiers[5].eq_min_pct = -100.0; g_dpTiers[5].eq_max_pct = -6.5001; g_dpTiers[5].dd_min_pct = 0.0; g_dpTiers[5].dd_max_pct = 10.0; g_dpTiers[5].risk_mult = 0.5;
   g_dpTierCount = 6;
   return true;
}

//--- Evaluate 6-tier anti-martingale Bellman DP schedule (MIN_OF_MATCHING_TIERS_DEFENSIVE_INTERSECTION)
double EvaluateBellmanDPRiskMultV105(const double signedEqPct, const double ddFromPeakPct, const double dailyDdPct, string &outRegime)
{
   double matchedMult = 1e9;
   string matchedId   = "DP_SURVIVAL_FALLBACK";
   bool   anyMatch    = false;
   double safestMult  = 0.5;
   string safestId    = "DP_SURVIVAL_FALLBACK";

   if(g_dpTierCount > 0)
   {
      safestMult = g_dpTiers[0].risk_mult;
      safestId   = g_dpTiers[0].tier_id;
   }
   for(int i = 0; i < g_dpTierCount; i++)
   {
      if(g_dpTiers[i].risk_mult < safestMult)
      {
         safestMult = g_dpTiers[i].risk_mult;
         safestId   = g_dpTiers[i].tier_id;
      }
      bool eqIn = (signedEqPct >= g_dpTiers[i].eq_min_pct - 1e-9 && signedEqPct <= g_dpTiers[i].eq_max_pct + 1e-9);
      bool ddIn = (ddFromPeakPct >= g_dpTiers[i].dd_min_pct - 1e-9 && ddFromPeakPct <= g_dpTiers[i].dd_max_pct + 1e-9);
      if(eqIn && ddIn)
      {
         if(!anyMatch || g_dpTiers[i].risk_mult < matchedMult)
         {
            matchedMult = g_dpTiers[i].risk_mult;
            matchedId   = g_dpTiers[i].tier_id;
            anyMatch    = true;
         }
      }
   }

   double mult = anyMatch ? matchedMult : safestMult;
   outRegime   = anyMatch ? matchedId   : safestId;

   // Daily headroom anti-breach safety taper
   double dailyHeadroom = MathMax(0.0, InpKillDailyDdPct - dailyDdPct);
   if(dailyHeadroom < 2.0)
   {
      double dailyScale = MathMax(0.25, dailyHeadroom / 2.0);
      double tapered    = mult * dailyScale;
      if(tapered < mult)
      {
         mult = tapered;
         outRegime = outRegime + "+DAILY_TAPER";
      }
   }
   return MathMax(0.0, mult);
}

//--- Count currently open + active in-flight Naqex positions sharing candidate entry direction
int CountSameDirectionConcurrentV105(const bool isBuy)
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
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
   {
      if(g_inFlight[i].active && g_inFlight[i].is_buy == isBuy)
         cnt++;
   }
   return MathMin(100, cnt);
}

//--- Live-quote tick value in USD for Shadow1x closed-R (avoids MT5 Tester stale TICK_VALUE_LOSS cache)
double ComputeLiveShadowTickValueLossV105(const string sym)
{
   double tickSize     = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double contractSize = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   string profitCcy    = SymbolInfoString(sym, SYMBOL_CURRENCY_PROFIT);
   StringToUpper(profitCcy);
   if(tickSize > 0.0 && contractSize > 0.0)
   {
      if(profitCcy == "USD")
         return tickSize * contractSize;
      if(profitCcy == "JPY")
      {
         double ujBid = SymbolInfoDouble(g_signals.SymbolAt(SYM_USDJPY), SYMBOL_BID);
         if(ujBid > 0.0)
            return (tickSize * contractSize) / ujBid;
      }
      if(profitCcy == "CAD")
      {
         double ucBid = SymbolInfoDouble(g_signals.SymbolAt(SYM_USDCAD), SYMBOL_BID);
         if(ucBid > 0.0)
            return (tickSize * contractSize) / ucBid;
      }
   }
   double tvLoss = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double tvRaw  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   return (tvLoss > 0.0) ? tvLoss : tvRaw;
}

double RoundCentHalfAwayV105(const double x)
{
   return (x >= 0.0) ? (MathFloor(x * 100.0 + 0.5) / 100.0)
                     : (-MathFloor((-x) * 100.0 + 0.5) / 100.0);
}

//--- Track newly opened position for exact phase-invariant Shadow1x closed-R calculation
void RegisterShadowPositionOpenV105(const ulong posId,
                                    const long magic,
                                    const string sym,
                                    const bool isBuy,
                                    const double entryPrice,
                                    const double lots,
                                    const double initRiskUsd)
{
   if(posId == 0 || !MathIsValidNumber(initRiskUsd) || initRiskUsd <= 1e-12)
      return;
   for(int i = 0; i < NAQEX_V105_MAX_SHADOW_POS; i++)
   {
      if(g_shadowPos[i].active && g_shadowPos[i].pos_id == posId)
      {
         g_shadowPos[i].magic         = magic;
         g_shadowPos[i].symbol        = sym;
         g_shadowPos[i].is_buy        = isBuy;
         g_shadowPos[i].entry_price   = entryPrice;
         g_shadowPos[i].lots          = lots;
         g_shadowPos[i].init_risk_usd = initRiskUsd;
         return;
      }
   }
   for(int i = 0; i < NAQEX_V105_MAX_SHADOW_POS; i++)
   {
      if(!g_shadowPos[i].active)
      {
         g_shadowPos[i].active        = true;
         g_shadowPos[i].pos_id        = posId;
         g_shadowPos[i].magic         = magic;
         g_shadowPos[i].symbol        = sym;
         g_shadowPos[i].is_buy        = isBuy;
         g_shadowPos[i].entry_price   = entryPrice;
         g_shadowPos[i].lots          = lots;
         g_shadowPos[i].init_risk_usd = initRiskUsd;
         return;
      }
   }
}

//--- Idempotently commit any newly closed tracked positions into Shadow1x closed-R curve
void SyncClosedShadowPositionsV105()
{
   for(int i = 0; i < NAQEX_V105_MAX_SHADOW_POS; i++)
   {
      if(!g_shadowPos[i].active || g_shadowPos[i].pos_id == 0)
         continue;
      ulong pid = g_shadowPos[i].pos_id;
      bool stillOpen = false;
      for(int p = PositionsTotal() - 1; p >= 0; p--)
      {
         ulong ptk = PositionGetTicket(p);
         if(ptk == 0) continue;
         if((ulong)PositionGetInteger(POSITION_IDENTIFIER) == pid)
         {
            stillOpen = true;
            break;
         }
      }
      if(stillOpen)
         continue;

      // Position is fully closed: recover exact net USD PnL across all deals of this position
      double brokerProfit = 0.0;
      double brokerSwap   = 0.0;
      double brokerComm   = 0.0;
      double entryPx      = g_shadowPos[i].entry_price;
      double exitPxSum    = 0.0;
      double closedVol    = 0.0;
      bool   foundOutDeal = false;
      if(HistorySelectByPosition(pid))
      {
         int nDeals = HistoryDealsTotal();
         for(int d = 0; d < nDeals; d++)
         {
            ulong dtk = HistoryDealGetTicket(d);
            if(dtk == 0) continue;
            long dtype = HistoryDealGetInteger(dtk, DEAL_TYPE);
            if(dtype != DEAL_TYPE_BUY && dtype != DEAL_TYPE_SELL)
               continue;
            long dentry = HistoryDealGetInteger(dtk, DEAL_ENTRY);
            double dvol = HistoryDealGetDouble(dtk, DEAL_VOLUME);
            double dpx  = HistoryDealGetDouble(dtk, DEAL_PRICE);
            if(dentry == DEAL_ENTRY_IN && entryPx <= 0.0 && dpx > 0.0)
               entryPx = dpx;
            if(dentry == DEAL_ENTRY_OUT || dentry == DEAL_ENTRY_OUT_BY || dentry == DEAL_ENTRY_INOUT)
            {
               foundOutDeal = true;
               if(dpx > 0.0 && dvol > 0.0)
               {
                  exitPxSum += dpx * dvol;
                  closedVol += dvol;
               }
            }
            brokerProfit += HistoryDealGetDouble(dtk, DEAL_PROFIT);
            brokerSwap   += HistoryDealGetDouble(dtk, DEAL_SWAP);
            brokerComm   += HistoryDealGetDouble(dtk, DEAL_COMMISSION);
         }
      }
      if(foundOutDeal && g_shadowPos[i].init_risk_usd > 1e-12)
      {
         double grossUsd = brokerProfit;
         string psym = g_shadowPos[i].symbol;
         string profitCcy = SymbolInfoString(psym, SYMBOL_CURRENCY_PROFIT);
         StringToUpper(profitCcy);
         if(profitCcy == "JPY" && closedVol > 0.0 && entryPx > 0.0 && exitPxSum > 0.0)
         {
            double exitPx       = exitPxSum / closedVol;
            double contractSize = SymbolInfoDouble(psym, SYMBOL_TRADE_CONTRACT_SIZE);
            double diffPx       = g_shadowPos[i].is_buy ? (exitPx - entryPx) : (entryPx - exitPx);
            double pnlJpy       = diffPx * contractSize * closedVol;
            string ujSym        = g_signals.SymbolAt(SYM_USDJPY);
            double conv         = (psym == ujSym)
               ? exitPx
               : ((pnlJpy >= 0.0) ? SymbolInfoDouble(ujSym, SYMBOL_ASK) : SymbolInfoDouble(ujSym, SYMBOL_BID));
            if(contractSize > 0.0 && conv > 0.0 && MathIsValidNumber(pnlJpy / conv))
               grossUsd = RoundCentHalfAwayV105(pnlJpy / conv);
         }
         double netUsd = grossUsd + brokerSwap + brokerComm;
         double netR   = netUsd / g_shadowPos[i].init_risk_usd;
         g_mlFilter.RecordClosedTradeShadow1x(g_shadowPos[i].magic, netR);
      }
      g_shadowPos[i].active        = false;
      g_shadowPos[i].pos_id        = 0;
      g_shadowPos[i].magic         = 0;
      g_shadowPos[i].symbol        = "";
      g_shadowPos[i].is_buy        = false;
      g_shadowPos[i].entry_price   = 0.0;
      g_shadowPos[i].lots          = 0.0;
      g_shadowPos[i].init_risk_usd = 0.0;
   }
}

void WriteFeatureDumpRowV105(const NaqexSignalIntent &it,
                             const double &feat[],
                             const double pWin,
                             const bool mlAllowed,
                             const string mlBackend,
                             const int sameDirCnt)
{
   if(g_featDumpFh == INVALID_HANDLE || !MQLInfoInteger(MQL_TESTER))
      return;
   datetime srvNow = TimeCurrent();
   string srvStr = TimeToString(srvNow, TIME_DATE | TIME_SECONDS);
   string row = StringFormat(
      "%I64d,%I64d,%s,%s,%I64d,%s,%s,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.12f,%d,%s,%.10f,%.10f,%.8f,%d\n",
      g_featDumpSeq,
      (long)it.signal_utc,
      srvStr,
      it.engine_id,
      it.magic,
      it.symbol,
      it.is_buy ? "BUY" : "SELL",
      feat[0], feat[1], feat[2], feat[3], feat[4], feat[5], feat[6], feat[7],
      pWin,
      mlAllowed ? 1 : 0,
      mlBackend,
      g_mlFilter.ShadowEq1x(),
      g_mlFilter.ShadowPeak1x(),
      g_mlFilter.ShadowRollingDdPct1x(),
      sameDirCnt
   );
   FileWriteString(g_featDumpFh, row);
   g_featDumpSeq++;
}

int LastSundayOfMonthV105(const int year, const int month)
{
   MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 31;
   TimeToStruct(StructToTime(d), d);
   return 31 - d.day_of_week;
}

int PragueUtcOffsetHoursV105(const MqlDateTime &utc)
{
   if(utc.mon < 3 || utc.mon > 10) return 1;
   if(utc.mon > 3 && utc.mon < 10) return 2;
   int ls = LastSundayOfMonthV105(utc.year, utc.mon);
   if(utc.mon == 3) return (utc.day > ls || (utc.day == ls && utc.hour >= 1)) ? 2 : 1;
   return (utc.day < ls || (utc.day == ls && utc.hour < 1)) ? 2 : 1;
}

int PragueMidnightUtcOffsetHoursV105(const int year, const int month, const int day)
{
   if(month < 3 || month > 10) return 1;
   if(month > 3 && month < 10) return 2;
   int ls = LastSundayOfMonthV105(year, month);
   if(month == 3) return (day > ls) ? 2 : 1;
   return (day <= ls) ? 2 : 1;
}

int CurrentResetDayKeyV105()
{
   datetime refTs = 0;
   if(InpDailyResetMode == 0)
      refTs = CNaqexPropGuard::ServerNow();
   else if(InpDailyResetMode == 1)
   {
      datetime nowUtc = g_guard.NowUTC();
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      refTs = nowUtc + (datetime)(PragueUtcOffsetHoursV105(utc) * 3600);
   }
   else
      refTs = g_guard.NowUTC();
   MqlDateTime dt; TimeToStruct(refTs, dt);
   return dt.year * 1000 + dt.day_of_year;
}

datetime CurrentResetStartServerTimeV105()
{
   datetime srvNow = CNaqexPropGuard::ServerNow();
   if(InpDailyResetMode == 0) return srvNow - (srvNow % 86400);
   datetime nowUtc = g_guard.NowUTC();
   long srvMinusUtc = (long)srvNow - (long)nowUtc;
   if(InpDailyResetMode == 1)
   {
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      int curOff = PragueUtcOffsetHoursV105(utc) * 3600;
      datetime prgNow = nowUtc + (datetime)curOff;
      MqlDateTime prgDt; TimeToStruct(prgNow, prgDt);
      int midOff = PragueMidnightUtcOffsetHoursV105(prgDt.year, prgDt.mon, prgDt.day) * 3600;
      datetime prgMidUtc = (prgNow - (prgNow % 86400)) - (datetime)midOff;
      return prgMidUtc + (datetime)srvMinusUtc;
   }
   return (nowUtc - (nowUtc % 86400)) + (datetime)srvMinusUtc;
}

void PersistAutoKillStateV105(const int dayKey, const bool active)
{
   if(MQLInfoInteger(MQL_TESTER) || dayKey <= 0) return;
   GlobalVariableSet(CNaqexPropGuard::AcctDayKeyName(), (double)dayKey);
   GlobalVariableSet(CNaqexPropGuard::AcctAutoKillKey(), active ? 1.0 : 0.0);
}

bool IsAccountSyncedV105(const double bal, const double eq)
{
   if(!MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
      return false;
   return (bal > 0.0 && eq > 0.0);
}

void RestoreOrInitDayAnchorV105()
{
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsAccountSyncedV105(bal, eq)) return;
   datetime nowUtc = g_guard.NowUTC();
   int today = CurrentResetDayKeyV105();
   bool isNewDay = (today != g_dayKey);
   if(!isNewDay && g_dayAnchorEq > 0.0 && !g_anchorUnrecovered) return;
   if(!isNewDay && g_anchorUnrecovered && (nowUtc - g_lastAnchorRetry) < 15) return;
   g_lastAnchorRetry = nowUtc;

   double reconstructedBal = bal;
   double reconstructedEq  = (InpDailyResetMode == 1) ? bal : MathMax(bal, eq);
   g_anchorUnrecovered = false;
   if(!MQLInfoInteger(MQL_TESTER))
   {
      datetime resetStart = CurrentResetStartServerTimeV105();
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
         PersistAutoKillStateV105(today, false);
   }
   else if(isNewDay)
   {
      g_autoKillActive = false;
   }
}

int CountActiveInFlightV105()
{
   int n = 0;
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active) n++;
   return n;
}

void ReconcileInFlightOrdersV105(const datetime nowUtc)
{
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
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

void RegisterInFlightV105(const NaqexSignalIntent &it, const double estRiskPct, const ulong ordTicket, const bool isUnknown)
{
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
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
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
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

bool HasOpenOrInFlightForMagicV105(const long magic)
{
   for(int p = PositionsTotal() - 1; p >= 0; p--)
      if(PositionGetTicket(p) > 0 && PositionGetInteger(POSITION_MAGIC) == magic)
         return true;
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].magic == magic)
         return true;
   return false;
}

double GetInFlightSymbolRiskV105(const string sym)
{
   double s = 0.0;
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
      if(g_inFlight[i].active && g_inFlight[i].symbol == sym)
         s += g_inFlight[i].est_risk_pct;
   return s;
}

void GetInFlightFactorRisksV105(double &uL, double &uS, double &jL, double &jS, double &iL, double &iS, double &tot)
{
   uL = 0.0; uS = 0.0; jL = 0.0; jS = 0.0; iL = 0.0; iS = 0.0; tot = 0.0;
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
      tot += g_inFlight[i].est_risk_pct;
      CNaqexPropGuard::AccumulateDirectionalFactor(g_inFlight[i].symbol, g_inFlight[i].is_buy, g_inFlight[i].est_risk_pct,
                                                   uL, uS, jL, jS, iL, iS);
   }
}

void GetInFlightExtendedFactorRisksV105(double &eL, double &eS, double &gL, double &gS, double &aL, double &aS, double &tot)
{
   eL = 0.0; eS = 0.0; gL = 0.0; gS = 0.0; aL = 0.0; aS = 0.0; tot = 0.0;
   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
   {
      if(!g_inFlight[i].active) continue;
      tot += g_inFlight[i].est_risk_pct;
      CNaqexEngineSlotRegistry::AccumulateExtendedDirectionalFactor(
         g_inFlight[i].symbol, g_inFlight[i].is_buy, g_inFlight[i].est_risk_pct,
         eL, eS, gL, gS, aL, aS
      );
   }
}

void LogMasterShadowRowV105(const NaqexSignalIntent &it, const string evType, const double riskPct,
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

//--- Compute risk multiplier: 100% v103-identical when InpUseBellmanDP=false; 6-tier anti-martingale DP when true
double ComputePhaseRiskMultiplierV105(const double dailyDdPct, const double staticDdPct,
                                      const double eqProfitPct, const double realizedProfitPct,
                                      const double signedEqPct, const double ddFromPeakPct,
                                      string &outRegime)
{
   if(InpUseBellmanDP)
      return EvaluateBellmanDPRiskMultV105(signedEqPct, ddFromPeakPct, dailyDdPct, outRegime);

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

void WriteMasterHeartbeatV105(const datetime nowUtc, const double bal, const double eq,
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
   double eL = 0.0, eS = 0.0, gL = 0.0, gS = 0.0, aL = 0.0, aS = 0.0;
   if(posState == "CONFIRMED")
   {
      totOpenPct = g_guard.ComputeAccountFactorRisk(uL, uS, jL, jS, iL, iS);
      CNaqexEngineSlotRegistry::ComputeAccountExtendedClusterRisk(eL, eS, gL, gS, aL, aS);
   }

   int fh = FileOpen(fname, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh != INVALID_HANDLE)
   {
      string js = StringFormat(
         "{\"utc_ts\":%I64d,\"account_login\":%I64d,\"account_server\":\"%s\",\"build_version\":\"master-1.05-modular\","
         "\"sku\":\"%s\",\"sizing_mode\":%d,\"bellman_dp\":%s,\"bellman_dp_phase\":%d,\"shadow_compare\":%s,"
         "\"terminal_connected\":%s,\"quote_ts\":%I64d,\"positions_state\":\"%s\",\"anchor_state\":\"%s\","
         "\"balance\":%.2f,\"equity\":%.2f,\"day_anchor_eq\":%.2f,\"day_anchor_bal\":%.2f,"
         "\"daily_dd_pct\":%.3f,\"static_dd_pct\":%.3f,\"profit_pct\":%.3f,\"reset_mode\":%d,"
         "\"regime\":\"%s\",\"risk_mult\":%.3f,\"slots_enabled\":%d,"
         "\"kill_switch\":%s,\"manual_halt\":%s,\"manual_halt_ack\":%s,"
         "\"open_positions\":%d,\"total_account_positions\":%d,\"pending_orders\":%d,\"in_flight_orders\":%d,"
         "\"orphan_no_sl\":%d,\"open_total_risk_pct\":%.3f,\"max_total_open_risk_pct\":%.2f,"
         "\"factor_usd_max_pct\":%.3f,\"factor_jpy_max_pct\":%.3f,\"factor_idx_max_pct\":%.3f,"
         "\"factor_eur_max_pct\":%.3f,\"factor_gbp_max_pct\":%.3f,\"factor_aud_max_pct\":%.3f,"
         "\"spread_guard_enabled\":%s,\"news_pad_sec\":%d,\"news_6ccy_10m\":%s,"
         "\"ml_enabled\":%s,\"ml_threshold\":%.6f,\"ml_onnx_ready\":%s,\"ml_backend\":\"%s\","
         "\"ml_passed\":%I64d,\"ml_blocked\":%I64d,\"shadow_dd_1x_pct\":%.3f,"
         "\"last_tick_lag_ms\":%I64d,\"max_tick_lag_ms\":%I64d,\"dry_run\":%s}\n",
         (long)nowUtc, login, srv, InpContractSku, InpSizingMode,
         InpUseBellmanDP ? "true" : "false", InpBellmanDPPhase,
         InpShadowCompareMode ? "true" : "false", termConn ? "true" : "false", quoteTs,
         posState, anchorState,
         bal, eq, g_dayAnchorEq, g_dayAnchorBal,
         dailyDdPct, staticDdPct, profitPct, InpDailyResetMode,
         regime, riskMult, g_registry.CountEnabledSlots(),
         effectiveKill ? "true" : "false", manualHalt ? "true" : "false", manualHalt ? "true" : "false",
         openCount, totalAcctPos, pendingCount, inFlightCount,
         orphanCount, (totOpenPct >= 900.0 ? -1.0 : totOpenPct), EffectiveTotalOpenRiskCapPctV105(),
         MathMax(uL, uS), MathMax(jL, jS), MathMax(iL, iS),
         MathMax(eL, eS), MathMax(gL, gS), MathMax(aL, aS),
         InpEnableSpreadGuard ? "true" : "false", InpGuardNewsPadSec, InpUse6CcyNewsPad10m ? "true" : "false",
         InpUseV105ML ? "true" : "false", InpMLThreshold,
         g_mlFilter.IsOnnxReady() ? "true" : "false", g_mlFilter.LastBackend(),
         g_mlFilter.PassedCount(), g_mlFilter.BlockedCount(), g_mlFilter.ShadowRollingDdPct1x(),
         g_lastTickLagMs, g_maxTickLagMs,
         IsDryRunFailClosedV105() ? "true" : "false"
      );
      FileWriteString(fh, js);
      FileClose(fh);
   }
}

int ClosePositionsByReasonV105(const datetime nowUtc, const bool flattenAll, const string globalReason)
{
   bool isDry = IsDryRunFailClosedV105();
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

void CancelPendingOrdersByReasonV105(const datetime nowUtc, const bool cancelAll, const string globalReason)
{
   bool isDry = IsDryRunFailClosedV105();
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
         PrintFormat("[DRYRUN-V105-CANCEL] ord=%I64u magic=%I64d sym=%s vol=%.2f reason=%s", ot, om, osym, ovol, reason);
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

void ProcessIntentAtomicallyV105(const NaqexSignalIntent &it, const double riskMult)
{
   // Modular 16-slot registry check (handles ACTIVE / HALVED / SHADOW / RETIRED cleanly)
   double slotWeightMult = 1.0;
   bool slotForceShadow  = false;
   if(!g_registry.IsMagicAllowedForLiveOrShadow(it.magic, slotWeightMult, slotForceShadow))
      return;

   bool isShadowOrDry = (it.shadow_only || slotForceShadow || IsDryRunFailClosedV105());
   if(HasOpenOrInFlightForMagicV105(it.magic))
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
            LogMasterShadowRowV105(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      }
      else
         LogMasterShadowRowV105(it, "ORDER_BLOCKED_NEWS", 0.0, 0.0, whyNews);
      return;
   }

   // Shield B2: Real M1-calibrated per-symbol SpreadGuard + rollover blackout
   double spreadCapPts = MaxSpreadCapForSymbolV105(it.symbol);
   if(!g_guard.IsSpreadAndSessionSafeFor(it.symbol, spreadCapPts))
   {
      double obsSpread = (double)SymbolInfoInteger(it.symbol, SYMBOL_SPREAD);
      string whySpr = StringFormat("SPREAD_GUARD|obs=%.1f|cap=%.1f", obsSpread, spreadCapPts);
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "SPREAD", "SPREAD_GUARD:ORDER_BLOCKED_SPREAD", blkCnt, evCnt);
         if(logTrans)
            LogMasterShadowRowV105(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
      }
      else
         LogMasterShadowRowV105(it, "ORDER_BLOCKED_SPREAD", 0.0, 0.0, whySpr);
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
      LogMasterShadowRowV105(it, "ORDER_BLOCKED_STOPS", 0.0, 0.0, "SL_BELOW_BROKER_STOPS_LEVEL");
      return;
   }

   // Wave 5 W5-G10 / W5-G12 Aligned Causal ML Filter (1:1 Python == MQL5 + Shadow1x DD)
   double mlProb = 1.0;
   string mlBackend = "ML_DISABLED";
   if(InpUseV105ML)
   {
      // Ensure any just-closed positions are committed to Shadow1x before building features
      SyncClosedShadowPositionsV105();
      int symIdx = SymbolIndexForV105(it.symbol);
      int atrH   = (symIdx >= 0 && symIdx < NAQEX_SYM_COUNT) ? g_mlAtrHandles[symIdx] : INVALID_HANDLE;
      int sameDirCnt = CountSameDirectionConcurrentV105(it.is_buy);
      double mlFeat[];
      bool featOk = g_mlFilter.BuildAlignedFeaturesV105(
         it.symbol, atrH, it.signal_utc, it.magic, sameDirCnt, mlFeat
      );
      bool mlAllowed = featOk && g_mlFilter.ShouldAllowTrade(mlFeat, mlProb, mlBackend);
      if(InpDumpMLFeaturesCsv && MQLInfoInteger(MQL_TESTER) && featOk)
         WriteFeatureDumpRowV105(it, mlFeat, mlProb, mlAllowed, mlBackend, sameDirCnt);

      if(!mlAllowed)
      {
         string whyMl = StringFormat("ML_V105_FILTER|p=%.6f|thr=%.6f|backend=%s|feat_ok=%s",
                                     mlProb, InpMLThreshold, mlBackend, featOk ? "true" : "false");
         if(InpOpportunityLifecycleMode == 1)
         {
            int blkCnt = 0, evCnt = 0;
            bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "OTHER", "ML_V105_FILTER:ORDER_BLOCKED_ML_TOXIC", blkCnt, evCnt);
            if(logTrans)
               LogMasterShadowRowV105(it, "ORDER_BLOCKED_ML_TOXIC", 0.0, 0.0, whyMl);
         }
         else
            LogMasterShadowRowV105(it, "ORDER_BLOCKED_ML_TOXIC", 0.0, 0.0, whyMl);
         // W4G05-F01 closure: lock out engine for this session (1-shot toxic filter; 0 delayed re-entries!)
         g_signals.MarkEngineTraded(it.magic, it.session_day_key);
         return;
      }
   }

   // Shield A + Shield B1 (USD/JPY/IDX) + P2-3 (EUR/GBP/AUD) atomic risk allocation
   double reqRiskPct = it.base_risk_pct * riskMult * slotWeightMult;
   double usedSymPct = g_guard.GetOpenSymbolRiskPctFor(it.symbol) + GetInFlightSymbolRiskV105(it.symbol);
   double symHeadroom = (InpMaxSymbolRiskPct > 0.0) ? MathMax(0.0, InpMaxSymbolRiskPct - usedSymPct) : 999.0;

   double fUL, fUS, fJL, fJS, fIL, fIS, fTot;
   GetInFlightFactorRisksV105(fUL, fUS, fJL, fJS, fIL, fIS, fTot);
   double effTotalOpenCap = EffectiveTotalOpenRiskCapPctV105();
   double factorAndTotalHeadroom = g_guard.ComputeFactorHeadroomPct(
      it.symbol, it.is_buy,
      InpMaxUsdClusterPct, InpMaxJpyClusterPct, InpMaxIdxClusterPct, effTotalOpenCap,
      fUL, fUS, fJL, fJS, fIL, fIS, fTot
   );

   double eEL, eES, eGL, eGS, eAL, eAS, eTot;
   GetInFlightExtendedFactorRisksV105(eEL, eES, eGL, eGS, eAL, eAS, eTot);
   double extClusterHeadroom = CNaqexEngineSlotRegistry::ComputeExtendedClusterHeadroomPct(
      it.symbol, it.is_buy,
      InpMaxEurClusterPct, InpMaxGbpClusterPct, InpMaxAudClusterPct, effTotalOpenCap,
      eEL, eES, eGL, eGS, eAL, eAS, eTot
   );

   double combinedFactorHeadroom = MathMin(factorAndTotalHeadroom, extClusterHeadroom);
   double allowedRiskPct = MathMin(reqRiskPct, MathMin(symHeadroom, combinedFactorHeadroom));
   if(allowedRiskPct <= 0.01)
   {
      string whyCap = (combinedFactorHeadroom <= symHeadroom) ? "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP" : "ORDER_BLOCKED_SYMCAP";
      if(InpOpportunityLifecycleMode == 1)
      {
         int blkCnt = 0, evCnt = 0;
         bool logTrans = g_signals.RecordOpportunityBlocked(it.magic, "CAP", whyCap, blkCnt, evCnt);
         if(logTrans)
            LogMasterShadowRowV105(it, whyCap, reqRiskPct, 0.0,
                                   StringFormat("symRem=%.2f|facTotRem=%.2f|extRem=%.2f|totCap=%.2f",
                                                symHeadroom, factorAndTotalHeadroom, extClusterHeadroom, effTotalOpenCap));
      }
      else
         LogMasterShadowRowV105(it, whyCap, reqRiskPct, 0.0,
                                StringFormat("symRem=%.2f|facTotRem=%.2f|extRem=%.2f|totCap=%.2f",
                                             symHeadroom, factorAndTotalHeadroom, extClusterHeadroom, effTotalOpenCap));
      return;
   }

   // Conservative lot sizing (TICK_VALUE_LOSS + 5% cushion + fail-closed OrderCalcMargin <= 85%)
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
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
      LogMasterShadowRowV105(it, "ORDER_BLOCKED_MARGIN", allowedRiskPct, 0.0, "FAIL_CLOSED_MARGIN_CHECK");
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
      string dryNote = StringFormat("%s|ml_p=%.6f|ml_be=%s|slot_w=%.2f", it.tag, mlProb, mlBackend, slotWeightMult);
      LogMasterShadowRowV105(it, (it.shadow_only || slotForceShadow) ? "SHADOW_INTENT" : "DRYRUN_SIGNAL_V105", allowedRiskPct, lots, dryNote);
      g_signals.MarkEngineTraded(it.magic, it.session_day_key);
      return;
   }

   double actualRiskPct = (((slDist / tickSize) * tickVal * lots) / bal) * 100.0;
   double effectiveHeadroom = MathMin(symHeadroom, combinedFactorHeadroom);
   if(actualRiskPct > effectiveHeadroom + 1e-6)
   {
      LogMasterShadowRowV105(it, "ORDER_BLOCKED_POST_ROUND_CAP", actualRiskPct, lots, "EXCEEDS_HEADROOM");
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
      RegisterInFlightV105(it, actualRiskPct, g_trade.ResultOrder(), true);
      g_guard.LogExecAuditFor(it.symbol, sideStr, "FILL_UNRESOLVED", it.signal_price, -1.0, normSl, lots, latMs, ret,
                              StringFormat("%s|v105|ml_p=%.4f|intent=%s|ord=%I64u|UNKNOWN_INFLIGHT",
                                           it.tag, mlProb, it.intent_id, (ulong)g_trade.ResultOrder()),
                              it.magic);
      return;
   }
   if(!ok || (ret != TRADE_RETCODE_DONE && ret != TRADE_RETCODE_DONE_PARTIAL))
   {
      g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_REJECT", it.signal_price, g_trade.ResultPrice(), normSl, lots, latMs, ret,
                              StringFormat("%s|v105|ml_p=%.4f|intent=%s|%s",
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
      RegisterInFlightV105(it, actualRiskPct, ordId, false);

   double execLots = (g_trade.ResultVolume() > 0.0) ? g_trade.ResultVolume() : lots;
   double fillPx   = g_guard.ResolveExecutedFillPrice(g_trade, it.symbol, -1.0);
   if(InpUseV105ML)
   {
      double shadowTv          = ComputeLiveShadowTickValueLossV105(it.symbol);
      double shadowInitRiskUsd = (shadowTv > 0.0 && tickSize > 0.0)
         ? ((slDist / tickSize) * shadowTv * execLots)
         : (lossPerLot * execLots);
      double shadowEntryPx     = (fillPx > 0.0) ? fillPx : it.signal_price;
      RegisterShadowPositionOpenV105(posId, it.magic, it.symbol, it.is_buy, shadowEntryPx, execLots, shadowInitRiskUsd);
   }

   g_guard.LogExecAuditFor(it.symbol, sideStr, "ORDER_FILL", it.signal_price, fillPx, normSl, execLots, latMs, ret,
                           StringFormat("%s|v105|ml_p=%.4f|ml_be=%s|intent=%s|deal=%I64u|ord=%I64u|tk=%I64u|pos=%I64u%s",
                                        it.tag, mlProb, mlBackend, it.intent_id, dealId, ordId, ordId, posId,
                                        (fillPx <= 0.0) ? "|FILL_UNRESOLVED" : ""),
                           it.magic);
   g_signals.MarkEngineTraded(it.magic, it.session_day_key);
}

int ReconcilePendingClosesV105()
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

void RunMasterCycleV105()
{
   datetime nowUtc = g_guard.NowUTC();
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);

   if(!IsAccountSyncedV105(bal, eq))
   {
      WriteMasterHeartbeatV105(nowUtc, bal, eq, 0.0, 0.0, 0.0, "DISCONNECTED", 0.0, true, false,
                               "UNKNOWN", -1, -1, -1, CountActiveInFlightV105(), -1, "UNSYNCED");
      return;
   }

   if(eq > g_peakEquity) g_peakEquity = eq;
   if(InpUseV105ML)
      SyncClosedShadowPositionsV105();

   RestoreOrInitDayAnchorV105();
   if(!g_signals.IsTradedDayHydrated() && (nowUtc - g_lastHydrateRetry) >= 5)
   {
      g_lastHydrateRetry = nowUtc;
      g_signals.HydrateTradedDaysFromHistory(nowUtc);
   }
   ReconcileInFlightOrdersV105(nowUtc);

   long lag = g_signals.PollSymbolTicks();
   g_lastTickLagMs = lag;
   if(lag > g_maxTickLagMs) g_maxTickLagMs = lag;

   double dailyDdPct = (InpDailyResetMode == 1)
      ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
      : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
   double staticDdPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double eqProfitPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double signedEqPct       = (InpInitialBalanceUSD > 0.0) ? (((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double ddFromPeakPct     = (g_peakEquity > 0.0) ? MathMax(0.0, ((g_peakEquity - eq) / g_peakEquity) * 100.0) : 0.0;
   double realizedProfitPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((bal - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
   double profitPct         = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;

   string regime = "NORMAL";
   double riskMult = ComputePhaseRiskMultiplierV105(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, signedEqPct, ddFromPeakPct, regime);

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
         PersistAutoKillStateV105(g_dayKey, true);
      }
   }
   bool effectiveKill = g_autoKillActive || manualHalt || g_anchorUnrecovered;
   if(g_anchorUnrecovered) regime = "ANCHOR_UNRECOVERED";
   if(manualHalt) regime = manualFlatten ? "MANUAL_FLATTEN" : "MANUAL_HALT";

   int closedConfirmedCount = 0;
   if(g_autoKillActive)
   {
      string killWhy = (dailyDdPct >= InpKillDailyDdPct) ? "MASTER_KILL_DAILY_DD" : "MASTER_KILL_STATIC_DD";
      CancelPendingOrdersByReasonV105(nowUtc, true, killWhy);
      closedConfirmedCount = ClosePositionsByReasonV105(nowUtc, true, killWhy);
   }
   else if(manualFlatten)
   {
      CancelPendingOrdersByReasonV105(nowUtc, true, "MASTER_MANUAL_FLATTEN");
      closedConfirmedCount = ClosePositionsByReasonV105(nowUtc, true, "MASTER_MANUAL_FLATTEN");
   }
   else
   {
      CancelPendingOrdersByReasonV105(nowUtc, false, "");
      closedConfirmedCount = ClosePositionsByReasonV105(nowUtc, false, "");
   }
   closedConfirmedCount += ReconcilePendingClosesV105();

   if(InpUseV105ML && closedConfirmedCount > 0)
      SyncClosedShadowPositionsV105();

   if(InpPostCloseRefreshMode == 1 && closedConfirmedCount > 0)
   {
      bal = AccountInfoDouble(ACCOUNT_BALANCE);
      eq  = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq > g_peakEquity) g_peakEquity = eq;
      dailyDdPct = (InpDailyResetMode == 1)
         ? ((InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((g_dayAnchorBal - eq) / InpInitialBalanceUSD) * 100.0) : 0.0)
         : ((g_dayAnchorEq > 0.0) ? MathMax(0.0, ((g_dayAnchorEq - eq) / g_dayAnchorEq) * 100.0) : 0.0);
      staticDdPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((InpInitialBalanceUSD - eq) / InpInitialBalanceUSD) * 100.0) : 0.0;
      eqProfitPct       = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      signedEqPct       = (InpInitialBalanceUSD > 0.0) ? (((eq - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      ddFromPeakPct     = (g_peakEquity > 0.0) ? MathMax(0.0, ((g_peakEquity - eq) / g_peakEquity) * 100.0) : 0.0;
      realizedProfitPct = (InpInitialBalanceUSD > 0.0) ? MathMax(0.0, ((bal - InpInitialBalanceUSD) / InpInitialBalanceUSD) * 100.0) : 0.0;
      profitPct         = (InpProfitLockBasisMode == 1) ? realizedProfitPct : eqProfitPct;
      regime = "NORMAL";
      riskMult = ComputePhaseRiskMultiplierV105(dailyDdPct, staticDdPct, eqProfitPct, realizedProfitPct, signedEqPct, ddFromPeakPct, regime);
      if(dailyDdPct >= InpKillDailyDdPct || staticDdPct >= InpKillStaticDdPct)
      {
         if(!g_autoKillActive)
         {
            g_autoKillActive = true;
            PersistAutoKillStateV105(g_dayKey, true);
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
         ProcessIntentAtomicallyV105(intents[i], riskMult);
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

   WriteMasterHeartbeatV105(nowUtc, bal, eq, dailyDdPct, staticDdPct, profitPct,
                            regime, riskMult, effectiveKill, manualHalt,
                            "CONFIRMED", openNaqex, totalPos, pendingCnt, CountActiveInFlightV105(), orphanCnt,
                            g_anchorUnrecovered ? "UNRECOVERED_AFTER_GAP" : "SYNCED");
}

int OnInit()
{
   // Fail-closed Shield A hard ceiling check (never allow > 3.00%)
   if(InpHardTotalOpenCeilingPct <= 0.0 || InpHardTotalOpenCeilingPct > 3.00)
   {
      PrintFormat("[MASTER-V105-ERR] InpHardTotalOpenCeilingPct must be in (0.0, 3.00] (got %.2f)", InpHardTotalOpenCeilingPct);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Fail-closed Shield B3 parameter consistency checks
   if(InpGuardEnableRedNews && InpGuardNewsPadSec < InpGuardNewsHardBanSec)
   {
      PrintFormat("[MASTER-V105-ERR] InpGuardNewsPadSec (%d) must be >= InpGuardNewsHardBanSec (%d)",
                  InpGuardNewsPadSec, InpGuardNewsHardBanSec);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpGuardEnableRedNews && InpUse6CcyNewsPad10m && InpGuardNewsPadSec < 600)
   {
      PrintFormat("[MASTER-V105-ERR] InpUse6CcyNewsPad10m=true requires InpGuardNewsPadSec >= 600 (got %d)", InpGuardNewsPadSec);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Fail-closed ML threshold check
   if(InpUseV105ML && (!MathIsValidNumber(InpMLThreshold) || InpMLThreshold <= 0.0 || InpMLThreshold >= 1.0))
   {
      PrintFormat("[MASTER-V105-ERR] InpMLThreshold must be strictly inside (0, 1) (got %.6f)", InpMLThreshold);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Fail-closed Bellman DP phase check
   if(InpUseBellmanDP && InpBellmanDPPhase != 1 && InpBellmanDPPhase != 2)
   {
      PrintFormat("[MASTER-V105-ERR] InpBellmanDPPhase must be 1 or 2 (got %d)", InpBellmanDPPhase);
      return INIT_PARAMETERS_INCORRECT;
   }

   for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++) g_inFlight[i].active = false;
   for(int i = 0; i < NAQEX_V105_MAX_SHADOW_POS; i++)
   {
      g_shadowPos[i].active        = false;
      g_shadowPos[i].pos_id        = 0;
      g_shadowPos[i].magic         = 0;
      g_shadowPos[i].symbol        = "";
      g_shadowPos[i].is_buy        = false;
      g_shadowPos[i].entry_price   = 0.0;
      g_shadowPos[i].lots          = 0.0;
      g_shadowPos[i].init_risk_usd = 0.0;
   }
   g_lastTesterSec = 0;
   for(int s = 0; s < NAQEX_SYM_COUNT; s++) g_mlAtrHandles[s] = INVALID_HANDLE;
   CNaqexPropGuard::ResetPendingCloseTable(g_pendingCloses);

   if(!g_signals.Init(InpSymUSDJPY, InpSymGBPUSD, InpSymEURJPY, InpSymUS100, InpSymUS500,
                      InpSymEURUSD, InpSymAUDUSD, InpSymUSDCAD, InpMaxBreakoutTickLagMs, InpEnableS6Shadow,
                      InpOpportunityLifecycleMode))
      return INIT_FAILED;

   // Initialize modular 16-slot engine registry over PORT_7E adapter
   g_registry.InitCore7EAdapter(
      g_signals.SymbolAt(SYM_USDJPY),
      g_signals.SymbolAt(SYM_GBPUSD),
      g_signals.SymbolAt(SYM_EURJPY),
      g_signals.SymbolAt(SYM_US100),
      InpEnableS6Shadow,
      InpSlot0Weight, InpSlot1Weight, InpSlot2Weight, InpSlot3Weight,
      InpSlot4Weight, InpSlot5Weight, InpSlot6Weight
   );

   if(InpUseBellmanDP)
   {
      if(!LoadBellmanDPScheduleV105())
         return INIT_FAILED;
   }

   if(InpUseV105ML)
   {
      for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      {
         g_mlAtrHandles[s] = iATR(g_signals.SymbolAt(s), PERIOD_D1, 14);
         if(g_mlAtrHandles[s] == INVALID_HANDLE)
         {
            PrintFormat("[MASTER-V105-ERR] ML D1 iATR handle failed for %s", g_signals.SymbolAt(s));
            return INIT_FAILED;
         }
      }

      ENUM_NAQEX_ML_V105_MODE effMlMode = V105_PURE_MQL5_TREE_ONLY;
      if(InpMLUseOnnx)
         effMlMode = InpMLFailClosedOnnxOnly ? V105_ONNX_ONLY_FAIL_CLOSED : V105_ONNX_OR_PURE_MQL5_FALLBACK;

      if(!g_mlFilter.InitFromFile(InpMLOnnxFile, effMlMode, InpMLThreshold))
      {
         PrintFormat("[MASTER-V105-ERR] ML v1.05 filter init failed (use_onnx=%s file=%s err=%d)",
                     InpMLUseOnnx ? "true" : "false", InpMLOnnxFile, g_mlFilter.LastOnnxError());
         return INIT_FAILED;
      }
      g_mlFilter.ResetShadow1x();

      if(InpDumpMLFeaturesCsv && MQLInfoInteger(MQL_TESTER))
      {
         g_featDumpSeq = 0;
         g_featDumpFh = FileOpen(InpDumpMLFeaturesFile, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
         if(g_featDumpFh == INVALID_HANDLE)
         {
            PrintFormat("[MASTER-V105-ERR] Failed to open tester feature dump CSV '%s' err=%d",
                        InpDumpMLFeaturesFile, GetLastError());
            return INIT_FAILED;
         }
         FileWriteString(
            g_featDumpFh,
            "signal_seq,entry_utc_ts,entry_server_time,engine_id,magic,symbol,side,"
            "f0,f1,f2,f3,f4,f5,f6,f7,ea_p_win,ea_ml_allowed,ea_backend,"
            "shadow_eq_1x,shadow_peak_1x,shadow_dd_pct_1x,same_dir_concurrent\n"
         );
      }
   }

   g_peakEquity = MathMax(InpInitialBalanceUSD, AccountInfoDouble(ACCOUNT_EQUITY));
   g_guard.Init(g_trade, g_signals.SymbolAt(SYM_USDJPY), InpMagicRangeMin, InpKillDailyDdPct);
   RestoreOrInitDayAnchorV105();
   g_signals.HydrateTradedDaysFromHistory(g_guard.NowUTC());
   if(!MQLInfoInteger(MQL_TESTER))
   {
      if(InpOpportunityLifecycleMode == 1)
         g_signals.RestoreOppStateOnce();
      int loadedPending = 0;
      CNaqexPropGuard::LoadPendingCloseState(g_pendingCloses, loadedPending);
   }

   PrintFormat("[MASTER-V105-INIT] sku=%s ml_enabled=%s ml_use_onnx=%s ml_thr=%.6f ml_onnx_ready=%s ml_backend=%s "
               "bellman_dp=%s dp_phase=%d dp_tiers=%d slots_enabled=%d tot_open_cap=%.2f%% "
               "eur_cap=%.2f%% gbp_cap=%.2f%% aud_cap=%.2f%% dump_csv=%s dry_run=%s",
               InpContractSku,
               InpUseV105ML ? "true" : "false",
               InpMLUseOnnx ? "true" : "false",
               InpMLThreshold,
               g_mlFilter.IsOnnxReady() ? "true" : "false",
               g_mlFilter.LastBackend(),
               InpUseBellmanDP ? "true" : "false",
               InpBellmanDPPhase,
               g_dpTierCount,
               g_registry.CountEnabledSlots(),
               EffectiveTotalOpenRiskCapPctV105(),
               InpMaxEurClusterPct, InpMaxGbpClusterPct, InpMaxAudClusterPct,
               (InpDumpMLFeaturesCsv && MQLInfoInteger(MQL_TESTER)) ? "true" : "false",
               IsDryRunFailClosedV105() ? "true" : "false");

   EventSetTimer(MQLInfoInteger(MQL_TESTER) ? 60 : 1);
   RunMasterCycleV105();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_featDumpFh != INVALID_HANDLE)
   {
      FileFlush(g_featDumpFh);
      FileClose(g_featDumpFh);
      g_featDumpFh = INVALID_HANDLE;
   }
   PrintFormat("[MASTER-V105-DEINIT] ml_passed=%I64d ml_blocked=%I64d ml_onnx_calls=%I64d ml_pure_calls=%I64d "
               "ml_fallback_calls=%I64d shadow_closed=%I64d shadow_dd_1x=%.6f dump_rows=%I64d",
               g_mlFilter.PassedCount(), g_mlFilter.BlockedCount(),
               g_mlFilter.OnnxCalls(), g_mlFilter.PureCalls(), g_mlFilter.FallbackCalls(),
               g_mlFilter.ShadowClosedTradeCount(), g_mlFilter.ShadowRollingDdPct1x(), g_featDumpSeq);
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

bool ShouldSkipDuplicateTesterSecondV105()
{
   if(!MQLInfoInteger(MQL_TESTER))
      return false;
   datetime cur = TimeCurrent();
   if(cur == g_lastTesterSec)
      return true;
   g_lastTesterSec = cur;
   return false;
}

void OnTick()
{
   if(ShouldSkipDuplicateTesterSecondV105())
      return;
   RunMasterCycleV105();
}

void OnTimer()
{
   if(ShouldSkipDuplicateTesterSecondV105())
      return;
   RunMasterCycleV105();
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(InpUseV105ML && trans.type == TRADE_TRANSACTION_DEAL_ADD)
      SyncClosedShadowPositionsV105();

   if(trans.order == 0) return;
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD ||
      (trans.type == TRADE_TRANSACTION_ORDER_DELETE && trans.order_state != ORDER_STATE_FILLED))
   {
      for(int i = 0; i < NAQEX_V105_MAX_INFLIGHT; i++)
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
