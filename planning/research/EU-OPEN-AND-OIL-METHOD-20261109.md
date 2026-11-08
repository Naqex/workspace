# Chọn bước sau close-momentum negatives: đổi cơ chế, kiểm mapping trước

[Consensus](INDEX-CONSENSUS-RESULTS-20261109.md) đã không đạt. Không thêm clock/
filter vào exact recipes cũ. Research ngày 09/11 đưa ra hai hướng có mức độ
admission khác nhau; chưa có economic outcomes mới ngoài R078/R079.

## 1. EU-open uncertainty resolution: ưu tiên method/source admission

[Cambridge / Bondarenko–Muravyev](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/market-return-around-the-clock-a-puzzle/089E33AC0B4D3B9A02CBA31EDF6505B3)
nghiên cứu E-mini S&P 500, không CFD. [Appendix chính thức IA.7/IA.8 và Figure IA.7](https://static.cambridge.org/content/id/urn%3Acambridge.org%3Aid%3Aarticle%3AS0022109022000783/resource/name/S0022109022000783sup001.pdf)
xác định full EU-open 23:30–03:30 ET; baseline mua đầu, đóng cuối. Không suy
clock 02:00–06:00 từ tên “European open”. Phần điều kiện dùng VIX/volatility
chưa có input admission nên chưa đưa vào. Không copy code/data/tables.

Own adaptation dự kiến để đăng ký riêng: unconditional BUY US500, entry
decision 23:30 New York ngày trước, scheduled exit 03:30 ngày mang nhãn;
M1Open 23:31/03:31 là causal interval proxy, không actual tick fill. Dùng
America/New_York DST, nhãn theo exit date, skip halfdays theo calendar biết
trước; regular NYSE mask khác futures calendar phải giữ rõ. Không rollover
dates bằng UTC hoặc lấy last available endpoint thay phút đã định.

Cơ chế uncertainty resolution khác prediction bằng đầu/cuối ngày; không phải
đổi giờ để cứu R076/R078. Chưa calendar/endpoint source admission cho window
này; full-day canonical M1 đã có có thể reuse bằng four-quarter loader/proofs.
Phải kiểm day-boundary/DST/Sunday-to-Monday, BidAsk/grid/missing/coverage và
calendar census trước PnL. No trade rule không được dựa vào exit quality tương lai.
Không có VIX/news surprise input thì không mô phỏng conditional policy của paper.

Before numeric cần protocol: candidate, exact holding/cost/funding/coverage/gate/
controls và distinction futures→CFD. Same declared unit và fees có thể reuse
nhưng funding/rollover phải là explicit scenario, chưa verified broker terms.
Nếu component sống sau phí mới chốt risk/SL/time-fit/prop/holdout/forward; không
gọi market premium hoặc published headline là challenge-ready edge.

[NY Fed sr917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
landing/PDF mở được, nhưng các targeted clock searches bị timeout. Giữ partial
read; không gộp giờ/conditional rule chưa kiểm của Fed vào recipe Cambridge,
không claim full method đã đọc hoặc retune theo một paper khác sau outcome.

## 2. Oil/EIA: đã tìm full accepted method, chưa chuyển sang CFD

[Accepted manuscript của Wen và cộng sự](https://digital.library.adelaide.edu.au/server/api/core/bitstreams/aee73b81-111e-4bef-9e0e-7b1164f368a1/content)
dùng **USO ETF**, không WTI CFD. Predictor trên Wednesday EIA là 10:30–11:00;
trade 15:30–16:00. Tác giả nêu ETF roll/rebalancing có thể làm intraday returns
khác futures. Không lấy kết quả USO làm proof cho `lightcmdusd`. Chỉ đọc personal
reference theo repository notice, không import/redistribute paper code/data/text.

[Lịch EIA chính thức](https://www.eia.gov/petroleum/supply/weekly/schedule.php)
có release exceptions; trang hiện tại không đủ historical event census 2019/
2022. Không coi mọi Wednesday là ngày EIA đúng giờ hoặc gắn surprise labels khi
không có point-in-time releases/expectations. Calendar/news/ETF→CFD mapping và
target instrument/cost còn thiếu nên **không bulk fetch oil hoặc chạy PnL** ở đây.

Phần thiếu này là method/data gap, không bottleneck CPU/GPU. Chọn EU-open
baseline làm lát admission tiếp vì có primary clock và source đã sở hữu; oil
giữ queue có điều kiện. Source callbacks/package/account/provider/runtime không
đổi; own2025+, broker, paid service và quyền gửi lệnh vẫn giữ riêng.
