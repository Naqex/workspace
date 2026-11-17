# S01 GBPUSD — kết quả và đối soát chi phí

Ngày17/11/2026. **Economics-v2 dương trong Development, đủ cổng sàng lọc
của S01 và đã qua đối soát độc lập đúng phạm vi. Chưa đủ điều kiện Challenge.**

Chiến lược cố định: GBPUSD quét biên vùng Á rồi đóng trở lại vùng trong
08:00–11:00UTC; natural SL ngoài nến H1 có đệm ATR; không TP cứng, đóng
trong ngày theo deadline đã khóa. Hai chiều BUY/SELL giữ nguyên. Không
thêm filter, thay risk hoặc tối ưu tham số trong lượt này.

## Những gì đã thay đổi

Nguồn ban đầu có hai giờ H1 không khớp tick. Source-v2 sửa đúng hai giờ
theo tick đã sealed, toàn300 tín hiệu/SL giữ nguyên;25.537.048ticks,
3.576giờ được admit. Original proof thất bại vẫn giữ. Đây là cùng vendor,
không xác nhận dữ liệu FTMO.

Oracle đầu tiên trỏ original proof nên dừng. Oracle v2 ngày17/11 dùng đúng
source-v2 và phát hiện **một false reject ở ngưỡng15%**: BUY19/06/2023,
SL12pip và phí1,8pip. Float cho `0.15000000000000002`, trong khi giá trị đúng
bằng15% phải được nhận.

Đăng ký [precision repair](SOLO-GBP-COST-GATE-CORRECTION-20261117.md) tại
commit `1900d19`, sửa code tại `9ca78a6`, rồi chạy `economics-v2` riêng.
Giữ nguyên toàn286 trade records và money cũ; thêm đúng một tín hiệu trên.
Lệnh thêm chạm SL, net **−162,51USD =−1,0834R** ở risk150. Không chọn
giữ kết quả cũ vì lợi nhuận đẹp hơn.

Đường dữ liệu:
sealed source-v2 →300 raw signals → exact cost gate →287 fills/13 rejects
→paired tick SL/time exits →lot/fees/net →GBP M1 curves →marginal screen.
Phần cuối cộng các đường M1 riêng, chưa là một tài khoản dùng chung vốn/risk.

## Kết quả cố định, sau phí đã khai báo

`1R =150USD` ở bảng GBP standalone. Phí FX là paired spread,
commission5USD/lot/vòng và slippage4USD/lot/vòng; không có rollover trên
đường giữ lệnh đã đăng ký.

| Chỉ số | 2022 | 2023 |
|---|---:|---:|
| Tín hiệu thô |147|153|
| Lệnh được nhận |142|145|
| Tỷ lệ giữ sau cổng phí |96,60%|94,77%|
| NetUSD |+767,60|+3.658,09|
| NetR |+5,1173|+24,3873|
| Mean netR/lệnh |+0,0360|+0,1682|
| Winrate |36,62%|34,48%|
| NetR nếu bỏ3 lệnh thắng lớn nhất |−11,5454|+0,3017|

Standalone GBP M1-envelope MaxDD là20,0957R, chưa phải exact intraminute
drawdown. Tại risk75, net đã đối soát là350,36USD/1.823,56USD hai năm; lot
flooring và cent rounding khiến kết quả không đúng bằng chia đôi risk150.

Không TP cứng nên một số ít lệnh thắng lớn có vai trò rất lớn. Năm2022
đặc biệt mỏng; số lệnh đủ cho screening không tự chứng minh edge bền.
Raw DAY markout trước SL vẫn âm ở cả hai năm. S01 là xác nhận inherited
stopped recipe trong ngoại lệ V3 và lịch sử112configs, không raw Stage-0 pass.

## Đóng góp dự kiến vào danh mục, chưa là account replay

Gold risk150, EUR risk75 và GBP risk75. Bảng dùng **common-R=USD/150**,
không cộng R theo risk riêng của từng lệnh.

| Gold cost model | A+EUR net / M1 envelope DD | A+EUR+GBP net / M1 envelope DD | Tương quan ngày GBP với A+EUR |
|---|---:|---:|---:|
| SYM−40/−40 |24,9543R /25,4046R|39,4471R /29,5560R|0,0682|
| ASYM−45/−5 |29,4719R /23,9186R|43,9647R /28,6926R|0,0677|

Tỷ số Net/DD tốt hơn nhưng DD tuyệt đối tăng. Không dùng tương quan thấp để
suy ra an toàn: có lúc nhiều tài sản cùng giữ lệnh và có thể dùng chung
exposure USD. Thêm GBP cũng thêm risk budget; không gọi return tăng là
hiệu quả miễn phí. Margin/news/source age và shared admission chưa đo ở đây.

## Kiểm chứng và các lần thất bại

- Code correction:61 S01 tests,60pass/1Windows symlink skip;21V3 regressions
  pass. Independent review2.790Fraction comparisons và metadata lineage đạt.
- Reviewer bắt được đường cấu hình cho phép thay baseline A/EUR; đã khóa
  về exact prior root/pins trước run. V1 vẫn chặn producer drift.
