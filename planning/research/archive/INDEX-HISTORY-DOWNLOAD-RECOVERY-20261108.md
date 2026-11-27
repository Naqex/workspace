# Hồi phục tải dữ liệu US500 từ phần đã xác minh

`us500-long-m1-v1` đã giữ Q4/2012Bid22968rows/hash472a6e… rồi fail ởAsk,
elapsed65,45s. V1chỉ lưu Error.name nên chưa biết HTTP,decode hay validation;
không được đoán thiếu dữ liệu hoặc gọi là schemafail đã xác minh. Providercache
giữ91dayBidresponses;Askpartial không đượclibraryflushkhi requestquarterfail.

Manualdiagnosticmộtlần cho đúng AskM1Q4/2012 (01/10→01/01/2013UTCexclusive),
existingpackage/options/retry0/WAFoff/batch2. GhiHTTPstatus/publicpath và raw
responsebytes incremental trước librarydecode, khôngheaders/cookies/token/
payload khác. Không đổi URL/source,auth,browser,WAF hoặcnetworkretries.
403/rate-limit/empty/error dừng vàgiữrequest/failinglocation. Deadline120s.
PhầnBidđãsealed khôngfetchlại. Đây là diagnosis khôngstrategyPnL/holdout.

Sau khi biết nguyên nhân mới chọnrecoverinputset; không re-run từđầu hoặc
tự bỏ qua ngày lỗi. Newattempt phải bind/adopt exactparentraw/hash/cost/protocol
vàgiữfailurehistory. Downloadsuccess không làdataquality/strategyqualification.
