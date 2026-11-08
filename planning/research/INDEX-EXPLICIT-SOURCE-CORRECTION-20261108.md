# C2: phân biệt nến nguồn với nến do thư viện chèn

Đăng ký cách sửa trước khi tính lại outcome bị ảnh hưởng. C1/C2 vẫn chưa đạt;
không đổi strategy, ngày/giờ, risk, cost hoặc gate để cứu kết quả.

## Lỗi đã tái hiện

Pinned `dukascopy-node@1.51.1`, `dist/index.js` hàm `normaliseCandles`, dòng
15707–15719: tự thêm carried-close/volume0 vào các khoảng `times` bỏ qua,
kể cả phần đầu ngày trước nến đầu tiên. `ignoreFlats:false` giữ cả phần chèn;
`ignoreFlats:true` lại loại cả nến nguồn có volume0. Hai option không thay thế
được việc xác định nguồn gốc từng nến.

Fixture03/01/2023 đã sealed: EZU1260 nến native/379 nến explicit,881 chèn,
trong đó11 phút cash; SPY1260/390/870, đều ngoài cash; EURUSD1440/1429/11.
Cả hai side có cùng counts ở fixture này. Chưa suy mọi data/broker có lỗi
hoặc giá nguồn vắng mặt chứng minh không có quote thực tế.

## Phép biến đổi mới và kiểm chứng

- Raw JSON đã cache là nguồn xác định timestamps: cộng `times[i] * shift`
  theo đúng thứ tự; giữ đúng các nến được liệt kê. Không tự điền timestamp,
  giá, volume hoặc suy từ việc nến flat/volume0.
- Giữ native decoder/format và giá nến nguồn. `getCachedM1` thêm opt-in
  `sourceCandlesOnly:true` cùng callback hash/count của raw responses. Default
  native vẫn giữ để tái hiện historical attempts, không phải source-only proof.
- Reviewer Python riêng dựng integer price units/volume từ raw JSON, đối chiếu
  toàn export native và nến explicit. Chấp nhận sai số biểu diễn base float
  tối đa1e−7 **đơn vị giá nguyên** như384.43600000000004; không nới price grid.
  Off-grid có ý nghĩa, giá/volume sửa, duplicate time, thiếu raw/columns đều lỗi.
- Tạo output/view mới, pin source/protocol/raw/parent; cache-only và chặn network
  trong lượt kiểm fixture. Không sửa installed package/upstream hoặc dữ liệu cũ.
- R025: đối chiếu explicit provenance tại đúng endpoints đã dùng trên2018Q4
  warmup và2019–2024. Giữ rows có giá nguồn, đánh dấu padding/missing unknown,
  tính lại **chỉ các rows/summary bị ảnh hưởng**, tiêu chí cũ không đổi. Không
  lựa ngày đẹp hoặc chạy lại toàn M1/numerical strategy chỉ để review.
- Các sách US500 khác dùng native expanded views phải được ghi rõ limitation;
  kiểm mức ảnh hưởng theo signal/fill/range/risk trước rerun phần cần. Hash và
  arithmetic binding cũ chỉ chứng minh expanded-view scenario, chưa explicit
  observation hoặc intrabar/broker correctness. QDM Forex/Gold khác pipeline
  không tự bị invalidate bởi phát hiện này.

14 Node tests và7 Python tests đạt trước lượt cache-only/source-view review.
Giữ failure float-base ở probe đầu, bổ sung regression; không gọi tất cả lần
đều pass đầu tiên. Đây là sửa data semantics, không optimization speedup.
Deadline/cancel/PID/status/log/source snapshots dùng attempt owner hiện có;
không network tải mới, holdout2025+, model hoặc broker calls cho correction.

Kết quả cập nhật tại [correction results](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md).
File kết quả có thể chưa tồn tại trước khi hoàn tất correction; protocol không
được sửa sau outcome chỉ để nâng trạng thái hoặc thay hash nguồn cũ.
