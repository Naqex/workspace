# Nhật–Mỹ: kiểm phương pháp và nguồn, chưa thử lợi nhuận

09/11/2026, tiếp R086 đã gác; không sửa lookback/holding/fees để cứu R086.
Catalogue vẫn86/58, chưa thêm candidate/accountpolicy. Câu hỏi mới: nguồn
giá hiện có có đủ để nghiên cứu phản ứng Nhật sau phiên Mỹ một cách causal?

## Động cơ và phần chưa biết

[Iwanaga2026, DOI](https://doi.org/10.1016/j.finr.2026.100108) và
[author page](https://sites.google.com/view/iwanagay/) xác nhận paper về
US-return và Nikkei futures. Primary search-served abstract/method excerpts
mô tả phản ứng đầu/cuối phiên, cửa sổ30phút và tín hiệu Mỹ ngày trước.
Đây là motivation, cơ chế underlying chưa được paper trực tiếp kiểm; không
copy headlineperformance. Directpublisher403/DOIredirecterror; chưa đọc full
paper, không tự bịa samplefilters/roll/transactioncosts. Authorpage không có
fullPDF của bài này; không bypass WAF/auth hoặc đòi owner mua data/account.

Phân biệt futures với cash/CFD: [JPX contracts](https://www.jpx.co.jp/english/derivatives/products/domestic/225futures/01.html)
ghi futuresdayopen08:45JST hiện tại, khác cash09:00; không tự gắn09:00 vào
paper hoặc áp lịch hiện tại cho cả2001–2024. [2017JPXnotice](https://www.jpx.co.jp/english/corporate/news/news-releases/0060/b5b4pj000001syq8-att/20170919NSNews_E.pdf)
có08:45–15:15. Historicalhour/cashcalendar/CFDmapping cần admission riêng
trước recipe. Related opening-reversal/crossmarketfamily, chưa independentedge.

[Dukascopy range](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/)
gọi`JPN.IDX/JPY` là Japan200+; native metadata`jpnidxjpy` có cùng identity.
Packageauthor gọi followsNikkei225 là mapping sơ bộ, chưa chứng minh bằng
official historical contract/benchmark definition. Không futures replication,
không actual FTMOJP225/The5erssymbol/spec hoặc PnL/USD conversion.

## Source-only pilot khóa trước quotes mới

- Ngày Nhật cố định10/01/2019 và15/07/2022, dùng lại fixturedate convention
  đã chọn ở previoussourcework, không chọn theo biến động/lợi nhuận.
- Chỉ8day-side URLs JPN: UTC09–10Jan2019 và14–15Jul2022, mỗi ngàyBid/Ask.
  Cần haiUTCdays vì08:45JST ở23:45UTC ngày trước còn09:00 ở00:00UTC.
  Existing pinnedproviderhelper, explicit source M1, ignoreFlatsfalse,
  volumeprovider-native; không suy quotevolume thành exchangevolume.
- Kiểm coverage cả hai clockroles **chỉ để hiểu nguồn**, không tính hướng/
  returns/PnL hoặc chọn clock thắng:08:45/08:46/09:14/09:15 và
  09:00/09:01/09:29/09:30JST trên cả hai ngày.8unique roleminutes/day.
  Source timestamps/sideOpen nằm trong `[t,t+1min)`; upperknown-at=t+1min,
  không simultaneoustick/executablefill.
- Reuse sourceproofs US5002019/2022 đã admitted: đối soát lastM1Close của
  08–09Jan2019 và13–14Jul2022, timezoneNY/upperknown-at16NY. Chỉ timestamp/
  rawfields/availability, **không tính return hoặc side**, chưa strategyfeature.
  Same-daypreviousUSclose phải trước cả08:45/09:00JST; không ngàyUTCjoin.
- Raw giữ nguyên, SHA/size/url/package/code/protocol/snapshots/PID/deadline/
  phasecounter/failure. Native explicit output đối chiếu fullrawDeltafields
  OHLCV bằng Fractiondecoder khác; giữ explicitvolume0 và missing khácpadding.
  Rawmultiplier xác định grid; không lấy pointvaluecurrency làm quotegrid.
- Source có wronginstrument/day/shift/grid/schema/pricebinding, duplicated/
  missingrole thì fail/unknown theo phạm vi; không ffill/đổi giờ/ngày để pass.
  RoleOpencrossed không được admit. Kiểm side/time/value/absence/authority
  mutations trước kết luận; unknown không biến thành0 hoặc endpoint fallback.
- Deadline180s cho fetch8URLs, nativehiddenretries0, cumulativefailurecap1
  (không retry trước cap); noauth/WAFchanges. Review deadline180s riêng,
  nooverwrite và counter theo từngrequest/day. Cancel giữa workitems; không
  hứa ngắt ngay một blockingrequest. Reuse partialsealed nếu cần, không
  restart chỉ vì observertimeout. Không sourceprice2025+ hoặc provider mới.

## Đầu ra và quyết định tiếp

Chỉ `source_fixture_reviewed_only` hoặc explicitinconclusive, không recipe/
economicwinner/prop/authority. Nếu đủ nguồn thì trước economics phải chốt
paperclock/method hoặc ownadaptation được ghi rõ, lịch Nhật/US và holidays/
sessionlabel, giáknown-at, source/targetcontract, JPYunits/costs/risk. Không
chuyển sourceprobe thành testlợi nhuận ngay bằng cách đoán những gap đó.

Nếu thiếufullmethod hoặc benchmarkmapping, tìm primarysource hợp lệ có hạn;
không tải history lớn để bù methodunknown hoặc bỏ qua các cơ hội khác.
Chi phí triển khai được xét cùng tín hiệu từ đầu, không chỉ sau khi thua:
grossbenchmark →spread →commission →slippage →funding/credit →net/rounding,
giữ scope/fixedpath khác fullreplay; không tănglot hoặc fee0 để tạo edge.

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
pilotoutput`execution-v1/japan-us-source-pilot-v1/`. Không botpaid/codeclosed,
account/holdout/broker/runtime/globalconfig hoặc skillmanager mới.
