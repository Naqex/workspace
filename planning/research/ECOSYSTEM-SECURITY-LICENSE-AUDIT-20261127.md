# Kiểm Toán Hệ Sinh Thái, Bảo Mật Gitleaks & Giấy Phép 5 Kho Mã Nguồn Naqex

- **Ngày kiểm toán:** 27/11/2026 (UTC: 2026-11-26T20:35Z)
- **Phạm vi:** Toàn bộ 4 trụ cột hệ sinh thái (`UI-Systems/UI`, `education`, `projects/integrations/*`, `check_workspace.py`), quét bí mật nội bộ Gitleaks `v8.30.1` trên đủ 5 kho Git, kiểm toán giấy phép & chuỗi cung ứng trên `9` môi trường Python `.venv` (`385` lượt cài đặt gói), `6` tệp khóa JavaScript (`531` gói npm) và Rust `Cargo.lock` (`297` crate), cùng truy vết chuyên sâu gói `diffq-fixed==0.2.4`.
- **Ranh giới an toàn đã giữ chặt:** `OrderSend = 0` · `Holdout 2025+ SEALED` · `0` thao tác lên `naqex-node1` · `0` lệnh `git commit`/`git push` · `5/5` tệp đang làm dở (`WIP`) tại `projects/vi-dubber` nguyên vẹn 100% theo mã băm SHA-256.
- **Mức phân loại tài liệu:** Tầng 1 công khai sạch — không chứa địa chỉ IP nội bộ/Tailscale, tên người dùng thật, tên ứng dụng cloud nội bộ, tên bot nội bộ hay bất kỳ khóa bí mật nào.

---

## 1. Tóm Tắt Điều Hành

Kết quả kiểm toán toàn diện đạt **ĐẠT VỀ BẢO MẬT & CÁCH LY**, với **1 rào cản pháp lý cần gỡ trước khi thương mại hóa `projects/vi-dubber`** và một số điểm cập nhật tài liệu tuân thủ mức vừa:

- 🟢 **4/4 Trụ cột hệ sinh thái ĐẠT (`EXIT 0`):** `ui-registry-check.mjs` (`2` sản phẩm, `3` pin, `0` lỗi), `registered-products.test.mjs` (`2/2` test đạt), `education/check_setup.py` (`8` module, `24` bài học, `56` lượt học), `integrations/doctor.mjs` (`4/4` nguồn `source-ready`, bao gồm `hermes-agent`), và `check_workspace.py` (`9` tài liệu hướng dẫn, `8` submodule ghim SHA chuẩn).
- 🟢 **Quét bí mật Gitleaks `v8.30.1` (đã xác minh SHA-256 tệp phát hành gốc): `0` bí mật thật trên cả 5 kho Git (`2.908` commit lịch sử `HEAD`/`hygiene` + quét cây tệp hiện hành).** Toàn bộ `1` cảnh báo ở `private_vault` và `111` cảnh báo thô khi quét không cấu hình ở các thư mục con đều đã được mở kiểm tra thực tế và xác minh **100% là dương tính giả** (tên trường JSON, mã băm SHA-256, mã fixture thử nghiệm, chuỗi minh họa tiếng Việt). Kho `private_vault` (`449` tệp) có **`0` mật khẩu sàn, `0` khóa API, `0` token Heroku, `0` token Telegram, `0` khóa riêng tư SSH/PEM**.
- 🟢 **Cách ly giấy phép Copyleft mạnh ở mã lõi & sản phẩm: `0` vi phạm trên `1.328` tệp `.py`.** Không có bất kỳ dòng `import` hay chuỗi nhắc tới `backtesting` (`AGPL-3.0`), `backtrader` (`GPLv3+`) hay `vectorbt` (`Apache-2.0 + Commons Clause`) trong `quant_core`, `quant_factory`, `ops_cloud`, toàn bộ `tooling/ai-engines`, `projects/trader`, `projects/quant-trading/src` và `projects/vi-dubber/src`.
- 🟡 **Giấy phép Copyleft yếu (LGPL / MPL-2.0): An toàn khi liên kết động nhưng cần bổ sung thông báo bản quyền.** Ghi nhận `11` nhóm gói Python (`nautilus_trader`, `portion`, `psycopg`, `psycopg-binary`, `psycopg-pool`, `soxr`, `orjson`, `tqdm`, `certifi`, `hypothesis`, `pytest-base-url`) và `3` gói JS (`@blocknote/core`, `@blocknote/react`, `@blocknote/ariakit`). Tệp `projects/trader/THIRD_PARTY_NOTICES.md` đã ghi tốt cho BlockNote và NautilusTrader, nhưng `THIRD_PARTY_NOTICES.md` ở gốc và `projects/vi-dubber` cần bổ sung thêm `hermes-agent`, `soxr`, `orjson`, `psycopg*`, `portion`, `tqdm`, `certifi`.
- 🔴 **Rào cản thương mại hóa duy nhất (P0 cho `projects/vi-dubber`):** Gói **`diffq-fixed==0.2.4` (`CC-BY-NC-4.0` — cấm dùng cho mục đích thương mại)** đang được cài tự động vào `projects/vi-dubber/.venv` do `audio-separator==0.47.0` khai báo phụ thuộc cứng trên Windows (và `diffq==0.2.4` cũng `CC-BY-NC-4.0` trên Linux/macOS). Tin tốt là **`vi-dubber` hoàn toàn KHÔNG nạp hay gọi `diffq` khi chạy thật** (vì đang dùng mô hình `BS-RoFormer` thuộc nhánh `MDXC`, không dùng `Demucs`), nên có thể gỡ sạch gọn gàng trước khi đóng gói bán sản phẩm hoặc mở dịch vụ thu phí.

---

## 2. Kết Quả Kiểm Định 4 Trụ Cột Hệ Sinh Thái (Chỉ Đọc)

