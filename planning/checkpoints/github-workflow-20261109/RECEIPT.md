# GitHub workflow và dọn branch — 09/11/2026

Owner yêu cầu hoàn thiện hướng dẫn/skill sau khi khó hiểu danh sách branch.
Đây là task Git đang được giao riêng; Goal nghiên cứu prop vẫn paused.

## Trader branch và submodule audit — 09/11

Owner yêu cầu kiểm branch Trader và quan hệ workspace→submodule. Kết quả:
`.gitmodules` đúng `projects/trader`, URL`https://github.com/Naqex/trader.git`,
branch hint`main`. Gitlink trong workspace main và actual checkout đều là
`83731fc8b4d7f531225086422266f10396525631`; remote branch
`codex/note-workspace-completion` cũng đúng SHA, không WIP. Pin hợp lệ và
published; branch hint không tự thay exact pin khi clone/update thông thường.

Trader origin/main tại`2cbb9d5baa97830822c66fe66e8841b6c5616849` và pin đang
phân kỳ:32main-only/171pin-only. Vì vậy chưa là thống nhất Trader về main;
không thay pin bằng main hoặc merge726files chỉ để giảm branch trong task
kiểm tra này. Có0PRmở không chứng minh171commits đã hội nhập. Bước hội nhập
Trader riêng cần giữ cả hai nguồn, xử lý dependency/source/contract/UI changes,
kiểm appropriate gates rồi mới cập nhật gitlink workspace bằng PR riêng.

| Local branch sau audit | Trạng thái và hành động |
|---|---|
| main | Bản chuẩn GitHub, worktree dependency-pr-review đang giữ; không đổi |
| codex/note-workspace-completion | Pin workspace hiện hành,171commits chưa vào main; giữ |
| codex/research-metals |166commits chưa vào main, ancestor của pin; worktree đang giữ; giữ |
| codex/research-resume |170commits chưa vào main, ancestor của pin; worktree đang giữ; giữ |
| codex/archive-trader-legacy |26commits chưa vào main, ancestor của pin; giữ, không xóa dựa riêng vào nhánh nghiên cứu |

Đã xóa local `Nam`(`c58270d6`), `codex/github-resolution`(`e92d8d99`) và
`codex/replay-issue-verification`(`8394ec43`) sau explicit ancestry vào
origin/main, noopenPR/noWIP/process-consumer checks. Hai review checkout cũ
E:/ghtr,E:/ghreplay được detach đúng original SHA, file/commit giữ nguyên.
Git branch-d cảnh báo hai tip chưa vào currentHEAD83731fc8; guard main-ancestry
đã xác minh riêng, không dùng currentresearchHEAD làm đích nghiệm thu.

Hai review checkout cũ cũng kế thừa relative core.worktree, làm Git tự nhìn
nhầm metadata và báo xóa giả. Không stage/revert từ status sai; dùng explicit
`--work-tree=<actual checkout>` để kiểm sạch và detach. Không sửa shared/global
config hoặc xóa worktree. Runtime/SDK/DB/product code không đổi.

Fetch-prune đúng origin bỏ19remote-tracking refs đã vắng trên server:
27→8refs gồm origin/HEAD, tương ứng7branch thật trên GitHub. Ba remote
Dependabot PR2/4/9 đã CLOSED nhưng tip không ancestor main (lát thay thế dùng
commit khác), giữ để review provenance/patch nếu sau này dọn, không tự coi
CLOSED là MERGED. Chỉ còn3researchbranches/main và3Dependabotheads trên remote;
không có remote branch mới hoặc force deletion trong audit này.

