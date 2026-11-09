# R086 — giá trước FOMC: dương phí cơ sở, chưa chịu được stress

[Protocol](US500-FOMC-PRICE-MOMENTUM-PROTOCOL-20261109.md) freeze commit`7f7ddb6`
trước giá/outcomes mới.32anchor rows/32books/256financialcases đã đối soát;
**không qua frozen triage**, chưa ứng viên challenge. Catalogue86records,
58account policy-modelversions giữ nguyên. Không xem256cases là256lệnh độc lập.

## Kết quả dễ hiểu

Tín hiệu dùng **giá đã biết trước cuộc họp**, không nhãn surprise biết sau.
Một researchunit=1USD/indexpoint; số dưới đây **không là return trên tài khoản**.
Mỗi năm8event windows, BUY/SELL theo dấu25sessionpricechange; không SL/sizing/
equity/portfolio hoặc gửi broker. Cả32anchors có đủ đầu vào/endpoint, khôngunknown.

| Cohort chính | Net phí cơ sở | Net stress | Stress tốt hơn tuần đối chứng |
|---|---:|---:|---:|
|2019,8event windows|+60,55USD|−63,33USD|+396,16USD|
|2022,8event windows|+151,62USD|−14,66USD|+388,77USD|

Quy tắc quanh FOMC tốt hơn matchedweek trong hai năm, nhưng **tốt hơn một
đối chứng đang lỗ chưa đủ**: cả hai stressnet chính vẫn âm, không qua gate
primary>0. Không chọn control tốt nhất hoặc bỏ năm xấu để đổi verdict.
Hai năm exposed/development; cohort nhỏ/overlap, chưa cleanOOS/edge/prop-fit.

## Phí nào làm mất phần dương?

| Cohort/scenario | Sau BidAsk+slippage, trước funding | Funding debit | Net cuối |
|---|---:|---:|---:|
|2019 cơ sở|176,89|116,34|60,55|
|2019 stress|168,89|232,22|−63,33|
|2022 cơ sở|310,34|158,72|151,62|
|2022 stress|302,34|317,00|−14,66|

Đơn vịUSD/researchunit. Funding8%/16%/year, debit22UTC/cents từng ngày theo
protocol, **chưa target-broker swap đã xác minh**. Vì vậy kết quả nói “không
đủ bền trong scenario đã khai báo”, không chứng minh phí FTMO/The5ers chắc
chắn làm strategy thua. Cũng không được đặt funding0 để nhận winner.
Core `gross_account` ở embeddedBidAsk đã chứa tác động side prices; trường
`spread_cost_account=0` không nghĩa giao dịch miễn spread. Funding ở component
ledger, corefinancing0 không có nghĩa tổngfunding0.

## Correctness và source

- Sixfocusedtests đạt: calendar/DST/crossyear/holdout; futureexit không đổi
  tín hiệu; missingfeature khác flat; missing/crossedentryexit; BUY/SELLfees,
  fundingrounding/boundaries bằng Fraction; fullbookcensus/unknown/authority.
  Lượt đầu testharness thiếu `bind_core`, sửa setup trước realprices; không
  marketattempt bị ghi đè hoặc strategyrule sửa sau outcomes.
-126unique minutes/252rawday-sides; mỗi mốc đủBid/Ask. Reuse250raws đã seal,
  chỉ2newday-side GETs cho06/01/2023. RawdeltaFractionOpen kiểm252sideinputs,
  đối chiếu mọi quote/feature vào raw, không gọi252checks là fullOHLC/history.
- Separate reviewer dựng lại sessionoffsets từ acceptedexchange calendars,
 16events/publication từ acceptedR062calendar; partialJan2020/2023 đúng scope.
  Không mở annual-loader yearguard hoặc holdout2025+.
- Trước realPnL:256syntheticfinancialcases và5mutations net/funding/clock/
  unknown/authority bị reject. Sau run:256/256actualcases và32books đối soát
  Fraction, tất cảfundingboundaries, source-preparedrows giữ nguyên.
- Sameagent/differentmethod, không independentfeed/model/human. M1Opens riêng
  side không simultaneous executabletick; không kiểm intraholdingpath,
  margin/drawdown/SL/prop/time-fit/forward hoặc ownerhandover.

## Hậu kiểm vận hành và thời gian

