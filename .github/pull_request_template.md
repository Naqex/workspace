## Thay đổi và lý do

Link issue bằng `Naqex/workspace#…` khi có. Dùng `Refs` nếu acceptance còn chờ;
chỉ dùng `Fixes` khi merge đủ điều kiện đóng issue.

## Kiểm chứng

Ghi lệnh/kết quả, commit đã kiểm tra và phạm vi chưa kiểm.

## Tương thích và vận hành

Breaking change, migration, license hoặc rollout/rollback nếu có.

## Agent

Nếu có AI: role (triển khai/review), tool, requested model ID và nguồn danh tính.
Không biết model thì ghi `unknown`. Chỉ ghi reported model khi runtime xác nhận.
Reviewer ghi SHA đã xét; review cũ không tự áp dụng cho commit mới.
