# Kiểm sai số chi phí của Gold sweep London DAY

Phép kiểm chỉ dùng `XAUUSD.SWEEP.PREVDAY.LONDON.DAY` với 107 tín hiệu
Development 2022–2023 của V8. Giữ nguyên luật, giờ, mức giá SL cấu trúc,
exit, risk và phí stress. Giá fill hai chiều, nếu thay được bằng nguồn
quan sát, có thể đổi khoảng cách từ fill tới cùng mức SL. Không xét
24H/48H. Khóa phép kiểm trước khi đọc PnL từng lệnh.

1. Dựng lại retention trên toàn bộ raw cohort. Cổng V8 gồm 100%
   endpoint theo mô hình, ít nhất 20 lệnh/năm, ≥50% tín hiệu giữ lại,
   median friction / median natural SL ≤15% và net dương cả hai năm,
   hai swap models, các ngân sách cũ. Tách khỏi chuẩn hiện hành với
   cap từng intent 12%, giữ ≥50%, median scale trong dải đã khóa
   12%–15% và raw markout sau stress ở horizon chính. Chỉ cần một
   cổng cần thiết hụt là dừng. Không đổi cap thực thi hoặc verdict V8.
2. Giữ stress slippage 0,40 USD/oz vòng lệnh và commission 0,0007%
   notional/side theo V8. So bid/ask tại đúng giờ, giữ Bid V8 và đặt
   spread bằng 0 chỉ ở entry dùng Ask proxy để tính cận chẩn đoán.
   BUY tính lại khoảng cách từ cùng Bid tới cùng mức SL, SELL giữ
   nguyên khoảng cách. Commission ước lượng theo giá entry ứng với
   cùng công thức. Dựng thêm cận mọi entry spread bằng 0 để phân biệt
   giới hạn phí và giới hạn sửa proxy. Quote native giữ nguyên ở cận
   sửa proxy. Báo spread tối đa mỗi intent còn lọt cap nếu hữu ích.
   Các giá giả lập này không dùng làm fill, không chứng minh qua cổng.
3. Nếu cận sửa proxy đủ cho cả hai năm, kiểm nguồn paired Bid/Ask
   bổ sung tại đúng timestamps/giờ proxy và dữ liệu đủ để xác nhận
   phí thay được. Không tìm giờ, lệnh hay phí dựa theo PnL. Chỉ đọc
   2022–2023, dùng nguồn local; thiếu giá hay spec thì ghi blocker.
   Chỉ mở bước 2018–2021 có exposure nếu đúng cơ chế vượt cổng bằng
   chứng cứ, rồi mới kiểm đóng góp sau phí, overlap và risk với BASE.
   Việc replay 50k còn cần triển vọng cải thiện đáng kể ở cả hai
   kịch bản đã khóa. Giữ 2024–2026 đóng và mọi thao tác offline.

[Nguồn V8](PROP-GOLD-V8-PROTOCOL-20261115.md) ·
[Cổng hiện hành](../../.agents/skills/strategy-qualification/references/validation-gates.md)

## Kết quả 2022–2023

**Dừng đầu mối. Sửa riêng Ask proxy không đủ để mở replay theo cổng hiện
hành.** Năm 2023 cần ít nhất 28/56 tín hiệu đạt cap từng intent 12%.
Ngay cả khi spread của mọi entry proxy bằng 0, năm đó chỉ đạt 25/56
(44,6%). Thiếu ba tín hiệu. Phép kiểm đã khóa ở `27b6595`.

| Phép kiểm | Năm | Raw | Qua cap V8 15% | Qua cap hiện hành 12% | Median phí / median SL |
|---|---:|---:|---:|---:|---:|
| Quote V8 đã lưu | 2022 | 51 | 23 (45,1%) | 15 (29,4%) | 15,82% |
| Quote V8 đã lưu | 2023 | 56 | 21 (37,5%) | 14 (25,0%) | 16,92% |
| Cận spread 0 ở entry proxy | 2022 | 51 | 33 (64,7%) | 30 (58,8%) | 13,36% |
| Cận spread 0 ở entry proxy | 2023 | 56 | 31 (55,4%) | 25 (44,6%) | 9,96% |
| Cận spread 0 ở **mọi** entry | 2022 | 51 | 47 (92,2%) | 41 (80,4%) | 8,81% |
| Cận spread 0 ở **mọi** entry | 2023 | 56 | 45 (80,4%) | 37 (66,1%) | 9,94% |

