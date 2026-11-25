# Bot Lab · MQL5 Sourcing Pass 2 · 20/11/2026

**Trường hợp B. Tám hồ sơ Real qua vòng số liệu công khai và cả tám đều
yêu cầu đăng nhập ở tab Trading history.** Chưa có CSV thực để chạy
auditor. Bảng ứng viên và điểm cần kiểm trên từng log nằm trong
[shortlist](MQL5-LIVE-CANDIDATE-SHORTLIST-20261120.md).

## Phạm vi rà nguồn

| Bước | Số lượng | Cách kiểm |
| --- | ---: | --- |
| Bảng công khai MT4 và MT5 | 18 phản hồi, 864 dòng | Mỗi nền tảng có 8 trang sắp xếp DD tăng dần và 1 bảng mặc định. Form thử trả bảng chưa lọc. |
| Hồ sơ duy nhất | 856 | Gộp theo Signal ID. |
| Qua vòng lọc danh sách | 170 | Badge Real, tối thiểu 52 tuần và 150 lệnh, DD list tối đa 20%. |
| Đọc hồ sơ chi tiết | 72 | 49 MT4 và 23 MT5. Ưu tiên tài khoản lâu năm, DD thấp và đủ đại diện hai nền tảng. Còn 98 lead chưa đọc chi tiết. |
| Qua vòng sàng lọc công khai | 8 | 7 MT4 và 1 MT5. 6/8 có ít nhất 104 tuần tuổi tài khoản công bố. Cả tám có ít nhất 364 ngày theo dõi theo thống kê MQL5. |
| Log đầy đủ truy cập được khi là khách | 0/72 | Có tab history và lời mời đăng nhập, thiếu bảng giao dịch và nút CSV. |

