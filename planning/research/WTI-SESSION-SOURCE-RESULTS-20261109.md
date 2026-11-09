# WTI overnight session: chưa qua cửa nguồn

Thực thi 10/11/2026 Asia/Saigon; tên protocol09/11 giữ theo lần freeze.
[Protocol](WTI-SESSION-SOURCE-PROTOCOL-20261109.md) tại `1f602af`, helper/tests
tại `291b957`, [method](WTI-OPEN-EXPANSION-METHOD-20261109.md). Chỉ kiểm source
capacity, không financial experiment hoặc R092 mới. Catalogue91/58 giữ nguyên.

## Kết quả theo từng phiên đã đăng ký

Own18:00NY ngày lịch trước →16:55NY labelday, M1Open mỗi5phút,276pairedslots.
Hai endpoint đủ là điều kiện cần; vẫn phải có ít nhất98% toàn phiên.

| Nhãn phiên | Paired /276 | Coverage | Endpoint đầu/cuối | Admission |
|---|---:|---:|---|---|
|2019-02-04|266|96,38%|Đủ|Không đạt|
|2019-02-05|253|91,67%|Đủ|Không đạt|
|2019-07-02|267|96,74%|Đủ|Không đạt|
|2022-02-07|276|100%|Đủ|Đạt riêng fixture|
|2022-02-08|276|100%|Đủ|Đạt riêng fixture|
|2022-07-05|276|100%|Đủ|Đạt riêng fixture|

Tổng1.614/1.656slots,42missing giữunknown. Không dùng tổng97,46% thay gate
từng phiên. Sundayopen và winter/summer endpoints không thiếu trong fixture;
vấn đề nằm ở coverage nội phiên2019. Không thay bằng Friday hoặc nextquote.
Không chọn riêng2022 hoặc bỏ holiday để làm admissionpass.

## Bằng chứng và kiểm chứng

- 20/20registered day-side requests,20raw responses mới,0reuse/20GET;
  installeddukascopy-node1.51.1, LIGHT.CMD/USD, Bid/Ask M1 UTC. Config trước
  fetch, retry0/WAFoff/failurecap1/deadline180s, PID/progress/events/CANCEL,
  pins/raw/exports/seals/source-snapshots và no-overwrite.
- Fullnative28.796bars gồm21.302explicit sourcebars và7.494nativepaddingbars.
  Padding không được tính là quote hoặc bù42missingroles. Chưa suy thị trường
  không đổi giá, không có giao dịch hoặc sourcecorruption chỉ từ missingbar.
- Decimal/native expansion đối chiếu separateFraction decoder trên106.510
  OHLCVfields; fulltimestamps/order/day/grid/bounds/nativepadding kiểm riêng.
  Calendar oracle dùng explicitUTC winter/summer arithmetic khác NYhelper,
  đối chiếu mọi1.656slots và mọi coveragefield, Bid≤Ask Open/Close.
- 4actual mutations price/time/count/padding đều bịreject. 4focusedtests đã
  đạt ở checkpoint291b957 trước fetch; không chạy lại khi helper/tests không
  đổi. Reviewer xử lý validemptycolumns là absence sau schema validation,
  không ép có baseprices. Separate arithmetic do cùng agent viết/kiểm,
  không independentfeed hoặc externalreview.

| Phase đo thực | Wall | CPU |
|---|---:|---:|
|Collect20requests|10,338s|0,969s|
|Full source/coverage review|1,725s|1,703s|
|Tổng hai phase|12,063s|2,672s|

Không gọi12s là tổng thời gian đọc paper/thiết kế/triển khai. Collector exit0,
pendingreview; reviewer exit0, `admitted:false` là kết quả gate, không crash.
Khôngjobnền,0returns/features/PnL/broker/model/holdout2025+.

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/wti-session-source-pilot-v1/`:config/manifest/rawcache/native
  exports/seals/snapshots/result/review/progress/events. Controllerlock đã gỡ
  sau terminal; giữ PID trong manifest/events.
- `prepare-wti-session-source-v1.cjs`, `review-wti-session-source-v1.py`,
  `wti-session-calendar-v1.json`:savedcollector/reviewer/calendar, pins trước
  requests gồm oldFraction decoder và repohelper/native/lock/protocol.
- ResultSHA`eda95c3a5f7198942293009deeb0b24870b50febcdf17cd5d199b0930bb31817`.
- ReviewSHA`42486cc4d415feb3b07434d65e9ebf3d402c6e0549023acdd67f6038af480779`.

## Quyết định và bước tiếp

**Chưa admit full-session source; không bulk hoặc strategy PnL.** Không kết
luận WTI expansion không có edge. Giữ recipe chưa được định nghĩa, không
giảm coveragegate/đổi clock/padding hoặc fit q/SL để cứu bản này.

Muốn mở lại cần nguồn bổ sung đủ roles hoặc protocolsource mới có căn cứ
giải quyết missing semantics trước outcome; không retry unchanged20requests.
Không tự lấy3phiên2022 tốt làm đại diện lịch sử. Nếu chưa có nguồn mới,
tiếp một cơ chế khác được primary method/source hỗ trợ trong campaign.
M1Open không simultaneousexecutableticks; futures→CFD/targetcontract/funding/
SL/account/prop/OOS/forward vẫn chưa được chứng minh dù sourcepass sau này.

Hậu kiểm hữu hạn: earlysourcegate tránh bulk trên nguồn thiếu; phase timing,
pins và negativeprobes đủ cho lát này. Không có evidence cần thêm Rust/GPU/
DB/RAG/skillmanager hoặc rerun catalogue. Metadata DOI được sửa riêng trong
method bằng publisher, không sửa frozenprotocol/threshold hoặc marketbytes.
