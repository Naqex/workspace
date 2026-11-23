---
doc_type: evergreen
domain: knowledge
topic: ai-quant-engineering-frontier-2026
updated_utc: 2026-11-23
sources:
  - "T1: Microsoft Research (NeurIPS 2025, arXiv:2505.15155v2) — R&D-Agent-Quant: Data-Centric Factors and Model Joint Optimization"
  - "T1: Microsoft Qlib (github.com/microsoft/qlib, 50.5k stars) — AI-oriented Quantitative Investment Platform"
  - "T1: AlphaAgent (KDD 2025, arXiv:2502.16789v2) — LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay"
  - "T1: QuantaAlpha (Feb 2026, arXiv:2602.07085v3) — An Evolutionary Framework for LLM-Driven Alpha Mining"
  - "T1: FactorMiner (Feb 2026, arXiv:2602.14670v2) — A Self-Evolving Agent with Skills and Experience Memory for Financial Alpha Discovery"
  - "T1: Nov 2026 LLM Audit Trio (arXiv:2611.18934v1, 2611.19530v1, 2611.22177v1) — rò rỉ dữ liệu & beta vs alpha"
  - "T2: Cộng đồng Quant Trung Quốc (Zhihu / Quantide / QuantaAlpha) — đánh giá triển khai thực tế Qlib + RD-Agent"
---

# Biên giới Kỹ thuật AI Quant 2025–2026: Chắt lọc Kiến trúc Gọn cho `quant_factory/`

> Thay vì cài nguyên hệ sinh thái nặng hàng GB (PyTorch + GPU + Qlib server + Docker), tài liệu này **giải phẫu 5 hệ thống AI-Quant hàng đầu thế giới (`RD-Agent-Q`, `Qlib`, `AlphaAgent`, `FactorMiner`, `QuantaAlpha`)** từ nguồn học thuật EN + cộng đồng CN, chỉ giữ lại đúng các **ý tưởng kiến trúc nhẹ, tái sử dụng trực tiếp ngay trên dây chuyền 4 lớp `quant_factory/` (NumPy + Numba + JSON + `.npz`) của Naqex** mà không tăng một chút bloat nào.

---

## 1. Đồng thuận T1 (2025–2026): Đâu là chỗ LLM tạo giá trị thật trong Quant?

Ba bài kiểm định arXiv tháng `11/2026` (`2611.18934`, `2611.19530`, `2611.22177` — đã tóm tắt tại [Bản đồ Cạnh tranh Quant 2026](solo-ai-quant-competitive-landscape.md)) đã khép lại cuộc tranh luận:
- **Thất bại:** Cho LLM đọc giá/tin rồi tự bấm nút Buy/Sell (`LLM-as-Trader`) → `98%` bài báo bị rò rỉ cutoff, `78%` lợi nhuận chỉ là Beta ăn theo thị trường, không ổn định giữa các lần chạy.
- **Thành công rõ rệt:** Dùng LLM làm **Đội ngũ R&D tự động tạo giả thuyết có căn cứ kinh tế, viết mã kiểm thử nhân quả, đọc báo cáo thất bại và chống trùng lặp (`LLM-as-Quant-Researcher & Auditor`)**, trong khi toàn bộ việc tính toán và khớp lệnh chạy bằng **code tất định tốc độ cao (Numba/C++/MQL5)**.

---

## 2. Giải phẫu 5 hệ thống biên giới (`EN + CN`) & Phần ĐÁNG COPY vs NÊN BỎ

