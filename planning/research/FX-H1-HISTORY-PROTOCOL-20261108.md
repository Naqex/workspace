# GBPUSD/AUDUSD H1 history: source admission trước outcomes

Kế thừa [pilot thật](FX-H1-SOURCE-RESULTS-20261108.md) và [cơ sở/mapping/license](FX-H1-SOURCE-ADMISSION-20261108.md).
Đợt này chuẩn bị nguồn2010–2024 cho hai USDquotedpairs, **không tính signal,
return,correlation,weights hoặc chọnwinner**. Không sửaR056 hoặc mở2025+.

## Phạm vi cố định

- GBPUSD/AUDUSD×Bid/Ask×15years,60requestbooks. Mỗi book01Jan→01Jan nămsau,
  UTC,H1sourcehourmonthlybuffer(720monthpaths tổng,January2019cacheđãcó).
  Wholemonthrawexposure được ghi; khôngclaim dữ liệu mới làcleanOOS dù
  chưa córeturnstudy của2pairs. Mẫu1999–2019 của paper đãpublic,selection
  cơchế/currency không blind. Khôngreadmetadata/data2025+ ngoàicurrentdate.
- Reuseinstalleddukascopy-node1.51.1 vàsource-onlyH1helper`5664706` với
  pin/hash,noWAF/auth/OAuth/newprovider,hiddenretries0/boundedtransienthelper.
  Sequentialrequests,progress mỗimonth/book,deadline420s;khôngcài package.
  Cacheprivatecampaign`source-hour-cache-v1`,khôngwrite managedQDMstore.
- UTCms/H1start,barhigh/low/closeknownat+3600000;OpenintervalH1khôngactual
  jointtick. Providerunits quoteUSD/baseGBP hoặcAUD,pricegrid0,00001,
  volume native millions,nhãnBid/Ask từrequestkhôngsuy từgiá.
- Chỉsource-listedtimestamps,giữexplicitvolume0,khôngcarriedpadding. Không
  lấpgiờthiếu/holiday,khôngcắt nến bằngPnL. Missing/bidonly/askonly giữcensus
  vàqualitymetrics,khôngbiếnmissing thànhprice0. Khônginventmidextrema.

## Ràng buộc và kết quả được phép

Mộtwriter/rootmới,config/protocol/package/helper/runtime pins trướcdownload;
peryear/sidefiles+sourceproof/rawcachepaths/hash,logs/events/status/PID/
failure/CANCEL. Khôngrerun completedbooks cùngattempt. Nếu lỗi giữ allsealed
books; dừng vàquyếtđịnhrecovery riêng,không tựrestartall60books. Checkpoint
khôngđược gọi CLIresume nếu chưa có implementation/verification.

Sourcevalidator:timestamp/order/range/H1grid,positivefiniteOHLCbounds/
pricegrid/volume,census/dedup,sourcemetadata/hash,nativepaddingcounter. Output
normalization làcopycóversion,rawcachebấtbiến,sourcedelta khôngoverwrite.
Separateimplementation Fraction rawintegerdelta mọiOHLC/volume/bar của
60books đối chiếu nativeexports;pairedOpen/closetime/spread,mismatchesfail
hoặcsourceinconclusive,khôngrepair bằngcarriedquotes. Bind parentpilotreview
vàoriginalsource/protocolpins,sourceknown-at/units/exposure/authority flags.
Mutationtests sai price/timestamp/census/authority;reuse fixtures đãđạt,
khôngmassivebacktest để kiểmdatacontract.

Admission đạt trongscope cần đủ60bookseals vàprice/sourcechecks khớp;report
gaps/pairedcoverage ngaycảkhipricechecksđạt. Không nhận executableticks,
historicalFTMO/The5erscontract,wholemarketcoverage,OOS/edge/prop bởiSHA.
Sauadmission mớifreeze pricecomponent→portfolio hypothesis,entry/exit/cost/
risk/sharedbudget vàretention trước số mới. Hậu kiểmtiming rồi tốiưu nếu
có bottleneck thật; khôngframework/RAG/skill/dashboard mới chođợt này.

## Correction trước outcomes: attempt2

Attempt1`fx-h1-history-v1` dừng4,306s tại metadata `.slice` vì native
`validateConfigNode` normalize requestdates in-place thànhDate.0booksseals,
0numeric/signal/outcomes. Raw12months củafirstrequest đãcache;khôngxoá/đổi
rawbytes. Fix H1helpercopyrequest/dates trướcnativevalidation, thêmregression
callerconfigkhôngđổi sauholdout-reject. M1helper/oldfixtures giữ nguyên.
Attempt2root`fx-h1-history-v2` với sourcepins mới, cùng60requests/date/side/
schema/quality;reuse rawcache đãtảibằngnativecache/hash,khôngtảilạitoàn bộ.
Không gọi attempt1completed hoặc sửaoldmanifest theohelpermới.
