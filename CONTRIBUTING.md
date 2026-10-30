# Đóng góp và Git workflow

```text
Sản phẩm:  codex/task → PR → CI + review → main/master
Workspace: codex/task → PR docs/pins → CI + review → main
```

Commit có một mục đích rõ, ưu tiên Conventional Commits. Giữ task độc lập trong
PR riêng; không stage WIP, cache, dữ liệu cá nhân hoặc credentials. Không force
push nhánh đã chia sẻ. README/AGENTS của sản phẩm giữ command kiểm tra thực tế.

## CI và branch protection

Issue inbox và metadata agent: [workflow GitHub](tooling/github-workflow/README.md).
Bug cần theo dõi hoặc task qua nhiều phiên dùng issue ở `Naqex/workspace`, ghi rõ
repo sở hữu code. Task nhỏ có thể đi thẳng commit/PR; không tạo issue mỗi commit.

Workspace kiểm tra docs/topology, secret và registry UI; Trader kiểm tra hygiene,
Python contracts, web/browser và Rust. Required CI là gate merge, không là bằng
chứng broker/production acceptance. Các repo khác có workflow theo sản phẩm;
fork giữ workflow upstream, không đồng bộ mù vào mọi repo.

PR mô tả thay đổi chính, lý do, kiểm chứng và migration/rủi ro khi có. Owner có
thể tự merge sau các check bắt buộc; khi có nhiều maintainer thì tăng yêu cầu
review. Không tự bypass gate hoặc tăng timeout để che lỗi.

## Version và release

| Thành phần | Version |
|---|---|
| Workspace | Commit và submodule pins; không có version ứng dụng chung |
| Trader | Một version sản phẩm trong `VERSION`; [release policy](https://github.com/Naqex/trader/blob/main/docs/releases.md) |
| VI Dubber / Quant Lab | Manifest và policy của từng repo |
| Fork | Giữ version/tag upstream và ghi rõ thay đổi local |

Agent có thể chuẩn bị version/changelog/release PR từ phạm vi đã kiểm chứng.
Không tự tăng version ở mọi commit. Trước 1.0 dùng `0.x.y` và prerelease khi cần;
đừng gọi 1.0 chỉ vì UI đã đầy đủ. Đóng gói, deploy và public release ứng dụng
được hoãn; không có auto-publish từ nhánh main.

Phần do Naqex sở hữu dùng [Naqex Source Available License](LICENSE); xem
[phạm vi và quyền sử dụng](docs/licensing.md). Chỉ owner/nhân sự được ủy quyền
trong org tham gia phát triển ở giai đoạn này. GitHub org membership không tự
chuyển copyright; thỏa thuận quyền đóng góp phải rõ trước khi nhận code mới.
License không đổi quyền đối với Advanced Charts, model, media hoặc dataset.
