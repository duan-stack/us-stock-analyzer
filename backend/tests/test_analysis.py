import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.analysis import build_logic, compute_indicators


def _bars(closes: list[float]) -> list[dict]:
    return [{"time": f"2024-01-{i+1:02d}", "close": c, "volume": 1000 + i} for i, c in enumerate(closes)]


class AnalysisLogicTest(unittest.TestCase):
    def test_uptrend_scores_bullish(self) -> None:
        closes = [100 + i * 0.4 for i in range(80)]
        logic = build_logic(
            "US.AAPL",
            {"name": "Apple", "pe_ratio": 22, "lowest52weeks_price": 90, "highest52weeks_price": 140},
            _bars(closes),
            {"current_drawdown": -0.02, "max_drawdown": -0.18, "underwater_days": 3},
            [{"title": "Apple beat estimates, growth accelerates"}],
        )
        self.assertEqual(logic["verdict"]["bias"], "偏多")
        trend = next(d for d in logic["dimensions"] if d["id"] == "trend")
        self.assertGreaterEqual(trend["score"], 1)
        self.assertTrue(logic["levels"]["supports"])

    def test_downtrend_scores_bearish(self) -> None:
        closes = [180 - i * 0.8 for i in range(80)]
        logic = build_logic(
            "US.TSLA",
            {"name": "Tesla", "pe_ratio": 80, "lowest52weeks_price": 90, "highest52weeks_price": 200},
            _bars(closes),
            {"current_drawdown": -0.32, "max_drawdown": -0.36, "underwater_days": 40},
            [{"title": "下调目标价 downgrade 减持"}],
        )
        self.assertEqual(logic["verdict"]["bias"], "偏空")
        risk = next(d for d in logic["dimensions"] if d["id"] == "risk")
        self.assertLessEqual(risk["score"], -1)

    def test_indicators_have_moving_averages(self) -> None:
        ind = compute_indicators(_bars([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] * 6))
        self.assertIsNotNone(ind["ma20"])
        self.assertGreater(ind["last_close"], ind["ma20"])


if __name__ == "__main__":
    unittest.main()
