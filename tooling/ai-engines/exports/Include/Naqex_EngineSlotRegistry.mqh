//+------------------------------------------------------------------+
//| Naqex_EngineSlotRegistry.mqh (Wave 5 W5-G15 Modular Registry)    |
//| 16-Slot Plug-and-Play Engine Registry + Shield A & P2-3 Guards   |
//|                                                                  |
//| Architecture:                                                    |
//|   - Slots 0..6 wrap the 7 core PORT_7E engines via adapter       |
//|     without modifying NAQEX_SYM_COUNT=8 in immutable             |
//|     Naqex_Signals_7E.mqh.                                        |
//|   - Slots 7..15 independently managed for Wave 5 new engines     |
//|     or SHADOW_ONLY incubation.                                   |
//|   - Unified Shield A total open risk cap enforcement             |
//|     (EffectiveTotalOpenRiskCapPct <= 3.00%, fail-closed).        |
//|   - Extended directional cluster exposure counters for           |
//|     EUR, GBP, and AUD (P2-3 guardrail complementing immutable    |
//|     Naqex_PropGuard.mqh USD/JPY/US100 caps).                     |
//|                                                                  |
//| PURE SIGNAL & REGISTRY MODULE: ZERO trade execution API calls.   |
//+------------------------------------------------------------------+
#ifndef NAQEX_ENGINE_SLOT_REGISTRY_MQH
#define NAQEX_ENGINE_SLOT_REGISTRY_MQH

#define NAQEX_SLOT_COUNT                16
#define NAQEX_CORE_7E_SLOT_COUNT        7
#define NAQEX_SHIELD_A_HARD_CEILING_PCT 3.00

enum ENUM_NAQEX_SLOT_STATUS
{
   NAQEX_SLOT_ACTIVE  = 0,
   NAQEX_SLOT_SHADOW  = 1,
   NAQEX_SLOT_HALVED  = 2,
   NAQEX_SLOT_RETIRED = 3
};

struct NaqexEngineSlot
{
   int                    slot_id;
   string                 engine_id;
   long                   magic;
   string                 symbol;
   bool                   enabled;
   double                 weight_mult;            // 1.0 / 0.5 / 0.0
   ENUM_NAQEX_SLOT_STATUS status;                 // ACTIVE | SHADOW | HALVED | RETIRED
   bool                   mt5_hcc_ready;          // MT5 symbol history / bar readiness
   bool                   red_news_6ccy_warning;  // true if symbol has CCY outside 6-CCY news CSV
};

class CNaqexEngineSlotRegistry
{
private:
   NaqexEngineSlot m_slots[NAQEX_SLOT_COUNT];
   bool            m_initialized;

   static bool IsCovered6CcyToken(const string ccy)
   {
      return (ccy == "USD" || ccy == "EUR" || ccy == "GBP" ||
              ccy == "JPY" || ccy == "AUD" || ccy == "CAD");
   }

   static bool IsKnownCoveredIndexOrUsdProxy(const string uSym)
   {
      return (StringFind(uSym, "US100")  >= 0 || StringFind(uSym, "NAS100") >= 0 ||
              StringFind(uSym, "NDX")    >= 0 || StringFind(uSym, "USTEC")  >= 0 ||
              StringFind(uSym, "US500")  >= 0 || StringFind(uSym, "SPX")    >= 0 ||
              StringFind(uSym, "US30")   >= 0 || StringFind(uSym, "GER40")  >= 0 ||
              StringFind(uSym, "DE40")   >= 0 || StringFind(uSym, "DAX")    >= 0 ||
              StringFind(uSym, "UK100")  >= 0 || StringFind(uSym, "FTSE")   >= 0);
   }

public:
   CNaqexEngineSlotRegistry()
   {
      m_initialized = false;
      ResetAllSlots();
   }

   static string StatusToString(const ENUM_NAQEX_SLOT_STATUS st)
   {
      if(st == NAQEX_SLOT_ACTIVE)  return "ACTIVE";
      if(st == NAQEX_SLOT_SHADOW)  return "SHADOW";
      if(st == NAQEX_SLOT_HALVED)  return "HALVED";
      return "RETIRED";
   }

