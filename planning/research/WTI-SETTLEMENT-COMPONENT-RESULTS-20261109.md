# R083 WTI settlement: đầy đủ cả hai năm, vẫn không qua phí stress

[Protocol](WTI-SETTLEMENT-COMPONENT-PROTOCOL-20261109.md), commit`cbb63fa`
trước đọc slot mới. Relatedtrial sauR082, không independentdiscovery hoặc
cleanOOS. Own slot14:01→14:29NY dựa trên [normalCMEsettlement14:28–14:30](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-4867.html);
không VWAP/futuresexecution/expirycalendar hoặc mappedCFDbrokercontract.

## Kết quả đủ nguồn cho slot đã đăng ký

Tất cả88days cóđủ31feature+29holdingM1/sourcebothsides; **strictrole và
endpoint-only sensitivity cho kết quả giống nhau**. Không drop ngày hoặc
fillmissingđể đạt; không thayR082unknowns. Đơn vị1researchbarrel, khônglot/
account10k hoặc %return/passprobability;44trades/year, noSL/equitysimulation.

| Năm | Đủrole / dựkiến | Grossmidmove USD/unit | Spread drag | Net chuẩn | Net cao |
|---|---:|---:|---:|---:|---:|
|2019|44/44|+0,5375|2,4355|−4,0980|−6,2980|
|2022|44/44|+5,3455|2,2425|+0,9030|−1,2970|

Net chuẩn/cao đã trừ side-spread và extraRTfees0,05/0,10USD/unit/trade;
không actualbrokerfees. Năm2019grosskhông bùspread;2022dươngchuẩn nhưngkhông
qua frozenstressgate. Không đổi fee/threshold/holdingtime để cứu bản này.

**Quyết định:** gác exactR083, cả strictpriority và endpointresearchinterest
false. Không loại mọi oilmomentum, không chứng minh marketkhôngcóedge.
Calendar làretrospectivelabel, actual/PIT/brokerfill/SL/prop/OOS/forward chưa
đủ; ngay cả outcomesdương cũngchưaC1/C2. Không promote controlthắng hoặc
bắt đầu clockgrid khác trên cùng predictor.

## Correctness, tái sử dụng và timing

| Lát | Bằng chứng / giới hạn |
|---|---|
| Parent/source | Rebind176raw/native vàaccepted1.162.180fieldreview/day-grid proof; no repeated network/fullreview hoặcR082economics |
| Newslot | Đủ88dates/704endpointOpenfields, exactsymbol/day/grid,31+29roles vàwinter/summerclock; firstquote-in-minute sideproxy chưa jointtick |
| Financial | 40books, mỗiview880directcashcases;1.760checks cólặp views, không176independenttrades. RebuiltFraction totals/gross-spread-extra/counts/nullstate/strictN/A |
| Fixtures | 17checks gồmparentBUY/SELL/flat/sign/DST/futurecausality vànewrole/internalgap/endpointmissing/crossedendpoint/oldslotreject |
| Mutations | Net/cost/count/primaryview/authority/signal/sourcebinding bịexecutablevalidator từchối |
| Source-binding | 0,500s wall; snapshot đúngfrozenhash choLF/CRLF, currenthashriêng; không sửaoriginalpins/raw |
| Newrole sampling | 5,296s wall |
| Compute+initialfinancialreview | 0,169s wall |
| Toàn consumer | 6,330s wall /5,641s CPU, gồmfinalmutations/serialization; khôngresearch/Git |

Chạy consumer dưới network-denied socketguard, **0newsource/broker/modelcalls**,
noown2025+/holdout. Đây là newworkload/reuse, không A/Bspeedup cùngsemantics
soR082102s. Không engine/GPU/Rust/framework đổi; chưa bottleneck cầnprofile.
Cùngagent/feed, không independentmodel/human/fillcertificate. Sourcequality
vàfuturequoteavailability chỉ diagnostic, khôngcausalentryfilter.

Private`execution-v1/wti-settlement-component-v1/` trongcampaignbase giữ
manifest/resolvedbindings/snapshots/rows/source-scope-review/results/progress/
events. Phase`completed_reviewed`, khôngjobnền. RowsSHA
`fd17f447b1585bb9fcaf44210fa54a5c238c7a9caaff9f32dbdea423ba0e180d`;
reviewerSHA`ce7a215479f01e04a5783c31cf024196614771d9bd2397bcc6635b012eb373ec`.

Catalogue thêmR083relatedcomponent,83records/58policy-modelversions/25native/
9controls. Khôngcandidate/accountpolicy mới. Bước tiếp khác marketflow:
[Tokyo-fix methodadmission](TOKYO-FIX-METHOD-ADMISSION-20261109.md) xétJPY,
khôngretuneEURUSDnegative hoặc lấybankinventoryprofit thànhretailalpha.
