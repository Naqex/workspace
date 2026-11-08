# Sau R061: kiểm cơ chế trước khi thêm bot

Goal C1/C2 active, [R061](NASDAQ100-H4-SMA-RESULTS-20261108.md) không đạt
filter của pilot. Lát này không sửa rules cũ hoặc chạy thêm PnL; chốt hướng
nghiên cứu và kiểm điều kiện thống kê bằng dữ liệu đã có.

## Nguồn và quyết định trước outcome

Nguồn primary đọc08/11/2026, không import code/data của paper:

| Hướng | Điều đã kiểm | Quyết định |
|---|---|---|
| Equity overnight drift | [NYFed2021](https://libertystreeteconomics.newyorkfed.org/2021/05/the-overnight-drift-in-us-equity-returns/) mô tả giờ02–03Eastern; [cập nhật2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) báo giảm rõ sau publication | Chưa ưu tiên recipe unconditional trên CFD; thiếu actual signed closing order imbalance, không thay bằng quotevolume |
| ORB Nasdaq | [Đại học NTU/IEEE2019](https://scholars.lib.ntu.edu.tw/entities/publication/d69ecf33-892c-4f8a-9a88-2af1bcc4efcd) abstract có nghiên cứu5futures; [arXiv2026](https://arxiv.org/abs/2605.04004) abstract nêu phản chứng sau costs | Các studies khác data/recipe/cost; chưa full-method audit, không lấy abstract xanh/đỏ làm verdict chung. Không thêm ORBgrid trong lát này |
| R035 spread hai FX | [NBER Gatev etal.](https://www.nber.org/papers/w7032) là stock-pair distance, không chứng minh FX cointegration; [statsmodels coint](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html) nêu giả định I(1), null no-cointegration, lag/default/gaps | Nhận một phép kiểm nền của GBPUSD/AUDUSD; chưa nhận bot, edge hoặc exact paper replication |

SSRN7428398 search trả abstract phản chứng ORB nhưng mở fullpage403; không
bypass hoặc dùng như full audit. NBER PDF403, chỉ summary chính thức đã đọc.
Public research snippets có aggregate outcomes tới2025/2026 của tác giả khác;
ghi external literature exposure, **không mở giá/own strategy holdout2025+**,
không được gọi mọi public-information search là blind với literature mới.

GBPUSD/AUDUSD được chọn **trước khi đo** vì source Bid/Ask H1 đã có và cùng
USD quote; khác FX monthly-momentum R033 và unconditional local-flow R059/60.
Chung USD không chứng minh equilibrium: UK/Australia có nền kinh tế và chính
sách khác nhau, spread có thể trôi hoặc đứt gãy. Đó chính là giả thuyết bác bỏ.
Không chọn pair dựa trên correlation/returns đẹp, không thử mọi cặp rồi báo
pair tốt nhất. USD-neutral hai legs vẫn còn relative-currency risk.

## Frozen statistical admission, chưa trading experiment

Một pair có thứ tự: y=ln(GBPUSD BidClose),x=ln(AUDUSD BidClose). Hai formation
windows **calendar2018 và2021**, dùng cho khả năng nghiên cứu subsequent2019/
2022 đã exposed; không cleanOOS. Source-only H1 ở
`execution-v1/fx-h1-history-v3` dưới campaignroot. Only read4books/year ×2years,
không tải nguồn, không đọc outcome2019/2022/2025+, không source imputation.

- Sampling16UTC H1Close, known-at17UTC, mỗi weekday trừ01Jan/25Dec theo
  calendar đã chọn; exclusion là thiết kế mẫu, **không chứng nhận marketclosed**.
  Retain census mọi expecteddate, side availability/crossed/quality; thiếu một
  ngày trong calendar hoặc không đủ240paired observations thì inconclusive
  data, không drop bất kỳ ngày khó nào để fit và không backfill/asof.
- Date boundaries/year/UTC/grid0.00001/sideOHLC/seals/source identity phải đúng.
  Bid và Ask đều cần để quality, chỉ BidClose đi vào diagnostic. Không biến
  H1Close thành actual jointquote hoặc price có thể fill vào giờ16UTC.
- Fixed Engle–Granger `coint(y,x,trend='c',maxlag=1,autolag=None,
  return_results=False)`; fixed OLS y=a+bx. Không reverse regression, đổi lag,
  transform, window, chọn cặp hoặc nới p để cứu kết quả.
- ADF levels và first differences từng leg, constant/maxlag1/autolagNone;
  rejection/nonrejection không chứng minh I(1). Report finite t/p/coefficients,
  residual scale/AR1 diagnostic; không chuyển estimated half-life thành
  holding/stop rule trước khi có protocol kinh tế riêng.
- Chỉ retain để **thiết kế một economic pilot** nếu cả2windows: cointp<=0.05,
  eachlevelADF p>=0.05/differenceADF p<0.05, positive finite beta0.1–10 và
  residualSD>0. Đây là prefilter riêng, không multiplicity-adjusted proof,
  không economic edge, không yêu cầu mọi strategy phải cointegrated.
  Nếu fail/inconclusive, giữ kết quả, không mở cointegration grid hoặc PnL.

## Capability, review và artifacts

Đã kiểm productvenv không NumPy/SciPy/statsmodels; bundledPython cóNumPy nhưng
khôngSciPy/statsmodels; existing `.runtime/research-ml` cóNumPy/SciPy nhưng
thiếuPandas/statsmodels. Không tự viết p-value table rồi gọi là Engle–Granger.
Nếu cần thêm package, scope `.runtime/research-statistics` isolatedvenv, official
PyPI wheels only, version/hash/dependency/license lock, không product/global
mutation hoặc service/account. [Official install](https://www.statsmodels.org/stable/install.html)
và [PyPI](https://pypi.org/project/statsmodels/) liên kết đúngupstream, BSD3,
released0.15.0 metadata27/08/2026; compatibility phải kiểm bằng thực tế pip.
Không chạy sdist/installscript/download-and-execute hoặc nightly chỉ để đủtool.

Trước numeric real-data diagnostic, synthetic known cointegration/randomwalk,
degenerate/gaps/clock/finite guards phải đạt. Reviewer riêng kiểmsourcebinding,
date census, log/OLS và residualADF t-stat bằng arithmetic khác; p-value curves
cùng library không là independent statistical implementation. Mutations data/
date/source hash/reportedstat/falseauthority reject. Không hứa certified test.

Output mới `execution-v1/fx-pair-formation-v1`,1writer/PID/events/progress/
deadline120s/CANCEL; manifest pin protocol/source/code/runtime/packages.
Giữ failures; không retry tự động khi observer timeout. Nếu cần sửa material,
attempt mới và chỉ affectedwork. Hậu kiểm timing/nextaction và route index/
catalogueR035/currentcontext; chưa policyimplementation nên không tăng44versions.
