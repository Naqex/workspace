# Naqex Knowledge Vault — Bộ nhớ dài hạn, Sổ tay Chủ sở hữu & Kho Tri thức

Kho tri thức **Markdown-first** (Git-tracked, dễ đọc bằng mắt người & Obsidian, được lập chỉ mục tức thời qua SQLite FTS5 + Hybrid Vector tại `.runtime/knowledge/brain.sqlite3`).

## Phân quyền rõ ràng (không tạo bản sao cạnh tranh)

| Miền thông tin | Nơi sở hữu bản chính (Single Source of Truth) |
|---|---|
| **Chân dung, mục tiêu, tò mò, quyết định liên dự án của Owner** | `knowledge/owner/` (`PROFILE.md`, `CURIOSITY-LOG.md`, `DECISIONS-JOURNAL.md`) |
| **Tri thức tổng hợp ngoài trading (AI, công cụ, kỹ thuật, nghề nghiệp, hệ thống)** | `knowledge/topics/*.md` (1 chủ đề = 1 tài liệu sống, cập nhật delta) |
| **Nguồn thô mới kéo từ web/Reddit/CN/RU/PDF/YouTube** | `knowledge/inbox/` *(local ignored, chỉ chắt lọc phần có giá trị lên `topics/` hoặc `planning/research/`)* |
| **Protocol, kết quả backtest, biên nhận Holdout/Prop Trading** | `planning/research/` *(giữ nguyên chủ sở hữu, chỉ đặt link chéo từ `knowledge/`)* |
| **Kế hoạch thi công & trạng thái sản phẩm** | `planning/` và từng repo trong `projects/` |

## Lệnh thao tác nhanh (chạy từ workspace root)

```powershell
$rpy = 'D:\ANNAM\TradingWorkspace\.runtime\research-tools\Scripts\python.exe'

# 1. Nạp nhanh hồ sơ & định hướng Owner (< 0.1s — đầu mọi phiên mới)
& $rpy -X utf8 tooling/knowledge/brain_cli.py owner-brief

# 2. Lập chỉ mục tăng trưởng (SHA-256, ~0.25s nếu không đổi, ~8s build nguội toàn bộ 660 file)
& $rpy -X utf8 tooling/knowledge/brain_cli.py index

# 3. Tìm kiếm lai (BM25 + tách dấu tiếng Việt + Vector ngữ nghĩa + ưu tiên tài liệu Evergreen, ~35 ms)
& $rpy -X utf8 tooling/knowledge/brain_cli.py query "thi quy ftmo calmar holdout" --top 8
& $rpy -X utf8 tooling/knowledge/brain_cli.py query "owner risk tolerance" --domain owner

# 4. Ghi nhanh câu hỏi / sự tò mò / bài học mới vào Sổ tay Owner
& $rpy -X utf8 tooling/knowledge/brain_cli.py log-curiosity --topic "AI Agents" --question "..." --takeaway "..."

# 5. Nghiên cứu đa nguồn (arXiv/OpenAlex/GitHub/HN/QuantSE/Habr RU/CN/VI) & kéo bài sạch ra Markdown
& $rpy -X utf8 tooling/knowledge/research_cli.py search "volatility targeting portfolio" --sources arxiv,openalex,github,hn,quant,cn,ru --max 3
& $rpy -X utf8 tooling/knowledge/research_cli.py fetch "https://arxiv.org/abs/2304.04676" --mode directed --question "..." --save
```
