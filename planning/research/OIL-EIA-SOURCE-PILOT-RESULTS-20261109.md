# Oil/EIA: raw/source đã kiểm, chưa admit ETF→CFD economic study

[Protocol](OIL-EIA-SOURCE-PILOT-PROTOCOL-20261109.md) `80e2bad` trước8requests.
2dates×2assets×2sides đãfetched/reviewed; **fixture không đạt gate** vìUSO thiếu
exact16:00M1Open ởcảhaidates, và2019USOcashcoverage382/390=97,95%<98%.
Khôngnewstrategy/PnL, khônggọithấtbạichỉvìmodelđỏ; dữliệunguồn đãcógiới hạn.

| Asset / date | PairedcashM1 / expected | Nativepadding mỗi side | Exact4endpoints |
|---|---:|---:|---|
|USO2019-01-09|382/390|878|Thiếu16:00|
|WTIproxy2019-01-09|389/390|64|Đủ|
|USO2022-07-13|390/390|810|Thiếu16:00|
|WTIproxy2022-07-13|390/390|60|Đủ|

16:00M1Open đòi quotesauclockclose; regularsession390minutes cóthểđủmà
khôngcóbar16:00. Đây là clock/endpointmappinggap, không tựsuynguyênnhân là
corruptedfeed. Không thay16:00Open bằng15:59Close/nextquote trongprotocolcũ.
Mộtrevision sửdụngbarCloseknown16:00hoặcexecutablelasttick phảiđăngký riêng,
giữfilltiming/ETFvsCFD distinction, khônglấy cáiđẹp saukhi tínhPnL.

8rawURLs/7.056explicit sidebars/35.280OHLCvolume checks;timestamps/order/
fullnativeexpansion/paddingđượcbind bằnghelpershiệncó. Grid0,001/provider
volumemillions, chưaexchangevolume/adjustments/rollverified.3mutations ở
disposablecopiesexplicitprice/paddingprice/timestampđều bịchặn; frozenbytes
giữnguyên. Open/CloseBidAskpairednoncrossed; khôngsimultaneous/tickcertificate.

Producer2,237s/review0,330s, tổng2,567s;callsraw8, broker/model0, no2025+.
Reuseexistingnative/helper/provenance, khôngpackageupgrade/validatorDB mới.
Khôngactualnumericbug/retry hoặc cầnperformanceoptimization; existing skills
đủsourceadmission. Fullsourcevalidation dùngDecimaldecoderhiệncó, khôngclaim
independentfeed; noPITeventcalendar/fullhistory/economics hoặcpropacceptance.

## Quyết định và phần cần làm tiếp

GiữETF→CFDtransfer **chưaadmitted**, khôngbulkfetch/PnL từpilot. WTIquotes
cótrênhaifixturekhôngchứngminhWTIrulecóedge hoặcđượcphépdùngpaperUSOoutcomes.
[EIAarchive](https://www.eia.gov/petroleum/supply/weekly/archive/) đãxácminh
release dates, nhưngallhistoryeventcensus/actualreleasehours/exceptions cần
proofriêng; [29Jun2022statement](https://www.eia.gov/pressroom/releases/press507.php)
giữ2dataweeks cùngreleaseevent, khôngdoubletrade. Cost/contractspec củađúng
targetprogram chưaadmitted. Hướngtiếp làcalendar/endpointsemanticregistration,
không thêm mộtnghiêncứucorrelationsauđó giảedge.

Private `execution-v1/oil-eia-source-pilot-v1/`;savedproducer/reviewer/rawcache/
exports/seals/manifest/snapshots/result/review/progress/events giữđủfailedgate.
ResultSHA`fd7fd0f992e60655d4674f8bbb46b507897f727f047ef162c91baba4e658888e`;
reviewerSHA`805a4c5b39fe37115c0e90d59eeee21df7f5c78e0895b8c7b662a452212d417a`.
Khôngjobnền, khôngwinner/accountpolicy mới;trở về[plan](MECHANISM-FIRST-EXECUTION-20261109.md).
