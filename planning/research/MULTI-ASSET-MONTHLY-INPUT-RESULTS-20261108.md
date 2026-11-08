# Đã có bộ quan sát tháng chung, chưa có portfolio PnL

Thực hiện [protocol](MULTI-ASSET-MONTHLY-INPUT-PROTOCOL-20261108.md), commit
7d921a5 trước chuẩn bị giá; helper/tests c6c1bef. Không sửa raw/caches hoặc
sourcebindings cũ, không network/account/model/broker/holdout calls.

| Market | Giá tín hiệu có/144 | Giá tham chiếu rebalance có/144 | Side |
|---|---:|---:|---|
|EURUSD|144|144|ObservedBidAsk cùng tick; UTCmillisecond/sequence|
|Gold|144|144|ObservedBidM1;Asknull/unknown,không syntheticAsk|
|US500|140|143|Retainedsource-listedM1BidAsk; không actualtickfill|

**864records**,859có Bid và5missing. Giai đoạn2018–2024 đủ504/504records
theo clock đã khóa; không chọn giai đoạn theo PnL. MissingUS500:rebalance
06/2013 và signalclose09/2013,12/2014,12/2015,10/2016. Không fill/zero/drop.

Mỗi record có instrument/month/role/target/units, status/sides, source/hash,
known-at hoặc M1quote timestampinterval, exposure và authorityfalse. Signal
cutoff theo lastNYSEsessionclose; rebalanceobservation10:00NY của firstsession.
Không lấy giá futureexecution làm quyết định đầu tháng hoặc coiM1open là
actualtimestamp khớp tick. GoldAsk cần economicprotocol riêng nếu dùng về sau.

## Kiểm chứng và thời gian

-5focusedtests đạt:DST/earlyclose,laststrictbefore/firstafter,stale/future,
  missing/census/authority và GoldAskunknown. Tickquote có timestamp quote
  riêng; việc xác định **last quote before cutoff** known-at ở cutoff.
- Nativecurrent boundhourcache2013–2022 giữ nguyên rawSHA/producer/runtime/
  payload/model/count guards. FX2023/2024 dùng explicitrawsparsemode vì
  producer cũ khác current; không sửa binding hoặc ép nativeguard pass.
- Separate review **1.430selectedprices**:576FXcachedquote prices,288GoldCSV,
  566US500rawdelta prices; kiểm5missingUS500 từ canonicalview,864rowcensus,
  clock/units/sides/known-at.4mutations reject:inventGoldAsk,futuretick,
  missingrecord,falseauthority. Cùngagent/provider, khác codepaths.
- Historical2023/24H1caches chỉ làm read-onlypriceoracle để so raw-sparse
  extraction mới. Không executeoldcode hoặc gọi chúng current-compatible.

| Phase | Wallseconds |
|---|---:|
|FX10compatiblecacheyears,bao gồm rawhash|102,009|
|FX2023/24sparse raw extraction|39,528|
|Gold5.399.878M1rows/sparse selectedprices|5,794|
|US500pairedM1join/seals|16,890|
|Producer toàn lượt|154,861;CPU88,109|
|Separate source/contract review|15,442|

Các phase timers có overhead/clock granularity và không dùng làm speedup
so một workload khác; không cộng làm exacttotal nếu khác scopes. Raw bytes
được kiểm đầy đủ trong sourcepass/nativecacheloader. Bộ quan sát sealed nhỏ
giúp lượt sau tính features mà không parse rawticks lại; provenance vẫn giữ.
Chưa tạo vectorDB, service, data migration hoặc reusableasofhelper không có gain.

Private `execution-v1/multiasset-monthly-input-v1`:config/manifest/source-snapshot,
permarket/peryear records/proofs,records/quality/result/events/progress/source-review.
Worker10092/exec90781 và reviewexec88065 đã terminal0. RecordsSHA
`eb817f8bdd0cace9fa912cfd2c8b1d455367ce3d31d19300ac048b70f09ada5a`;
resultSHA`887ae1dc217c9f0afef3fce2e53a6b2e536cc08f684e7c565262b85613fa28aa`.

**Bước tiếp:** freeze exactmixedmomentum/volweights/continuousproxyNAV,
cost/fundingcounterfactual và missing/endmark policies trước outcomes.
Datareview không là strategy admission, statisticaledge, intrabarprop/DD,
actualGoldAsk hoặc authority. C1/C2goal chưa đạt, không rerun preparation
không đổi để benchmark hoặc chọn lại clocks theo kết quả.
