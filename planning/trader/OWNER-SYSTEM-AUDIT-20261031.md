# Trader — đồng bộ UI và tốc độ cho một owner

01/11/2026 · WORK: ACTIVE/PARTIAL · REVIEW: REVIEWED-PARTIAL · DOC: FULL

Owner đã giao tiếp tục audit cùng Studio sau lần tạm dừng. Đọc
[checkpoint hiện hành](../../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/CHECKPOINT.md)
và [review tổng hợp](../../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/OWNER-REVIEW-20261101.md)
trước khi tiếp tục; source/fixture theo từng lát chưa là owner-runtime acceptance.

Phụ lục execution của [Product Plan](PRODUCT-COMPLETION-PLAN.md), theo yêu cầu
owner ngày 31/10. Không thay ledger/STATE hay nghiệm thu U/Y/W lịch sử.
Receipt hiện hành: [owner-system-audit](../../projects/trader/foundation_v2/evidence/owner-system-audit-20261031/).

## Mục tiêu và thứ tự

Ưu tiên phản hồi nhanh, dễ hiểu và nhất quán cho **một người dùng**. Giữ tenant
isolation, tính đúng của tiền/thời gian, revision và quyền; không thêm hạ tầng
1.000 người dùng. Giữ React/Rust/PostgreSQL và hướng FX-aligned hiện hành.

1. Khóa inventory/source/runtime và đối chiếu PLAN, giữ nguyên WIP/dữ liệu.
2. Sửa chuẩn dùng chung và UI reference trước để các trang cùng theo một chuẩn.
3. Sửa workflow/lớp nổi/copy và các điểm chờ hoặc lặp công việc đã tìm được.
4. Kiểm chứng tích hợp các trang, lớp ẩn và các trạng thái; bổ sung lỗi vào cùng
   receipt. Dọn code/caller/tài liệu đúng phạm vi sau mỗi lát.
5. Chuẩn bị candidate, rollback và báo cáo giản dị. Rollout/migration nếu cần
   được trình bằng kết quả cụ thể sau khi candidate đã được kiểm chứng.

Khi audit bắt đầu, AI autonomy tạm dừng; sau khi audit pause, owner đã tiếp các
lát AI. Trạng thái AI do §6 của [brief hiện có](../research/AUTONOMOUS-TRADING-SYSTEM-BRIEF.md) giữ.

## Baseline và phân công

- Source canonical: `projects/trader/foundation_v2`, HEAD ban đầu `884d04f2`;
  product tree sạch trước khi bắt đầu. Root Product Plan có WIP Rust-native
  extension từ trước; VI Dubber và `projects/evidence` nằm ngoài diff được stage.
- Kiểm listener đầu phiên: không có 5180/8010; không suy tab trình duyệt đang mở
  thành runtime hoạt động. Baseline build riêng trên E:, preview 5217; candidate
  dự kiến 5218, nhưng sau đó 5218 được dùng cho preview AI Research/Paperclip.
  Kiểm listener và chọn cổng trống trước candidate. Root sở hữu process đã mở,
  đóng đúng process sau QA.
- Root giữ plan/tích hợp/QA. Lanes: foundations/reference; route/overlay/workflow;
  frontend loading; API/DB; PLAN/cleanup. Ownership file được giao riêng,
  review trước tích hợp, không agent tự sửa acceptance ledger.

## Phạm vi và acceptance

