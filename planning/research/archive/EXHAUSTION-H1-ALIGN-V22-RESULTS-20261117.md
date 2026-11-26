# V22 — cổng exhaustion, H1 20:00 và MT5 preflight

**Hai cổng G_L3 đều rớt Development; H120:00 khôi phục phần lớn endpoint nhưng chưa có breadth booster đủ điều kiện. Giữ V16/V19 BASE_GUARD, chưa đủ căn cứ mua Challenge.**

PR100/head `1118904` merge `ec0cbe7`, nhánh V21 đã xóa. Protocol `98dd4ec`, implementation `5236af1`, Dev freeze `f0b823a` trước Full anatomy; PR101 để mở. Giữ source/freezes/negative attempts, Trader pin và VI WIP; không broker/account/provider/deploy/Astra/memory.

## 1. Top10 so với L3: giữ siêu lệnh vẫn chưa đủ

Global top10 có **9 EURUSD F5 và1 Gold F4**; Dev-only top10 có **8 EURUSD F5 và2 Gold F4**. G_L3 chỉ chặn F3/F4 nên phần lớn siêu lệnh EUR được giữ sẵn theo scope. Không có Gold F3 trong hai danh sách top10 này; không suy rằng F3 sẽ không có tail lớn trong tương lai.

Các tỷ lệ dùng high/low ngàyUTC từ M1 đóng trước decision và D1 Wilder ATR14 đã đóng. Signal F4 dùng H1, F3/F5 dùng H4; mẫu số Body/Range là ATR H4 đã biết. Edge gap là khoảng từ executable entry đến biên cùng chiều của ngày: GoldUSD/oz, FX tỷ giá; số âm có thể là entry vượt biên cũ, không phải dư địa lợi nhuận bảo đảm. Source/context vẫn có assumptions.

### Global top10 đã exposed từ V21 (chỉ anatomy sau freeze)

| Ngày UTC | Nhánh/chiều | NetR | Day/ATR D1 | Edge gap | Body/ATR H4 | Range/ATR H4 | Provisional |
|---|---|---|---|---|---|---|---|
| 2023-03-15 08:00 | EUR F5 SELL | 7.646 | 0.402 | 0.00123 | 0.331 | 0.632 | False |
| 2025-08-22 12:00 | EUR F5 BUY | 6.788 | 0.429 | 0.00109 | 0.375 | 0.561 | True |
| 2018-03-19 08:00 | EUR F5 BUY | 5.460 | 0.258 | 0.00130 | 0.163 | 0.582 | False |
| 2024-02-02 12:00 | EUR F5 SELL | 5.156 | 0.389 | 0.00136 | 0.089 | 0.821 | False |
| 2023-04-25 04:00 | EUR F5 SELL | 4.357 | 0.189 | 0.00014 | 0.154 | 0.523 | False |
| 2022-08-02 04:00 | EUR F5 SELL | 4.209 | 0.343 | 0.00175 | 0.224 | 0.792 | False |
| 2018-06-26 04:00 | EUR F5 SELL | 4.152 | 0.226 | 0.00111 | 0.255 | 0.638 | False |
| 2023-10-12 08:00 | EUR F5 SELL | 3.783 | 0.256 | 0.00002 | 0.276 | 0.641 | False |
| 2019-08-01 15:00 | Gold F4 BUY | 3.766 | 0.732 | 0.47200 | 1.251 | 1.367 | False |
| 2021-07-14 04:00 | EUR F5 BUY | 3.357 | 0.175 | 0.00011 | 0.288 | 0.455 | True |

### Top10 riêng Development dùng cho cửa giữ>=90%

