# US500 lịch sử dài từ M1: tái sử dụng cho nhiều hypothesis

Campaign C1/C2 tiếp tục, không dừng sau checkpoint. Data capability mới phát
hiện upstreamH1/D1 low không khớp134observedticks trong minute18/10/2022
15:38UTC;M1khớp toànOHLC. Vì vậy không dùng shortcutD1/H1range để ép nhanh.
Chi tiết ở [oracle](INDEX-DAILY-RANGE-ORACLE-20261108.md). Chỉderive higher
timeframe từsourceM1 đã kiểm; vẫn giữgaps và giới hạn sample/tickfaithfulness.

## Read-only data preparation trước các outcomes mới

- ExistingpublicDukascopy/package1.51.1/source/lock reviewed. USA500idxusd,
 M1Bid vàAsk,UTC01/10/2012→01/01/2022exclusive. Quarterlyparts:Q4/2012 rồi
 4quarters×2013–2021,37quarters×2=74requests. Không2011,không2025+.
- Reuse2022/23/24 sealedquarterdata đã có,khôngfetch lại. Năm2013 vàQ4/2012
 làmwarmup/context cho12calendar-month trend; chưa tự chuyển thành cleanOOS.
 Olderdata làretrospectiveextension sauxemlaterresults,không selection-free.
- Onecontroller/onewriter,perquarterrawseals/status/PID/log,source/protocol/
 package/runtimehashes. WAFoff/tokencachefalse/retry0/batch2/pause300ms;
 403/error/emptydừng,khôngauth/bypass/fallbackprovider. Totaldeadline3600s,
 CANCELgiữarequests. Giữpartialverifiedparts đểkhôngfetchlạikhiresume;không
 overwritefailure/outcomes hoặcautospawnretry. Khôngmodel/brokercalls.

Kiểmrawhash/schema/order/quarterbounds/grid0,001/volume/BidAskalignment,
khôngsort/dedup/fill. AggregationUTCday giữ first/lastactualquote times vàside
OHLC;không giảmidextrema hoặcfullcoverage. MộtngàyM1/tickoracle không chứngminh
mọingàykhônglỗi; candidatepromotion cầnnative/source/fill/risk/uncertaintygates.
Chuẩn bịdata không làPnL/edge/challengepermission. Exactnumericalrecipes/trials
phảiregistertrướcoutcomesmới,khônggridsearch cứu losers. Reusearchivevàsnapshot.
