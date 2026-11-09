# R089 source-only fixture trước full cohort

Theo [economic registration](FX-ABNORMAL-DAY-PROTOCOL-20261109.md), freeze
`a74dd44`, và [method admission](FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md).
4 focused causal-feature tests đã đạt trước đọc price fixture; chưa real-data
signal, financial PnL hoặc account trial. ID R089 mới dự kiến, catalogue vẫn88/58.

## Census và reuse khóa trước đọc giá

- Hai entrydates: **Tuesday đầu tiên tháng2** của2019 và2022, tức05/02/2019
  và01/02/2022. Chọn lịch trước source, không theo return hoặc có quote đẹp.
- Mỗi date cần20calibrationweekdays trước shockday + shockday:21days×2slots
  (00/23UTC), cộng entry01UTC/exit08UTC:44targets/date, **88slots** tổng.
  Không chạy feature trên giá thật hoặc tính return/PnL trong source-onlyrun.
- Reuse exact2019/2022 raw/cache thuộc sealed config/result/review của
  `execution-v1/pre-ecb-long-price-v1/`. Pin parentreceipt/config, rawSHA và
  accepted cache SHA. Native `load_coarse_hours` chỉ đọc/kiểm, không prepare
  lại cache, sửa expectedbinding, network hoặc rebuild historical source.
- Native H1 first Bid/Ask + actualtime/sequence là observation; không lấy H1
  Close/high/low hoặc mean(side-extrema) làm quote. Quote có thể trễ; native
  missinghour giữmissing, không gán giờ khác vào slot. GiáEURUSD grid0,00001.

## Oracle và acceptance

Reader riêng stream raw prefix tới target cuối của mỗi fixture, lấy first
quote≥target và predecessor<target, kiểm raw sequence/timestamp/BidAsk.
Không import native quote decoder/cache loader hoặc feature/cost helper cho
oracle. Toàn rawSHA vẫn do native strict loader kiểm; prefix oracle **không**
được gọi là independent full-year feed audit. Nếu source binding fail thì
giữfailure, không normalize raw hoặc tự thay pin.

So đủ88source slots về target, actualtime, sequence, Bid/Ask và≤60slags.
Mọi slot phải resolved đúng contract mới admit bounded fixture; late/missing
giữ explicit và gatefalse. Không gộp88 thành full2019/2022coverage. Mutation
sai price/time/sequence hoặc mất target phải bịreject bởi cùng comparator.
Không dùng fixture chọnclock/threshold/side hoặc xác minh profit của paper.

Một writer/output mới `execution-v1/fx-abnormal-day-source-fixture-v1/`,
deadline120s, status/PID/events/timers/source snapshots/pins/nooverwrite và
CANCEL; không retry tự động. Failure giữ nguyên, chỉ sửa đúng ảnh hưởng.
Không broker, OrderCheck/OrderSend, model, paidprovider/account hoặc2025+.

Tiếp nếu source-only đạt: full predictor/endpoint census của yearscope đã
đăng ký, calibrationwarmup2018/2021 hiện có; native/fullsource pins và synthetic
finance preflight trước outcomes. Data còn thiếu vẫn giữ unknown. Không
đưa0risk/SL vào component rồi tuyên bố đã kiểm account/prop.
