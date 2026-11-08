# Chiến dịch tìm ứng viên challenge — Goal mới, 08/11/2026

**Đang thực hiện.** Owner giao mở rộng phương pháp, tìm ứng viên đủ bằng chứng
cho challenge, đồng thời sửa correctness, cải tiến performance và dữ liệu khi
có nhu cầu thực. Goal mới đã active. Quyết định dừng B ở
[campaign trước](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) là lịch sử, không là
điều kiện tự hoàn tất Goal này. Giữ nguyên tài liệu/pins của các đợt đã freeze.

## Đích và cách biết đã đạt

Kế thừa **C1/C2** của campaign trước: ứng viên có lợi thế sau phí và đủ bằng
chứng cho đúng bước challenge; quá trình có protocol, causal inputs, kiểm
chéo số học/nguồn, trial history, prop equity/time-fit, prospective
reconciliation và bàn giao owner. Không hạ ngưỡng để tạo winner hoặc coi một
batch/admission hoàn tất là đạt mục tiêu. Không bảo đảm thị trường có edge.

FTMO/The5ers phải đánh giá riêng theo program và điều kiện hiện hành. Profile
10k/25USD mỗi lệnh và mốc so sánh 3/6/12 tháng kế thừa để nghiên cứu; chưa là
đề nghị mua challenge hay deadline cá nhân. Holdout 2025+, broker sends,
tài khoản/provider mới, trả phí và production vẫn có gate riêng.

## Baseline và các lát kế tiếp

Baseline: 53 hồ sơ/41 policy versions, chưa challenge-qualified. Giữ negatives
và [owner report](OWNER-EVIDENCE-REPORT-20261108.md), không chạy lại 624 cases
FX không đổi. Gold SMA50k là research survivor, chưa đủ time-fit/realism/OOS.

| Lát | Câu hỏi sẽ giải quyết | Đầu ra cần |
|---|---|---|
| Chuẩn hóa đầu vào đang dùng | Một file có hash có thật là đúng loại giá, giờ, side và nguồn không? | Reuse validators, metadata có version, hash/lineage, exposure, units và quality; áp fixture thật, kiểm mutation; không migration/raw rewrite |
| R026 hedge cổ phiếu cuối tháng | Có thể tạo tín hiệu tương đối EUR/US causal bằng proxy đang có không? | Source/clock/mapping admission trước outcome; ghi rõ proxy khác paper, dividend/adjustment unknown; không gọi Total Market là total return |
| Component trước bot | Với recipe được khóa, tín hiệu có giữ economics sau phí qua hai giai đoạn không? | Protocol trước outcome, các ngày thiếu vẫn có mặt, baseline/control và uncertainty; không claim account PnL từ price component |
| Qualification | Survivors có giữ được sau causal fill, prop equity path và dữ liệu chưa dùng không? | Exact C1/C2 review, chỉ affected reruns, đúng permissions; owner handover dễ hiểu |

Mỗi lát có phạm vi hữu hạn; kết quả âm dẫn tới hypothesis mới có lý do, không
đóng Goal mới bằng kết luận B của đợt cũ. Lưu timing/status/log/attempt và
quyết định trước/sau tại artifact/protocol owner. Sau batch có kết quả mới,
hậu kiểm gọn; chỉ profile hoặc dọn khi có bottleneck/phần thừa đã xác minh.
Không xóa evidence, không thêm dashboard/ledger cạnh tranh Paperclip.

## Lát đang triển khai

[R026 continuation](R026-RELATIVE-EQUITY-CONTINUATION-RESULTS-20261108.md)
đã terminal/reviewed:3/4năm mới âm, không đạt; gác exactpriceproxy, không
rescue bằngSL/clock/side. [R010 source results](MULTI-ASSET-TREND-DATA-RESULTS-20261108.md)
đã phân rã data blockers:monthlyhistory84/84 từ2018, ATRfullsessions chỉ32;
asofcap120s không tăng140/144endpoints. [Monthly results](MULTI-ASSET-TREND-RESULTS-20261108.md)
đã hoàn tất4books/review:primaryreference−1.138,18/stress−3.519,01USD trên10kproxy,
khôngretained. Dataset864records cósource/clockreview và tái sử dụng cho numeric
1,416s; không hạ phí hoặc tăngleverage cứu outcome. Bước tiếp: cơ chế holding
ngắn có data/method rõ và khác các exactversions đã gác, freeze trước số mới.
Dùng repo skills hiện có; không tạo một skill quản lý toàn bộ khác.
[Gold session results](GOLD-SESSION-COMPONENT-RESULTS-20261108.md) thêmR054/R055:
cả2negative saufees/0of15stressyears dương, khôngretained. Catalogue hiện55hồ
sơ nhưng vẫn41accountpolicies; không tăngcount bằngpricecomponents. Lát tiếp
ưu tiên full-historyPreECBprice robustness trước thiết kế riskwrapper khác.
[PreECB long results](PRE-ECB-LONG-PRICE-RESULTS-20261108.md):đã terminal/reviewed,
stress12/13years dương/cả4blocks dương; đủ ưu tiên đăng ký1wrapper theo scale
holding-session nhưng chưaSL/account/prop/OOS. Giữ risk25USD,không grid/giữlot
khi nớiSL; xem kết quả này để tiếp, không khởi động lại monthly/gold negatives.
[Recent continuation](PRE-ECB-RECENT-PRICE-RESULTS-20261108.md) đã thêm2023/24
same-clock/cost explicitrawmode:+187,1/+184,9stresspip. Combined14/15positive
years/cả4blocks dương; đủ ưu tiên1riskwrapper, chưaaccount/SL/prop/OOS.
[R056riskresults](PRE-ECB-SESSION-RISK-RESULTS-20261108.md) đã chạy1wrapper
theoholding-sessionRMS20x2/risk25:3.171trades/cost,+1.535,95/+1.078,12USD
nhưng2/4stressblocksâm,khôngretained. Khônghạgate/SLgrid;catalogue56records/
42researchpolicyversions. Lát tiếp sourceadmissionGBPUSD/AUDUSDH1 với
USDquote/existingDukascopy trước cơchế/portfoliobudgetchung,khôngbroker/holdout.
[H1sourcepilot](FX-H1-SOURCE-RESULTS-20261108.md) đãđạt144bars/720Fraction
checks/bridgeEURUSD7.971ticks;chưahistory/PnL. Bướctiếp đăngkýsourcehistory
2010–24GBPUSD/AUDUSD trước numeric,không sourcepadding/nativefillclaim.
[H1historyresults](FX-H1-HISTORY-RESULTS-20261108.md) đãreview60books/
373.652bars/1.868.260checks;719/720months/30crossedhours,fulljointadmission
inconclusive. Recoveryreuse15books vàvolume-roundingmetadata giữrõ. Tiếp
registeredendpointcomponents trênOpenroleshợplệ,giữmissing/crossedrows;
chưaeconomicoutcomes,khôngtrade/newprovider/holdout hoặcR056retuning.
