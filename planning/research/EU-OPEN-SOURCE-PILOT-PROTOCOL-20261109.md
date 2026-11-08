# EU-open source admission: kiểm night endpoints trước PnL

Theo [method admission](EU-OPEN-AND-OIL-METHOD-20261109.md). Chưa economic recipe
hoặc PnL mới. Giữ R078/R079 negative và selection history, không đổi clock để cứu.

US500 nguồn có sẵn, hai năm consumed 2019/2022. Eight dates khóa trước giá mới:
2019-01-02, 2019-03-08, 2019-03-11, 2019-07-01; 2022-01-03, 2022-03-11,
2022-03-14, 2022-07-01. Gồm first regular Jan/Jul và Friday/Monday quanh US
March DST, không chọn bằng returns. Nhãn theo exit date; phải là regular NYSE
session của calendar frozen. Không own2025+, remote fetch/provider/broker.

Primary window method 23:30 ngày trước →03:30 New York ngày ghi nhãn. Pilot chỉ
kiểm endpoints **23:31/03:31 M1Open**, interval proxy sau decision một phút.
Không actual tick/arrival/fill, không thêm các clock alternatives của paper.
Ngày Sunday→Monday vẫn phải có source; không nhảy về Friday vì last quote.

Reuse accepted US500 proof/facts từ R075; full-year loader yêu cầu đủ 4 quarters/
8 side seals trước lấy subset. Bind proof/calendar/canonical/raw hashes; không
rerun full raw transformation hoặc rewrite old sources. Với mỗi selected M1bar,
dựng explicit source values từ original raw cached UTC-day response bằng helper
hiện có, so timestamp/OHLC/volume exact và grid/side/order/source presence. Không
dùng decoder padding/volume0 heuristic hoặc raw file mới không đúng proof.

8 dates×2endpoints×2sides=32 M1bars, 192 timestamp/OHLC/volume checks. Pair clock,
positive bounds và BidOpen≤AskOpen; missing/crossed/conflict giữ unavailable,
không forwardfill, đổi timestamp hoặc tạo nến. Kiểm ba in-memory mutations
price/clock/volume phải reject. Metadata giữ UTCms, local clock/DST, priceunit/
grid, native quotevolume, consumed exposure/source code/proof/cutoff/authority.

Private output mới `execution-v1/us500-euopen-source-pilot-v1/`, one writer,
no overwrite, deadline180s/PID/progress/events/CANCEL và pins. Chỉ source
admission cho **8 dates** nếu đủ32bars/no conflicts; không full-history/execution/
equity/edge/prop/OOS hoặc C1/C2. Sau pilot cần exact economic/cost/funding/
missing/controls/gate protocol trước annual component; không numeric trong job.
