---
doc_type: evergreen
domain: knowledge
topic: frontier-agent-harness-2026
updated_utc: 2026-11-27
untrusted_external_data: true
trust_tier: T1_PRIMARY_OFFICIAL
holdout_rows_analysed: 0
order_send_count: 0
sources:
  - "T1_PRIMARY_OFFICIAL: Lauren Tan (@poteto) pstack v0.15.48 (MIT) — https://github.com/cursor/plugins/tree/main/pstack"
  - "T1_PRIMARY_OFFICIAL: Lauren Tan Scoped Verification Example — https://github.com/poteto/verification-skill-example"
  - "T1_PRIMARY_OFFICIAL: OpenAI Engineering — Harness Engineering (https://openai.com/index/harness-engineering/)"
  - "T1_PRIMARY_OFFICIAL: Anthropic Engineering — Building Effective Agents, Effective Harnesses for Long-Running Agents, Demystifying Evals (https://www.anthropic.com/engineering/)"
  - "T1_PRIMARY_OFFICIAL: NousResearch/hermes-agent v0.23.4 (MIT) — https://github.com/NousResearch/hermes-agent"
  - "T1_PRIMARY_OFFICIAL: microsoft/RD-Agent v1.0.0 (MIT) — https://github.com/microsoft/RD-Agent"
  - "T1_PRIMARY_OFFICIAL: nautechsystems/nautilus_trader v1.231.0 / v2.0.0rc9 (LGPL-3.0-or-later) — https://github.com/nautechsystems/nautilus_trader"
  - "T1_PRIMARY_OFFICIAL: astral-sh/ruff 0.17.6 & astral-sh/ty 0.0.112 (MIT) — https://github.com/astral-sh/ruff, https://github.com/astral-sh/ty"
  - "T1_PRIMARY_OFFICIAL: duckdb/duckdb v2.0.1 (MIT), pola-rs/polars py-2.2.0 (MIT), numba/numba 0.68.1 (BSD-2-Clause), HypothesisWorks/hypothesis v6.170.17 (MPL-2.0)"
---

# Mẫu Thiết Kế Harness Engineering & Bộ Công Cụ Quant Tốc Độ Cao 2025–2026

> **Mục đích tài liệu bền vững (`evergreen`):** Chắt lọc các nguyên lý bất biến từ các hệ thống **Agent Harness Engineering** và **công cụ tốc độ quant** hàng đầu thế giới (`2025–2026`) để tra cứu nhanh qua `brain_cli.py`, giúp Naqex chọn đúng đòn bẩy có lợi ích thật (`0 USD`, không server, không phình to) và chặn đứng tâm lý chạy theo công cụ ồn ào. Xem bản kiểm toán đối chiếu đầy đủ ngày `27/11/2026` tại [FRONTIER-AI-AGENT-AND-QUANT-TOOLING-RADAR-20261127.md](../../planning/research/FRONTIER-AI-AGENT-AND-QUANT-TOOLING-RADAR-20261127.md).

---

## 1. Bảy Quy Luật Vàng Của Agent Harness Engineering (OpenAI + Anthropic + `@poteto`)