Kiểm trực tiếp Git/GitHub: default/main, remoteURLs, exactSHA, worktree/status,
ancestry và counts. Source/pin không đổi nên không chạy lại product/backtest.
Private before/after ở
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/dependency-pr-closeout-20261109/trader-branches-before.json`
và`trader-branches-after.json`. Workspace contracts/diff và requiredCI áp dụng
cho receiptPR; không gọi source audit là runtime/broker acceptance. Goal vẫn
paused; issue10 vẫnOPEN. Không mở task nghiên cứu hoặc broker job mới.

## Hội nhập workspace về main theo owner — 09/11

Owner đã giao rõ việc rà và gộp phần tồn về main sau khi xác nhận các merge
trước mới dừng tại nhánh trung gian. Không coi số PR mở bằng0 là all-source
integrated. Base remote main trước hội nhập:
`d9e8389f0492ac9d03be85d5e55ad268f8ad1404`; source workspace đang dùng:
`92fc58018a1ac65c09397ab2fb63e119b3a9c623`.

Trước hòa giải có5commit riêng trên main và430commit riêng trên branch;
diff từ merge-base gồm563files,66.117insertions/118deletions. Đây là lịch sử
nghiên cứu và tooling đã có, không phải563file mới được viết trong lượt này.
Nhánh ngắn `codex/integrate-workspace-main` giữ source đang dùng và merge
main vào để bảo toàn cả hai parent, không rebase/squash/force-push lịch sử.

### Review và giải quyết xung đột

- Nhóm chính: planning/research279files; tooling/ai-engines189files; các
  skill/context/CI/integration/config còn lại được rà theo owner. Không chạy
  lại backtest, mở holdout hoặc sửa kết luận chiến lược khi làm Git.
- Sáu text conflicts là phiên bản cũ của GitHub skill, workflowCI, AGENTS,
  development guide, GitHub README và tests. So sánh hai stage cho thấy main
  chưa có các cải tiến đã kiểm ở branch hiện hành; giữ các bản đầy đủ hiện có,
  gồm paths integration mới, paired-trailer regression và CI shadow gates.
- Conflict thứ7 là Trader gitlink. Giữ pin workspace đang dùng
  `83731fc8b4d7f531225086422266f10396525631`, không tự thay bằng main-side
  `e92d8d99b0936781f7acf67706c92726ab6830f2` hoặc Trader main mới. Hòa giải
  source của repo Trader là task khác; không restart runtime/terminal.
- Git báo thiếu object7ab579... khi thử tự merge submodule; không dùng thông
  báo đó để xóa ref/worktree. Pin được chọn đã có trên remote Naqex/trader,
  checkout sạch và khớp index. Giải quyết ở superproject bằng exact gitlink.
- Kiểm bảo toàn tree với92fc580: mọi file source/research/config và cả8pin
  giữ nguyên; trước ghi receipt chỉ có2delta mới là GitHub skill và branch
  guide. Các commit riêng của main được giữ bằng merge parent, không bỏ history.
- `.codex/config.toml` giữ cấu hình đã có: review policy, tool allowlist,
  Context7 và local Paperclip MCP; không đổi secret/global permission hay
  tuyên bố runtime tool mới được expose. Forks/pins/license giữ nguyên.

### Quy trình sau hội nhập

Nhánh chính là base/đích mặc định. Checkout agent trở về main giữa các việc
khi sạch; việc đáng kể dùng branch ngắn, review/check rồi merge sớm. Sửa nhỏ
trực tiếp main vẫn theo gate riêng, không mặc định direct-push. PR phụ thuộc
được giữ base trung gian khi cần diff nhỏ nhưng phải ghi đường hội nhập còn
lại; task trọn vòng không tự kết thúc ở nhánh trung gian. Giữ điều kiện không
xóa branch/worktree có consumer và không thêm daemon dọn branch.

### Kiểm chứng trước PR về main

- `tooling/check_workspace.py`:9guides/8pins đạt;13tooling tests và5GitHub
  workflow tests đạt. Check diff/metadata chạy trước publish.
- Offline shadow suites:40tests đạt14,921s, dùng fixtures/mocks, không broker/
  provider. Node owner/registered-products:5tests đạt; UI registry0errors.
- Integration doctor:Paperclip/RD-Agent/TradingAgents/Hermes đều source-ready,
  khớp origin/pin/license, không dirty. Không coi source-ready là runtime-ready.
- Skill validator đạt; scoped13skills links0errors/0warnings; maintainer audit
  0errors/0warnings,21skills;global12.279B,project10.073/65.536B,
  reserve55.463B,combined22.352B. Khác byte count cũ do normalization LF khi
  khôi phục exact Git blob, không đổi semantics AGENTS.
- Required GitHub CI trên exact final head phải đạt trước merge; quyền repo
  giữ strict status checks, enforce_admins và PR gate, không bypass.

Receipt giữ scope/evidence; GitHub PR giữ head/merge SHA và trạng thái cuối.
Sau merge kiểm ancestry của cả hai nguồn vào origin/main, fast-forward checkout
chính, rồi chỉ dọn branch đã vào main và không còn PR/worktree/consumer.
Giữ các worktree không thuộc lane này; không thêm commit sau merge chỉ để tự
ghi merge SHA vào cùng PR. Goal nghiên cứu vẫn paused và issue10 vẫn OPEN.

## Owner duyệt merge và đổi quy ước tên branch — 09/11

Owner giao merge các PR và xử lý issue đủ acceptance; không tự công nhận
issue chưa xong là complete. Quy ước mới dùng tên branch tiếng Anh
`codex/<short-task-name>`; mô tả/hướng dẫn cho owner vẫn tiếng Việt. Thay
convention tiếng Việt không dấu ở hướng dẫn và skill GitHub hiện có;
không rename ref đang được PR/worktree/consumer sử dụng. Không thêm skill
dọn branch hoặc background service. Các kết quả cleanup trước đây bên dưới
giữ nguyên là lịch sử.

### Closeout thực tế của lượt owner duyệt

| Repo / phần việc | Kết quả đã đối soát |
|---|---|
| Workspace workflow PR11 | Merge `6b4d0b7` vào `codex/naqex-workspace-pin`, merge SHA `9436fbd`; cả 3 checks đạt trên head mới. Quy ước tiếng Anh và skill đã có ở base đang dùng |
| VI Dubber PR1 | Merge vào main: `eeebe1ba9bc9f0615743e4c3067cf2cefb5a54b3`; CI Python contracts đạt; checkout main fast-forward |
| Quant Trading PR1 | Merge vào master: `203552238965c61b3e5788276ffc36922bd72dae`; CI offline research đạt; checkout master fast-forward |
| Khảo sát EA PR12 | Merge `d32a553` vào workspace branch đang dùng, merge SHA `e0a11f7`; cả 3 checks đạt. Chỉ tài liệu, không mua/chạy bot |
| Trader PR17 | Merge data-worker patch vào main: `3a4c4d65e4570f8e04e5674b7becc4cc59952537`; 5 checks đạt trên head đã review |
| Trader PR18/19/21/23 | Các exact heads đã vào main qua PR22; GitHub xác nhận cả bốn PR MERGED. Kiểm toàn bộ dependency graph cùng nhau |
| Trader PR22 | Head `b0b9b47350aeb62dbe70ed2e86cfc0b3eaa97825`; cả 5 required checks đạt, merge vào main tại `2cbb9d5baa97830822c66fe66e8841b6c5616849` |
| Trader PR20 | Đóng không merge: plugin-react6 yêu cầu Vite8, CI npm peer conflict. Giữ quyết định Vite7/plugin5 từ PR5/16, không bypass peer hoặc đổi Dependabot ignore settings |

PR22 giữ Pydantic2.13.5 và bound `<2.14`: bản nâng gây mất pattern của
Decimal trong schema, không sửa frozen contracts để lấy green. 105 command
contracts/native OpenAPI và prop schema exports giữ nguyên; 155 focused tests,
1 skip và 21 subtests đạt trên dependency graph cuối. Bổ sung đúng hai phiên
bản jsonschema helper0.60.2 vào notice mapping; license từ root crate đã kiểm
khớp byte/hash với upstream commit `0b657fa991c9333908e8c51e8a582d602aac5391`.
Inventory thật:346components/0unresolved;13release-workflow tests đạt. Không
runtime rollout, database migration, broker call hoặc release.

Issue6 đóng theo source/runtime-adoption receipt; issue7 đóng theo
`projects/trader/foundation_v2/evidence/owner-system-audit-20261031/ACCOUNT-LIFECYCLE-20261103.md`.
Commit0b980948 của issue7 có trên published product/research branch nhưng
chưa là ancestor của Trader main: close issue ghi rõ scoped source/local
runtime acceptance, không giả thành hội nhập toàn lịch sử. Issue10 giữ OPEN
và có comment giải thích remaining overnight qualification; không khởi chạy
capture mới từ task Git, Goal nghiên cứu vẫn paused.

Pins VI/Quant cập nhật tới hai merge SHA nêu trên trong workspace commit
`d2923b3`. Giữ Trader pin83731fc8: không thay checkout nghiên cứu hiện tại bằng
main dependency head hoặc tự gộp lịch sử lớn chưa được review.

Đã xóa local `codex/quy-trinh-github`, `codex/khao-sat-bot-tra-phi` và
VI`codex/resource-monitor-ignore`; remote xóa ba ref đó cùng Quant
`codex/datetime-gap-resolution` sau exact-tip/ancestry/worktree/PR checks.
Không xóa branch integration, research worktree hoặc worktree VI còn dùng.
Branch hiện hành của closeout dùng tiếng Anh `codex/merge-closeout`.

Managed dependency worktree ban đầu kế thừa `core.worktree` tương đối của
submodule, làm status nhìn nhầm metadata và báo xóa giả. Chưa stage gì ở
trạng thái sai; sửa duy nhất worktree config của checkout mới, xác nhận
`--show-toplevel` đúng và status sạch. Source checkout khác giữ nguyên.
Bổ sung bẫy này vào branch guide; không đổi shared/global Git config.

Skillcreator validation, scoped links và5workflow tests đạt; maintainer audit
0errors/0warnings,21skills;global12.279B,project10.160/65.536B,reserve55.376B,
combined22.439B. Positive walkthrough: tên mới English; negative: ref đang
được consumer dùng không rename, issue chưa acceptance không tự đóng.
Đây là same-agent review/automated checks, không independent model review.

Kết quả cuối Trader: không còn PR mở; PR17/18/19/21/22/23 MERGED, PR20
CLOSED không merge. Sáu remote Dependabot heads đã tự biến mất sau merge;
script closeout đối soát ancestry/exact tips/open PR/worktree rồi ghi
`Already absent`, không giả nhận đã phát lệnh xóa những ref đó. Local main
fast-forward `2cbb9d5b`; local head PR22 đã dọn bằng `branch -d`.

Worktree kiểm phụ sạch, không job local còn chạy. Codex archive API từ chối
với `This worktree is owned by another task.` dù attachment/creation đã trả
về trong lượt này; giữ checkout, không xóa bằng shell để vượt ownership.
Notice inventory ngoài checkout vẫn còn tại private
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/dependency-pr-closeout-20261109/notices-v1/`.
Các research worktree cũ và runtime/Trader pin83731fc8 được giữ nguyên.

