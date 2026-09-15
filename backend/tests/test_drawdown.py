import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.drawdown import compute_drawdown


class DrawdownTest(unittest.TestCase):
    def test_peak_trough_and_rebound(self) -> None:
        bars = [
            {"time": "2024-01-01", "close": 100},
            {"time": "2024-01-02", "close": 120},
            {"time": "2024-01-03", "close": 90},
            {"time": "2024-01-04", "close": 99},
        ]
        metrics = compute_drawdown(bars)
        self.assertAlmostEqual(metrics["max_drawdown"], 90 / 120 - 1)
        self.assertEqual(metrics["max_drawdown_start"], "2024-01-02")
        self.assertEqual(metrics["max_drawdown_end"], "2024-01-03")
        self.assertEqual(metrics["underwater_days"], 2)
        self.assertAlmostEqual(metrics["current_drawdown"], 99 / 120 - 1)
        self.assertAlmostEqual(metrics["rebound_from_trough"], 99 / 90 - 1)
        self.assertAlmostEqual(metrics["period_return"], 99 / 100 - 1)


if __name__ == "__main__":
    unittest.main()
