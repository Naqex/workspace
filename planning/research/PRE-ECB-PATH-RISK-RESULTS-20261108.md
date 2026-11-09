# Giá đi ngược đủ lớn: chưa thể bỏ stop — 08/11/2026

Thực hiện [protocol](PRE-ECB-PATH-RISK-20261108.md), source65b833f và correction
3be44f8. Reuse raw-bound H1 cache và commonmask attribution; không rerun
simulator, không đổi parent hoặc mở dữ liệu mới. 8 focused tests đạt.

## Câu hỏi → phép đo → quyết định

**Câu hỏi:** giữ tới14:00 có tổng lời tốt hơn SL cũ, nhưng giữa đường phải
chịu mức giá đi ngược bao nhiêu? SELL đóng bằng Ask; đo observed extrema từ
entry02NY tới quote đầu14:00Berlin, không lấy cả exit-hour nhìn tương lai.

**Kết quả:** 519/519matched dates đo được (259năm2019,260năm2022), không thiếu
H1 trong các cửa sổ đó. Đủ observed hours không chứng minh feed liên tục hoặc
broker fills hoàn hảo. 25/12/2019 thiếu endpoint vẫn excluded;01/01/2019 thiếu
entry đã ở denominator upstream. Không gọi cả năm là complete noSL account.

MAE là mức giá đi ngược lớn nhất; MFE là mức đi thuận lớn nhất trước endpoint.
Percentiles dùng nearest rank, không là khoảng tin cậy hoặc dự báo tương lai.

| Năm | MAE trung vị | MAE p95 | MAE lớn nhất | MFE trung vị | MFE p95 |
|---|---:|---:|---:|---:|---:|
|2019|12,6pip|35,9pip|68,7pip|12,8pip|40,6pip|
|2022|25,5pip|82,2pip|125,8pip|19,8pip|75,6pip|

Nếu giả định giữ tới14:00 **kể cả sau lúc parent đã có thể SL**, dùng đúng lot
đã quan sát của mỗi cost book, lỗ tại Ask bất lợi nhất cộng roundtrip phí/slip
như bảng. Đây là **worst hypothetical liquidation từng path**, không actual
trade loss, account drawdown, first-breach hoặc prop simulation.

| Năm/phí | Lỗ giữa đường trung vị | p95 | Lớn nhất | Số ngày vượt25USD | Lớn nhất / planned25USD |
|---|---:|---:|---:|---:|---:|
|2019 chuẩn|23,75USD|72,72USD|137,04USD|125/259|5,48R|
|2019 cao|23,80USD|71,53USD|132,25USD|122/259|5,29R|
|2022 chuẩn|27,17USD|75,46USD|132,55USD|140/260|5,30R|
|2022 cao|27,27USD|75,90USD|132,99USD|139/260|5,32R|

Phí cao đôi khi có cashloss thấp hơn vì parent chọn lot nhỏ hơn, không phải
phí giúp strategy. Không nhân đôi519 thành1038independentpaths.

**Ví dụ hậu nghiệm, chỉ để giải thích:**12/09/2019 SELLentryBid1,10133,
pathAskmax1,10699: đi ngược56,6pip. Với0,24lot reference, giả định chưaSL thì
lỗ tại extrema cộng phí137,04USD; endpoint component lại net468USD/lot, tức
112,32USD ởlotđó. Hai số cùng đúng ở thời điểm khác nhau. Không nhận112,32USD
là actualparentprofit hoặc chọn ngày này làm policy. Raworacle chỉ kiểm8ngày
đăng ký, không riêng ví dụ hậu nghiệm này.

Nhóm endpointreference dương:2019 có137dates, MAEp95=24,9pip/max56,6pip;
2022 có129dates, MAEp95=35,7pip/max53,1pip. Phân nhóm biết sau outcomes không
là entryfilter. Endpointprofit không đủ chọn stop hoặc gọi noSL an toàn.

**Quyết định:** giữ parent parked, SL/risk cũ không thay đổi. Không bỏSL hoặc
giữlotcũ khi nới stop. Chưa có cơ chế đăng ký cho stop thay thế, chưa chạy ATR
grid để cứu. Nếu tiếp tục phải chốt cơ chế invalidation/stop và tính lại lot
trong cùng plannedbudget trước đo; portfolio/nativeprop/OOS/forward vẫn riêng.

## Bằng chứng và giới hạn review

Private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/`.
`pre-ecb-path-risk-v2` giữ manifest/source snapshots/result/events/status,
`review.py`, `review-result.json`; fixtures/tests/log ở sibling
`pre-ecb-path-risk-fixtures-v2`. Numeric resultSHA:
`8535904a01425e4ab85e9458b790246c2470248e238bb661034cc8b8e995438b`.

- Loader kiểm rawSHA/cache schema/runtime/source/order/grid, endpoint Bid/Ask/
  time/sequence và wholehour continuity. Producer hiện hành đúng cache;
  không rebuild/rebind oldpins. Numeric không parse lại66triệuticks để lấy
  extrema của whole-hour windows, nhưng vẫn kiểm rawhash.
- Separate implementation kiểm arithmetic/distributions toàn519rows, quantity
  binding riêng2costs; đọc/hash66.133.073rawrows, parse295.728selectedticks
  trên8paths đã đăng ký (4dates sớm nhất/năm). Cả8extrema/endpoints/counts
  khớp;4mutations reject: maxAsk, sequence, stresscash, stressquantity.
- Review cùng agent bằng code khác; không independentagent audit/fullannual
  rawextrema oracle/brokerfillproof. Không xác định thứ tự/thời điểm high/low,
  gaps nộiH1 hoặc SLfirstcrossing cả năm từ các summaries này.
- Numeric7,447s CPU7,375s; raw/arithmeticreview39,720s. Timings của lát mới,
  không speedup toàn pipeline, activecode/researchtime hoặc quota/token cost.
  Simulation/broker/model calls=0.

## Failure và hậu kiểm

Attempt1/source65b833f dừng3,608s tại guard lotbằngnhau,0pathcomputed, không
ghi đè. Sourcebooks xác nhận cost-aware sizing khác165dates2019/50dates2022.
Correction3be44f8 có regression, protocolappend trướcnumericv2: deduplicate
**quotes/path**, giữ **sizing/cost riêng**, không đổi strategy. V2numeric và
reviewterminalexit0, không worker nghiên cứu còn chạy.

Chưa có bottleneck cần framework/GPU/Rust: cache reuse trả lời dưới8s;
rawcheck là phần chờ nhiều hơn nhưng hữu hạn~40s. Giữ validation và sample,
không hạ guard để nhanh. Failure→fix→run giữ đầy đủ; không mở fullbatch chỉ
để lấp receipt. Không có accountbacktest hoặc challengecandidate mới.

Qualification skill thêm ownerhandover và [ownerreport](OWNER-EVIDENCE-REPORT-20261108.md)
có ví dụ; trạng thái `prepared_not_demonstrated`. Agent chuẩn bị không nghĩa
owner đã hiểu/thực hành; hiểu strategy không thay economicedge/propfit.