| Ngày UTC | Nhánh/chiều | NetR | Day/ATR D1 | Edge gap | Body/ATR H4 | Range/ATR H4 | Provisional |
|---|---|---|---|---|---|---|---|
| 2023-03-15 08:00 | EUR F5 SELL | 7.646 | 0.402 | 0.00123 | 0.331 | 0.632 | False |
| 2018-03-19 08:00 | EUR F5 BUY | 5.460 | 0.258 | 0.00130 | 0.163 | 0.582 | False |
| 2023-04-25 04:00 | EUR F5 SELL | 4.357 | 0.189 | 0.00014 | 0.154 | 0.523 | False |
| 2022-08-02 04:00 | EUR F5 SELL | 4.209 | 0.343 | 0.00175 | 0.224 | 0.792 | False |
| 2018-06-26 04:00 | EUR F5 SELL | 4.152 | 0.226 | 0.00111 | 0.255 | 0.638 | False |
| 2023-10-12 08:00 | EUR F5 SELL | 3.783 | 0.256 | 0.00002 | 0.276 | 0.641 | False |
| 2019-08-01 15:00 | Gold F4 BUY | 3.766 | 0.732 | 0.47200 | 1.251 | 1.367 | False |
| 2021-07-14 04:00 | EUR F5 BUY | 3.357 | 0.175 | 0.00011 | 0.288 | 0.455 | True |
| 2023-12-01 15:00 | Gold F4 BUY | 2.975 | 0.700 | 7.11900 | 0.556 | 0.960 | False |
| 2023-06-02 08:00 | EUR F5 SELL | 2.657 | 0.281 | 0.00036 | 0.199 | 0.607 | False |

### Tất cả45 L3, tách giai đoạn


**Development2018–2023: 27 lệnh / -10.858R.**

| Ngày UTC | Nhánh/chiều | NetR | Day/ATR D1 | Edge gap | Body/ATR H4 | Range/ATR H4 | Provisional |
|---|---|---|---|---|---|---|---|
| 2018-04-03 15:00 | Gold F4 SELL | -1.063 | 0.915 | 0.42800 | 0.912 | 1.051 | False |
| 2018-09-12 20:00 | Gold F3 BUY | -0.124 | 1.393 | 1.98000 | 0.760 | 1.216 | False |
| 2019-07-17 20:00 | Gold F3 BUY | -0.179 | 1.288 | -0.30800 | 0.354 | 0.729 | False |
| 2019-07-25 20:00 | Gold F3 SELL | -0.115 | 1.107 | 3.07000 | 0.480 | 0.937 | False |
| 2019-08-23 16:00 | Gold F3 BUY | -0.235 | 1.610 | 1.11500 | 3.348 | 3.509 | False |
| 2020-03-11 20:00 | Gold F3 SELL | -0.113 | 1.226 | 3.37000 | 0.732 | 0.980 | False |
| 2020-03-31 20:00 | Gold F3 SELL | -0.092 | 0.905 | 0.71000 | 1.830 | 1.869 | False |
| 2020-06-19 16:00 | Gold F3 BUY | -0.042 | 0.913 | 2.76500 | 0.873 | 1.469 | False |
| 2020-06-30 16:00 | Gold F3 BUY | -0.274 | 0.935 | 2.68400 | 1.932 | 2.299 | False |
| 2021-03-17 20:00 | Gold F3 BUY | -0.114 | 0.975 | 6.10500 | 1.664 | 2.381 | False |
| 2021-03-29 20:00 | Gold F3 SELL | -0.019 | 1.093 | 5.67000 | 0.028 | 0.689 | False |
| 2021-06-01 15:00 | Gold F4 SELL | -1.003 | 1.076 | 2.64000 | 1.043 | 1.981 | False |
| 2021-06-03 16:00 | Gold F3 SELL | -0.277 | 2.005 | 4.12000 | 2.388 | 2.986 | False |
| 2021-08-23 16:00 | Gold F3 BUY | -0.096 | 1.415 | 1.53500 | 1.533 | 1.857 | False |
| 2021-10-29 16:00 | Gold F3 SELL | -0.638 | 1.307 | 6.19000 | 1.628 | 2.344 | False |
| 2022-05-19 16:00 | Gold F3 BUY | -0.163 | 1.286 | 6.44700 | 0.930 | 1.712 | False |
| 2022-08-15 12:00 | Gold F3 SELL | -1.011 | 1.284 | 2.23100 | 1.309 | 1.678 | False |
| 2022-08-30 15:00 | Gold F4 SELL | -0.077 | 0.916 | 2.71600 | 0.983 | 1.294 | False |
| 2022-09-01 15:00 | Gold F4 SELL | -0.401 | 0.965 | 3.46000 | 0.772 | 1.185 | False |
| 2022-09-02 15:00 | Gold F4 BUY | -1.041 | 1.043 | 0.40200 | 0.618 | 0.833 | False |
| 2022-11-01 15:00 | Gold F4 SELL | -0.206 | 1.066 | 14.68100 | 0.521 | 0.868 | False |
| 2022-11-30 20:00 | Gold F3 BUY | -0.012 | 0.980 | 0.71300 | 1.565 | 2.452 | False |
| 2022-12-01 15:00 | Gold F4 BUY | -0.099 | 1.273 | 1.33300 | 1.275 | 1.482 | False |
| 2023-01-03 15:00 | Gold F4 BUY | -1.032 | 1.011 | 4.79900 | 0.547 | 1.219 | False |
| 2023-03-01 15:00 | Gold F4 BUY | -1.013 | 0.929 | 1.99200 | 0.608 | 0.928 | False |
| 2023-04-03 16:00 | Gold F3 BUY | -0.381 | 1.344 | 2.21600 | 0.751 | 1.452 | False |
| 2023-07-03 15:00 | Gold F4 BUY | -1.038 | 0.922 | 0.57900 | 0.533 | 0.899 | True |