| Trụ cột | Lệnh kiểm tra đã chạy | Kết quả | Số liệu xác minh chính xác |
|---|---|---|---|
| **UI-Systems & UI** | `node tooling/ui-qa/ui-registry-check.mjs --json` | 🟢 PASS (`exit 0`) | `projectCount = 2` (`projects/trader`, `projects/vi-dubber`), `pinCount = 3`, `errorCount = 0`, `partialProjects = 2` |
| **UI Registered Products** | `node --test tooling/ui-qa/tests/registered-products.test.mjs` | 🟢 PASS (`exit 0`) | `2/2` bài kiểm tra đạt trong `124,89 ms` (loại trừ bản checkout runtime cũ, chặn đường dẫn thoát khỏi `projects/`) |
| **Giáo dục (`education/`)** | `python education/check_setup.py` | 🟢 PASS (`exit 0`) | `4` mục đánh giá đầu vào lưu trữ, `7` kiểm tra đáp án cũ, `8` module, `24` bài học/đáp án/rubric, `26` trường số, `12` phép tính mẫu, `56` lượt học đã ghi |
| **Tích hợp AI (`integrations/`)** | `node tooling/integrations/doctor.mjs` | 🟢 PASS (`exit 0`) | `4/4` nguồn ở trạng thái `source-ready`, toàn bộ `pinMatches = true`, `originMatches = true`, `licensePresent = true`, `dirty = false` |
| **Hợp đồng Workspace** | `python tooling/check_workspace.py` | 🟢 PASS (`exit 0`) | `9` tài liệu hướng dẫn chính không gãy liên kết và sạch định danh cũ; `8` submodule khớp đúng URL và mã SHA 40 ký tự |

### 2.1 Chi tiết Trụ cột UI-Systems & UI

- Nền tảng toàn cục (`UI-Systems/ui-platform.json`): `schemaVersion = 1`, `platformVersion = 0.1.0-dev`, định dạng token `DTCG-compatible`, chính sách nâng cấp `pinned-versions-with-reviewed-upgrades`.
- Lớp tên miền giao dịch (`UI/domain-ui.json`): `domain = trading`, dự án thí điểm `trader`.
- Cả `3` bản chụp CSS dùng chung đều khớp **100% từng byte** với trình xuất token chuẩn (`errors = []`):
  1. `projects/trader` → `annam-productivity@1.0.0` (phạm vi `prop.report.controls`, bản chụp `foundation_v2/web/src/ui-system.snapshot.css`, `sourceSha256 = 578f95b7...5186f9`, `snapshotSha256 = 85f7fa1b...0de2c8`).
  2. `projects/trader` → `annam-compact@0.3.0` (phạm vi `application.palette`, `control-geometry`, `typography`, `motion`, `interaction-states`, bản chụp `foundation_v2/web/public/project-palette.css`, `sourceSha256 = 1d7675bc...113a71`, `snapshotSha256 = a7698775...aa1b81`; đã vượt cổng kiểm chứng `focusedReceipt` cho `state`, `keyboard`, `theme`, `contrast`).
  3. `projects/vi-dubber` → `annam-productivity@1.0.0` (phạm vi `header.raw-json-control`, bản chụp `frontend/src/ui-system.snapshot.css`, khớp đúng cặp mã băm như trên).
- Lưu ý trạng thái triển khai: Cả hai dự án đều đang ở mức `adoption = partial` (`projects/trader` còn 5 cổng nghiệm thu chờ chốt gồm `native-browser-zoom`, `axe-wcag`, `canonical-golden`, `long-duration-memory`, `full-bleed-promotion`; chưa bật cờ `approvedForProductionPropagation`).

### 2.2 Chi tiết Trụ cột Giáo Dục (`education/`)

- Toàn bộ cấu trúc khóa học Anh–Việt (`8` module, `24` bài học/đáp án/rubric, liên kết nội bộ, `26` trường số học và `12` phép tính mẫu) đều hợp lệ và khớp chặt chẽ; đã ghi nhận `56` lượt học của học viên.
- Ghi nhận vệ sinh cục bộ (không ảnh hưởng Git): tồn tại thư mục môi trường ảo chưa theo dõi `education/.venv-mt5/`. Thư mục này không nằm trong Git, nhưng khi chạy quét thư mục thô `gitleaks detect --no-git` trên `education/` đã tạo `6` cảnh báo dương tính giả từ tệp kiểm thử nội bộ của `numpy` (`test_generator_mt19937.py`). Khuyến nghị rà soát dọn bỏ hoặc chuyển ra `.runtime/` nếu không còn dùng.

### 2.3 Chi tiết 4 Nguồn Tích Hợp (`projects/integrations/*`)

| ID tích hợp | Vai trò | Đường dẫn | Origin URL | Upstream URL | Mã SHA đã ghim | Giấy phép gốc | Trạng thái Doctor |
|---|---|---|---|---|---|---|---|
| `paperclip` | `control-plane-ui` | `projects/integrations/paperclip` | `https://github.com/Naqex/paperclip.git` | `https://github.com/paperclipai/paperclip.git` | `550175702676e03cd9cd92b555e1fd8372749509` | **MIT** | 🟢 `source-ready`, sạch |
| `rd-agent` | `research-worker` | `projects/integrations/rd-agent` | `https://github.com/microsoft/RD-Agent.git` | `https://github.com/microsoft/RD-Agent.git` | `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` | **MIT** | 🟢 `source-ready`, sạch |
| `tradingagents` | `analysis-worker` | `projects/integrations/TradingAgents` | `https://github.com/Naqex/TradingAgents.git` | `https://github.com/TauricResearch/TradingAgents.git` | `ecaafe585a98478ef7dbcf5678f4a64b5e7d1066` | **Apache-2.0** | 🟢 `source-ready`, sạch |
| `hermes` | `research-review-worker` | `projects/integrations/hermes-agent` | `https://github.com/NousResearch/hermes-agent.git` | `https://github.com/NousResearch/hermes-agent.git` | `bf0203a794a07aac3ff764972ab9087baa4e4f4e` | **MIT** | 🟢 `source-ready`, sạch |

