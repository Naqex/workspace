# V24 — connector MT5, Bot Lab và phép thử Pareto

**P80_20 rớt Development; giữ V16/V19 BASE_GUARD. Connector và lab đã có implementation/fixtures, nhưng native login/capture chưa kiểm thực tế, chưa có causal clone tự động và chưa đạt mục tiêu tốc độ.**

PR102/head19bf58c đã merge555c2bd, nhánh V23 local/remote đã xóa. V24 đăng ký220550d trước kết quả, đúng một trial1,30/0,70/0,70, không grid hoặc tune theo2024+. Giữ Trader pin930fa768/VI WIP, không broker orders/deploy. PR103 để mở.

## 1. Kết nối MT5 cũ và rotation tài khoản mới

Connector product có sẵn, không mất: Python IPC được API owner quản lý bằng private portable terminal; secret DPAPI-sealed trong mt5_connections, không phải password plain text cần khôi phục. Owner cho biết account cũ hết hạn; V24 không query database hay xác nhận lại hạn dùng tài khoản.

| Thành phần | Vị trí | Reuse/thay đổi |
|---|---|---|
| Product connector | projects/trader/foundation_v2/scripts/mt5_connector.py | prepare_terminal/verify_identity/error codes, không sửa submodule |
| Secret/connection owner | projects/trader/foundation_v2/api-rust/src/mt5_connector.rs | DPAPI binding/mt5_connections; không decrypt secret cũ |
| Broker clock | projects/trader/foundation_v2/scripts/mt5_clock.py | Exact FTMO-Demo2026→UTC; ticks/rates/deal envelopes |
| Process tree | projects/trader/foundation_v2/trading_workspace_v2/nautilus_worker.py | Windows Job kill-on-close; launch suspended→assign→resume |
| Legacy socket | projects/trader/archive/legacy/root/mt5_data.py | Historical reference; không khôi phục legacy runtime |
| Trial integration | tooling/ai-engines/ftmo_connection.py + ftmo_trial_runner.py | Four-key parser/own terminal/account hash binding |
| Private new credential file | config/ftmo_free_trial.env | Ignored; example tracked, no shell eval/password argv |

Inventory D/E: 272,988 candidate files, 4,821 signature matches, 1016 bot file paths, 48426 recorded errors, 3839 large candidate files skipped. Maxdepth18; generated folders pruned. Không gọi đây là toàn bộ nội dung mọi file/dependency. Full redacted list và Git-history metadata nằm trong Zstd private; không password/account values vào báo cáo hoặc Git. Lần Python walk đầu quá chậm được giữ receipt và thay bằng rg traversal.

48.425 errors là FileNotFoundError, chủ yếu generated/long paths, cộng1 rg traversal error; đó là scan gaps, không phải48.426 connector hỏng và không bị biến thành coverage100%. Không thay quyền hệ thống để ép đọc các cây không liên quan.

Dùng `--credentials-file config/ftmo_free_trial.env` hoặc bốn environment keys. Đúng FTMO Demo/Trial USD mới được nhận; không đổi terminal Trader đang chạy. Lock theo account, process tree riêng tắt Experts/DLL. Snapshot/parity và ticks/rates/deals dùng clock helper product, account đổi giữa login/probe/capture thì fail. Không login bằng account saved cuối cùng khi credential thiếu.

Actual CLI không credentials: check exit2/no ready, watcher2s exit2/timeout; không tài khoản mới hoặc terminal đích để chứng nhận login/capture thành công. Fixture kiểm launch/Job/binding/clock/shutdown; actual Windows Job create/close smoke đã chạy. Shadow vẫn yêu cầu manifest, seed và session/news/spec parity; không suy từ login thành execution-ready. 10giây là thao tác rotation sau prerequisites, không là cam kết cold/network timing.

## 2. Kiểm thử và fast-fail: đo lại premise, không giảm coverage

Runner thực tế là unittest, không phải pytest. Smoke8modules/78IDs, không66; nó chưa từng import tất cả23thế hệ chỉ vì filename collection. V22/V23 tests không chạy batch5.000 hoặc giải nén research archives trong từng test. Vì vậy không thêm cache phức tạp không có hotspot. Profile V24 cho thấy import/path/stat và fixture filesystem; tải concurrent inventory làm số đo trước đầu phiên không tương đương idle.

| Phép đo | Tests | Wall | Scope |
|---|---|---|---|
| V23 receipt lịch sử | 1295 | 19,728s | 5 runtime groups, khác thời điểm/tải |
| V24 initial five groups | 1325 | 41.506s | Inventory concurrent; không dùng làm causal speedup |
| Same-runtime baseline4shards | 1334 | 15.007s | Cùng current tests, inventory paused |
| RAM log buffering4shards | 1334 | 15.157s | Không cải thiện; đã revert |
| Final source6shards | 1335 | 13.278s | Giữ mọi1295 IDs, không skip; sáu logical CPUs |

**1335 PASS/0skip**, final source **13.278444s**, target<12,5s: **chưa đạt**. Six workers là lựa chọn explicit, CI vẫn4; không đổi dependency runtime product. Runtime test chung dùng exact pins CI và PyYAML từ worker lock; lần thiếu PyYAML được giữ nguyên lỗi, không skip tests.

Smoke release10fresh processes, cùng78IDs: **0/10<0,55s; 0/10<0,65s**, median0.685731s/max0.712075s. Giữ các samples ban đầu, A/B và release; release đo lại vì source log buffering đã revert, không chọn nhanh nhất làm kết quả. Chưa đạt performance acceptance; không bảo đảm tốc độ trên tải/máy khác.