## Thay đổi hướng dẫn

[README GitHub](../../../tooling/github-workflow/README.md) là cửa vào;
[branch lifecycle](../../../tooling/github-workflow/BRANCHES.md) sở hữu quy tắc
tên branch, base/worktree, commit/push/PR/CI/merge, submodule pin và cleanup.
Mở rộng skill `github-issue-workflow` hiện có, giữ tên để không hỏng callers;
AGENTS, development guide, CONTRIBUTING và README root đều dẫn về đúng owner.
Không thêm skill/MCP/hook hoặc quy trình quản lý song song.

Branch mới cho task này: `codex/quy-trinh-github`, base
`codex/naqex-workspace-pin` tại `41b1a48a141087786d3165b1ca1f323528f24e99`.
Đây là PR phụ thuộc source workspace đang dùng, không PR gom toàn bộ lịch sử
chưa vào main. Task này chỉ đổi hướng dẫn và lưu evidence; source hiện tại
không bị thay bằng local main cũ. Hội nhập lịch sử workspace/Trader là review
riêng, không tự merge hàng trăm commits hoặc relabel là đã nghiệm thu.

## Dọn thực tế đã kiểm

GitHub PR metadata, fetched `origin/main`, exact tips, open head/base PRs và
worktree lists được kiểm trước. Lưu đầy đủ tên/SHA và hành động ở private:
`E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/git-branch-cleanup-20261109/`.
`before.json`, `after.json`, `completed.json` giữ cả lần guard từ chối và recovery.
Git/GitHub hiện hành vẫn là nguồn trạng thái; bảng này chỉ là snapshot ngày kiểm.

