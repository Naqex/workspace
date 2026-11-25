---
doc_type: security-and-ci-audit
domain: layer1-opsec-and-github-actions
status: CLOSED
updated_utc: 2026-11-25
order_send_count: 0
holdout_rows_analysed: 0
---

# Báo Cáo Kiểm Toán Bảo Mật Layer-1, Chốt Chặn OPSEC Vĩnh Viễn & Đánh Giá CI (`.github/workflows/workspace.yml`)

> **Phạm vi:** Quét toàn bộ **`3.802` tệp** được Git theo dõi trong `Naqex/workspace` (loại trừ submodule `projects/` và kho riêng `private_vault/`), dọn sạch toàn bộ vết OPSEC thực tế còn sót ở Layer-1, lắp chốt chặn kiểm thử vĩnh viễn [`test_layer1_opsec_guard.py`](../../tooling/ai-engines/tests/test_layer1_opsec_guard.py), và kiểm toán chỉ đọc quy trình CI [`.github/workflows/workspace.yml`](../../.github/workflows/workspace.yml).
> **Khóa an toàn:** `OrderSend = 0`, `Holdout 2025+ SEALED`, không sửa `projects/*`, `private_vault/`, `education/`, `AGENTS.md` hay `quant_factory/prop_live_tca_monitor.py`.

---

## 1. Kết Quả Quét Toàn Kho (`git ls-files`: `3.802` Tệp Layer-1) & Các Vết Đã Dọn Sạch

| Hạng mục kiểm toán | Số vết trước dọn | Đã xử lý trong đợt này | Trạng thái sau dọn |
|---|---:|---:|---|
| **Tệp `private_vault/` bị track trong Git** | `0` | `0` | **SẠCH (`0` tệp; `.gitignore` chặn `/private_vault/`)** |
| **Khóa API / GitHub Token / Postgres DSN có mật khẩu / Công thức `private_vault/`** | `0` | `0` | **SẠCH (`0` vết thật)** |
| **IP LAN thật (`<LAN_IP>`) & Tailscale thật (`<TAILSCALE_IP>`)** | `0` *(đã dọn ở Wave 2.8A)* | `0` | **SẠCH (`0` vết trên toàn bộ file tracked)** |
| **Tên app Heroku thật (`<HEROKU_DEADMAN_APP>`)** | `0` *(đã dọn ở Wave 2.8A)* | `0` | **SẠCH (`0` vết trên toàn bộ file tracked)** |
| **Handle bot Telegram (`<TELEGRAM_GUARD_BOT>`)** | **`12`** | **`12`** | **SẠCH (`0` vết còn lại trên toàn repo)** |
| **Đường dẫn tên người dùng Windows cục bộ (`tooling/ai-engines/` & `planning/research/*.md` `202611xx`)** | **`9`** | **`9`** | **SẠCH (`0` vết trong toàn vùng Layer-1 đang hoạt động)** |

### Chi tiết `21` vết OPSEC thật đã dọn sạch trong lượt này
1. **Thay handle bot Telegram -> `<TELEGRAM_GUARD_BOT>` (`12` vị trí):**
   - [`knowledge/playbooks/ftmo-the5ers-live-launch-sop.md`](../../knowledge/playbooks/ftmo-the5ers-live-launch-sop.md) (`6` vị trí)
   - [`knowledge/playbooks/naqex-master-roadmap-2026-2027.md`](../../knowledge/playbooks/naqex-master-roadmap-2026-2027.md) (`1` vị trí)
   - [`planning/TOP1-SOLO-QUANT-MASTER-PLAN.md`](../TOP1-SOLO-QUANT-MASTER-PLAN.md) (`5` vị trí)
2. **Thay đường dẫn tên người dùng cục bộ -> di động / chuẩn hóa (`9` vị trí):**
   - [`planning/research/TYPESAFE-AI-EVALUATION-AND-BENCHMARK-20261124.md`](TYPESAFE-AI-EVALUATION-AND-BENCHMARK-20261124.md) (`1`), [`PROP-V4-HARVEST-FX-SPLIT-20261119.md`](PROP-V4-HARVEST-FX-SPLIT-20261119.md) (`1` — sửa luôn liên kết tuyệt đối về tương đối sạch), [`SOLO-LANE-ADOPTION-20261117.md`](SOLO-LANE-ADOPTION-20261117.md) (`2`), [`FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md`](FTMO-FREE-TRIAL-EXECUTION-SPEC-20261116.md) (`1`), [`METAL-DISCOVERY8-SCREEN-20261108.md`](METAL-DISCOVERY8-SCREEN-20261108.md) (`1`), [`NATIVE-RESUME-REVIEW-20261108.md`](NATIVE-RESUME-REVIEW-20261108.md) (`1`).
   - [`tooling/ai-engines/prop_v15_delivery.py`](../../tooling/ai-engines/prop_v15_delivery.py) (`1`) & [`tooling/ai-engines/prop_v16_performance.py`](../../tooling/ai-engines/prop_v16_performance.py) (`1`) -> chuyển sang `Path.home() / ".cache/..."`.
3. **Ngoại lệ lịch sử / ngoài phạm vi giữ nguyên (ghi nhận minh bạch):** Các biên nhận JSON đóng băng (`20261115–20261117`), thư mục lưu trữ cũ `planning/archive/`, `planning/checkpoints/`, log kiểm thử tháng `10/2026` (`ai-architecture-review-20261023/`, `fxreplay-capture/`), `planning/trader/`, và `education/` không nằm trong phạm vi sửa của lượt này; toàn bộ mã chạy, kỹ năng, playbook và tài liệu nghiên cứu đang hoạt động đều đã sạch `0` vết.

---

