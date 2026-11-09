# Calibration recovery: cache scope, không thay recipe — 08/11/2026

Parent [protocol](SCREEN-CALIBRATION-REPAIR-20261108.md) đã freeze ở592fa82.
Attempt1 failed trước numeric0,625s: reader hiện hành đòi cachekey khác pilot
07/11. Không auto rebuild/rebind, không sửa cache/sourcepins cũ. Failure và
originaldriver giữ trong `screen-calibration-repair-v1/attempt-1`.

Recovery mới `attempt-2` giữ4candidates/2costs/03–07Jan2022/risk/deadlines và
outcomecriteria. Thay **admission transport**, không economics: đọc oldcache
packet đúng sha/seal/binding, rồi dựng độc lập tất cả raw warmupH1 và toàn bộ
evaluationprefixH1 từ current native rawreader (hash/order/grid/date vẫn kiểm).
So từng fieldCoarseHour gồm mid/sideOHLC/firstlasttime/sequence/count/maxspread
trên scope sẽ dùng. Chỉ exactfieldparity mới nhận observations cho probe.

Không đổi bindingpacket cũ thành currentbinding. Receipt giữ oldcachehash,
oldproducers, currentsource/runtime, exactcomparedhours/rawticks và scopes.
Không claim validated mọi giờQ1; chưa đọc numerical outcomes của4policies ở
prefix này trong attempt1. Đây là correction của preflight trước replay.
Không đổi namedcandidate/model/risk/cost/entry/exit để tránh failure.

Đọc raw warmup+prefix chỉ để oracle, không đọc lại whole-quartersimulation;
nativecases dùng cùng verifiedprefix nhưparentprotocol. Source snapshots của
attempt1 giữ trước sửa driver; attempt2 và implementationreceipt pin khác biệt.
