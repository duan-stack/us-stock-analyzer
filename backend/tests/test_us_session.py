import unittest
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.us_session import us_equity_session

ET = ZoneInfo("America/New_York")


class UsSessionTest(unittest.TestCase):
    def test_regular_hours(self) -> None:
        now = datetime(2026, 9, 14, 10, 15, tzinfo=ET)
        state = us_equity_session(now)
        self.assertEqual(state["session"], "regular")
        self.assertEqual(state["label"], "盘中")

    def test_pre_market(self) -> None:
        now = datetime(2026, 9, 14, 7, 0, tzinfo=ET)
        self.assertEqual(us_equity_session(now)["session"], "pre")

    def test_after_hours(self) -> None:
        now = datetime(2026, 9, 14, 17, 30, tzinfo=ET)
        self.assertEqual(us_equity_session(now)["session"], "after")

    def test_weekend(self) -> None:
        now = datetime(2026, 9, 13, 12, 0, tzinfo=ET)
        state = us_equity_session(now)
        self.assertEqual(state["session"], "closed")
        self.assertEqual(state["label"], "周末休市")

    def test_holiday(self) -> None:
        now = datetime(2025, 12, 25, 12, 0, tzinfo=ET)
        state = us_equity_session(now)
        self.assertTrue(state["holiday"])
        self.assertEqual(state["session"], "closed")


if __name__ == "__main__":
    unittest.main()
