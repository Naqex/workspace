# Tìm chiến lược theo bản đồ: ít nhánh khác nhau, đào sâu có giới hạn

12/11/2026. Owner hỏi nên thử một/nhiều setup, top-down/bottom-up, mượn
thuật toán để tìm nhanh hơn. **Đề xuất: top-down để tổ chức giả thuyết,
bottom-up để kiểm bằng chứng, sàng lọc nhiều tầng để phân bổ công sức.**
Đây là tư vấn tổ chức nghiên cứu, chưa phải protocol/batch hoặc bộ tìm kiếm
tự động mới. Không đổi các run, verdict, thresholds và exposure đã khóa.

## Đối chiếu 8 setup thực tế

Đã đối chiếu `us500_recent_setups.py`, frozen recent protocol, kết quả và
bản đồ cơ chế cũ. Chưa chạy similarity/correlation mới trên returns/traces.

| Họ | Nhánh con | Setup | Mức liên quan và khác biệt |
|---|---|---|---|
| Tiếp diễn theo giá | Vượt một mốc | RS01, RS03, RS04 | Kênh20nến, phiên trước, vùng mở cửa; cùng kiểu cược đi tiếp nhưng không exact duplicate |
| Tiếp diễn theo giá | Vượt mốc rồi thử lại | RS02 | Related RS01; thêm chuỗi retest/expiry có thể đổi trade set, không edge độc lập mặc định |
| Tiếp diễn theo giá | Hồi rồi vượt MA | RS06 | SMA20/80 và reclaim; vẫn cược tiếp diễn, giữ parent R123 negative |
| Quay lại | Phá rồi trở vào | RS05 | Chung vùng mở cửa với RS04 nhưng đi ngược cú phá; không cùng chiều exposure mặc định |
| Quay lại | Đi xa trung bình rồi trở vào band | RS07 | Mốc mean/SD khác, còn price-based; giữ recent negative/unknown |
| Quay lại | Hồi khoảng lệch mở cửa | RS08 | Gap/phiên trước; không cùng trigger/clock với band reentry |

Hai họ và sáu nhánh ở đây là **phân loại tổ chức**, không census toàn thị trường,
không xác nhận số cơ chế độc lập hoặc correlation. Một leaf có thể có nhiều
parent; dùng cây để đọc, graph/DAG cho lineage nếu cần. Cùng ý tưởng không
đồng nghĩa cùng trades; tên khác cũng không chứng minh diversification.

## Không nhầm trạng thái, thước đo, setup và lợi thế

Ví dụ “xu hướng” có các trục: tăng/giảm; mạnh/yếu; ngắn/dài; đầu/cuối phiên;
biến động cao/thấp. Các trục có thể đồng thời, không phải tất cả các nhánh loại
trừ nhau cần quét toàn tích Descartes.

- Trạng thái thị trường: bối cảnh muốn mô tả, chỉ được dùng thông tin đã có.
- Thước đo: MA, đỉnh/đáy, độ dốc, ATR... cách lượng hóa, chưa là nguồn lợi nhuận.
- Setup: tình huống vào; exit/sizing/cost tạo thành recipe được kiểm.
- Cơ chế giả thuyết: vì sao một hành vi có thể tiếp diễn/quay lại sau costs.
  Price proxy không tự chứng minh nguyên nhân order flow, inventory hay tin tức.

Top-down: mục tiêu/constraint → giả thuyết cơ chế → tình huống → luật cụ thể.
Bottom-up: từ dữ liệu/mẫu quan sát xây giả thuyết rồi kiểm trên dữ liệu khác.
Cả hai có thể hợp lệ hoặc overfit. “Chọn cái có lời ngay” chỉ là điều kiện
screening trên development, chưa chứng minh edge; top-down có câu chuyện đẹp
cũng không tự tốt hơn. Cần kết hợp lý do và kiểm chứng bác bỏ được.

## Quy trình đề xuất cho only-one US500/M15

1. Giữ một sản phẩm/timeframe và mục tiêu intraday/prop hiện có. Một strategy
   đem vận hành khác với nhiều giả thuyết offline để so sánh; không mở thị trường
   hoặc trading account để tạo breadth.
2. Gom lineage trước. Vòng kế tiếp đề xuất 2–3 nhánh có câu hỏi khác nhau thật,
   mỗi nhánh một recipe tối giản. Đây là giới hạn công việc theo case, không
   số lượng tối ưu được paper chứng minh. Ưu tiên tiếp diễn theo owner; một
   reversion/control để đối chiếu khi nó trả lời câu hỏi, không rerun negatives.
3. Khóa lý do, exact rule/exit/risk/cost, source/clock/window và điều kiện chuyển
   bước trước outcomes. Check dữ liệu/timing và cadence trước screening tài chính
   hữu hạn; cadence không thay net economics. Ít cơ hội không tự bác bỏ edge,
   nhưng có thể không hợp vai trò nguồn thu chính.
4. So đại diện trên cùng development và assumptions phù hợp, giữ theo năm/phiên,
   net expectancy, cost stress, losses/DD và uncertainty. Không loại từ một đoạn
   ngắn thua hoặc xếp unknown dưới zero. Entry/exit là một phần hypothesis;
   cùng exit mặc định chỉ là controlled comparison, không optimum mọi họ.
