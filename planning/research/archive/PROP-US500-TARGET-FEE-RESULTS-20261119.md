# US500 có đổi quyết định khi bỏ commission?

**Gác các ứng viên đã rà.** Bỏ commission mở thêm cơ hội và làm một số
phép đo đổi dấu, nhưng chưa có ứng viên nào đạt mức 1.000 USD/năm ở cả hai
cụm Development. VIX Curve là ca đáng chú ý nhất. Phần dương ở cụm yếu chỉ
đạt 128,09 USD/năm và cụm còn lại chỉ có 3,7 cơ hội định giá mỗi năm.
Không tái dựng đường SL, không chạy mô phỏng Challenge/Payout. Danh mục
nghiên cứu vẫn là BASE_GUARD với trạng thái NOT_QUALIFIED.

## Cách đo

Chỉ dùng 2018–2020 và 2021–2023 tại checkpoint `8ffd256`. Phí stress cũ
ngoài spread là 2,50 điểm/vòng, gồm 1,00 commission và 1,50 trượt giá.
Kịch bản đích bỏ 1,00 điểm commission theo công bố của FTMO, giữ Bid/Ask,
trượt giá và quy ước funding đã đăng ký. Đây là phí tham chiếu công khai.
Đặc tả tài khoản đích và phí lịch sử từng năm chưa được đo trong lượt này.
[Công bố FTMO](https://ftmo.com/en/blog/zero-commissions-on-indices/).

Cổng 12% dùng spread biết tại entry cộng phí stress, chia cho SL tự nhiên.
Đối chiếu độc lập cổng 15% của kho V12/V16 và chuyển tiếp gốc 15% → mới 12%.
Phần chênh tiền được đối soát theo công thức
`cũ + hoàn phí + hiệu ứng đổi lot + tiền lệnh mới − tiền lệnh rớt = mới`.
Lệnh chưa có giá giữ trạng thái thiếu. Trần chuyển bước được khóa trước
outcome: ≥1.000 USD/năm và ≥40 cơ hội có giá/năm ở mỗi cụm, giữ ≥50% cơ hội,
độ phủ đã đo ≥99% và cải thiện tiền ở cả hai cụm. Nếu đạt mới xét dựng tối
đa một đường SL rồi kiểm đóng góp và rủi ro trước khi mô phỏng tài khoản.

## Các nghiên cứu có sổ riêng

Các cặp số theo thứ tự 2018–2020 và 2021–2023. Cột cuối tính trên phần đã
định giá. Ba dòng đầu là chênh giá đến giờ thoát sau phí. VIX Curve giữ sizing
gốc 150 USD gồm dự phòng phí và bước 0,1 lot. Hai nhóm còn lại quy đổi theo
150 USD/SL để so quy mô.

| Luật | Qua cổng 12% cũ → mới, 2018–2020 | Qua cổng 12% cũ → mới, 2021–2023 | Sau phí cũ → mới, USD/năm |
|---|---:|---:|---|
| VIX Divergence | 9 → 17/144 | 22 → 48/169 | +2,47 → −104,98 / −67,91 → −294,18 |
| VIX Curve | 31 → 47/118 | 10 → 11/17 | −585,99 → +128,09 / +387,94 → +393,25 |
| LETF-AUM | 3 → 22/384 | 15 → 74/369 | −38,44 → −316,02 / −44,34 → +5,18 |
| Calendar 60/40 | 99 → 131/140 | 144 → 144/144 | −256,78 → −164,22 / −78,06 → +37,94 trên đúng 216 lệnh có SL đã lưu |

- **VIX Curve.** Trong từng cụm ba năm, hoàn phí **+112,50 / +37,10 USD**.
  Đổi lot ở **25 / 9** cơ hội cũ đóng góp **−43,62 / +44,28 USD**. **16 / 1**
  cơ hội mới đóng góp **+2.073,37 / −65,43 USD** tại giờ thoát.
  Tần suất sau phí đạt 15,7 / 3,7 cơ hội/năm. Tỷ lệ giữ ở cụm đầu
  chỉ 39,8%. Chưa đo first-passage SL trên các cơ hội này.
- **VIX Divergence.** 8 / 26 cơ hội mới làm hao thêm **360,67 / 769,74 USD**
  qua ba năm mỗi cụm. Hoàn phí trên nhóm cũ chưa bù được phần này.
- **LETF-AUM.** Gốc dùng spread bình quân ở hai đầu và giữ 17 cơ hội.
  Tái lập với spread tại entry, giữ nguyên phí, đưa 4 cơ hội vào và loại 3,
  còn 18. Sau bước chuẩn hóa này, riêng việc bỏ commission thêm 19 / 59
  cơ hội. Cụm đầu xấu hơn và cụm sau chỉ sát hòa vốn.
- **Calendar.** 32 cơ hội mới đều ở cụm đầu. Chỉ 5 có đủ phút để xem xét
  tái dựng đường SL. Cả 32 cộng +11,715 điểm tại giờ thoát, tính trên mỗi
  đơn vị và chưa mô phỏng SL hoặc sizing mới. Vì vậy phần chênh trên 216
  lệnh cũ trong bảng là phép hoàn phí cùng lot. [Sổ Calendar](PROP-US500-CALENDAR-REBALANCE-RESULTS-20261119.md).

## Rà kho cấu hình V12 và V16

| Kho | Phạm vi | Dương ở hai cụm với phí mới | Kết quả của cấu hình có cụm yếu tốt nhất, USD/năm | Đạt 1.000 USD/năm cả hai cụm |
|---|---|---:|---:|---:|
| V12 | 392 ô tín hiệu, 675 đường thoát khác nhau từ 808 dòng | 4/675 | +82,66 / +24,91 | 0 |
| V16 | 98 endpoint khác nhau từ 202 dòng (92 cặp P0/P1, 6 bộ P0/P1/P2) | 4/98 | +16,44 / +37,03 | 0 |

- Ở cổng 12% → 12%, V12 thêm **6.800 / 8.348** lượt qua cổng. V16 thêm
  **1.244 / 1.531**. Đây là các lượt tín hiệu theo ô cấu hình, có trùng
  cơ hội thị trường giữa những cấu hình. Cả hai so sánh ở 15% → 15% và
  15% lịch sử → 12% đích vẫn cho 0 ứng viên đạt mốc tiền.
- V12 dùng giá thoát đã lưu và khối lượng tham chiếu 150 USD/SL làm tròn
  xuống bước 0,01. Bản đứng đầu theo cụm yếu chỉ có giá thoát ở 11/26 và
  16/45 lượt qua cổng. Các chế độ thoát dùng mức bảo vệ theo net R như
  P1/P2 cần tính lại đường thoát nếu áp dụng phí mới vào logic đó.
- V16 giữ mốc đóng ngày gốc và đo giá ở endpoint. Bản đứng đầu có 25/25
  và 45/45 endpoint, cả hai cụm đổi dấu, nhưng chưa có chứng nhận đường SL.
  Kết quả cũ khớp số tín hiệu, số qua cổng 15% và tổng endpoint R ở cả 98 ô.
  Cache mốc đóng trong phép đối soát dùng timestamp entry. Một ngày UTC
  có thể chứa hai ngày New York, nên dùng chung một mốc cho ngày UTC làm
  lệch phép đếm đầu tiên.
- V12 có 84 lượt thuộc 2018/2020 qua ratio 15% đã lưu nhưng entry chậm quá
  một phút. So 15% lịch sử dùng đúng mask cũ; cổng mới áp điều kiện entry
  đã đăng ký. 84 lượt này rời tập do kiểm thời gian, không quy cho phí tăng.

R048/R051 đã có rerun commission 0 và sửa nguồn riêng. Atlas chỉ có
2022–2023 ở phạm vi này. V26 mới đối chiếu được sổ tổng hợp, chưa có ý định
từng lệnh để xác định thay đổi số vào và lot. Các kết quả trên không bao
trùm những nghiên cứu đó.
[R048/R051 phí 0](FTMO-INDEX-COMMISSION-RESULTS-20261108.md) ·
[Sửa nguồn](INDEX-EXPLICIT-SOURCE-RESULTS-20261108.md).

## Tái hiện và vận hành

Kho evidence local
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-us500-target-fee-20261119/`.

| Artifact | SHA256 |
|---|---|
| `registration.md` | `c6d763e0fccafeafcc17a2cf9901bb37d230f16d7c9d7da07e1dbd66e21d4438` |
| `fee_audit.py` | `28a144a8f5521fb377d3e34e3d2fb53fd073bdf730b2c661e8295be8311afeb0` |
| `fee-audit.json.zst` | `67eee7b88dd0e208e31f047909e94d8f9f600131b0679826d5bff1fce360a26d` |

- Chạy từ Workspace, thêm `tooling/ai-engines` vào PYTHONPATH, dùng
  `uv run --offline --no-project --with numpy --with zstandard --with tzdata python -u <fee_audit.py>`.
  Script tạo file ở chế độ không ghi đè. Đã kiểm SHA của 12 đầu vào trong
  receipt, đọc lại Zstandard, kiểm 18.624 đẳng thức tiền và số đếm, đối
  chiếu Calendar với receipt 216 lệnh và V16 với tổng R gốc. Nguồn giá chỉ
  gồm 1.926.201 phút Bid/Ask đã niêm phong trong 2018–2023.
- Study chạy qua [`index_noise_study.py`](../../tooling/ai-engines/index_noise_study.py)
  có thể chọn profile `FTMO_ZERO_COMMISSION` bằng
  `--cost-scenario ftmo-index-zero-commission-public-20261108`. Chọn trước
  bước lọc phí và sizing. Default vẫn dùng phí lịch sử để tái hiện sổ cũ.
  [Kernel vector hóa V12/V16](../../tooling/ai-engines/quant_core/vectorized_sl_active_kernel.py)
  vẫn gắn mức 0,50 commission và 0,75 slippage mỗi chiều của US500 trong
  SYM. Lượt này chỉ đối chiếu sổ, chưa đưa profile phí đích vào kernel.
  Nếu có ứng viên qua cổng sau này, phải truyền cùng profile xuyên lọc,
  sizing, tính ngưỡng bảo vệ và khớp/thoát, rồi mới đánh giá đường vốn.
- Không mở giá 2024–2026, không tối ưu tham số và không kết nối broker.