| Hệ thống (Nguồn T1) | Đột phá kiến trúc cốt lõi | **NÊN COPY thẳng vào `quant_factory/` (Nhẹ, Zero-Bloat)** | **KHÔNG NÊN COPY (Quá nặng / Sai quy mô cá nhân)** |
|---|---|---|---|
| **1. Microsoft Qlib** (`github.com/microsoft/qlib`) | Chuẩn hóa kho dữ liệu nhị phân cột (`bin`/cache), biểu thức nhân tố nhất quán, tách bạch *Data Layer → Model/Signal → Portfolio Backtester → Recorder*. | **Hợp đồng dữ liệu tách lớp & cache nhị phân tốc độ cao** (Naqex đã hiện thực gọn gấp 10 lần bằng `.npz` zero-pickle trong `data_store.py` chạy `0,28s` cho 9 động cơ, kèm SHA-256). | Không cần cài nguyên Qlib + LightGBM/PyTorch cho danh mục `7–12` tài sản FX/Index/Crypto (Qlib thiết kế cho rổ `300–5.000` cổ phiếu CSI300/S&P500). |
| **2. RD-Agent-Q** (*NeurIPS 2025*, `arXiv:2505.15155`) | Vòng lặp 2 pha **Research (giả thuyết) ↔ Development (`Co-STEER` viết & sửa code)** + bộ lập lịch **Multi-Armed Bandit (MAB)** phân bổ ngân sách thử nghiệm giữa *tìm tín hiệu mới* và *tối ưu ghép danh mục/mô hình*. | **Phân tách rõ vòng lặp *Hypothesis → Spec JSON → Numba Eval → Verdict* và cơ chế phân bổ ngân sách R&D có giới hạn** (dừng ngay khi một họ chiến lược có `0/N` ứng viên sống sót — như Naqex đã đóng dòng ORB ở Pass 13 và FX single-asset breakout ở Pass 25). | Không chạy vòng lặp vô tận không có đồng hồ đếm đa phép thử (`DSR`/`BH-FDR`), vì `M` phình lên hàng nghìn sẽ giết sạch ý nghĩa thống kê trên chuỗi 7 năm FX. |
| **3. AlphaAgent** (*KDD 2025*, `arXiv:2502.16789`) | Ba vai trò tách biệt (*Idea → Factor → Eval*) + **Kiểm tra độ nguyên bản bằng cây cú pháp (AST Originality Regularizer)** và phạt độ phức tạp công thức để chống suy giảm alpha (*alpha decay*). | **Cổng chống trùng lặp cấu trúc & giới hạn độ phức tạp tham số (`<= 3–4` tham số tự do, bắt buộc `6/9` ô 2D ổn định):** Ngăn AI biến tấu lại cùng một công thức `ATR Breakout` bằng cách đổi tên biến! | Không cần xây bộ phân tích AST phức tạp cho biểu thức Alpha158 cổ phiếu; với white-box Naqex, kiểm tra bằng **tương quan chuỗi R hàng ngày (`|r| < 0,25`) + đối chiếu Sổ Giả Thuyết (`alpha-hypothesis-ledger.md`)** nhanh và sát thực tế hơn. |
| **4. FactorMiner** (*2026*, `arXiv:2602.14670`) | **Kiến trúc Skill mô-đun (Modular Skill Architecture)** + **Bộ nhớ Kinh nghiệm có Cấu trúc (Structured Experience Memory)** chạy theo vòng **Ralph Loop (`Retrieve → Generate → Evaluate → Distill`)** để thoát *"Biển Đỏ Tương Quan" (Correlation Red Sea)*. | **100% tương thích với Naqex!** Naqex đã có sẵn bộ skill mô-đun (`.agents/skills/`) và `brain_cli.py`; bước nâng cấp sống còn chính là biến lịch sử thất bại/thành công thành **Experience Memory có cấu trúc** ([Sổ cái Giả thuyết Alpha](alpha-hypothesis-ledger.md)) để AI luôn chạy `Retrieve` trước khi `Generate`! | Không lưu hàng nghìn yếu tố nhiễu vào kho; chỉ chắt lọc bài học cấp *họ cơ chế* (*Success Patterns* & *Failure Constraints*). |
| **5. QuantaAlpha** (*2026*, `arXiv:2602.07085`) | **Kiến trúc 3 tầng Harness (`Lead` hoạch định → `N × Miner` song song → `Reviewer` kiểm toán chéo)** + **Tiến hóa cấp Quỹ đạo (Trajectory-level Mutation/Crossover)** + **Factor Wiki có cấu trúc**. | **Mô hình 3 tầng `Lead / Parallel Miners / Independent Red-Team Reviewer`** (đúng mô hình Swarm mà owner đang làm chủ!) + **Đột biến có kiểm soát trên giả thuyết gốc** (ví dụ từ `E2 USDJPY Expansion` đột biến sang `E3 GBPUSD + Vol-High` và `E6 EURJPY + Vol-Compression`, có giải thích kinh tế rõ trước khi chạy). | Không chạy tiến hóa di truyền (Genetic Crossover) mù trên hàng nghìn tổ hợp công thức không có ý nghĩa kinh tế — dễ gây overfit cục bộ (*noise chasing*). |

---

## 3. Năm nâng cấp Gọn–Nhẹ áp dụng trực tiếp vào `tooling/ai-engines/quant_factory/`

Không thêm bất kỳ thư viện nặng hay daemon nền nào — chỉ áp dụng `5` mẫu thiết kế đã kiểm chứng từ 5 hệ thống trên vào chính ngăn xếp hiện tại của Naqex:

