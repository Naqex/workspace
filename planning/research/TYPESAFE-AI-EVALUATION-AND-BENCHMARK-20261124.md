---
doc_type: research-report
title: "TypeSafe AI (jev-1.14.0) Architecture Audit, Cookbook Mapping & Live Benchmark Evaluation (2026-11-24)"
date: 2026-11-24
status: verified
model_pinned: jev-1.14.0
order_send: 0
holdout_2025_sealed: true
supersedes_delta_from: planning/typesafe-research-2026-09-19/REPORT.md
---

# Đánh Giá Kiến Trúc, Cookbook & Benchmark Thực Nghiệm TypeSafe AI (`jev-1.14.0`) Cho TradingWorkspace (24/11/2026)

> **Kết luận điều hành (Trả lời thẳng câu hỏi "Có nên áp dụng không?"):**
> **CÓ — nhưng áp dụng CÓ CHỌN LỌC (`Hybrid: Code làm luật/tính toán + Jev làm phán đoán ngữ nghĩa/ảnh ở lớp phụ trợ`), TUYỆT ĐỐI KHÔNG đưa vào đường lệnh giao dịch lõi hay backtest nhân quả.**
> - **Ngon hơn rõ rệt khi áp dụng tại 4 điểm biên ngữ nghĩa & kiểm toán (off-path):** (1) Kiểm toán mã nguồn `.mq5` mở chống martingale/grid/SL=0 ẩn (`Regex 37,5% -> Jev 100%`), (2) Lớp chắn prompt-injection song ngữ Anh–Việt ở `chart_ai_contract.py` (`Regex 50% -> Jev 100%`), (3) Kiểm toán tự động điều khoản Prop Firm FTMO/The5ers/Topstep (`12/12`, độ lặp `100%`), và (4) Xác minh ảnh biểu đồ/học trading qua tính năng **Vision + `Box` mới trên `jev-1.14.0`** (`IoU = 0,83` ở `278 ms`).
> - **Chạy như bình thường (100% code deterministic) vẫn NGON HƠN tuyệt đối tại:** toàn bộ chiến lược giao dịch lõi (`PORT_7E`, `S2/S3A/S3B/S4`, `Naqex_PropGuard.mqh`, `NCO_CexCap25`), parser đọc JSON/CSV/HTML nội bộ (`cockpit/server.py`, `daily_ops_briefing.py`, `mt5_vs_python_reconciler.py`), và bộ lọc tín hiệu vào lệnh (Lab #6 đã chứng minh ML/model overlay không thắng trắng nguyên bản).

---

## 1. Delta Quan Trọng So Với Báo Cáo Cũ ([REPORT.md](../typesafe-research-2026-09-19/REPORT.md), 19/09/2026)

| Hạng mục | Thực tế ngày 19/09/2026 (`jev-1.13.0`) | Thực tế ngày 24/11/2026 (`jev-1.14.0`, phát hành 14/10/2026) |
|---|---|---|
| **Kiểu đầu vào & nguyên thủy** | Chỉ text (`Choice`, `Noul`, `Score`); báo cáo cũ ghi *"không nhận ảnh"* | **Hỗ trợ ảnh PNG/JPEG + nguyên thủy `Box`** (định vị tọa độ chuẩn hóa `[top, bottom, left, right]`) qua header `TypeSafe-Danger-Zone-Images: true` |
| **Độ trễ thực đo từ VN** | Trung vị `773 ms`, max `1.126 ms` | **Trung vị `287,9 ms`, P90 `314,3 ms`, max `369,0 ms`** (nhanh hơn **`2,68×`**) |
| **Giá & Context** | `0,042 USD / 1M` input tokens, output miễn phí | Giữ nguyên **`0,042 USD / 1M` input tokens** (output free); `64k` per-request / `32k` per-question (mở `262k` qua `Long-Context` nhưng kém chính xác hơn) |
| **Kỹ năng `typesafe-ai`** | Bản cũ `149` dòng | Đã cập nhật lên bản GitHub mới nhất `289` dòng (`C:\Users\MIIKEY\.gemini\config\skills\typesafe-ai\SKILL.md`, `audit-ai-environment.ps1`: `0 errors, 0 warnings`) |
| **Điểm yếu đã công bố (`jaggedness.md`)** | Kém toán/đếm/ngày giờ, nhạy injection | Xác nhận thêm: **Choice option-order bias** (hơi thiên vị phương án đầu), **Literal reading**, **`Box` luôn trả tọa độ ngay cả khi không có vật thể** (bắt buộc kẹp `Noul` đồng hành), và không huấn luyện lại trên dữ liệu khách hàng |

---

## 2. Prompt 1 — Rà Soát Toàn Bộ `TradingWorkspace`: Cơ Hội Thật vs Chỗ Không Nên Dùng

### 2.1. Bốn bề mặt đáng áp dụng TypeSafe (`High ROI`)

1. **Bộ kiểm toán EA `.mq5` mở (`tooling/ai-engines/mq5_whitebox_exporter.py::audit_open_source_mq5`):**
   - *Điểm yếu hiện tại:* Chỉ dùng regex từ khóa (`martingale|grid`, tìm chữ `sl`). Nếu EA ngoài viết nhân lot giấu tên (`prevVol * 2.0`), rải lệnh bình quân giá không ghi chữ `grid`, hoặc khai báo `double sl = 0.0;`, regex **lọt sạch**; ngược lại nếu đặt biến `InpForbidMartingale = true`, regex **báo oan**.
   - *Giải pháp TypeSafe:* Tách comment bằng code rồi gửi **1 request gom 4 `Noul` nguyên tử song song** (`loss_scaling`, `averaging_down`, `missing_nonzero_sl`, `external_dll_or_web`), kết hợp bảng chân trị (truth table) trong code + regex cứng cho `#import`.
2. **Ranh giới AI-on-Chart trong `projects/trader/foundation_v2` (`chart_ai_contract.py` & `semantics/ai_service.py`):**
   - *Hiện trạng:* `chart_ai_contract.py` (dòng 6–7) **đã xây sẵn hợp đồng fail-closed chờ adapter TypeSafe/Jev**, nhưng `semantics/ai_provider.py` mới chỉ có `OfflineProvider` và `FakeProvider`, còn bộ chặn prompt-injection (`_PROMPT_INJECTION_PATTERNS`, 5 regex tiếng Anh) dễ bị vượt qua bằng tiếng Việt hoặc diễn đạt vòng.
   - *Giải pháp TypeSafe:* Bổ sung `TypeSafeProvider` sau `AIService` với 3 `Noul` bảo vệ song ngữ Anh–Việt + Playbook search + Research rule draft (nhưng ranh giới quyền hạn vẫn nằm hoàn toàn trong backend không có tool đặt lệnh).
3. **Giám sát điều khoản Prop Firm (`FTMO / The5ers / Topstep`) & Intake Research:**
   - *Điểm yếu hiện tại:* Điều khoản quỹ thay đổi âm thầm theo quý (như Terms §11 The5ers, cấm tin đỏ `±2m`, cấm giữ qua đêm `15:10 CT` Topstep, trần consistency `50%`).
   - *Giải pháp TypeSafe:* Chạy 1 request gom 4–6 `Noul` song song mỗi tháng/quý để kiểm biến động điều khoản + dẫn chứng (`citation_check`) trước khi xuống tiền mua gói thi.
4. **Học đọc biểu đồ (`education/` + `chart-guided-tutoring`) & Tái xếp hạng Knowledge Vault (`tooling/knowledge/brain_cli.py`):**
   - `jev-1.14.0` đọc ảnh nến + định vị vùng `Box` ở `~280 ms` (`~4,3 VND`/ảnh), rất hợp làm bộ chấm nhanh bài tập vẽ vùng hỗ trợ/kháng cự/breakout trên ảnh giả định trong course.
   - Với `brain_cli.py` (`698` file / `4.555` chunk), thêm cờ tùy chọn `--rerank typesafe` (sau khi mở rộng Stage-1 shortlist từ `top_k=8` lên `20–30` bằng nới lỏng FTS5 `OR`) giúp tăng mạnh độ chính xác hỏi đáp tiếng Việt và **từ chối sạch (`no-match`)** khi câu hỏi không có trong kho.

### 2.2. Những chỗ chạy như hiện tại (Deterministic Code) NGON HƠN tuyệt đối

- **Đường lệnh & chiến lược lõi (`PORT_7E`, `exports/*.mq5`, `quant_factory/`, `projects/quant-trading`):** Tuyệt đối giữ `100%` code trắng nhân quả, `0` độ trễ mạng, `0` lỗi `429`, tái lập bit-for-bit khi kiểm toán.
- **Đọc báo cáo/telemetry nội bộ (`cockpit/server.py`, `daily_ops_briefing.py`, `mt5_vs_python_reconciler.py`):** Nếu muốn bỏ regex đọc bảng Markdown, cách đúng là xuất kèm file JSON sidecar (`0 ms`, `0 USD`, chính xác `100%`), không dùng AI.
- **`projects/integrations/TradingAgents/tradingagents/agents/schemas.py`:** Đã nâng cấp sẵn native structured output của Pydantic (`json_schema`/`response_schema`) + `_coerce_optional_float()`; chỉ cần cân nhắc TypeSafe `llm_guardrails` / `citation_check` nếu chạy batch khối lượng lớn để lọc nhiễu tin tức trước khi đưa vào LLM đắt tiền.
- **`projects/vi-dubber/`:** Không đụng trong phạm vi hiện tại (`translate.py` xử lý chuỗi/phụ đề thuần cục bộ; có thể khảo sát riêng nếu cần lọc ảo giác phụ đề sau này).

---

## 3. Prompt 2 — Kết Quả Benchmark Thực Nghiệm Trực Tiếp Trên `jev-1.14.0`

Toàn bộ `34` lượt gọi thật tới `POST https://api.typesafe.ai/v1/systemone` (pin `model = "jev-1.14.0"`, chỉ dùng dữ liệu công khai/giả định, `0` mật khẩu/tài khoản/Holdout `2025+`, lưu đầy đủ payload và kết quả tại `.runtime/typesafe-eval/benchmark_20261124.json`):

- **Tổng chi phí toàn bộ `34` lượt:** `47.397` input tokens + `2.912` output tokens (free) = **`0,001991 USD` (`~50,8 VND`)**.
- **Độ trễ đầu-cuối (VN -> API):** Min **`258,0 ms`**, Trung vị **`287,9 ms`**, P90 **`314,3 ms`**, Max **`369,0 ms`** (`34/34` HTTP 200, `0` lỗi).

| Thử nghiệm | Incumbent (Code hiện tại) | TypeSafe `jev-1.14.0` | Độ trễ TB | Nhận định kỹ thuật |
|---|---|---|---:|---|
| **Exp 1: Knowledge Vault (`brain_cli.py`, 6 câu hỏi VN + 2 câu không có trong kho)** | `0/6` Top-1, `1/6` Top-3 (`~47 ms`, không biết từ chối `no-match`); chỉ `3/6` lọt Top-8 | **Đưa `2/3` ca lọt shortlist lên Top-1 (`0` đảo đáp án khi đảo thứ tự chọn)**; từ chối đúng **`2/2` ca không tồn tại (`noul = 0,01–0,02`)** | `292 ms` | Phơi bày nút thắt thật: **Stage-1 recall của `brain_cli.py`** bỏ sót `3/6` câu hỏi tiếng Việt dài -> phải sửa Stage-1 FTS5 trước, rồi mới ghép `--rerank typesafe` |
| **Exp 2: Kiểm toán `.mq5` (`audit_open_source_mq5`, 8 mẫu sạch & độc hại ẩn)** | **`3/8` (`37,5%`)** — lọt cả `4/4` EA độc hại ẩn (martingale giấu tên, grid rải lệnh, `sl=0.0`, injection) & báo oan `InpForbidMartingale` | **`8/8` (`100,0%`)** — bắt sạch `0,94–0,99` mọi mẫu độc hại, `0` báo oan trên `3/3` EA sạch (gồm cả `Naqex_WB_E2/E4` thật!) | `286 ms` | **Thắng áp đảo.** Chi phí ~`0,00008 USD`/EA (`~2 VND`), ghép làm tầng 2 sau regex cứng là hoàn hảo |
| **Exp 3: Chặn Prompt Injection song ngữ EN+VI (`chart_ai_contract.py`, 10 ca)** | **`5/10` (`50,0%`)** — lọt **`5/6`** đòn tấn công tiếng Việt & diễn đạt vòng | **`10/10` (`100,0%`)** — `0,01–0,02` trên `4/4` câu hỏi hợp lệ (không báo oan "đóng lệnh bán"), `0,95–0,99` trên `6/6` đòn tấn công | `301 ms` | **Thắng áp đảo.** Khớp nguyên bản kiến trúc fail-closed của `chart_ai_contract.py` |
| **Exp 4: Kiểm toán điều khoản Prop Firm (`FTMO / The5ers / Topstep`, 12 tiêu chí × 2 lượt lặp)** | Kiểm tra thủ công | **`12/12` (`100,0%`)**; độ lặp lại 2 lần liên tiếp **`12/12` (`100%`)**, `max_repeat_prob_delta = 0,01` | `270 ms` | Rất ổn định để chạy job kiểm toán điều khoản quỹ định kỳ |
| **Exp 5: Vision + `Box` mới trên ảnh nến PNG (`640×400`, breakout có khung vàng vs sideway không khung)** | Chưa có (báo cáo 19/09 ghi Jev text-only) | Breakout: `brk=0,99`, `box=0,99`, `struct=bullish_breakout (1,00)`, **`Box IoU = 0,8297`** (`~5 px` sai số!); Sideway: `brk=0,05`, `box=0,05`, `struct=sideways_range (0,97)` | `281 ms` | **Xác nhận năng lực thị giác thật của `jev-1.14.0`** (`~4,3 VND`/ảnh); bắt buộc kẹp `Noul` vì `Box` vẫn trả tọa độ giả trên ảnh không có hộp |

---

## 4. Prompt 3 — Ánh Xạ TypeSafe Cookbooks (`docs.typesafe.ai/cookbooks`) Vào Codebase

| Cookbook chính thức | Mức độ phù hợp với `TradingWorkspace` | Vị trí áp dụng cụ thể |
|---|---|---|
| **[Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md)** | **Rất cao (Ưu tiên #1)** | Gom 4–6 `Noul` vào 1 call duy nhất cho `audit_open_source_mq5` (`.mq5` intake), `chart_ai_contract.py` (guard song ngữ), và kiểm toán điều khoản Prop Firm (đọc `state` 1 lần, rẻ và nhanh ~10×) |
| **[Guardrails for LLMs](https://docs.typesafe.ai/cookbooks/llm_guardrails.md)** | **Rất cao (Ưu tiên #2)** | Chặn prompt-injection song ngữ Anh–Việt & yêu cầu đặt lệnh trái phép ở `projects/trader/foundation_v2/trading_workspace_v2/chart_ai_contract.py` + `semantics/ai_service.py` |
| **[Re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md) & [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md)** | **Cao (Ưu tiên #3 — sau khi vá Stage-1)** | Thêm tùy chọn `--rerank typesafe` cho `tooling/knowledge/brain_cli.py` (sau khi nới lỏng truy vấn FTS5 Stage-1 lên `top_k=20–30`) + Playbook search trong `projects/trader` |
| **[Double-checking citations](https://docs.typesafe.ai/cookbooks/citation_check.md) & [Verify LLM outputs](https://docs.typesafe.ai/cookbooks/verify_llm_outputs.md)** | **Trung bình (Có điều kiện)** | Kiểm tra trích dẫn nguồn cho báo cáo AI tổng hợp (`research_cli.py` / `TradingAgents`) khi chạy tự động quy mô lớn |
| **[Function calling](https://docs.typesafe.ai/cookbooks/function_calling.md) & [Pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md)** | **Trung bình (Chỉ cho UI read-only/draft)** | Phù hợp cho thanh lệnh tra cứu read-only trong Control Room hoặc Research Rule Draft trong `projects/trader` — **tuyệt đối không nối thẳng sang lệnh broker** |
| **[OCR / Image Box cookbooks](https://docs.typesafe.ai/cookbooks/feeder_watch.md)** | **Tiềm năng cho Education** | Chấm nhanh vùng giá/cấu trúc nến trên ảnh giả định trong `education/` (`chart-guided-tutoring`) |
| **[Autoresearch feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md)** | **Không ưu tiên cho trading giá** | Không dùng để trích feature từ nến/số học (`jaggedness.md` xác nhận Jev kém số học); chỉ hợp nếu sau này khai thác dữ liệu văn bản (tin tức/biên bản FOMC) |

---

## 5. Đề Xuất Lộ Trình Tích Hợp Tối Thiểu (Nếu Chủ Nhân Duyệt Triển Khai)

Chưa sửa code sản phẩm trong lượt research này (giữ sạch 100% nhánh hiện tại). Nếu chủ nhân muốn tích hợp thật theo thứ tự hiệu quả cao nhất -> ít rủi ro nhất:

1. **Lát 1 (Nhanh nhất, rủi ro = 0, lợi ích ngay lập tức):** Nâng cấp `audit_open_source_mq5` (`--semantic-audit` tùy chọn, pin `jev-1.14.0`, mặc định vẫn chạy offline regex không cần key) + tạo CLI nhỏ `prop_terms_auditor.py` kiểm toán điều khoản FTMO/The5ers/Topstep trước mỗi đợt mua gói thi.
2. **Lát 2 (Cải thiện tìm kiếm kho tri thức tiếng Việt):** Sửa Stage-1 recall của `tooling/knowledge/brain_cli.py` (FTS5 OR-relaxation + tăng shortlist `top_k=20`), rồi thêm tùy chọn opt-in `--rerank typesafe` (có `Noul` `no-match`).
3. **Lát 3 (Gắn vào sản phẩm `projects/trader`):** Hiện thực hóa `TypeSafeProvider` sau `AIService` (`semantics/ai_provider.py`, mặc định tắt — chỉ bật khi cấu hình tường minh, pin `jev-1.14.0`, giữ nguyên hợp đồng `chart_ai_contract.py` với `broker_actions = False`).

---

## 6. Triển Khai Hoàn Tất Cả 3 Lát & Kiểm Chứng Live (`2026-11-24`)

Đã triển khai đủ **Shared Client + Lát 1 + Lát 2 + Lát 3** theo nguyên tắc opt-in mặc định tắt, fail-closed, pin `jev-1.14.0`, zero dependency ngoài và `ORDER_SEND_CAPABLE = False` / `broker_actions = False`:

1. **Shared client (`tooling/ai-engines/quant_factory/typesafe_client.py`):**
   - Pure-stdlib (`urllib.request`), pin `jev-1.14.0`, tự đọc `TYPESAFE_API_KEY`, chặn các key cấm (`secret`, `password`, `holdout`, `broker`, `order_send`, `mt5_login`, ...), lỗi transport/timeout/4xx/5xx luôn fail-closed (`TypeSafeClientError`), không bao giờ ép lỗi thành `"no"`.
2. **Lát 1 — MQL5 Intake Layer-2 & Prop Terms Drift Auditor:**
   - `tooling/ai-engines/mq5_whitebox_exporter.py`: thêm `semantic_audit: bool = False` vào `audit_open_source_mq5()` và CLI `--audit <file.mq5> [--semantic-audit]`. Strip comment MQL5 trước khi gửi 1 call 4-Noul song song (`loss_scaling`, `averaging_down`, `missing_nonzero_sl`, `external_dll_or_web`) rồi gộp bằng Truth Table tất định.
   - `tooling/ai-engines/quant_factory/prop_terms_auditor.py`: kiểm toán 1 call 6-Noul chống drift điều khoản so với baseline đóng băng cho `ftmo_swing`, `ftmo_standard`, `the5ers_high_stakes`, `topstep_50k`.
3. **Lát 2 — Nâng cấp `tooling/knowledge/brain_cli.py`:**
   - Vá Stage-1 recall tiếng Việt: lọc `QUERY_STOPWORDS` (Anh–Việt) + ưu tiên token số/miền trước khi cắt `toks[:18]`, mở rộng index thêm `knowledge/playbooks/*.md` & `planning/MORNING-BRIEFING*.md` (`699 -> 703` files, `4,604` chunks), mở rộng FTS5 `LIMIT 80`.
   - Thêm `--rerank {none,typesafe}` (mặc định `none`) với Companion Noul `has_relevant_doc` (`< 0.30 -> no_match: True`) + Noul chấm từng ứng viên + Choice Top-1 boost.
4. **Lát 3 — `TypeSafeProvider` trong `projects/trader` (nhánh nội bộ `feat/typesafe-jev114-provider`):**
   - `projects/trader/foundation_v2/trading_workspace_v2/semantics/ai_provider.py`: thêm `TypeSafeProvider` (mặc định `enabled=False`, `broker_actions=False`, giữ nguyên `OfflineProvider` và `FakeProvider`), guard song ngữ Anh–Việt 3-Noul (prompt-injection / đặt lệnh trái phép / đòi secret-holdout) + hỗ trợ `playbook_search`, `research_rule_draft`, `journal_review`, `chart_overlay`.

### Kết quả kiểm chứng (Offline + Live `jev-1.14.0`)

- **Superproject offline tests:** `pytest -vv tooling/ai-engines/tests/test_typesafe_integration.py test_knowledge_audit_upgrade.py test_mql5_parity_and_kit.py test_wave2_mt5_realtick.py` -> **`23 passed in 5.38s`**.
- **Trader `foundation_v2` offline tests:** `pytest -vv tests/test_typesafe_provider.py tests/test_chart_ai_contract.py tests/test_journal_context.py` -> **`22 passed, 8 subtests passed`**.
- **4 bài Live Smoke trên API thật `jev-1.14.0` (`ALL_4_LIVE_SMOKES_PASSED=True`):**
  - `brain_cli.py` (8 câu hỏi tiếng Việt): Stage-1 Top-1 tăng từ **`1/6 -> 2/6`**, bật `--rerank typesafe` tăng lên **`4/6` (`66.7%`)** (2 câu còn lại vẫn trả về tài liệu governance/prop liên quan), giữ **`2/2` (`100%`) negative abstention** (`no_match=True`, `noul=0.02`, độ trễ trung vị `~325 ms`).
  - `mq5_whitebox_exporter.py --semantic-audit` trên EA sạch `E2`: `CLEAN_FOR_PYTHON_REPLICATION`, `flags=[]`, xác suất rủi ro thấp (`0.04–0.13`).
  - `prop_terms_auditor.py` trên baseline The5ers: `PASS_MATCHES_BASELINE`, `drift=[]`, `296.99 ms`.
  - `projects/trader` `TypeSafeProvider` qua `AIService` với prompt-injection tiếng Việt: chặn fail-closed (`status=invalid_context`, `blocked=True`, `tries_override_rules=0.97`, `asks_live_trade_action=0.97`, `advisory_only=True`).
- **Sức khỏe hệ thống:** `brain_cli.py audit-data` (`0` broken links), `system_doctor.py --mode fast` **`PASS (9/9)`**, `Holdout 2025+ SEALED`, `0` secret leaks.
