//+------------------------------------------------------------------+
//| Naqex_Signals_7E.mqh (v1.01 — Pure Signal Modules, 0 OrderSend)  |
//| Round-3 Approved Architecture: 7 Fixed Core Engines (E1..E7)     |
//| + Optional S6 Shadow-Only Compare Module.                        |
//| v1.01 Hardened: HistorySelect traded-day hydration, mid-window   |
//| E1/E4 box guard, ServerNow(), 23-date NYSE block on E4/E5/E7,    |
//| Sunday open WEEKEND_GAP_FAILSAFE_SWAP0 flatten.                  |
//|                                                                  |
//| PURE SIGNAL ONLY: contains ZERO CTrade / OrderSend calls.        |
//| Emits structured NaqexSignalIntent records to Master Authority.  |
//| Uses CopyTicksRange cursor for breakouts + M1 history fallback   |
//| so mid-day restarts reconstruct E1 Tokyo Box & E4 Morning Range. |
//+------------------------------------------------------------------+
#ifndef NAQEX_SIGNALS_7E_MQH
#define NAQEX_SIGNALS_7E_MQH

#include "Naqex_PropGuard.mqh"

#define NAQEX_MAX_INTENTS 16
#define NAQEX_SYM_COUNT   8

enum ENUM_NAQEX_SYM_IDX
{
   SYM_USDJPY = 0,
   SYM_GBPUSD = 1,
   SYM_EURJPY = 2,
   SYM_US100  = 3,
   SYM_US500  = 4,
   SYM_EURUSD = 5,
   SYM_AUDUSD = 6,
   SYM_USDCAD = 7
};

struct NaqexSignalIntent
{
   string   intent_id;
   string   opportunity_id;
   int      opp_eval_count;
   bool     opp_is_new;
   string   engine_id;
   long     magic;
   string   symbol;
   bool     is_buy;
   double   signal_price;
   double   sl_price;
   double   base_risk_pct;
   datetime signal_utc;
   long     tick_lag_ms;
   bool     shadow_only;
   datetime session_day_key;
   string   tag;
};

#define NAQEX_MAX_OPP_EVENTS 32

struct NaqexOppEpisode
{
   bool     active;
   string   opp_id;
   string   engine_id;
   long     magic;
   string   symbol;
   datetime session_day;
   int      side;              // +1 BUY, -1 SELL, 0 NONE
   datetime opened_utc;
   double   open_signal_price;
   int      eval_count;
   int      block_count;
   int      blk_lmin;
   int      blk_cap;
   int      blk_spread;
   int      blk_news;
   int      blk_other;
   string   last_block_key;
   int      ep_seq;
   datetime ep_seq_day;
};

struct NaqexOppTransition
{
   string   event_type;        // OPP_START, OPP_EXPIRED
   string   opp_id;
   string   engine_id;
   long     magic;
   string   symbol;
   bool     is_buy;
   datetime utc_ts;
   double   signal_price;
   int      eval_count;
   int      block_count;
   int      blk_lmin;
   int      blk_cap;
   int      blk_spread;
   int      blk_news;
   int      blk_other;
   string   last_block_key;
   string   reason;
};

struct NaqexSymbolFeedState
{
   string symbol;
   int    atr_handle;
   long   last_tick_msc;
   double last_bid;
   double last_ask;
   long   last_lag_ms;
   bool   has_fresh_tick;
};

class CNaqexSignals7E
{
private:
   NaqexSymbolFeedState m_feeds[NAQEX_SYM_COUNT];
   datetime             m_tradedDay[8]; // 0..6 = E1..E7, 7 = S6
   bool                 m_tradedDayHydrated;
   int                  m_intentSeq;
   int                  m_maxBreakoutLagMs;
   bool                 m_enableS6Shadow;
   int                  m_atrPeriod;

   // E1 Tokyo Box state
   datetime             m_e1BoxDay;
   bool                 m_e1BoxReady;
   double               m_e1BoxTop;
   double               m_e1BoxBot;

   // E4 US100 Morning Drive state
   datetime             m_e4SessDay;
   bool                 m_e4MornInit;
   bool                 m_e4MornFrozen;
   double               m_e4MornOpen;
   double               m_e4MornHigh;
   double               m_e4MornLow;
   double               m_e4MornClose;
   int                  m_e4MornDir;

   // E5 & E7 09:30 ET anchor state
   datetime             m_nyAnchorDay;
   bool                 m_nyAnchorReady;
   bool                 m_nyAnchorJustLocked;
   datetime             m_nyAnchorLockedUtc;
   datetime             m_nyAnchorLastTry;
   double               m_us100Open0930;
   double               m_us500Open0930;

   // Daily D1 ATR & E6 vol-compression cache (immutable intraday — shift=1 closed D1 bars only!)
   datetime             m_d1AtrCacheDay[NAQEX_SYM_COUNT];
   double               m_d1AtrCacheVal[NAQEX_SYM_COUNT];
   datetime             m_e6CompCacheDay;
   bool                 m_e6CompCacheOk;
   datetime             m_e1ReconstLastTry;

   // Base risk % per engine (exact Registry values)
   double               m_baseRisk[8];

   // v1.02-B opt-in opportunity lifecycle state (0 = frozen v1.01, 1 = stable opportunity_id + setup-validity expiry)
   int                  m_oppLifecycleMode;
   NaqexOppEpisode      m_opp[8];
   NaqexOppTransition   m_oppEvents[NAQEX_MAX_OPP_EVENTS];
   int                  m_oppEventCount;

   void ResetOppEpisode(const int idx)
   {
      if(idx < 0 || idx >= 8) return;
      m_opp[idx].active            = false;
      m_opp[idx].opp_id            = "";
      m_opp[idx].engine_id         = "";
      m_opp[idx].magic             = 0;
      m_opp[idx].symbol            = "";
      m_opp[idx].session_day       = 0;
      m_opp[idx].side              = 0;
      m_opp[idx].opened_utc        = 0;
      m_opp[idx].open_signal_price = 0.0;
      m_opp[idx].eval_count        = 0;
      m_opp[idx].block_count       = 0;
      m_opp[idx].blk_lmin          = 0;
      m_opp[idx].blk_cap           = 0;
      m_opp[idx].blk_spread        = 0;
      m_opp[idx].blk_news          = 0;
      m_opp[idx].blk_other         = 0;
      m_opp[idx].last_block_key    = "";
      m_opp[idx].ep_seq            = 0;
      m_opp[idx].ep_seq_day        = 0;
   }

   static string FormatOppBlockBreakdown(const int bLmin, const int bCap, const int bSpr, const int bNews, const int bOth)
   {
      string s = "";
      if(bLmin > 0) s += (s == "" ? "" : ",") + StringFormat("lmin:%d", bLmin);
      if(bCap  > 0) s += (s == "" ? "" : ",") + StringFormat("cap:%d", bCap);
      if(bSpr  > 0) s += (s == "" ? "" : ",") + StringFormat("spread:%d", bSpr);
      if(bNews > 0) s += (s == "" ? "" : ",") + StringFormat("news:%d", bNews);
      if(bOth  > 0) s += (s == "" ? "" : ",") + StringFormat("other:%d", bOth);
      return s;
   }