| Repo | Feature branch đã xóa local | Tip trước khi xóa | PR đã merge vào main |
|---|---|---|---|
| Workspace | `codex/naqex-workspace` | `d62fe3853a65f6735c02d75f89d8d9a6d7692384` | #1 |
| Workspace | `codex/agent-issue-workflow` | `f6151972b87d63d7d1dc2a3a432e81097272f264` | #4 |
| Trader | `codex/naqex-foundation` | `3122cdca38b0cbb7e60bac64cb002ac88cc439a4` | #1 |
| Trader | `codex/release-windows-fixtures` | `c4b8cef0fd7b5bd31a7a182e9617ce706387cdb4` | #10 |
| Trader | `codex/artifact-windows-path-identity` | `78c73f6795d09878ad0422f6c357c2b9fd22e5c6` | #11 |
| Trader | `codex/live-analytics-controls` | `51e6e23ed004e2cc144671927fff83bdb3a2dbc1` | #12 |
| Trader | `codex/trader-agent-provenance` | `4428cc0fabca4766262b6fe827f19e8efa9d600d` | #14 |

7 local branches đã xóa bằng `-d`. Chỉ 1 trong số đó còn trên server:
`workspace:codex/agent-issue-workflow`; đã xóa remote với expected-tip lease
chỉ cho ref cần xóa. 6 remote branches còn lại vốn đã không tồn tại. Không
rewrite commit history; cả 7 tip đều vẫn reachable từ đúng `origin/main`.
Đã kiểm lại cả local refs và remote advertised refs sau thao tác.

