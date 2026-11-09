# ML vàng: admission cho labels có SL và phí

Hypothesis chưa triển khai/chưa train/chưa có economic outcomes mới. Tiếp sau
[R067](GOLD-SILVER-FORMATION-RESULTS-20261109.md), không retune pair hoặc noise14.

## Khác thử nghiệm ML trước ở đâu?

[Discovery5](ML-DISCOVERY5-20261108.md) train dự báo return4H không có SL;
policy thực có SL. Đây là surrogate đã được công bố, không bug bị che giấu.
Hai real policies EURUSD đã âm và shuffled control có lúc dương; giữ
[negatives](DISCOVERY5-RESULTS-20261108.md), không suy ML tốt hơn fixed rules.

Đề xuất hỏi: **một model học đúng PnL của cùng SL/holding/cost model có phân
biệt được cơ hội nên bỏ qua trên vàng không?** Asset và target khác; chưa
chứng minh mismatch gây old failure hoặc có conditional edge ở XAUUSD.

## Capability và lát cần khóa trước outcomes

- Reuse 21causal H1 features, native market sizing/protection/cost helpers,
  safe JSON forest export/inference và isolated `.runtime/research-ml` hiện có.
  Verified runtime09/11:sklearn1.9.1/numpy2.5.4/scipy1.18.1; không install/update,
  external weights/pickle hoặc live LLM/provider calls.
- Reuse observed-side XAU H1 sources2018/2021 của R067 cho training admission;
  nếu cần dev2019/2022 từ cùng provider, register exactsource scope trước
  fetch. Không trộn QDM indicativeBid/declarationAsk vào observedAsk mà không
  đổi data model rõ; đổi feed không biến exposed dates thành clean OOS.
- Đăng ký một forest real và paired-label shuffled control cùng config, không
  feature/model/threshold grid. Candidate recipe cần chốt decision cadence,
  nonoverlap holding, actual stop-path labels/cost/quantity và skipped/unknown
  label census; train-only processing, purge theo actual label endpoint,
  model availability sau cutoff. Chưa được phép train từ method note này.
- H1 bars chỉ cho interval proxy, chưa first-crossing tick fills. Tránh gọi
  label "actual broker PnL"; cùng model assumptions giữa label và replay chưa
  thay target spread/slippage, delayed fills, risk/prop/forward qualification.
- Giữ explicit data/risk profile10k/fixed25USD/oneposition, cả reference và
  stress. Freeze stage criterion trước outcome; numerical review và controls
  phải có thể bác bỏ candidate, không được train mãi đến khi xanh.

Primary docs đọc09/11: [sklearn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)
và [time-series validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
hỗ trợ tách fit/validation và tránh leakage; không chứng minh ML trading có
edge. Repo [ML skill branch](../../.agents/skills/strategy-research/references/ml-policies.md)
đã có workflow phù hợp, chưa cần skill/framework mới. Không mở own2025+,
broker/account/provider/paid services hoặc deployment từ method admission.
