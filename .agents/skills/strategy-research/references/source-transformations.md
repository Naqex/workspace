# Provider input: kiểm phép biến đổi trước khi tin backtest

Áp dụng khi thêm loader, đổi timeframe/side hoặc thấy số bars, range hay
gaps khác nguồn. Không bắt mỗi status check tải lại data hoặc kiểm toàn feed.

1. Pin source/package/runtime/config cùng raw bytes. Đọc default thực tế:
   ignoreFlats/zero-volume, aggregation/session/timezone, adjustment, volume
   units, duplicate/gap policies. Ghi explicit field khi default có thể thay
   sample; dữ liệu có checksum vẫn có thể đã bị lọc trước khi ghi file.
2. Kiểm fixture nhỏ có quotes/bar cùng thời gian, side và price grid. Một nến
   lớn phải chứa extrema của mọi quote đã quan sát trong interval; không thể
   giải thích low cao hơn actual bid tick bằng thiếu các tick khác. Không lấy
   mean(side-highs/lows) làm observed-mid extrema. Same-provider/two-transports
   không là independent feed và một fixture không chứng thực toàn history.
3. Volume0 không tự đồng nghĩa không có quote hoặc flat price. Giữ provider
   bars nếu scope dùng quote prices; không đổi quote volume thành exchange
   volume hay bằng chứng có thể fill. Nếu loại bars, phải có semantics và
   protocol rõ trước outcome, không gọi phần bị lọc là feed outage đã xác minh.
   Kiểm cả decoder: nó có thể tự chèn carried-close/volume0 vào phút không
   được raw response liệt kê. `ignoreFlats:false` không chứng minh source-only,
   còn lọc mọi volume0 có thể mất nến nguồn thật. Bind timestamp từng side vào
   raw source, phân biệt explicit/padding/unknown; giữ nến explicit có volume0.
   Với cached Dukascopy M1, opt-in `sourceCandlesOnly:true` và lưu callback
   provenance/hash/count trong manifest. Default native view giữ để tái hiện
   lịch sử, chưa là quan sát nguồn hoặc giá có thể khớp. Không tự suy M1 thành
   execution tick; kiểm availability cho đúng Bid/Ask của từng metric/fill.
4. Khi phát hiện material input defect: giữ old attempt, đánh dấu phạm vi bị
   ảnh hưởng; canonicaldecode output mới từ hashed cachedraw nếu có. Test
   network-denied để chắc reuse không lén tải nguồn khác. Rerun đúng affected
   policies/windows, giữ rules/risk/costs, rồi đối soát delta/count/fills/cash.
   Không rerun nguồn độc lập không bị ảnh hưởng hoặc im lặng đổi lịch sử.
   Nếu checkout chỉ đổi LF/CRLF: tìm snapshot đúng hash frozen, đối chiếu
   nội dung và ghi hash code đang dùng riêng; không normalize raw hoặc sửa
   original pins để ép reuse. Content drift khác newline vẫn cần review mới.
   [Case kiểm thật và negative regressions](../../../../planning/research/OIL-EIA-ROLE-SOURCE-RESULTS-20261109.md).
5. Tách lỗi transport/schema/economics. Nativecache/sourcecomponents trước
   downloader mới. GET timeout/5xx có thể retry hữu hạn theo request/day khi
   scope cho phép, có backoff/cumulativecap/deadline/cancel; giữ phần sealed.
   Không retry auth/WAF/403/rate-limit/invalid schema để ép outcome. Drain
   inflight trước failure/handoff; checkpoint không đủ state thì chưa resume.

Khi mở pilot thành full history, chốt và kiểm manifest các partitions/roles
thực sự cần (quý/năm/side/session), không copy subset của fixture rồi gọi là
coverage thị trường. So census/availability của predictors theo từng cohort
trước PnL; lệch lớn phải phân biệt loader omission với source missing. Với
US500 quarterly views dùng `us500_year_source.load_year_side` để buộc đủ bốn
quý và bind output vào accepted frozen proof. Chỉ rerun consumer bị ảnh hưởng,
giữ raw và phần tick/locator đã kiểm; không fetch hoặc replay toàn batch không đổi.
Case thật/giới hạn: [paper-window quarter correction](../../../../planning/research/INDEX-PAPER-WINDOW-SOURCE-CORRECTION-20261109.md).

Đã kiểm ở [US500 correction](../../../../planning/research/INDEX-UNFILTERED-SOURCE-CORRECTION-20261108.md),
[range oracle](../../../../planning/research/INDEX-DAILY-RANGE-ORACLE-20261108.md).
[Explicit-source correction](../../../../planning/research/INDEX-EXPLICIT-SOURCE-CORRECTION-20261108.md)
và [kết quả](../../../../planning/research/INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md)
ghi decoder padding, cache-only parity và phạm vi affected; không sửa upstream
hoặc ghi đè old raw/results để hợp thức hóa correction.

Với fixture nhiều instruments, reuse `research_input_admission.py` ở cùng
tooling thay script kiểm mới: bind parent seals, frozen raw hashes và producer
snapshots; pin UTC/ms/bar-known-at, instrument/price units, adjustment basis,
data role/exposure. Output `source_fixture_verified_only` không là clean OOS,
long coverage hoặc execution proof. Giữ adjustment unknown khi chưa kiểm;
“Total Market” không tự nghĩa “total return”. Phạm vi đã kiểm và fixture thật:
[data admission](../../../../planning/research/RESEARCH-DATA-ADMISSION-20261108.md).
Local tools: `sealed_m1_review.py`, `quote_bar_oracle.py` và pinned-native
`dukascopy_cached_m1.cjs`, reviewer `candle_source_provenance.py` tại `tooling/ai-engines/`; exact runtime/source pins
ở attempt. Đây là workflow đã có evidence, không policy cho mọi provider.