Local main không được checkout đã fast-forward và theo đúng `origin/main`:

| Repo | Trước | Sau | Tracking |
|---|---|---|---|
| Workspace | `e0fafdb` | `d9e8389` | Từ `legacy/main` sang `origin/main` |
| Trader | `159cd4fd` | `a8f3749d` | `origin/main` |

`branch -d` từng từ chối một ref sau khi upstream remote đã bị xóa: nó kiểm
HEAD hiện tại thay vì target main. Đã giữ failure, chứng minh ancestry vào
origin/main, trỏ upstream của đúng branch sắp xóa về target rồi dùng lại `-d`.
Không dùng `-D`. Bẫy này đã được bổ sung vào lifecycle guide.

## Các trường hợp được giữ và kiểm quy trình

- **Positive:** 7 tip đúng merged PR, không worktree/open PR, đều vào actual
  main; cleanup thành công và kiểm lại ref không còn.
- **Negative — reused branch:** workspace PR #2 đã merged nhưng branch
  `codex/naqex-workspace-pin` có commits mới sau merge; giữ baseline hiện tại.
- **Negative — worktree:** `codex/github-resolution-pin`, replay verification,
  research-metals/resume và các checkout khác đang gắn worktree được giữ;
  một PR merged không tự cho phép bỏ worktree.
- **Negative — pending PR:** VI Dubber #1 và Quant Trading #1 còn mở, CI đạt
  ở các SHA đã publish; giữ branch, không coi push hoặc CI pass là merge.
- `Nam`/legacy rollback branch chưa có ownership/retirement review riêng được
  giữ; không tự chuyển nhãn lịch sử thành đủ điều kiện xóa.

Đây là walkthrough trên Git/GitHub thật và cùng agent review, không phải
independent model test hoặc hook tự động chặn mọi branch sai tên.

## Kiểm chứng hướng dẫn

