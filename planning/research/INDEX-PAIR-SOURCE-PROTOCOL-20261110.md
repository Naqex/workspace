# S&P–Nasdaq: khóa nguồn và vai trò mẫu trước history

10/11/2026, tiếp [methodadmission](INDEX-PAIR-METHOD-ADMISSION-20261110.md).
Chỉ source/census, không statisticaldiagnostics, trade/features/returns/PnL.
SameexistingDukascopy1.51.1; reuse `dukascopy_cached_h1.cjs`, canonical/Fraction
decoder và calendars đã kiểm ở NASDAQ/metals. Không method/pvalue/gridsearch.

## Scope bất biến

- Instruments: `usa500idxusd`/USA500.IDX-USD và `usatechidxusd`/USATECH.IDX-USD;
  hai năm calendar2018 và2021, UTC01Jan→next01Janexclusive, Bid/AskH1.
  8exports/96rawmonthsideinputs; không2019/22outcomes hoặc2025+.
- Dùng hai formationyears tiêu chuẩn đã có trongcampaign, **không gọi chúng
  là cleanOOS** hoặc học lại model cũ. Chưa chọnpair từcorrelation/returns.
- Source-listedH1 bars giữ cả volume0, paddingkhông là quote. Nativefullview
  count so source-onlycount; exactrawhash/proof/census/knownat/side/grid0,001/
  OHLC/volume/order/UTCyear. Không fill/asof/dropmissing hoặc dropcrossedhours.
- Reuse NASDAQhistoryreview/rawbindings đãaccepted, đúng năm/instrument/side/
  monthhash;8Nov/Dec2018/2021raws có thểseed vào cachemới. Chỉ countedreuse khi
  copyhash đúng và sourceeventconfirmscachehit; nguồn đã có khôngrefetch.
  Kiểm exactknowncachechoUS500 khi có acceptedbinding, khôngmặcđịnhreuse.

## Sample admission đã chốt trước giá mới

Ownsample dates từ `nasdaq_cash_calendar.calendar_for(2018/2021)` và
`sealed_m1_review.cash_sessions`, dùng như businessdatecensus; không phải
giờmởcửaCFDhoặcexactfuturessettlement. Mỗi ngày dùng exact16UTCsourceH1Close,
known-at17UTC, haiassets×haisides. SideOpen/Closekhôngcrossed tạirole.

Giữ đủ251dates2018/252dates2021 trongcensus dù thiếu. Samplechỉadmitted nếu
cả503dates đủfourroles và≥240/năm; thiếu/crossed→inconclusivesource, không
đổi giờ hoặc bỏ ngày để chạy statistics. Yearoutside-sampleunpaired/crossed
phải báo riêng, không tuyên bố fulljointyearadmitted chỉ vì sample đủ.
M1/tickvàH1 khácroles; đây khôngsimultaneousexecutablequotes hoặc fills.

## Thực thi và kiểm chứng

Sourcejob private `execution-v1/index-pair-history-v1/`:singlewriter/nooverwrite,
PID/lock/progress/events/CANCEL,deadline240s,retry0/WAFoff/cumulativefailurecap1,
existinghelperboundedbatch. Config/scripts/protocol/helper/native/lock/accepted
parentpins/snapshots trước requests, mỗiexport/finalrecheck; immutable rawcache,
export/proof/seals. Không tựretry khi source/observer lỗi, giữpartialseals.

Preflight trước source: reuse existingH1decoder/canonical on accepted0,001
fixtures, samplingcalendar/grid/identity/missing/crossed/scope và noholdout.
Fullreviewtừngrawmonth bằng canonicalDecimal và separateFractiondelta;
fullretainedOHLCV/census/overlap/metadata/sourceproof kiểm, M1padding không
liênquanH1observations. Sourceempty phải là missingcoverage, không épbaseprices.
Actualmutations price/time/count/hash/falseauthority bịreject, không fakepass.

Lưu sourcecounts/newGET/reuse, coveragequality/samplecensus, wallCPU và exact
seals; collectorpendingreview chưapass. Reviewer sameagent/provider phải ghi
rõ, không independentfeed hoặc targetbrokerspecproof. Không thêm candidate/
policyversion, chưa sửa rules/risk/cost; catalogue91/58 vàGoalactive giữ.
Pass chỉ cho phép đăng kýstatisticaladmission trước diagnostics, khôngpromotion
economics/account/prop/holdout/forward. Không install/update runtime/dependencies.
