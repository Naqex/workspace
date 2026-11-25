# Chẩn đoán lệnh thắng có chọn lọc

Dùng với sổ Development đã khóa để hiểu nguồn tiền lời và độ mong manh của
exit. Đọc cùng [chẩn đoán lệnh thua](selective-loss-diagnosis.md). Khóa cohort,
cost, cách ghép pairs, benchmark và ngưỡng trước khi xem breakdown. Các
mặc định dưới đây là cổng chẩn đoán và phải giữ nguyên trong cùng protocol.

## Hai nhóm nhãn và điều kiện quan sát

- **Known-at-Entry.** Trend, volatility, dấu carry, session/ngày trong tuần
  và khoảng cách tới cấu trúc. Mọi input có timestamp `known_at <= entry`
  và phải thuộc đúng nguồn có thể biết tại thời điểm đó. Công bố thiếu
  dữ liệu dưới dạng unknown. Đối chiếu win rate, loss rate, số trade và
  net kỳ vọng của mỗi bucket với toàn cohort, dùng cả winners, losers và
  hòa, tránh suy luận từ pool winners. Chốt buckets trước khi đọc kết quả.
- **Post-Entry Path.** MAE là độ lỗ nổi xấu nhất, MFE là độ lãi nổi tốt nhất;
  dùng units R với mẫu số risk gốc và cùng quy ước net của sổ. Capture
  efficiency = realized net R / MFE R khi MFE > 0. Đo time-to-peak tới mốc
  đầu tiên có MFE và báo độ phân giải; swap share = swap credit / net R
  khi net R > 0. Dấu swap thực nhận thuộc post-entry, dấu quote ở entry
  thuộc known-at-entry. Mọi dữ liệu post-entry chỉ dùng chẩn đoán exit và
  kiểm độ mong manh. Cấm đưa vào biến số/điều kiện vào lệnh. Exit
  counterfactual cần ghép cùng intent, entry, initial risk và cost.

## Năm nhãn, theo thứ tự ưu tiên

Chỉ gán cho lệnh đóng có net R > 0. Gán đúng một nhãn khi đủ bằng chứng
theo thứ tự sau. Giữ `UNCLASSIFIED_MISSING_EVIDENCE` riêng khi thiếu dữ liệu
cần cho nhãn ưu tiên còn khả dĩ. Trạng thái này nằm ngoài taxonomy.

1. **CUTOFF_TRUNCATED_WIN.** Exit thực tế do lịch đóng đã đăng ký. Đường
   đối chứng đi tiếp có `net_R − actual_net_R >= 0,50R` và net đối chứng
   ≥1,25× net thực tế. Giữ cùng entry, stop, risk và phí. Khi không có
   counterfactual hợp lệ, hiệu ứng cutoff là unknown.
2. **CARRY_ASSISTED_WIN.** Swap credit ≥0,10R, đồng thời góp ít nhất 25%
   net win hoặc net trước swap ≤0. Lưu swap debit/credit có dấu.
3. **TAIL_TREND_RUNNER.** MFE ≥3R, realized net ≥2R, giữ ≥72 giờ và
   capture efficiency ≥0,40. Với path bar, ghi độ phân giải ở receipt.
4. **CLEAN_STRUCTURAL_WIN.** MFE ≥1R, net ≥0,50R, MAE ≤0,75R (độ lớn)
   và capture efficiency ≥0,50. Đây là quy ước cấu trúc theo path.
5. **LUCKY_NOISE_WIN.** Winner còn lại sau bốn cửa, nhạy với ma sát hoặc
   có capture/MAE yếu theo ngưỡng. Tên là nhãn vận hành, chưa chứng minh
   ngẫu nhiên hay dự báo kém. Giữ metric gốc để phân biệt nguyên nhân.

## Winner fragility

- Mẫu số tỷ trọng là tổng realized net R dương, với phạm vi giống nhau.
  Cảnh báo nếu tiền lời lucky/noise >30% pool thắng hoặc nếu winner-label
  coverage <90%. Không coi unknown là clean. Báo thêm unknown share.
- Báo tỷ trọng và net loại Top‑2/5/10. Cảnh báo Top‑2 >50% hoặc net
  Ex‑Top‑5 ≤0. Báo cỡ mẫu, cohort và quy ước xếp hạng.
- Với các thắng bị cắt, báo pool net thực tế, phần tăng đối chứng và tỷ
  lệ phần tăng/tổng net dương counterfactual trên tập winner ghép cặp.
  Báo cỡ mẫu và lý do thiếu cặp. Không khái quát sang mọi trade hay tuyên
  bố đổi exit cải thiện payout từ riêng pool thắng.
- Chỉ dùng Development theo protocol, loại lệnh có quyết định/entry/exit
  ngoài biên. Giữ lock holdout nguyên trạng. Không thêm exit variant hoặc
  chuyển subgroup đẹp thành luật mới từ phép hậu kiểm. Mọi giả thuyết sau
  đó cần đăng ký riêng, giữ lịch sử lựa chọn và kiểm trên tập phù hợp.