   void PushOppTransition(const string evType, const NaqexOppEpisode &ep, const datetime nowUtc,
                          const double sigPx, const string reason)
   {
      if(m_oppEventCount >= NAQEX_MAX_OPP_EVENTS) return;
      m_oppEvents[m_oppEventCount].event_type     = evType;
      m_oppEvents[m_oppEventCount].opp_id         = ep.opp_id;
      m_oppEvents[m_oppEventCount].engine_id      = ep.engine_id;
      m_oppEvents[m_oppEventCount].magic          = ep.magic;
      m_oppEvents[m_oppEventCount].symbol         = ep.symbol;
      m_oppEvents[m_oppEventCount].is_buy         = (ep.side > 0);
      m_oppEvents[m_oppEventCount].utc_ts         = nowUtc;
      m_oppEvents[m_oppEventCount].signal_price   = sigPx;
      m_oppEvents[m_oppEventCount].eval_count     = ep.eval_count;
      m_oppEvents[m_oppEventCount].block_count    = ep.block_count;
      m_oppEvents[m_oppEventCount].blk_lmin       = ep.blk_lmin;
      m_oppEvents[m_oppEventCount].blk_cap        = ep.blk_cap;
      m_oppEvents[m_oppEventCount].blk_spread     = ep.blk_spread;
      m_oppEvents[m_oppEventCount].blk_news       = ep.blk_news;
      m_oppEvents[m_oppEventCount].blk_other      = ep.blk_other;
      m_oppEvents[m_oppEventCount].last_block_key = ep.last_block_key;
      m_oppEvents[m_oppEventCount].reason         = reason;
      m_oppEventCount++;
   }

   void ExpireOppIfActive(const int idx, const datetime nowUtc, const double sigPx, const string reason)
   {
      if(m_oppLifecycleMode != 1 || idx < 0 || idx >= 8) return;
      if(!m_opp[idx].active) return;
      PushOppTransition("OPP_EXPIRED", m_opp[idx], nowUtc, sigPx, reason);
      m_opp[idx].active            = false;
      m_opp[idx].opp_id            = "";
      m_opp[idx].side              = 0;
      m_opp[idx].opened_utc        = 0;
      m_opp[idx].open_signal_price = 0.0;
      m_opp[idx].eval_count        = 0;
      m_opp[idx].block_count       = 0;
      m_opp[idx].blk_lmin          = 0;
      m_opp[idx].blk_cap           = 0;
      m_opp[idx].blk_spread        = 0;
      m_opp[idx].blk_news          = 0;
      m_opp[idx].blk_other         = 0;
      m_opp[idx].last_block_key    = "";
   }

   // Update opportunity episode for a setup engine inside its valid session when fresh tick is observed.
   // NOTE: On tick gaps (!hasFreshTick), callers MUST NOT call this with curSide=0 — tick gaps mean
   // unobserved state only and NEVER imply price left the setup zone!
   void UpdateSetupOppOnObservedTick(const int idx, const string engShort, const string engId, const long magic,
                                     const string sym, const datetime curDay, const datetime nowUtc,
                                     const int curSide, const double curPx,
                                     string &outOppId, int &outEvalCount, bool &outIsNew)
   {
      outOppId = ""; outEvalCount = 0; outIsNew = false;
      if(m_oppLifecycleMode != 1 || idx < 0 || idx >= 8) return;
      if(m_opp[idx].active && m_opp[idx].session_day != curDay)
         ExpireOppIfActive(idx, nowUtc, curPx, "SESSION_ENDED");
      if(m_opp[idx].active && curSide != m_opp[idx].side)
         ExpireOppIfActive(idx, nowUtc, curPx, "PRICE_CONDITION_LOST");
      if(!m_opp[idx].active && curSide != 0)
      {
         if(m_opp[idx].ep_seq_day != curDay)
         {
            m_opp[idx].ep_seq     = 0;
            m_opp[idx].ep_seq_day = curDay;
         }
         m_opp[idx].ep_seq++;
         m_opp[idx].active            = true;
         m_opp[idx].opp_id            = StringFormat("OPP_%s_%I64d_%d", engShort, (long)curDay, m_opp[idx].ep_seq);
         m_opp[idx].engine_id         = engId;
         m_opp[idx].magic             = magic;
         m_opp[idx].symbol            = sym;
         m_opp[idx].session_day       = curDay;
         m_opp[idx].side              = curSide;
         m_opp[idx].opened_utc        = nowUtc;
         m_opp[idx].open_signal_price = curPx;
         m_opp[idx].eval_count        = 0;
         m_opp[idx].block_count       = 0;
         m_opp[idx].blk_lmin          = 0;
         m_opp[idx].blk_cap           = 0;
         m_opp[idx].blk_spread        = 0;
         m_opp[idx].blk_news          = 0;
         m_opp[idx].blk_other         = 0;
         m_opp[idx].last_block_key    = "";
         PushOppTransition("OPP_START", m_opp[idx], nowUtc, curPx, "PRICE_CONDITION_ENTERED");
         outIsNew = true;
      }
      if(m_opp[idx].active && curSide == m_opp[idx].side)
      {
         m_opp[idx].eval_count++;
         outOppId     = m_opp[idx].opp_id;
         outEvalCount = m_opp[idx].eval_count;
      }
   }

   static int LastSundayOfMonth(const int year, const int month)
   {
      MqlDateTime d; ZeroMemory(d); d.year = year; d.mon = month; d.day = 31;
      TimeToStruct(StructToTime(d), d);
      return 31 - d.day_of_week;
   }

   static int HelsinkiUtcOffsetHours(const MqlDateTime &utc)
   {
      if(utc.mon < 3 || utc.mon > 10) return 2;
      if(utc.mon > 3 && utc.mon < 10) return 3;
      int ls = LastSundayOfMonth(utc.year, utc.mon);
      if(utc.mon == 3) return (utc.day > ls || (utc.day == ls && utc.hour >= 1)) ? 3 : 2;
      return (utc.day < ls || (utc.day == ls && utc.hour < 1)) ? 3 : 2;
   }

   static int NewYorkUtcOffsetHours(const MqlDateTime &utc)
   {
      if(utc.mon < 3 || utc.mon > 11) return -5;
      if(utc.mon > 3 && utc.mon < 11) return -4;
      if(utc.mon == 3)
      {
         int s2 = CNaqexPropGuard::NthSundayOfMonth(utc.year, 3, 2);
         return (utc.day > s2 || (utc.day == s2 && utc.hour >= 7)) ? -4 : -5;
      }
      int s1 = CNaqexPropGuard::NthSundayOfMonth(utc.year, 11, 1);
      return (utc.day < s1 || (utc.day == s1 && utc.hour < 6)) ? -4 : -5;
   }

   static string ResolveBrokerAlias(const string preferred, const string alt1, const string alt2)
   {
      if(preferred != "" && SymbolSelect(preferred, true)) return preferred;
      if(alt1 != "" && SymbolSelect(alt1, true)) return alt1;
      if(alt2 != "" && SymbolSelect(alt2, true)) return alt2;
      return preferred;
   }

   bool ReadPriorD1Atr(const int idx, double &outAtr)
   {
      outAtr = 0.0;
      if(idx < 0 || idx >= NAQEX_SYM_COUNT || m_feeds[idx].atr_handle == INVALID_HANDLE) return false;
      datetime d1Bar = iTime(m_feeds[idx].symbol, PERIOD_D1, 0);
      if(d1Bar > 0 && m_d1AtrCacheDay[idx] == d1Bar && m_d1AtrCacheVal[idx] > 0.0)
      {
         outAtr = m_d1AtrCacheVal[idx];
         return true;
      }
      double buf[1];
      // Strict causal shift=1 (prior completed D1 bar ONLY!)
      if(CopyBuffer(m_feeds[idx].atr_handle, 0, 1, 1, buf) != 1 || buf[0] <= 0.0) return false;
      m_d1AtrCacheDay[idx] = d1Bar;
      m_d1AtrCacheVal[idx] = buf[0];
      outAtr = buf[0];
      return true;
   }