**Lịch sử2024–2026YTD đã exposed: 18 lệnh / -9.872R.**

| Ngày UTC | Nhánh/chiều | NetR | Day/ATR D1 | Edge gap | Body/ATR H4 | Range/ATR H4 | Provisional |
|---|---|---|---|---|---|---|---|
| 2024-01-24 20:00 | Gold F3 SELL | -0.157 | 1.041 | 1.01000 | 0.326 | 0.904 | False |
| 2024-02-23 20:00 | Gold F3 BUY | -0.197 | 1.233 | 3.70200 | 1.024 | 1.596 | False |
| 2024-02-29 16:00 | Gold F3 BUY | -0.677 | 1.181 | 2.27200 | 2.442 | 3.106 | False |
| 2024-03-01 15:00 | Gold F4 SELL | -1.050 | 0.954 | 7.36000 | 0.695 | 1.447 | False |
| 2024-04-01 15:00 | Gold F4 SELL | -0.894 | 1.316 | 7.41000 | 0.739 | 1.260 | False |
| 2024-05-09 20:00 | Gold F3 BUY | -0.015 | 0.990 | -0.01700 | 0.974 | 1.086 | False |
| 2024-06-27 15:00 | Gold F4 BUY | -0.292 | 1.023 | 1.49900 | 0.494 | 0.698 | False |
| 2024-10-31 15:00 | Gold F4 SELL | -0.991 | 1.867 | 0.01000 | 1.764 | 1.892 | False |
| 2025-02-03 15:00 | Gold F4 BUY | -1.024 | 1.888 | 0.70200 | 1.351 | 1.482 | False |
| 2025-02-27 15:00 | Gold F4 SELL | -0.139 | 1.273 | 4.33300 | 0.966 | 1.439 | False |
| 2025-02-28 15:00 | Gold F4 SELL | -0.944 | 1.255 | 0.41700 | 0.864 | 1.070 | False |
| 2025-03-04 15:00 | Gold F4 SELL | -0.936 | 1.105 | 21.67000 | 1.086 | 1.121 | False |
| 2025-03-10 20:00 | Gold F3 SELL | -0.110 | 0.940 | 5.46000 | 1.105 | 1.557 | False |
| 2025-03-27 12:00 | Gold F3 BUY | -1.007 | 0.952 | 0.86200 | 1.254 | 1.489 | False |
| 2026-01-16 16:00 | Gold F3 SELL | -0.477 | 1.052 | 34.32000 | 1.158 | 2.329 | False |
| 2026-07-08 16:00 | Gold F3 SELL | -0.828 | 0.997 | 12.42000 | 0.651 | 1.514 | False |
| 2026-07-31 15:00 | Gold F4 BUY | -0.053 | 0.928 | 57.31200 | 0.677 | 0.842 | False |
| 2026-09-23 16:00 | Gold F3 SELL | -0.081 | 0.924 | 4.65000 | 0.716 | 1.093 | False |

