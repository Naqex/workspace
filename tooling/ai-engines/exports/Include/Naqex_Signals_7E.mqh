//+------------------------------------------------------------------+
//| Naqex_Signals_7E.mqh (v1.00 — Pure Signal Modules, 0 OrderSend)  |
//| Round-3 Approved Architecture: 7 Fixed Core Engines (E1..E7)     |
//| + Optional S6 Shadow-Only Compare Module.                        |
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

   // Reconstruct [startUtc, endUtc) M1 high/low/open/close from broker history (restart resilience!)
   bool ReconstructM1Window(const string sym, const datetime nowUtc, const datetime startUtc, const datetime endUtc,
                            double &outOpen, double &outHigh, double &outLow, double &outClose) const
   {
      long srvMinusUtc = (long)TimeCurrent() - (long)nowUtc;
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
      m_intentSeq        = 0;
      m_maxBreakoutLagMs = 5000;
      m_enableS6Shadow   = true;
      m_atrPeriod        = 14;
      m_e1BoxDay         = 0; m_e1BoxReady = false; m_e1BoxTop = 0.0; m_e1BoxBot = 0.0;
      m_e4SessDay        = 0; m_e4MornInit = false; m_e4MornFrozen = false;
      m_e4MornOpen       = 0.0; m_e4MornHigh = 0.0; m_e4MornLow = 0.0; m_e4MornClose = 0.0; m_e4MornDir = 0;
      m_nyAnchorDay      = 0; m_nyAnchorReady = false; m_nyAnchorLastTry = 0; m_us100Open0930 = 0.0; m_us500Open0930 = 0.0;
      m_e6CompCacheDay   = 0; m_e6CompCacheOk = false; m_e1ReconstLastTry = 0;
      for(int s = 0; s < NAQEX_SYM_COUNT; s++) { m_d1AtrCacheDay[s] = 0; m_d1AtrCacheVal[s] = 0.0; }
      for(int i = 0; i < 8; i++) m_tradedDay[i] = 0;
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
             const int maxBreakoutLagMs = 5000, const bool enableS6Shadow = true)
   {
      m_maxBreakoutLagMs = maxBreakoutLagMs;
      m_enableS6Shadow   = enableS6Shadow;
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
         m_tradedDay[idx] = dayKey;
   }

   bool IsEngineTraded(const int idx, const datetime dayKey) const
   {
      return (idx >= 0 && idx < 8 && m_tradedDay[idx] == dayKey);
   }

   // Poll all 8 symbols via CopyTicksRange cursor (handles duplicate ms & records decision tick lag)
   long PollSymbolTicks()
   {
      long maxLagMs = 0;
      long srvNowMsc = (long)TimeCurrent() * 1000;
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

   // Check whether a given engine magic should hard-flatten by clock / holiday half-day
   bool ShouldClockFlattenMagic(const long magic, const datetime nowUtc, string &outReason) const
   {
      outReason = "";
      MqlDateTime utc; TimeToStruct(nowUtc, utc);
      if(utc.day_of_week == 0 || utc.day_of_week == 6) return false;
      if(magic == 20261122) // E1 Helsinki 18:00
      {
         int flatH = 18 - HelsinkiUtcOffsetHours(utc);
         if(utc.hour >= flatH) { outReason = "HARD_FLAT_18H_HELSINKI_SWAP0"; return true; }
         return false;
      }
      if(magic == 20261124 || magic == 20261126) // E4, E5 US100 15:55 ET + US half-day
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
      if(utc.day_of_week == 0 || utc.day_of_week == 6) return 0;

      datetime utcDay = nowUtc - (nowUtc % 86400);
      datetime nowNy  = nowUtc + (datetime)(NewYorkUtcOffsetHours(utc) * 3600);
      MqlDateTime ny; TimeToStruct(nowNy, ny);
      datetime nyDay  = nowNy - (nowNy % 86400);
      int nyMins      = ny.hour * 60 + ny.min;
      bool isUsHalf   = CNaqexPropGuard::IsUsEquityHalfDayNY(ny);

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
            if(!m_e1BoxReady) { m_e1BoxTop = mid; m_e1BoxBot = mid; m_e1BoxReady = true; }
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
         if(m_e1BoxReady && m_e1BoxTop > m_e1BoxBot && !IsEngineTraded(0, utcDay) &&
            utc.hour >= 3 && utc.hour < 10 && utc.hour < flatH && m_feeds[SYM_USDJPY].has_fresh_tick)
         {
            if(ask >= m_e1BoxTop)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E1", nowUtc); it.engine_id = "E1_USDJPY_TOKYO"; it.magic = 20261122;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = m_e1BoxBot;
               it.base_risk_pct = m_baseRisk[0]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = utcDay; it.tag = "Naqex_M_E1_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(bid <= m_e1BoxBot)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E1", nowUtc); it.engine_id = "E1_USDJPY_TOKYO"; it.magic = 20261122;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = m_e1BoxTop;
               it.base_risk_pct = m_baseRisk[0]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = utcDay; it.tag = "Naqex_M_E1_SELL";
               PushIntent(outIntents, count, it);
            }
         }
      }

      // --- E2: EXP_DAILY_OPEN_080 (USDJPY) ---
      if(utc.hour >= 7 && utc.hour < 17 && m_feeds[SYM_USDJPY].has_fresh_tick)
      {
         string sym = m_feeds[SYM_USDJPY].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         if(!IsEngineTraded(1, d1Start) && ReadPriorD1Atr(SYM_USDJPY, atrD1) && dayOpen > 0.0)
         {
            double ask = m_feeds[SYM_USDJPY].last_ask, bid = m_feeds[SYM_USDJPY].last_bid;
            if(ask >= dayOpen + 0.80 * atrD1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E2", nowUtc); it.engine_id = "E2_USDJPY_EXP80"; it.magic = 20261123;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
               it.base_risk_pct = m_baseRisk[1]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E2_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(bid <= dayOpen - 0.80 * atrD1)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E2", nowUtc); it.engine_id = "E2_USDJPY_EXP80"; it.magic = 20261123;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.75 * atrD1;
               it.base_risk_pct = m_baseRisk[1]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
               it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E2_SELL";
               PushIntent(outIntents, count, it);
            }
         }
      }

      // --- E3: WB_EXP_80_VOL_HIGH (GBPUSD) ---
      if(utc.hour >= 7 && utc.hour < 17 && m_feeds[SYM_GBPUSD].has_fresh_tick)
      {
         string sym = m_feeds[SYM_GBPUSD].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         if(!IsEngineTraded(2, d1Start) && ReadPriorD1Atr(SYM_GBPUSD, atrD1) && dayOpen > 0.0)
         {
            double prevRng = iHigh(sym, PERIOD_D1, 1) - iLow(sym, PERIOD_D1, 1);
            if(prevRng >= 1.10 * atrD1)
            {
               double ask = m_feeds[SYM_GBPUSD].last_ask, bid = m_feeds[SYM_GBPUSD].last_bid;
               if(ask >= dayOpen + 0.80 * atrD1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E3", nowUtc); it.engine_id = "E3_GBPUSD_VH"; it.magic = 20261125;
                  it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[2]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_GBPUSD].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E3_BUY";
                  PushIntent(outIntents, count, it);
               }
               else if(bid <= dayOpen - 0.80 * atrD1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E3", nowUtc); it.engine_id = "E3_GBPUSD_VH"; it.magic = 20261125;
                  it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[2]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_GBPUSD].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E3_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
      }

      // --- E6: EURJPY_VOLCOMP_EXP75 (EURJPY) ---
      if(utc.hour >= 7 && utc.hour < 17 && m_feeds[SYM_EURJPY].has_fresh_tick)
      {
         string sym = m_feeds[SYM_EURJPY].symbol;
         datetime d1Start = iTime(sym, PERIOD_D1, 0);
         double atrD1 = 0.0, dayOpen = iOpen(sym, PERIOD_D1, 0);
         if(!IsEngineTraded(5, d1Start) && ReadPriorD1Atr(SYM_EURJPY, atrD1) && dayOpen > 0.0)
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
            if(m_e6CompCacheOk)
            {
               double ask = m_feeds[SYM_EURJPY].last_ask, bid = m_feeds[SYM_EURJPY].last_bid;
               if(ask >= dayOpen + 0.75 * atrD1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E6", nowUtc); it.engine_id = "E6_EURJPY_VOLCOMP"; it.magic = 20261128;
                  it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.75 * atrD1;
                  it.base_risk_pct = m_baseRisk[5]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_EURJPY].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = d1Start; it.tag = "Naqex_M_E6_BUY";
                  PushIntent(outIntents, count, it);
               }
               else if(bid <= dayOpen - 0.75 * atrD1)
               {
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E6", nowUtc); it.engine_id = "E6_EURJPY_VOLCOMP"; it.magic = 20261128;
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
            if(!m_e4MornInit) { m_e4MornOpen = bid; m_e4MornHigh = bid; m_e4MornLow = bid; m_e4MornClose = bid; m_e4MornInit = true; }
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
         if(m_e4MornFrozen && m_e4MornDir != 0 && !IsEngineTraded(3, nyDay) &&
            m_feeds[SYM_US100].has_fresh_tick && ReadPriorD1Atr(SYM_US100, atrUs100))
         {
            if(m_e4MornDir == 1 && ask >= m_e4MornHigh)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E4", nowUtc); it.engine_id = "E4_US100_SESS40"; it.magic = 20261124;
               it.symbol = sym; it.is_buy = true; it.signal_price = ask; it.sl_price = ask - 0.65 * atrUs100;
               it.base_risk_pct = m_baseRisk[3]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
               it.shadow_only = false; it.session_day_key = nyDay; it.tag = "Naqex_M_E4_BUY";
               PushIntent(outIntents, count, it);
            }
            else if(m_e4MornDir == -1 && bid <= m_e4MornLow)
            {
               NaqexSignalIntent it;
               it.intent_id = NextIntentId("E4", nowUtc); it.engine_id = "E4_US100_SESS40"; it.magic = 20261124;
               it.symbol = sym; it.is_buy = false; it.signal_price = bid; it.sl_price = bid + 0.65 * atrUs100;
               it.base_risk_pct = m_baseRisk[3]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
               it.shadow_only = false; it.session_day_key = nyDay; it.tag = "Naqex_M_E4_SELL";
               PushIntent(outIntents, count, it);
            }
         }
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
                  m_tradedDay[4] = nyDay; // Signal evaluated & declined for today
               }
               else
               {
                  bool isBuy = (rsDiff > 0.0);
                  double px = isBuy ? m_feeds[SYM_US100].last_ask : m_feeds[SYM_US100].last_bid;
                  double sl = isBuy ? (px - 0.75 * atrMain) : (px + 0.75 * atrMain);
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E5", nowUtc); it.engine_id = "E5_US100_RS1130"; it.magic = 20261126;
                  it.symbol = m_feeds[SYM_US100].symbol; it.is_buy = isBuy; it.signal_price = px; it.sl_price = sl;
                  it.base_risk_pct = m_baseRisk[4]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_US100].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = nyDay; it.tag = isBuy ? "Naqex_M_E5_BUY" : "Naqex_M_E5_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
      }

      // --- E7: USDJPY_NY_RISK_FLOW_10ET (USDJPY) ---
      if(m_nyAnchorReady && !IsEngineTraded(6, nyDay) &&
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
                  m_tradedDay[6] = nyDay;
               }
               else
               {
                  bool isBuy = (usdFac > 0.0);
                  double px = isBuy ? m_feeds[SYM_USDJPY].last_ask : m_feeds[SYM_USDJPY].last_bid;
                  double sl = isBuy ? (px - 0.75 * atrJpy) : (px + 0.75 * atrJpy);
                  NaqexSignalIntent it;
                  it.intent_id = NextIntentId("E7", nowUtc); it.engine_id = "E7_USDJPY_NY10ET"; it.magic = 20261129;
                  it.symbol = m_feeds[SYM_USDJPY].symbol; it.is_buy = isBuy; it.signal_price = px; it.sl_price = sl;
                  it.base_risk_pct = m_baseRisk[6]; it.signal_utc = nowUtc; it.tick_lag_ms = m_feeds[SYM_USDJPY].last_lag_ms;
                  it.shadow_only = false; it.session_day_key = nyDay; it.tag = isBuy ? "Naqex_M_E7_BUY" : "Naqex_M_E7_SELL";
                  PushIntent(outIntents, count, it);
               }
            }
         }
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
                  it.intent_id = NextIntentId("S6", nowUtc); it.engine_id = "S6_FX_USD_BSK"; it.magic = 20261127;
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
