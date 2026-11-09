# NASDAQ100: mẫu tick/M1/H1 khớp, chưa chạy chiến lược

Thực hiện [source protocol](NASDAQ100-SOURCE-ADMISSION-20261108.md), commit
`2612348` trước download. Pilot producer và reviewer đều terminal0; **mẫu đạt
source/fidelity checks**, không full-history hoặc target broker admission.

| Lát thực kiểm | Kết quả |
|---|---:|
| 10source requests | Đủ4H1month/4M1day/2tickhour sources |
| H1 bars / M1 bars | 88 /5.100, cả2sides |
| Joint BidAsk ticks | 63.876 |
| Raw delta/volume transforms | 25.940bar và319.380tick-field checks |
| SourceM1 → H1 | 88side-hour comparisons khớp OHLC |
| Tick → M1/H1 | 244side-interval comparisons khớp OHLC;0differences |
| Negative mutations | 5lỗi giá, row thiếu, future clock, false authority, false joint-bar claim bị reject |
| Source collection | 3,063s wall; không retry/failure |
| Separate review | 3,674s wall |

Ngày02/01/2019 có23H1/1.335M1 mỗi side;01/07/2022 có21H1/1.215M1 mỗi side.
Không ép thành24/1.440. Đã bỏ8carried-padding H1 rows và210M1padding rows;
trong selected source bars này không có explicitvolume0. Không suy thiếu
giờ là market closure đã xác minh. Tick intervals15–16UTC mùa đông và14–15UTC
mùa hè đều là10–11NewYork;26.320/37.556ticks tương ứng.

Raw multiplier cả10sources là0,001price unit, **không FTMO/The5ers SYMBOL_POINT,
tickvalue hoặc lot contract**. M1 giữ source volume precision; H1 native
aggregate round4 được reviewer tái hiện. Volume là provider units, không
signed order flow hoặc exchange traded volume cho VWAP strategy.

Dữ liệu `USATECH.IDX/USD` là Dukascopy CFD, không NDX/QQQ/NQ hoặc quỹ US100.
History label: whole Jan2019/Jul2022 exposure do H1month responses; M1selected
days/tickselectedhours. CleanOOS=false, execution-authorized=false. Native
decoder và independent Fraction decode/quote-bar oracle khớp; cùng provider/
agent không independent feed hoặc independent human/model audit.

Nguồn [FTMO indices commission0](https://ftmo.com/en/blog/zero-commissions-on-indices/)
đã đọc, nhưng browser Symbols timeout/ERR_CONNECTION_CLOSED không nhận được
US100row. Không dùng Forex fee của [The5ers](https://the5ers.com/asset-specifications/)
cho indices hoặc NQfutures multiplier cho CFD. Broker cost/spec/funding/
sessions/delays/dividend vẫn cần đúng program; pilot không trả lời economics.

## Hậu kiểm và quyết định

Source-only representation được kiểm trước PnL, đã reuse installed1.51.1 và
cache/provenance/oracle helpers. Không cần đổi code sản phẩm, cài package,
tạo account/OAuth hoặc framework/RAG/skill mới. M1request được clone trước
native validator để giữ declared dates bất biến; không sửa helper/oldartifacts.
Không có bottleneck đáng tối ưu: collection+review~6,7s, không benchmark claim
cho toàn pipeline hoặc history lớn. Raw/cached sources và snapshots giữ nguyên.

Private campaign root
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/nasdaq-source-pilot-v1` giữ10exports/source proofs/seals/config/
manifest/source-snapshot/result/review/progress/events. Producer
`prepare-nasdaq-source-pilot-v1.cjs`, reviewer `check-nasdaq-source-pilot-v1.py`.
ResultSHA `f4f92c4de46263ab6ddf4afeb3dbc3295c812b6a3c724d1d9d0f023fed9987ba`;
reviewerSHA `960bb74ff5fa1a457cb26157a6cb3cfbae6d2272cd0d5cccef494918ebbe4be6`.
PID20068 và review đã terminal, không numerical jobs còn chạy của pilot.

**Tiếp:** [history protocol](NASDAQ100-HISTORY-PROTOCOL-20261108.md) cho
2019/2022 và Nov–Dec warmup năm trước, không tải toàn1990+, không PnL trước
registered recipe/cost/risk. R061 là hypothesis NASDAQ H4SMA20/80 dự kiến,
chưa implemented policy hoặc challenge candidate. Goal C1/C2 active.