- **Điểm cần bổ sung tài liệu:** Tệp `THIRD_PARTY_NOTICES.md` ở thư mục gốc đã liệt kê `paperclip`, `rd-agent`, `TradingAgents`, nhưng **chưa có dòng ghi nhận cho `projects/integrations/hermes-agent` (Nous Research, MIT)**. Cần thêm 1 dòng vào bảng `THIRD_PARTY_NOTICES.md` ở đợt cập nhật kế tiếp.

---

## 3. Kiểm Toán Bí Mật Nội Bộ Gitleaks (`v8.30.1`) Trên Đủ 5 Kho Git

### 3.1 Xác minh tính toàn vẹn công cụ Gitleaks nội bộ

- **Đường dẫn công cụ:** `.runtime/tools/gitleaks/gitleaks.exe` (`version 8.30.1`).
- **Xác minh SHA-256 gói nén chính thức (`gitleaks_8.30.1_windows_x64.zip`):**
  - Giá trị tính toán thực tế: `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`
  - Giá trị trong `gitleaks_8.30.1_checksums.txt` (dòng 10): `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e` → **KHỚP 100%**.
- **SHA-256 tệp thực thi đã giải nén (`gitleaks.exe`):** `17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c`.

### 3.2 Kết quả quét lịch sử Git (`gitleaks git --redact --no-banner --verbose --log-opts ...`)

| Kho Git | Nhánh / Mốc quét | Commit quét (Gitleaks / `rev-list`) | Dung lượng quét | Thời gian | Cấu hình bỏ qua | Cảnh báo thô | Bí mật thật | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| `TradingWorkspace` (gốc) | `HEAD` | `1.334` / `1.434` | `49,38 MB` | `3,13 s` | `.gitleaks.toml` + `.gitleaksignore` (`30` dấu vân tay) | `0` | **`0`** | 🟢 SẠCH |
| `private_vault` (Tầng 2) | `HEAD` | `14` / `15` | `21,06 MB` | `2,36 s` | Chưa có | `1` (dương tính giả đã xác minh) | **`0`** | 🟢 SẠCH (1 FP) |
| `projects/quant-trading` | `HEAD` | `67` / `68` | `979,71 KB` | `0,40 s` | Không cần | `0` | **`0`** | 🟢 SẠCH |
| `projects/trader` | `HEAD` | `1.108` / `1.136` | `93,42 MB` | `5,22 s` | `.gitleaksignore` (`428` dòng dấu vân tay) | `0` | **`0`** | 🟢 SẠCH |
| `projects/vi-dubber` | `HEAD` (`eeebe1b`) | `190` / `191` | `13,67 MB` | `1,42 s` | Không cần | `0` | **`0`** | 🟢 SẠCH |
| `projects/vi-dubber` | `codex/agent-first-hygiene` (`2f4815f`) | `195` / `196` | `15,16 MB` | `1,55 s` | Không cần | `0` | **`0`** | 🟢 SẠCH |

*Ghi chú kỹ thuật:* Số commit Gitleaks báo nhỏ hơn nhẹ so với `git rev-list --count` vì Gitleaks bỏ qua các merge commit hoặc commit không có diff văn bản.

### 3.3 Kiểm tra chuyên sâu `private_vault` (Chặn tuyệt đối bí mật Tầng 3)

Ngoài lượt quét Gitleaks `git` và `detect --no-git`, chúng tôi đã chạy bộ quét chuyên biệt Tầng 3 trên toàn bộ **`449` tệp** hiện hữu trong `private_vault/` nhằm săn mật khẩu sàn giao dịch (`Password`, `MasterPassword`, `InvestorPassword`, `mt5_pass`), khóa API (`sk-`, `AIza`, `ghp_`, `github_pat_`), token Heroku (`HRKU-`), token bot Telegram (`<id>:AA...`), khóa riêng tư SSH/PEM (`BEGIN ... PRIVATE KEY`) và tệp cấu hình nhạy cảm (`.env`, `.pem`, `.key`, `id_rsa`, `credentials*`):

- **Tệp có tên nghi vấn nhạy cảm:** `0` tệp.
- **Lượt khớp mẫu bí mật Tầng 3:** **`0` lượt**.
- **Giải trình duy nhất `1` cảnh báo của Gitleaks trong `private_vault`:**
  - Vị trí: `strategies/wave2-overnight-rd-20261125/crypto_spot_b06_b02_audit/live_liquidity_audit_20261125.json` (dòng 8–9, luật `generic-api-key`, entropy `3,577`).
  - Nội dung thực tế đã đọc trực tiếp: dòng 8 là `"binance_base_used": "https://api.binance.com",` và dòng 9 là `"ticker_24h_fetch_ms": 396.6,`. Do từ `api` xuất hiện trong tên miền công khai `api.binance.com` ngay trước tên khóa `"ticker_24h_fetch_ms"` trên dòng tiếp theo, biểu thức mặc định của Gitleaks nhận nhầm tên trường thời gian phản hồi này là khóa API. **Xác minh 100% là dương tính giả — không có bất kỳ khóa bí mật nào.**

### 3.4 Kết quả quét thư mục hiện hành (`gitleaks detect --no-git`) trên 5 kho