   // Reconstruct [startUtc, endUtc) M1 high/low/open/close from broker history (restart resilience + V101-03 ServerNow!)
   bool ReconstructM1Window(const string sym, const datetime nowUtc, const datetime startUtc, const datetime endUtc,
                            double &outOpen, double &outHigh, double &outLow, double &outClose) const
   {
      long srvMinusUtc = (long)CNaqexPropGuard::ServerNow() - (long)nowUtc;
      datetime srvStart = startUtc + (datetime)srvMinusUtc;
      datetime srvEnd   = endUtc + (datetime)srvMinusUtc - 1;
      if(srvEnd < srvStart) return false;
      MqlRates rates[];
      int copied = CopyRates(sym, PERIOD_M1, srvStart, srvEnd, rates);
      if(copied <= 0) return false;
      outOpen  = rates[0].open;
      outHigh  = rates[0].high;
      outLow   = rates[0].low;
      outClose = rates[copied - 1].close;
      for(int i = 1; i < copied; i++)
      {
         if(rates[i].high > outHigh) outHigh = rates[i].high;
         if(rates[i].low  < outLow)  outLow  = rates[i].low;
      }
      return (outHigh > 0.0 && outLow > 0.0);
   }

   string NextIntentId(const string engineId, const datetime nowUtc)
   {
      m_intentSeq++;
      return StringFormat("%s_%I64d_%d", engineId, (long)nowUtc, m_intentSeq);
   }

   void PushIntent(NaqexSignalIntent &outIntents[], int &count, const NaqexSignalIntent &item) const
   {
      if(count >= NAQEX_MAX_INTENTS) return;
      outIntents[count] = item;
      count++;
   }

public:
   CNaqexSignals7E()
   {
      m_tradedDayHydrated = false;
      m_intentSeq        = 0;
      m_maxBreakoutLagMs = 5000;
      m_enableS6Shadow   = true;
      m_atrPeriod        = 14;
      m_e1BoxDay         = 0; m_e1BoxReady = false; m_e1BoxTop = 0.0; m_e1BoxBot = 0.0;
      m_e4SessDay        = 0; m_e4MornInit = false; m_e4MornFrozen = false;
      m_e4MornOpen       = 0.0; m_e4MornHigh = 0.0; m_e4MornLow = 0.0; m_e4MornClose = 0.0; m_e4MornDir = 0;
      m_nyAnchorDay      = 0; m_nyAnchorReady = false; m_nyAnchorJustLocked = false; m_nyAnchorLockedUtc = 0; m_nyAnchorLastTry = 0; m_us100Open0930 = 0.0; m_us500Open0930 = 0.0;
      m_e6CompCacheDay   = 0; m_e6CompCacheOk = false; m_e1ReconstLastTry = 0;
      for(int s = 0; s < NAQEX_SYM_COUNT; s++) { m_d1AtrCacheDay[s] = 0; m_d1AtrCacheVal[s] = 0.0; }
      for(int i = 0; i < 8; i++) { m_tradedDay[i] = 0; ResetOppEpisode(i); }
      m_oppLifecycleMode = 0;
      m_oppEventCount    = 0;
      // Registry exact base risk percentages (E1..E7 + S6)
      m_baseRisk[0] = 0.16; // E1_USDJPY_TOKYO
      m_baseRisk[1] = 0.59; // E2_USDJPY_EXP80
      m_baseRisk[2] = 0.75; // E3_GBPUSD_VH
      m_baseRisk[3] = 0.50; // E4_US100_SESS40
      m_baseRisk[4] = 0.50; // E5_US100_RS1130
      m_baseRisk[5] = 0.50; // E6_EURJPY_VOLCOMP
      m_baseRisk[6] = 0.50; // E7_USDJPY_NY10ET
      m_baseRisk[7] = 0.50; // S6_FX_USD_BSK (shadow compare)
      for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      {
         m_feeds[s].symbol = "";
         m_feeds[s].atr_handle = INVALID_HANDLE;
         m_feeds[s].last_tick_msc = 0;
         m_feeds[s].last_bid = 0.0;
         m_feeds[s].last_ask = 0.0;
         m_feeds[s].last_lag_ms = 0;
         m_feeds[s].has_fresh_tick = false;
      }
   }

   bool Init(const string symUsdjpy, const string symGbpusd, const string symEurjpy,
             const string symUs100, const string symUs500,
             const string symEurusd, const string symAudusd, const string symUsdcad,
             const int maxBreakoutLagMs = 5000, const bool enableS6Shadow = true,
             const int oppLifecycleMode = 0)
   {
      m_maxBreakoutLagMs = maxBreakoutLagMs;
      m_enableS6Shadow   = enableS6Shadow;
      m_oppLifecycleMode = oppLifecycleMode;
      m_oppEventCount    = 0;
      m_nyAnchorJustLocked = false;
      m_nyAnchorLockedUtc  = 0;
      for(int i = 0; i < 8; i++) ResetOppEpisode(i);
      m_feeds[SYM_USDJPY].symbol = ResolveBrokerAlias(symUsdjpy, "USDJPY.pro", "USDJPY");
      m_feeds[SYM_GBPUSD].symbol = ResolveBrokerAlias(symGbpusd, "GBPUSD.pro", "GBPUSD");
      m_feeds[SYM_EURJPY].symbol = ResolveBrokerAlias(symEurjpy, "EURJPY.pro", "EURJPY");
      m_feeds[SYM_US100].symbol  = ResolveBrokerAlias(symUs100,  "NAS100",     "USTEC");
      m_feeds[SYM_US500].symbol  = ResolveBrokerAlias(symUs500,  "SPX500",     "US500");
      m_feeds[SYM_EURUSD].symbol = ResolveBrokerAlias(symEurusd, "EURUSD.pro", "EURUSD");
      m_feeds[SYM_AUDUSD].symbol = ResolveBrokerAlias(symAudusd, "AUDUSD.pro", "AUDUSD");
      m_feeds[SYM_USDCAD].symbol = ResolveBrokerAlias(symUsdcad, "USDCAD.pro", "USDCAD");

      for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      {
         if(!SymbolSelect(m_feeds[s].symbol, true))
         {
            PrintFormat("[SIGNALS-7E-ERR] SymbolSelect failed for idx=%d sym=%s", s, m_feeds[s].symbol);
            return false;
         }
         m_feeds[s].atr_handle = iATR(m_feeds[s].symbol, PERIOD_D1, m_atrPeriod);
         if(m_feeds[s].atr_handle == INVALID_HANDLE)
         {
            PrintFormat("[SIGNALS-7E-ERR] iATR handle failed for %s", m_feeds[s].symbol);
            return false;
         }
         MqlTick tk;
         if(SymbolInfoTick(m_feeds[s].symbol, tk))
         {
            m_feeds[s].last_tick_msc = tk.time_msc;
            m_feeds[s].last_bid = tk.bid;
            m_feeds[s].last_ask = tk.ask;
         }
      }
      return true;
   }

   void Deinit()
   {
      for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      {
         if(m_feeds[s].atr_handle != INVALID_HANDLE)
         {
            IndicatorRelease(m_feeds[s].atr_handle);
            m_feeds[s].atr_handle = INVALID_HANDLE;
         }
      }
   }

   string SymbolAt(const int idx) const { return (idx >= 0 && idx < NAQEX_SYM_COUNT) ? m_feeds[idx].symbol : ""; }

   static int EngineIndexFromMagic(const long magic)
   {
      if(magic == 20261122) return 0; // E1
      if(magic == 20261123) return 1; // E2
      if(magic == 20261125) return 2; // E3
      if(magic == 20261124) return 3; // E4
      if(magic == 20261126) return 4; // E5
      if(magic == 20261128) return 5; // E6
      if(magic == 20261129) return 6; // E7
      if(magic == 20261127) return 7; // S6
      return -1;
   }

   void MarkEngineTraded(const long magic, const datetime dayKey)
   {
      int idx = EngineIndexFromMagic(magic);
      if(idx >= 0 && idx < 8)
      {
         m_tradedDay[idx] = dayKey;
         // Clear active opportunity silently when engine completes trade (caller emits OPP_ACCEPTED)
         if(m_oppLifecycleMode == 1 && m_opp[idx].active)
         {
            m_opp[idx].active            = false;
            m_opp[idx].opp_id            = "";
            m_opp[idx].side              = 0;
            m_opp[idx].opened_utc        = 0;
            m_opp[idx].open_signal_price = 0.0;
            m_opp[idx].eval_count        = 0;
            m_opp[idx].block_count       = 0;
            m_opp[idx].blk_lmin          = 0;
            m_opp[idx].blk_cap           = 0;
            m_opp[idx].blk_spread        = 0;
            m_opp[idx].blk_news          = 0;
            m_opp[idx].blk_other         = 0;
            m_opp[idx].last_block_key    = "";
         }
      }
   }

