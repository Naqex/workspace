# C2: canonical paired source-only views và reader gate

Tiếp [decoder correction](INDEX-EXPLICIT-SOURCE-CORRECTION-20261108.md) và
[review đã có](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md). Đăng ký trước khi
tạo quarterly views hoặc tính lại outcome của sáu sách commission0.

## Input và phép biến đổi cố định

- Chỉ US5002022–2024 từ existing `us500-unfiltered-m1-v1/<year>` và raw
  response cache do manifest dẫn tới.8quarter-side parts/năm. Không network,
  provider/account mới, download bổ sung,2025+, broker hoặc model calls.
- Rehash parent manifests/result/seals; kiểm schema/time/order/grid/BidAsk.
  Raw cache thiếu hoặc không khớp phải dừng; không quay sang native padding,
  tự tải mạng, sửa source hoặc coi đó là lợi nhuận0.
- Decode raw timestamp/price/volume theo pinned format bằng helper đã kiểm.
  Giữ nến explicit nằm trong parent view và có giá/volume khớp. Padding chỉ
  được nhận diện sau binding giá carried-close; không loại mọi volume0.
- Parent có thể đã là paired intersection. Không tạo lại nến side đã bị
  parent bỏ; ghi số explicit source không hiện diện trong parent. View mới
  tiếp tục lấy intersection của **hai side explicit**, original order.
  Giữ unpaired explicit rows trong journal, không tạo giá side còn thiếu.
- Tạo output mới, không sửa raw/old views/results. Manifest/result/proof/seals
  pin code/validator/protocol/calendar/raw/parent và counts. Một writer/year,
  deadline900s/year, CANCEL/status/log/source snapshots.2022 chạy trước; sau
  khi reader/independent check đạt mới chuẩn bị2023/24, tối đa2workers data.

## Reader và scope của bằng chứng

Reader legacy vẫn dùng được để tái hiện expanded-view scenarios nhưng trả
`source_presence_verified:false`, coverage chỉ là decoded timestamps. Current
study CLI bắt buộc source-only proof trước simulation; không cho bypass để
lấy kết quả. Label trên manifest riêng lẻ không đủ.

Proof phải khớp producer/validator code, calendar/protocol, parent/raw hashes,
retained output seals, side/quarter counts và unpaired journals. Đây là cache
của phép biến đổi đã thực thi và có regression; không là independent feed,
chữ ký chống người cố tình giả toàn bộ artifacts, executable tick hoặc edge.
Code/input đổi thì phải revalidate thành attempt mới; không thay hash cũ.

Trước numeric rerun: actual CLI negative trên legacy phải bị chặn trước
simulation; source-only view phải qua reader thật. Sau đó review khác code
path về source timestamps/giá/counts trên data đã tạo. Không bỏ validation để
đạt thời gian ngắn hơn. Timers tách prepare/review/simulation/rework.

## Phần numerical được phép tiếp sau data gate

Giữ exact Noise14 và first→last30, cost scenario public FTMO commission0,
hai mức slippage0,25/0,75 mỗi chiều,10k/planned25USD và null-control. Không
thay strategy/clock/SL/risk/funding hoặc tiêu chí cũ theo outcome. So parent
decisions/entries/exits/cash/range/gaps; source sửa có thể đổi state cả phần
sau nên affected book cần rerun trọn, không chỉ xóa trade rồi trừ PnL.

Chỉ rerun sách cần thiết sau review ảnh hưởng; giữ original results và source
snapshots. Không đọc tất cả lịch sử dài RSI/monthly trong lượt chuẩn bị này.
Các studies đó tiếp tục expanded-view limitation cho tới slice correction
của riêng chúng. C1/C2 chưa đạt; data gate xanh không cho phép challenge/broker.