`quick_validate.py` cho skill đạt; scoped skill links 0 errors/warnings;
`tooling/github-workflow/check.py` cho forms đạt; diff whitespace check đạt.
Kiểm `--commit` đã bắt lỗi metadata ở `b4db388`: hai dòng AI bị tách thành
hai đoạn do dùng hai `-m`. Giữ nguyên commit đã publish, sửa hướng dẫn dùng
hai `--trailer` và thêm regression chạy native Git trong disposable repo.
Commit sửa kế tiếp phải qua `check.py --commit HEAD`; không nới validator
để chấp nhận block sai hoặc ghi metadata lịch sử là đã pass.
AI environment audit: 0 errors/warnings, 21 skills; global 12.279 B,
project 10.160/65.536 B, reserve 55.376 B, combined 22.439 B.
Chỉ router project đổi, không global config/permissions hoặc native agent assignment.
Không cần rerun backtest/product tests cho thay đổi hướng dẫn này.

## CI: phân loại hai cảnh báo secret lịch sử

Contracts/UI registry đạt, nhưng Gitleaks v8.30.1 phát hiện hai generic-api-key
matches trong prose: từ ghép về cache key tại historical CURRENT-CONTEXT
`c92297ab:12`, và câu về idempotency keys tại receipt `e69729bc:1027`.
Đã đối chiếu preimage và matched spans: không phải secret, credential hoặc
assignment. Không gọi lỗi scanner là lộ key thật; không bỏ gate để pass.

Thêm đúng hai fingerprints vào `.gitleaksignore` hiện có, không path/rule-wide
allowlist, không xóa/viết lại lịch sử. CI giữ `--redact` và thêm `--verbose`
để lần sau hiện file/rule/commit thay vì chỉ số lượng. Cơ chế fingerprint theo
[Gitleaks v8.30.1](https://github.com/gitleaks/gitleaks/blob/v8.30.1/README.md#gitleaksignore).

Để tái hiện, tải asset Windows cùng version từ official GitHub release,
kiểm SHA256 bằng checksums công bố, kiểm zip paths và MIT license; chỉ giải
nén trong `.runtime/tools/gitleaks-8.30.1/` bị ignore, không global install.
Windows archive SHA256:
`d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`.
Giữ redacted findings, scan log và kết quả kiểm trong thư mục runtime đó.
Sau hai ngoại lệ exact, full history scan đạt exit0/0 findings. Positive
control tạo chuỗi giả lập ngẫu nhiên offline trong thư mục tạm vẫn bị
generic-api-key bắt (exit1/1 finding); chuỗi không cấp quyền dịch vụ nào,
không được commit hoặc in ra. Không thay rule, exit code hoặc mức redact.

## Bổ sung quyết định cho AI coding và closeout

Owner hỏi tiếp về sửa trực tiếp/tách branch/gộp và tự dọn sau merge.
Thêm decision table vào branch lifecycle, phân biệt branch với worktree và
file isolation với runtime/data ownership. Skill GitHub tự gọi post-merge
closeout khi merge/cleanup đã được giao quyền; parallel-agent skill dẫn về
cùng bảng, không có rule/daemon cạnh tranh hoặc một branch mới mỗi agent.

Đã kiểm GitHub trước chỉnh sửa: workspace #11, VI Dubber #1 và Quant Trading
#1 đều open, mergeable/CLEAN và CI đạt tại head tương ứng `e17d058`, `d6f280b`,
`52f6501`. Đề xuất gộp ba lát nhỏ; chưa tự merge từ câu hỏi tư vấn “có nên”.
Workspace #11 vào base `codex/naqex-workspace-pin`, không vào main. Toàn bộ
lịch sử chưa vào main của workspace/Trader vẫn cần review hội nhập riêng.
Nếu #11 có commit mới từ bổ sung này thì phải chờ/check CI của HEAD mới,
không dùng bộ check cũ để merge. Không resume Goal nghiên cứu đang paused.

Positive walkthrough: sửa tiếp guide/CI cùng PR #11 giữ nguyên branch;
merge đã có quyền → tự closeout. Negative walkthrough: nhiều agent chỉ đọc
không sinh thêm worktree; checkout của lane khác đang ghi giữ nguyên; query
“có nên merge” không mở authority hoặc tự xóa branch gắn worktree.
Hai skill được validate/scoped-link-check đạt; GitHub workflow checker và
diff check đạt. Maintainer audit vẫn 0 errors/warnings, 21 skills;
project 10.160/65.536 B, reserve 55.376 B, combined 22.439 B.
