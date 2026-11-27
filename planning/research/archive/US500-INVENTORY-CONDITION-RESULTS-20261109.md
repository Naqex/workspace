# R081: chỉ mua sau phiên đóng cửa giảm vẫn chưa tạo edge

[Protocol](US500-INVENTORY-CONDITION-PROTOCOL-20261109.md) `c604e20`, code/tests
`0f8b12a` trước outcomes. Hai năm đã run/reviewed, **không retained**. Giữ
[parentR080](US500-EU-OPEN-COMPONENT-RESULTS-20261109.md) negative/unknown.
Đây là một conditionalvariant liên quanparent, không independentedge.

## Kết quả dễ hiểu

Chỉmua trongwindow cũ nếu last30minmidreturn củaexpectedpreviouscashsession
âm; không đổi clock/cost/threshold hoặc tựnhận signedflow. Một researchunit=
1USD/indexpoint, chưa lot/account/risk0,25%. Tổng dưới chỉknownsubset.

| Năm | Eligiblepredictors / hợp lệ | Chọn giao dịch | Resolved / unknown | Chuẩn USD/unit | Cao USD/unit |
|---|---:|---:|---:|---:|---:|
|2019|245/245|113|90/23|−97,61|−187,61|
|2022|248/248|129|128/1|−279,44|−407,44|

Predictors đủ ởmọieligiblepriorregularsession; firstsessionoutofscope2,
currenthalfday4/previoushalfday4 knownabstain. 251nonnegative→noexposure,
242negative→planned, khôngchọn bằngfutureexit hoặcparentPnL.2019selected
endpointcoverage79,65%chưađạt98%;2022=99,22%đạt nhưngstressnetâm.
Không gọi2019fullannualnegative, không gán24unknowns thành0 hoặcxóaplanned.

### Lỗ do tín hiệu hay phí?

Phần có đầy đủquotes, USD/unit, giữdigits đểreconcile; roundingresidual trong
JSON giải thích chênh cents khi cộng nhiều roundedtrade. Midgross chỉdiagnostic,
khônggiákhớp; embeddedspread đãnằm trongBidAskPnL, khôngtrừlần2.

| Cohort | Mid-price movement | Embeddedspread | Slippagechuẩn | Netchuẩn |
|---|---:|---:|---:|---:|
|Parent2019/191known|−17,3665|105,9245|95,50|−218,64|
|Conditional2019/90known|−3,0625|49,6035|45,00|−97,61|
|Parent2022/248known|−127,1715|142,1755|124,00|−393,38|
|Conditional2022/128known|−141,7415|73,7075|64,00|−279,44|

Commission/funding0 làdeclaredintradaycostscenario, khôngactualbrokerproof.
**Giá tựdịchchuyển đãkhông thuận lợi trênknownsubset**, không chỉdo phí. Giảm
sốlệnh cógiảmtiềnphí nhưngchưa đủthànhedge. So totalconditional vớiparent
kháccohort khônglàreturnimprovement hoặcpassrate. Oppositecontrol2022chuẩn
+4,03nhưngstress−123,99; khôngđảoBUY→SELL đểcứu kếtquảhồi tố.

## Kiểm và thời gian

-5focusedtests đạt0,982s:sign/zero/missing/crossed/grid, priorcalendar/
 holiday/weekend/halfday, futureprice/netkhôngchọnentry, sourceimmutable,
 authority/census/knownat vàkhôngdoublecountspread.
-Preflight rawdelta/sign vàFractionwaterfall2fixtures trước actualoutcomes.
-Review actual503rows từ986rawday-sideresponses, calendarlogic/Fraction riêng
 khôngimportselector;mask/unknown/parentexactreuse/summary/decomposition/gate
 khớp.5mutationsselected/predictor/knownat/cost/scopeđều bịchặn.
-Producer4,282s;review4,318s;total8,599s. Fullquarterloader/filter chiếm3,47s
 của prefix, phầncòn reuseparentoutputs. Khôngfetchsource/tickrerun/network/
 model/brokercalls. Khôngphát hiệnbugnumeric mới hoặcbottleneck cầnGPU/Rust.
-Sameagent/methodkhác, khôngsignedorderflow, feed/model/humanaudit độc lập;
 consumed2019/2022, chưaSL/account/equity/prop/OOS/forward. Guard/kiểm phùhợp
 currentconsumer, khôngwhole-systemcertification.

Gác exactR081; khôngthêm magnitude/VIX/day/spreadfilters vàkhôngclockgrid.
Giữ proxy/missing limitations, bước tiếp distincteventmechanism sourceadmission
theo [mechanism plan](MECHANISM-FIRST-EXECUTION-20261109.md).

Private `execution-v1/us500-inventory-condition-v1/` trongcampaignbaseE: giữ
predictors/rows503/summary/config/manifest/snapshots/result/review/events/progress.
Scripts `run-inventory-condition-v1.py`,`review-inventory-condition-v1.py` và
`inventory-condition-preflight-v1.json`. Khôngjob nền phải đợi.
ResultSHA`3152e38f43043450f6d6aa0488a35ed4eeafea694a0b9549f31b5d8acc173bf7`;
reviewSHA`84bc69053e530313ea9c9ce0172ddf2ec995216ad248c28c3b32e763bb94be0e`;
reviewerSHA`621e7f7c153ea040d34b21001fc0c8b535799953b6c4cee5ffc81458626770a3`.