Fast-fail Gate1 pure toxicity+declared scale, không write artifact khi fail; chưa chứng minh hardSL/safety. Ba controls Gate1 max0.002004s. Gate2 chỉ nhận Dev/causal/SL-active và so net/DD/static/daily/open risk với baseline; Gate3 đòi freeze thực sự nằm trong GitHEAD, source/input/decision hash và tính lại gate, không tin passed=True do caller cấp. <0,5s/<2s là prepared compute budget trên workload được đo, không universal runtime cap.

## 3. Bot Lab: capabilities đã có và phần chưa thể suy ra

Luồng: inbox file→bounded static parser→DNA/evidence/flags→prepared Gate1 nếu có scale→review causal recipe→Stage-0/Dev→Gate3. File lạ không được import/execute hoặc gửi lệnh. Source limit1MiB cho Python AST, binary/log16MiB, logs≤50.000rows; closed-loss lookup dùng heap theo thời gian/symbol.

| Input | Có | Giới hạn |
|---|---|---|
| .py | AST/tokenizer + structural evidence | Không complete dataflow/call graph |
| .mq4/.mq5/.cs/.pine | Indicator/timeframe/entry/exit/session/sizing patterns | Không compiler đầy đủ; dynamic/obfuscated logic unknown |
| .ex4/.ex5/.dll/.pyc | ASCII/UTF16 + bounded PE import metadata khi có | Không decompile, loadDLL, marshal hoặc bypass khóa |
| CSV/HTML/JSON log | UTC session signature, stop/target geometry, prior closed loss sizing | Cần canonical columns/timezone; không unique causal algorithm |
| Optional MarketDataStore | ATR H1/H4,MA/RSI/Donchian/PDH-PDL/Asian causal Bid features | Ask/execution parity không có; source binding bắt buộcUTC |

Seed corpus: **3controls PASS** với expected patterns; **18** tracked strategy/order-bearing sources được inspect trong scope scanner, giữ SHA. Martingale fractional>1 trong loss context, literalSL0, date-condition review và friction ratio có flags. Không có ground truth corpus để tuyên bố100% real-world recall hoặc mọi bot không flag đều sạch. Hardcoded dates có thể là holiday hợp lệ, multiplier có thể là sizing hợp lệ; manual reachability/context vẫn cần.

Ngoài seed, toàn bộ **1016** MQL source/binary paths tìm được được inspect tĩnh, **420** profile nội dung duy nhất sau dedup, **0** parse/access failures. Đây gồm example/library/utility và bản sao backup, không phải1.016 chiến lược độc lập. Raw profiles/flags SHA-bound ở Zstd private; không chạy EX5 hoặc promote bằng absence-of-flags.

**Chưa có engine tự khôi phục causal bot tương đương từ EX5/trade logs hoặc tự chạy9năm.** Đã có fingerprint/typed translation gate; thuật toán không định danh duy nhất từ các đầu vào này. Không ghi timestamp trades thành alpha giả hoặc lách Dev bằng outcome. Review hướng dẫn dùng tại [playbook](BOT-REVERSE-LAB-PLAYBOOK.md), có lệnhinspect/clone-log/market-store/credentials.

## 4. P80_20 và quyết định chốt

Protocol khóa EURF5×1,30, GoldF3×0,70, GoldF4×0,70 trước outcome. Đây không phải80% vốn vàoEUR, không tìm grid1,25–1,35. V23 lợi nhuận87,1% từF5 là attribution lịch sử, không tự suy weight tối ưu; “Vàng thấp/cao” cũng chưa được chứng minh là nguyên nhân regime. Giữ340 Dev trades, actual lot floor, stress cash fees, causal original SL-active paths cả hai ordering.

| Order | Model | NetR | EquityDD R | Static loss R | Daily R UTC | Open stop risk USD | 2018–20 R | 2021–23 R |
|---|---|---|---|---|---|---|---|---|
| OLHC | Baseline | 23.852 | 12.207 | 3.984 | 2.037 | 312.80 | 9.339 | 14.514 |
| OLHC | P80_20 | 32.278 | 14.673 | 3.707 | 1.862 | 314.52 | 10.613 | 21.665 |
| OHLC | Baseline | 23.852 | 12.207 | 3.984 | 2.037 | 312.80 | 9.339 | 14.514 |
| OHLC | P80_20 | 32.278 | 14.673 | 3.707 | 1.862 | 314.52 | 10.613 | 21.665 |

End-to-end data preparation+measurement **3.953s**; prepared two-book+gate compute mỗi ordering 0.451s, 0.348s. **NO-GO**: equityDD14,673R>12,207R và maxopen314,52USD>312,80USD. Net32,278R cao hơn và static/daily tốt hơn không đủ pass toàn gate. Đây là fixed-unit marked book trước account admission, không giả là account compliance; fail sớm nên không chạy tiếp lifecycle để cứu kết quả.

**0 new historical105-start children /0 new bootstrap5.000-draw children.** Không dùng giá2024–2026 để chọn/đổi weights. Giữ V16/V19 BASE_GUARD; không mua Challenge, tăng risk hoặc promote bot.

Independent review đã phát hiện và sửa: clock toàn rates/deals, configured-account drift, terminal tree race, risk input domains, future-loss inference, fractional multiplier và log work bounds. Fixtures/source review khác successful native acceptance; final CI/IDs ghi private receipts sau push.

Artifacts mới dạng bảng dùng Zstd9+SHA256/roundtrip; small reports và test receipts JSON để đối chiếu. Không xóa raw source, old attempts hoặc duplicate price caches. Không đổi Trader gitlink/VIWIP.

[Protocol](PARETO-MT5-BOT-LAB-V24-PROTOCOL-20261117.md) · [JSON](PARETO-MT5-BOT-LAB-V24-RESULTS-20261117.json) · [Playbook](BOT-REVERSE-LAB-PLAYBOOK.md)
