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

## Amendment trước source attempt2 — runtime khác, không sửa binding cũ

Attempt1 đã dừng11,953s trước source quote extraction: current runtime
Python3.12.14/Pydantic2.14.2 khác cacheproducer3.12.10/2.13.5. Native source
hashes vẫn đúng; native loader tính cachekey mới và không thấy file tương ứng.
Đó không chứng minh cache sai hoặc raw mất; không ghi runtime mới vào pin cũ.
Các previous-runtime folders đã kiểm không còn Python executable để reuse.

Attempt2 `fx-abnormal-day-source-fixture-v2` là **source-admission view riêng**:
đọc cache đã niêm phong làm reference, kiểm originalSHA/payloadchecksum/binding/
rawSHA và native source hashes; model validation với consumer hiện tại được
ghi riêng, không gọi `load_coarse_hours` hiện hành đã nhận cache cũ. Quote
primary được kiểm lại từ raw first-after bằng native quote decoder hiện tại,
thêm Fraction/raw-prefix oracle khác và so đủ88slots với frozenreference.
Đầu ra vẫn chỉ source fixture, không feature/PnL, không account replay.

Giữ original producer runtime trong reference và current consumer runtime
trong receipt; không runtime-binding override, monkeypatch, sửa strictloader,
rebuild/overwritecache hoặc gọi fallback tự động. Raw/parent/hash drift phải
fail. Expected dates,88targets,lag≤60s,mutation/census/deadline và mọi gate khác
giữ nguyên. V1failure/scripts/manifest/snapshot giữ tại locator cũ.

## Amendment trước attempt3 — Friday close là thiết kế clock, không outage

Attempt2 đã reviewed25,595s:80/88slots tronglag, 4mutations bịreject, không
realfeature/financialcase. Cả8unavailable làFriday23UTC, rawfirstafter làSunday;
native vàFractiondecoder/reference đồng ý. Không còn runtime transportblocker
trong registeredsourceview, nhưng gate fixture v1 vẫnfalse.

Theo v2 của economicprotocol, attempt3 `fx-abnormal-day-source-fixture-v3`
thay endslot23→20UTC **cho toàn21days/date**, khôngchỉ8missing;88targets giữ
census cùngentrydates/start00/entry01/exit08. Giữ đúng schema/side/lag và mọi
sourcehash, native+Fractionprefixproof/4mutations. Không reuse old23hquotes
như20hquotes hoặc đổi lời giải thích thành observedprofit. Runtime/sourceview
guard như amendment2, không thay original cache/runtime. 5featuretests phải
đạt, có hồi quy Friday23 không được dùng thay Friday20, trước attempt3.