   static double NormalizeSlotWeight(const double rawWeight, const ENUM_NAQEX_SLOT_STATUS st)
   {
      if(!MathIsValidNumber(rawWeight) || rawWeight <= 0.0)
         return 0.0;
      if(st == NAQEX_SLOT_RETIRED || st == NAQEX_SLOT_SHADOW)
         return 0.0;
      if(st == NAQEX_SLOT_HALVED)
         return 0.5;
      if(rawWeight <= 0.25)
         return 0.0;
      if(rawWeight < 0.75)
         return 0.5;
      return 1.0;
   }

   //--- Unified Shield A absolute cap enforcement (fail-closed <= 3.00%)
   static double EnforceShieldACapPct(const double requestedCapPct, const double hardCeilingPct = NAQEX_SHIELD_A_HARD_CEILING_PCT)
   {
      double ceilPct = NAQEX_SHIELD_A_HARD_CEILING_PCT;
      if(MathIsValidNumber(hardCeilingPct) && hardCeilingPct > 0.0)
         ceilPct = MathMin(hardCeilingPct, NAQEX_SHIELD_A_HARD_CEILING_PCT);
      if(!MathIsValidNumber(requestedCapPct) || requestedCapPct <= 0.0)
         return ceilPct;
      return MathMin(requestedCapPct, ceilPct);
   }

   //--- Detect whether symbol touches currencies outside 6-CCY red-news CSV (USD/EUR/GBP/JPY/AUD/CAD)
   static bool ComputeRedNews6CcyWarning(const string sym)
   {
      if(sym == "")
         return true;
      string u = sym;
      StringToUpper(u);
      if(IsKnownCoveredIndexOrUsdProxy(u))
         return false;
      // Non-6CCY tokens (CHF, NZD, XAU, XAG, OIL, WTI, BRENT, JP225, AUS200, BTC, ETH, SOL)
      if(StringFind(u, "CHF") >= 0 || StringFind(u, "NZD") >= 0 ||
         StringFind(u, "XAU") >= 0 || StringFind(u, "XAG") >= 0 ||
         StringFind(u, "OIL") >= 0 || StringFind(u, "WTI") >= 0 ||
         StringFind(u, "BRENT") >= 0 || StringFind(u, "JP225") >= 0 ||
         StringFind(u, "AUS200") >= 0 || StringFind(u, "BTC") >= 0 ||
         StringFind(u, "ETH") >= 0 || StringFind(u, "SOL") >= 0)
         return true;
      if(StringLen(u) >= 6)
      {
         string baseCcy  = StringSubstr(u, 0, 3);
         string quoteCcy = StringSubstr(u, 3, 3);
         if(IsCovered6CcyToken(baseCcy) && IsCovered6CcyToken(quoteCcy))
            return false;
      }
      return true;
   }

   static bool CheckSymbolHccReady(const string sym)
   {
      if(sym == "")
         return false;
      if(!SymbolSelect(sym, true))
         return false;
      datetime d1Bar = iTime(sym, PERIOD_D1, 1);
      datetime m1Bar = iTime(sym, PERIOD_M1, 1);
      return (d1Bar > 0 && m1Bar > 0);
   }

   void ResetAllSlots()
   {
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
      {
         m_slots[i].slot_id               = i;
         m_slots[i].engine_id             = StringFormat("SLOT_%02d_UNASSIGNED", i);
         m_slots[i].magic                 = 20261130 + i;
         m_slots[i].symbol                = "";
         m_slots[i].enabled               = false;
         m_slots[i].weight_mult           = 0.0;
         m_slots[i].status                = NAQEX_SLOT_RETIRED;
         m_slots[i].mt5_hcc_ready         = false;
         m_slots[i].red_news_6ccy_warning = true;
      }
      m_initialized = false;
   }

