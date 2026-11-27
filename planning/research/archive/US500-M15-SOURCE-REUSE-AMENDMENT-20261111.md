# Source reuse correction trước mọi outcome M15

Attempt `us500-m15-opening-screen-v1` dừng ở source preflight,0books/0PnL.
Giữ failure/manifest/protocol và source snapshots nguyên vẹn. Frozen economic
protocol ở commit `cc7a1e8` không sửa.

Root cause: current fixture2022 có CRLF, accepted source proof pin LF;
normalized newline probe khớp SHA7357319f…ec8e84. Bản exact bytes còn tại
`us500-explicit-source-v1/2022/source-snapshot/4-nyse-2022.json`. Không sửa
raw, proof, fixtures hoặc hashes để ép pass. Code consumer mới đã vô tình
chọn full raw-revalidation path yêu cầu current calendar exact thay vì
accepted canonical-view reuse hiện có.

Trước rerun, giữ nguyên mọi signal/SL/cost/year và sửa source plumbing:

- Reuse `us500_year_source.load_year_side` với expected proofhash đã đăng ký;
  helper kiểm đủ4quý/8seals/year/census/clock và direct canonical hashes.
  Thêm2023/2024 là các source years đã accepted;2019/2022 giữ,2025+ vẫn chặn.
  Đọc được năm không tự là quyền financial study hoặc holdout.
- Lấy exact calendar snapshot đúng accepted hash, yêu cầu duy nhất một bản;
  so parsed content với fixture hiện hành để bắt thay đổi holiday/DST/session
  thật, ghi cả hai hashes. Không normalize/reseal calendar làm evidence mới.
- Đây là kế thừa raw transformation proof đã accepted và kiểm canonical
  bytes hiện tại; **không thực thi lại raw decoder/raw archive hashing toàn
  bộ**. Giới hạn này thay câu chưa rõ về raw bindings trong protocol, không
  tuyên bố full fresh raw review. Canonical file/proof thay đổi vẫn reject.
- Synthetic tests thêm recent years/holdout và calendar missing/tamper/content
  mismatch trước actual outcome. Output mới `us500-m15-opening-screen-v2`;
  không đèv1 hoặc tự đổi year guards khác. Protocol và amendment hashes cùng
  lưu vào manifest trước run.

Đây là technical correction trước PnL, không strategy trial/version mới.
Không bỏ kiểm tra bắt buộc của shared raw validator; dùng đúng consumer reuse
được thiết kế và giữ bằng chứng nguyên gốc.
