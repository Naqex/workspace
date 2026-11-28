//+------------------------------------------------------------------+
//| Naqex_ML_Parity500_Probe_v105.mq5 (Wave 5 W5-G12 Parity Probe)   |
//| Lightweight, ZERO-trade-execution MT5 Strategy Tester probe that |
//| loads naqex_v105_lgbm.onnx + wave5_ml_parity_500.csv via         |
//| #property tester_file, evaluates BOTH OnnxRun() AND Pure-MQL5    |
//| tree evaluator across all 500 Fold-4 OOS golden vectors,         |
//| verifies fail-closed NaN / +Inf / -Inf rejection, writes all     |
//| 500 predicted probabilities to CSV, and logs machine-parseable   |
//| parity metrics.                                                  |
//+------------------------------------------------------------------+
#property strict
#property version     "1.05"
#property tester_file "naqex_v105_lgbm.onnx"
#property tester_file "wave5_ml_parity_500.csv"

#include "Include/Naqex_ML_Filter_v105.mqh"

input string InpModelOnnxFile    = NAQEX_V105_ML_ONNX_FILE_DEFAULT;
input string InpParityInputCsv   = "wave5_ml_parity_500.csv";
input string InpParityOutputCsv  = "wave5_ml_mt5_parity500_out.csv";
input double InpMLThreshold      = NAQEX_V105_ML_DEFAULT_THRESHOLD;
input double InpParityMaxTol     = 1e-5;
input bool   InpRunPoisonedCheck = true;

CNaqexMLFilterV105 g_probeFilter;
bool               g_probeDone = false;