Chúng tôi chạy bổ sung `gitleaks detect --no-git --redact` (dùng bộ luật mặc định khắt khe nhất, không dùng tệp bỏ qua của repo) trên toàn bộ các thư mục mã nguồn/tài liệu đã theo dõi và `11` tệp cấu hình gốc (`AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `THIRD_PARTY_NOTICES.md`, `pyproject.toml`, `.pre-commit-config.yaml`, `.gitmodules`, cùng các `pyproject.toml` và `config.yaml` của 3 sản phẩm):

- **Nhóm sạch `0` cảnh báo ngay cả dưới bộ luật mặc định thô:** Toàn bộ `11` tệp gốc/cấu hình, `docs/`, `knowledge/`, `UI/`, `UI-Systems/`, `.agents/`, `.github/`, `tooling/{github-workflow,integrations,paperclip,search,ui-qa}/`, `projects/quant-trading/{src,tests,docs}/`, `projects/trader/{foundation_v2/web/src,scripts,docs}/`, `projects/vi-dubber/{src,tests,frontend/src,docs}/`.
- **Nhóm phát sinh `111` cảnh báo `generic-api-key` khi chạy không kèm `.gitleaks.toml`/`.gitleaksignore` (`100` ở tệp tracked, `11` ở tệp untracked) — ĐÃ PHÂN LOẠI & XÁC MINH 100% DƯƠNG TÍNH GIẢ:**
  1. `planning/` (`89` lượt: `88` tracked + `1` untracked `vue-*.js`): gồm `54` trường mô tả khóa chiến lược (ví dụ mã định danh `us500-v11-admission`) trong `STRATEGY-CATALOGUE-20261107.json` (đã có quy tắc allowlist chính xác trong `.gitleaks.toml`), mã băm SHA-256 trong các biên nhận kiểm định lịch sử (`receipt.json`, `PS02-*.json`, `PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114.json`), mã fixture cục bộ `CO04_CHARLIE_83F2` trong `CO-04-batch-candidate-r1.json` / `lane-output.json`, và văn xuôi tiếng Việt nhắc cụm `"idempotency keys"` trong `RECEIPT.md`. Toàn bộ đã nằm trong danh sách dấu vân tay chính xác tại `.gitleaksignore` gốc.
  2. `tooling/ai-engines/` (`2` lượt tracked): `HEROKU-DEPLOY-GUIDE.md:L56` chứa chuỗi hướng dẫn giả `"dung-chuoi-bi-mat-o-buoc-2"` và `pass27_portfolio_m1_phase_audit.py:L917` chứa biến vòng lặp `pol_key` đi cùng tên gói quỹ `FTMO_SWING_10K`. Cả hai đã được định nghĩa allowlist hẹp đúng dòng/tệp trong `.gitleaks.toml`.
  3. `projects/trader/foundation_v2/` (`9` lượt tracked): `mt5_connector.py:L26` (hằng mã lỗi công khai `'mt5_auth_failed'`), `ai_mt5_tools.rs:L529,L659` (tên biến môi trường kiểm thử đơn vị `"TW_MT5_MCP_KEY_FIXTURE"`), `test_m6_connector_ledger*.py` (`6` khóa `idempotency_key` kiểm thử ngoại tuyến). Toàn bộ đã có trong `projects/trader/.gitleaksignore`.
  4. `education/.venv-mt5/` (`6` lượt untracked) và `tooling/agent-workflow/runs/` (`4` lượt untracked): tệp kiểm thử thư viện `numpy` MT19937 và bản sao biên nhận chạy agent cũ (không theo dõi Git).
  5. `private_vault/` (`1` lượt tracked): chính là trường `"ticker_24h_fetch_ms"` sau `api.binance.com` đã chứng minh dương tính giả ở Mục 3.3.

**Ghi chú riêng cho `projects/vi-dubber/config.yaml` (WIP):** Dòng 27 có trường `aurora_api_key: "123456"` đi kèm `aurora_base_url: http://127.0.0.1:8317` (chuỗi mẫu cục bộ nội máy). Tệp này thuộc 5 tệp WIP được giữ nguyên tuyệt đối; trước khi chia sẻ hoặc đẩy công khai, vẫn nên tách giá trị khóa ra biến môi trường theo chuẩn OPSEC.

---

## 4. Ma Trận Kiểm Toán Thư Viện & Giấy Phép Toàn Hệ Sinh Thái (5 Kho)

### 4.1 Tổng quan kiểm kê trên `9` môi trường Python, `6` khóa JS và Rust

| Môi trường / Tệp khóa | Hệ sinh thái | Tổng số gói | Tầng 0: Nội bộ Naqex | Tầng 1: Thoáng (MIT/BSD/Apache/ISC...) | Tầng 2: Copyleft yếu (LGPL/MPL-2.0) | Tầng 3: Copyleft mạnh / Phi thương mại / Giới hạn bán |
|---|---|---:|---:|---:|---:|---:|
| `.runtime/quant-audit-v24` | Python (Quant Audit) | `63` | `0` | `58` | `5` | `0` |
| `projects/quant-trading/.venv` | Python (Quant Lab) | `16` | `1` | `15` | `0` | `0` |
| `projects/trader/foundation_v2/.venv` | Python (Trader API) | `31` | `0` | `27` | `4` | `0` |
| `projects/trader/foundation_v2/engine_runtime/.venv` | Python (Trader Engine) | `15` | `0` | `12` | `3` | `0` |
| `projects/vi-dubber/.venv` | Python (VI Dubber) | `169` | `1` | `162` | `5` | **`1` (`diffq-fixed`, CC-BY-NC-4.0)** |
| `tooling/strategy-engines/backtesting/.venv` | Python (Sandbox) | `14` | `0` | `13` | `0` | **`1` (`backtesting`, AGPL-3.0)** |
| `tooling/strategy-engines/backtrader/.venv` | Python (Sandbox) | `5` | `0` | `4` | `0` | **`1` (`backtrader`, GPLv3+)** |
| `tooling/strategy-engines/observer/.venv` | Python (Observer RO) | `5` | `0` | `5` | `0` | `0` |
| `tooling/strategy-engines/vectorbt/.venv` | Python (Sandbox) | `67` | `0` | `64` | `2` | **`1` (`vectorbt`, Commons Clause)** |
| `projects/trader/foundation_v2/web/package-lock.json` | JS / npm (Trader Web) | `184` | `0` | `181` | `3` (`@blocknote/*`) | `0` |
| `projects/trader/foundation_v2/{data_worker,experiments}/package-lock.json` | JS / npm (Trader Aux) | `145` | `0` | `145` | `0` | `0` |
| `projects/vi-dubber/frontend/package-lock.json` | JS / npm (VI Dubber UI) | `189` | `0` | `189` | `0` | `0` |
| `tooling/{search/codegraph,ui-qa}/package-lock.json` | JS / npm (Tooling) | `13` | `0` | `13` | `0` | `0` |
| `projects/trader/foundation_v2/api-rust/Cargo.lock` | Rust (Trader API) | `297` | `1` | `277` đã kiểm (`275` đơn + `2` kép thoáng) · `19` crate đa nền tảng chưa tải cache | `0` (trong `277` crate đã kiểm) | `0` (trong `277` crate đã kiểm) |

### 4.2 Phân tích chi tiết 4 tầng chính sách giấy phép

#### Tầng 1 — Giấy phép Thoáng (MIT / BSD / Apache-2.0 / ISC / PSF-2.0 / Unlicense / Zlib / CC0 / Artistic)
- **Trạng thái:** 🟢 **Sạch & sẵn sàng thương mại.** Nghĩa vụ duy nhất khi phân phối là giữ lại thông báo bản quyền và văn bản giấy phép gốc của tác giả (nhất là tệp `NOTICE` của nhóm Apache-2.0).
- **Hai trường hợp đã mở trực tiếp `LICENSE.txt` để tránh nhầm lẫn:**
  1. `MetaTrader5==5.0.6231` (có trong `quant-audit-v24`, `trader/foundation_v2`, `engine-observer`): Bản thân thư viện bọc Python phân phối trên PyPI mang giấy phép **MIT** (`Copyright 2000-2025 MetaQuotes Ltd.`). Tuy nhiên, phần mềm đầu cuối **MetaTrader 5 trên Windows** cài tách rời thuộc bản quyền thương mại độc quyền của MetaQuotes và không được đóng gói vào sản phẩm Naqex (đã nêu đúng trong `projects/trader/THIRD_PARTY_NOTICES.md`).
  2. `text-unidecode==1.3` (trong `projects/vi-dubber/.venv`, do `python-slugify==8.0.4` kéo theo): Mang **giấy phép kép `Artistic License` HOẶC `GPLv2+`**. Dự án chọn nhánh **Artistic License** (thoáng), không bị ràng buộc bởi GPL; khuyến nghị ghi rõ lựa chọn nhánh này khi xuất danh mục bản quyền phát hành.

#### Tầng 2 — Copyleft Yếu / Bắt buộc Ghi chú (LGPL-2.1/3.0 & MPL-2.0)

| Gói & Phiên bản | Giấy phép chính xác | Môi trường chứa | Chuỗi phụ thuộc kéo vào | Nghĩa vụ tuân thủ khi phân phối | Đã ghi trong `THIRD_PARTY_NOTICES.md`? |
|---|---|---|---|---|---|
| `nautilus_trader==1.231.0` | `LGPL-3.0-or-later` | `quant-audit-v24`, `trader/engine_runtime` | Trực tiếp (tùy chọn engine) | Giữ nguyên liên kết động (import gói rời, không trộn tĩnh vào file chạy đóng), giữ thông báo LGPLv3, cho phép người dùng tự thay thế phiên bản thư viện tương thích | 🟢 Đã có ở `projects/trader/THIRD_PARTY_NOTICES.md` (cần bổ sung bản gốc nếu dùng từ root) |
| `portion==2.6.2` / `2.6.3` | `LGPL-3.0-or-later` | `trader/engine_runtime`, `quant-audit-v24` | Phụ thuộc của `nautilus_trader` | Tương tự LGPL-3.0: giữ dạng mô-đun Python rời, kèm văn bản giấy phép LGPL-3.0 khi đóng gói cùng Nautilus | 🟡 Chưa nêu tên riêng (nên ghép chung nhóm Nautilus) |
| `psycopg==3.3.6`, `psycopg-binary==3.3.6`, `psycopg-pool==3.3.3` | `LGPL-3.0-only` | `projects/trader/foundation_v2/.venv` | Trực tiếp trong `foundation_v2/pyproject.toml` | Giữ cài dạng wheel/thư viện động tách rời khỏi mã nguồn Naqex; nếu phân phối bản cài đặt kèm Python runtime phải đính kèm thông báo LGPL-3.0 và cách thay thế `psycopg` | 🟡 Chưa liệt kê cụ thể trong `projects/trader/THIRD_PARTY_NOTICES.md` |
| `soxr==1.1.0` | `LGPL-2.1-or-later` | `projects/vi-dubber/.venv` | `librosa==1.0.0`, `vieneu==3.7.1` | Giữ wheel `soxr` (và thư viện C `libsoxr`) ở dạng liên kết động tách rời; khi đóng gói bản thương mại phải kèm `COPYING.LGPL`, `LICENSE-libsoxr.txt`, `LICENSE-PFFFT.txt` và cho phép relink | 🟡 Chưa liệt kê cụ thể trong `projects/vi-dubber/THIRD_PARTY_NOTICES.md` |
| `@blocknote/core`, `@blocknote/react`, `@blocknote/ariakit` (`0.55.0`) | `MPL-2.0` | `projects/trader/foundation_v2/web` | Trực tiếp trong web lockfile | Copyleft cấp từng tệp: giữ nguyên gói gốc không sửa, giữ thông báo MPL-2.0, cung cấp đường dẫn mã nguồn phiên bản tương ứng khi phân phối bundle web | 🟢 Đã ghi rất chuẩn trong `projects/trader/THIRD_PARTY_NOTICES.md` |
| `orjson==3.12.0` | `MPL-2.0 AND (Apache-2.0 OR MIT)` | `projects/vi-dubber/.venv` | Gói biên dịch JSON tốc độ cao | Do có toán tử `AND` với `MPL-2.0` cho một số tệp nội bộ, khi phân phối cần kèm cả thông báo `LICENSE-MPL-2.0` và chọn `MIT` hoặc `Apache-2.0` | 🟡 Chưa liệt kê cụ thể |
| `tqdm==4.70.1` | `MPL-2.0 AND MIT` | `quant-audit-v24`, `trader/engine_runtime`, `vi-dubber`, `engine-vectorbt` | `audio-separator`, `faster-whisper`, `transformers`, `nautilus_trader`, `fsspec`... | Giữ nguyên gói gốc không sửa và đính kèm `LICENCE` (MPL-2.0 + MIT) khi phát hành | 🟡 Chưa liệt kê cụ thể |
| `certifi==2026.7.22` / `2026.10.23` | `MPL-2.0` | `quant-audit-v24`, `trader/foundation_v2`, `vi-dubber`, `engine-vectorbt` | `httpx`, `httpcore`, `requests`, `yt-dlp` | Giữ nguyên kho chứng chỉ Mozilla không sửa và giữ thông báo `MPL-2.0` khi phát hành | 🟡 Chưa liệt kê cụ thể |
| `hypothesis==6.170.17` & `pytest-base-url==2.1.0` | `MPL-2.0` | `quant-audit-v24` (`hypothesis`), `vi-dubber` (`pytest-base-url`) | Chỉ dùng cho kiểm thử phát triển (`dev`/`test`) | Không đóng gói vào bản chạy sản xuất (dev-only) → rủi ro phân phối bằng `0` | 🟢 Dev-only (không đóng gói sản phẩm) |

#### Tầng 3 — Copyleft Mạnh, Nguồn Mở Có Điều Kiện & Phi Thương Mại (AGPL-3.0 / GPLv3+ / Commons Clause / CC-BY-NC-4.0)

1. **Cách ly tuyệt đối 3 engine nghiên cứu trong `tooling/strategy-engines/`:**
   - `backtesting==0.6.6` (`AGPL-3.0`) — chỉ nằm trong `tooling/strategy-engines/backtesting/.venv`.
   - `backtrader==1.9.78.123` (`GPLv3+`) — chỉ nằm trong `tooling/strategy-engines/backtrader/.venv`.
   - `vectorbt==1.2.0` (`Apache-2.0 + "Commons Clause" License Condition v1.0`, cấm bán lại sản phẩm/dịch vụ lấy giá trị chính từ thư viện) — chỉ nằm trong `tooling/strategy-engines/vectorbt/.venv`.
   - **Bằng chứng kiểm toán mã nguồn (AST + quét từ khóa toàn văn):**

| Cây mã nguồn lõi / sản phẩm Naqex | Số tệp `.py` đã kiểm | Lượt `import` qua AST (`backtesting`/`backtrader`/`vectorbt`) | Lượt nhắc tên trong văn bản mã nguồn | Trạng thái |
|---|---:|---:|---:|---|
| `tooling/ai-engines/quant_core` | `37` | `0` | `0` | 🟢 SẠCH |
| `tooling/ai-engines/quant_factory` | `61` | `0` | `0` | 🟢 SẠCH |
| `tooling/ai-engines/ops_cloud` | `14` | `0` | `0` | 🟢 SẠCH |
| Toàn bộ `tooling/ai-engines` (bao gồm 3 thư mục trên) | `755` | `0` | `0` | 🟢 SẠCH |
| `projects/trader` (toàn bộ mã Python) | `498` | `0` | `0` | 🟢 SẠCH |
| `projects/quant-trading/src` | `35` | `0` | `0` | 🟢 SẠCH |
| `projects/vi-dubber/src` | `40` | `0` | `0` | 🟢 SẠCH |
| **TỔNG CỘNG KHÔNG TRÙNG LẶP** | **`1.328`** | **`0`** | **`0`** | 🟢 **CÁCH LY 100%** |

2. **`tooling/reverse-skill`:** Gốc `MIT`, chứa các công cụ con `GPLv3` — chỉ nằm trong submodule tham khảo riêng, đã có quy định không tự chạy và đã ghi rõ trong `THIRD_PARTY_NOTICES.md` gốc.
3. **`diffq-fixed==0.2.4` (`CC-BY-NC-4.0`) trong `projects/vi-dubber/.venv`:** Xem phân tích pháp y đầy đủ tại Mục 5 bên dưới.

#### Tầng 4 — Bản quyền Nội bộ Naqex & Thành phần Thương mại / Trọng số AI Bên ngoài
- Toàn bộ mã nguồn tự viết thuộc `TradingWorkspace`, `projects/quant-trading`, `projects/trader` và `projects/vi-dubber` thống nhất áp dụng **`Naqex Source Available License 1.0.0`**.
- Các thành phần ngoài chuỗi khóa Python/JS/Rust (như `TradingView Advanced Charts`, đầu cuối `MetaTrader 5`, `QuantDataManager`, tệp chạy `FFmpeg` có thể biên dịch với codec GPL như `libx264`/`libx265`, và trọng số mô hình AI `BS-RoFormer`, `Whisper large-v3`, `VieNeu`) mang điều khoản riêng biệt, không tự động trở thành giấy phép mở nhờ mã bọc Python.

---

## 5. Truy Vết Chuyên Sâu `diffq-fixed==0.2.4` (`CC-BY-NC-4.0`) Trong `projects/vi-dubber`

### 5.1 Chuỗi phụ thuộc chính xác (từ `pyproject.toml` → `uv.lock` → `.venv`)

```text
vi-dubber==0.1.0  (projects/vi-dubber/pyproject.toml:L9 -> "audio-separator[cpu]>=0.44.2,<0.48")
  └─ audio-separator==0.47.0  (Giấy phép: MIT)
       ├─ Trên Windows (sys_platform == "win32"):  diffq-fixed>=0.2  ->  diffq-fixed==0.2.4
       └─ Trên Linux/macOS (sys_platform != "win32"): diffq>=0.2     ->  diffq==0.2.4
```

- **Bản chất gói `diffq-fixed==0.2.4`:** Là bản fork sửa tương thích Python 3.11+ (`JackismyShephard/diffq`) từ dự án lượng tử hóa mô hình `facebookresearch/diffq` (Alexandre Défossez, Yossi Adi, Gabriel Synnaeve).
- **Giấy phép xác minh trực tiếp từ `diffq_fixed-0.2.4.dist-info/METADATA` & `LICENSE` (`19.730` byte):** **`Creative Commons Attribution-NonCommercial 4.0 International` (`CC-BY-NC-4.0`)** — nghiêm cấm sử dụng, sao chép hoặc phân phối cho mục đích thu lợi thương mại hay nhận thù lao tài chính. Cả `diffq==0.2.4` (Linux/macOS) lẫn `diffq-fixed==0.2.4` (Windows) đều mang cùng giấy phép `CC-BY-NC-4.0` này.

### 5.2 Kiểm chứng thực thi & mã nguồn: `vi-dubber` có thực sự dùng `diffq` không?

**Câu trả lời xác minh bằng bằng chứng chạy thật: KHÔNG.**

1. **Cấu hình mặc định của `vi-dubber` không dùng Demucs:**
   - `projects/vi-dubber/config.yaml:L12`: `separation.model: model_bs_roformer_ep_317_sdr_12.9755.ckpt` (thuộc kiến trúc **`MDXC / BS-RoFormer`**, không phải `Demucs`).
   - `projects/vi-dubber/src/vi_dubber/separation.py:L245`: Chỉ tương tác với `audio_separator.separator.architectures.mdxc_separator`. Không có bất kỳ dòng nào trong toàn bộ `projects/vi-dubber/src/` nhắc tới `diffq` hay `demucs`.
2. **Thử nghiệm nạp thực tế trong `projects/vi-dubber/.venv`:**
   - Khi chạy `from audio_separator.separator import Separator`, tập mô-đun liên quan được nạp vào `sys.modules` là **`[]` (rỗng — `0` mô-đun `diffq`, `0` mô-đun `demucs`)**.
3. **Vị trí duy nhất gọi `diffq` trong toàn bộ `169` gói của `vi-dubber/.venv`:**
   - `audio_separator/separator/separator.py:L977,L996` nạp kiến trúc theo cơ chế **nạp lười (lazy dynamic import)** bằng `importlib.import_module(...)` tùy theo loại mô hình (`MDX`, `VR`, `Demucs`, `MDXC`).
   - Chỉ duy nhất nhánh `DemucsSeparator` (`architectures/demucs_separator.py:L7-L9`) mới kéo vào `uvr_lib_v5/demucs/{pretrained.py:L17, states.py:L18, utils.py:L26}`, và chỉ 3 tệp đó mới có dòng `from diffq import DiffQuantizer / UniformQuantizer / restore_quantized_state` để giải nén các checkpoint Demucs lượng tử hóa kiểu cũ.

### 5.3 Rủi ro pháp lý thực tế & Hướng dẫn gỡ rào cản trước khi thương mại hóa cho chủ sở hữu

- **Giai đoạn hiện tại (dùng cá nhân nội bộ, chưa bán phần mềm hay dịch vụ):** Chưa phát sinh phân phối thương mại.
- **Rào cản bắt buộc trước khi thương mại hóa (bán app desktop, bán gói cài đặt, hoặc mở API/SaaS lồng tiếng thu phí):** Vì `audio-separator==0.47.0` khai báo `diffq-fixed`/`diffq` là phụ thuộc bắt buộc trong metadata PyPI, `uv sync` luôn cài sẵn gói `CC-BY-NC-4.0` này vào `.venv` và ghi chặt vào `uv.lock` (dòng `161, 202–203, 487–508`). Việc đóng gói `.venv`/container hoặc vận hành hệ thống thương mại khi vẫn chứa gói `CC-BY-NC-4.0` trong môi trường chạy là **rủi ro vi phạm giấy phép trực tiếp (Blocker P0)**.

**3 phương án gỡ triệt để (xếp theo độ nhanh và độ sạch):**

1. **Phương án A — Nhanh nhất (1–2 ngày kỹ thuật, giữ nguyên chất lượng BS-RoFormer 100%):**
   - Trong bản phát hành thương mại của `vi-dubber`, loại bỏ `diffq` và `diffq-fixed` khỏi cây phụ thuộc bằng một trong hai cách sạch: (i) dùng fork nội bộ gọn của `audio-separator` (vốn mang giấy phép MIT) bỏ `diffq`/`diffq-fixed` khỏi `pyproject.toml`, xóa hoặc rào `try/except ImportError` cho nhánh `demucs`, hoặc (ii) khóa danh sách mô hình hợp lệ trong `vi_dubber/separation.py` chỉ cho phép `MDXC/RoFormer` (từ chối tuyệt đối tên mô hình `Demucs`) kết hợp override/loại trừ `diffq` & `diffq-fixed` khi đóng gói.
   - Bổ sung 1 bài kiểm tra tự động trong CI (`pytest`) khẳng định `importlib.util.find_spec("diffq") is None` và `uv.lock` thương mại không chứa `diffq` / `diffq-fixed`.
2. **Phương án B — Sạch bền vững nhất (3–5 ngày kỹ thuật, cắt luôn gánh nặng phụ thuộc thừa):**
   - Thay hoàn toàn `audio-separator` bằng một mô-đun tách lời thoại nội bộ (~150–200 dòng Python, giấy phép hoàn toàn sạch MIT/Apache-2.0) chạy thẳng trọng số `BS-RoFormer` bằng `torch` hoặc `onnxruntime` (có sẵn trong `.venv`).
   - Lợi ích kép: vừa xóa vĩnh viễn `diffq-fixed` (`CC-BY-NC-4.0`), vừa cắt gọn hàng chục gói phụ thuộc bắc cầu nặng nề của `audio-separator`, giảm dung lượng đóng gói và giảm bề mặt rủi ro chuỗi cung ứng.
3. **Phương án C — Chỉ xét nếu tương lai thực sự cần chạy mô hình Demucs thương mại:**
   - Tuyệt đối không dùng checkpoint nén bằng `diffq`. Dùng phiên bản HTDemucs không lượng tử hóa (giấy phép MIT từ Meta Research) với trình nạp thuần PyTorch không phụ thuộc `diffq`.
- **Kiểm tra đi kèm bắt buộc trước ngày ra mắt thương mại `vi-dubber`:** Xác minh thêm giấy phép từng tệp trọng số mô hình AI đang tải về (`model_bs_roformer_ep_317_sdr_12.9755.ckpt`, `whisper large-v3`, `vieneu`) và chọn bản dựng **FFmpeg LGPL** (không bật cờ `--enable-gpl` / `libx264` nếu đóng gói kèm app thương mại mà không muốn phát sinh nghĩa vụ GPL).

---

## 6. Bảng Hành Động Tuân Thủ Khả Thi

| Ưu tiên | Hạng mục tuân thủ | Kho áp dụng | Hành động cụ thể | Tiêu chí hoàn thành |
|---|---|---|---|---|
| **🔴 P0 (Trước thương mại hóa)** | Loại bỏ hoàn toàn `diffq-fixed` / `diffq` (`CC-BY-NC-4.0`) | `projects/vi-dubber` | Áp dụng Phương án A hoặc B ở Mục 5.3; khóa cấm nạp `Demucs` trong chế độ thương mại; thêm test CI cấm `diffq*` | `0` gói `diffq*` trong `uv.lock` thương mại và `.venv`; test tách lời thoại `BS-RoFormer` chạy đạt 100% |
| **🔴 P0 (Trước thương mại hóa)** | Kiểm toán trọng số AI & bản build FFmpeg | `projects/vi-dubber` | Ghi rõ giấy phép từng tệp model (`BS-RoFormer`, `Whisper`, `VieNeu`) và chọn bản FFmpeg LGPL (hoặc yêu cầu người dùng tự cài FFmpeg riêng) | Có bảng xác nhận quyền thương mại cho 100% tệp trọng số & tệp thực thi đính kèm |
| **🟡 P1 (Đợt dọn tài liệu kế)** | Đồng bộ `THIRD_PARTY_NOTICES.md` trên 3 kho | Gốc, `projects/trader`, `projects/vi-dubber` | Thêm `hermes-agent` (MIT) vào tệp gốc; thêm `psycopg`, `psycopg-binary`, `psycopg-pool` (LGPL-3.0) và `portion` (LGPL-3.0) vào `trader`; thêm `soxr` (LGPL-2.1), `orjson` (MPL-2.0/MIT/Apache), `tqdm`, `certifi` và lưu ý `text-unidecode` (chọn nhánh Artistic) vào `vi-dubber` | Toàn bộ gói Tầng 2 (LGPL/MPL) và 4/4 tích hợp đều có mục thông báo tương ứng |
| **🟡 P1 (Vệ sinh Gitleaks)** | Thêm dấu vân tay dương tính giả duy nhất cho `private_vault` | `private_vault` | Thêm `.gitleaksignore` chứa đúng 1 dấu vân tay dòng `live_liquidity_audit_20261125.json:L8` đã xác minh | `gitleaks git` trên `private_vault` trả về `0 leaks` (`exit 0`) |
| **🟢 P2 (Bảo trì định kỳ)** | Vệ sinh `education/.venv-mt5` & kiểm đủ 19 crate Rust đa nền tảng | Gốc, `projects/trader` | Xóa hoặc chuyển `education/.venv-mt5` ra `.runtime/` nếu không còn dùng; chạy `cargo deny check licenses` hoặc tải cache đủ 19 crate `wasm-*`/`windows-*` trước khi xuất bản nhị phân `api-rust` | `0` cảnh báo rác từ `.venv` chưa track; `297/297` crate Rust được xác nhận giấy phép |

---

## 7. Hồ Sơ Tái Lập & Toàn Vẹn Kiểm Chứng

- **Lệnh xác minh trụ cột:** `node tooling/ui-qa/ui-registry-check.mjs --json`, `node --test tooling/ui-qa/tests/registered-products.test.mjs`, `.runtime\quant-audit-v24\Scripts\python.exe education/check_setup.py`, `node tooling/integrations/doctor.mjs`, `.runtime\quant-audit-v24\Scripts\python.exe tooling/check_workspace.py`.
- **Lệnh quét bí mật:** `.runtime\tools\gitleaks\gitleaks.exe git --redact --no-banner --verbose --log-opts <HEAD|codex/agent-first-hygiene>` trên cả 5 kho Git + `detect --no-git --redact` trên cây tệp tracked và `private_vault`.
- **Biên nhận cấu trúc JSON:** `.tmp/swarm_dropbox/l10-ecosystem.json` (chứa đủ mã băm SHA-256 kiểm chứng 5 tệp WIP của `projects/vi-dubber`, thống kê gói từng `.venv`, và mã băm SHA-256 của báo cáo này).