1. **Chuyển luật cấm tuyệt đối từ văn bản Markdown sang mã nguồn chặn cứng (`exit 2`):** `AGENTS.md` chỉ nên gọn như bản đồ điều hướng mở sâu theo nhu cầu; mọi bất biến (Holdout, OPSEC, đơn vị, copyleft, định dạng) phải chạy bằng hook cục bộ và cổng kiểm tra tất định (`check_architecture.py`, `.pre-commit-config.yaml`).
2. **Thông báo lỗi phải dạy agent cách sửa (*Instructional Linter*):** Thay vì báo lỗi chung chung, mỗi vi phạm kiến trúc in đúng `[ARCH-XX] <file>:<line> | <vấn đề> | REMEDIATION: <hành động sửa>` để vòng lặp tự sửa khép kín mà không tốn lượt hỏi lại.
3. **Cảm biến tất định chạy trước, LLM phản biện chạy sau:** Ưu tiên `ruff` (`~200 ms`), `ty` (`~400 ms`), `pytest` và `Hypothesis` (`0` token, độ chính xác tuyệt đối) trước khi gọi agent đọc-thuần phản biện (`adversarial-self-audit`).
4. **Tách vai trò *Lập kế hoạch -> Thực thi -> Kiểm định độc lập* và chia pha *Phân loại -> Tái lập -> Bản vá nháp*:** Tác giả không tự chấm đậu; bộ đánh giá đọc-thuần phải tìm phản ví dụ phá vỡ ít nhất `1` cổng trước khi cấp `PASS`; mọi tự động hóa dừng trước nút `Merge` vào `main`.
5. **Bản đồ hành vi khoanh vùng thay cho Wiki phình to (`Scoped Feature Map`):** Theo mẫu `poteto/verification-skill-example`, agent tốn token mỗi lần đọc lại wiki dài; hãy duy trì `feature_map.json` trỏ thẳng từng tính năng tới đúng lệnh kiểm chứng thực thi và cập nhật kèm mỗi PR.
6. **Nguyên lý bánh cóc (*Ratchet*) & Trạng thái JSON cho phiên dài:** Mỗi lỗi CI/kiểm toán mới phải biến thành `1` quy tắc `[ARCH-*]` hoặc `1` đột biến âm mới thay vì nhồi thêm dòng vào prompt. Dữ liệu bàn giao giữa các phiên dùng JSON có lược đồ chặt thay vì văn xuôi dễ bị LLM sửa hỏng.
7. **Đo độ nhất quán `pass^k` & Quản lý phiên bản Harness:** Đừng đánh giá agent bằng 1 lần ăn may (`pass@k`); hãy đo tỷ lệ đạt liên tiếp trên cả `k` lượt (`pass^k`), ghi rõ mã phiên bản harness đi kèm và rà soát định kỳ nhật ký thực thi thô (*transcript review*).

---

## 2. Quy Tắc Chọn & Chặn Công Cụ Quant Tốc Độ Cao Cho Solo Lab (3 Máy · 0 USD)

