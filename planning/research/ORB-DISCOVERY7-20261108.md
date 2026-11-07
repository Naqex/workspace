# Discovery7 — opening range và hồi giá có điều kiện

Frozen trước outcomes bốn rules mới. [Campaign C1/C2](CHALLENGE-CANDIDATE-CAMPAIGN-20261108.md)
giữ nguyên. Discovery4/5/6 đã dùng2023/2024 để định hướng; đây là historical
development/data-informed research, không cleanOOS hoặc bốn alpha độc lập.

| Rule mới | Range/entry/exit cố định |
|---|---|
| LondonORB |Range từ đúng bar08:00–09:00Europe/London; quyết định ở10:00/11:00/12:00London, close vượt high BUY/dưới low SELL; exit16London |
| NYORB |Range08:00–09:00America/New_York; quyết định10/11/12NY, close vượt high BUY/dưới low SELL; exit16NY |
| Asia→London |Đủ6observed bars09:00–15:00Asia/Tokyo cùng localdate; quyết định08/09/10/11/12London, close vượt range BUY/dưới low SELL; exit16London |
| BBflat |Parent BB20reentry; chỉ khi flat và trước entry abs(SMA20−SMA80)<=0,5WilderATR14 của priorbar. Entry re-cross band2populationSD theo parent; exit mean hoặc12observed hours |

Tất cả SL1,5WilderATR14/risk25USD/initial10k, noTP, maximumoneposition, shared
cost/slippage/financing/native execution. ORBs tối đa1emitted entry/ngàyUTC,
Mon–Fri của entryzone; rejected entry vẫn tiêu ngày, không retry. Không có
quote đúng giờ thì không bịa hoặc fill trước decision; missing range hours
skip, late exit next observed close rồi next quote. Flat filter chỉ chặn entry,
không khóa exit. Warmup100H1 đủ SMA80, indicators causal, clocksDST có tests.

H1close breakout là **adaptation chậm** của opening-range idea, không giả vờ
stop-order bắt ngay intrahour breakout. Nếu H1không có edge không loại toàn
family/M5/tick. BBflatthreshold0,5ATR là heuristic đăng ký, không ngưỡng đã được
paper chứng minh. Sources chỉ cơ chế/định nghĩa:
[NYFed stop cascades](https://www.newyorkfed.org/research/staff_reports/sr150.html),
[TradingView BB](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/),
đã có trong [catalogue](STRATEGY-CATALOGUE-20261107.md); không import code/data.

Screen hữu hạn4×two costs×2023/2024, từng năm account riêng bắt đầu flat.
Ưu tiên max2rules annual net dương ở cả hai năm/costs, rank weakest-year stress;
không forcedwinner hoặc tuning theo outcomes. Input/source/protocol pins trước
run, giữ negative/control history. Dossier/core accounting/causal fixtures trước
numeric; survivors vẫn cần tick/risk/prop/uncertainty/holdout/forward gates.
2025+closed, không broker/LLM/API trong numerical job, không đổi risk để ép target.
