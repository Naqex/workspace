# R065: kiểm giới hạn giá H1 tại đoạn thiếu năm 2019

Đăng ký trước khi trích giá của fixture. Đây là kiểm nguồn đã lưu, không phải
backtest mới hoặc quyền thay đổi verdict của R065. Parent là
[data revision](NASDAQ-OPENING5-ORB-DATA-REVISION-RESULTS-20261109.md).

## Câu hỏi và phạm vi

H1 Bid/Ask 25/01/2019, 14:00–15:00 UTC có chứa mọi M1/tick đã quan sát trong
giờ này không? Nếu có, envelope đó có loại trừ khả năng chạm SL hoặc TP của
vị thế đang unknown tại 14:49 không? Kiểm riêng từng side và từng giá OHLC;
không dùng Bid thay Ask để đánh giá vị thế SELL.

Chỉ đọc source-only H1 từ `nasdaq-history-v1`, các M1 của đúng giờ trong
`nasdaq-m1-history-v1` và cached ticks `nasdaq-M1-gap-ticks-v1/2019-01-25-14.json`
ở private campaign `challenge-discovery4-20261108/execution-v1`. Bind H1
result SHA256 `858a86b14c739a91a1751fa9b5aff388453e5cbc347beae91cce7232f72ff9c0`,
review SHA256 `9d2b0dabe64cc9220d56f85270a6d557921d825c362943d3b7d5f71191493f0e`,
2019 Bid SHA256 `89162a7828332530d6c2b4c6b1877bc5eee47966969ad8e4a53eaab2288dcb18`,
Ask SHA256 `05b4a9eb28cbe4012d19f3a2c943a46d087f577d471c1cf52399ab05132a55eb`.
Verify parent receipts/seals before price inspection. No network, 2025+,
provider/account changes, interpolation or raw overwrite.

## Các kết luận được phép

- Nếu H1 không chứa observed M1/ticks: ghi source inconsistency; không dùng
  nó để chứng minh giá trong đoạn thiếu.
- Nếu H1 chứa mọi giá đã thấy: chỉ xác nhận consistency của fixture này.
  H1 high dưới SL và low trên TP có thể loại trừ barrier trong giờ theo
  envelope assumption; chỉ cần một barrier còn khả thi thì chưa biết timing.
- H1 có cả đoạn trước entry. High vượt SL không chứng minh SL xảy ra sau
  entry; low chạm TP cũng không chứng minh TP xảy ra sau entry. Không suy
  thứ tự high/low từ OHLC hoặc biến coarse bar thành quote thực thi.
- Kể cả loại trừ được hai barrier, đây chưa chứng minh missing minute có
  executable quote hoặc cho phép bỏ unknown policy đã freeze. Mọi bounded
  financial model/affected replay cần protocol mới và review riêng.

Output private mới `nasdaq-h1-gap-envelope-v1`: pins/config, result/review,
timing và authority=false. Numeric review bằng Fraction, producer Decimal;
mutation sai side/price/timestamp/hash phải bị phát hiện. Không chạy lại
R065, không sửa annual N/A, không tự promote hoặc tính trial mới.

## Bước trước đã terminal

[BI5 probe](NASDAQ-BI5-SOURCE-PROTOCOL-20261109.md) có đúng một GET; failure
`URLError/WinError 10060` trước HTTP response sau 21,608 giây. Không có binary
payload; chưa kiểm archive coverage. Không retry request không đổi, không
gọi timeout là file không tồn tại. Giữ nguyên failed attempt.

## Sửa locator trước trích giá

Metadata check sau commit `06e0a5a` phát hiện `nasdaq-m1-history-v1` là
attempt failed, không có result. M1 thực sự được R065 dùng là
`nasdaq-m1-history-v2`, result SHA256
`3058b26de169c11ff0fbb841ec11d74df1c81b1035de4cad4d1aad901a0006e7`.
Chỉ sửa locator này, giữ nguyên giờ/câu hỏi/tiêu chí; chưa trích target prices
hoặc chạy fixture khi sửa. Không sửa failed v1 hoặc coi nó đã complete.