Đọc bảng và hồ sơ bằng giao diện HTTP công khai, giãn hai giây giữa các
request liên tiếp trong lượt quét. Chỉ số chi tiết lấy tại snapshot của từng
hồ sơ. Tỷ lệ phần trăm hoặc PF trên bảng có thể khác ở hồ sơ, ví dụ Innolife
4 có PF 2,09 trên bảng và 1,18 trong Statistics. Shortlist dùng giá trị chi
tiết và giữ dữ liệu list riêng. [Bảng MT4](https://www.mql5.com/en/signals/mt4/list) ·
[Bảng MT5](https://www.mql5.com/en/signals/mt5/list) ·
[Giải thích về thời gian theo dõi](https://www.mql5.com/en/articles/2704).

Trong 72 hồ sơ đã đọc, 64 bị loại. Các lý do có thể trùng nhau. Có 43 hồ
sơ thiếu 52 tuần theo dõi, 7 vượt trần DD dù cột list đã qua, 9 có lỗ
trung bình từ ba lần lãi trung bình, và 20 có cảnh báo 80% tăng trưởng dồn
trong tối đa hai tuần. Ngưỡng tỷ lệ lỗ/lãi 3× nhất quán với auditor hiện có
và chỉ dùng để sàng lọc trước khi có log. Ngưỡng theo dõi dùng 364 ngày
cùng ngưỡng tuổi tài khoản 52 tuần. Giao dịch gần đây yêu cầu trong 30 ngày.

| Ví dụ bị loại | Bằng chứng |
| --- | --- |
| [NHF NZDCAD](https://www.mql5.com/en/signals/2394283) | 134 tuần hiển thị và 434 lệnh, mới có 34 ngày theo dõi. |
| [AUDCAD 1 mt4](https://www.mql5.com/en/signals/2271699) | DD list 20% nhưng DD equity trong hồ sơ là 20,03%. |
| [RSE 200](https://www.mql5.com/en/signals/1997766) | DD list 19% và equity 19,06%. Tỷ lệ đi kèm mức sụt balance lớn nhất theo tiền là 50,87%. |
| [ANC WAVE PRO](https://www.mql5.com/en/signals/2193243) | Max DD chi tiết 6,33%, phần mô tả ghi dùng DCA trên AUDCAD/NZDCAD. |
| [SNOW EAGLE](https://www.mql5.com/en/signals/2252948) | Max DD 12,31%, phần mô tả ghi dùng grid hồi quy và tăng lot. |
| [Steady State Accumulation](https://www.mql5.com/en/signals/2197435) | DD equity 13,61% và DD balance tương đối 2,15%. Tác giả nêu DD kỳ vọng khoảng 30%. |

## Lịch sử giao dịch và quyền lấy file

Trên từng hồ sơ, đã kiểm nội dung riêng của vùng Trading history, nơi
MQL5 hiển thị yêu cầu đăng nhập hoặc đăng ký. Vùng đó không trả bảng cho
khách. **Không có cột giao dịch nào** trong bộ 12 cột cần kiểm
`Time / Type / Volume / Symbol / Price / S/L / T/P / Time / Price /
Commission / Swap / Profit`. Statistics vẫn hiển thị số tổng hợp như số
lệnh, tỷ lệ thắng, các khoản gross và DD. Quyền của tài khoản sau khi đăng
nhập và độ đầy đủ của export còn phải xác minh trên file được cấp quyền.
[Ví dụ hồ sơ](https://www.mql5.com/en/signals/2308133) ·
[Hướng dẫn export](https://www.mql5.com/en/articles/3166).

Khi có quyền, làm theo [hướng dẫn tải tay](MQL5-LIVE-CANDIDATE-SHORTLIST-20261120.md#lấy-log-có-quyền-truy-cập)
và lưu thông tin nguồn cùng file. Runner batch đang có sẽ tạo leaderboard
và chỉ xuất blueprint cho hồ sơ đủ cổng. Dùng output mới mỗi lần chạy.
Mục tiêu đánh giá vẫn là Swing 10k/25k 1:30, trọng số 80%, và Standard
10k/50k 1:100, trọng số 20%, với phí đã khóa ở `36f1535` và spec Swing
`8fd77ef`. Chưa có số liệu Swing/Standard, net sau phí FTMO hoặc blueprint
từ log live ở Pass 2.

## Adapter và kiểm chứng

Adapter dùng đúng chữ ký 12 cột MQL5 Signals để xác định `Volume` là lot
và ghép cặp hai cột giờ/giá mở–đóng. Khi đủ ba thành phần, net được tính
bằng `Profit + Commission + Swap` với dấu như file báo cáo. Giờ địa
phương cần timezone của nguồn, tài khoản cần currency đã xác minh, và
`S/L` hiển thị cần bằng chứng riêng để dùng làm SL lúc vào. Nếu thiếu
thành phần, auditor giữ trường liên quan ở trạng thái unknown.

**65 kiểm thử PASS, 0 skip** trên năm module liên quan. Hai test mới dùng
mẫu CSV giả lập 12 cột, kiểm dấu phẩy, chấm phẩy kèm dấu phẩy thập phân,
ô bị mask, dấu phí và trạng thái unknown cho SL ban đầu hoặc timestamp
thiếu timezone. Đã xác nhận mẫu đường dẫn CSV trong inbox bị Git bỏ qua.

```powershell
$env:PYTHONPATH = 'tooling/ai-engines;tooling/ai-engines/tests'
& tooling/strategy-engines/observer/.venv/Scripts/python.exe -X utf8 -m unittest test_bot_live_leaderboard test_bot_live_auditor test_bot_lab test_mt_report_parser test_research_inventory_documents
```

Khóa giá local từ 01/01/2025 trùng blob ở `9a44b6c`. MT5 không mở,
`OrderSend = 0`, không đọc credential, không chạy backtest chiến lược mới.
Hai gitlink Trader và VI Dubber giữ nguyên, thư mục VI Dubber còn đúng WIP
ban đầu. Lưu thay đổi trong commit local trên `codex/prop-research-roadmap`.

[JSON đối soát](BOT-LAB-MQL5-SOURCING-PASS2-20261120.json) ·
[SHA256](BOT-LAB-MQL5-SOURCING-PASS2-20261120.sha256).
SHA256 của báo cáo và shortlist dựa trên byte chuẩn LF trong Git.
Bằng chứng HTML công khai lưu ngoài Git, có hash trong manifest.
Tra bằng `research_inventory.py --key mql5-sourcing-pass2-20261120`.