bool RunParity500ProbeV105Once()
{
   if(g_probeDone)
      return true;
   g_probeDone = true;

   bool initOk = g_probeFilter.InitFromFile(InpModelOnnxFile, V105_ONNX_OR_PURE_MQL5_FALLBACK, InpMLThreshold);
   bool onnxReady = g_probeFilter.IsOnnxReady();
   PrintFormat("[ML-PARITY500-V105-INIT] init_ok=%s onnx_ready=%s backend=%s last_err=%d model=%s thr=%.6f",
               initOk ? "true" : "false",
               onnxReady ? "true" : "false",
               g_probeFilter.LastBackend(),
               g_probeFilter.LastOnnxError(),
               InpModelOnnxFile,
               InpMLThreshold);

   // 1. Fail-closed NaN, +Inf & -Inf poisoned feature rejection drill (zero compiler warnings!)
   bool nanBlocked = true;
   bool infBlocked = true;
   if(InpRunPoisonedCheck)
   {
      double negOne    = -1.0;
      double nanVal    = MathSqrt(negOne);
      double posInfVal = MathExp(1000.0);
      double negInfVal = -MathExp(1000.0);
      double badNan[NAQEX_V105_ML_N_FEATURES];
      double badPosInf[NAQEX_V105_ML_N_FEATURES];
      double badNegInf[NAQEX_V105_ML_N_FEATURES];
      for(int j = 0; j < NAQEX_V105_ML_N_FEATURES; j++)
      {
         badNan[j]    = 0.5;
         badPosInf[j] = 0.5;
         badNegInf[j] = 0.5;
      }
      badNan[0]    = nanVal;
      badPosInf[1] = posInfVal;
      badNegInf[2] = negInfVal;

      double pTmp  = 0.0;
      string beTmp = "";
      bool okNanPure  = CNaqexMLFilterV105::PredictPureMql5(badNan, pTmp);
      bool okNanOnnx  = g_probeFilter.PredictOnnx(badNan, pTmp);
      bool okNanAllow = g_probeFilter.ShouldAllowTrade(badNan, pTmp, beTmp);
      nanBlocked = (!okNanPure && !okNanOnnx && !okNanAllow);

      bool okPosInfPure  = CNaqexMLFilterV105::PredictPureMql5(badPosInf, pTmp);
      bool okPosInfOnnx  = g_probeFilter.PredictOnnx(badPosInf, pTmp);
      bool okPosInfAllow = g_probeFilter.ShouldAllowTrade(badPosInf, pTmp, beTmp);

      bool okNegInfPure  = CNaqexMLFilterV105::PredictPureMql5(badNegInf, pTmp);
      bool okNegInfOnnx  = g_probeFilter.PredictOnnx(badNegInf, pTmp);
      bool okNegInfAllow = g_probeFilter.ShouldAllowTrade(badNegInf, pTmp, beTmp);

      infBlocked = (!okPosInfPure && !okPosInfOnnx && !okPosInfAllow &&
                    !okNegInfPure && !okNegInfOnnx && !okNegInfAllow);
   }

   // 2. Read all 500 golden vectors from Strategy Tester sandbox MQL5/Files
   ResetLastError();
   int inFh = FileOpen(InpParityInputCsv, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(inFh == INVALID_HANDLE)
   {
      PrintFormat("[ML-PARITY500-V105-ERR] Failed to open input CSV '%s' err=%d", InpParityInputCsv, GetLastError());
      return false;
   }

   int outFh = FileOpen(InpParityOutputCsv, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(outFh == INVALID_HANDLE)
   {
      FileClose(inFh);
      PrintFormat("[ML-PARITY500-V105-ERR] Failed to open output CSV '%s' err=%d", InpParityOutputCsv, GetLastError());
      return false;
   }

   FileWriteString(outFh, "row_idx,ref_proba,onnx_proba,pure_mql5_proba,abs_err_onnx_ref,abs_err_pure_ref,abs_err_onnx_pure,ref_size,onnx_size,pure_size\n");

   int rows = 0;
   int onnxOkCnt = 0;
   int pureOkCnt = 0;
   int onnxSizeMatch = 0;
   int pureSizeMatch = 0;
   double maxErrOnnxRef  = 0.0;
   double maxErrPureRef  = 0.0;
   double maxErrOnnxPure = 0.0;
   double feat[NAQEX_V105_ML_N_FEATURES];

   bool firstLine = true;
   while(!FileIsEnding(inFh))
   {
      string line = FileReadString(inFh);
      StringTrimLeft(line);
      StringTrimRight(line);
      if(line == "")
         continue;
      if(firstLine)
      {
         firstLine = false;
         if(StringFind(line, "row_idx") == 0)
            continue;
      }

      string cols[];
      int nCols = StringSplit(line, ',', cols);
      if(nCols < 1 + NAQEX_V105_ML_N_FEATURES + 2)
         continue;

      int rowIdx = (int)StringToInteger(cols[0]);
      for(int j = 0; j < NAQEX_V105_ML_N_FEATURES; j++)
         feat[j] = StringToDouble(cols[1 + j]);
      double refProba = StringToDouble(cols[1 + NAQEX_V105_ML_N_FEATURES]);
      double refSize  = StringToDouble(cols[1 + NAQEX_V105_ML_N_FEATURES + 1]);

      double pOnnx = -1.0;
      double pPure = -1.0;
      bool okOnnx = onnxReady && g_probeFilter.PredictOnnx(feat, pOnnx);
      bool okPure = CNaqexMLFilterV105::PredictPureMql5(feat, pPure);

      double errOnnxRef  = okOnnx ? MathAbs(pOnnx - refProba) : 999.0;
      double errPureRef  = okPure ? MathAbs(pPure - refProba) : 999.0;
      double errOnnxPure = (okOnnx && okPure) ? MathAbs(pOnnx - pPure) : 999.0;

      if(okOnnx)
      {
         onnxOkCnt++;
         if(errOnnxRef > maxErrOnnxRef) maxErrOnnxRef = errOnnxRef;
      }
      if(okPure)
      {
         pureOkCnt++;
         if(errPureRef > maxErrPureRef) maxErrPureRef = errPureRef;
      }
      if(okOnnx && okPure && errOnnxPure > maxErrOnnxPure)
         maxErrOnnxPure = errOnnxPure;

      double onnxSize = (okOnnx && pOnnx >= InpMLThreshold) ? 1.0 : 0.0;
      double pureSize = (okPure && pPure >= InpMLThreshold) ? 1.0 : 0.0;
      if(okOnnx && MathAbs(onnxSize - refSize) < 0.5) onnxSizeMatch++;
      if(okPure && MathAbs(pureSize - refSize) < 0.5) pureSizeMatch++;

      FileWriteString(
         outFh,
         StringFormat("%d,%.12f,%.12f,%.12f,%.12e,%.12e,%.12e,%.1f,%.1f,%.1f\n",
                      rowIdx, refProba, pOnnx, pPure,
                      errOnnxRef, errPureRef, errOnnxPure,
                      refSize, onnxSize, pureSize)
      );
      rows++;
   }

   FileFlush(outFh);
   FileClose(outFh);
   FileClose(inFh);

   bool parityPass = (rows == 500 &&
                      onnxReady &&
                      onnxOkCnt == 500 &&
                      pureOkCnt == 500 &&
                      maxErrOnnxRef <= InpParityMaxTol &&
                      maxErrPureRef <= InpParityMaxTol &&
                      maxErrOnnxPure <= InpParityMaxTol &&
                      onnxSizeMatch == 500 &&
                      pureSizeMatch == 500 &&
                      nanBlocked &&
                      infBlocked);

   PrintFormat(
      "PARITY500_V105_SUMMARY|rows=%d|onnx_ready=%s|onnx_ok=%d|pure_ok=%d|"
      "max_err_onnx_ref=%.12e|max_err_pure_ref=%.12e|max_err_onnx_pure=%.12e|"
      "onnx_size_match=%d|pure_size_match=%d|nan_blocked=%s|inf_blocked=%s|parity_pass=%s|out_csv=%s",
      rows,
      onnxReady ? "true" : "false",
      onnxOkCnt,
      pureOkCnt,
      maxErrOnnxRef,
      maxErrPureRef,
      maxErrOnnxPure,
      onnxSizeMatch,
      pureSizeMatch,
      nanBlocked ? "true" : "false",
      infBlocked ? "true" : "false",
      parityPass ? "true" : "false",
      InpParityOutputCsv
   );
   return parityPass;
}

int OnInit()
{
   RunParity500ProbeV105Once();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   g_probeFilter.Deinit();
}

void OnTick()
{
   // No-op: pure offline ONNX + Pure-MQL5 verification probe (0 trade orders)
}