### 3.1. Vòng lặp *Ralph Loop* cho mọi Pass nghiên cứu tương lai (từ `FactorMiner`)
Trước khi mở bất kỳ Pass khám phá mới nào (`Pass 29+`), AI bắt buộc đi qua 4 bước có cổng chặn:
1. **`Retrieve` (Tra bộ nhớ trước):** Chạy `brain_cli.py query` + đọc [alpha-hypothesis-ledger.md](alpha-hypothesis-ledger.md) để kiểm tra họ giả thuyết định thử đã từng bị bác bỏ ở Pass `1..28` chưa (ví dụ: không bao giờ thử lại *M15 Liquidity Sweep*, *US500 Overnight FTMO Swap*, hay *Positive-Swap Donchian FX*).
2. **`Generate` (Đề xuất có lý do kinh tế):** Mỗi giả thuyết mới phải ghi rõ *Đối tác kinh tế là ai* ([Sổ tay Vi cấu trúc](market-microstructure-and-economic-edge-handbook.md)), có `<= 4` tham số và đăng ký trước vào `Protocol` trước khi đụng dữ liệu.
3. **`Evaluate` (Đo nhanh bằng Numba + Cổng Pháp y):** Chạy trên `.npz` zero-pickle + Numba JIT (`prop_engine.py`, `eval_pipeline.py`), bắt buộc qua cả Cụm A → Cụm B mù, stress phí, mặt phẳng 2D, `BH-FDR` / `DSR`, và **đo tương quan với toàn bộ lõi hiện có (`|r_core| < 0,20`)**.
4. **`Distill` (Chưng cất kết quả âm lẫn dương):** Dù đậu hay trượt, ghi 1 dòng chuẩn hóa vào [alpha-hypothesis-ledger.md](alpha-hypothesis-ledger.md) và chạy `brain_cli.py index` để toàn bộ các phiên AI tương lai đều nhớ.

### 3.2. Cổng Phản biện Độc lập (*Adversarial Reviewer Harness* — từ `QuantaAlpha` + `AlphaAgent`)
- Tách hoàn toàn Agent đề xuất/viết code (`@quant-rnd`) với Agent phản biện/kiểm toán (`@verifier` / `@risk-auditor`).
- Danh sách soi mặc định của Reviewer: *(1) Look-ahead bias (`<= t` cho lệnh `t+1`)*, *(2) Đếm đúng tổng số phép thử `M` trong BH-FDR/DSR*, *(3) Phí/trượt giá/swap đúng thực tế sàn đích*, *(4) Tương quan đuôi 5% ngày xấu nhất (`Worst-5% Tail Corr`)*, *(5) Giữ nguyên kết quả âm không giấu*.

### 3.3. Lập lịch Ngân sách Thử nghiệm theo Họ (*Hypothesis-Family Bandit Budget* — từ `RD-Agent-Q`)
- Vì chuỗi dữ liệu lịch sử hữu hạn (`2018–2024` = `7` năm), mỗi phép thử thêm đều làm tăng phạt chọn lọc (`DSR`).
- Áp dụng ngân sách cứng **tối đa `20–40` cấu hình cho mỗi họ cơ chế mới**: nếu `0` ứng viên vượt qua Cụm A và kiểm tra độ nhạy 2D (`>= 6/9` ô), **đóng vĩnh viễn nhánh đó** (*Exhausted*) và chuyển ngân sách sang lớp tài sản/nhánh trực giao mới (như Crypto Spot thanh khoản trượt, Futures CME, hoặc Basis/Funding trung hòa) thay vì cố "vắt nước từ đá".

### 3.4. Kiểm toán Vệ sinh Kho Tri thức Tự động (`brain_cli.py audit-data`)
- Để **Experience Memory** thực sự đáng tin sau nhiều tháng cộng dồn hàng chục báo cáo, `brain_cli.py audit-data` được nâng cấp thêm 2 lớp kiểm định tự động (không tốn GPU, chạy `< 0,2s`):
  1. **Phát hiện liên kết Markdown tương đối bị gãy (`broken_knowledge_links`):** đảm bảo mọi link chéo từ `knowledge/` sang `planning/research/` hay `tooling/` luôn trỏ đúng file thật.
  2. **Phát hiện tiêu đề chủ đề gần trùng lặp (`near_duplicate_topic_headings`):** dùng so khớp tập token không dấu tiếng Việt (`Jaccard similarity >= 0,70`) trên các file trong `knowledge/topics/` để chặn AI tạo ra 2 tài liệu lặp nội dung cạnh tranh nhau.

### 3.5. Nguyên tắc "Đơn giản hóa trước khi phức tạp hóa" (Chống bẫy ML cho dữ liệu ít mẫu)
- Trên cổ phiếu Trung Quốc/Mỹ (`3.000` mã × `10` năm = hàng triệu quan sát cắt ngang), LightGBM/Neural Net trong `Qlib` phát huy sức mạnh.
- Trên **FX/Index Intraday Prop (`7–12` mã) và Crypto Spot (`10–30` mã thanh khoản cao)**, số quan sát độc lập theo ngày chỉ cỡ vài nghìn: **quy tắc white-box ít tham số + quản trị rủi ro đa động cơ + phanh biến động 1 chiều** thắng áp đảo mô hình học sâu hộp đen cả về độ ổn định ngoài mẫu lẫn khả năng giải trình tuân thủ luật quỹ (`FTMO` / `The5ers`).
