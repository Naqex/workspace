# Oil/EIA: role-based source admission trước economics

09/11/2026, trước đọc geometry mới/return/PnL. Parent
[oil pilot](OIL-EIA-SOURCE-PILOT-RESULTS-20261109.md) không đạt full-cash98%/
16:00Open gate; giữ nguyên. Đây là revision nguồn/clock **đăng ký mới**, không
sửa frozen protocol, không nhìn outcome để chọn endpoint hoặc gọi source fix
là evidence có edge. Existing raw8URLs/2dates/2assets/2sides được reuse.

## Method delta có primary evidence

[Accepted Wen et al.](https://digital.library.adelaide.edu.au/server/api/core/bitstreams/aee73b81-111e-4bef-9e0e-7b1164f368a1/content)
§2.2 footnote6, PDFpage9: authors chỉ đưa các releases thứ Tư vào EIA group;
không áp cùng clock cho Thursday/Friday. Method cũ chỉ ghi predictor10:30–11
và trade15:30–16; bổ sung exclusion của tác giả, chưa bê nguyên PnL/Sharpe.

Hai archived EIA PDFs2019-01-09/2022-07-13, p2/p42, mô tả selected tables/
highlights quanh10:30 và fullPDF/HTML quanh13h. PDF creationtime không là
publicationtime. [June28announcement](https://www.eia.gov/pressroom/releases/press506.php)
preannounces June29 regular schedule and two dataweeks; chỉ xác nhận một
exception, không chứng minh PITcalendar/actualtimestamp của mọi ngày.

## Fixture mới cố định, không source fetch

Cùng hai ngày winter/summer2019-01-09/2022-07-13, USO/WTI, Bid/Ask. Vì USO
regularsession đóng16:00 không có16:00M1Open, lựa chọn riêng của project là:

- Feature source Opens10:30 và11:00NY; cả31phút inclusive là input role.
  Native Open trong interval[minute,minute+1), nên chỉ quyết định sau11:01;
  không gọi quote timestamp chính xác hoặc lấy futureClose làm entryfilter.
- Hypothetical entry15:31NY, scheduled exit15:59NY; toàn29phút inclusive là
  holding role. Chọn exit trước closingminute để tránh giảquote sau close,
  entry trễ1minute so paper. Đây là **own timing adaptation**, không replication
  ETFclose/auction hoặc execution/edge proof. Chưa dùng direction/returns.
- Rebind raw/seal/full-expansion và roles với clock/grid/paired noncrossed
  Open/Close. Gate: mọi4asset-days có đủ cả60roleminutes và4endpoints; báo
  coverage toàncash390nhưdiagnostic, không dùng whole-day gap ngoài roles để
  làm future tradefilter. Không hạ gate sau outcome; thiếu một role thì
  inconclusive, không tự đổi endpoint/ngày/điền quote. Old98%gate giữ lịch sử.
- Source-only CSV/M1/volume không thể chứng minh exchangeprints, informedflow,
  ETFroll/adjustments hoặc cost/CFDtransfer. Không dùng volume làm predictor.

## Output/review

Private `execution-v1/oil-eia-role-source-v1/` trong campaign root. Một writer,
no output overwrite; source/code/protocol pins/result/review, counter/timing;
reuse8oldrawURLs, **0newmarketrequests**/broker/model/ownholdout calls.
Separate Fraction decode từ raw so native expansions bằng helper hiện có;
role census/endpoint order reviewed separately, synthetic DST/boundary và
missing-role/wrong-scope/raw mutation giữ explicit rejection.

Nếu pass: đủ **đăng ký** lịch sử/price component riêng, chưa tự chạy bulk hoặc
qualification. New history phải chốt advance Wednesday calendar/failure handling,
ET/DST/holiday/earlyclose, ETF vs CFD economics và fees/units trước outcomes.
Chỉ labels nghiên cứu ex-post không được giả thành calendar known-in-advance.
Nếu fail: giữ role geometry và gaps; không retry unchanged pilot hoặc rescue
bằng động chọn giờ. Không candidate count mới ở source-only admission này.
