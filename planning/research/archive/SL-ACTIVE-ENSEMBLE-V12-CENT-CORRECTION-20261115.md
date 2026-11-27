# V12 — sửa cent boundary US500, giữ lần chạy đầu

Producer freeze `7aa2034`, auditor freeze `a85d395`. Lần đầu đo đủ 2.888
cells ở root private job, verdict K=0; chưa mở validation. Giữ toàn bộ
matrices, decision và `independent-audit.json` thất bại, không ghi đè.

Oracle đối soát 1.569.694 cost views và 8.037 path samples. Gold/EUR/GBP/AUD
không có sai khác. US500 có 562 discrepancies, gồm net cash cent và first-hit
P1: price grid 0,001 point với contract 1 USD/point/lot nhưng screen cũ giữ
gross nhỏ hơn cent tới khi cộng phí. Sổ tiền phải làm tròn **từng leg** tới
cent. Ví dụ gross +0,805 USD → +0,81; trừ 2,50 USD phí → −1,69, khác với
làm tròn tổng raw −1,695 thành −1,70. P1 cũng phải nghịch đảo đúng plateau
cent, không tính trigger/protect từ unrounded gross.

Sửa chỉ nhánh US500 của money/net-level/daily mark; các tài sản khác giữ
nguyên code path. Thêm regression số cụ thể và scalar oracle trước khi chạy.
V12 là screen reference 1 lot; chưa actual sizing/account. Khi đổi quantity,
fee/lot/cent policy phải replay theo quantity đó; không nhân R thành payout.

Sau commit correction, đo lại **chỉ US500** tại `cent-corrected/`, reuse và
hash-bind Gold/EUR/GBP/AUD cũ. Không đổi alpha, SL, entry, horizon, phí danh
nghĩa, F5 grid, correlation hoặc cổng. Tổng vẫn 2.888 logical cells, hai
technical attempts. Chạy lại auditor trên final mixed-version bindings;
giữ cả failed oracle. Không lấy correction làm lý do mở 2024–2026 hoặc tune.
