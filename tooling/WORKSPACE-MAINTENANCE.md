# Kiểm tra dung lượng và cleanup

Chạy từ workspace bằng Python3.12 có sẵn. `workspace_maintenance.py` không là
service nền, không tự xóa cache khi import hoặc chạy inventory.

Một lệnh kiểm tra, dọn cache D có xác nhận bằng flag và xuất backup preview:

```powershell
python tooling/workspace_maintenance.py maintain --root D:/ANNAM/TradingWorkspace --apply-caches --destination E:/BACKUP-TRADINGWORKSPACE/workspace --output <private-job>/health.json
```

Bỏ `--apply-caches` để chỉ xem trước. Backup luôn giữ `/L`, không tự copy/xóa E.
Các chế độ riêng khi chỉ cần một phần:

```powershell
python tooling/workspace_maintenance.py inventory --root D:/ANNAM/TradingWorkspace --output <private-job>/inventory.json
python tooling/workspace_maintenance.py purge --root D:/ANNAM/TradingWorkspace --approved-inventory <private-job>/inventory.json --output <private-job>/purge.json
python tooling/workspace_maintenance.py backup-plan --root D:/ANNAM/TradingWorkspace --destination E:/BACKUP-TRADINGWORKSPACE/workspace --output <private-job>/backup-plan.json
```

Inventory chỉ cộng logical bytes/file/folder; không follow junction/symlink.
Những entry không đọc được và links giữ riêng; không gọi con số đó total
physical NTFS hoặc âm thầm thay quyền đọc. Trên Windows hỗ trợ long paths.

`purge` chỉ xóa `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
đã liệt kê; preflight tất cả trước mutation. Chặn root/outside/reparse,
`.git`, VI Dubber. Không quét tên `.tmp` hoặc logs rồi mặc định xóa; không
đụng raw, seal, venv active hoặc worktree của chat khác.

Hai API explicit cho maintenance đã xác minh ownership:
`purge_incremental` chỉ nhận `target/debug|release/incremental`; giữ binary,
deps và source. `compact_environment` chỉ nhận `.venv`/`node_modules` dưới
`.artifacts`; không embedded Git hoặc reparse. Archive SHA256 từng file,
roundtrip và rehash source trước bỏ bản giải nén. Khôi phục archive vào
parent cũ rồi kiểm MANIFEST; hash bytes không chứng nhận Windows ACL/runtime.
Không dùng các API này cho raw/evidence directories đang có consumers.

`snapshot_view` nhận danh sách source/hash, xuất exact-byte view vào một root
riêng. Absolute input chỉ là nguồn đọc, không được ghép thành output path.
Chỉ chấp nhận exact hash hoặc bản LF/CRLF khớp đúng hash đã đăng ký; không
normalize nội dung tùy ý hoặc đổi seal. V7/V8 có newline seals khác nhau nên
không ép cả hai vào cùng byte representation của một checkout.

E có nhiều raw/private inputs được pin bằng path/hash: **không mirror purge**.
Backup plan chỉ xuất argv Robocopy với `/L /E /XJ`, không `/MIR /PURGE`.
Giữ `/L` để xem trước; không tự áp plan vào E. Không merge hoặc xóa các bản
backup cũ chỉ vì trùng tên. MANIFEST và archive của V9 nằm trong private job.

CI `check_anti_bloat.py --base <commit>` chặn mỗi JSON/JSONL/CSV mới/đổi
>1MiB, tổng>8MiB hoặc>100 files. Blobs lịch sử không đổi được grandfathered.
Raw/ledger đặt private, tracked summary nhỏ có provenance; không thay seal
lịch sử bằng bản nén mới. Nén lossless không tự làm raw phù hợp đưa lên Git.

## Phase2: phân hoạch và cold bundles

`deep_storage.disjoint_partitions(inventory)` tách cấp2 và phần `@direct` còn
dư của cha; tổng bytes/files/folders phải khớp phần đọc được, không cộng cha
và con chồng lấn. Lấy Top15 theo files/bytes từ các partition, luôn báo phần
còn lại và permission errors. Không gọi đó là100% allocated space của ổ.

`backup_plan(census, output)` chỉ xuất metadata manifest/hash cho build caches
cũ của E, bảo vệ workspace/ai-engine-jobs/current-owner snapshots. Không xóa,
không cho rằng trùng tên là duplicate content. Trước apply cần đối soát owners,
processes/worktrees, rebuildability hoặc archive và metadata hiện hành.

`cold_zip(root, target, destination, remove=True)` chỉ cho explicit derivatives
dưới `.artifacts` hoặc UI QA artifacts: chặn reparse/embeddedGit, SHA256 từng
file, verifyZIP rồi rehashsource trước remove. MANIFEST giữ restore parent;
giải nén vào parent đó và kiểm từng hash. Có link thì dừng, không tự tháo guard.
`generated_dependencies` chỉ xóa node_modules của UI QA artifacts sau kiểm
ownership/process ở caller; không follow package-manager links. Không áp dụng
cho app active, canonical data, pinned evidence hoặc VI WIP.

V10 dùng Git `repack -a -d --keep-unreachable` với fsck và refs/HEAD trước/sau;
không `prune=now` trên repository có shared worktrees. Các API explicit không
là cleanup daemon; người/agent vẫn phải xác minh scope rồi mới gọi mutation.
