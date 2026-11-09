# ECB archived source: đọc đúng cấu trúc, chưa đủ làm tín hiệu giao dịch

10/11/2026. Tiếp [protocol](ECB-ARCHIVED-SURPRISE-SOURCE-PROTOCOL-20261110.md)
freeze `87bc58d` và [revision đọc file](ECB-ARCHIVED-SOURCE-READ-REVISION-20261110.md)
freeze `72589fb` trước numeric review. Collector và reviewer v2 đã terminal exit0;
không còn job này chạy nền. Catalogue giữ **92 hồ sơ / 58 policy-model versions**,
chưa thêm hypothesis hoặc ứng viên challenge.

## Kết quả và ý nghĩa

| Phần kiểm | Kết quả | Có thể kết luận |
|---|---|---|
| Nguồn | 3 file đúng ref/blob/size/SHA đã khóa | Đọc đúng archived package, không phải main tới 2025 |
| Ngày | Mỗi sheet 308 ngày, 07/01/1999–12/12/2024, tăng dần và không trùng | Date census đạt; cả lịch sử này là source exposure, không clean OOS |
| Metadata | 8 ngày năm 2024 mỗi sheet; README còn ghi tới 2023, Notes ghi last update 18/07/2024 | Giữ bất nhất metadata, không dùng nhãn update làm publication timestamp |
| Số học | 1.709 ô numeric OIS2Y/STOXX được đối chiếu XML/Fraction với openpyxl; sai lệch tối đa 1e−15, dưới 1e−12 đã khóa | Parser parity trong phạm vi hai cột, không chứng minh raw data đúng |
| Focus | Đủ 8 ô, 4 ngày pilot × 2 fields trong conference sheet | Source binding đủ, chưa tính direction/signal/returns |
| Known-at | Cả 4 ngày không được admit | Chưa có last-observation, publication/access và causal cleaning bounds |

| Sheet | OIS2Y numeric / text / numeric bằng 0 | STOXX numeric / text / numeric bằng 0 |
|---|---:|---:|
| Press Release Window | 286 / 22 / 24 | 308 / 0 / 0 |
| Press Conference Window | 256 / 52 / 3 | 265 / 43 / 0 |
| Monetary Event Window | 286 / 22 / 8 | 308 / 0 / 0 |

Số 0 là tập con của numeric, không cộng thêm vào tổng. Text sentinel không
được đổi thành 0; đây không phải số liệu đủ cả cặp trên mọi ngày. Các ô numeric
ngoài 4 ngày được đọc để kiểm nguồn, không chạy classification/regression/PnL.

Notes xác nhận **OIS2Y theo basis points**, **STOXX50E theo percentage points**;
actual header `OIS_2Y`/`STOXX50` đã bind theo alias đã đăng ký. Đơn vị được đối
chiếu bằng tay với definitions/headers sau review; `selected-cells.json` vẫn
giữ marker `definition_sheet_binding_pending`, không sửa artifact đã seal hoặc
giả một consumer máy đã tự xác minh đơn vị.

Notes mô tả old conference medians 14:15–14:25 → 15:40–15:50 và ghi windows
đổi từ 21/07/2022. Điều này xác nhận có đổi lịch, **chưa bind chính xác từng
window mới với raw inputs**. Không tự dịch processed values 15 phút rồi gọi
đúng causal timing. [Official appendix](https://www.ecb.europa.eu/pub/pdf/annex/Appendix_Measuring_Euro_Area_Monetary_Policy.pdf)
còn dùng full-day spread median, centered outlier filter, same-ms medians và
minute carry-forward. Window label không chứng minh mọi input đã có lúc bot
quyết định; current downloadable file không tự là live-available feature.

## Guard và giới hạn kiểm chứng

Reviewer v1 giữ nguyên failure `external_relationship`. V2 chỉ cho phép đúng
hyperlink citation tới workbook ECB, chặn network DNS/connect khi đọc, macro,
formulas, external data links/connections và mọi external relationship khác.
Sai part/target/type và DNS attempt đều bị reject. Không có external requests
trong review; không execute nội dung workbook.

Date gate được kiểm trước hai cột values; actual date mutation sang 2025 bị
reject. Actual value/authority/raw bytes mutations cũng bị reject. 11 causal
negative fixtures kế thừa đạt; các fixture không là runtime broker enforcement
hoặc độc lập về nguồn. Hai cách đọc số học dùng cùng source và cùng agent.

Giữ [tick pilot](ECB-CONFERENCE-SOURCE-RESULTS-20261110.md) **admitted:false**:
3/4 ngày đủ, ngày 24/01/2019 pre-window không qua density/gap gate. Workbook
processed không lấp quotes thiếu, không nâng source pilot hoặc C1/C2 thành đạt.
Không broker/model calls, own 2025+ data, strategy/features/PnL hay quyền execution.

## Thời gian, lưu và bước tiếp

| Phase thực đo | Wall | CPU |
|---|---:|---:|
| Collector 3 GET | 2,593 s | 0,047 s |
| Offline reviewer v2 | 87,052 s | 86,563 s |

Không tính research/code/Git hoặc v1 failure chưa đo. V2 gọi `sheet.cell`
nhiều lần trên read-only worksheet; source cho thấy khả năng scan XML lặp,
chưa có profiler để quy phần trăm thời gian. Không rerun file đã kiểm để làm
đẹp benchmark. Nếu cần reader này cho package mới, đổi sang one-pass iter_rows
và kiểm parity trên sealed outputs trước; chưa cần engine/framework mới.

Private campaign `E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/ecb-archived-surprise-source-v1/` giữ raw/seals/config/manifest/
source result và v1 failure; `execution-v1/ecb-archived-surprise-review-v2/`
giữ pins/snapshots/definitions/headers/focus/result. Saved scripts
`prepare-ecb-archived-source-v1.py`, `review-ecb-archived-source-v1.py` và v2.

- Source result SHA256: `7c6a820623aa54274261e4aaa5222957e104738d5130c03a7f2ceb17bd004963`.
- Review result SHA256: `adac9f8a902ec1e5a70bd32dee8af44c897dcc071e8612ea99d8630972496246`.
- Workbook SHA256: `bbe89f13a0df157137af6d5b603bd7a547609231fed02f72764aecaece9fff1a`.

**Quyết định:** source structure reviewed, intraday feature chưa được admit.
Gác financial trial dùng archive này cho tới khi có causal/access evidence
mới; không tải lại package hoặc relax gate. Tiếp cơ chế khác có primary support
hoặc blocker material của survivor khi có nguồn mới; không fee/holding grid
để bù một thiếu sót về dữ liệu. Goal active, C1/C2 chưa đạt.