| ID | Đầu ra cần có | Điều kiện khép |
|---|---|---|
| O1 | Inventory route và lớp nổi | Khóa danh sách theo candidate; baseline có20 sidebar destinations, Studio hiện có19. Deep links riêng; số file owner lớp nổi chỉ là inventory source, không phải số luồng đã test |
| O2 | Bảng PLAN → source/evidence | 26 Y requirements, 2 deferred; phân biệt source/fixture/runtime/gate, không dùng 37 task lịch sử làm % sản phẩm |
| O3 | Kích thước/spacing/alignment/icon | Reference đọc giá trị hiệu lực, contract khớp consumer, screenshot desktop/mobile |
| O4 | Màu/trạng thái/motion | Normal/hover/selected/selected+hover/focus/disabled; light/dark, giảm chuyển động, checkbox portal |
| O5 | Dialog/popup/tooltip/notification | Dùng primitive đúng layer, Escape/focus/async/error, không đường bấm cụt |
| O6 | VI/EN và workflow | Copy đúng ngữ cảnh, kiểm cả locale, loading/error không giả thành empty/0 |
| O7 | Frontend performance | Đo cùng fixture; bỏ waterfall/lặp công việc có căn cứ; tách tải code/API/render |
| O8 | API/DB performance và correctness | Inventory native/adapter, query/index/paging/cache; tối ưu có parity/operation-count, không đổi financial semantics |
| O9 | Grid/paging/lazy loading | Sort/filter/count/alignment/overflow, state theo scope; kiểm route có bảng thật |
| O10 | Kiểm chứng tích hợp | Matrix route + overlay có kết quả/giới hạn rõ; source/build/fixture/actual local không trộn |
| O11 | Cleanup và handoff | Manifest keep/merge/remove/defer, không mất WIP/negative evidence; routing/resume rõ |
| O12 | Candidate và rollout readiness | Diff review, build, receipt, rollback; active rollout/broker/migration giữ gate riêng |

Đây là danh sách **12 đầu ra của đợt audit**, không phải trọng số chất lượng hay
ước lượng 12 phần bằng effort. Trạng thái chi tiết và findings do receipt giữ;
plan giữ scope/acceptance. Chỉ báo % khi có danh sách mẫu số dẫn tới được.

## Cách báo tiến độ

- Coverage khảo sát: `N/M` route sidebar theo census của candidate; browser coverage
  có mẫu số riêng theo route × theme × locale × viewport và surface đã liệt kê.
- Findings: `K/L` lỗi đã sửa và có evidence; giữ open/untested/deferred cạnh nhau.
- Product: map từng Y01–Y26 và bốn hành trình A–D; chưa có proof không được tự
  ghi đạt. Hiện các mảng U1–U7 partial, U8 demo có scope/live mở, U9 mở.
- Không gán 80% cảm quan của owner thành acceptance; không biến 37/37 accepted
  tasks r389 thành 100% product.

## Quyết định reuse và Jev

Reuse Lucide/TestingIcon/ChartIcon, compact palette/profile, FxSelect,
LegacyModal/LegacyPopover, shared grid/pagination/selection/editor/query owner.
Không thêm bộ icon/framework mới khi incumbent đã có. Màu mới phải có vai trò
và cặp tương phản; sửa owner/token trước khi thêm override CSS.

Jev dành cho phán đoán ngôn ngữ có ích (ví dụ tìm ghi chú/gợi ý nhãn), cần bộ
đánh giá/chi phí/quyền riêng. Không cần gọi model để căn lề, đổi trang, lọc ngày,
tính số tiền hay mở popup. Tài liệu TypeSafe hiện hành xác định model nhận state
và trả typed judgments; code giữ workflow. Đợt này không thêm provider call.
Nguồn đã đọc: [TypeSafe docs](https://docs.typesafe.ai/llms.txt).

## Cleanup và quyền

Ưu tiên sửa routing cũ, gom primitive có nhiều consumer thật và xóa code chết
được chứng minh. Không xóa hàng loạt plans/evidence/dist/runtime chỉ vì nhiều.
Manifest ban đầu nằm trong `plans-cleanup-audit.md`: root `projects/evidence`
có file khác/thiếu ở canonical, cần giữ; checkout cũ có runtime/WIP phải giữ.
Mọi move/delete cần exact path, provenance, writer/caller và rollback.

Không mở broker/live, holdout, paid provider/OAuth, migration, public release
hoặc restart runtime đang hoạt động từ task audit. Candidate dùng fixture và
chặn network ngoài/ghi thật; fixture writes chỉ được phép trong DB tạm có owner.

## Resume

Đọc receipt `CHECKPOINT.md` khi có, rồi finding đang mở và files ownership.
Không rerun phần đã kiểm nếu source/scope không đổi. Chưa đóng mọi O1–O12 thì
không gọi đợt audit hoặc toàn sản phẩm hoàn thành.