   //--- Configure a single slot cleanly (slots 0..15)
   bool ConfigureSlot(const int slotId,
                      const string engineId,
                      const long magic,
                      const string symbol,
                      const bool enabled,
                      const double weightMult,
                      const ENUM_NAQEX_SLOT_STATUS status)
   {
      if(slotId < 0 || slotId >= NAQEX_SLOT_COUNT)
         return false;
      m_slots[slotId].slot_id               = slotId;
      m_slots[slotId].engine_id             = engineId;
      m_slots[slotId].magic                 = magic;
      m_slots[slotId].symbol                = symbol;
      m_slots[slotId].status                = status;
      m_slots[slotId].weight_mult           = NormalizeSlotWeight(weightMult, status);
      m_slots[slotId].enabled               = (enabled && status != NAQEX_SLOT_RETIRED &&
                                               (status == NAQEX_SLOT_SHADOW || m_slots[slotId].weight_mult > 0.0));
      m_slots[slotId].mt5_hcc_ready         = (symbol != "") ? CheckSymbolHccReady(symbol) : false;
      m_slots[slotId].red_news_6ccy_warning = ComputeRedNews6CcyWarning(symbol);
      return true;
   }

   //--- Initialize slots 0..6 via adapter over PORT_7E symbols + slots 7..15 for incubation/expansion
   bool InitCore7EAdapter(const string symUsdjpy,
                          const string symGbpusd,
                          const string symEurjpy,
                          const string symUs100,
                          const bool enableS6Shadow = false,
                          const double w0 = 1.0,
                          const double w1 = 1.0,
                          const double w2 = 1.0,
                          const double w3 = 1.0,
                          const double w4 = 1.0,
                          const double w5 = 1.0,
                          const double w6 = 1.0)
   {
      ResetAllSlots();

      double weights[NAQEX_CORE_7E_SLOT_COUNT];
      weights[0] = w0;
      weights[1] = w1;
      weights[2] = w2;
      weights[3] = w3;
      weights[4] = w4;
      weights[5] = w5;
      weights[6] = w6;

      string coreIds[NAQEX_CORE_7E_SLOT_COUNT] =
      {
         "E1_USDJPY_TOKYO",
         "E2_USDJPY_EXP80",
         "E3_GBPUSD_VH",
         "E4_US100_SESS40",
         "E5_US100_RS1130",
         "E6_EURJPY_VOLCOMP",
         "E7_USDJPY_NY10ET"
      };
      long coreMagics[NAQEX_CORE_7E_SLOT_COUNT] =
      {
         20261122, 20261123, 20261125, 20261124, 20261126, 20261128, 20261129
      };
      string coreSyms[NAQEX_CORE_7E_SLOT_COUNT];
      coreSyms[0] = symUsdjpy;
      coreSyms[1] = symUsdjpy;
      coreSyms[2] = symGbpusd;
      coreSyms[3] = symUs100;
      coreSyms[4] = symUs100;
      coreSyms[5] = symEurjpy;
      coreSyms[6] = symUsdjpy;

      for(int i = 0; i < NAQEX_CORE_7E_SLOT_COUNT; i++)
      {
         ENUM_NAQEX_SLOT_STATUS st = NAQEX_SLOT_ACTIVE;
         bool en = true;
         if(!MathIsValidNumber(weights[i]) || weights[i] <= 0.0)
         {
            st = NAQEX_SLOT_RETIRED;
            en = false;
         }
         else if(weights[i] < 0.75)
         {
            st = NAQEX_SLOT_HALVED;
         }
         ConfigureSlot(i, coreIds[i], coreMagics[i], coreSyms[i], en, weights[i], st);
      }

      // Slot 7: Optional S6 Shadow-Only Incubation
      ConfigureSlot(7, "S6_FX_USD_BSK", 20261127, symGbpusd, enableS6Shadow, 0.0,
                    enableS6Shadow ? NAQEX_SLOT_SHADOW : NAQEX_SLOT_RETIRED);

      // Slots 8..15: Independent Wave 5 expansion / shadow incubation slots (disabled by default)
      for(int s = 8; s < NAQEX_SLOT_COUNT; s++)
      {
         ConfigureSlot(s, StringFormat("W5_SLOT_%02d_INCUBATION", s),
                       20261130 + (s - 8), "", false, 0.0, NAQEX_SLOT_RETIRED);
      }

      m_initialized = true;
      return true;
   }

