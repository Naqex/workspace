# FOMC surprise: nguồn lịch sử đã kiểm, chưa nhận tín hiệu intraday

[Protocol](FOMC-SURPRISE-SOURCE-PROTOCOL-20261109.md) commit`a6c05df` trước
tải CSV; author Git commit`f04846678ad4ec981dc24de615c0af16dd3573e8`,20/04/2024.
Không chạy Matlab, PCA hoặc backtest, không thị trường/provider trả phí mới.

## Kết luận có ích

Nguồn công khai giúp kiểm cơ chế lịch sử nhưng **không được dùng nhãn sự
kiện/“30 phút” làm bằng chứng dữ liệu đã sẵn sàng tại t+20 phút**. [README
tại bản đã pin](https://github.com/marekjarocinski/jkshocks_update_fed_202401/tree/f04846678ad4ec981dc24de615c0af16dd3573e8)
nêu cửa sổ median có thể kéo dài khi ít quan sát; file không có endtime/count
cho từng biến/từng hàng. Publicfile2024 cũng không chứng minh owner nhận
được cùng feed tại quyết định2019/2022. Không tự thay bằng các factor
orthogonalized/fullsample vì có thêm nguy cơ lookahead.

| Kiểm thực tế | Kết quả |
|---|---|
| Source bytes |3files, Gitblob+SHA256/size/seals khớp exactcommit;no retry|
| CSV |359hàng,17cột; chronological và timestamp duy nhất;1988→31/01/2024|
| Lệch metadata |README ghi1988–2023 nhưng có1hàng31/01/2024; giữraw và tách hàng này khỏi numericcensus/selectedscope, không âm thầm sửa source |
| Scope đã đăng ký |358hàng1988–2023; thiếu kháczero. Ví dụMP1:319known/39missing/91zero;FF4:304/54/69 |
| Focus cohort |16scheduledevents2019/2022, lấy từ accepted R062calendar; không chọn theo dấu hoặc độ lớn |
| Timezone |NYclock khớp16/16official14ET;UTCinterpretation0/16. Reconciliation này chưa chứng thực rawvendor timestamps độc lập |
| Ô số focus |240/240known; Decimal/Fraction parsing khớp. Không tính tradingPnL hoặc tìm threshold |
| Causal fixtures |Positive before/at/after known-at boundary, prefix-fit/raw-observation và zero-vs-missing;12negative cases bị validator từ chối |
| Các nhánh bị chặn |Unknown/futureobservation, future/unknownpublication, unverifiedaccess, fullsample/futurefit, missing/nonfinite, trướcobservation, sourceauthority và actualrawbyte mutation |
| Real source admission |`source_structure_reviewed_intraday_not_admitted`; cả16rows có observation-end/access gaps; không signal hoặc execution grant |
| Phạm vi tiếp cận |Không2025+/holdout;2024Jan31sourceexposure đã ghi, không gọi row này unseen về sau |

Repo không có permissive license; chỉ private source review với citation,
không copy/run code hoặc redistribute data. Chưa xác minh quyền realtime/
commercial feed/redistribution của underlying vendors. Không coi author code
hoặc publicdownload là permission mở account/provider/broker.

## Engineering và khả năng kế thừa

| Phase | Wall / CPU thực đo |
|---|---:|
|3source accesses+seals/snapshots|1,850s /0,047s|
|Source/clock/numeric/causal review|0,253s /0,094s|
|Research/authoring|Chưa timer tách đủ; không gọi2,103s là toàn bộ quá trình|

Không còn job; source/review đã terminal. Viewer/validator ở private fixture,
**chưa tích hợp enforcement vào runtime mọi loại feature**. Numeric/parser
checks chỉ đúng scope này, không data-provider fidelity hoặc whole-system edge.
Không có lý do optimize CPU/GPU/Rust, thêm RAG/database/MCP hoặc skill manager.
Existing research/qualification/evidence skills đã có causal-known-at rules.

Private base`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/`:
`execution-v1/fomc-surprise-source-v1/` giữ raw/seals/protocol+producer+reviewer
snapshots,manifest/result/review và selected-source-rows. Reviewer
`review-fomc-surprise-source-v1.py`; source `prepare-fomc-surprise-source-v1.py`.
ReviewSHA `ad3f23c224c36518007edcbfc88b60a0a7d2821acaff191cc424eb5213113734`;
selectedSHA `1d51cfb7e096a57d8926421ab5b6e9015acfc055d450d9d74acbe2dd1febddff`.

## Quyết định và bước tiếp

R027/R028 không còn là “chưa tìm nguồn public”, nhưng **intraday availability,
units/sign/source-access và executable adaptation chưa admitted**. Chưa
accountpolicy/PnL/candidate mới; catalogue85/58giữ nguyên. Không đổi rawscope,
cohort hoặc authority để tựpass; không mua feed hoặc mởholdout.

Lát tiếp dùng đầu vào **giá đã quan sát được trước sự kiện** từ nguồn hiện
có: [R086 protocol](US500-FOMC-PRICE-MOMENTUM-PROTOCOL-20261109.md). Đây là own
price-only adaptation; không dùng future surprise để phân loại một lệnh trước
FOMC, không biến researchdataset2024 thành featurelive2019. C1/C2 vẫn chưa đạt.