5. Chỉ 1–2 recipe có lý do/bằng chứng đủ mới nhận phần kiểm sâu và dữ liệu mới
   theo protocol riêng. Không bắt giữ đủ số nếu tất cả yếu/inconclusive. Đổi
   một thành phần có giả thuyết một lần, giữ parent và đếm thêm trial; không
   tự grid thêm MA/ATR/giờ/SL/TP để cứu đường equity.
6. Mỗi nhánh có budget/stop condition trước outcomes. Economic negative đúng
   recipe → park recipe; data/code defect → sửa đúng lỗi; thiếu mẫu → inconclusive.
   Muốn quay lại phải có thông tin/cơ chế/data mới cụ thể. Không xóa trialcount,
   không coi backtracking làm cửa sổ đã xem thành chưa xem.

Không từ failure một representative suy cả family hết cơ hội: chưa có bound
hợp lệ cho mọi child. Giữ notes lý do park để tránh vừa loại nhầm vừa cứu
nhánh vô hạn. Candidate không có survivor thì kết quả đúng có thể là không chọn.

## Mượn ý tưởng thuật toán đến mức nào?

| Ý tưởng | Áp dụng có ích | Giới hạn trong trading |
|---|---|---|
| Cây/graph | Nhìn nhánh, parent, biến thể, phần chưa kiểm | Không tự tạo hoặc chứng minh edge |
| Hash/cache/dedup | Reuse đúng inputs/rules/version; phát hiện kết quả/tín hiệu trùng | Hash inputs không tự phát hiện hai thuật toán khác chữ cùng ý nghĩa |
| Tìm rộng rồi sâu có ưu tiên | So ít representative, sau đó đào nhánh có giá trị thông tin | Không có priority score biết chắc future return |
| Successive halving / Hyperband | Mượn nguyên tắc bài rẻ trước, bài đắt sau, giữ fewer candidates | Không cắt cơ học nửa nhóm theo vài tuần PnL; market regimes/rankings không ổn định |
| Backtracking | Park hypothesis và chuyển nhánh có log | Không reset exposure hay giải quyết multiple testing |
| Branch-and-bound | Chỉ dùng nếu có outer bound hợp lệ cho đúng mô hình đã khóa | PnL parent âm không là upper bound của mọi child/future |

Sort chỉ sắp thứ tự theo thước đo đang có; ở đây giá trị cần biết là lợi nhuận
tương lai chưa biết, noisy/nonstationary, nên không có sort/đường tìm bảo đảm
winner hoặc nghiệm tối ưu toàn cục trong thời gian hữu hạn.

## Toán ưu tiên và dữ liệu chưa dùng

Ưu tiên net expectancy và uncertainty/dependence của nó; costs, tail/DD và
khả năng đạt mục tiêu quỹ là các cửa riêng. Khi đủ mẫu, block resampling theo
ngày/tuần có thể hỏi độ bất định dưới assumptions rõ; không tự gọi xác suất
pass đã hiệu chỉnh. Trial ledger + selection-aware review giữ cả negatives;
DSR/PBO/CSCV chỉ khi dữ liệu/assumptions phù hợp, không tem pass mặc định.

Bottom-up/data-mining được dùng trên development, nhưng mọi features/filters/
tham số lựa theo outcome tính vào search history. Validation phải đi sau freeze,
giữ thứ tự thời gian, và có gap/purge khi dependence/overlap cần. Không dùng
random split các trades/candles như IID để tuyên bố clean OOS.

Hiện 2025 đã dùng chọn và 2026 đã consumed cho RS01/RS07; không tái sử dụng
nhãn pristine validation. RS02 chưa có economic2026 không khiến toàn campaign
chưa biết thị trường2026. [Recent results](US500-RECENT-SCREEN-RESULTS-20261112.md)
và [gap probe](US500-RECENT-GAP-RESULTS-20261112.md) vẫn authoritative. Tổ chức
map tốt hơn không sửa được một phút nguồn thiếu hoặc biến modeled PnL thành known.

## Nguồn và phạm vi kiểm 12/11/2026

- [QuantConnect Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide):
  central hypothesis và cảnh báo tuning/theory drift. Các mốc số backtests/
  giờ của hãng là heuristics; không lấy làm chứng nhận hoặc hardcode vào project.
- [Bailey et al., PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf):
  thử/chọn nhiều trên cùng mẫu tăng false discoveries; một holdout đơn lẻ không
  tự giải quyết toàn selection process. Không tính PBO mới ở lượt này.
- [Li et al., Hyperband, JMLR](https://www.jmlr.org/papers/v18/16-558.html):
  adaptive allocation/early stopping cho HPO. Đề xuất dùng ý tưởng phân bổ công
  sức là suy luận của project; không chứng minh Hyperband tìm được profitable
  trading strategy hoặc speedup của case US500.
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html):
  chronological splits, gap; helper không tự xử lý financial label overlap,
  trial selection hoặc regime relevance. Không cài/thay engine/tool để trả lời.

Quyết định hiện tại: ghi đề xuất/lineage và bài học tìm kiếm; không backtest
mới, đổi rubric hoặc tạo Goal/skill/framework. Skills research/qualification
hiện có đã bao phủ các cửa cần. Nếu owner chọn hướng, exact study tiếp theo
vẫn cần registration riêng; không dispatch từ bản đồ tư vấn này.
