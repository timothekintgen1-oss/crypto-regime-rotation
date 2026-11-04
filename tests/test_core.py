"""Unit tests for the engine: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import backtest as bt  # noqa: E402
import data_sources as ds  # noqa: E402
import indicators as I  # noqa: E402
import strategy as st  # noqa: E402


def synthetic_ohlc(n=900, seed=0, start="2019-01-01"):
    """Random-walk daily candles."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="D")
    close = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
    df = pd.DataFrame({"close": close}, index=idx)
    df["open"] = df["close"].shift(1).fillna(df["close"])
    df["high"] = df[["open", "close"]].max(axis=1) * (1 + rng.uniform(0, 0.02, n))
    df["low"] = df[["open", "close"]].min(axis=1) * (1 - rng.uniform(0, 0.02, n))
    return df[["open", "high", "low", "close"]]


def change_future(df, cut, seed=1):
    """Same candles up to `cut`, different ones after it."""
    out = df.copy()
    rng = np.random.default_rng(seed)
    after = out.index > cut
    out.loc[after] = out.loc[after].to_numpy() * rng.uniform(0.5, 1.5, (after.sum(), 1))
    return out


class TestNoLookAhead(unittest.TestCase):
    """Changing future candles must not change any signal already computed."""

    def check_block(self, spec):
        df = synthetic_ohlc()
        cut = df.index[700]
        _, _, a = I.build_tpi(df, spec, entry=0.0, exit=0.0)
        _, _, b = I.build_tpi(change_future(df, cut), spec, entry=0.0, exit=0.0)
        for label in a.columns:
            with self.subTest(indicator=label):
                pd.testing.assert_series_equal(a[label].loc[:cut], b[label].loc[:cut])

    def test_regime_block(self):
        self.check_block(st.MTPI_SPEC)

    def test_rotation_block(self):
        self.check_block(st.ROT_SPEC)

    def test_alts_block(self):
        self.check_block(st.TRASH_SPEC)


class TestRegime(unittest.TestCase):
    def test_hysteresis(self):
        idx = pd.date_range("2024-01-01", periods=6, freq="D")
        df = pd.DataFrame({"sig": [1, 1, 0.05, -0.05, -1, 0.0]}, index=idx)
        I.INDICATORS["_test"] = lambda d: d["sig"].to_numpy()
        try:
            spec = [{"label": "t", "name": "_test", "tf": "1D", "params": {}}]
            _, regime, _ = I.build_tpi(df, spec, entry=0.1, exit=0.1)
        finally:
            del I.INDICATORS["_test"]
        # stays LONG between the thresholds, flips only below -0.1, then stays CASH
        self.assertEqual(regime.tolist(), [1, 1, 1, 1, -1, -1])

    def test_evaluate_output(self):
        res = st.evaluate(synthetic_ohlc(seed=2), synthetic_ohlc(seed=3), synthetic_ohlc(seed=4))
        self.assertIn(res["regime"], ("LONG", "CASH"))
        self.assertTrue(-1 <= res["mtpi"] <= 1)
        self.assertEqual(len(res["states"]), len(st.MTPI_SPEC))
        self.assertTrue(0 <= res["trash_pct"] <= st.TRASH_MAX)


class TestTradingViewDates(unittest.TestCase):
    def test_two_day_candles_are_labelled_at_close(self):
        opens = pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-05"])
        df = pd.DataFrame({"open": [1, 2, 3], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5],
                           "close": [1.5, 2.5, 3.5]}, index=opens)
        out = ds._label_at_close(df)
        self.assertEqual([d.strftime("%m-%d") for d in out.index], ["01-02", "01-04", "01-06"])

    def test_daily_candles_are_unchanged(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({"open": [1, 2, 3], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5],
                           "close": [1.5, 2.5, 3.5]}, index=idx)
        self.assertTrue(ds._label_at_close(df).index.equals(idx))


class TestMetrics(unittest.TestCase):
    def test_drawdown_and_performance(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        r = pd.Series([0.0, 0.10, -0.50, 0.20, 0.0], index=idx)    # 1 -> 1.1 -> 0.55 -> 0.66
        m = bt._metrics(r)
        self.assertEqual(m["dd"], -50.0)
        self.assertEqual(m["perf"], -34.0)


if __name__ == "__main__":
    unittest.main()
