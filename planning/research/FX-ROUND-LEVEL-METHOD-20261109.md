# Chuyển từ breakout chỉ báo sang phép kiểm mốc số tròn

09/11/2026, sau R090 không đạt và C2 signal review của Gold. Rà catalogue90
records: R001/R015/R019 đã thử breakout/retest đỉnh–đáy, nhưng chưa kiểm riêng
00/50-pip geometry. Hướng này có liên quan family breakout, chưa độc lập về
PnL hoặc rủi ro. Không mở lại một exact recipe đã gác.

## Primary methods đã đọc

- [NY Fed125, Osler2001](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf),
  intro và phần clustering/quotation: orders một bank 1999–2000, gồm EURUSD,
  có clustering và bất đối xứng stop/take-profit quanh 00/50. Đây là cơ chế
  giả thuyết, không sổ orders hiện tại của feed mình hoặc recipe có phí.
- [NY Fed150, Osler2002](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf),
  §§I–IV, TablesV–VIII: quote DEM/JPY/GBP 1996–1998, NY09–16; so với arbitrary
  levels, horizons15min–days. **Crossing subsample dùng trạng thái 15 phút
  sau lúc chạm**, rồi đo move gồm 15 phút đó. Không dùng classification ấy
  để giả vào tại lúc chạm. Paper cũng không chứng minh causality từ orders.

Own adaptation tại [protocol](FX-ROUND-LEVEL-PROTOCOL-20261109.md): chỉ nhận
cross đã quan sát trên joint quotes 5 phút, entry sau decision; kiểm phần
tiếp diễn sau đó. Không exact replication, không dùng 15-minute winner label,
không gọi quote crossing là quan sát stop-loss orders thực sự. EURUSD/era/feed
khác empirical DEM, không chuyển headline effect thành kỳ vọng lợi nhuận.

## Quyết định admission

| Hướng đã rà | Quyết định |
|---|---|
| COT positioning | [RBNZ AN2018/03](https://www.rbnz.govt.nz/research-and-publications/research/our-research-and-analysis/analytical-notes/2018/an2018-03), official summary: publication lag và predictive use hạn chế. Chưa fullmethod/PIT source, không mở batch chỉ từ raw net positions |
| Thêm VIX để cứu R080 | Chưa: đã gác unconditional và closing-pressure variant. Chưa có causal input/recipe mới đủ admission; không tự thêm VIX grid từ outcomes cũ |
| Round-level continuation | Có thể khóa own hypothesis và source fixture; cơ chế cụ thể, chỉ cần quote đã sở hữu, holding trong phiên giảm funding uncertainty. Chưa edge hoặc prop-ready |

Đọc/download paper không cấp quyền sao chép code/dataset; chỉ dùng ý tưởng và
metadata, tự viết code. Không mua bot, provider mới, gọi broker hoặc own2025+.
Private `execution-v1/round-level-method-sources-v1/receipt.json` giữ official
PDFs personal reference:125 SHA `d72bc0a020d04f0b7dd423c0f4f2dcebc83b34ebd160ca8eca75b52d69e1341d`,
150 SHA `0132a12fe1116a4608e437bb36212e21589fec22e925a04edb903d0f0e601904`.
Không redistribute. Existing research/qualification skills đủ, không thêm MCP.
