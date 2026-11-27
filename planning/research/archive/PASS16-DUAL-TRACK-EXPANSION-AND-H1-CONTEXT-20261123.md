# Pass 16 · Động lượng mở rộng tần suất thấp (`swap = 0`) & 8 mã `H1` còn lại của `strategy-intel`

- **Protocol khóa trước thực nghiệm:** [PASS16-DUAL-TRACK-EXPANSION-AND-H1-CONTEXT-PROTOCOL-20261123.md](PASS16-DUAL-TRACK-EXPANSION-AND-H1-CONTEXT-PROTOCOL-20261123.md) (commit `8e590ca`)
- **Dữ liệu & tốc độ:** Hot M1 Cache SSD (`2018–2024`, `holdout_rows = 0`, `network_calls = 0`, `OrderSend = 0`), Nhánh 1 `28.72s` · Nhánh 2 `14.11s`, `quant_test_suite` **`1519/1519 PASS (0 skip, 20.56s)`**.
- **Phán quyết tổng hợp:** **`PASS16_FOUND_2_TIER1_AND_3_TIER2`** (Nhánh 1: `{'TIER_3_DEAD_NO_EDGE': 8, 'TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU': 1, 'TIER_1_FTMO_READY': 2, 'TIER_2_PERSONAL_VAULT': 1}` · Nhánh 2: `{'TIER_3_DEAD_NO_EDGE': 23, 'TIER_2_PERSONAL_VAULT': 1}`).

---

## 1. Nhánh 1 · Động lượng mở rộng biên độ lớn (`swap = 0`, `m = 12` cặp, BH FDR)

| Chiến lược | Mã | `n` | FTMO Stress R (Cụm A / B · Năm+ · DD) | Fade R | MC Null (`p_g / p_f`) · FDR (`q_f`) | Phân tầng |
| --- | --- | ---: | --- | ---: | --- | --- |
| **`EXP_DAILY_OPEN_080`** | `XAUUSD` | `600` | **`+0.03R`** (`-3.2 / +3.3` · `4/7` · DD `13.1R`) | `-124.4R` | `0.001 / 0.001` · `q=0.004` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_100`** | `XAUUSD` | `360` | **`+9.27R`** (`-0.4 / +9.7` · `3/7` · DD `7.2R`) | `-81.9R` | `0.001 / 0.001` · `q=0.004` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_120`** | `XAUUSD` | `204` | **`+10.43R`** (`+4.2 / +6.2` · `5/7` · DD `4.6R`) | `-53.8R` | `0.001 / 0.001` · `q=0.004` | `TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU` |
| **`EXP_DAILY_OPEN_080_TREND`** | `XAUUSD` | `296` | **`-4.84R`** (`-7.9 / +3.0` · `3/7` · DD `11.5R`) | `-63.9R` | `0.065 / 0.065` · `q=0.097` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_080`** | `USDJPY` | `569` | **`+35.24R`** (`+22.2 / +13.1` · `7/7` · DD `6.4R`) | `-113.7R` | `0.002 / 0.002` · `q=0.005` | `TIER_1_FTMO_READY` |
| **`EXP_DAILY_OPEN_100`** | `USDJPY` | `344` | **`+21.81R`** (`+15.5 / +6.3` · `6/7` · DD `5.6R`) | `-63.8R` | `0.013 / 0.013` · `q=0.026` | `TIER_2_PERSONAL_VAULT` |
| **`EXP_DAILY_OPEN_120`** | `USDJPY` | `213` | **`+11.81R`** (`+12.3 / -0.5` · `4/7` · DD `9.0R`) | `-48.1R` | `0.021 / 0.021` · `q=0.036` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_080_TREND`** | `USDJPY` | `276` | **`+24.74R`** (`+8.8 / +15.9` · `6/7` · DD `6.8R`) | `-53.6R` | `0.002 / 0.002` · `q=0.005` | `TIER_1_FTMO_READY` |
| **`EXP_DAILY_OPEN_080`** | `EURUSD` | `595` | **`-19.15R`** (`-5.9 / -13.2` · `2/7` · DD `24.0R`) | `-72.6R` | `0.733 / 0.733` · `q=0.880` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_100`** | `EURUSD` | `320` | **`-19.63R`** (`-10.7 / -9.0` · `1/7` · DD `19.6R`) | `-42.7R` | `0.906 / 0.906` · `q=0.921` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_120`** | `EURUSD` | `173` | **`-11.42R`** (`-9.5 / -2.0` · `2/7` · DD `11.4R`) | `-20.8R` | `0.921 / 0.921` · `q=0.921` | `TIER_3_DEAD_NO_EDGE` |
| **`EXP_DAILY_OPEN_080_TREND`** | `EURUSD` | `300` | **`-9.92R`** (`-4.1 / -5.8` · `3/7` · DD `14.3R`) | `-35.7R` | `0.604 / 0.604` · `q=0.806` | `TIER_3_DEAD_NO_EDGE` |

---

## 2. Nhánh 2 · 8 chiến lược `H1` nội phiên còn lại của ô `39 TÌNH HUỐNG` (`swap = 0`, `m = 24` cặp, BH FDR)

