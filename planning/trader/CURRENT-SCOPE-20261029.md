# Naqex Trader current execution scope — 29/10/2026

## Quyết định phạm vi

Đây là scope điều hành hiện tại cho Naqex Trader. Nó áp dụng cho code và
evidence mới ở `projects/trader/foundation_v2`, nơi các AI agents đã hoàn thiện
UI theo hướng tham chiếu FX Replay và các contract/runtime hiện hành.

Các plan/checkpoint cũ vẫn giữ để truy vết lịch sử, nhưng không dùng các yêu cầu
đã lỗi thời làm điều kiện chặn cho slice hiện tại.

## Tạm hoãn khỏi đợt này

| Hạng mục cũ | Cách xử lý hiện tại |
|---|---|
| Figma Make round-trip / Y26 / U1d | Deferred. Không mở Figma, không upload context, không yêu cầu Make artifact. |
| Miro board / Y12 | Deferred. Không cập nhật board hoặc coi board là acceptance source. |
| Điều kiện Figma/Miro trong U9 | Bỏ khỏi critical path hiện tại; U9 chỉ xét integrated code, QA, cleanup, rollback và evidence thực tế. |

Việc tạm hoãn này không đánh dấu Y12/Y26 là đạt; chỉ loại chúng khỏi phạm vi
đang thực thi. Có thể mở lại bằng một quyết định phạm vi mới.

## Gate đang dùng

| Nhóm | Phạm vi hiện tại | Trạng thái từ audit mới |
|---|---|---|
| UI | FX-aligned shell, design system, chart, live/practice/analytics và các hành trình hiện có | U1/U3/U4: partial; U9: chưa đóng |
| Data | QDM/Dukascopy isolated import, contracts, catalog, scope guard | U2: partial |
| Research | Engine, deterministic reconciliation, OOS/stress software slices | U5: partial |
| Analytics/Prop | Read model, metrics và live presentation | U6: partial |
| AI | Offline/provider-neutral boundary, context hash, no-broker guard | U7: partial |
| Demo/live | Demo lifecycle receipt theo account đã được cấp quyền; live tách riêng | U8 demo slice: pass có giới hạn; U8 live: mở |

Một slice chỉ được ghi `scoped accepted` khi receipt nêu đúng source/build,
phạm vi và giới hạn. Không chuyển slice thành full product acceptance.

## Nguyên tắc tiếp tục

1. Ưu tiên sửa và kiểm chứng code/evidence hiện hành trong `foundation_v2`.
2. Dùng browser/runtime QA theo các hành trình thực tế của Naqex Trader; không
   quay lại preview legacy để quyết định UI.
3. Không tự mở provider trả phí, holdout, broker/live, deploy hoặc packaging.
4. Khi muốn đưa Figma/Miro trở lại, tạo một scope amendment mới thay vì sửa
   receipt lịch sử.