L3 đòi cả net<=0 và MFE<0,25R sau entry, nên việc L3 có Day/ATR cao là một phần định nghĩa đã chọn. Phân bố L3-vs-winner không là bằng chứng độc lập rằng tỷ lệ này dự báo loss. L3 cũng không phải pool lỗ lớn nhất: L4 ở V21 đóng góp−99,86R.

### Hai biến thể tiên nghiệm, khóa trước outcome

- A: F3/F4, chặn Day/ATR>0,90; F5 giữ nguyên.
- B: F3/F4, chặn vượt phân vị90% Dev theo sleeve: F3=1.485, F4=1.313. Fit chỉ covariates, không labels/returns.
- Giữ>=9/10 Dev top10, tăng net/ExTop10, giảm equityDD, worst daily không tăng. Không chỉnh SL/exit/risk.

| Dev OLHC | Lệnh | NetR | EquityDD R | Worst day% | ExTop5 R | ExTop10 R | DevTop10 giữ |
|---|---|---|---|---|---|---|---|
| BASE_GUARD | 340 | 23.852 | 12.207 | 0.611 | -1.971 | -18.509 | 10/10 |
| G_L3_A | 262 | 23.329 | 12.788 | 0.478 | -2.495 | -19.032 | 10/10 |
| G_L3_B | 324 | 22.491 | 13.006 | 0.611 | -3.333 | -19.870 | 10/10 |

Equity metrics là fixed150USD marked book, không adaptive-account Daily DD. Cả hai M1 orderings cùng verdict. ExTop10 loại từng candidate own top10; JSON còn cột loại original baseline top10 identities.

| Gate | Bỏ lệnh | Bỏ winners | WinnerR mất | LoserR tránh | Trong đó L3 | Lý do rớt |
|---|---|---|---|---|---|---|
| G_L3_A | 78 | 35 | 17.813 | -17.289 | 27 / -10.858R | NET_NOT_HIGHER; EQUITY_DD_NOT_LOWER; EX_TOP10_NOT_HIGHER |
| G_L3_B | 16 | 6 | 3.973 | -2.612 | 2 / -0.512R | NET_NOT_HIGHER; EQUITY_DD_NOT_LOWER; EX_TOP10_NOT_HIGHER |

A chặn được toàn27 L3 Dev nhưng đồng thời bỏ các lệnh thắng; giữ10 siêu lệnh vẫn làm phần nền yếu hơn. B cũng bỏ winner nhiều hơn loss tránh được. **Không chọn ngưỡng thứ ba**, không dùng body/edge của bảng Full để cứu hai gates. Target−20,73R là pool hindsight toàn kỳ, không là khoản thu hồi được biết trước.

## 2. H1 20:00: hết lệch lưới, chưa hết missing hoặc economic failure

Đã reuse22 M1 cases không đổi, tính lại6 GBP B2, thêm6 AUD B2 riêng:34 cases báo cáo, 12 cases mới đo. B3 giữ4 Gold/US500 cases; không tự thêm B3 FX để đổi budget. Threshold sweep/ATR/side/stop không đổi. H1 cut=floor_hour(min20:30, early guard), thường20:00; M1 vẫn20:30 và US500/session clamp cũ. H1 fills dùng observed opens đúng boundary, không forward-fill hoặc chọn last quote trước gap. Đây là exit-policy mới có registration, không sửa V21.

| Asset (cộng recipe observations) | Raw | Có endpoint | Coverage% | Missing | Stage0 |
|---|---|---|---|---|---|
| GBPUSD | 2288 | 2282 | 99.738 | 6 | 0 |
| AUDUSD | 1795 | 1789 | 99.666 | 6 | 0 |