   int DrainOppTransitions(NaqexOppTransition &outEvents[])
   {
      int n = m_oppEventCount;
      for(int i = 0; i < n; i++)
         outEvents[i] = m_oppEvents[i];
      m_oppEventCount = 0;
      return n;
   }

   static string FormatTransitionBlockBreakdown(const NaqexOppTransition &ev)
   {
      return FormatOppBlockBreakdown(ev.blk_lmin, ev.blk_cap, ev.blk_spread, ev.blk_news, ev.blk_other);
   }

   bool RecordOpportunityBlocked(const long magic, const string category, const string blockKey,
                                 int &outBlockCount, int &outEvalCount)
   {
      outBlockCount = 0; outEvalCount = 0;
      if(m_oppLifecycleMode != 1) return false;
      int idx = EngineIndexFromMagic(magic);
      if(idx < 0 || idx >= 8 || !m_opp[idx].active) return false;
      m_opp[idx].block_count++;
      if(category == "LMIN")        m_opp[idx].blk_lmin++;
      else if(category == "CAP")    m_opp[idx].blk_cap++;
      else if(category == "SPREAD") m_opp[idx].blk_spread++;
      else if(category == "NEWS")   m_opp[idx].blk_news++;
      else                          m_opp[idx].blk_other++;
      outBlockCount = m_opp[idx].block_count;
      outEvalCount  = m_opp[idx].eval_count;
      bool changed  = (m_opp[idx].block_count == 1 || m_opp[idx].last_block_key != blockKey);
      m_opp[idx].last_block_key = blockKey;
      return changed;
   }

   void GetOpportunityStats(const long magic, int &outEvalCount, int &outBlockCount,
                            string &outLastBlockKey, string &outBreakdown) const
   {
      outEvalCount = 0; outBlockCount = 0; outLastBlockKey = ""; outBreakdown = "";
      int idx = EngineIndexFromMagic(magic);
      if(idx < 0 || idx >= 8 || !m_opp[idx].active) return;
      outEvalCount    = m_opp[idx].eval_count;
      outBlockCount   = m_opp[idx].block_count;
      outLastBlockKey = m_opp[idx].last_block_key;
      outBreakdown    = FormatOppBlockBreakdown(m_opp[idx].blk_lmin, m_opp[idx].blk_cap,
                                                m_opp[idx].blk_spread, m_opp[idx].blk_news,
                                                m_opp[idx].blk_other);
   }

   bool ConsumeNyAnchorJustLocked(datetime &outUtc, double &outUs100, double &outUs500)
   {
      if(!m_nyAnchorJustLocked) return false;
      m_nyAnchorJustLocked = false;
      outUtc   = m_nyAnchorLockedUtc;
      outUs100 = m_us100Open0930;
      outUs500 = m_us500Open0930;
      return true;
   }

   bool IsEngineTraded(const int idx, const datetime dayKey) const
   {
      return (idx >= 0 && idx < 8 && m_tradedDay[idx] == dayKey);
   }

   bool IsTradedDayHydrated() const
   {
      return m_tradedDayHydrated;
   }

   // V101-02 (OPS-01): Hydrate m_tradedDay[8] from 48h deal history + open positions after mid-day restart!
   // Fail-closed: returns false (blocking new entries until retry succeeds) if HistorySelect fails while live.
   bool HydrateTradedDaysFromHistory(const datetime nowUtc)
   {
      if(MQLInfoInteger(MQL_TESTER))
      {
         m_tradedDayHydrated = true;
         return true;
      }
      datetime srvNow = CNaqexPropGuard::ServerNow();
      if(srvNow <= 0 || nowUtc <= 0)
      {
         m_tradedDayHydrated = false;
         return false;
      }
      if(!HistorySelect(srvNow - 48 * 3600, srvNow + 60))
      {
         m_tradedDayHydrated = false;
         return false;
      }

      long srvMinusUtc = (long)srvNow - (long)nowUtc;
      datetime curUtcDay = nowUtc - (nowUtc % 86400);
      MqlDateTime curUtcDt; TimeToStruct(nowUtc, curUtcDt);
      datetime curNy = nowUtc + (datetime)(NewYorkUtcOffsetHours(curUtcDt) * 3600);
      datetime curNyDay = curNy - (curNy % 86400);

      int nDeals = HistoryDealsTotal();
      for(int i = 0; i < nDeals; i++)
      {
         ulong dtk = HistoryDealGetTicket(i);
         if(dtk == 0) continue;
         long dEntry = HistoryDealGetInteger(dtk, DEAL_ENTRY);
         if(dEntry != DEAL_ENTRY_IN) continue;
         long dType = HistoryDealGetInteger(dtk, DEAL_TYPE);
         if(dType != DEAL_TYPE_BUY && dType != DEAL_TYPE_SELL) continue;
         long dMagic = HistoryDealGetInteger(dtk, DEAL_MAGIC);
         int idx = EngineIndexFromMagic(dMagic);
         if(idx < 0 || idx >= 8) continue;

         datetime dealSrv = (datetime)HistoryDealGetInteger(dtk, DEAL_TIME);
         datetime dealUtc = dealSrv - (datetime)srvMinusUtc;
         if(idx == 0 || idx == 7)
         {
            datetime dUtcDay = dealUtc - (dealUtc % 86400);
            if(dUtcDay > m_tradedDay[idx]) m_tradedDay[idx] = dUtcDay;
         }
         else if(idx == 1 || idx == 2 || idx == 5)
         {
            int symIdx = (idx == 1) ? SYM_USDJPY : ((idx == 2) ? SYM_GBPUSD : SYM_EURJPY);
            datetime d1Bar = iTime(m_feeds[symIdx].symbol, PERIOD_D1, 0);
            if(d1Bar > 0 && dealSrv >= d1Bar)
               m_tradedDay[idx] = d1Bar;
         }
         else
         {
            MqlDateTime du; TimeToStruct(dealUtc, du);
            datetime dNy = dealUtc + (datetime)(NewYorkUtcOffsetHours(du) * 3600);
            datetime dNyDay = dNy - (dNy % 86400);
            if(dNyDay > m_tradedDay[idx]) m_tradedDay[idx] = dNyDay;
         }
      }

      // Also mark any currently open position's engine as traded for its active session day
      for(int p = PositionsTotal() - 1; p >= 0; p--)
      {
         ulong ptk = PositionGetTicket(p);
         if(ptk == 0) continue;
         int idx = EngineIndexFromMagic(PositionGetInteger(POSITION_MAGIC));
         if(idx < 0 || idx >= 8) continue;
         if(idx == 0 || idx == 7)
            m_tradedDay[idx] = curUtcDay;
         else if(idx == 1 || idx == 2 || idx == 5)
         {
            int symIdx = (idx == 1) ? SYM_USDJPY : ((idx == 2) ? SYM_GBPUSD : SYM_EURJPY);
            datetime d1Bar = iTime(m_feeds[symIdx].symbol, PERIOD_D1, 0);
            if(d1Bar > 0) m_tradedDay[idx] = d1Bar;
         }
         else
            m_tradedDay[idx] = curNyDay;
      }

      m_tradedDayHydrated = true;
      return true;
   }

