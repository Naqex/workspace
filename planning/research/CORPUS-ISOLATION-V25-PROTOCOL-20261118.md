# V25 — nhận hạ tầng, khai thác corpus và đồng mức risk

Owner prompt: attachment `c629b92c-1c45-478a-9b0c-d60907843045`.
PR103 head `4b86ec6` đã merge `0bb221e`; nhánh V24 local/remote đã xóa.
Nhánh mới `codex/corpus-mining-and-isolation-v25`; Trader baseline `930fa768`.
Đăng ký trước các outcome mới. Chỉ scope offline; không broker, runtime
restart, credential access, xóa cache/data, ghi source lane hoặc VI Dubber WIP.

## 1. Hạ tầng và corpus

Port có chọn lọc runtime/output ownership và artifact long-path/read integrity
từ Trader `7241a8b0`/`a60db1e5`; không merge cả branch cũ hay Rust formatting.
Product thay đổi qua PR riêng, publish trước gitlink; không tự deploy.
Workspace dùng path guard chung cho đường I/O, giữ logical path cho manifest;
không follow symlink/junction/reparse points, không đổi Windows global config.

So sánh với V24 `connector-source-inventory` và 420 profiles. Quét D/E trong
cùng scope maxdepth18/pruned generated dirs, thêm runtime/source worktree được
giao khi cần đọc có chọn lọc. Không đọc credential values hoặc export source
thô vào Git. Phân biệt MAX_PATH, path không còn tồn tại, access denied, links,
rg errors và file quá lớn. Không mặc định 48.425 FileNotFound đều do MAX_PATH.
Không che lỗi bằng cách bỏ chúng khỏi mẫu số; scope mở rộng báo riêng.

Static corpus: SHA256 dedup, giữ mọi aliases/format; no-flags khác clean.
Clean structural cần source đọc được, execution entry + SL binding có thể
review, không cờ đỏ/external opaque logic và không chỉ là library/indicator.
Top10 tối đa, có thể ít hơn10; thiếu chứng cứ thì REVIEW_REQUIRED.
Quyền dùng source/license chưa rõ: chỉ fingerprint/ý tưởng có provenance,
không copy source hoặc tuyên bố causal clone.

Tối đa3 cơ chế mới, khác F3 compression/F4 impulse/F5 range rejection.
Chọn theo đặc tả rõ + dữ liệu sẵn + khác cơ chế, trước mọi PnL; khóa card/source
hash riêng trong Git trước run. Không đủ recipe thì không sáng tác để đủ3.
Stage0 Dev2018–2023: primary +8h trong tuần, clamp trước known long closure,
natural stop nguyên bản; stress BidAsk + phí hiện có; cap12%/retention>=50%.
Mọi năm mean net phải dương và >=mean friction; cadence>=40/năm là suitability
screen riêng. Horizon phụ +4h chỉ diagnostic, không dùng chọn winner.
Chỉ recipe đạt toàn Stage0 mới chạy SL-active chính xác theo card đã khóa,
giữ gaps/unknown, hai clusters2018–20 và2021–23 dương; không tune sau outcome.

## 2. P80_ISO và GBP

Không gọi cumulative NetR/DD là annualized Calmar. C_iso duy nhất:
min(exact Dev baseline DD / exact V24 P80 DD,
exact Dev baseline open risk / exact V24 P80 open risk), lấy saved JSON,
không số làm tròn trong prompt. Vector = c_iso × (F5=1.30,F3=.70,F4=.70).
Tính lại lot floor, cents và đường SL-active OLHC/OHLC. Không bảo đảm tuyến
tính. Net>baseline, equityDD<=baseline, openrisk<=baseline; static/daily
không xấu hơn; dual clusters dương; missing paths vẫn unknown. Chỉ1 ISO trial.

Exact cost membership audit Dev: đối chiếu float vs integer 12%/15% trên raw
cohort sẵn có, không sửa historical producers/seals hoặc tự đổi signal sample.
GBP giữ nguyên recipe `GBPUSD.SWEEP.ASIA.LONDON.DAY`, hai chiều, H1 Asia box
sweep/reclaim, deadline gốc theo source card; không biến thành F5 hoặc đổi exit
sang20:00 chỉ vì endpoint có sẵn. So source/bars/2018–2023 và path resolution
trước PnL. H1 envelopes/20:00 endpoints không phải exact intrahour path.
S01 Dev2022–23 result chỉ là điểm đối chiếu, không thay admission2018–23.
Satellite trials cố định .25x và .50x; ExTop5/10 theo từng recipe và danh mục.
Nếu đủ path thì đo marked book với đúng lot/cost trên risk gốc150USD×weight.
Không trộn R theo risk từng trade.

Chọn để mở later/lifecycle chỉ bằng Dev: ưu tiên ISO độc lập; GBP satellite
chỉ thêm khi tăng net và không tăng risk/DD so parent và đủ paths; nếu cả hai
satellite đạt thì chọn .25x. Tối đa1 tổ hợp ISO+GBP, không grid/clean-bot combo
khi chưa card và gate riêng. Ghi toàn selection history.
Sau gatepass khóa source/input/weights trong commit rồi mới đọc later:
105 historical starts +5.000 common bootstrap draws so BASE_GUARD,
PRIMARY và declared strict-gap stress; overlap/reused history không là OOS mới.
Nếu không case nào qua gate thì0 lifecycle/MC children, giữ BASE_GUARD.

## 3. Hiệu năng và bàn giao

V24 1.335tests13,278s khác adoption1.340tests18,635s; không ghép thành một run.
Profile78 smoke IDs; tối đa2 thay đổi có hotspot, giữ mọi IDs và failures.
Final10 fresh-process smoke samples, kể cả startup, target10/10<.72s;
full complete target<13.5s. Không giảm coverage/skip/retry chọn streak.
Large tables Zstd9+SHA256+roundtrip; receipts nhỏ JSON, output exclusive mới.
Private job `execution-v1/corpus-isolation-v25-20261118`.
Kết thúc bằng results JSON/MD, residual gaps, source/admission delta,
tests/performance IDs và PR104 nếu số đó còn trống, 3CI đúng final head.
Prompt nói Track0–5 nhưng chỉ có0–4: phần đóng sổ trên là delivery cuối,
không tự thêm một campaign hoặc quyền dữ liệu/broker.
