# Nhật–Mỹ: nguồn pilot đạt, chưa chiến lược/PnL

[Protocol](JAPAN-US-SOURCE-ADMISSION-20261109.md) freeze`071e53a` trước fetch.
**Đã review nguồn đúng scope**: hai ngày Nhật, hai nhómclock; không chọnclock
theo lợi nhuận, không tính hướng/returns/PnL hoặc thêm catalogue record.

| Phần | Kết quả thực kiểm |
|---|---|
| JPN nguồn mới |8day-sideURLs,09–10Jan2019 và14–15Jul2022; đúng`JPN.IDX-JPY`, M1UTC |
| Fullraw |49.570fields OHLCV bằng Decimaldecoder và Fractiondelta khác; explicit/padding phân biệt, volume0 giữ |
| Quotegrid |Raw multiplier0,001; không dùng publicpointvalue0,01JPY làm minimumquotegrid |
| Giờ Nhật |Mỗi ngày đủ8mốc08:45/08:46/09:14/09:15 và09:00/09:01/09:29/09:30JST; khôngmissing/crossedroles |
| Nguồn Mỹ reuse |8cachedrawday-sides,4exact15:59NYM1Close/40fields; upperknown-at16NY trước cả08:45 và09JST |
| Mutations |5rejections: nativeprice/time, missing/crossedrole, authority |
| Time |Fetch1,742swall/0,421CPU;review1,451s/1,141CPU;total3,193swall,khôngallresearchtime |

Source two-sided M1 vẫn không simultaneous executableticks. Hai ngày không
chứng thực fullcalendar/history hoặc targetCFDcontract/funding. Không có
JPY→USDtranslation/SL/quantity/prop/time-fit/OOS/forward/authority từpilot.

## Method và cách dùng đúng

[Primarypaper](https://doi.org/10.1016/j.finr.2026.100108) search-served method
về previousUSreturn và Japaneseopeningreversal chỉ là động cơ, không
replication. Directpublisher403/redirectfailure đã giữ; authorpage không có
fullPDF bài này. Chưa biết đầy đủ sessionboundary/rolling/fees của paper.
Không bypass hoặc viết ownrule rồi gắn headlineSharpe vào nó.

Paperfutures khác cash/CFD. [JPXcashrules](https://www.jpx.co.jp/english/equities/trading/domestic/01.html)
xác nhận morning09–11:30JST, nghỉ nationalholidays/01–03Jan/31Dec;
futures08:45 cần tách. [Dukascopyofficialrange](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/)
định danh Japan200+; chưa đủ legalbenchmarktransfer sang Nikkei225future hoặc
FTMOJP225. OwnCFDadaptation phải ghi sourceidentity này và chốtclock riêng.

Lát có thể làm tiếp: ownhypothesis về **cross-marketreaction tại cash09JST**,
khác opening-USselfgap đã thử; không tự là independentedge. Freeze rule,
cohort/calendar/previousUSsession/holidays/costJPY trước nguồn/PnL mới.
Không dùng08:45 để cứu09:00 nếu thua, không crossclockgrid hoặc tính mẫu
chỉ các ngàyquotes đầy đủ mà giấu ngàythiếu. Fullcalendar/currentaccountfit
vẫn cần được review trước stage ứng viên challenge.

## Artifact và tái sử dụng

Privatebase `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`;
`execution-v1/japan-us-source-pilot-v1/` raw/native/seals/sourcepins/snapshots,
manifest/result/review/progress/events; producer`prepare-japan-us-source-v1.cjs`,
reviewer`review-japan-us-source-v1.py`. Nooverwrite,deadline/cancel/checkpoints.

- ResultSHA`f7e4ab0034397d1986d96fe8f91a71aa8fc8ec6f548d279d1c437e5d7cc68ba4`.
- ReviewSHA`6839eb8899417e36099fafee2962ff279d1b58a1480cab2a421e22bd6d3dffb1`.

Các primitive `inspect_expansion`/`explicit_candles` và savedFractiondecoder
reuse, không nới multiassetadmission schema để giảindex=FX/stockfixture.
Sourceonly/privatehelpers không runtimeprovider triển khai. Khôngjobnền.
Catalogue86/58, C1/C2 chưa đạt; Goalactive. Không broker/own2025+/paidprovider.