   // Poll all 8 symbols via CopyTicksRange cursor (handles duplicate ms & records decision tick lag)
   long PollSymbolTicks()
   {
      long maxLagMs = 0;
      long srvNowMsc = (long)CNaqexPropGuard::ServerNow() * 1000;
      bool isTester = (MQLInfoInteger(MQL_TESTER) != 0);
      for(int s = 0; s < NAQEX_SYM_COUNT; s++)
      {
         m_feeds[s].has_fresh_tick = false;
         int copied = 0;
         MqlTick ticks[];
         if(!isTester)
         {
            long fromMsc = (m_feeds[s].last_tick_msc > 0) ? (m_feeds[s].last_tick_msc + 1) : (srvNowMsc - 5000);
            copied = CopyTicksRange(m_feeds[s].symbol, ticks, COPY_TICKS_INFO, (ulong)MathMax((long)0, fromMsc));
         }
         if(copied > 0)
         {
            MqlTick last = ticks[copied - 1];
            if(last.bid > 0.0 && last.ask > 0.0)
            {
               m_feeds[s].last_tick_msc = last.time_msc;
               m_feeds[s].last_bid = last.bid;
               m_feeds[s].last_ask = last.ask;
               long lag = MathMax((long)0, srvNowMsc - last.time_msc);
               m_feeds[s].last_lag_ms = lag;
               m_feeds[s].has_fresh_tick = (lag <= m_maxBreakoutLagMs || isTester);
               if(lag > maxLagMs) maxLagMs = lag;
            }
         }
         else
         {
            MqlTick tk;
            if(SymbolInfoTick(m_feeds[s].symbol, tk) && tk.bid > 0.0 && tk.ask > 0.0)
            {
               m_feeds[s].last_tick_msc = tk.time_msc;
               m_feeds[s].last_bid = tk.bid;
               m_feeds[s].last_ask = tk.ask;
               long lag = MathMax((long)0, srvNowMsc - tk.time_msc);
               m_feeds[s].last_lag_ms = lag;
               m_feeds[s].has_fresh_tick = (lag <= m_maxBreakoutLagMs || isTester);
               if(lag > maxLagMs) maxLagMs = lag;
            }
         }
      }
      return maxLagMs;
   }

   // Check whether a given engine magic should hard-flatten by clock / holiday half-day / Sunday gap
   bool ShouldClockFlattenMagic(const long magic, const datetime nowUtc, string &outReason) const
   {
      outReason = "";
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      if(utc.day_of_week == 6) return false;
      // V101-04: Flatten any stranded Friday position immediately on Sunday market open (swap=0 failsafe!)
      if(utc.day_of_week == 0)
      {
         if(utc.hour >= 21) { outReason = "WEEKEND_GAP_FAILSAFE_SWAP0"; return true; }
         return false;
      }
      if(magic == 20261122) // E1 Helsinki 18:00
      {
         int flatH = 18 - HelsinkiUtcOffsetHours(utc);
         if(utc.hour >= flatH) { outReason = "HARD_FLAT_18H_HELSINKI_SWAP0"; return true; }
         return false;
      }
      if(magic == 20261124 || magic == 20261126) // E4, E5 US100 15:55 ET + US holiday/half-day
      {
         datetime nowNy = nowUtc + (datetime)(NewYorkUtcOffsetHours(utc) * 3600);
         MqlDateTime ny; TimeToStruct(nowNy, ny);
         int nyMins = ny.hour * 60 + ny.min;
         if(CNaqexPropGuard::IsUsEquityHalfDayNY(ny)) { outReason = "HARD_FLAT_US_HALF_DAY_SWAP0"; return true; }
         if(nyMins >= 15 * 60 + 55) { outReason = "HARD_FLAT_1555_ET_SWAP0"; return true; }
         if(nyMins < 9 * 60 + 30) { outReason = "OVERNIGHT_FAILSAFE_SWAP0"; return true; }
         return false;
      }
      // E2, E3, E6, E7, S6 -> 20:55 UTC hard flat
      if(utc.hour > 20 || (utc.hour == 20 && utc.min >= 55))
      {
         outReason = "HARD_FLAT_2055_UTC_SWAP0";
         return true;
      }
      return false;
   }

