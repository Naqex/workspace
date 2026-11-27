# Bản quyết định trước close — có thể khớp hơn, chưa đủ bằng chứng vào challenge

[Protocol](US500-PRECLOSE-REVERSION-20261108.md) chốt trước kết quả: quyết định
hai phút trước close, chỉ dùng nến đã kết thúc; khớp một phút sau. Đây là clock
variant có lý do vận hành, không sửa risk/threshold/fees của bản cũ để cứu PnL.

| Năm | Net chuẩn / stress USD trên10k | Entries /scenario | Cuối mẫu |
|---|---:|---:|---|
|2022|+13,78 / −0,12|25|Flat|
|2023|+45,88 / +26,04|19|Flat|
|2024|+93,40 / +74,46|19|1open, gồm floating|

Không qua tiêu chí mọi năm dương ở cảcosts đã đăng ký. Stress2022 gần0,
không phải lý do giảm phí sau outcome, bỏ năm hoặc gọi là edge chắc chắn.
Các annualbooks riêng, chưa native tick/prop/DD/target funding/dividend.
Giữ cả net dương/âm, sample63entries nhỏ, không quảng cáo challenge-ready.

51,234s tổng3studies×2costs+3nullcontrols+3financialreviews. Fractionoracle
kiểm signal/distance trong mỗi simulation;3causaltests trước PnL kiểm cutoff,
halfday, missingprefix và cuối ngày tương lai không sửa signal trước đó.
Checker riêng đối soát cash/cost/funding/SL/quotes/openmark; không là independent
model/human sign-off. Private`execution-v1/us500-preclose-dev-v1` giữ allpins/
snapshots/results/logs/reviews;khôngorders/modelcalls hoặc2025+read.

So với parent, clockfit không đồng nghĩa edge tốt hơn. Parent2016 có13BUY
signals nhưng0entry vì sauclose thiếu exactfillminute;phải ghi inconclusive
operationalcoverage,không coi0PnL là ngày/năm không có cơ hội hoặc cólợi.
Không chọn lại cutoffs1/3/5minute thànhgrid sau thấy những numbers này.
