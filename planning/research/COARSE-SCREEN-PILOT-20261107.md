# Pilot sàng lọc PnL H1 — khóa trước outcome, 07/11/2026

Owner duyệt triển khai kho ý tưởng và thử một tầng economic screen rẻ, có giới
hạn, trước khi dùng nó chọn/gác ứng viên. Scope chỉ software research trên
Q1/2022 đã consumed; không OOS, không mở2025+, không broker/provider/model job.

## Câu hỏi và phạm vi cố định

- Dùng raw warmup01–31/12/2021 và evaluation03/01–31/03/2022 đúng hashes của
  Discovery3. Không export/download. Chuẩn bị source-bound H1 summary một lần,
  giữ first/last observed BidAsk, extrema riêng Bid/Ask, midOHLC và tickcount.
  Xây H4 bằng builder hiện có, gồm đúng partial/missing-hour semantics.
- Tái sử dụng tám rule hiện tại, native size_for_stop, stop-at-fill, bar-protection,
  cost arithmetic và financing_calendar. Planned risk25USD, initial10k, một vị thế,
  hai cost reference/stress cũ; không đổi parameter/risk/exit sau outcome.
- Pending entry/strategy exit chỉ xử lý ở first observed quote của H1 kế tiếp;
  SL theo side-price H1extrema, gap dùng open, intrahour dùng stop level. Đây là
  **modeled bar execution**, không phải first-crossing-tick fill. Giá đối ứng
  không ảnh hưởng PnL được ghi là modeled, không gắn provenance broker quote giả.
- Financing22UTC/weekday/Wed×3 xử lý trước quote đầu H1 theo calendar; không
  bịa quote ở weekend. Cuối mẫu giữ position/pending/floating, không force-close.
- Không mô phỏng full tick internal-risk/prop DD, daily stop hoặc phase reset.
  Không dùng coarse output làm evidence qualified hoặc tự reject/promotion.

## Kiểm chứng trước dùng

1. Fixtures BUY/SELL, phí/credit, stop gap/intrahour, next-open causality,
   pending cuối mẫu, partial Friday/weekend, giá không đổi và malformed input.
   Candidate state không nhìn tương lai; samebar signal không được fill ngay.
2. H4 từ new H1 input phải khớp sealed inspection archive trên cả warmup và
   evaluation. Archive là đối chứng, không nới current native cache guard.
3. Historical comparison bốn Discovery3candidates×2costs, kể cả positive và
   negative. Giữ mọi mismatch. Diagnostic budget cho ưu tiên review: abs net
   difference <=6,25USD (0,25 của planned25USD), same entry/closed/open/pending
   counts và same sign ngoài vùng gần0. Đây là ngân sách sai số kỹ thuật cho
   pilot, không tiêu chuẩn thống kê/edge và không bảo đảm dữ liệu tương lai.
4. Một bounded real-prefix Jan3–Jan7/2022 comparison với native tick source
   hiện tại, cùng warmup/rules/costs; input read ngoài compute timing. Tick path
   dùng toàn bộ observed quotes trong prefix, không synthetic ticks. Không full
   quarter replay mới chỉ để benchmark. Existing full-quarter evidence giữ nguồn.
5. Ghi cold preparation/read/probe/compute/report wall+CPU và source/input pins.
   Mục tiêu compute ít nhất5× nhanh hơn bounded native cases với phạm vi khác
   được ghi rõ; không gọi ratio là exact-engine speedup. Cold cost báo riêng.

Nếu lỗi material, quarantine đúng output. Nếu không có lợi ích rõ hoặc sai khác
vượt budget/đổi verdict, giữ prototype/triage-only và dùng tick core cho quyết
định kinh tế. Không sửa tiêu chí theo kết quả. Near-zero/risk/gap ambiguity đều
cần tick review; không tuyên bố PnL là bound hình thức trên mọi tick path.

Ngân sách thực thi: một preparer,300giây trần; bounded benchmark180giây trần;
không auto retry, output riêng không overwrite. Chưa triển khai8–12rule mới
hoặc mở annual batch trong pilot này. Catalogue30–50hồ sơ được làm độc lập,
phân biệt existing/new/variant/deferred và nguồn chỉ gợi cơ chế với paper replication.

Receipt/actual measurements theo AI plan owner hiện có. Không tạo UI, engine
production, risk owner, approval ledger hoặc service nền mới.
