# Kiểm lại giả định commission chỉ số theo nguồn FTMO

Đăng ký lúc tiếp tục Goal 08/11/2026, trước khi tính kết quả commission mới.
Goal đã được owner bật rõ ràng; C1/C2 giữ nguyên trong
[campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md). Không broker/holdout mới.

## Phát hiện nguồn và phạm vi xác minh

Đọc lại 08/11: [FTMO — Zero Commissions on Indices](https://ftmo.com/en/blog/zero-commissions-on-indices/)
nêu các index symbols trên nền tảng của hãng không có commission. Đây là nguồn
chính thức cho **tham số commission hiện được công bố**, không chứng minh giá
khớp, spread/slippage, lot/tick/margin, swap/dividends hoặc lịch sử commission
từng năm 2013–2024. Không lấy thông số FTMO US/OANDA thay profile global Swing.

Các kết quả US500 cũ dùng commission **0,5 USD/lot/chiều** như một giả định đã
khai báo; chưa từng được xác nhận là phí FTMO thực tế. Không sửa hoặc xóa những
attempts đó. Khác biệt nguồn này cho phép đăng ký một cost scenario có căn cứ;
không phải giảm phí tùy ý để làm một chiến lược thua trở thành thắng.

## Lát triển khai và thí nghiệm trước outcome

1. Thêm cost-scenario rõ tên cho research index, giữ default legacy 0,5 và
   backward compatibility của các artifact cũ. Profile mới chỉ commission0;
   không thay quantity grid, contract size, giá, clock, entry/exit, SL, risk,
   margin hoặc slippage/funding assumptions. Phải ghi những phần chưa verified.
2. Đối soát và sizing cùng nhận commission scenario; không chỉ cộng trả lại
   phí vào PnL cũ. Quantity/margin/trade path có thể đổi nên cần mô phỏng mới.
   Reviewer vẫn recompute số học riêng, kiểm profile/manifest/result bindings.
3. Trước PnL: fixture tính tay commission0 cho BUY/SELL, lot/risk và open/funding;
   default legacy giữ numerical results; profile không biết hoặc mismatch phải
   bị chặn. Không sửa numerical source khi có writer đang pin source đó.
4. Đợt đầu chỉ **hai phiên bản intraday đã có**: R048 noise14 và R051
   first→last30min, cùng canonical unfiltered2022–24 và frozenNYSEcalendars.
   Không thêm strategy/threshold sau thấy outcome. Input vẫn có cash gap2023
   và modeled M1 stop limitations; không giả toàn bộ tick path đã đầy đủ.
5. Hai kịch bản: commission0 với slippage0,25/chiều (reference), commission0
   với slippage0,75/chiều (stress); spread lấy observed Bid/Ask như cũ. Giữ
   declared funding cho vị thế nếu bị carry ngoài ý muốn; không tự đặt swap0.
   Mỗi policy/year có null control. Protocol/source/input/output mới có hash,
   deadline/status/log, một writer; không download lại dữ liệu đã seal.
6. Giữ tiêu chí initial triage đã dùng: ưu tiên kiểm sâu nếu cả ba năm dương ở
   hai costs, không material defect; nếu không đạt giữ outcome. Dù đạt cũng
   chưa C1. Đây là exposed retrospective **target-cost scenario**, không clean
   OOS hoặc tái hiện chính xác điều kiện FTMO lịch sử. Trial/selection history,
   tick/native prop path và prospective evidence vẫn phải review.

Chưa có kết quả mới tại thời điểm đăng ký. Hậu kiểm theo existing research/
qualification/engineering skills; ưu tiên correctness và data/cost fit, không
thêm framework, thay broker runtime, mua challenge hoặc mở2025+.
