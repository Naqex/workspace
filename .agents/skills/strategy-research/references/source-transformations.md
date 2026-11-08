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
4. Khi phát hiện material input defect: giữ old attempt, đánh dấu phạm vi bị
   ảnh hưởng; canonicaldecode output mới từ hashed cachedraw nếu có. Test
   network-denied để chắc reuse không lén tải nguồn khác. Rerun đúng affected
   policies/windows, giữ rules/risk/costs, rồi đối soát delta/count/fills/cash.
   Không rerun nguồn độc lập không bị ảnh hưởng hoặc im lặng đổi lịch sử.
5. Tách lỗi transport/schema/economics. Nativecache/sourcecomponents trước
   downloader mới. GET timeout/5xx có thể retry hữu hạn theo request/day khi
   scope cho phép, có backoff/cumulativecap/deadline/cancel; giữ phần sealed.
   Không retry auth/WAF/403/rate-limit/invalid schema để ép outcome. Drain
   inflight trước failure/handoff; checkpoint không đủ state thì chưa resume.

Đã kiểm ở [US500 correction](../../../../planning/research/INDEX-UNFILTERED-SOURCE-CORRECTION-20261108.md),
[range oracle](../../../../planning/research/INDEX-DAILY-RANGE-ORACLE-20261108.md).
Local tools: `sealed_m1_review.py`, `quote_bar_oracle.py` và pinned-native
`dukascopy_cached_m1.cjs` tại `tooling/ai-engines/`; exact runtime/source pins
ở attempt. Đây là workflow đã có evidence, không policy cho mọi provider.
