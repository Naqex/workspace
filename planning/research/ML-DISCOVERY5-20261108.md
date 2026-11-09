# Discovery5 — ML hữu hạn, khóa trước outcome

## Câu hỏi và phạm vi

Sau [Discovery4](DISCOVERY4-RESULTS-20261108.md), thử xem quan hệ có điều kiện
giữa returns/volatility/session có ích hơn các entry rules đơn giản không.
Đây là research hypothesis, không giả định ML tốt hơn. Hai chính sách thực và
hai shuffled-label controls là bốn trials có quan hệ, không bốn alpha độc lập.
Mục tiêu C1/C2 ở [campaign](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md) giữ nguyên.

Chỉ EURUSD H1 từ observed quote summaries đã source/hash-bound. Dùng Nov–Dec2022
làm lịch sử đặc trưng; 2023 là training và các quý2024 là chronological development
evaluation. Năm2024 đã consumed, tuyệt đối không gọi cleanOOS. Không đọc2025+.
Không broker/API/LLM trong numeric job; không mua challenge hoặc đổi risk.

## Quy tắc cố định

- Mỗi decision chỉ sau đóng một H1. Features từ đúng100 H1 đã đóng, không bịa
  nến thiếu. Return lags1/3/6/12/24/48/72 chia rolling mean14 true ranges;
  TR gồm gap với close trước. Các features còn lại: current range/body/upperwick/
  lowerwick chia TR14, close trừ SMA20/80 chia TR14, population std20 hourly
  changes chia TR14, vị trí close trong high-low20 (0,5 nếu phẳng), sin/cos giờ
  UTC và weekday, calendar gap giờ cuối capped168/168, spread cuối/TR14.
  21 features theo thứ tự trên; sin/cos weekday dùng period7. Khoảng cách SL
  bằng1,5×rolling mean14TR; **khác Wilder ATR** của Discovery4.
- Surrogate label BUY/SELL là net price PnL/25USD cho hypothetical entry tại
  first quote của H1 tiếp theo và exit tại first quote sau4observed H1 holding
  bars. Dùng lot sizing/core cost chuẩn; gồm spread, commission/slippage và
  scheduled financing. Label không mô phỏng SL; đây là dự báo return4H để tạo
  tín hiệu, không phải realized strategy PnL hoặc một engine execution mới.
  Label endpoint là actual exit quote timestamp; samples thiếu endpoint bỏ.
- Refits đúng01/01,01/04,01/07,01/10/2024 UTC. Training trailing12calendar months,
  chỉ samples có decision>=windowstart và **actual label endpoint<cutoff**.
  Không shuffle split hoặc preprocessing trên future. Training pairs giữ hai
  sides cùng hàng; shuffled control permutes hàng target bằng seed42+foldindex.
  Mỗi model chỉ available từ cutoff+3600s, không giả định training zero latency.
- Ridge alpha10 với StandardScaler fit training-only; RandomForestRegressor
  80trees/max_depth4/min_samples_leaf100/random_state42/n_jobs1, hai outputs.
  Không grid search, chọn feature/threshold hoặc tune sau numerical outcomes.
  Mỗi thuật toán có một control cùng config trained on shuffled target rows.
- Khi flat: chọn side có predicted net R lớn hơn side kia và >0,10R; bằng nhau
  thì flat. Không model hoặc <100past bars/zeroTR thì flat. Không reversal cùng
  event. Mở theo next observed quote; SL1,5TR14, exit khi4observed H1holding bars
  đóng (bar chứa fill tính1); gap không tự tăng count. Không TP hoặc trailing.
- Initial10k/planned25USD/oneposition và hai costs/financing giữ Discovery4.
  Screening dùng **cùng simulate_coarse**, không viết simulator mới. Kết quả
  H1không full tick internal risk/prop/DD. Inference stdlib từ JSON weights/trees,
  không pickle hoặc sklearn trong product runtime. RF dùng float32 input giống
  library. Pack bind recipe/protocol/data/source/cutoffs/scaling và identity.

## Thực thi và review trước/sau

Trước market outcome: kiểm feature future mutation/prefix, purge bằng actual
endpoint, train-only scaling, safe serialization/RFthreshold, label arithmetic
tính tay BUY/SELL + gap, state roundtrip và holding age. Test synthetic kiểm
native/development controls; không dùng market results để sửa expected.
H1cache guard giữ nguyên. Source snapshot và manifest SHA trước numeric job.
Dependency scikit-learn wheel/hash pin ở isolated `.runtime/research-ml`, BSD/MIT
license metadata được review; không thêm product dependency hoặc service nền.

Development2024 bốn chính sách×hai costs; lưu cả thất bại/control, từng quý và
cả năm, trades/exposure/concentration cùng timing/fit/predict/cache phases.
Một writer, status/progress/failure, attempt mới nếu lỗi material; không overwrite.
Không fake uncertainty từ overlapping labels; control chỉ diagnostic, không
statistical p-value hoặc bằng chứng0edge. Historical daily costs là scenario.

Ưu tiên tối đa2real policies có annual net dương ở cả hai costs và stress dương
ít nhất3/4quý (quarterly realised cash; floating boundary tách riêng nếu có).
Không ép có winner hoặc tăng risk để đạt target. Control tốt ngang/thắng real
là cảnh báo cần review, không đổi rule để cứu real. Survivors cần native tick
causality/risk review, exposed robustness, uncertainty/multiple trials và exact
holdout/forward protocol theo gates trước C1; coarse pass không hoàn thành C1/C2.
Nếu không có survivors, giữ failed trials và chuyển hypothesis có cơ chế mới.

Nguồn thiết kế đã đọc08/11:
[scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html),
[time-series CV](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split),
[Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html),
[RandomForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html).
Đây là phương pháp kiểm leakage, không bằng chứng ML forex có lời.
