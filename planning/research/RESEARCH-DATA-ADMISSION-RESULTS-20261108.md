# Data admission: fixture thật đạt, R026 tiếp được sang component

Đã kiểm08/11/2026 theo [protocol](RESEARCH-DATA-ADMISSION-20261108.md) và
[recovery delta](R026-PILOT-RECOVERY-20261108.md). Đây là source/semantics
admission, chưa strategy PnL, clean OOS hoặc challenge qualification.

| Phần | Kết quả thực đo | Ý nghĩa |
|---|---|---|
| Fixture cũ03/01/2023 | 6 exports/3 instruments;379/390/1429 nến nguồn mỗi side;0,182s wall | Khớp raw hash/giá/volume và report trước; không dùng padding làm quan sát |
| Hồi quy reviewer mới | 8 tests đạt; có tamper/hash/price/padding/units/clock/exposure/holdout/missing side/raw census | Code kiểm được metadata/lineage; không chỉ có quy ước Markdown |
| Pilot attempt1 | 1/28 requests,10,999s rồi generic transport Error | Giữ failure/raw/native/seal; log thiếu status nên chưa xác định chắc nguyên nhân |
| Pilot attempt2 | 28/28 hoàn tất26,092s;1 prefix raw cache reuse,27URL mới | Không tải lại prefix; giữ attempt cũ, recovery hữu hạn, không đổi ngày/proxy |
| Admission pilot | 6 day fixtures,28 sides;1,179s | Mọi điểm close signal/FX endpoint đã chọn có nguồn, đúng thứ tự thời gian |

Ngày signal:03/01,28/01,01/02,25/02/2022. Mỗi ngày kiểm đồng thời EZU/SPY/
EURUSD ở phút cuối NYSE session; close chỉ biết sau phút đó. Chúng đều có
trước15:00 London của last-session day. FX15:01/16:03 London ngày31/01 và
28/02 có cả Bid/Ask nguồn. Chưa tính equity returns, signal direction hoặc
FX trade outcomes trong pilot. EZU có gaps trong phiên nên không gọi đầy đủ
long coverage hoặc bỏ missing events trong phép đo tiếp.

Metadata/admission hiện chuẩn hóa timestamp/units, instrument mapping,
adjustment unknown, role/exposure, parent/protocol/producer/raw bindings và
quality. Tool đọc lại raw bằng decoder Python và so mọi retained/native
price/volume; giữ raw artifacts và public DatasetManifest/DB hiện hữu. Không
thêm service/vector DB. Output chỉ `source_fixture_verified_only`.

## Hậu kiểm kỹ thuật và giới hạn

- V1 reviewer mới tự hash raw tại lần đọc; review trước commit đã bổ sung
  **expected raw hashes được freeze**. Actual fixture v2 bind với raw pins
  của independent-source-review cũ, không tự gọi current hash là provenance
  lịch sử. Giữ v1 artifact để truy vết. Output v2 khớp cả6 raw/counts cũ.
- Pilot thất bại đầu tiên cho thấy generic Error không đủ chẩn đoán. V2 thêm
  safe HTTP/cause classification, sourceframes, events/progress, CANCEL và
  bounded recovery qua helper đã có. Không khẳng định v1 là timeout/500 vì
  không có bằng chứng. V2 không phát event transient retry; hai requests chờ
  khoảng10s rồi thành công. Không dùng elapsed để suy ra HTTP retry ngầm.
- CPU nhỏ/fixtures ngắn; không có lý do GPU/Rust/vectorDB hoặc fullengine
  benchmark ở lát này. Giữ nguyên các batch cũ và mọi user WIP.
- Skill research/source-transformations đã được mở rộng đúng reference;
  structure và links đạt. Đây là hai code paths trong cùng agent, không
  independent human/model sign-off.

Private root `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:

- `execution-v1/research-input-admission-v1` và `v2`; v2 resultSHA
  `34e9891a2a98fc4215887798a2b085ebf0c5d902aef94fa0108549d8b9e14076`.
- `execution-v1/fixing-proxy-pilot-v1` failed; `fixing-proxy-pilot-v2`
  downloaded/admitted. Admission resultSHA
  `5508d994f1f9ac5fc496b4a5ee3672536e00f8fb20f1f10925bab23b57560239`.
- `prepare-fixing-proxy-pilot-v1.py`, `prepare-fixing-proxy-recovery-v2.py`,
  `download-fixing-proxy-pilot-v{1,2}.cjs`, `review-fixing-proxy-pilot-v2.py`;
  mọi bindings ở plan/manifest/admission, source snapshots giữ bytes.

**Bước tiếp:** đăng ký một bilateral price-proxy component trên2019/2022,
không ngầm yêu cầu total-return feed hoặc gọi adaptation là exact paper.
Giữ corporate-action/calendar/fill/prop/OOS gaps. C1/C2 tổng thể chưa đạt,
Goal mới tiếp tục; không đóng Goal bằng việc admission đã xong.
