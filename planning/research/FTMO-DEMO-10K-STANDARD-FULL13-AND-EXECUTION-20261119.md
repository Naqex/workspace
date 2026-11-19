# FTMO Demo 10k Standard · commission, trượt SL và đủ 13 mã

19/11/2026. Đã đối soát **16 vòng Demo trên FTMO-Demo USD 10k Standard 1:100** gồm 12 vòng market và 4 vòng có SL. Số lần gọi gửi lệnh là **29**, thấp hơn hai lần mỗi vòng vì 3 lệnh thoát do SL tự khớp trên server. Kết thúc với **0 vị thế, 0 lệnh chờ**, thay đổi số dư Demo **−18,59 USD**. Đã đọc bar đóng H1/H4/D1 trực tiếp từ MT5 để thống kê biên độ, không đọc kho holdout đã khóa hoặc chạy tín hiệu.

**Điểm mới so với lát 0,01 lot.** EURUSD và GBPJPY đo đúng **5,00 USD/lot khứ hồi**. XAUUSD quan sát **5,20 USD/lot** tại giá lúc thử, khớp biểu phí phần trăm giá trị danh nghĩa. US500.cash đo **0 USD commission ở 1,00 lot**. Spread từ các mẫu đã thu riêng. [Biểu phí chính thức FTMO](https://ftmo.com/en/blog/trading-updates/trading-update-11-sep-2025/) · [Thông số mã](https://ftmo.com/en/symbols/).

## 1. Commission và trượt giá có đối soát

Tất cả vòng mở BUY rồi đóng đúng vị thế. Trượt dương là bất lợi. Độ trễ SDK là thời gian từ lúc gọi gửi đến khi nhận phản hồi trên host. Tệp JSON giữ từng giá tham chiếu, giá khớp, commission vào/ra, fee, profit và timestamp UTC. Mốc server setup→done tách khỏi độ trễ host để tránh trừ hai đồng hồ lệch nhau.

| Mã | Lot × số vòng | Commission mỗi phía quan sát | USD/lot khứ hồi | Trượt market RT min / med / max | Mẫu market đúng thời lượng | SDK p50 / max (ms) |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 0.10 × 3 | 0.25 USD | 5.00 | -0.300 / -0.200 / +0.000 pip | 3 | 363 / 544 |
| GBPJPY | 0.10 × 3 | 0.25 USD | 5.00 | -0.100 / +0.000 / +0.000 pip | 3 | 397 / 464 |
| XAUUSD | 0.10 × 3 | 0.26 USD | 5.20 | +0.010 / +0.015 / +0.020 USD/oz | 2 | 383 / 418 |
| US500.cash | 1.00 × 3 | -0.00 USD | -0.00 | +0.000 / +0.100 / +0.100 điểm | 3 | 393 / 416 |

Commission EURUSD/GBPJPY là **0,25 USD mỗi phía** trên 0,10 lot. Vàng là **0,26 USD mỗi phía** trên 0,10 lot, khớp mức **0,0007% notional** khi tính riêng giá khớp của từng phía và làm tròn cent. Khoảng giá của ba vòng gần nhau nên dữ liệu Demo tự nó không phân biệt được công thức phần trăm và một mức phí cố định trùng số ở khoảng giá này. Phân loại dựa thêm vào biểu phí chính thức. FX còn lại dùng mức công bố 5 USD/lot và chưa đối soát trực tiếp từng mã. Fee bổ sung trên các deal kiểm là 0. Bốn mã trong snapshot bao phủ toàn bộ nhóm FX chính/chéo, kim loại và chỉ số hiện có, nên không thêm mã thứ năm.

Một vị thế XAUUSD market mất **90,839 giây** do bộ đọc thấy trạng thái lệnh trung gian và dừng. Đã mở lại phiên riêng để đóng đúng ticket, xác minh vị thế phẳng rồi tiếp tục các vòng còn lại. Commission vẫn tính đủ ba vòng XAUUSD. Phân bố trượt market và độ trễ chỉ dùng hai vòng Vàng đúng thời lượng. So với repo, kết quả xác nhận commission EURUSD B0 5 USD/lot và công thức Vàng. Chất lượng mẫu chưa đủ giảm slippage stress từng có hoặc suy ra phân bố đuôi.

| Mã SL | Lot | SL gốc → fill | Trượt giá SL | Số khớp / thử | Ghi chú |
|---|---:|---:|---:|---:|---|
| EURUSD | 0.05 | 1.10075 → 1.10076 | -0.10 pip | 1/2 | Một vòng hết giờ và đóng market sau 59,347 giây. |
| XAUUSD | 0.05 | 3736.08 → 3736.06 | +0.02 USD/oz | 1/1 | Thoát do stop broker. |
| US500.cash | 0.50 | 7410.29 → 7410.45 | -0.16 điểm | 1/1 | Thoát do stop broker. |

SL khớp được xác nhận từ lý do deal DEAL_REASON_SL và mức stop của order mở. Lượt hết giờ market tách khỏi mẫu SL. [MT5 Deal Properties](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties).

## 2. Xếp hạng 13 mã theo chi phí, ATR và dữ liệu

Đã ghi **39/39 chuỗi** với **1,740,707 bar đóng** từ FTMO-Demo. Loại bar hiện tại bằng offset 1 và kiểm lại mốc bar 0. Timestamps trong Parquet giữ nguyên nhãn giờ server. Khoảng cách giữa bar có thể do nghỉ phiên, cuối tuần hoặc khoảng trống nguồn.
Cả 39 chuỗi đã thử yêu cầu 99.999 bar theo giới hạn chart 100.000 bar, rồi giảm yêu cầu khi MT5 không trả dữ liệu cho kích thước đó. Các mốc đầu/cuối là độ sâu thực tế đã thu được. Chưa xác minh độ sâu khi nâng giới hạn chart hoặc đổi phiên truy cập. [Giới hạn lịch sử chart của MT5](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py).

ATR Wilder(14) dùng nến native từng khung, tính trung vị toàn chuỗi và trung vị 90 ngày gần nhất theo lịch server. Bảng tỷ lệ dùng trung vị 90 ngày. Friction bằng spread trung vị cộng commission và fee. Mẫu spread London 120 giây của audit trước là cùng một thước đo cho 13 mã. Swap dương trong cột tỷ lệ là tốn phí, âm là được cộng. JPY và FX đổi về pip, Vàng dùng USD/oz, US500.cash dùng điểm.

| Tier | Mã | Bar H1 / H4 / D1 | Ngày đầu H1 / H4 / D1 | Spread med / P95 | Phí RT USD/lot | ATR90 H1 / H4 / D1 | Phí/ATR H1 / H4 / D1 | Swap BUY / SELL 1× → 3× (% ATR D1) |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | US500.cash | 35,235 / 9,794 / 2,298 | 2017-12-29 / 2017-12-29 / 2017-12-29 | 0.60 / 0.60 | 0.60 | 14.84 / 28.90 / 74.59 | 4.04% / 2.08% / 0.80% | +1.17% / +1.19% → +3.51% / +3.57% |
| 1 | EURUSD | 99,998 / 41,490 / 6,924 | 2010-10-13 / 2000-03-29 / 2000-03-29 | 0.10 / 0.30 | 6.00 | 10.15 / 21.52 / 58.93 | 5.91% / 2.79% / 1.02% | +1.44% / -0.05% → +4.31% / -0.15% |
| 1 | USDJPY | 99,998 / 41,478 / 6,923 | 2010-10-14 / 2000-03-29 / 2000-03-29 | 0.30 / 0.80 | 6.88 | 18.49 / 39.18 / 103.28 | 5.95% / 2.81% / 1.06% | -0.26% / +1.87% → -0.77% / +5.61% |
| 1 | EURJPY | 75,062 / 37,658 / 6,797 | 2014-10-22 / 2002-09-10 / 2000-03-29 | 0.90 / 1.10 | 10.63 | 20.22 / 42.65 / 118.14 | 8.40% / 3.98% / 1.44% | -0.18% / +0.94% → -0.54% / +2.83% |
| 1 | GBPUSD | 99,998 / 41,454 / 6,923 | 2010-10-04 / 2000-03-29 / 2000-03-29 | 0.70 / 0.80 | 12.00 | 12.33 / 26.20 / 66.19 | 9.73% / 4.58% / 1.81% | +0.69% / +0.81% → +2.08% / +2.42% |
| 2 | XAUUSD | 99,998 / 34,406 / 5,774 | 2010-03-19 / 2004-06-11 / 2004-06-11 | 0.35 / 0.39 | 40.23 | 16.42 / 34.93 / 90.83 | 2.45% / 1.15% / 0.44% | +0.62% / +0.05% → +1.87% / +0.14% |
| 2 | USDCHF | 99,998 / 41,480 / 6,923 | 2010-10-13 / 2000-03-29 / 2000-03-29 | 0.50 / 0.60 | 10.94 | 9.89 / 21.23 / 52.84 | 9.31% / 4.34% / 1.74% | -0.37% / +2.56% → -1.11% / +7.68% |
| 2 | USDCAD | 75,062 / 41,486 / 6,925 | 2014-10-23 / 2000-03-29 / 2000-03-29 | 0.40 / 0.60 | 7.80 | 10.21 / 22.02 / 60.31 | 10.92% / 5.07% / 1.85% | -0.12% / +1.79% → -0.35% / +5.38% |
| 2 | AUDJPY | 99,998 / 41,124 / 6,865 | 2010-10-14 / 2000-03-29 / 2000-03-29 | 1.00 / 1.20 | 11.25 | 16.34 / 35.39 / 86.94 | 11.01% / 5.09% / 2.07% | -0.43% / +1.75% → -1.30% / +5.26% |
| 2 | AUDUSD | 99,998 / 41,480 / 6,923 | 2010-10-14 / 2000-03-29 / 2000-03-29 | 0.40 / 0.40 | 9.00 | 8.54 / 17.56 / 44.41 | 10.54% / 5.13% / 2.03% | +0.55% / +1.59% → +1.66% / +4.76% |
| 2 | GBPJPY | 75,062 / 41,480 / 6,925 | 2014-10-22 / 2000-03-29 / 2000-03-29 | 2.40 / 2.80 | 20.01 | 24.28 / 51.96 / 140.24 | 13.18% / 6.16% / 2.28% | -0.42% / +1.79% → -1.26% / +5.38% |
| 2 | NZDUSD | 99,998 / 41,475 / 6,923 | 2010-10-13 / 2000-03-29 / 2000-03-29 | 0.60 / 0.60 | 11.00 | 8.21 / 17.84 / 44.91 | 13.39% / 6.17% / 2.45% | +1.07% / -0.00% → +3.21% / -0.00% |
| 2 | EURGBP | 99,998 / 41,457 / 6,919 | 2010-10-14 / 2000-03-29 / 2000-03-29 | 0.50 / 0.60 | 11.58 | 4.92 / 9.99 / 25.62 | 17.87% / 8.81% / 3.43% | +2.65% / -0.06% → +7.96% / -0.18% |

Tier 1 cần phí H4 ≤5%, D1 ≤2,5%, swap 3× bên tốn hơn ≤6%, tối thiểu 252 bar D1 và đặt được cả hai mức SL trên 10k. Tier 2 khi vượt ngưỡng thuận lợi, margin >15% ở một khung hoặc chỉ một khung khả thi. Tier 3 nếu phí H4 >10%, D1 >5%, hoặc cả hai khung vượt khả năng đặt lot. Các ngưỡng dùng xếp ưu tiên nghiên cứu, chưa gắn điều kiện edge.

**Tier 1** gồm US500.cash, EURUSD, USDJPY, EURJPY, GBPUSD. **Tier 2** gồm XAUUSD, USDCHF, USDCAD, AUDJPY, AUDUSD, GBPJPY, NZDUSD, EURGBP. **Tier 3** trống theo ngưỡng đã dùng.

Ưu tiên **US500.cash H4** và **EURUSD** theo chi phí và độ sâu. **EURGBP** có phí H4 và swap BUY cao so với ATR. **XAUUSD** có chi phí/ATR thấp ở giai đoạn biến động gần đây, nhưng lot sàn chặn D1 trên 10k. GBPJPY vẫn có spread tuyệt đối cao, còn ATR lớn hơn nên nằm Tier 2 theo tỷ lệ. Phí thấp trong cửa sổ đo không quyết định được lợi thế tín hiệu.

### Đặt lot và margin trên 10k và 50k

Dùng rủi ro 0,50% vốn (50 hoặc 250 USD), stop bằng ATR gần đây. Tính lỗ từ giá giữa cộng phí vào/ra, làm tròn xuống bước lot và kiểm margin. Mỗi ô là lot / USD margin. Kịch bản 50k dùng thông số tài khoản 10k. Chưa tính stop gap, vị thế đồng thời, margin tier ở tài khoản khác hoặc stress slippage.

| Mã | H4 10k | H4 50k | D1 10k | D1 50k | Lỗ lot sàn H4 / D1 (USD) |
|---|---:|---:|---:|---:|---:|
| US500.cash | 1.69 / 250.58 | 8.47 / 1255.89 | 0.66 / 97.86 | 3.32 / 492.27 | 0.30 / 0.75 |
| EURUSD | 0.22 / 242.15 | 1.13 / 1243.77 | 0.08 / 88.05 | 0.41 / 451.28 | 2.21 / 5.95 |
| USDJPY | 0.19 / 190.00 | 0.99 / 990.00 | 0.07 / 70.00 | 0.38 / 380.00 | 2.52 / 6.53 |
| EURJPY | 0.18 / 198.12 | 0.90 / 990.61 | 0.06 / 66.04 | 0.33 / 363.22 | 2.77 / 7.49 |
| GBPUSD | 0.18 / 237.08 | 0.91 / 1198.59 | 0.07 / 92.20 | 0.37 / 487.34 | 2.74 / 6.74 |
| XAUUSD | 0.01 / 74.63 | 0.07 / 522.38 | 0.00 / 0.00 | 0.02 / 149.25 | 35.33 / 91.24 |
| USDCHF | 0.19 / 190.00 | 0.95 / 950.00 | 0.07 / 70.00 | 0.39 / 390.00 | 2.63 / 6.38 |
| USDCAD | 0.30 / 300.00 | 1.54 / 1540.00 | 0.11 / 110.00 | 0.58 / 580.00 | 1.62 / 4.29 |
| AUDJPY | 0.21 / 140.96 | 1.07 / 718.24 | 0.09 / 60.41 | 0.45 / 302.06 | 2.33 / 5.55 |
| AUDUSD | 0.27 / 181.24 | 1.35 / 906.19 | 0.11 / 73.84 | 0.55 / 369.19 | 1.85 / 4.53 |
| GBPJPY | 0.14 / 184.40 | 0.72 / 948.33 | 0.05 / 65.86 | 0.27 / 355.63 | 3.45 / 8.97 |
| NZDUSD | 0.26 / 143.75 | 1.32 / 729.80 | 0.10 / 55.29 | 0.54 / 298.56 | 1.89 / 4.60 |
| EURGBP | 0.34 / 374.23 | 1.74 / 1915.18 | 0.14 / 154.10 | 0.71 / 781.48 | 1.43 / 3.49 |

**XAUUSD D1** cần khoảng **91.24 USD** ở 0,01 lot trên ngân sách 50 USD. Kịch bản 50k đặt được **0.02 lot**. Nếu JSON có order_calc_margin ở đúng lot, bảng lấy kết quả ước tính native theo phía cao hơn. Còn lại dùng margin mỗi lot theo snapshot. Mọi số margin đều dựa trên 10k Demo.

## Spec tối thiểu cho News Guard và lịch phiên FTMO Standard

| Thành phần | Repo hiện có | Đầu vào và hợp đồng tối thiểu | Hành vi cần kiểm trước khi mở cổng |
|---|---|---|---|
| News Guard | Workspace có calendar_known và news_guard, bám phase, asset và mốc ±120 giây. Trader có clock profile FTMO-Demo. | FTMO Economic Calendar cung cấp cờ Restricted event và phạm vi mã. Dùng bảng FTMO làm nguồn phân loại, calendar MQL5 hoặc nguồn phát hành làm đối chiếu giờ và ID. Chưa xác minh endpoint tự động có hợp đồng ổn định của FTMO. | Manifest hết hiệu lực, giờ chưa rõ, event đổi giờ hoặc mapping mã chưa được xác nhận thì chặn tín hiệu mới. Funded Standard áp cửa sổ cho cả market, pending, SL và TP. Nếu chính sách giữ vị thế qua tin, phải xử lý rủi ro SL/TP từ trước cửa sổ thay vì trông vào chặn nút gửi. |
| Tuần thường và ngoại lệ | Script MQL5 xuất Quote/Trade sessions. parity kiểm cutoff có nằm trong phiên. session_deadline hiện dùng một deadline theo ngày UTC. | Baseline theo server, MT5 build, symbol, giờ tuần và clock profile. Lớp ngoại lệ riêng từ FTMO Trading Updates theo ngày server và symbol alias. Phân loại FULL_CLOSE, EARLY_CLOSE, LATE_OPEN, INTERRUPTED. | Áp ngoại lệ trước weekly, kiểm cả close/reopen, tính giờ nghỉ hơn 2 giờ, tính deadline riêng mỗi mã và mô hình lead time đóng. Có dữ liệu đủ phạm vi mới nhận exact_session_parity. |
| Reset ngày | Trader prop_session.calendar_oracle và repo FTMO adapter dùng Europe/Prague. | Reset theo 00:00 Prague, lưu cả timestamp UTC và ngày Prague. Giờ MT5 chuyển theo profile server đã kiểm, UTC+2 hiện tại và có thể UTC+3. | Test tuần Mỹ và châu Âu đổi DST lệch nhau và timestamp server bị lặp. Không dùng đồng hồ giao dịch làm reset. |
| Lịch sử nguồn | Repo có lịch Gold, FX và một số lịch chỉ số nghiên cứu, có mốc known_at rời rạc. | Lưu raw thông báo và phiên bản chuẩn hóa có SHA256, retrieved_at_utc, known_at_msc, phạm vi có hiệu lực và declared coverage. | Bản sửa giờ chỉ có tác dụng sau khi agent biết. Lịch research và ngày quote tồn tại chỉ là dữ liệu đối chiếu. Không chứng nhận lịch broker từ việc có nến ở ngày đó. |

**News manifest và dự kiến owner.** Một producer đọc nguồn công bố, lưu bản thô bất biến, rồi chuẩn hóa event_id, event label, event_at_msc UTC, known_at_msc, revision, restricted, assets, program scopes và nguồn URL/hash. Envelope giữ from_msc, to_msc, coverage_complete và as_of. MQL5 CalendarValueHistory dùng giờ server, nên cần lưu timestamp gốc và clock profile. FTMO là nguồn xác định sự kiện nào bị hạn chế, còn nhãn high-impact chung chỉ hỗ trợ so sánh. [Luật tin FTMO](https://ftmo.com/en/faq/can-i-trade-news/) · [Lịch kinh tế MQL5](https://www.mql5.com/en/docs/calendar).

**Holiday manifest và dự kiến owner.** Mỗi record có server_date, actual_symbol, close_at_utc_msc, reopen_at_utc_msc, exception_kind, known_at_msc, source_url, sha256 và clock_profile. Ngày chỉ định đóng cả ngày ghi FULL_CLOSE. Khi nguồn nói giờ nền tảng, ghi nguyên nhãn trước khi đổi sang UTC. Từ đó sinh view days theo contract adapter hiện có hoặc mở rộng rõ sang ngày × mã; không áp một giờ đóng của US500.cash cho toàn bộ FX.

**Fixture ngoại lệ đầu tiên.** FTMO công bố ngày 26/11/2026 theo GMT+2, US500.cash đóng 20:00 server và Metals CFD đóng 21:30 server. Sau đổi giờ, cutoff 20:30 UTC cần dời sớm cho cả hai, lần lượt trước 18:00 và 19:30 UTC. Nạp cả giờ mở lại và kiểm khoảng nghỉ trước khi chứng nhận. FTMO nêu miễn trừ Challenge/Verification và Swing cho hạn chế tin và nghỉ thị trường; guard thận trọng có thể mô phỏng funded Standard nếu protocol ghi rõ. [Trading Updates](https://ftmo.com/en/trading-updates/) · [Quy định giữ qua kỳ nghỉ](https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/).

**Điều kiện để đóng hai lỗ hổng.** Có nguồn tin có phiên bản và năng lực lấy tự động đã xác minh. Có manifest holiday 13 mã đủ khoảng hiệu lực và fixture cho DST, cập nhật sai thứ tự, ngày thanh khoản đóng sớm, reset Prague và mất coverage. Lượt này chốt thiết kế. Cờ exact_session_parity của lịch đầy đủ vẫn false.

## Thu spread nhiều phiên và lưu bằng chứng

Runner hỗ trợ --session-tag asia|london|ny|rollover --duration 180. Từ dữ liệu Parquet, --combine-spread ghép các cửa sổ theo mã và tag, kiểm SHA256, account binding và thời gian không trùng. Đã chạy smoke native London 20 giây, **13/13 mã, 202 quan sát, 0 lệnh**. Các cửa sổ Á, Mỹ và rollover mới được kiểm logic bằng fixture, chưa có mẫu native. [Quickstart](QUICKSTART-FTMO-FREE-TRIAL.md).

- [JSON đối soát](./FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.json).
- Inventory key ftmo-demo-full13-20261119. Parquet Zstd lưu tách khỏi deal trong kho private trên ổ E.
- Manifest ftmo-demo-full13-20261119/manifest.json, SHA256 958efae21180c0dfc2654de3ecc447effb88e0ddc12eb63e30aca894c6980f1c.
