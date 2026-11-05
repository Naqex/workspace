# Time-fit 2023: exact windows và data preparation

Execution addendum 06/11/2026 cho [thiết kế time-fit](TIME-FIT-REGISTRATION-20261106.md).
Tài liệu trước là thiết kế: chưa khóa ngày, source/risk/cost nên chưa phải
registration đủ để chạy mô phỏng. Không sửa snapshot private cũ thành proof đã
freeze. Addendum này khóa phạm vi trước export mới; không chọn window theo PnL.

| Phần | Phạm vi |
|---|---|
| Start | 01/01/2023 00:00 UTC |
| 3 tháng | [01/01/2023, 01/04/2023) |
| 6 tháng | [01/01/2023, 01/07/2023) |
| 12 tháng | [01/01/2023, 01/01/2024) |
| Warmup | Reuse 01/11–31/12/2022, hash `77fcaa2722b336e729cb5fcce0b6f2aec1be9a652bbfdc7eabeb58a88a6f518a` |
| Nguồn | Dukascopy cache qua QDM `EURUSD_TICK_TW`, UTC millisecond/Bid/Ask |
| Exposure | Q1/2023 đã consumed; Q2–Q4 prior exposure unverified, không clean OOS |
| Holdout | Không mở 2024 hoặc 2025+; không tải lại full cache |

Chọn một start năm lịch, cả năm chứa ba horizon lồng nhau. Không coi là ba
sample độc lập. Một annual replay có thể phát snapshot causal ở mỗi cutoff;
không chạy ba annual jobs trùng prefix, không force-close cuối horizon.
Source và numerical risk/cost pin trong `TIME-FIT-HISTORICAL-20261106.json`
trước run sau data preflight.

## Việc được thực thi ở lát này

Kiểm CLI rảnh và metadata cache → export cả năm một lần → hash/row count →
kiểm toàn bộ timestamp/BidAsk/grid/order/quality và H4 bằng reader đã có →
giữ inspection cache có source/runtime binding. Reuse warmup đã hash. Không
gọi model/broker và không chạy simulation từ bước export/preflight.

## Điều kiện numerical và hạn chế

Chỉ dùng 5 candidate và risk/cost đã có, không tăng lot để đuổi target.
FTMO 2-Step Swing USD 10.000 là **declared offline profile**, không cần mua
challenge để chạy; current observed spec không chứng minh phí lịch sử. The5ers
chưa có account/program/cost pin nên chỉ giữ nghiên cứu, không chặn FTMO offline.

Numerical observation: 5 candidate giữ nguyên ID/rules; USD 10.000 giả lập,
25 USD/trade, internal daily 100/overall 500 USD, 1 vị thế. Reference: commission
2,50 USD/lot/side, slippage 0, financing buy 9,3/sell -0,31 USD/lot; stress:
commission giữ nguyên, slippage 0,00002/side, financing buy/sell 20 USD/lot.
Financing 22:00 UTC ngày làm việc, thứ Tư ×3: declared counterfactual, không
phải lịch broker 2023. Giữ gap, thứ tự quote và không đóng ép cuối mẫu.

Ba horizon lấy từ một annual replay/scenario. Primary: ending equity delta tại
mỗi cutoff; secondary: cash/floating/count/exposure/last quote age và internal
risk stop/minimum observed equity. Không gọi minimum equity là maximum drawdown.
Không candidate nào tự promote dù mọi horizon dương; kết luận tối đa là tiếp
nghiên cứu. Numerical timeout 2 giờ/worker, 4 giờ/batch, tối đa 4 worker trên
6 core; parallel-start dựa full-batch đã verified. Đây là hard ceiling, không ETA.
Không automatic retry; chỉ completed job hoặc sealed scenario reuse.

`prop_session.py` đã có target/minimum days/phase/reset/DST, nhưng pilot H4
hiện chưa nối evaluator này: ledger cũ không có equity tại mọi reset hoặc
đường intrabar đầy đủ. Vì vậy chưa được gọi annual PnL là full time-to-pass.
Muốn chuyển phase phải nối vào numerical state và tiếp tục với balance/risk/
financing đã reset đúng; không trừ target từ ledger cũ để giả lập phase 2.
Gap/news/inactivity/payout thiếu thì unknown; không kéo dài quarterly return.

Artifact/status ở private root:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-time-fit-20261106/execution-v1/`.
Receipt AI hiện hành giữ completion/checkpoint; tài liệu này giữ execution scope.
