import unittest
from datetime import datetime
from types import SimpleNamespace

from src.live_monitor import LiveMonitor


class LiveMonitorTests(unittest.TestCase):
    def test_trade_side_uses_latest_quote(self):
        monitor = LiveMonitor()
        monitor.record_trade({
            "price": 100,
            "size": 1,
            "timestamp": "2026-01-15T15:00:00Z",
        })
        monitor.record_quote({
            "bid_price": 99,
            "bid_size": 10,
            "ask_price": 101,
            "ask_size": 12,
        })
        monitor.record_trade({"price": 101, "size": 1})
        monitor.record_trade({"price": 99, "size": 1})
        monitor.record_trade({"price": 100, "size": 1})

        trades = monitor.snapshot()["trades"]
        self.assertEqual(
            [trade["side"] for trade in trades],
            [
                "MID-SPREAD / UNCERTAIN",
                "SELL-INITIATED (EST.)",
                "BUY-INITIATED (EST.)",
                "UNKNOWN",
            ],
        )
        self.assertEqual(trades[-1]["time"], "10:00:00.000")

    def test_large_trade_threshold_is_inclusive(self):
        monitor = LiveMonitor(large_trade_shares=1_000)
        monitor.record_trade({"price": 10, "size": 999})
        monitor.record_trade({"price": 10, "size": 1_000})

        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["trade_count"], 2)
        self.assertEqual(snapshot["large_trade_count"], 1)
        self.assertEqual(snapshot["trades"][0]["alert"], "<<< LARGE TRADE")
        self.assertEqual(snapshot["trades"][1]["alert"], "")

    def test_tape_is_bounded_while_counters_keep_total(self):
        monitor = LiveMonitor(max_tape_rows=2)
        for price in (10, 11, 12):
            monitor.record_trade({"price": price, "size": 1})

        snapshot = monitor.snapshot()
        self.assertEqual(snapshot["trade_count"], 3)
        self.assertEqual(
            [trade["price"] for trade in snapshot["trades"]],
            [12, 11],
        )

    def test_naive_timestamp_is_treated_as_utc(self):
        monitor = LiveMonitor()
        monitor.record_trade({
            "price": 10,
            "size": 1,
            "timestamp": datetime(2026, 1, 15, 15, 0),
        })

        self.assertEqual(monitor.snapshot()["trades"][0]["time"], "10:00:00.000")

    def test_invalid_trade_values_are_rejected(self):
        monitor = LiveMonitor()
        for trade in (
            {"price": 0, "size": 1},
            {"price": 10, "size": 0},
            SimpleNamespace(price=float("inf"), size=1),
        ):
            with self.subTest(trade=trade):
                with self.assertRaises(ValueError):
                    monitor.record_trade(trade)


if __name__ == "__main__":
    unittest.main()
