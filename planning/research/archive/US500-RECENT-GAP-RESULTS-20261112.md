# Phút thiếu RS01/RS02: tick endpoint cũng không có giá

12/11/2026. Theo [protocol khóa trước source response](US500-RECENT-GAP-PROTOCOL-20261112.md),
commit `54d925e`. **Đã kiểm; chưa phục hồi được phút thiếu từ nguồn này.**
Không patch giá, rerun backtest hoặc thay verdict/điểm đã báo.

| Kiểm tra | Kết quả |
|---|---:|
| Phạm vi | Chỉ US500, 04/04/2025 15:00–16:00 UTC |
| Tick cả giờ | 23.875 |
| Phút có tick | 59/60 |
| Phút 15:01 UTC (11:01 NY) | 216 tick |
| **Phút 15:02 UTC (11:02 NY), đúng chỗ thiếu** | **0 tick trả về** |
| Phút 15:03 UTC (11:03 NY) | 236 tick |
| So OHLC M1 hai side trên 59 phút còn lại | 118/118 khớp chính xác |
| Thử sửa giá/timestamp/thứ tự để kiểm reviewer | Cả 3 bị phát hiện |
| Native fetch/cache + persistence | 4,31 giây |
| Fraction decode + overlap/mutation review | 3,76 giây |

Tick JSON native được đối chiếu toàn 23.875 records bằng Fraction delta
decoder đã dùng trong campaign, gồm timestamp, Bid/Ask và volume. Khớp nguồn
cũ nhưng không phải feed/người review độc lập. Hash/source snapshot giữ nguyên.
Không mở source/strategy outcomes 2026 hoặc gọi broker/LLM. Không có job nền.

## Điều đã biết và điều chưa thể suy ra

Phút thiếu không chỉ xuất hiện sau bước gộp M1 của mình: tick endpoint cùng
nhà cung cấp cũng không trả tick trong đúng phút đó. 118 nến overlap khớp là
bằng chứng phép biến đổi đúng trong giờ được kiểm, không chứng nhận toàn feed.
Chưa phân biệt được provider không phát quote, mất dữ liệu upstream hay thị
trường/broker mục tiêu có diễn biến khác. Không coi phút này chắc chắn đứng
yên hoặc dùng giá trước/sau thay thế. Hai SELL của RS01/RS02 năm2025 vẫn
unresolved; full-period PnL của các sổ đó vẫn N/A, không tự thay bằng known subset.

**Bước tiếp nhỏ nhất:** kiểm inventory nguồn tick US500/QDM đã có quyền dùng
cho đúng giờ này. Chỉ khi có nguồn phù hợp mới đăng ký đối chiếu clock/BidAsk/
contract và derived repair; giá của provider khác không tự là exact replacement.
Hoặc đăng ký một sensitivity/bounds study giữ đầy đủ nhánh stop/gap, không
đổi source uncertainty thành exact result. Chưa tự chạy thêm cả năm, sửa rule
hay mua data chỉ để xử lý một phút. Không có evidence mới để promote challenge.

Private evidence:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1/us500-recent-gap-source-v1/`
giữ manifest/source snapshot, raw/native hour, result, progress/events và review.
Probe/review scripts được copy bên cạnh; replay không được overwrite output
v1. Final review có raw/native/manifest/reviewer hashes và cả các hạn chế trên.
