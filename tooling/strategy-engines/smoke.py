"""Run real framework order/accounting smoke tests on a synthetic M15 fixture.

Run each backend with its own locked interpreter. This is installation evidence,
not US500 execution parity, economic research, or a broker connection.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time


def fixture():
    import pandas as pd

    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    return pd.DataFrame(
        {"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": 1000},
        index=pd.date_range("2022-01-03 09:30", periods=6, freq="15min"),
    )


def backtesting_smoke(data):
    from backtesting import Backtest, Strategy

    class RoundTrip(Strategy):
        def init(self):
            pass

        def next(self):
            if len(self.data) == 2:
                self.buy(size=2)
            elif len(self.data) == 4:
                self.position.close()

    result = Backtest(data, RoundTrip, cash=10000, spread=0, commission=(0.5, 0),
                      trade_on_close=False).run()
    trades = result["_trades"]
    assert len(trades) == 1
    row = trades.iloc[0]
    assert (int(row["EntryBar"]), int(row["ExitBar"])) == (2, 4)
    assert (float(row["EntryPrice"]), float(row["ExitPrice"])) == (102, 104)
    assert float(row["Commission"]) == 1
    return float(result["Equity Final [$]"])


def backtrader_smoke(data):
    import backtrader as bt

    class RoundTrip(bt.Strategy):
        def __init__(self):
            self.fills = []

        def next(self):
            if len(self) == 2:
                self.buy(size=2)
            elif len(self) == 4:
                self.close()

        def notify_order(self, order):
            if order.status == order.Completed:
                self.fills.append((order.executed.price, order.executed.comm))

    engine = bt.Cerebro()
    engine.adddata(bt.feeds.PandasData(dataname=data))
    engine.addstrategy(RoundTrip)
    engine.broker.setcash(10000)
    engine.broker.setcommission(commission=0.25, commtype=bt.CommInfoBase.COMM_FIXED,
                                stocklike=True)
    (strategy,) = engine.run()
    assert strategy.fills == [(102.0, 0.5), (104.0, 0.5)]
    assert not strategy.position
    return float(engine.broker.getvalue())


def vectorbt_smoke(data):
    import vectorbt as vbt

    # Decisions after bars 1/3 are executed at opens 2/4, not on their signal close.
    orders = [0, 0, 2, 0, -2, 0]
    portfolio = vbt.Portfolio.from_orders(
        data["Close"], size=orders, price=data["Open"], init_cash=10000,
        fees=0, fixed_fees=0.5, freq="15min",
    )
    records = portfolio.orders.records
    assert len(records) == 2
    assert list(records["idx"]) == [2, 4]
    assert list(records["price"]) == [102.0, 104.0]
    assert list(records["fees"]) == [0.5, 0.5]
    assert float(portfolio.assets().iloc[-1]) == 0
    return float(portfolio.value().iloc[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("backtesting", "backtrader", "vectorbt"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("use a fresh receipt path; do not overwrite a previous attempt")
    began = time.perf_counter()
    data = fixture()
    end = globals()[args.engine + "_smoke"](data)
    assert abs(end - 10003) < 1e-8, (args.engine, end)
    receipt = dict(
        status="native_framework_synthetic_roundtrip_passed", engine=args.engine,
        version=importlib.metadata.version(args.engine), python=sys.version,
        fixture="synthetic_M15_six_flat_OHLC_bars_not_market_data",
        fixture_sha256=hashlib.sha256(data.to_csv().encode()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        lock_sha256=hashlib.sha256((Path(__file__).parent/args.engine/"uv.lock").read_bytes()).hexdigest(),
        starting_cash=10000, ending_cash=end, quantity=2,
        entry=102, exit=104, roundtrip_fee=1, net=3,
        wall_seconds=time.perf_counter()-began,
        target_us500_parity=False, strategy_qualified=False, broker_calls=0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