| Phase | Wall / CPU | Kết luận |
|---|---:|---|
|2tailGETs|0,815s /0,281s|Không bulkrefetch|
|Prepare126minutes/252raws+pins/snapshots|188,998s /6,469s|Vượt180s khi finalprogress emit; giữfailure|
|Separate raw/calendar+synthetic review|5,968s /1,906s|Nguồn và256syntheticcases đạt|
|Economics32books|0,665s /0,547s|Không numerical bottleneck cầnGPU/Rust|
|Actualreview|0,314s /0,234s|256cases đạt|
|Research/authoring|Chưa timer đầy đủ|Không gọi tổngworkerwall là toànquytrình|

Prepare đã lưu source/result và kiểm finalbindings **trước** finalprogress
deadlineexception; chưa chạy realPnL. Không xóa lỗi hoặc rerun: reviewer
kiểm toàninput/calendar/preflight, sau đó receipt `source-recovery.json`
ghi lý do nhận phần sealed, rồi mới chạy economics. Không thay rule/input/
originalpins; toàn bộ original producer/reviewer snapshots giữ nguyên.

CPU nhỏ so wall chỉ khoanh vùng nonCPUwait; **chưa profile để quy lỗi cho disk**.
Thiếu guard/progress trong rawpreparation loop là điểm cần sửa trước reuse
runner cho workload lớn: kiểm cancel/deadline theo chunk, phátcounters trong
loop, seal terminalstate sau guard. Không tăngdeadline hoặc chạy lại history
chỉ để có timing đẹp. Đây là private bounded runner, chưa sửa runtime chung.
Skill hiện có đủ: không tạo manager/skill/framework mới hoặc gọi self-review
là independentreview. Không job còn chạy.

## Artifacts và quyết định

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/us500-fomc-momentum-v1/` giữ source/specs/preparedrows/rawcatalog,
snapshots/manifests, source/recovery/failure, rows/summary/result/review/progress.
Tailsource tại `execution-v1/us500-fomc-momentum-tail-v1/`.

- ResultSHA`41f953b4402e7a2e2b06a84ff744a872947394fef276fb110fb87a2cea0e7dbd`.
- ReviewSHA`74ba754280e1da21788df4bdd68a92e915b3e4fe85233ee85fe2377da747489e`.
- SourceReviewSHA`f72abd638f627b427a99b51018fc8f481a600b52bc5ca48c42c8bfa8f2cb1c88`.
- RecoverySHA`9b669275175fc3837aca373ccca318d89a711ae782bf63b4ea026b82fad257e1`.

**Gác exactR086 theo frozenstressgate.** Chưa bác bỏ toàn cơ chếmonetarymomentum.
Một follow-up hữu hạn có giá trị là admission **funding/spec thật của index
CFD đích** từ nguồn chính thức: chỉ khi có evidence materially khác scenario
mới đăng ký distinctcostdiagnostic; không phí0/horizon/lookbackgrid để cứu.
Nếu không xác minh được publicterms thì ghi unknown, không lặp source/PnL.
Chưa holdout/broker/account/feed trả phí/challenge/runtime mutation; Goalactive,
C1/C2 chưa đạt. NHP/Fury vẫn publicreference, không mua/cài/clone EA.

### Delta: public target-cost admission đã rà cùng lượt

09/11 đọc lại [FTMO Symbols](https://ftmo.com/en/symbols/),
[The5ers specs](https://the5ers.com/asset-specifications/) và
[The5ers commissions FAQ](https://the5ers.com/faqs/what-are-the-spreads-and-commissions/).
FTMO textreader chưa trả exactUS500rows; The5ers specs defaultForex, yêu cầu
MT5 để xem đúngsymbol. FAQ xác nhận indexcommission0, nhưng không cung cấp
rate/mode/multiplier/resetclock của US500 đúngprogram/account. Specs cũng
cảnh báo weekendcarry có swapcost cao. Không lấy FTMOUS/OANDA, Exness hoặc
broker khác thay profile đích; không dùng Forexcontract100k cho index.

Publicreview hữu hạn đã xong: chưa đủ sourcepackage để repricing R086, không
mua account/feed, không zero-swap inference hoặc lặp lại cùng3pages. Chỉ mở
lại costdiagnostic khi có symbol/account specification mới và đăng ký trước.
Trong lúc thiếu package, chuyển method/source admission sang cơ hội khác có
inputs/holding/costs tái hiện được; giữ R086parked, không xem nới gate là tối ưu.