- Economics-v2 chạy48,32giây, bắt đầu02:16:02UTC, kết thúc02:16:50UTC.
  Result SHA256:
  `e9e877ac8c5f9faaf9b772b20e6faeee0f7f9f7034f68cd97451dc67712005f4`.
- Review ban đầu pin economics SHA `c91adcb…`; hash run `bd045b83…` bổ sung
  đúng một tên `assert_day_flat` vào AST guard. Reviewer đối soát delta byte
  và chấp nhận addendum khi run đã bắt đầu; không đổi hàm hay formula.
  Bài học vận hành: chốt final file hashes giữa writer/reviewer trước dispatch.
- Oracle v3 đã qua12nhóm synthetic và review script. Real audit kết thúc
  exit0 sau56,71giây, `CORRECTNESS_PASS_FOR_DECLARED_SCOPE`: đủ300raw,
  287fills/13rejects,3.576giờ tick độc lập, money150/75 và annual/side totals.
  Sáu GBP M1 arrays, mỗi array1.051.201points, sai lệch tối đa2,77e−13R,
  dưới tolerance khóa1e−8R. Post-run hashes giữ nguyên.
- Independent receipt SHA256:
  `f1f7e2ff77b6ed63fff6da2e59e917024b53cbc53933a45682e4c9a5e040b536`.
  Oracle không tái tính độc lập Gold/EUR baselines, correlation hoặc các
  admission/phase của danh mục; không mở rộng PASS sang các phần này.
- EUR boundary audit riêng:247raw/236fills/11rejects, toàn membership không
  đổi dưới integer gate; không đọc exit/PnL hoặc tái chọn EUR.

Scope source/cost/timing vẫn có giới hạn: không independent market feed,
không tái sinh lại signal/ATR bằng oracle này, không FTMO broker acceptance,
không mở2024–2026. Software tests không thay kiểm định ngoài mẫu.

Hậu kiểm kỹ thuật dùng `engineering-retrospective`: ưu tiên sửa lỗi tính
đúng và tránh chạy lại vô ích; chưa có bottleneck performance cần đổi engine.

| Vấn đề | Quyết định và kiểm chứng |
|---|---|
| Float làm lệch inclusive cost gate | Exact integer comparison, regression tại đúng witness và hai phía ngưỡng;2.790Fraction checks độc lập |
| Source code đã sửa nhưng receipt nguồn cũ còn giá trị | Reuse nguồn sealed bằng historical committed bytes đúng pin; code mới/pins/output riêng, không bỏ guard |
| Cấu hình baseline có thể đổi phép thử | Pin lại root và toàn baseline artifacts với v1, denial fixture trước numerical |
| Final guard thêm sau hash review | Giữ addendum chính xác; writer bàn giao final hashes rồi dừng ghi trước dispatch lần tiếp |
| Có cần chạy lại all campaigns hoặc tối ưu tốc độ? | Không; chỉ correction cohort300 và EUR boundary audit. Chưa có benchmark cũ cùng semantics nên không tuyên bố speedup |

Không thêm skill mới từ một lỗi đơn lẻ: workflow sửa lỗi, source lineage,
exact arithmetic và independent review đã có consumer/guidance. Regression
được đặt cạnh implementation; giữ skill/environment hiện có.

## Bước tiếp và điều còn thiếu

Sau oracle đầy đủ, tiếp [S02 shared-account replay](SOLO-THREE-ASSET-REPLAY-PROTOCOL-20261117.md):
108accounts theo fixed150/75/75, baseline cùng policy, annual/continuous
và monthly lifecycle, theo đúng thứ tự tick và quote age từng asset.
Không quét sizing hay mở2024 trong S02. Implementation/test đang thực hiện,
chưa có numerical S02; reuse Account/PortfolioAccount, không thay engine.

FTMO public refresh ngày17/11 chưa thực hiện được: web trả rỗng, HTTPS CLI
lỗi TLS, IAB không khả dụng. Báo cáo nguồn cũ giữ ngày kiểm10–15/11, không
đổi thành xác minh hôm nay. Trong source/docs/metadata đã kiểm chưa thấy
lịch selected news USD/EUR/GBP đầy đủ2022–2023; session calendar không thay
news calendar. Vì vậy funded/payout vẫn chỉ conditional khi chưa kiểm luật
đích, margin, feed, lịch tin và forward/reconciliation.

## Locator bằng chứng

Root riêng:
`E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/`.

- `S01-gbp-confirmation-source-v2/economics-v2/`: registration, execution
  start/finish, `run/result.json`, raw/trades và curves.
- Cùng source-v2: `independent-review-v2/REVIEW.md`, `gate-diagnosis.json`
  giữ lỗi thật; `gate-correction-independent-review/` giữ code review/hash
  addendum; `independent-review-v3/` giữ oracle mới.
- `three-asset-preparation/EUR-COST-BOUNDARY-AUDIT.json`, SHA
  `002b0802803746d3138094af6460d5f30b2961be0383a4a3f14d734242938393`.
- `target-spec-public/refresh-20261117.md` và browser-attempt receipt giữ
  failure hiện hành, không giả nguồn đã xác minh.

Trạng thái campaign thuộc [plan](SOLO-PROP-SYSTEM-PLAN-20261115.md);
report này không cấp quyền mua Challenge hoặc gửi lệnh.
