# Discovery5 ML — kết quả và hậu kiểm

**Không có ứng viên đi tiếp từ hai model thực.** Frozen design ở
[protocol](ML-DISCOVERY5-20261108.md), root commit91d83f4 trước train; implementation
Traderdb05ef54/workspacecd3e5d7. Năm2024 là consumed development, không cleanOOS.

| Chính sách | Net chuẩn/cao USD trên10k | Lệnh đóng | Quý có closed-trade net dương khi stress |
|---|---:|---:|---:|
| Ridge |−175,30 / −593,70|475 /475|0/4|
| Forest |−1375,12 / −1537,26|263 /263|1/4|
| Ridge shuffled-control |+143,33 / +40,18|120 /120|2/4|
| Forest shuffled-control |−186,84 / −250,13|67 /67|1/4|

Ridge và forest-control còn một position cuối mẫu; floating có trong net.
Shuffled không là candidate được giữ: nó cho thấy một backtest dương đơn lẻ
có thể xuất hiện khi bỏ quan hệ features/target. Không suy p-value hoặc kết
luận mọi ML vô dụng từ bốn trials. Không tăng risk/tune để cứu model.
Coarse không internal brake/prop/full tickDD; net âm vượt500USD không là đường
account native đã được duyệt vận hành.

## Độ đúng trong phạm vi kiểm

| Lát | Evidence | Gap/decision |
|---|---|---|
| Causality |17product/coarse tests+4subtests;5training tests trước outcome: future mutation, actual-endpoint purge, model availability+1hour, train-only scaler, restored state, position identity | Không model/threshold search sau outcome |
| Model export |JSONweights/trees, float32 forest inputs; so toàn training rows trong16fits với library <=1e-10; synthetic split-boundary cases <=1e-12 | Không pickle; scientific libs chỉ isolated research venv |
| Labels |BUY/SELL net return4observed hours, manual price/spread/commission fixture; financing core | Surrogate không SL; strategy có SL, không nhầm label với realized performance |
| Accounting |8/8cash, equity/floating, tradecount, model digest/purge packs được kiểm riêng | Không là native tick/prop qualification |
| Selection |Hai real versions đều không đạt frozen screen; giữ outcomes/control/history | C1chưa đạt, không đề xuất challenge |
| Performance |34,3266s toàn load/features/16fits/8annual screens/export checks | Chưa timer riêng từng fit; đủ nhanh, chưa có lý do tối ưu kernel/GPU |

Private artifact:
`E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\challenge-discovery4-20261108\execution-v1\ml-discovery5\attempt-v1`.
Config/source snapshot/protocol/packs/results và independent-accounting-review
giữ provenance; zero broker/LLM calls trong job. Không numerical worker còn chạy.

Tiếp nghiên cứu source-backed fixing windows với clock/exit/holding rules khóa
trước numerical outcomes. Không lặp train cùng source/data để tìm PnL đẹp.
