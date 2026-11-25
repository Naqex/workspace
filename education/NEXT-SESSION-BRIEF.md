# Thẻ Tiếp Nối Nhanh Khóa Học Trading (`15` Phút)

> **Phạm vi:** Tóm tắt 1 trang từ [course.json](course.json), [progress.json](progress.json), [README.md](README.md) và [eurusd-breakout-retest-v0.md](practice/eurusd-breakout-retest-v0.md). Không chứa đáp án, không đặt lệnh, ngân sách `1 triệu VND` chỉ ở mức kế hoạch.

---

## 1. Vị Trí Hiện Tại

- **Khóa học:** *Forex từ nền tảng đến thực hành có kiểm chứng* (v1.1 · `8` chặng · `24` bài · tiếng Việt chính).
- **Trạng thái:** Đánh giá đầu vào đã đóng (`07/09/2026`); đang học `main_course` (`in_progress`), có **`56` lượt làm bài** và **`15` sản phẩm thực hành** (`M01-DEMO-01` → `M08-L01-OBS01`).
- **Hoàn tất chính thức:** **`4 / 24` bài** (`M01-L03`, `M02-L01`, `M02-L02`, `M04-L01`) và **`0 / 8` chặng** (đã đi qua khung `24/24` chủ đề tới `M08-L03`, chưa chốt hết sản phẩm cuối chặng).
- **Bản đồ `19` kỹ năng:**
  - **Độc lập (`11 / 19`):** phần trăm, phí và P/L ròng, đọc cặp tiền, hướng lệnh bán, quy đổi pip/lot/unit EURUSD, cỡ lệnh theo SL, tỷ lệ lỗ tài khoản, P/L lệnh đã đóng, trạng thái tài khoản và giải phóng ký quỹ, tính rủi ro tích hợp.
  - **Làm được khi có hỗ trợ (`2 / 19`):** xác suất cơ bản (`probability`), P/L lệnh mua (`buy_position_pnl`).
  - **Chưa đánh giá chính thức (`5 / 19`):** đọc chart (`chart_reading`), cơ chế loại lệnh (`forex_order_mechanics`), kế hoạch rủi ro viết tay (`risk_plan`), thuật ngữ tiếng Anh (`english_*`).
  - **Cần luyện thêm đúng `1` kỹ năng (`1 / 19`):** **`leverage_margin_vs_pnl`** — ở các bài trước bạn đã tính đúng số tiền lỗ dự kiến và mức ký quỹ, nhưng diễn đạt nhân quả còn dễ trộn lẫn. Điểm cần chốt khi ghép vào bài thực hành: *đòn bẩy chỉ làm thay đổi tiền ký quỹ tạm giữ, không tự làm tăng hay giảm tiền lỗ nếu khối lượng (lot/unit) và khoảng SL giữ nguyên*.

---

## 2. Buổi Học `15` Phút Kế Tiếp (Sẵn Sàng Ngay)

Hoạt động đang chờ trong `progress.json` là **áp dụng luật [BR-01 v0](practice/eurusd-breakout-retest-v0.md)** (ứng viên phá lên và retest lần đầu trên `EUR/USD H1`, chưa backtest đạt lợi thế, không dùng để đặt lệnh):

1. **Tình huống chính (`5–8` phút) — `BR-01-APPLY-02`:**
   - *Bối cảnh nối tiếp:* Ở ca `BR-01-APPLY-01`, nến chạm đầu tiên đóng trên biên trên vùng nhưng `Close < Open` nên setup bị hủy theo luật v0.
   - *Đề bài kế tiếp cần bạn tự quyết định:* Sau một nến breakout hợp lệ, cả **`6` nến H1 tiếp theo (`B+1` tới `B+6`) đều nằm hoàn toàn phía trên vùng đóng băng mà không chạm vào vùng**. Tại thời điểm đóng cửa nến thứ `6`, trạng thái của setup này là gì theo luật v0? *(Chỉ trả lời ngắn bằng tiếng Việt + `1` dòng lý do; không cần làm lại chuỗi phép tính cơ bản.)*
2. **Bước nối tiếp (`5` phút) — Khoảng TP `2:1` & Chi phí thực:**
   - Sau khi bạn đã chọn đúng nến **Retest** làm mốc đặt SL (`BR-01-SL-ANCHOR`), gia sư sẽ minh họa khoảng **TP cách Entry đúng `2` lần khoảng `Entry – SL`** và phân biệt tỷ lệ giá dự kiến với kết quả ròng sau phí/trượt giá.
3. **Nhắc ôn tùy chọn (`2` phút):**
   - Lồng `1` câu kiểm tra ngắn cho kỹ năng **`leverage_margin_vs_pnl`** (cùng khối lượng và SL, đổi đòn bẩy thì ký quỹ đổi ra sao và khoản lỗ tới SL có đổi không?) — không mở lại bài kiểm tra đầu vào.

---

## 3. Lựa Chọn Khác Nếu Muốn Chốt Sản Phẩm Chặng

| Hướng muốn học | Mục tiêu cụ thể | Tài liệu gốc |
|---|---|---|
| Đọc biểu đồ thực tế | Hoàn thiện ghi chú chart bằng dữ kiện, tách dự báo (`M04-L02/L03`) | [modules/04-doc-thi-truong.md](modules/04-doc-thi-truong.md) |
| Phương pháp & Demo | Quay lại phần thực hành `M05/M06` từng tạm hoãn theo yêu cầu | [modules/05-phuong-phap.md](modules/05-phuong-phap.md) · [modules/06-demo.md](modules/06-demo.md) |
| Quỹ & Việt Nam | Chốt bảng kiểm tra hợp đồng, thuế, thanh toán Việt Nam (`M07-L03`) | [modules/07-quy-viet-nam.md](modules/07-quy-viet-nam.md) |

---

## 4. Câu Mở Buổi Nhanh (Copy-Paste Cho Gia Sư)

> *"Tiếp tục khóa học trading từ `education/NEXT-SESSION-BRIEF.md` và `education/progress.json`: giao ngay bài `BR-01-APPLY-02`, sau đó minh họa TP `2:1` và lồng `1` câu ngắn chốt kỹ năng `leverage_margin_vs_pnl`. Không lặp bài toán cơ bản, không đặt lệnh."*