| Lớp công cụ | Chuẩn áp dụng tại Naqex | Kỷ luật sử dụng bắt buộc | Ranh giới loại bỏ (Anti-Bloat) |
|---|---|---|---|
| **Kiểm tĩnh Python** | **`ruff`** (`0.17.6`, MIT) + **`ty`** (`0.0.112`, MIT) | Bật cả `ruff check` và `ty check` (đã ghim cứng bản `0.0.x`) trên lõi `quant_core/`, `ops_cloud/`, `tooling/automation/` trong pre-commit và CI | Không dùng `ty` bản thả nổi không ghim phiên bản; không bật ép toàn bộ script lưu trữ `legacy/` ngay lập tức |
| **Lưu trữ & Truy vấn phân tích** | **SQLite WAL + `DuckDB 2.0.1`** (MIT, nhúng không server) + **Parquet / `.npz`** | Dùng `con.appender()` cho ghi lô lớn, `Agent Mode` khi truy vấn CLI, khóa chặn lệnh SQL ghi/nạp extension ngoài, đồng bộ cùng nhánh `DuckDB 2.0.x` (`v69`) giữa `PC Dev` và `X13` | Không bật chế độ máy chủ mạng `DuckDB quack`; không dựng Postgres/ClickHouse/Airflow chỉ để quản lý `~627 MB` dữ liệu M1 |
| **Biến đổi bảng lớn** | `DuckDB` SQL + `PyArrow` + `Pandas` (đã có sẵn theo `nautilus_trader`) | Giữ một đường ống sạch, luôn sắp xếp dấu thời gian tường minh trước khi cắt cửa sổ nhân quả | **Hoãn `Polars` (`py-2.2.0`)** cho tới khi dữ liệu vượt `> 10 GB`; cảnh giác động cơ streaming mặc định `Polars 2.0+` không bảo đảm thứ tự dòng nếu quên `.sort()` |
| **Mô phỏng đường đi nhanh** | **`Numba 0.68.1`** (BSD-2-Clause) trên mảng `float64`/`int64` liên tục | Bật `@njit(cache=True)`, tách rời vòng mô phỏng khỏi khâu nạp dữ liệu, kiểm đối chiếu với `decimal_oracle.py` | **Cấm `fastmath=True`** trong mã kế toán vốn, drawdown, trượt giá hay cổng quyết định (tránh làm hỏng phát hiện `NaN`/`Inf` chuẩn IEEE-754) |
| **Kiểm thử phá hoại & Máy trạng thái** | **`Hypothesis 6.170.17`** (MPL-2.0 dev-only) + Bộ đột biến cổng | Kết hợp `@given` bất biến số học với **`RuleBasedStateMachine`** mô phỏng chuỗi *mất kết nối API `None` -> khớp một phần -> qua nửa đêm Prague -> khởi động lại* | Không đóng gói `Hypothesis` vào bản phát hành thương mại; không thay thế bài kiểm tra đột biến bằng unit test happy-path |
| **Động cơ giao dịch 1 lõi** | **`NautilusTrader`** (LGPL-3.0-or-later, giữ pin `v1.231.0` chờ `v2.0.0` GA) | Dùng cho nhánh ngoài MT5 (`Crypto Spot` / `Carry` / `Own-Book` ở Mốc 2–3), tận dụng đối soát `ExecutionEngine` fail-closed, giữ wheel liên kết động & ghi `THIRD_PARTY_NOTICES.md` | Không nâng sớm sang bản thử nghiệm `v2.0.0rc9`; không viết lại EA Prop MT5 `PORT_7E` sang Nautilus |

---

## 3. Ranh Giới An Toàn Với Các Khung Agent Tự Trị Bên Ngoài

- **Nguyên tắc chuỗi cung ứng (`untrusted_external_data: true`):** Mọi kho agent bên ngoài chỉ được phép nằm ở dạng **submodule tham khảo chỉ-đọc** hoặc bài học thiết kế — **tuyệt đối không chạy daemon tự sửa bộ nhớ/skill** trên máy chứa khóa dự án hay máy vận hành bot.
- **Lý do thực tế (xác minh `27/11/2026`):**
  - `NousResearch/hermes-agent` có tốc độ đổi mã cực nhanh (`> 1.100` commit trong 4 ngày ở `v0.23.4`), cơ chế tự viết đè `MEMORY.md`/`SKILL.md` tiềm ẩn rủi ro nhiễm độc bộ nhớ dài hạn qua tiêm lệnh gián tiếp, và từng xuất hiện lỗ hổng thoát biên (`PYTHONPATH` leak `Issue #7071`, tiêm biến môi trường `CVE-2026-130164`).
  - `microsoft/RD-Agent` (`v1.0.0`) gắn chặt với Docker + Qlib cổ phiếu + chi phí API LLM cao, dễ làm nổ số phép thử `M` và phá hủy `DSR` khi đem chạy vòng lặp tự do lên chuỗi FX 7 năm.
  - Chép nguyên hàng chục skill từ các gói bên ngoài (như `59` skill của `pstack`) sẽ phá vỡ kỷ luật tối giản `18` skill khép kín và ngân sách ngữ cảnh của Naqex.
- **Tài liệu liên quan nội bộ:** [ai-quant-engineering-frontier-2026.md](ai-quant-engineering-frontier-2026.md) · [ai-research-and-memory-stack.md](ai-research-and-memory-stack.md) · [TOP1-SOLO-QUANT-MASTER-PLAN.md](../../planning/TOP1-SOLO-QUANT-MASTER-PLAN.md)
