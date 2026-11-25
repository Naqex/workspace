# Pass 15 · Engine #2 đo ni đóng giày cho FTMO (`XAUUSD` Intraday `swap = 0` & FX Positive-Carry Trend)

- **Protocol khóa trước thực nghiệm:** [PASS15-FTMO-NATIVE-ENGINE2-PROTOCOL-20261123.md](PASS15-FTMO-NATIVE-ENGINE2-PROTOCOL-20261123.md) (commit `b2e5803`)
- **Dữ liệu & tốc độ:** Hot M1 Parquet Cache SSD (`2018–2024`, `holdout_rows = 0`, `network_calls = 0`, `OrderSend = 0`), chạy xong trong **`14.61s`**, `quant_test_suite` **`1518/1518 PASS (0 skip, 17.96s)`**.
- **Phán quyết tổng hợp:** **`PASS15_ALL_SEVEN_HYPOTHESES_REJECTED_ENGINE1_NEEDS_PARTNER`** (`tier_counts = {'TIER_3_DEAD_NO_EDGE': 7}`).

---

## Kết quả 7 giả thuyết đăng ký trước (M1 thực 2018–2024 · BH FDR `m = 7`)

| Giả thuyết | Mã | `n` | FTMO Stress R (Cụm A / B · Năm+ · DD · Top10) | Swap FTMO | Fade / ExSF | MC Null (`p_g / p_f`) · FDR (`q_f`) | Phân tầng |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| **`XAU_DAILY_OPEN_ATR`** | `XAUUSD` | `1235` | **`-38.20R`** (`-32.6 / -5.6` · `2/7` · DD `56.9R` · Top10 `26.7R`) | `$+0` | Fade `-182.6R` | `0.004 / 0.004` · `q=0.028` | `TIER_3_DEAD_NO_EDGE` |
| **`XAU_LONDON_NY_MOMENTUM`** | `XAUUSD` | `241` | **`-19.54R`** (`-3.6 / -15.9` · `2/7` · DD `21.0R` · Top10 `20.5R`) | `$+0` | Fade `-16.2R` | `0.329 / 0.329` · `q=0.573` | `TIER_3_DEAD_NO_EDGE` |
| **`XAU_H1_DONCHIAN_INTRADAY`** | `XAUUSD` | `1307` | **`-148.48R`** (`-47.1 / -101.4` · `1/7` · DD `160.2R` · Top10 `63.4R`) | `$+0` | Fade `-227.5R` | `0.016 / 0.016` · `q=0.056` | `TIER_3_DEAD_NO_EDGE` |
| **`XAU_ASIA_SQUEEZE_BREAK`** | `XAUUSD` | `650` | **`-92.54R`** (`-41.6 / -51.0` · `1/7` · DD `112.1R` · Top10 `56.5R`) | `$+0` | Fade `-173.7R` | `0.276 / 0.276` · `q=0.573` | `TIER_3_DEAD_NO_EDGE` |
| **`CARRY_USDJPY_LONG_DONCHIAN20`** | `USDJPY` | `43` | **`+11.28R`** (`-5.2 / +16.4` · `4/7` · DD `6.7R` · Top10 `23.4R`) | `$+1,677` | ExSF `+10.2R` | `0.374 / 0.410` · `q=0.573` | `TIER_3_DEAD_NO_EDGE` |
| **`CARRY_USDJPY_LONG_PULLBACK_H4`** | `USDJPY` | `185` | **`+12.18R`** (`-1.0 / +13.2` · `4/7` · DD `10.2R` · Top10 `24.2R`) | `$+1,826` | ExSF `+10.2R` | `0.698 / 0.699` · `q=0.810` | `TIER_3_DEAD_NO_EDGE` |
| **`CARRY_EURUSD_SHORT_DONCHIAN20`** | `EURUSD` | `38` | **`-0.30R`** (`-5.1 / +4.8` · `4/7` · DD `7.9R` · Top10 `13.8R`) | `$+206` | ExSF `-0.3R` | `0.807 / 0.810` · `q=0.810` | `TIER_3_DEAD_NO_EDGE` |