   void RefreshHccReadiness()
   {
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
      {
         if(m_slots[i].symbol != "")
            m_slots[i].mt5_hcc_ready = CheckSymbolHccReady(m_slots[i].symbol);
      }
   }

   int FindSlotByMagic(const long magic) const
   {
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
      {
         if(m_slots[i].magic == magic)
            return i;
      }
      return -1;
   }

   bool GetSlotCopy(const int slotId, NaqexEngineSlot &outSlot) const
   {
      if(slotId < 0 || slotId >= NAQEX_SLOT_COUNT)
         return false;
      outSlot = m_slots[slotId];
      return true;
   }

   bool IsMagicAllowedForLiveOrShadow(const long magic, double &outWeightMult, bool &outForceShadow) const
   {
      outWeightMult  = 0.0;
      outForceShadow = true;
      int idx = FindSlotByMagic(magic);
      if(idx < 0)
         return false;
      if(!m_slots[idx].enabled || m_slots[idx].status == NAQEX_SLOT_RETIRED)
         return false;
      if(m_slots[idx].status == NAQEX_SLOT_SHADOW)
      {
         outWeightMult  = 0.0;
         outForceShadow = true;
         return true;
      }
      if(m_slots[idx].weight_mult <= 0.0)
         return false;
      outWeightMult  = m_slots[idx].weight_mult;
      outForceShadow = false;
      return true;
   }

   int CountSlotsByStatus(const ENUM_NAQEX_SLOT_STATUS st) const
   {
      int cnt = 0;
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
         if(m_slots[i].status == st && (st == NAQEX_SLOT_RETIRED || m_slots[i].enabled))
            cnt++;
      return cnt;
   }

   int CountEnabledSlots() const
   {
      int cnt = 0;
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
         if(m_slots[i].enabled)
            cnt++;
      return cnt;
   }

   int CountRedNews6CcyWarningsOnEnabled() const
   {
      int cnt = 0;
      for(int i = 0; i < NAQEX_SLOT_COUNT; i++)
         if(m_slots[i].enabled && m_slots[i].red_news_6ccy_warning)
            cnt++;
      return cnt;
   }

   bool IsInitialized() const { return m_initialized; }

   //--- P2-3 Guardrail: Extended directional cluster exposure accounting for EUR, GBP, and AUD
   //    (Complements immutable Naqex_PropGuard.mqh USD / JPY / US100 cluster caps!)
   static void AccumulateExtendedDirectionalFactor(const string sym,
                                                   const bool isBuy,
                                                   const double riskPct,
                                                   double &eurLong, double &eurShort,
                                                   double &gbpLong, double &gbpShort,
                                                   double &audLong, double &audShort)
   {
      if(riskPct <= 0.0 || sym == "")
         return;
      string u = sym;
      StringToUpper(u);
      int dir = isBuy ? 1 : -1;

      // Regional equity indices linked to EUR / GBP / AUD factors
      if(StringFind(u, "GER40") >= 0 || StringFind(u, "DE40") >= 0 || StringFind(u, "DAX") >= 0)
      {
         if(dir > 0) eurLong += riskPct; else eurShort += riskPct;
         return;
      }
      if(StringFind(u, "UK100") >= 0 || StringFind(u, "FTSE") >= 0)
      {
         if(dir > 0) gbpLong += riskPct; else gbpShort += riskPct;
         return;
      }
      if(StringFind(u, "AUS200") >= 0 || StringFind(u, "ASX") >= 0)
      {
         if(dir > 0) audLong += riskPct; else audShort += riskPct;
         return;
      }

      int posEur = StringFind(u, "EUR");
      if(posEur == 0)
      {
         if(dir > 0) eurLong += riskPct; else eurShort += riskPct;
      }
      else if(posEur >= 3)
      {
         if(dir > 0) eurShort += riskPct; else eurLong += riskPct;
      }

      int posGbp = StringFind(u, "GBP");
      if(posGbp == 0)
      {
         if(dir > 0) gbpLong += riskPct; else gbpShort += riskPct;
      }
      else if(posGbp >= 3)
      {
         if(dir > 0) gbpShort += riskPct; else gbpLong += riskPct;
      }

      int posAud = StringFind(u, "AUD");
      if(posAud == 0)
      {
         if(dir > 0) audLong += riskPct; else audShort += riskPct;
      }
      else if(posAud >= 3)
      {
         if(dir > 0) audShort += riskPct; else audLong += riskPct;
      }
   }

