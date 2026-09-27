import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.board_filter import filter_board_items, is_mainstream_us_listing


class BoardFilterTest(unittest.TestCase):
    def test_keeps_common_shares_and_etfs(self) -> None:
        self.assertTrue(is_mainstream_us_listing("US.AAPL", "Apple"))
        self.assertTrue(is_mainstream_us_listing("US.BRK.B", "Berkshire"))
        self.assertTrue(is_mainstream_us_listing("US.SPY", "SPDR S&P 500 ETF"))
        self.assertTrue(is_mainstream_us_listing("US.HPE", "Hewlett Packard Enterprise"))

    def test_rejects_obscure_adrs(self) -> None:
        self.assertFalse(
            is_mainstream_us_listing(
                "US.JPPHY",
                "JAPAN POST HLDGS CO LTD UNSP ADR EA REPR 1 ORD",
            )
        )
        self.assertFalse(is_mainstream_us_listing("US.FNBKY", "FINECOBANK SPA UNSP ADR EACH REP 2 ORD SHS"))
        self.assertFalse(is_mainstream_us_listing("US.BSQKZ", "BLOCK INC"))

    def test_filter_board_items(self) -> None:
        items = [
            {"code": "US.JPPHY", "name": "JAPAN POST HLDGS CO LTD UNSP ADR"},
            {"code": "US.HPE", "name": "Hewlett Packard Enterprise"},
            {"code": "US.DELL", "name": "Dell Technologies"},
        ]
        kept = filter_board_items(items, limit=10)
        self.assertEqual([row["code"] for row in kept], ["US.HPE", "US.DELL"])


if __name__ == "__main__":
    unittest.main()
