# R024: endpoints có thật trong export; một lần mở cửa muộn chưa đủ bằng chứng

**Metadata đủ để thiết kế một thí nghiệm component tiếp theo, chưa có strategy
hoặc PnL R024.** [Protocol](WEEKEND-GAP-DATA-ADMISSION-20261108.md), commit
`767b585`, giữ scope trước endpointdiagnostics: EURUSD2019/2022 đã consumed,
không đọc outcome2025+, không tải market mới hoặc rebuild cache.

## Bằng chứng mới

| Scope |2019|2022|
|---|---:|---:|
|ObservedH1 / source ticks trong cache|6.224 /29.186.310|6.240 /36.946.763|
|Weekends nằm trọn trong annualscope|52|51|
|Tìm thấy cả Fridayclose và Sundayopen trong searchwindows|52/52|51/51|
|Raw quote endpoints kiểm trực tiếp|104|102|
|Fridayquote sớm hơn declared17:00NY|3,319–115,866giây|0,028–45,455giây|
|Sundayfirstquote muộn hơn declared17:00NY|1,330–10.799,984giây|0,007–247,698giây|
|Saturday có ticks theo NYcalendar|0|0|
|Declaredweekend47/48/49giờ qua US DST|1/50/1|1/49/1|

Denominator2022 có51 vì Friday30/12→Sunday01/01/2023 nằm ngoài annualscope;
không đọc phần năm kế tiếp hoặc gán missingquote. ReferenceNY17:00 là declared
clock cho inputadmission, **không historicaltargetbrokercontract**. Không drop
holiday khỏi denominator hoặc đổi mốc theo giá/PnL.

## Trường hợp muộn gần ba giờ

Weekend24→26/05/2019: firstsourcequoteSunday tại23:59:59,984UTC (19:59:59,984NY),
saureference17NY10.799,984s. Fridayendpoint sequence13.689.577; Sundayendpoint
13.689.578. Oracle đọc tickCSV xác nhận timestamp, Bid/Ask của hai endpoints và
đúng hai dòng liên tiếp. **Export này không có quote sớm hơn ở giữa.**

Điều đó không chứng minh thị trường/broker đóng, cũng không xác định lỗi do
provider, exporthayavailability. Không lấy19:59 làm17:00, không padding/carry
giá để dựng gap hoặc suy “không có tick=giá không đổi”. Futureprobe phải định
qualitydeadline trước payoff, giữ missing/lateweekend trong denominator và
không hardreject cảhypothesis do một lỗ hổng nguồn.

## C2 trong scope đã kiểm

- Rehash3,023GB rawCSV của hai năm, parentconfig/completed/result/rawseal và
  H1cache; JSONpayloadchecksum/originalbindings khớp,3producer snapshots giữ.
  Cache dùng originalsource; không sửa hash để nhận currentreplaycode.
-12.464H1 qua existingCoarseHour schema/OHLC/grid/BidAsk/time/sequence/tickcount.
  Validatorfilebytehash khớp producer; currentreplaycodeparity không được suy.
-6negativecases reject: wrongbinding/checksum/reverseorder cho mỗi năm;
  reverseorder bị chặn ngay firstsequence, không claim mọi orderguard đã được
  isolate-test. Calendar có đủ47h/49hweekends, không ép48h quanh DST.
- Raworacle riêng scan66.133.073CSVrows, kiểm206selectedquote timestamps/BidAsk
  và103close→open source-row adjacencies. Không revalidate mọi giá/field của
  66millionticks, không independentfeed hoặc independenthuman/modelsign-off.
  Cache và raw cùng một QDMsource, không chứng minh brokertradability.
- Không tính pricegap/returns/gapfillrate hoặc strategyoutcome. Inputprices đã
  consumed trong campaigncũ, không trở thành cleanOOS vì review lại.

| Workload đo | Wall | Giới hạn |
|---|---:|---|
|Metadataadmission gồm rawhash/cachevalidation/calendar|39,159s|CPU8,688s; không mô phỏng|
|Rawendpointoracle|15,917s|Đọc dòng nhưng chỉ parse206endpointquotes; không fullrawreplay|

Hai workloads khác nhau; không gọi đây là speedup của tickbacktester hoặc
cộng thêm research/webtime chưa đo. Không cần GPU/Rust/cacheframework mới.

## Quyết định, nguồn và tiếp tục

R024 từ `price_data_spec_possible` sang `endpoint_metadata_reviewed` cho đúng
hai năm; chưa policyimplementation, không tăng sốrules hoặc strategies.
Một lateopen quan trọng được giữ thay vì tự loại theo eventualPnL. Chưa có
primaryfullmethod đọc được: publisher/NTUpaper403, MDPI429, không bypass/retry
hoặc gắn abstract thành paperreplication. Nguồn/giới hạn ở [preflight](WEEKEND-GAP-DATA-ADMISSION-20261108.md).

Bước tiếp là [component probe đã đăng ký](WEEKEND-GAP-COMPONENT-PROBE-20261108.md)
trên same2019/2022data, entry/exit/quality/costs khóa trước gap/returnoutcomes.
Đây là kiểm cơ chế giá sauphí, không account/risk/propqualification; đủ evidence
mới viết rule vào sharedengine. Không chạy lại Gold/IBS hoặc mở2025+/broker.

Private`execution-v1/weekend-gap-data-admission-v1`: `review.py`,manifest/
progress/events/result, `endpoint_oracle.py`,oraclemanifest/progress/result.
Review28700/session68752 và oraclesession44982 terminalexit0; khôngjobnền.
Không source/product/runtime/skills changes hoặc newmarketdata/model/brokercalls.
