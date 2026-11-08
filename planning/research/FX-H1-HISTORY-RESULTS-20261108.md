# Hai thị trường mới: kiểm được nguồn, còn gaps phải giữ rõ

Thực hiện [protocol và recovery](FX-H1-HISTORY-PROTOCOL-20261108.md),khôngPnL.
**Giá/biến đổi của373.652sourcebars đã kiểm; không chứng nhận full joint-price
history.** GBPUSD/AUDUSD2010–24 có60year/sidebooks,719/720rawmonthbuffers.
AskAUDUSDJan2013chưa lấyđược;30pairedhoursAUDUSD2010bịcrossedOpen/Close.
Khôngfillprice,không gọimissing/crossed làactualspreadhợplệ hoặcmarketclosed.

## Kết quả và contract

| Phần | Đã kiểm / giới hạn |
|---|---|
|Raw/exports|719rawmonthSHA và60seals/config/protocol/producer/runtime pins|
|Sourcebars|373.652,đủnative→rawFractiontimestamps/OHLC/volume-transform;1.868.260checks|
|Decoderpadding|148.096nativecarriedhourrows bịloại bằngraw-listedtimestamps;khônglọcvolume0|
|Explicitvolume0|40rows giữ nguyên,sourcemembership độc lập volume|
|Pairedhours|186.560common timestamps;không mặcđịnhjointticks|
|Crossedpairquality|30hourschỉAUDUSD2010:13Open/17Closeflags;1targetexitOpenaffected,0entryOpen|
|Availability|AUDUSD2013haiendpointH1hợplệ237/261weekdays;AUDUSD2010usableOpen260/261;khôngdroprows|
|Mutations|5reject:price,time,census,volume,falseOOS/authority|
|Financialoutcomes|0signals/returns/weights/correlation/strategy/broker/holdoutcalls|

UnitsUSD_per_GBP/USD_per_AUD,tickgrid0,00001,UTC/H1startms. High/Low/Close
knownafter+1h;Open tronghourinterval,khôngactualfirstquote/jointBidAsk.
Volume **nativeaggregate round4 trongmillions**,khôngrawfullprecision hoặc
signeddealerorderflow.2.052rows bịround đãđối chiếu đúng biếnđổi,rawunrounded
giữbấtbiến. [Volume note](FX-H1-VOLUME-INTERPRETATION-20261108.md) giữvídụ/
installedfunctiontrace,khôngnới tolerance. [Pair note](FX-H1-PAIR-QUALITY-20261108.md)
giữ30timestamps/fieldflags;nguyênnhânrawasynchrony/revision chưa xácminh.

Fullhistoryadmission=`false`:per-sideprices được kiểm không làmpairedroles,
nguồnchưacó hoặcactualexecution tự đạt. GiáOpen củasourcehourskhôngbịcross
cóthểphụcvụ một **registeredendpointcomponent** với knownmissing/crossed
states/denominator đầyđủ;không dùngpartialdatađểtựqualifiedbot. Futureexit
bad khôngđượcdùngđểlọcentryhindsight. Mọi nativepromotion cầnsourcegap/path
review riêng. Sameprovider/agent,khácimplementation,chưaindependentaudit.

## Sự cố, recovery và hậu kiểm

| Attempt / việc | Kết quả |
|---|---|
|v1/sourcecallerdate|Dừng4,306s,0sealedbooks;nativevalidator mutateddates;fixcopy+regression|
|v2/sourcefetch|Dừng185,411s,15sealedbooks;AUDAskJan2013timeout3lần|
|v3/sourceviews|Hoàn tất214,894s/5,062sCPU;reuse15books,knownURLkhôngfetchlại;45views mới|
|Reviewsourcevolume|Guardchặn mấtprecision;kiểm`Number(toFixed(4))`,ghiinterpretation,khôngrerundownload|
|Reviewpairedquality|GuardchặnnegativeOpen/Close;giữflags/inconclusive,khôngsửagiáđểpass|
|Finalreview|27,117s cho1.868.260checks,quality/unknowns/seals/mutations|

V315booksreused bằngbytecopy/hash/oldmanifest/proofs/originalhelper snapshot,
không nhậnhelpermớiđãproduceoldoutputs. Oldattempts/protocolsnapshots giữ
nguyên;sourcehelperfixes`599db5e`/`23d6a5a` có17Nodechecksđạttrongaffected
H1/M1recoverypaths. Noauth/WAF/429bypass/hiddenretry hoặcnewprovider/account.
Khôngclaim arbitraryCLIresume:đây làrecovery rõ15books vớireceiptidentity,
không interruptionequivalence của mọiworker.

Network chờ chiếmsourcephase;27sreview hữuhạn,khôngcầnGPU/Rust. Chuẩn bịH1
kháctickexecution,khôngreport speedupcùngđộđúng. Khôngthêmdatabase/RAG/MCP/
UI/skill hoặc xóaevidence. Rawcache giữprivate,khôngupload/datalicenseclaim.
PIDs22072/9220/17072 vàreviewhandle27799đãterminal;khôngworker cònchạy.

Private`execution-v1/fx-h1-history-v1/v2/v3` dưới campaignroot giữfailures/
config/manifest/source-snapshots/perbook/sideexports/seals/sourceproofs/events/
progress;v3giữquality,raw-source-bindings,crossed-pair-quality,review vàreview
failures. Rawpathcampaign`source-hour-cache-v1`. Không đưa chúngvàoGit.
V3resultSHA`19f85521a4f29d7b4e683ef33398deb7e2336b6df8ed658f8562ba27c490ec43`;
reviewerSHA`7dded79cdf403de39f4d5944dc3deffbfccb1f64362ee03673244c2f56a422a3`.

## Bước tiếp

Freeze price/costcomponentriêng choGBPUSD/AUDUSD,giữsameclock/side cơchế
trướcfix,không SLgrid/costrescue củaR056. DùngonlysourceOpenqua fieldguard,
giữmọiweekdays/missing/crossed,cost/retention trướcPnL;chưaportfolioaccount.
Nếu giữđược mới xétriskwrapper/sharedbudget/tick/prop/selection/unseen/
prospectivereconciliation. Catalogue chưa tăng chỉvì códata mới;C1/C2active.
