# V9 — storage, quant core và nghiên cứu đa chế độ

Task `a07359d1-cc62-4fcb-a849-8012b47c5b28`. PR87 merged `5f1b687`;
branch `codex/system-and-alpha-v9`. Không broker/paid/Astra, không sửa V1–V8
đã freeze, Trader pin hoặc VI Dubber WIP. Một PR mới, không tự merge.

## Những gì chưa được chứng minh

N1 đổi compression **và** cost/stop gates. Attribution V8 2023: context bỏ
+8,189R và cost gate bỏ +18,378R. Không chứng minh 80% phiên là phá giả.
Backward −52,16R là net ASYM; gross 2020 dương. Sweep V8 còn median friction
/ SL >15%, cadence và Ask proxy; ba horizon cùng tín hiệu, không ba alpha.

2018–2026 đều exposed. Dev mới: 2019–20 và 2022–23; reused historical
validation: 2018/2021 rồi 2024–13/10/2026. Không gọi split mới clean OOS.
Warmup chỉ dùng giá trước quyết định, không tính vào PnL.

## Engineering contract

Inventory D/E cấp1/2, không đi theo junction. Purge D chỉ cache sinh tự động
đã xác minh ownership/containment, loại VI Dubber và .git. Không tự xóa venv,
node_modules, raw, seal hoặc private E inputs. Cold archive phải SHA256
roundtrip, bảo toàn directory path đang được seals/consumers dùng. E chỉ đề
xuất script, không purge. Đo logical bytes/file/folder, không gọi là allocated NTFS.

995 test IDs trước thay đổi qua bốn runtime đã có; lưu thời gian từng test/module,
không bỏ test để báo speedup. Tách Fast CI/Historical, parity hợp nhất ID.
Core mới reuse execution/lifecycle đã kiểm qua adapter, không rewrite công thức
hay đổi sealed source. Benchmark cùng inputs/cache scope, giữ raw samples.

## Budget nghiên cứu cố định trước outcome

Không grid hoặc B1. **S1** dùng đúng prevday London H1 sweep V8 (08–11 UTC,
mỗi ngày tối đa một tín hiệu BOTH). SL theo extreme của **4 nến H1 hoàn chỉnh
liền trước/bao gồm nến tín hiệu** +0,1 ATR_H1 trước nến. Không kéo theo sàn phí.
Hai horizons DAY và24H; 48H chỉ control V8, không một trial S1 thứ ba.

**S2** một regime split causal duy nhất: Asian width / median20 ngày hoàn
chỉnh trước đó >1,5 là expansion. Chưa đủ context thì abstain.
Expansion: giữ Asian breakout/H4 bias A gốc, whole-box stop+0,1 ATR.
Normal: H1 quét Asian high/low rồi đóng trở lại hộp, nến xác nhận cùng hướng,
08–15 UTC; stop extreme4H+0,1ATR, mỗi ngày tối đa một tín hiệu.
Đây là giả thuyết, ratio chỉ proxy expansion, không macro event detector.
Horizon DAY duy nhất. XAUUSD primary; EURUSD/US500 readiness trước, chỉ triển
khai nếu local M1/tick đủ cả Dev clusters với source/cost/calendar rõ.

Stage0 cho mỗi branch: all raw signals, net markout stress tại DAY/24H
(S2 chỉ DAY primary,24H diagnostic), không lọc phí để nâng markout;
positive ở từng năm Dev, gross vượt friction, medianF/medianSL≤15%;
retention≥50%, admitted≥40/năm (20/năm cho satellite S1).
Giữ failed/canceled, không cứu bằng chọn side hoặc đổi horizon sau outcome.

Sau Stage0 đủ mới SL-active, risk150 USD, two swaps SYM−40/−40 và
ASYM−45/−5 USD/lot/rollover, commission0,0007%/side, slip0,20USD/oz/side,
lot1oz bước1oz (contract100oz). DAY min20:30/holiday/Friday, không blanket
zero swap: đếm rollover thực. M1 Ask proxy0,338 chỉ conditional, hai orders.

Selection: max(min cluster annualized SYM NetR), tie S1DAY→S124H→S2DAY;
không trộn DAY/24H cùng entry. Portfolio chỉ những alpha đủ gate; shared
budget/cap/guards và V6 lifecycle, không cộng sổ độc lập thành portfolio.
Đóng composition bằng commit trước validation. Nếu không ai đủ Dev, không
đốt validation cho trial fail: bảng9năm N/A + control V8 đã có, lifecycle
candidate N/A, không dựng danh mục giả.

## Verification và bàn giao

Unit fixtures, causal prefix parity, source checksum/tamper, stop/cost oracle,
exact accounting độc lập implementation do cùng implementer; không gọi là
independent person/model review. Giữ M1/tick gaps unknown.
Lưu MD/JSON, private ledgers/profile/storage manifests, context/index, coherent
commits, PR3CI đúngHEAD. Mục tiêu là bằng chứng; không bảo đảm tìm được edge.
