# Policies có huấn luyện — nhánh kiểm riêng

Dùng khi học tham số từ dữ liệu, tạo labels hoặc triển khai trained inference;
không mở rộng scope/holdout hoặc mặc định ML tốt hơn fixed rules.

1. Freeze recipe và tính cả model/features/threshold/search/control variants
   vào trial history trước outcomes. Tách training/development/cleanholdout;
   chronological refit không làm data đã dùng để chọn thành cleanOOS.
2. Features chỉ từ thông tin có tại decision; label giữ **actual endpoint**.
   Loại samples có label chưa kết thúc trước cutoff, kể cả gap/weekend kéo dài
   quá số bars danh nghĩa. Fit scaler/imputer/featureselection training-only.
   Model availability gồm thời gian train/deploy, không backdate weights.
3. Labels có thể là surrogate; ghi khác biệt SL/holding/cost với policy thực.
   Dùng financial helpers hiện có và oracle nhỏ tính tay, không tạo simulator
   thứ hai chỉ để tính labels. Shuffled/control không tự là p-value hoặc winner.
4. Pack bind identity/features/source/data/protocol/cutoffs/preprocessing.
   Dùng local safe serialization; không load external pickle/joblib để tiện.
   Kiểm exported inference so library, kể cả dtype/split thresholds. Pack/state
   roundtrip và prefix/future-mutation tests phải giữ quyết định quá khứ.
5. Tách training deps khỏi execution runtime khi không cần ở đó; pin wheels/
   hashes/license theo supply-chain guard. Signal vẫn qua execution/risk owner;
   predicted return hoặc modelscore không là broker authority.
6. Giữ negative outcomes; lỗi material thì fix/rerun affected stage, đổi
   recipe theo outcome là trial mới. Không train/search mãi tới khi xanh rồi
   dùng cùng development làm validation. Qualification vẫn theo gates hiện có.

Đã thực thi nhánh này ở
[Discovery5](../../../../planning/research/DISCOVERY5-RESULTS-20261108.md):
train-only scaling/actual-endpoint purge/safe JSON float32 forest parity,
future mutation/state tests và shuffled controls. Hai real policies thất bại;
workflow đúng trong scope kiểm không đồng nghĩa có edge hoặc đã production.
Implementation reusable ở `tooling/ai-engines/forex_ml_study.py` và product
`forex_ml_candidate.py`; API mới cần contracts/guards/tests phù hợp trước dùng.