| Chiến lược | Mã | `n` | FTMO Stress R (Cụm A / B · Năm+ · DD) | MC Null (`p_g / p_f`) · FDR (`q_f`) | Phân tầng |
| --- | --- | ---: | --- | --- | --- |
| **`BRK011`** | `XAUUSD` | `1159` | **`-130.27R`** (`-70.5 / -59.8` · `0/7` · DD `141.4R`) | `0.022 / 0.022` · `q=0.115` | `TIER_3_DEAD_NO_EDGE` |
| **`BRK037`** | `XAUUSD` | `1019` | **`-81.20R`** (`-20.4 / -60.8` · `1/7` · DD `90.7R`) | `0.004 / 0.004` · `q=0.048` | `TIER_3_DEAD_NO_EDGE` |
| **`IND017`** | `XAUUSD` | `1601` | **`-139.88R`** (`-83.0 / -56.8` · `0/7` · DD `159.7R`) | `0.002 / 0.002` · `q=0.048` | `TIER_3_DEAD_NO_EDGE` |
| **`IND027`** | `XAUUSD` | `836` | **`-96.24R`** (`-52.5 / -43.8` · `2/7` · DD `96.3R`) | `0.067 / 0.067` · `q=0.178` | `TIER_3_DEAD_NO_EDGE` |
| **`MTF005`** | `XAUUSD` | `409` | **`-57.77R`** (`-41.6 / -16.2` · `1/7` · DD `71.7R`) | `0.182 / 0.182` · `q=0.384` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN024`** | `XAUUSD` | `10` | **`+1.48R`** (`-0.1 / +1.6` · `4/7` · DD `0.2R`) | `0.084 / 0.084` · `q=0.201` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN029`** | `XAUUSD` | `59` | **`-12.95R`** (`-2.7 / -10.3` · `1/7` · DD `20.9R`) | `0.955 / 0.955` · `q=0.986` | `TIER_3_DEAD_NO_EDGE` |
| **`VIR024`** | `XAUUSD` | `93` | **`-3.82R`** (`-1.1 / -2.8` · `2/7` · DD `12.8R`) | `0.234 / 0.234` · `q=0.432` | `TIER_3_DEAD_NO_EDGE` |
| **`BRK011`** | `USDJPY` | `1152` | **`-8.83R`** (`+1.8 / -10.6` · `3/7` · DD `41.8R`) | `0.040 / 0.040` · `q=0.137` | `TIER_3_DEAD_NO_EDGE` |
| **`BRK037`** | `USDJPY` | `1063` | **`+33.82R`** (`-17.0 / +50.8` · `3/7` · DD `36.8R`) | `0.006 / 0.006` · `q=0.048` | `TIER_3_DEAD_NO_EDGE` |
| **`IND017`** | `USDJPY` | `1519` | **`-38.61R`** (`-80.3 / +41.7` · `2/7` · DD `94.1R`) | `0.025 / 0.024` · `q=0.115` | `TIER_3_DEAD_NO_EDGE` |
| **`IND027`** | `USDJPY` | `802` | **`+12.62R`** (`-24.9 / +37.5` · `3/7` · DD `39.4R`) | `0.035 / 0.035` · `q=0.137` | `TIER_3_DEAD_NO_EDGE` |
| **`MTF005`** | `USDJPY` | `396` | **`-36.35R`** (`-25.2 / -11.1` · `2/7` · DD `39.5R`) | `0.442 / 0.442` · `q=0.623` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN024`** | `USDJPY` | `6` | **`-0.47R`** (`-0.1 / -0.4` · `2/7` · DD `1.0R`) | `0.821 / 0.818` · `q=0.893` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN029`** | `USDJPY` | `119` | **`-1.74R`** (`-0.0 / -1.7` · `2/7` · DD `10.9R`) | `0.338 / 0.339` · `q=0.542` | `TIER_3_DEAD_NO_EDGE` |
| **`VIR024`** | `USDJPY` | `65` | **`+16.27R`** (`+11.3 / +4.9` · `4/7` · DD `6.1R`) | `0.050 / 0.049` · `q=0.147` | `TIER_2_PERSONAL_VAULT` |
| **`BRK011`** | `EURUSD` | `1190` | **`-115.29R`** (`-52.3 / -63.0` · `1/7` · DD `119.0R`) | `0.519 / 0.519` · `q=0.693` | `TIER_3_DEAD_NO_EDGE` |
| **`BRK037`** | `EURUSD` | `1190` | **`-120.99R`** (`-69.8 / -51.2` · `0/7` · DD `133.6R`) | `0.814 / 0.814` · `q=0.893` | `TIER_3_DEAD_NO_EDGE` |
| **`IND017`** | `EURUSD` | `1717` | **`-188.44R`** (`-109.2 / -79.2` · `0/7` · DD `198.5R`) | `0.677 / 0.677` · `q=0.813` | `TIER_3_DEAD_NO_EDGE` |
| **`IND027`** | `EURUSD` | `899` | **`-72.86R`** (`-47.9 / -25.0` · `1/7` · DD `86.3R`) | `0.561 / 0.561` · `q=0.709` | `TIER_3_DEAD_NO_EDGE` |
| **`MTF005`** | `EURUSD` | `448` | **`-19.58R`** (`-16.4 / -3.2` · `3/7` · DD `46.2R`) | `0.192 / 0.192` · `q=0.384` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN024`** | `EURUSD` | `9` | **`-3.46R`** (`-1.2 / -2.3` · `1/7` · DD `3.5R`) | `0.986 / 0.986` · `q=0.986` | `TIER_3_DEAD_NO_EDGE` |
| **`NEN029`** | `EURUSD` | `63` | **`-4.68R`** (`-5.8 / +1.1` · `2/7` · DD `9.8R`) | `0.268 / 0.268` · `q=0.459` | `TIER_3_DEAD_NO_EDGE` |
| **`VIR024`** | `EURUSD` | `116` | **`-2.75R`** (`-5.1 / +2.3` · `4/7` · DD `9.3R`) | `0.413 / 0.413` · `q=0.619` | `TIER_3_DEAD_NO_EDGE` |