   //--- Scan open account positions for EUR / GBP / AUD directional SL risk % (fail-closed 999.0 on orphan SL)
   static double ComputeAccountExtendedClusterRisk(double &eurLong, double &eurShort,
                                                   double &gbpLong, double &gbpShort,
                                                   double &audLong, double &audShort)
   {
      eurLong = 0.0; eurShort = 0.0;
      gbpLong = 0.0; gbpShort = 0.0;
      audLong = 0.0; audShort = 0.0;
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal <= 0.0)
         return 999.0;
      double totalPct = 0.0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong tk = PositionGetTicket(i);
         if(tk == 0)
            continue;
         string psym   = PositionGetString(POSITION_SYMBOL);
         double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
         double slPx   = PositionGetDouble(POSITION_SL);
         double vol    = PositionGetDouble(POSITION_VOLUME);
         if(vol <= 0.0)
            continue;
         if(slPx <= 0.0)
            return 999.0; // FAIL-CLOSED on orphan no-SL position
         double tSize = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_SIZE);
         double tVal  = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE_LOSS);
         if(tVal <= 0.0)
            tVal = SymbolInfoDouble(psym, SYMBOL_TRADE_TICK_VALUE);
         if(tSize <= 0.0 || tVal <= 0.0)
            return 999.0;
         double rPct = (((MathAbs(openPx - slPx) / tSize) * tVal * vol) / bal) * 100.0;
         totalPct += rPct;
         bool pBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         AccumulateExtendedDirectionalFactor(psym, pBuy, rPct, eurLong, eurShort, gbpLong, gbpShort, audLong, audShort);
      }
      return totalPct;
   }

   //--- Compute remaining directional headroom for EUR / GBP / AUD clusters + Shield A total cap
   static double ComputeExtendedClusterHeadroomPct(const string sym,
                                                   const bool isBuy,
                                                   const double maxEurClusterPct,
                                                   const double maxGbpClusterPct,
                                                   const double maxAudClusterPct,
                                                   const double maxTotalOpenPct,
                                                   const double extraEurLong = 0.0, const double extraEurShort = 0.0,
                                                   const double extraGbpLong = 0.0, const double extraGbpShort = 0.0,
                                                   const double extraAudLong = 0.0, const double extraAudShort = 0.0,
                                                   const double extraTotal = 0.0)
   {
      double eL, eS, gL, gS, aL, aS;
      double tot = ComputeAccountExtendedClusterRisk(eL, eS, gL, gS, aL, aS);
      if(tot >= 900.0)
         return 0.0;
      eL += extraEurLong; eS += extraEurShort;
      gL += extraGbpLong; gS += extraGbpShort;
      aL += extraAudLong; aS += extraAudShort;
      tot += extraTotal;

      double effCap = EnforceShieldACapPct(maxTotalOpenPct, NAQEX_SHIELD_A_HARD_CEILING_PCT);
      double headroom = MathMax(0.0, effCap - tot);

      double dEL = 0.0, dES = 0.0, dGL = 0.0, dGS = 0.0, dAL = 0.0, dAS = 0.0;
      AccumulateExtendedDirectionalFactor(sym, isBuy, 1.0, dEL, dES, dGL, dGS, dAL, dAS);

      if(maxEurClusterPct > 0.0)
      {
         if(dEL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxEurClusterPct - eL));
         if(dES > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxEurClusterPct - eS));
      }
      if(maxGbpClusterPct > 0.0)
      {
         if(dGL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxGbpClusterPct - gL));
         if(dGS > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxGbpClusterPct - gS));
      }
      if(maxAudClusterPct > 0.0)
      {
         if(dAL > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxAudClusterPct - aL));
         if(dAS > 0.0) headroom = MathMin(headroom, MathMax(0.0, maxAudClusterPct - aS));
      }
      return MathMax(0.0, headroom);
   }
};

#endif // NAQEX_ENGINE_SLOT_REGISTRY_MQH
