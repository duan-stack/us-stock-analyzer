import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.news import merge_news_items


class NewsMergeTest(unittest.TestCase):
    def test_dedupes_title_and_url(self) -> None:
        merged = merge_news_items(
            [
                [
                    {
                        "title": "Apple rises",
                        "url": "https://example.com/a",
                        "source": "Yahoo Finance",
                        "publish_time": "2026-09-14T10:00:00+00:00",
                    }
                ],
                [
                    {
                        "title": "Apple  rises!!!",
                        "url": "https://example.com/b",
                        "source": "Google 新闻",
                        "publish_time": "2026-09-14T11:00:00+00:00",
                    },
                    {
                        "title": "Amazon earnings",
                        "url": "https://example.com/a",
                        "source": "新浪财经",
                        "publish_time": "2026-09-14T12:00:00+00:00",
                    },
                    {
                        "title": "Nvidia launches",
                        "url": "https://example.com/c",
                        "source": "富途",
                        "publish_time": "2026-09-14T13:00:00+00:00",
                    },
                ],
            ],
            limit=10,
        )
        titles = [item["title"] for item in merged]
        self.assertEqual(titles, ["Nvidia launches", "Apple rises"])


if __name__ == "__main__":
    unittest.main()
