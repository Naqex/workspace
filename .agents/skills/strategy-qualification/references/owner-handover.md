# Bàn giao chiến lược cho người vận hành

Dùng khi chuyển strategy sang prospective demo/challenge hoặc owner không hiểu
rule do vibe-coding. Không áp cả quy trình cho hỏi status, phép tính đơn lẻ
hoặc component chưa thành policy. Reuse dossier/report/runbook hiện có; không
tạo dashboard, authority hoặc bài thi trade tay riêng.

## Kết quả cần bàn giao

Một strategy card ngắn, bound exact candidate/code/config/cost/rule version,
dẫn tới evidence và runbook. Viết bằng lời owner có thể giải thích lại:

| Owner cần biết | Cách làm rõ |
|---|---|
| Bot làm gì và vì sao kỳ vọng có lợi thế? | Instrument, giờ/timezone, trigger, entry, exit, stop, sizing; cơ chế là giả thuyết nào và evidence chưa chứng minh gì |
| Một lần sai mất bao nhiêu tiền? | Ví dụ USD và R trên đúng balance; risk dự kiến khác gap/slippage loss, nominal funded balance không là vốn owner sở hữu |
| Lệnh thua bình thường hay lỗi? | Ba traces: lời đúng luật, lỗ đúng luật, sai dữ liệu/duplicate order/wrong account. Trỏ decision→quote→order/fill→equity; thua đúng luật không tự động đổi rule |
| Khi nào quan sát, dừng hoặc thu hồi? | Phân biệt kill vì identity/data/execution/risk với review edge/regime theo tiêu chí đã đăng ký; không đặt ngưỡng dừng hồi tố để cứu PnL |
| Nếu AI/PC mất kết nối? | Ai giữ position/SL, nguồn trạng thái broker, stop-entry khác close-position, unknown submission chỉ đối soát trước retry; dùng execution owner/runbook hiện có |
| Quỹ và phí ảnh hưởng gì? | Exact program/phase/rule version, reset/equity/news/holding constraints, account-wide budget và tổng phí có thể mất; kiểm terms hiện hành trước sử dụng |

Không đòi owner phải dự báo giá, tự viết code hoặc trade tay có lãi. Không hứa
vận hành không cần giám sát. Không sửa risk/stop/signal chỉ vì owner khó chịu
với chuỗi thua; thay đổi policy phải có version/trial và kiểm phù hợp.

## Kiểm hiểu và giới hạn

Trình bày một trace thật đã sealed hoặc ví dụ giả định **ghi rõ giả định**,
rồi mời owner diễn giải bot làm gì, mất tối đa dự kiến bao nhiêu, và sẽ hành
động ra sao. Diễn tập demo/read-only lỗi mất giá hoặc restart, đối soát state;
quyền giao dịch riêng vẫn áp dụng. Dùng một vài tình huống có ích, không biến
thành khóa học/chart exercise khi owner chỉ muốn vận hành bot.

Ghi đúng trạng thái: `prepared_not_demonstrated`, `observed_in_demo` hoặc
`gap_found`, kèm câu hỏi/nhầm lẫn, thao tác thực sự đã thấy, evidence và bước
sửa. Agent viết tài liệu hoặc tự walkthrough không chứng minh owner đã hiểu;
owner nói “hiểu” không chứng minh thao tác khôi phục thành công. Không suy ra
edge/prop-fit hoặc auto permission từ comprehension.

Ví dụ minh họa, không lấy làm threshold: balance10.000USD, planned risk0,25%
=25USD=1R; ba lệnh SL modeled là−75USD trước các sai khác phí/gap thực tế.
Nếu cả ba đúng rules, đó là outcomes cần so với phân phối đã đăng ký, chưa là
bug. Một lệnh gửi nhầm account hoặc không có protective SL theo policy là
sự cố dù đang lời. SL không bảo đảm giá khớp hoặc lỗ tối đa tuyệt đối.

## Căn cứ và refresh

Đối chiếu08/11/2026: [QuantConnect live risks](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/risks)
phân biệt strategy/operational/error risk; [FTMO algorithmic trading](https://ftmo.com/en/blog/what-is-algorithmic-trading-and-how-to-use-it-for-the-ftmo-challenge/)
nêu trader vẫn chịu trách nhiệm objectives/risk dù code thực thi. Đây là cơ
sở thiết kế handover của project, không yêu cầu chứng chỉ của hai hãng và
không chứng minh owner hiện tại đã sẵn sàng. Terms hãng phải refresh theo
program trước quyết định; reference này không pin numeric rules vĩnh viễn.