   // Evaluate all 7 core engines + optional S6 shadow and return array of intents (ZERO OrderSend!)
   int CollectIntents(const datetime nowUtc, NaqexSignalIntent &outIntents[])
   {
      int count = 0;
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      if(utc.day_of_week == 0 || utc.day_of_week == 6)
      {
         for(int i = 0; i < 7; i++)
            ExpireOppIfActive(i, nowUtc, 0.0, "SESSION_ENDED");
         return 0;
      }

      datetime utcDay = nowUtc - (nowUtc % 86400);
      datetime nowNy  = nowUtc + (datetime)(NewYorkUtcOffsetHours(utc) * 3600);
      MqlDateTime ny; TimeToStruct(nowNy, ny);
      datetime nyDay  = nowNy - (nowNy % 86400);
      int nyMins      = ny.hour * 60 + ny.min;
      bool isUsHalf   = CNaqexPropGuard::IsUsEquityHolidayOrHalfDayNY(ny);

      // --- E1: TOKYO_BOX_OCO (USDJPY) ---
      {
         string sym = m_feeds[SYM_USDJPY].symbol;
         double ask = m_feeds[SYM_USDJPY].last_ask;
         double bid = m_feeds[SYM_USDJPY].last_bid;
         if(utcDay != m_e1BoxDay)
         {
            m_e1BoxDay = utcDay; m_e1BoxReady = false; m_e1BoxTop = 0.0; m_e1BoxBot = 0.0;
         }
         if(utc.hour >= 0 && utc.hour < 3 && ask > 0.0 && bid > 0.0)
         {
            double mid = 0.5 * (ask + bid);
            if(!m_e1BoxReady)
            {
               // V101-02: Guard mid-window restart (>= 2m after 00:00 UTC) so partial box never shrinks slDist!
               if((nowUtc - utcDay) >= 120)
               {
                  if((nowUtc - m_e1ReconstLastTry) >= 15 || MQLInfoInteger(MQL_TESTER))
                  {
                     m_e1ReconstLastTry = nowUtc;
                     double o0, h0, l0, c0;
                     if(ReconstructM1Window(sym, nowUtc, utcDay, nowUtc, o0, h0, l0, c0) && h0 > 0.0 && l0 > 0.0)
                     {
                        m_e1BoxTop = MathMax(h0, mid);
                        m_e1BoxBot = MathMin(l0, mid);
                        m_e1BoxReady = true;
                     }
                     else if(MQLInfoInteger(MQL_TESTER))
                     {
                        m_e1BoxTop = mid; m_e1BoxBot = mid; m_e1BoxReady = true;
                     }
                  }
               }
               else
               {
                  m_e1BoxTop = mid; m_e1BoxBot = mid; m_e1BoxReady = true;
               }
            }
            else { if(mid > m_e1BoxTop) m_e1BoxTop = mid; if(mid < m_e1BoxBot) m_e1BoxBot = mid; }
         }
         else if(utc.hour >= 3 && !m_e1BoxReady && (nowUtc - m_e1ReconstLastTry) >= 60)
         {
            m_e1ReconstLastTry = nowUtc;
            // Restart resilience: reconstruct 00:00..03:00 UTC box from broker M1 bars!
            double o0, h0, l0, c0;
            if(ReconstructM1Window(sym, nowUtc, utcDay, utcDay + 3 * 3600, o0, h0, l0, c0) && h0 > l0)
            {
               m_e1BoxTop = h0; m_e1BoxBot = l0; m_e1BoxReady = true;
            }
         }
         int flatH = 18 - HelsinkiUtcOffsetHours(utc);
         bool e1InSession = (m_e1BoxReady && m_e1BoxTop > m_e1BoxBot && !IsEngineTraded(0, utcDay) &&
                             utc.hour >= 3 && utc.hour < 10 && utc.hour < flatH);
         if(!e1InSession)
         {
            ExpireOppIfActive(0, nowUtc, ask, IsEngineTraded(0, utcDay) ? "TRADED_FILLED" : "SESSION_ENDED");
         }
         else if(m_feeds[SYM_USDJPY].has_fresh_tick)
         {
            int curSide = (ask >= m_e1BoxTop) ? 1 : ((bid <= m_e1BoxBot) ? -1 : 0);
            double curPx = (curSide >= 0) ? ask : bid;
            string oppId = ""; int oppEval = 0; bool oppNew = false;
            UpdateSetupOppOnObservedTick(0, "E1", "E1_USDJPY_TOKYO", 20261122, sym, utcDay, nowUtc, curSide, curPx, oppId, oppEval, oppNew);
            if(curSide == 1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E1", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E1_USDJPY_TOKYO"; it.magic = 20261122;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = m_e1BoxBot;
               it.base_risk_pct = m_baseRisk[0]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = utcDay; it.tag = "Naqex_M_E1_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(curSide == -1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E1", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E1_USDJPY_TOKYO"; it.magic = 20261122;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = m_e1BoxTop;
               it.base_risk_pct = m_baseRisk[0]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = utcDay; it.tag = "Naqex_M_E1_SELL";
               PushIntent(outIntents, count, it);
            }
         }
      }

      // --- E2: EXP_DAILY_OPEN_080 (USDJPY) ---
      {
         string sym = m_feeds[SYM_USDJPY].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         bool e2InWindow = (utc.hour >= 7 && utc.hour < 17);
         if(!e2InWindow || IsEngineTraded(1, d1Start))
         {
            ExpireOppIfActive(1, nowUtc, m_feeds[SYM_USDJPY].last_ask, IsEngineTraded(1, d1Start) ? "TRADED_FILLED" : "SESSION_ENDED");
         }
         else if(m_feeds[SYM_USDJPY].has_fresh_tick && ReadPriorD1Atr(SYM_USDJPY, atrD1) && dayOpen > 0.0)
         {
            double ask = m_feeds[SYM_USDJPY].last_ask, bid = m_feeds[SYM_USDJPY].last_bid;
            int curSide = (ask >= dayOpen + 0.80 * atrD1) ? 1 : ((bid <= dayOpen - 0.80 * atrD1) ? -1 : 0);
            double curPx = (curSide >= 0) ? ask : bid;
            string oppId = ""; int oppEval = 0; bool oppNew = false;
            UpdateSetupOppOnObservedTick(1, "E2", "E2_USDJPY_EXP80", 20261123, sym, d1Start, nowUtc, curSide, curPx, oppId, oppEval, oppNew);
            if(curSide == 1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E2", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E2_USDJPY_EXP80"; it.magic = 20261123;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
               it.base_risk_pct = m_baseRisk[1]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E2_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(curSide == -1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E2", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E2_USDJPY_EXP80"; it.magic = 20261123;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.75 * atrD1;
               it.base_risk_pct = m_baseRisk[1]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E2_SELL";
               PushIntent(outIntents, count, it);
            }
         }
      }

      // --- E3: WB_EXP_80_VOL_HIGH (GBPUSD) ---
      {
         string sym = m_feeds[SYM_GBPUSD].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         bool e3InWindow = (utc.hour >= 7 && utc.hour < 17);
         if(!e3InWindow || IsEngineTraded(2, d1Start))
         {
            ExpireOppIfActive(2, nowUtc, m_feeds[SYM_GBPUSD].last_ask, IsEngineTraded(2, d1Start) ? "TRADED_FILLED" : "SESSION_ENDED");
         }
         else if(m_feeds[SYM_GBPUSD].has_fresh_tick && ReadPriorD1Atr(SYM_GBPUSD, atrD1) && dayOpen > 0.0)
         {
            double prevRng = iHigh(sym, PERIOD_D1, 1) - iLow(sym, PERIOD_D1, 1);
            if(prevRng >= 1.10 * atrD1)
            {
               double ask = m_feeds[SYM_GBPUSD].last_ask, bid = m_feeds[SYM_GBPUSD].last_bid;
               int curSide = (ask >= dayOpen + 0.80 * atrD1) ? 1 : ((bid <= dayOpen - 0.80 * atrD1) ? -1 : 0);
               double curPx = (curSide >= 0) ? ask : bid;
               string oppId = ""; int oppEval = 0; bool oppNew = false;
               UpdateSetupOppOnObservedTick(2, "E3", "E3_GBPUSD_VH", 20261125, sym, d1Start, nowUtc, curSide, curPx, oppId, oppEval, oppNew);
               if(curSide == 1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E3", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E3_GBPUSD_VH"; it.magic = 20261125;
                  it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[2]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_GBPUSD].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E3_BUY";
                  PushIntent(outIntents, count, it);
               }
               else if(curSide == -1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E3", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E3_GBPUSD_VH"; it.magic = 20261125;
                  it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[2]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_GBPUSD].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E3_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
            else
            {
               ExpireOppIfActive(2, nowUtc, m_feeds[SYM_GBPUSD].last_ask, "SETUP_INVALID");
            }
         }
      }

      // --- E6: EURJPY_VOLCOMP_EXP75 (EURJPY) ---
      {
         string sym = m_feeds[SYM_EURJPY].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         bool e6InWindow = (utc.hour >= 7 && utc.hour < 17);
         if(!e6InWindow || IsEngineTraded(5, d1Start))
         {
            ExpireOppIfActive(5, nowUtc, m_feeds[SYM_EURJPY].last_ask, IsEngineTraded(5, d1Start) ? "TRADED_FILLED" : "SESSION_ENDED");
         }
         else if(m_feeds[SYM_EURJPY].has_fresh_tick && ReadPriorD1Atr(SYM_EURJPY, atrD1) && dayOpen > 0.0)
         {
            if(m_e6CompCacheDay != d1Start)
            {
               double sum5 = 0.0, sum20 = 0.0;
               bool okComp = true;
               for(int s = 1; s <= 20; s++)
               {
                  double rng = iHigh(sym, PERIOD_D1, s) - iLow(sym, PERIOD_D1, s);
                  if(rng <= 0.0) { okComp = false; break; }
                  sum20 += rng;
                  if(s <= 5) sum5 += rng;
               }
               m_e6CompCacheDay = d1Start;
               m_e6CompCacheOk  = (okComp && ((sum5 / 5.0) / (sum20 / 20.0)) < 0.85);
            }
            if(!m_e6CompCacheOk)
            {
               ExpireOppIfActive(5, nowUtc, m_feeds[SYM_EURJPY].last_ask, "SETUP_INVALID");
            }
            else
            {
               double ask = m_feeds[SYM_EURJPY].last_ask, bid = m_feeds[SYM_EURJPY].last_bid;
               int curSide = (ask >= dayOpen + 0.75 * atrD1) ? 1 : ((bid <= dayOpen - 0.75 * atrD1) ? -1 : 0);
               double curPx = (curSide >= 0) ? ask : bid;
               string oppId = ""; int oppEval = 0; bool oppNew = false;
               UpdateSetupOppOnObservedTick(5, "E6", "E6_EURJPY_VOLCOMP", 20261128, sym, d1Start, nowUtc, curSide, curPx, oppId, oppEval, oppNew);
               if(curSide == 1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E6", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E6_EURJPY_VOLCOMP"; it.magic = 20261128;
                  it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[5]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_EURJPY].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E6_BUY";
                  PushIntent(outIntents, count, it);
               }
               else if(curSide == -1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E6", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E6_EURJPY_VOLCOMP"; it.magic = 20261128;
                  it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[5]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_EURJPY].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E6_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
      }

      // --- Shared NY 09:30 ET open anchor (with M1 history reconstruction on mid-day restart) ---
      if(nyDay != m_nyAnchorDay)
      {
         m_nyAnchorDay = nyDay; m_nyAnchorReady = false; m_us100Open0930 = 0.0; m_us500Open0930 = 0.0;
      }
      if(!m_nyAnchorReady && nyMins >= 9 * 60 + 30 && (nowUtc - m_nyAnchorLastTry) >= 60)
      {
         m_nyAnchorLastTry = nowUtc;
         int nyOffSec = NewYorkUtcOffsetHours(utc) * 3600;
         datetime t0930Utc = (nyDay + 9 * 3600 + 30 * 60) - (datetime)nyOffSec;
         double o1, h1, l1, c1, o2, h2, l2, c2;
         if(ReconstructM1Window(m_feeds[SYM_US100].symbol, nowUtc, t0930Utc - 60, t0930Utc + 60, o1, h1, l1, c1) &&
            ReconstructM1Window(m_feeds[SYM_US500].symbol, nowUtc, t0930Utc - 60, t0930Utc + 60, o2, h2, l2, c2))
         {
            m_us100Open0930 = c1; m_us500Open0930 = c2; m_nyAnchorReady = true;
            m_nyAnchorJustLocked = true; m_nyAnchorLockedUtc = nowUtc;
         }
      }

      // --- E4: SESS_CONT_BRK_40 (US100) ---
      if(!isUsHalf && nyMins < 15 * 60 + 55)
      {
         string sym = m_feeds[SYM_US100].symbol;
         if(nyDay != m_e4SessDay)
         {
            m_e4SessDay = nyDay; m_e4MornInit = false; m_e4MornFrozen = false; m_e4MornDir = 0;
         }
         double ask = m_feeds[SYM_US100].last_ask, bid = m_feeds[SYM_US100].last_bid;
         if(nyMins >= 9 * 60 + 30 && nyMins < 11 * 60 + 30 && bid > 0.0)
         {
            if(!m_e4MornInit)
            {
               // V101-02: Guard mid-window restart (>= 09:32 ET) by backfilling [09:30 ET .. now] from M1 bars
               if(nyMins >= 9 * 60 + 32)
               {
                  int nyOffSec = NewYorkUtcOffsetHours(utc) * 3600;
                  datetime tStartUtc = (nyDay + 9 * 3600 + 30 * 60) - (datetime)nyOffSec;
                  double o4, h4, l4, c4;
                  if(ReconstructM1Window(sym, nowUtc, tStartUtc, nowUtc, o4, h4, l4, c4) && h4 > 0.0 && l4 > 0.0)
                  {
                     m_e4MornOpen  = o4;
                     m_e4MornHigh  = MathMax(h4, bid);
                     m_e4MornLow   = MathMin(l4, bid);
                     m_e4MornClose = bid;
                     m_e4MornInit  = true;
                  }
                  else if(MQLInfoInteger(MQL_TESTER))
                  {
                     m_e4MornOpen = bid; m_e4MornHigh = bid; m_e4MornLow = bid; m_e4MornClose = bid; m_e4MornInit = true;
                  }
               }
               else
               {
                  m_e4MornOpen = bid; m_e4MornHigh = bid; m_e4MornLow = bid; m_e4MornClose = bid; m_e4MornInit = true;
               }
            }
            else { if(bid > m_e4MornHigh) m_e4MornHigh = bid; if(bid < m_e4MornLow) m_e4MornLow = bid; m_e4MornClose = bid; }
         }
         double atrUs100 = 0.0;
         if(!m_e4MornFrozen && nyMins >= 11 * 60 + 30 && ReadPriorD1Atr(SYM_US100, atrUs100))
         {
            if(!m_e4MornInit)
            {
               int nyOffSec = NewYorkUtcOffsetHours(utc) * 3600;
               datetime tStartUtc = (nyDay + 9 * 3600 + 30 * 60) - (datetime)nyOffSec;
               datetime tEndUtc   = (nyDay + 11 * 3600 + 30 * 60) - (datetime)nyOffSec;
               if(ReconstructM1Window(sym, nowUtc, tStartUtc, tEndUtc, m_e4MornOpen, m_e4MornHigh, m_e4MornLow, m_e4MornClose))
                  m_e4MornInit = true;
            }
            m_e4MornFrozen = true;
            double mrng = m_e4MornHigh - m_e4MornLow;
            if(m_e4MornInit && mrng > 0.0 && MathAbs(m_e4MornClose - m_e4MornOpen) >= 0.40 * atrUs100)
            {
               double pos = (m_e4MornClose - m_e4MornLow) / mrng;
               if(m_e4MornClose > m_e4MornOpen && pos >= 0.70) m_e4MornDir = 1;
               else if(m_e4MornClose < m_e4MornOpen && pos <= 0.30) m_e4MornDir = -1;
            }
         }
         bool e4InSession = (m_e4MornFrozen && m_e4MornDir != 0 && !IsEngineTraded(3, nyDay));
         if(!e4InSession)
         {
            ExpireOppIfActive(3, nowUtc, ask, IsEngineTraded(3, nyDay) ? "TRADED_FILLED" : "SESSION_ENDED");
         }
         else if(m_feeds[SYM_US100].has_fresh_tick && ReadPriorD1Atr(SYM_US100, atrUs100))
         {
            int curSide = (m_e4MornDir == 1 && ask >= m_e4MornHigh) ? 1 : ((m_e4MornDir == -1 && bid <= m_e4MornLow) ? -1 : 0);
            double curPx = (curSide >= 0) ? ask : bid;
            string oppId = ""; int oppEval = 0; bool oppNew = false;
            UpdateSetupOppOnObservedTick(3, "E4", "E4_US100_SESS40", 20261124, sym, nyDay, nowUtc, curSide, curPx, oppId, oppEval, oppNew);
            if(curSide == 1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E4", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E4_US100_SESS40"; it.magic = 20261124;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.65 * atrUs100;
               it.base_risk_pct = m_baseRisk[3]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
               it.shadow_only = false; it.session_day_key = nyDay; it.tag = "Naqex_M_E4_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(curSide == -1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E4", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
               it.engine_id = "E4_US100_SESS40"; it.magic = 20261124;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.65 * atrUs100;
               it.base_risk_pct = m_baseRisk[3]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
               it.shadow_only = false; it.session_day_key = nyDay; it.tag = "Naqex_M_E4_SELL";
               PushIntent(outIntents, count, it);
            }
         }
      }
      else
      {
         ExpireOppIfActive(3, nowUtc, m_feeds[SYM_US100].last_ask, "SESSION_ENDED");
      }

      // --- E5: IDX_RS_US100_LEAD_1130 (US100 vs US500, closed M1 bar) ---
      if(!isUsHalf && m_nyAnchorReady && !IsEngineTraded(4, nyDay) &&
         nyMins >= 11 * 60 + 30 && nyMins < 11 * 60 + 40 && m_feeds[SYM_US100].has_fresh_tick)
      {
         double atrMain = 0.0, atrBench = 0.0;
         if(ReadPriorD1Atr(SYM_US100, atrMain) && ReadPriorD1Atr(SYM_US500, atrBench))
         {
            double m1 = iClose(m_feeds[SYM_US100].symbol, PERIOD_M1, 1);
            double b1 = iClose(m_feeds[SYM_US500].symbol, PERIOD_M1, 1);
            if(m1 > 0.0 && b1 > 0.0)
            {
               double zMain = (m1 - m_us100Open0930) / atrMain;
               double zBench = (b1 - m_us500Open0930) / atrBench;
               double rsDiff = zMain - zBench;
               if(MathAbs(rsDiff) < 0.25 || (zMain * rsDiff) <= 0.0)
               {
                  ExpireOppIfActive(4, nowUtc, m_feeds[SYM_US100].last_ask, "SETUP_INVALID");
                  m_tradedDay[4] = nyDay; // Signal evaluated & declined for today
               }
               else
               {
                  bool isBuy = (rsDiff > 0.0);
                  double px = isBuy ? m_feeds[SYM_US100].last_ask : m_feeds[SYM_US100].last_bid;
                  double sl = isBuy ? (px - 0.75 * atrMain) : (px + 0.75 * atrMain);
                  string oppId = ""; int oppEval = 0; bool oppNew = false;
                  UpdateSetupOppOnObservedTick(4, "E5", "E5_US100_RS1130", 20261126, m_feeds[SYM_US100].symbol, nyDay, nowUtc, isBuy ? 1 : -1, px, oppId, oppEval, oppNew);
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E5", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E5_US100_RS1130"; it.magic = 20261126;
                  it.symbol = m_feeds[SYM_US100].symbol; it.is_buy = isBuy; it.signal_price = px; it.sl_price = sl;
                  it.base_risk_pct = m_baseRisk[4]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = nyDay; it.tag = isBuy ? "Naqex_M_E5_BUY" : "Naqex_M_E5_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
      }
      else if(isUsHalf || nyMins < 11 * 60 + 30 || nyMins >= 11 * 60 + 40 || IsEngineTraded(4, nyDay))
      {
         ExpireOppIfActive(4, nowUtc, m_feeds[SYM_US100].last_ask, IsEngineTraded(4, nyDay) ? "TRADED_FILLED" : "SESSION_ENDED");
      }

      // --- E7: USDJPY_NY_RISK_FLOW_10ET (USDJPY) ---
      if(!isUsHalf && m_nyAnchorReady && !IsEngineTraded(6, nyDay) &&
         nyMins >= 10 * 60 && nyMins < 10 * 60 + 10 && m_feeds[SYM_USDJPY].has_fresh_tick)
      {
         double atrEq = 0.0, atrJpy = 0.0;
         if(ReadPriorD1Atr(SYM_US100, atrEq) && ReadPriorD1Atr(SYM_USDJPY, atrJpy))
         {
            double eq1 = iClose(m_feeds[SYM_US100].symbol, PERIOD_M1, 1);
            int lbMins = MathMax(60, (utc.hour - 7) * 60 + utc.min);
            int bskIdx[5]   = {SYM_USDJPY, SYM_USDCAD, SYM_EURUSD, SYM_GBPUSD, SYM_AUDUSD};
            int bskSigns[5] = {1, 1, -1, -1, -1};
            double usdSum = 0.0;
            bool okBsk = (eq1 > 0.0);
            for(int k = 0; k < 5 && okBsk; k++)
            {
               double ab = 0.0;
               if(!ReadPriorD1Atr(bskIdx[k], ab)) { okBsk = false; break; }
               double p1 = iClose(m_feeds[bskIdx[k]].symbol, PERIOD_M1, 1);
               double p0 = iClose(m_feeds[bskIdx[k]].symbol, PERIOD_M1, 1 + lbMins);
               if(p1 <= 0.0 || p0 <= 0.0) { okBsk = false; break; }
               usdSum += bskSigns[k] * ((p1 - p0) / ab);
            }
            if(okBsk)
            {
               double zEq = (eq1 - m_us100Open0930) / atrEq;
               double usdFac = usdSum / 5.0;
               if(MathAbs(zEq) < 0.25 || MathAbs(usdFac) < 0.25 || (zEq * usdFac) <= 0.0)
               {
                  ExpireOppIfActive(6, nowUtc, m_feeds[SYM_USDJPY].last_ask, "SETUP_INVALID");
                  m_tradedDay[6] = nyDay;
               }
               else
               {
                  bool isBuy = (usdFac > 0.0);
                  double px = isBuy ? m_feeds[SYM_USDJPY].last_ask : m_feeds[SYM_USDJPY].last_bid;
                  double sl = isBuy ? (px - 0.75 * atrJpy) : (px + 0.75 * atrJpy);
                  string oppId = ""; int oppEval = 0; bool oppNew = false;
                  UpdateSetupOppOnObservedTick(6, "E7", "E7_USDJPY_NY10ET", 20261129, m_feeds[SYM_USDJPY].symbol, nyDay, nowUtc, isBuy ? 1 : -1, px, oppId, oppEval, oppNew);
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E7", nowUtc); it.opportunity_id = oppId; it.opp_eval_count = oppEval; it.opp_is_new = oppNew;
                  it.engine_id = "E7_USDJPY_NY10ET"; it.magic = 20261129;
                  it.symbol = m_feeds[SYM_USDJPY].symbol; it.is_buy = isBuy; it.signal_price = px; it.sl_price = sl;
                  it.base_risk_pct = m_baseRisk[6]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = nyDay; it.tag = isBuy ? "Naqex_M_E7_BUY" : "Naqex_M_E7_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
      }
      else if(isUsHalf || nyMins < 10 * 60 || nyMins >= 10 * 60 + 10 || IsEngineTraded(6, nyDay))
      {
         ExpireOppIfActive(6, nowUtc, m_feeds[SYM_USDJPY].last_ask, IsEngineTraded(6, nyDay) ? "TRADED_FILLED" : "SESSION_ENDED");
      }

      // --- S6 (SHADOW COMPARE ONLY by Round-3 decision): FX_USD_BASKET_12U_Z35 ---
      if(m_enableS6Shadow && !IsEngineTraded(7, utcDay) && utc.hour == 12 && utc.min < 10)
      {
         int bskIdx[5]   = {SYM_USDJPY, SYM_USDCAD, SYM_EURUSD, SYM_GBPUSD, SYM_AUDUSD};
         int bskSigns[5] = {1, 1, -1, -1, -1};
         double zVals[5], aVals[5];
         double usdSum = 0.0;
         bool okS6 = true;
         for(int k = 0; k < 5; k++)
         {
            if(!ReadPriorD1Atr(bskIdx[k], aVals[k])) { okS6 = false; break; }
            double p1 = iClose(m_feeds[bskIdx[k]].symbol, PERIOD_M1, 1);
            double p0 = iClose(m_feeds[bskIdx[k]].symbol, PERIOD_M1, 1 + 300);
            if(p1 <= 0.0 || p0 <= 0.0) { okS6 = false; break; }
            zVals[k] = (p1 - p0) / aVals[k];
            usdSum += bskSigns[k] * zVals[k];
         }
         if(okS6)
         {
            double usdFactor = usdSum / 5.0;
            if(MathAbs(usdFactor) >= 0.35)
            {
               int usdDir = (usdFactor > 0.0) ? 1 : -1;
               int poolBskMap[4]  = {3, 2, 4, 1}; // GBPUSD, EURUSD, AUDUSD, USDCAD
               int poolUsdBase[4] = {-1, -1, -1, 1};
               int bestP = -1; double bestScore = -1e9; int bestSide = 0;
               for(int p = 0; p < 4; p++)
               {
                  int sd = usdDir * poolUsdBase[p];
                  double sc = sd * zVals[poolBskMap[p]];
                  if(sc > bestScore) { bestScore = sc; bestP = p; bestSide = sd; }
               }
               if(bestP >= 0 && bestScore > 0.0)
               {
                  int sIdx = bskIdx[poolBskMap[bestP]];
                  bool isBuy = (bestSide == 1);
                  double px = isBuy ? m_feeds[sIdx].last_ask : m_feeds[sIdx].last_bid;
                  double sl = isBuy ? (px - 0.75 * aVals[poolBskMap[bestP]]) : (px + 0.75 * aVals[poolBskMap[bestP]]);
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("S6", nowUtc); it.opportunity_id = ""; it.opp_eval_count = 0; it.opp_is_new = false;
                  it.engine_id = "S6_FX_USD_BSK"; it.magic = 20261127;
                  it.symbol = m_feeds[sIdx].symbol; it.is_buy = isBuy; it.signal_price = px; it.sl_price = sl;
                  it.base_risk_pct = m_baseRisk[7]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[sIdx].last_lag_ms;
                  it.shadow_only = true; it.session_day_key = utcDay; it.tag = isBuy ? "Naqex_M_S6_SHADOW_BUY" : "Naqex_M_S6_SHADOW_SELL";
                  PushIntent(outIntents, count, it);
                  m_tradedDay[7] = utcDay;
               }
            }
         }
      }

      return count;
   }
};

#endif // NAQEX_SIGNALS_7E_MQH
