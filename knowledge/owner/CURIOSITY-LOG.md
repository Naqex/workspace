---
doc_type: journal
domain: owner
updated_utc: 2026-11-23
---

# Sổ tay Tò mò & Câu hỏi Lớn của Owner (Curiosity Log)

> Ghi nhận các câu hỏi trọng tâm, mạch suy nghĩ và bài học owner quan tâm theo dòng thời gian. Mục tiêu giúp AI nhận diện chủ đề lặp lại, tránh giải thích lại cái cũ và chủ động đề xuất nghiên cứu đúng mạch quan tâm.

## 2026-11-23

- **[Quant & Prop Strategy]** *Làm sao vừa rút ngắn thời gian thi quỹ xuống `3–6` tháng mà không cháy tài khoản, và hồ sơ theo pha (P1 lãi mạnh → tắt vệ tinh khi Funded) có nên chia nhiều cấu hình theo thị trường không?*
  - **Kết quả đã xác minh:** Thiết kế 3 hồ sơ theo pha trên 4 quỹ (FTMO Swing/Standard, The5ers High Stakes/Hyper Growth); phanh tự động `AMBER/RED` + `Cluster-A Inverse-DD + Downside Vol Brake [0.55, 1.00]` kéo cháy P1 về `0.4%`, trần `1%/mã` bảo vệ luật *trade-idea bundle* FTMO với chi phí `0`. Xem [Pre-Holdout Audit](../../planning/research/PRE-HOLDOUT-READINESS-AND-BLINDSPOT-AUDIT-20261123.md).
- **[Statistical Rigor]** *Mở Holdout có dùng lại được không? Trước khi mở còn bỏ sót điểm mù nào từ cộng đồng thực chiến (MT5, FTMO, The5ers) không?*
  - **Kết quả đã xác minh:** Holdout chỉ mở **1 lần duy nhất**; đã kiểm toán toàn bộ `DSR(M=600)`, `Worst-5% Tail Correlation (-0.08..-0.11)`, bẫy `TimeGMT()` trong MT5 Tester, ngày lễ Mỹ đóng sớm, `ORDER_FILLING_*`, VPS restart, rồi mở Holdout `2025–2026` 1 lần → **`9/9` động cơ dương, `PORT_7E = GO (Calmar 1.75–1.94)`**. Xem [Holdout Verdict](../../planning/research/HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.md).
- **[Career / Quant Ceiling]** *Hệ thống hiện tại đã là Quant Trading chưa, đang thiếu gì, đẳng cấp cao nhất là gì, và một cá nhân IQ `115–120` dùng AI Agents có chạm tới được không?*
  - **Kết quả đã xác minh:** Xác định rõ tháp 5 tầng; cá nhân không nên đua HFT tầng 5 (rào cản vật lý FPGA/co-location), mà nhắm **"One-Person Quant Pod"** (vốn nhỏ, đa nhánh không tương quan). Đã dựng đủ 6 lớp Full-Stack thiếu (`PropGuard` v2, `AccountOrchestrator`, `TCA`, `CUSUM/SPRT`, `Ops Watchdog`, và Nhánh #2 Crypto Spot ghép đạt `Sharpe 1.91–1.99`). Xem [Quant Pod Brief](../topics/quant-pod-and-career-pyramid.md).
- **[AI Agent Workflow & Personal Memory]** *Làm sao tối ưu hóa quy trình research đa nguồn (EN/VI/CN/RU, Reddit, docs, cộng đồng) cho cả 2 chế độ (AI tự research & owner chỉ đạo), đồng thời tổ chức dữ liệu, sổ ghi chép, memory và tự động học hỏi đạt hiệu suất tốt nhất về lâu dài?*
  - **Kết quả đã xác minh:** Dựng `knowledge/` Markdown-first + `brain_cli.py` (SQLite FTS5 tiếng Việt + Vector RRF) + `research_cli.py` (`ddgs` + `trafilatura` + `markitdown` + Reddit `.json` + arXiv + GitHub + `yt-dlp`) + cài `rg`, `fd`, `jq` + tạo skill `research-and-memory-ops`. Xem [AI Research & Memory Stack](../topics/ai-research-and-memory-stack.md).
