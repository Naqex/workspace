# Trader legacy archive checkpoint — 29/10/2026

## Phạm vi

Đây là checkpoint cho đợt dọn dẹp theo thứ tự đã thống nhất: giữ
`foundation_v2` làm source hiện hành, chuẩn hóa consumer path, rồi archive phần
legacy không còn dùng. Không đụng Advanced Charts, database, runtime artifacts,
`foundation_v2/evidence/` hoặc các WIP ngoài phạm vi.

## Đã làm

1. Đối chiếu source và consumer của semantic modules trước khi di chuyển.
2. Đưa các module còn được `foundation_v2` sử dụng vào
   `projects/trader/foundation_v2/trading_workspace_v2/semantics/` và đổi import
   sang namespace ổn định.
3. Archive Flask/phase implementation, root launchers, root tests, verifier cũ
   và tài liệu Flask vào `projects/trader/archive/legacy/`.
4. Ghi manifest và hướng dẫn rollback tại
   `projects/trader/archive/legacy/{README.md,MANIFEST.md}`.
5. Đổi các lệnh/link vận hành còn trỏ tên cũ sang `projects/trader` và
   `planning/trader`. Receipt và evidence lịch sử giữ nguyên path đã ghi tại
   thời điểm chạy để bảo toàn provenance.

## Kiểm chứng

- `foundation_v2/tests/test_contracts.py`: pass.
- `foundation_v2/tests/test_u6_analytics_read_model.py`: pass.
- `foundation_v2/tests/test_risk_promotion_contract.py`: 11 pass.
- `tests/test_release_workflow.py`: 13 pass.
- `scripts/check_paths.py`: 0 failure.
- `scripts/release.py check`: pass, version `0.1.0-alpha.1`.
- `git diff --check`: pass.

Các test Python của `foundation_v2` được chạy trong environment do `uv` quản lý,
với `PYTHONPATH` trỏ tới `foundation_v2`.

## Chưa đóng

Archive này không tự đóng các gate sản phẩm: FH/state reconciliation, U1/U3/U4/U9
UI acceptance, U2 real provider/import, U5 research/OOS, U6 path-dependent
analytics/Prop inputs, U7 real AI provider/UI và U8 demo broker/live. Không có
broker reconnect, API restart, deploy, packaging hay public application release
trong checkpoint này.

## Rollback

Đợt archive là các rename có thể đảo ngược bằng `git revert` commit archive hoặc
di chuyển lại từng nhóm theo manifest. Không xóa dữ liệu runtime hay lịch sử Git.
