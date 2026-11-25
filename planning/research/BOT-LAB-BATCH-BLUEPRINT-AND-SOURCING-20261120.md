# Bot Lab · batch leaderboard, blueprint và lấy nguồn live

**Batch chạy được đầu-cuối. Inbox thật có 0 file, 0 ứng viên xếp hạng.** Rà kho metadata chưa phát hiện broker export đủ chuẩn. Kiểm tra công khai cho 0 hồ sơ được xác minh có đủ điều kiện nạp. Có hai blueprint từ fixture kiểm thử.

## Chạy batch

Chạy từ workspace root. Mỗi lần chọn thư mục output mới.

```powershell
uv run --project tooling/strategy-engines/observer --no-sync python -m tooling.ai_engines.bot_live_auditor --leaderboard-dir .runtime/bot-lab-batch
```

- **FTMO_LIVE_CANDIDATE_LEADERBOARD (MD/JSON)** ghi trạng thái từng file, lý do loại, cột thiếu, kịch bản DD/margin 0,50% và 1,00%, cash-only, cùng kiểm kỳ nghỉ và tin theo Standard funded. Chỉ xếp hạng hồ sơ qua Swing. Điểm lấy 80% lợi suất Swing/tháng của sổ yếu hơn tại 0,50% và 20% tương ứng khi Standard cũng qua.
- **BEHAVIORAL_BLUEPRINT (MD/JSON)** cho các hồ sơ qua cổng. Gồm tỷ trọng theo mã và net sau phí, phủ spec 13 mã, phân bố UTC và phiên có DST, thời gian giữ P25/P50/P75/P90, tỷ lệ trong ngày/qua đêm/cuối tuần, cadence theo tháng, payoff, SL/TP theo % giá và chi phí/positive price PnL. Nhãn thắng kế thừa Selective Win Diagnosis trên phần có đủ đường giá trước cutoff.

Cổng Swing áp cả 10k/25k 1:30, Standard 10k/50k 1:100. Kịch bản dùng chi phí đã khóa ở 36f1535 và spec 8fd77ef. Net dùng fills ghi trong log, spread nằm trong giá khớp. Các điểm equity dựng từ mark đủ phủ được so với daily 5% và static 10%. Standard cần lịch nghỉ >2 giờ và cửa tin đã ánh xạ theo mã. Đây là sàng lọc nghiên cứu ở các mốc quan sát. [FTMO Objectives](https://ftmo.com/en/trading-objectives/) · [FTMO tin tức](https://ftmo.com/en/faq/can-i-trade-news/) · [FTMO kỳ nghỉ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

**Holdout.** Trade có entry hoặc exit từ 01/01/2025 UTC được gắn bar_path_skipped_holdout_lock. Không truy vấn market store cho cả trade đó, kể cả tỷ giá quy đổi từ store. CLI vẫn tính thời gian, phiên, lot, R được báo, cờ từ log, cash và chi phí nếu đủ fills và quy đổi. Với log lệnh đóng thiếu đường nổi, cash không đủ để qua equity gate. Các khoảng thị trường đóng được loại khỏi mẫu số phút chỉ khi lịch có chứng cứ đủ phủ.

## Rà nguồn

Quét metadata **438 file** CSV/HTML/HTM tại research/bot_reverse_lab, education/real-example, .artifacts, .runtime, tmp và kho E:/…/ai-engine-jobs. Đếm theo tên và định dạng trong các root này. Không giải nén hoặc quét code tĩnh. Hai file trùng của Performance journal đã có bằng chứng thiếu lot, fills và close time từ e3f753f. Ngoài hai bản đó, không phát hiện theo metadata một broker export khả dĩ đủ chuẩn. Inbox thật trả 0 file.

Myfxbook Systems trả 403. MQL5 cho xem bảng thống kê và một số hồ sơ riêng lẻ, nhưng chưa xác minh tải được CSV đủ cột một cách công khai tại lượt này. Năm hồ sơ MQL5 bị loại theo DD hoặc tuổi lệnh. [Lọc 5 phút, bảng loại và hướng lấy mẻ đầu](LIVE-SIGNAL-SOURCING-PLAYBOOK.md).

## Kiểm chứng đầu-cuối

| Fixture | Kết quả | Bằng chứng |
| --- | --- | --- |
| clean_swing_survivor | PASS_SWING_CANDIDATE | Swing dương ở các sổ. Standard vướng kỳ nghỉ >2 giờ. |
| clean_swing_and_standard | PASS_SWING_AND_STANDARD | Qua Swing, lịch nghỉ và lịch tin Standard. |
| hidden_martingale_trap | REJECTED_TOXIC_OR_FTMO_BREACH | Tăng lot 5× sau hai lệnh thua. Net sau chuẩn hóa vẫn dương. |
| hidden_grid_ftmo_breach | REJECTED_TOXIC_OR_FTMO_BREACH | Averaging down, daily loss 18,12% ở 10k/0,50%, kèm vượt sàn lỗ tĩnh. |
| mixed_holdout_date_log | INSUFFICIENT_DATA_UNKNOWN | Một lệnh 2024 có giá. Hai lệnh 2025–2026 được chấm log-only. 10k/0,50% có +61,21 USD cash mô hình. Chưa đủ equity để pass. |

Chạy **63 test liên quan, 0 skip**. Chạy CLI thật trên bộ fixture và inbox rỗng. Test ghi mọi request market store, kiểm chỉ có EURUSD trước cutoff và dùng USDJPY hậu khóa để thử biên chuyển đổi. Hai log sau cutoff vẫn có cash/lot/phiên và dấu vết số dòng. OrderSend = 0. Holdout lock, pin Trader và WIP VI Dubber giữ nguyên.

[JSON đối soát](BOT-LAB-BATCH-BLUEPRINT-AND-SOURCING-20261120.json) · [SHA256](BOT-LAB-BATCH-BLUEPRINT-AND-SOURCING-20261120.sha256) · [Hướng dẫn inbox](../../research/bot_reverse_lab/inbox/live_signals/README.md).
Private manifest: bot-lab-batch-20261120/manifest.json. SHA256: cba79571e1cb321dbf48c873d1d02ce0476ad7a22cf9a054888faaf2ff1ef57f. Checksum các tệp tracked dùng byte LF chuẩn Git.