Các recipe có tín hiệu chồng nhau nên bảng này không đếm unique trades. GBP V21 chỉ12/2288 recipe observations được định giá ở mốc cũ; V22 có2282/2288, vẫn6 missing. Giờ đúng lưới không đồng nghĩa100% dữ liệu hoặc an toàn tuyệt đối.

| Asset / recipe | Raw/priced | Cost đủ% | 2018 pip | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| GBPUSD / B2:PD:sweep=0.1 | 509/507 | 91.7 | 4.69 | -1.44 | -13.65 | -3.21 | 8.24 | -5.81 |
| GBPUSD / B2:PD:sweep=0.3 | 285/285 | 97.2 | 6.99 | -9.32 | -5.73 | -7.03 | 19.16 | -4.88 |
| GBPUSD / B2:PD:sweep=0.6 | 75/75 | 98.7 | 22.65 | -9.59 | 4.81 | -11.60 | 41.08 | -21.59 |
| GBPUSD / B2:ASIA:sweep=0.1 | 792/788 | 87.6 | 1.91 | -0.18 | -12.06 | 7.66 | -7.01 | -3.80 |
| GBPUSD / B2:ASIA:sweep=0.3 | 479/479 | 96.2 | -0.05 | -9.08 | -10.21 | 2.03 | -8.47 | 2.99 |
| GBPUSD / B2:ASIA:sweep=0.6 | 148/148 | 100.0 | -0.18 | -3.30 | -7.78 | -3.10 | -3.11 | 5.93 |
| AUDUSD / B2:PD:sweep=0.1 | 428/427 | 54.4 | 0.33 | 0.85 | -2.20 | 1.45 | -1.16 | -5.28 |
| AUDUSD / B2:PD:sweep=0.3 | 228/227 | 73.2 | 7.43 | 3.29 | -3.14 | 4.70 | 2.38 | -4.33 |
| AUDUSD / B2:PD:sweep=0.6 | 70/70 | 91.4 | 6.23 | 2.98 | -6.19 | 1.55 | 17.09 | -7.22 |
| AUDUSD / B2:ASIA:sweep=0.1 | 689/686 | 43.1 | -1.55 | -1.43 | -6.21 | -1.97 | -5.24 | -0.35 |
| AUDUSD / B2:ASIA:sweep=0.3 | 314/313 | 63.1 | 1.94 | -5.75 | -4.92 | -3.39 | -3.22 | 1.52 |
| AUDUSD / B2:ASIA:sweep=0.6 | 66/66 | 93.9 | 8.48 | -1.66 | -11.08 | 5.74 | -12.73 | 3.18 |

Cột từng năm là mean raw net stress/trade theo pip, chưa SL-Active. FX model gồm Bid/Ask đã chứa spread, commission7USD/lot và slippage2USD/lot roundtrip; modeled swap0 vì same-day. Cost-only retention tách coverage; không gọi missing net0. Tất cả12 H1 recipes đều có ít nhất một năm âm; các biên dương lớn riêng năm2022 không được dùng để chọn subgroup. **0/34 qua đủ Stage-0**. Không chạy SL-Active cho losers; nguồn H1 cũng chưa đủ intrahour equity/DD.

## 3. Không có child đi tiếp: lifecycle baseline reuse

Dev freeze có selected=null trước Full entry snapshots. Không chạy mới child trên2024–2026, không105 monthly starts/5.000 bootstrap child. Full chỉ bảng anatomy baseline. Sau đây là receipts lịch sử V16/V19 đã có, không phải kết quả mới V22; monthly starts overlap, median có điều kiện chỉ nhóm hoàn tất.

| Baseline | Hai vòng/105 | Median tháng | Daily% | Static% |
|---|---|---|---|---|
| V16 | 71 | 47.075 | 1.963 | 6.383 |
| V19 | 71 | 48.061 | 2.027 | 6.383 |

