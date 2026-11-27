# Vào sau phá kênh hay chờ hồi: đối chiếu cùng giờ nhận cú phá

12/11/2026. Owner giao testing hai cách vào và hỏi ATR/kênh có đổi không.
Theo [hướng continuation](US500-HIERARCHICAL-SEARCH-REVIEW-20261112.md).
Phạm vi offline 2022–2025 đã consumed; không mở RS02/2026 hoặc fresh holdout.

## Lý do và lịch sử trước lượt mới

Saved-book review16sổ RS01/RS02 reference/stress đã chạy0,671s, có seal/cash/
Fraction/signal-parent checks; giữ fullnet N/A khi có gap. Chưa rerun financial.
Đã xác minh331retestsignals cùng parent đầu/ngày, side, frozenATR và muộn15–60phút.

Code/protocol cũ còn khác cutoff: RS01 nhận firstbreak10–15NY, RS02 chỉ
arm10–14NY để chờ confirm tới15NY. Không gọi chênh lệch cũ là chỉ do entrytiming.
Đăng ký hiện tại là **methodology repair sau khi đã biết kết quả**, không
preregistered/unseen discovery hoặc tuning tham số để chọn winner. Đếm prefix
đã biết trước lượt này: common14 RS01 có165/158/148/153signals năm2022–25;
lateexcluded30/16/23/23. Không dùng outcome của những trade đó để đặt cutoff.

## Hai recipe và những gì giữ cố định

- **BR01-common14-v1**: lấy đúng firsttrigger/ngày của RS01 đã khóa; chỉ
  nhận khi thời điểm đóng nến xác nhận≤14:00NY inclusive. Không tìm trigger
  thay thế sau khi bỏ một signal. Entry market ở phút sau decision.
- **RS02 v1 giữ nguyên**: cùng parent phá kênh≤14NY, freeze level+ATR;
  nến sau chạm vùng quanh level±0,10ATR và đóng trở lại phía phá ngoài đệm,
  tối đa60phút/15NY; vào phút sau confirm. Không limit fill ngay khi chạm vùng.
- Kênh = high/low20M15 trước currentbar; ATR14Wilder từ closedbars, actualATR
  thay đổi theo giá. Breakbuffer0,10ATR; retestwidth0,10frozenATR; stop2ATR;
  không grid lookback/ATRperiod/buffer/width/stop. RS02 level giữ tại cú phá,
  không dời theo kênh mới. BUY/SELL, một attempt/ngày, không add-on/martingale.
- Reuse cashNY/DST, nativeNautilus1.231.0, BidAsk/zero declared commission,
  reference/stressslip0,25/0,75point mỗi fill, quantity grid/lot/margin,
  plannedstoprisk≤25USD/reset10k, timeexit15:30/fill15:31 như parent.
- Held gaps/missing/open giữ unknown; không backfill hay forcedclose. Đây là
  M1envelope modeling, không targetbroker/tick/prop acceptance.

## Thực thi, kiểm và quyết định

1. Output mới `execution-v1/us500-entry-common14-v1`; manifest, snapshots,
   PID/status/events/CANCEL/deadline600s. Source/protocol/data pins trước PnL.
2. Chuẩn bị lại source+signals2022–25 bằng helper đã có, phải khớp exact saved
   signal/cadence trước lọc giờ. Kiểm BR01 chỉ thay prefix cutoff từ RS01;
   tất cả RS02 phải có parent được giữ, same side/ATR và later≤60min.
3. Chỉ BR01 mới chạy8financial+4null; RS02 dùng8sealed savedbooks, kiểm lại
   seal/accounting/policyclock/input/signal bindings. Không rerun RS02 không đổi.
4. Accounting Fraction, exactnextminute, stop/size/cash/null và oldunknown
   giữ nguyên. Kết quả so năm/scenario, count, knownsubset/fullnet tách biệt;
   matched-parent-day là diagnostics hồi tố, không tradable future-retest filter.
5. Báo có thể có trade-off ít lệnh/timing/chi phí, không chọn chỉ bởi net gần0,
   không épwinner. Nếu fullnetunknown hoặc kinh tế yếu thì khôngpromote, không
   tự chạy grid ATR/channel tiếp. Lượt sau nếu có phải newregistration/trial.

BR01 là **một related rule version mới**, không cơ chế/edge độc lập. Native
strategy và costmodel không đổi. Kết thúc bằng report/remaininggaps/nextsmallstep;
không broker/LLMcalls, tăngrisk hoặc tạoGoal/engine mới.
