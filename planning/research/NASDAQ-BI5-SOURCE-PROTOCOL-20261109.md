# NASDAQ BI5: một giờ archive đối chiếu nguồn2019 đang thiếu

Đăng ký trước marketdatafetch. Mục tiêu chỉ source admission cho25Jan2019
14:00–15:00UTC, nơi R065v1/v2 dừng ở14:49 vì không có quote/M1. Không thử
strategy mới, khôngnớiunknowngate, không scanprice/PnL/own2025+.

## Primarymethod đã kiểm trước fetch

Installeddukascopy-node1.51.1 dùng JSON, docs upstream [cache guide](https://www.dukascopy-node.app/using-cache)
xác nhận đổi khỏi BI5 từsau1.46.4. Đọc sourceMITv1.44.0 tại commit
`fa2cf83bbf686000bc4b9f86cf8110347784a80e`: [URL generator](https://github.com/Leo4815162342/dukascopy-node/blob/fa2cf83bbf686000bc4b9f86cf8110347784a80e/src/url-generator/index.ts),
decompressor/types/date/data-normaliser/formatVolume/metadata/license. Captures
trong private`nasdaq-bi5-method-source-v1`, localGitblobSHA1 đối chiếu tree.
Không install/chạy oldpackage/sourcecode; không đưa providerREADME thành
quyền globalconfig. Officialbankwiki fetch2lần timeout, không claim đã đọc.

VerifiedURLroot`https://datafeed.dukascopy.com/datafeed`, instrumentuppercase,
UTCyear/month0based/day/hour. Instrumentoldmetadata USATECH.IDX/USD có
decimalFactor1000. LZMAdecompress, record20bytes bigendian signed3int32 +2float32:
offsetms/Askint/Bidint/Askvolume/Bidvolume. Giá/1000, offset+hourUTC, archive
quotevolumes đã ởunitmillions. Sourceinstrument không targetFTMO/NQ/QQQ.

## Exactly one registered marketdata request

`https://datafeed.dukascopy.com/datafeed/USATECHIDXUSD/2019/00/25/14h_ticks.bi5`.
MộtGET, TLS bình thường,timeout30s,compressedcap8MiB/decompressedcap32MiB,
decoder memorycap64MiB,totaldeadline90s. Không retry/auth/WAF/403/429bypass,
khôngAWSrequesterpays/newaccount/paidprovider hoặc rộng thêmngày. HTTPempty/
404/denied phải record/giữrawmetadata, không đổi thành quote rỗng hợp lệ.

Reuse cachedJSONV1`2019-01-25-14.json`+rawproof/review của8tickhours; không
fetch lại JSON. Pin request/config/code/protocol/methodsources/oldJSON/raw
hash trước network. Newoutput`execution-v1/nasdaq-bi5-source-fixture-v1` giữ
rawBI5/export/manifest/results/review/status/events/failure/limit. One writer,
CANCEL,not source overwrite. No strategy/financial/book changes trong probe.

## Byte và quote admission

StdlibPython lzma/struct; separate decode bằng byteoffset/int.from_bytes và
IEEE754Fraction để kiểm20bytereccount/eof/trailingbytes/order/same-msordinal/
timebounds/grid/Bid<=Ask/nonnegativefinitevolumes. Syntheticfixture trướcfetch
để check sideorder/clock/truncated/schema/size guards. Capture rawsha256 và
decompressedsha256. Không quote padding/interpolate/sort để sửa lỗi.

So JSONV1 theoorderedsubsequence của(time,Bid,Ask) cómultiplicity: mọi oldquote
phải giữthứtự/giá; extraarchivequotes reportriêng. Không gọi2transports là2
independentfeeds. Inter-transportvolume sofloat32precision, reportmismatches
riêng; chưa dùngvolumesignal. Binaryvolume phải faithfulbytes trong mỗi export.
Quoteadmission cần fullbinaryreview/oldquotecontainment; không claim complete
marketcoverage hoặc targetbroker. Sourcegap/minute14:49cóquote/khôngquote và
maxinterarrival được đo trướcanyPnL. Cóquote mới thì register derivedview/
affectedreplay riêng; khôngquote thì giữ2019unknown, khôngrerununchangedbook.

Mutations wrongprice/time/side/order/recordcount/rawhash/authority reject.
Sameagent/provider, không độc lậphuman/modelaudit. OriginalR065twoyeargate
và v1unknownstate không được sửa thànhpass chỉ vì sourceprobe đãterminal.
