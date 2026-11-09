# EIA historical clock: normal schedule đã có nguồn, actual/PIT toàn kỳ chưa đủ

09/11/2026, tiếp [date census](EIA-RELEASE-DATE-CENSUS-RESULTS-20261109.md).
Không marketprice/PnL/broker mới ở lượt đọc clock. Web reader báo inaccessible
hai historicalPHP, nhưng urllib HTTPS bình thường trả200, TLS giữ nguyên;
không retry403/WAF hoặc dùng auth. BaHTML và haiPDF được giữ private.

| Nguồn | Điều xác minh được | Không chứng minh |
|---|---|---|
| [WPSR09/01/2019](https://www.eia.gov/petroleum/supply/weekly/archive/2019/2019_01_09/pdf/wpsrall.pdf), p2/42 | Mô tả lịch normalWednesday: selected tables/highlights10:30, fullPDF/HTML13h | Actualserver availability của từng file/lần phát hành |
| [WPSR13/07/2022](https://www.eia.gov/petroleum/supply/weekly/archive/2022/2022_07_13/pdf/wpsrall.pdf), p2/42 | Có cùng mô tả hai lớp lịch, không suy fullreport sẵn10:30 | Actualms của88Wednesday hoặc exceptions103dates |
| [Thông cáo28/06/2022](https://www.eia.gov/pressroom/releases/press506.php) | Văn bản đề ngày trước29/06, thông báo gộp hai dataweeks vào regularscheduledtime ngày hôm sau | Exactpublicationtime, toàn bộadvancecalendar hoặcpre-eventarchivecapture |
| [Wen et al. §2.2/footnote6](https://digital.library.adelaide.edu.au/server/api/core/bitstreams/aee73b81-111e-4bef-9e0e-7b1164f368a1/content) | Paper chỉ dùng Wednesday releases trong EIA subgroup; holiday shifts không dùng cùngclock | Futures/CFD performance hoặc lịch2022 đúng theo toàn bộsample paper |

PDFcreation/modification được đọc để tránh nhầm: Jan2019 tạo11:59/đổi12:10
UTC−05; Jul2022 tạo11:12/đổi11:20UTC−04. Không dùng các metadata này làm lúc
tin ra10:30, không lấy fullPDF hoặc revisedfundamentals làm inputs biết10:30.
ArchivedPDF ghi EST chung; ownwindow dùng America/New_York với DST đăng ký
rõ, chưa certified exacttimezone của mọi actualrelease từ metadataPDF.

**Delta:** từ current-schedule-only/unknown sang documentedhistoricalnormal
schedule + một datedpreannouncement. Các `actual_release_time_et=null` và
PIT/tradingeligibilityfalse trong originalevents vẫn nguyên. Không mark
calendarallpass hoặc fallbackallWednesday thành EIAactual10:30.

Private `execution-v1/eia-clock-primary-fixture-v1/` giữ HTTPmetadata/bytes/
SHA, clocktext hits cópage và review.json. HTMLfetch3requests2,165s; PDFfetch2
requests +textscan toàn62×2pages khoảng6s; không actualOOS/marketnewsdataset.
Không đưa PDFs/paper text/data lênGit; báo cáo chỉ ghi interpretation/locators.

Kế tiếp [WTI diagnostic](WTI-WEDNESDAY-COMPONENT-PROTOCOL-20261109.md) là own
conditionalprice association với retrospectivecohort, chưa causaltradingpolicy.
Muốn C1 vẫn phải xác minh calendar được biết trước, target costs, execution,
SL/risk/prop và OOS/forward; không dùng sourceclockdoc thay những cửa này.