Với Bid và mức SL cố định, cap mỗi lệnh đặt một trần trực tiếp lên
spread. Công thức cho BUY tính cả thay đổi giá khớp và mẫu số SL.
Với SELL, giá vào dùng Bid nên mẫu số đứng yên. Ở cả hai chiều, spread
không âm. Do đó đặt spread proxy bằng 0 cho **số lệnh tối đa** mà việc sửa
Ask proxy có thể giữ lại trong phép so này. Cận dùng đúng 25/51 và 30/56
entry proxy. Mỗi năm có 26 entry native và giữ nguyên giá hai chiều của
chúng. Source tại exit là proxy ở 23/51 và 26/56. Thay Ask ở exit hoặc
trên đường đi có thể đổi PnL/điểm chạm SL, còn cap entry đã được quyết định
khi vào.

**15% và 12% dẫn đến hai câu trả lời khác nhau.** Xét riêng các cổng
retention và scale cũ 15%, cận proxy có thể qua cả hai năm. Số liệu này
cho thấy độ nhạy của V8, chưa chứng minh V8 đã bị loại oan. Xét chuẩn
hiện hành, năm 2023 trượt retention ngay ở cận proxy. Cận mọi entry
spread 0 chỉ cho biết commission và slippage đứng riêng chưa đủ làm
hụt retention. Để dùng kết quả đó phải xóa cả spread đã quan sát ở
native, nên đây chỉ là phép kiểm toán học.

### Phí nào đã biết

- **Commission:** 0,0007% notional mỗi chiều là tham chiếu của dự án.
  V8 ước lượng vòng lệnh bằng hai lần notional entry. Trung vị khoản
  dự phòng này là 0,0252/0,0273 USD/oz. Giữ nguyên công thức và tỷ lệ.
- **Slippage:** 0,20 USD/oz mỗi chiều, tổng 0,40, là mức stress đã khóa.
  Đây là giả định kiểm định. Quote hai chiều tự nó không đo slippage
  thực tế hoặc xác nhận biểu phí lịch sử FTMO.
- **Spread:** dùng chênh Bid/Ask quan sát ở 52 entry native, và 0,338
  USD/oz ở 55 entry có Ask proxy. Median raw tổng dự phòng là
  0,7633/0,7649 USD/oz. SL trung vị tương ứng 4,8250/4,5215 USD/oz.
- **Financing:** không có rollover trên các vị thế DAY này, nên hai
  biểu swap không sửa được nút thắt. Kiểm chứng cả 107 entry/exit cùng
  ngày UTC. V8 dùng quote đủ điều kiện đầu tiên từ deadline khi đóng
  theo giờ. Có 20 exit sau deadline, tối đa 691 ms trên sổ mô hình.

[Nguồn thông số và phần cần chứng nhận trên tài khoản đích](FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md) ·
[Kết quả V8](PROP-GOLD-V8-RESULTS-20261115.md)

### Tác động và kiểm chứng

Số **1.894,58 USD/năm** là PnL tham chiếu V8 ở 150 USD/lệnh của
44 lệnh đã lọc qua hai năm, chưa trừ cạnh tranh risk với BASE và chưa
là payout. Không đủ cơ sở ghi nhận phần tiền rút tăng thêm. Giữ kết
quả V8, đóng việc đối chiếu tick bổ sung, không kiểm tiếp 2018–2021
hay replay tài khoản. Chưa xác minh spread/slippage thực thi FTMO
lịch sử. Phép cận không xác nhận hay bác bỏ lợi thế định hướng.

`verify-bound.py` ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/prop-gold-v8-day-cost-check-20261118/`
đối chiếu 107 định danh với Atlas, đọc lại từng entry đúng ordinal
trong manifest Dev, kiểm SHA256 các file quote đã dùng, tái lập
natural SL, phí và 44 lượt nhận của V8. So cap bằng Decimal. Không dùng
PnL từng lệnh để quyết định, không truy cập giá 2024–2026.
Artifact `v8-day-cost-bound.json.zst` round-trip PASS, SHA256
`3cd404e2a7234cde86dafe414cebe0894f9b389365cc4ae7f7503d66b9ab2fca`.