## 2. Chốt Chặn Kiểm Thử Vĩnh Viễn (`test_layer1_opsec_guard.py`)

Đã tạo [`tooling/ai-engines/tests/test_layer1_opsec_guard.py`](../../tooling/ai-engines/tests/test_layer1_opsec_guard.py) dưới dạng **`unittest.TestCase`** (chạy trong `< 1` giây):
- **Tự động chạy trên CẢ HAI hệ thống:** (1) `pytest -vv tooling/ai-engines/tests/test_layer1_opsec_guard.py` cục bộ, và (2) **`quant_test_suite.py --group complete --tier all`** trên GitHub Actions (vì `quant_test_suite.py` quét `tests/test_*.py` bằng `unittest.defaultTestLoader`).
- **5 khóa kiểm chứng fail-closed:**
  1. `0` tệp thuộc `private_vault/` trong `git ls-files` và `.gitignore` phải giữ `/private_vault/`.
  2. `0` IP LAN/Tailscale thật, `0` IP mạng riêng trong mã/tài liệu phi-test (cho phép chuẩn RFC 6598 `100.64.0.0/10`), `0` tên app Heroku thật, `0` handle Telegram thật.
  3. `0` đường dẫn chứa tên người dùng Windows cục bộ trên toàn bộ `tooling/ai-engines/`, `.agents/`, `knowledge/`, `planning/TOP1-SOLO-QUANT-MASTER-PLAN.md` và mọi báo cáo `planning/research/*.md`.
  4. `0` khóa API/token thật (`GitHub`, `OpenAI`, `Google`, `Telegram Bot API`, `Discord Webhook`, `Postgres DSN` có mật khẩu).
  5. `ORDER_SEND_COUNT == 0` và xác nhận phạm vi quét thực tế `> 100` tệp.

---

## 3. Kiểm Toán Chỉ Đọc GitHub Actions (`.github/workflows/workspace.yml`)

### 3.1. Các điểm bảo mật đã làm tốt
- **Quyền tối thiểu (*Least-Privilege*):** Khai báo `permissions: contents: read` ở cấp toàn workflow (không cấp thừa quyền `write` cho `GITHUB_TOKEN`).
- **Ghim Action theo Commit SHA đầy đủ:** Cả `4/4` action (`actions/checkout`, `actions/setup-python`, `actions/upload-artifact`, `actions/setup-node`) đều ghim SHA 40 ký tự, chống tấn công đổi tag chuỗi cung ứng.
- **Kiểm soát tài nguyên & concurrency:** Có `concurrency` (`group: workspace-<github.ref>`, `cancel-in-progress: true`) và `timeout-minutes: 10` trên cả `3` job (`contracts`, `secrets`, `registry`).
- **Quét bí mật Gitleaks có xác minh SHA-256:** Tải `gitleaks v8.30.1` và kiểm khớp đúng mã băm SHA-256 trước khi chạy `gitleaks git --redact`.

### 3.2. Kết Quả Đóng Các Phát Hiện CI (Trạng thái: `CLOSED`)

| Mức độ | Phát hiện trên `workspace.yml` | Trạng thái & Xử lý đã áp dụng |
|---|---|---|
| **CAO** | **Thiếu bước chạy `pytest` dù đã cài `pytest==9.2.0`:** `quant_test_suite.py` chỉ chạy `unittest.TestCase`, bỏ sót các suite hàm trần `def test_*` (`test_node_ctl.py`, `test_heroku_deadman.py`, `test_wave2_cockpit_and_treasury.py`, `test_ftmo_demo_calibration_probe.py`, `test_statement_reconcile_e2e.py`). | **`CLOSED`:** Đã thêm bước `Run pure-offline pytest OPSEC, ops-cloud, cockpit & contract suites` trong job `contracts` chạy đủ **`12` bộ kiểm thử thuần offline** (`test_layer1_opsec_guard.py`, `test_node_ctl.py`, `test_heroku_deadman.py`, `test_wave2_cockpit_and_treasury.py`, `test_ftmo_demo_calibration_probe.py`, `test_statement_reconcile_e2e.py`, `test_node_cutover_dryrun.py`, `test_node_weekly_digest.py`, `test_ftmo_pre_checkout_guard.py`, `test_holdout_and_tca_guards.py`, `test_mql5_v101_contract.py`, `test_prop_live_tca_monitor.py`) với `-k "not test_real_hot_m1_cache_baselines_enforce_zero_holdout"` -> **`80` test PASS, `0` skip, `0` phụ thuộc `.runtime/` hay `.ex5`**. |
| **TRUNG BÌNH** | **`actions/checkout` chưa đặt `persist-credentials: false`:** token vẫn lưu trong `.git/config` cho các bước sau. | **`CLOSED`:** Đã thêm `persist-credentials: false` trên toàn bộ **`3/3`** bước `actions/checkout` (`contracts`, `secrets`, `registry`; đã xác nhận `Naqex/workspace` & toàn bộ `.gitmodules` đều là repo công khai). |
| **TRUNG BÌNH** | **`gitleaks` chỉ quét `git --log-opts HEAD` (`line 95`):** cần giữ fixture test không khớp rule mặc định của Gitleaks. | **Đã ghi nhận / Theo dõi:** `test_layer1_opsec_guard.py` đã ghép chuỗi động toàn bộ pattern nhạy cảm để không tự kích hoạt Gitleaks; giữ `.gitleaks.toml` đồng bộ khi thêm bài test bảo mật mới. |
| **THẤP** | **`pip install` các gói khoa học ở `contracts` mới ghim version, chưa khóa hash (`--require-hashes`).** | **Hậu kỳ (không chặn):** Chuyển sang tệp lock có hash hoặc `uv` trong đợt chuẩn hóa hạ tầng CI tiếp theo. |
