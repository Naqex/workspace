# Thực thi sau đúc kết: cơ chế → điều kiện → economics → challenge

Owner giao tổng hợp và thực thi09/11, sau [giải thích mục9–11](OWNER-EVIDENCE-REPORT-20261108.md).
Đây là scope thực thi lượt mới thuộc [campaignv2](CHALLENGE-CANDIDATE-CAMPAIGN-V2-20261108.md),
không reset lịch sử hay tạo task authority mới. Goal UI hiện paused; lời giao
mới cho phép công việc này tiếp tục, không giả tool đã đổi Goal thành active.

## Công việc và acceptance

| Thứ tự | Công việc | Điều kiện hoàn thành / trạng thái khởi tạo |
|---|---|---|
|1|Gom toàn catalogue theo nguồn lợi nhuận, giữ parent/controls/variants|Đủ80IDs, không thiếu/trùng; bảng cơ chế không tự chứng minh độc lập thống kê|
|2|Cập nhật trạng thái, data/fees và exposure hiện có|R080 đúngreviewednegative/unknown; known/raw/derived/costunits/version và consumedyears rõ; không rawmigration|
|3|Kiểm một conditional hypothesis có cơ sở, không clock/thresholdgrid|Protocol trướcoutcomes, predictor biết trướcentry, so parent/null/opposite, giữnonselected vàunknown; raw/sốhọc reviewer riêng|
|4|Chuẩn bị hướng khác về cơ chế|Oil/EIA: kiểm nativeUSO/WTImetadata +primarymethod/calendar; fixture nguồn trướchistory/economics; không transferETF→CFD ngầm|
|5|Review survivor và dependency nếu có|Trước ghépportfolio cần alignednetreturns/jointloss/exposure; chưa cósurvivor không tính correlation để tìm cặp đẹp|
|6|Prop qualification|Chỉ economicsurvivor mới đăng ký đúngprogram/risk/equity/timefit3/6/12m, costs/ticks/OOS/prospective/ownerhandover; chưa tựmua hoặc gửi lệnh|
|7|Hậu kiểm và lưu|Phase/status/pins/failures/negative/decision; chỉ sửa bottleneck cóevidence; existing skills đủ, chưa cần framework/RAG/UI mới|

Không đổi verdict cũ hoặc hạ gate để cówinner; dataunknown khác economicnegative
và khác prioritygatefail. Thresholds của triage là heuristic đã đăng ký, không
luật quỹ. Không kỳ vọng cứ10lệnh phảilời, không chọn điểm dừnghồi tố.

## Bản đồ cơ chế — toàn80hồ sơ

Mỗi ID dưới có một bucket chính để census; có quan hệ chéo, không là sốedge.
Manual classification đọc title/family/parent, không model tựsuy profitability.

| Cơ chế giả thuyết / vai trò | IDs | Input hoặc giới hạn quyết định |
|---|---|---|
|Trend/pricebreak/continuation|R001,R002,R004,R005,R007,R009,R010,R015,R016,R017,R018,R019,R033,R042,R043,R045,R048,R061,R065,R066|Đã nhiềuversions; indicator khác có thể cùngbet, chưaưu tiên grid|
|Reversion/level/overnightgap|R003,R006,R008,R011,R012,R013,R014,R024,R044,R046,R049,R050,R052,R063,R070,R072,R074,R075|Futureexit không chọnentry; chưa loại cảfamily từexactnegatives|
|Flow/calendar/benchmark/closing/liquidity|R020,R021,R022,R023,R025,R026,R037,R047,R051,R054,R055,R056,R057,R058,R059,R060,R064,R076,R077,R078,R079,R080|Giờ/priceproxy chưaactualflow; inventory khácuncertainty nhưngcùngexposure có thể cao|
|Scheduledmacro/news information|R027,R028,R062|NewsPIT/calendar kháctimestamp củabáocáo; EIA khác preFOMC|
|Relativevalue|R034,R035,R067|Formation/data/universe/basis/twolegcost; chưa cóportfolio chứngminh|
|Carry/value/mixedpremia|R029,R030,R031,R032|Lợi tức underlying khácCFDswap, longhorizon/tailrisk có thểkhônghợpprop|
|MLestimator, chưa mộtcơchếkinhtế riêng|R038,R039,R068|Features/labels phảiđúngtrade; model khôngtựtạoedge|
|Controls/riskcomponent|R036,R040,R041,R053,R069,R071,R073|Khôngđếmcontrol/voltargetthànhindependentalpha|

## Vì sao chọn bước3 trước?

[NYFed917paper](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
và [tóm tắt chính thức](https://libertystreeteconomics.newyorkfed.org/2021/05/the-overnight-drift-in-us-equity-returns/)
được đọc09/11: inventorypressure lúcđóngcửa có liên hệ overnightreversal,
khác uncertaintyresolution củaR080. Đây là lý do kiểmcondition causal, không
chọn filter do thấy selectedPnL đẹp. Fullpaper cũng lưu ý pattern không dễ
kiếm lời sauBidAsk; không lấy headlineannualreturn làm kỳ vọngbot.

Chọn [R081protocol](US500-INVENTORY-CONDITION-PROTOCOL-20261109.md): giữ nguyên
window/cost củaR080, mộtclosingreturn sign proxy cốđịnh, không đổi sang2–3NY
hoặc thửnhiềuthresholds. Đây **là conditionalvariant córelatedparent**, không
đếm là cơhội độc lập mới chỉ vìđổi explanation. Signedvolume/dealerinventory
chưa có: protocol phảigiữ proxy gap. Nếu khôngadmitted/negative thìgác exact,
không tựthêm filter. Dùngsource/reviewedparent đãcó đểkhôngđợi thêmhistory.

## Hướng oil/EIA đang được chuẩn bị

Nativepinned dukascopy-node1.51.1 có `usoususd`=USO.US/USD và
`lightcmdusd`=LIGHT.CMD/USD; metadataavailability không chứng minh ngày nào có
quotehoặcUSOtradedshares. [USCFdisclosure](https://www.uscfinvestments.com/disclosures)
và [CMEcomparison](https://www.cmegroup.com/education/lessons/wti-futures-versus-etfs)
cho thấyETF/futures exposure/roll khác nhau; không assumeWtiCFD equivalence.
Existing [method](EU-OPEN-AND-OIL-METHOD-20261109.md) giữ acceptedUSOpaper.
[EIAarchive](https://www.eia.gov/petroleum/supply/weekly/archive/) córelease dates;
June2022haiweekreports cùng29/06 phảimerge thành1event, không doubletrade.
Eventtime/sourcefixture/targetfees cònphảiadmit trước economicprotocol; không
bulkfetch với lýdo thưviện liệtkêsymbol. Xếp sauR081boundedrun, khôngmởhai
numericwriterslêncùngjob. Không paidprovider/account/OAuth/globalconfig mới.
