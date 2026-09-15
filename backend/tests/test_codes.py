import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.codes import display_symbol, is_us_code, normalize_code, yahoo_symbol


class CodesTest(unittest.TestCase):
    def test_us_plain_ticker(self) -> None:
        self.assertEqual(normalize_code("aapl"), "US.AAPL")
        self.assertEqual(display_symbol("US.AAPL"), "AAPL")
        self.assertEqual(yahoo_symbol("US.AAPL"), "AAPL")

    def test_us_suffix_and_prefix(self) -> None:
        self.assertEqual(normalize_code("NVDA.US"), "US.NVDA")
        self.assertEqual(normalize_code("US.MSFT"), "US.MSFT")

    def test_dotted_us_ticker(self) -> None:
        self.assertEqual(normalize_code("BRK.B"), "US.BRK.B")
        self.assertEqual(normalize_code("BRK-B"), "US.BRK.B")
        self.assertEqual(display_symbol("US.BRK.B"), "BRK.B")
        self.assertEqual(yahoo_symbol("US.BRK.B"), "BRK-B")

    def test_rejects_hk_and_digits(self) -> None:
        with self.assertRaises(ValueError):
            normalize_code("700")
        with self.assertRaises(ValueError):
            normalize_code("HK.00700")
        with self.assertRaises(ValueError):
            normalize_code("00700.HK")
        with self.assertRaises(ValueError):
            normalize_code("CA.SNDK")
        with self.assertRaises(ValueError):
            normalize_code("KR.000700")
        with self.assertRaises(ValueError):
            normalize_code("苹果")
        self.assertFalse(is_us_code("HK.00700"))
        self.assertTrue(is_us_code("AAPL"))


if __name__ == "__main__":
    unittest.main()
