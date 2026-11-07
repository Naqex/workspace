# Hậu kiểm sau screening và kiểm nghiệm chiến lược

Dùng khi đóng một batch/cụm recovery có bằng chứng mới hoặc owner giao hậu
kiểm. Đọc protocol, source/data/cost pins, terminal/progress và review gần nhất;
không chạy lại mô phỏng chỉ để đọc kết quả. Các bước chung vẫn ở SKILL.md.

## Chọn đúng phần cần sửa

| Dấu hiệu | Việc kiểm trước | Hành động phù hợp |
|---|---|---|
| Kết quả không khớp | Signal/fill timing, giá Bid/Ask, cash/cost, cuối mẫu; lỗi ở data, simulator hay report? | Sửa nguyên nhân và regression nhỏ trước khi benchmark |
| Chuẩn bị chậm | Hash/read/parse/aggregate/write, cache hit/miss và binding | Profile prefix đã consumed; giữ raw validation, đo trước/sau cùng input |
| Compute chậm | Rule/sizing, valuation, ledger/risk, serialize/checkpoint | Chọn một hotspot được đo; không bỏ risk hoặc ledger checks |
| Review/bàn giao lâu | Có thể đọc lại numbers/pins/status từ artifact hiện có không? | Bổ sung đúng consumer/receipt thiếu; không tạo tracker/UI cạnh tranh |
| Lỗi quan sát/hủy/retry | Worker còn chạy? Observer lỗi hay numerical job lỗi? | Reconcile ownership, giữ output đã verified; không auto restart study |
| Screening bỏ sót hoặc lạc quan | So cả bản định giữ và định gác; stop/gap/DD/risk còn thiếu? | Đăng ký đối chiếu tick; chưa có ground truth thì không báo false-negative rate |

Xếp ưu tiên theo correctness → công việc lặp/thời gian chờ thực tế → chi phí
bảo trì. Một vòng chỉ cần một hoặc vài sửa đổi có quan hệ trực tiếp. GPU/Rust,
dependency hoặc song song không là mục tiêu khi hotspot nhỏ đã đủ nhanh.

## So sánh để không đánh đổi ngầm độ đúng

- Khóa câu hỏi engineering, baseline, input, giới hạn thời gian và expected
  invariants trước khi đo. Tách timer của research/code, preparation, load,
  compute, validate/report và rework; thiếu timer thì unknown, không suy active
  time từ commit hoặc cộng khoảng chồng nhau. Không đồng nhất CPU với token.
- Cùng semantics: so tất cả trường bị tác động. Với input aggregation, gồm
  OHLC từng side và mid, spread, timestamp/sequence/count, gaps/excluded bars.
  Mid high/low phải từ observed mids, không suy từ extrema Bid và Ask xảy ra
  ở hai thời điểm khác nhau. Giữ cả equality/decimal representation nếu consumer
  dùng byte hashes. Với mô phỏng, so decisions, entries/exits, costs/financing,
  balance/equity, floating và position/pending, không chỉ tổng PnL.
- Khác semantics: ghi là approximation hoặc scope reduction. H1 stop ở level
  không là first-crossing tick fill; thiếu risk/DD/prop không được báo exact
  engine speedup hoặc dùng kết quả để tự loại/nâng bước. Không áp sai số ở một
  mẫu thành error bound chung, không điều chỉnh budget sau khi thấy outcome.
- Benchmark A/B xen kẽ, cùng input/cache state/process count, tách profiling
  khỏi timing; lưu raw samples và số lần đo. Prefix nhanh hơn không tự chứng
  minh cả quý/năm nhanh cùng tỷ lệ. Full workload chỉ đo khi còn câu hỏi cần
  giải quyết; không lặp annual study để làm đẹp báo cáo.
- Source đổi thì binding/cache mới theo guard hiện có. Giữ attempts và source
  snapshots cũ; không sửa pin, tắt hash guard hoặc ghi đè kết quả để reuse.

## Đóng vòng

Lưu một bảng ngắn tại review/receipt owner: phát hiện → evidence → đã sửa/giữ
nguyên/để sau → số đo trước/sau → invariants/test → remaining gap/next trigger.
Nối delta vào context/index cần thiết; không thêm cùng một recap ở mọi tầng.
Kết thúc khi scope đã đạt và focused checks đạt, hoặc không có cải tiến đáng
làm được chứng minh; không mở vòng tự tối ưu vô hạn. Kết luận edge/prop-fit vẫn
thuộc strategy-qualification, sửa rules/risk/holdout là scope/protocol riêng.

Provenance thực tế: [pilot H1](../../../../planning/research/COARSE-SCREEN-REVIEW-20261107.md)
ghi preparation73s, stop bias và giới hạn speed ratio; bài học dùng cho lựa chọn
invariants, không hard-code workload, timing hoặc tolerance vào mọi bài sau.

Recovery có đổi numerical source: chọn explicit checkout cho cả worker lẫn
artifact reviewer trước khi import model; không sửa source đang pin của job
khác. Dùng registration/attempt mới và đối chiếu cả metadata kế thừa (candidate,
parent recovery, worker/deadline và protocol), không chỉ cập nhật hash. Source
snapshot cũ validate/roundtrip bằng code mới chỉ chứng minh tương thích state,
không thay replay hoặc chứng nhận code mới có cùng outcomes.

Với lỗi timing qua khoảng trống quote, phân biệt thời điểm quyết định đã khóa
với checkpoint cash/financing được thêm sau đó. Regression cần cả lệnh hợp lệ
đi qua cash event và lệnh giả mạo quyết định sớm hơn. Không sửa thời điểm quyết
định để validator pass. [Recovery thực tế08/11](../../../../planning/research/H1-ASIA-RECOVERY-20261108.md).

[Complete CLI resume](../../../../planning/research/NATIVE-RESUME-REVIEW-20261108.md)
đã có bounded actual-data parity. Khi kiểm checkpoint, bao gồm phase2/reset và
nested profile binding, không chỉ flat roundtrip. Legacy account JSON không tự
thành complete packet; nguồn đổi không được sửa hash để ép tiếp tục.
