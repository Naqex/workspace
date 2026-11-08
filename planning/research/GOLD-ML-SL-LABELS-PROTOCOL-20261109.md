# R068: forest vàng học cùng SL/holding/cost như replay

Đăng ký trước newsource fetch, labels/training và economic outcomes. Theo
[method](GOLD-ML-LABEL-ALIGNMENT-METHOD-20261109.md); giữ negatives R038/R039,
không nói old surrogate mismatch đã được chứng minh là nguyên nhân thất bại.

## Source và cơ hội cố định

- Reuse observed-side XAU H1 train2018/2021 từ reviewed
  `gold-silver-history-v1`; chỉ XAU được dùng, không XAG/cointegration outcomes.
  Fetch dev2019/2022 XAU ×Bid/Ask:4exports/48month sources, expected rawgrid0,001.
  Existing provider/package1.51.1/explicitH1helper, cache cùng campaign; WAF/
  token-cache off,retries0,cumulative transient failure budget1. One writer,
  CANCEL/deadline180s, không tự thêm năm hoặc đổi instrument. Source fidelity
  canonical/Fraction/month/census review trước numerical labels.
- Dataset mới `execution-v1/gold-ml-source-v1`; raw/proofs/seals không overwrite.
  Train/dev years đã exposed qua research khác, không clean OOS; own2025+ đóng.
- Chỉ full390minute dates từ frozen US cash calendar2018/19/21/22: weekdays,
  holidays và early closes bị loại theo lịch đã có, trước outcomes; đây là
  opportunity design, không metals/broker opening-hours claim.
- Ba quyết định08/12/16UTC mỗi ngày. Feature bar07/11/15UTC đã đóng, lấy đúng
 100source Bid H1 cuối cùng, dùng21features/TR1,5 của native ML helper; AskClose
  trừ BidClose của bar quyết định là spread proxy. Không future feature fill.
  Thiếu/crossed current bar hoặc không đủ100past bars thì unavailable.
- Fill đúng sourceH1Open tại09/13/17UTC, một giờ sau decision; đây là
  interval proxy[hour,hour+1), không exact tick. Scheduled market exit tại
  sourceH1Open12/16/20UTC. Các intervals không overlap; tối đa3entries/ngày.
  Không next-observed/asof fill. No re-entry/reversal/TP/trailing.

## Label và replay có cùng protective rules

- Initial account10.000USD/year, fixed25USD plannedrisk, oneposition.
  Declared XAU contract100oz/lot,tick0,001,min/step0,01,max50,leverage10;
  commission2,5USD/lot/side, observed-side spread, slip0,1/0,2USD/oz mỗi side.
  Intraday funding0 dưới model này. Không gọi là target broker terms/history.
- BUY entryAsk/SELLentryBid; stop cách actual entryquote đúng distance=1,5TR14
  từ features, floor tick cho BUY/ceil cho SELL; native market sizing bao gồm
  tick reserve, commission và2slippage sides. Quantity/min/max/margin checked.
  SL BUY dùng Bid, SELL dùng Ask. Native open-gap protection trước scheduled
  market exit, rồi intrabar stop; không TP ambiguity. Actual gap loss có thể
  lớn hơn planned25USD. H1model không native intrabar risk/prop compliance.
- Mỗi training opportunity tính hai hypothetical sides theo **reference**
  costs bằng cùng label/replay helper. Target=rounded netUSD/25. Labels chỉ
  dùng khi cả2sides resolved và financeable trên10k; retained census ghi rõ
  invalid/unavailable/unknown và không giả unknown=0.
- Missing/crossed entry: recorded skipped. Missing/crossed held/exit hour:
  unknown; eval block future entries/year, annualnet N/A. Training có unknown
  không fit target nhưng vẫn giữ census/missing-data selection limitation.
  Prediction eval không dùng label-validity/future availability để quyết định.
- Label endpoint là latest possible terminal quote time upper bound, tức
  exitbaropen+1hour kể cả open/SL; purge chỉ endpoint<cutoff. Feature/model
  availability không backdate. Quote interval không biến thành actual fill.

## Hai fits thực và hai shuffled controls

- Fit2018→dev2019 và2021→dev2022; chỉ samples decision thuộc đúng trainyear,
  actual endpoint<Jan1cutoff. Model available cutoff+1hour. Không refit trong
  devyear. One real forest và one paired-row target permutation control mỗi
  fold(seed42+foldindex). Giữ BUY/SELL labels cùng row khi shuffle.
- Reuse RandomForestRegressor80trees/max_depth4/min_samples_leaf100/
  random_state42/n_jobs1, twooutputs, cùng21features. Không preprocessing
  learning ngoài training, feature/model/threshold/hyperparameter grid.
  Export safe JSON qua existing helper, float32 inference; check wholetrain
  rows so library <=1e−10 và synthetic threshold cases trước numeric.
- Flat: chọn side có predictednetR lớn hơn side kia và >0,10R; equality hoặc
  không pack/feature thì no-entry. Eval costs reference/stress dùng cùng pack,
  không train lại theo scenario để cứu kết quả. Null có same opportunities/
  pack nhưng không entries. Reuse resolved labels để đối soát path, không
  dùng training labels làm thay actual account sizing/margin trong replay.

## Gate, review và tài sản

2devyears×2models(real/control)×2costs×2null=16books. Chỉ real policy là
candidate: knownflat/net>0 ở cả hai stressyears,>=100closedtrades/year để ưu
tiên stage tiếp. Gate này là research triage, không proof edge. Shuffled
positive/tốt ngang real là cảnh báo selection; không promote control hoặc suy
pvalue từ một permutation. Chưa internal brakes/prop DD/clean OOS/forward.
Không tăng risk hoặc tune labels/schedule/model sau outcomes.

Trước numeric: fixtures source roles, future mutation, actual-endpoint purge,
SL/time/open-gap/BidAsk/cost/sizing/margin, label/replay parity, unknown freeze,
safe inference. Source/raw checks riêng trước fitting. Review bằng Fraction
cho labels/cash và source path khác; inference/library/parity có scope rõ.
Giữ negatives/cancel/errors và code/input/protocol/package/runtime hashes.

Output `execution-v1/gold-ml-sl-labels-v1`: opportunity/label census,packs,
training/export checks,books,manifest,events/progress/timing/result/review.
One writer, CANCEL,deadline180s sau sourceadmission. Dùng isolatedML runtime
đã có, không install/update/global config/runtime rollout/LLM/broker calls.
Skills research/ML/qualification hiện có, không framework/skill mới.