| MC OLHC PRIMARY100 /5.000 | Hai vòng24 tháng% | Hai vòng36 tháng% |
|---|---|---|
| V16 | 14.320 | 33.360 |
| V19 | 14.500 | 33.560 |

Bootstrap frequencies không là xác suất tương lai; source/cost stress và32 paths chưa xác minh còn nguyên. Không kết luận đã giải quyết time-fit hoặc đủ payout. Giữ baseline thay vì ép một winner.

## 4. MT5 preflight, hiệu năng và storage

Lệnh mới: `python -m tooling.ai_engines.ftmo_trial_runner --check-mt5-ready` (dùng observer runtime trong quickstart). Output private MT5_PREFLIGHT.json; exit2 khi chưa sẵn sàng, không fallback replay trong diagnostic này. Kiểm đã thấy terminal trước initialize, FTMO DEMO/TRIAL USD, connected, last reported pingµs→ms, symbol info/quote age. Không symbol_select/login/order_check/order_send.

Máy hiện có **0 terminal**; verdict `NO_RUNNING_TERMINAL`. Probe 594.8ms; whole fresh CLI **0.970s**, target1s:True. Đây chỉ ca không có terminal; attach/network live chưa kiểm. Không bịa ping, không coi terminal-reported ping là RTT mới; shadow vẫn cần session/news/seeds/spec parity.

Full suite **1280 PASS/0skip**, giữ1.261 V21 IDs; wall **13.013s**. Hard<=13,5s:True; stretch<13,2s:True.

Smoke10 fresh serial processes/same78 IDs: **10/10 <0,75s**, stretch<0,72s:9/10; median **0.678s**, max **0.720108s**. Giữ tất cả mẫu, không retry streak; startup/import/fixture IO nằm trong wall. Stretch không tự gắn PASS khi thiếu dù chỉ0,1ms.

14 tables Zstd9: 1,241,511→222,119 bytes, SHA256/roundtrip mọi bảng. Job riêng 2.71MiB tại inventory, không cache giá mới/xóa nguồn. Small reports/freeze trong Git; audit/feed source vẫn read-only.

| Kho logical | V21 baseline GiB | Sau GiB | DeltaGiB | Errors |
|---|---|---|---|---|
| D | 197.378 | 197.379 | 0.001 | 2 |
| E | 215.366 | 215.369 | 0.003 | 0 |

Non-atomic inventories có thể gồm hoạt động khác; không gọi delta là physical bytes freed. D giữ2 read errors VI, không thay quyền/WIP. Audit riêng kiểm retained identities, Decimal cash, Dev/Full covariate parity,22 M1 results reuse,12 H1 source endpoints/net legs và every compressed hash. Cùng tác giả/feed, không independent human review.

| Hậu kiểm | Quyết định |
|---|---|
| Giữ top10 nhưng net/DD tệ hơn | Bác cả A/B; top-tail retention là điều kiện cần, chưa đủ |
| H1 giờ lẻ làm mất endpoint | Clamp20:00 có đăng ký, giữ missing thật; không tạo M1 giả |
| MT5 preflight dễ bị hiểu là execution-ready | Tách read-only readiness, live attach unknown, shadow vẫn gated |
| Smoke stretch hụt sát ngưỡng | Giữ exact sample và verdict; không rerun chọn streak |

PR101 để mở; three exact-head CI và downloaded IDs chốt sau push trong private `ci-exact-head-reconciliation.json` / `completion-receipt.json`. Chưa broker orders hoặc payout thật.

[Protocol](EXHAUSTION-H1-ALIGN-V22-PROTOCOL-20261117.md) · [Freeze](EXHAUSTION-H1-ALIGN-V22-FREEZE-20261117.json) · [JSON](EXHAUSTION-H1-ALIGN-V22-RESULTS-20261117.json) · [Quickstart](QUICKSTART-FTMO-FREE-TRIAL.md)

Primary docs: [MQL5 Python initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py), [terminal information](https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py), [FTMO holding rules](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/). Các nguồn không thay account-specific snapshot/session/news còn thiếu.
