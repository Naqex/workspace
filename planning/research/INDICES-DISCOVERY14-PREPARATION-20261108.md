# Discovery14 — kiểm capability SPY và US500 trước numerical strategy study

Sau [catalogue13](EURUSD-CATALOGUE-LONG-SCREEN-20261108.md),24FXversions không
qua stressretention. Chuyển sang equityintraday như một hypothesis khác, không
chỉnh giờ/risk/cost của các bản thất bại để kiếm winner.

## Research và giới hạn chuyển giao

[Paper tác giả, Beat the Market](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf)
đọc phần data/method08/11: SPY1minuteIQFeed, noiseband theo14ngày cùnggiờ,
cashsession NewYork,quyết định nửa giờ và exits nội ngày. Basecase khác version
cóVWAP/volatilitysizing. Đây là chiến lược auto bằng rules; không thể lấy
performance công bố làm bằng chứng cho bot hoặc CFD của project.

Ưu tiên nghiên cứu một adaptation dùng price-onlynoisebands; chưa đăng ký
signal/sizing/execution numerical. SPYETF khác US500indexCFD; bid/ask,marketopen/
DST/holidays/cashclose,contract/lot/cost và funding phải riêng. Tickvolume/CFD
volume không tự là exchangevolume cho VWAP. Không gọi nguyênbảnreplication khi
đổi asset hoặc thêm hardSL/risk0,25%. Không import code/data trả phí củapaper.

## Exact data-only probe

- Reuse installed isolated `dukascopy-node@1.51.1` tại workspace.runtime/research-data,
  supplychainreview/SRI/lock đã có. Không install/updatepackage/globalconfig,
  account/key/paidprovider hoặc browserrecovery.
- Cùng publicDukascopyprovider đã dùng choXAUfixture; chỉ instruments
  `spyususd` và`usa500idxusd`,UTC03/01/2023→04/01exclusive,M1BID vàM1ASK.
 4bounded requests,UTCdate/source/package/runtime/argv/hash/progress retained.
 2025+khôngđọc; không orders/strategyPnL hoặc simulation.
- WAFoff/token-cachefalse,retry0,requestinterval/pause300ms,batch2. Plain
 403/timeout/empty dừng và giữ log,không bypass/auth hoặc tự đổi provider.
- Kiểm header/schema,strictmonotonicminutegrid/OHLC/nonfinite/gaps/BidAsk,
  no sort/fill/syntheticquotes. Thống kê quotegrid/spread tạiM1open/close và
  quan sát coverage09:30–16:00America/New_York. Không gọi M1 extrema làtick.
- Installed instrumentmetadata:US500M1first2011,ticks2012;SPYM1metadata2000
  kháchour/ticks2017 nên ngày sớm chỉmetadata chưađượcxácminh. Không chọn
  historicalwindow từ metadata đơn lẻ hoặc báo códata khi chưa fetch thật.

Kết quả chỉcho biết transport/schema có dùngđược không, chưa contractbrokertarget
hoặc edge. Nếu usable mới freeze numerical adaptation và synthetic/causal/risk
fixtures trước outcomes; reuse existingexecution/cost core nếu thíchhợp,không
đổi ForexPilotSnapshotEURUSDguard để chạy index. C1/C2campaign vẫn ACTIVE.
