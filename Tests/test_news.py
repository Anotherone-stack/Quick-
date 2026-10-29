import json
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from src.news import (
    NEWS_SOURCES,
    fetch_yahoo_finance_news,
    parse_feed,
    summarize_news,
)


def test_parse_feed_keeps_only_articles_from_allowlisted_publisher():
    feed = b"""<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Market update</title>
        <link>https://www.bbc.com/news/business-123</link>
        <description><![CDATA[<p>New market <b>report</b>.</p>]]></description>
        <pubDate>Wed, 28 Oct 2026 01:00:00 GMT</pubDate>
      </item>
      <item>
        <title>Untrusted redirect</title>
        <link>https://example.com/fake</link>
      </item>
      <item>
        <title>Insecure link</title>
        <link>http://www.bbc.com/news/unsafe</link>
      </item>
    </channel></rss>"""

    articles = parse_feed(feed, NEWS_SOURCES[0])

    assert len(articles) == 1
    assert articles[0]["title"] == "Market update"
    assert articles[0]["summary"] == "New market report."
    assert articles[0]["source"] == "BBC Business"
    assert articles[0]["published"] == "2026-10-28T01:00:00+00:00"


def test_parse_feed_supports_atom_link_and_updated_date():
    feed = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Fed update</title>
        <link href="https://www.federalreserve.gov/news.htm"/>
        <updated>2026-10-28T01:00:00Z</updated>
        <summary>Official update</summary>
      </entry>
    </feed>"""

    federal_reserve = next(
        source for source in NEWS_SOURCES if source.name == "Federal Reserve"
    )
    articles = parse_feed(feed, federal_reserve)

    assert len(articles) == 1
    assert articles[0]["summary"] == "Official update"
    assert articles[0]["published"] == "2026-10-28T01:00:00+00:00"


def test_parse_feed_reports_invalid_xml():
    with pytest.raises(ET.ParseError):
        parse_feed(b"<rss>", NEWS_SOURCES[0])


def test_summarize_news_requires_an_api_key():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        summarize_news(
            [{"source": "BBC Business", "title": "Headline", "summary": "", "link": "https://bbc.com/news/1"}],
            "",
        )


def test_summarize_news_uses_source_attributed_input():
    response_body = json.dumps({
        "choices": [{"message": {"content": "BBC reports a market update."}}],
    }).encode()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, limit):
            return response_body

    articles = [{
        "source": "BBC Business",
        "title": "Market update",
        "summary": "Source report details",
        "link": "https://www.bbc.com/news/123",
    }]
    with patch("src.news.urlopen", return_value=FakeResponse()) as urlopen:
        digest = summarize_news(articles, "test-key")

    request = urlopen.call_args.args[0]
    request_data = json.loads(request.data)
    assert request.full_url == "https://api.openai.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-key"
    assert "BBC Business" in request_data["messages"][1]["content"]
    assert digest == "BBC reports a market update."


def test_yahoo_finance_news_keeps_only_yahoo_hosted_links():
    class FakeSearch:
        def __init__(self, *args, **kwargs):
            self.news = [
                {
                    "title": "Market headline",
                    "publisher": "Zacks",
                    "link": "https://finance.yahoo.com/news/market-headline.html",
                    "providerPublishTime": 1793149200,
                },
                {
                    "title": "Untrusted link",
                    "publisher": "Unknown",
                    "link": "https://example.com/not-yahoo",
                    "providerPublishTime": 1793149200,
                },
                {
                    "title": "Unapproved publisher",
                    "publisher": "BeInCrypto",
                    "link": "https://finance.yahoo.com/news/crypto-headline.html",
                    "providerPublishTime": 1793149200,
                },
            ]

    with patch("yfinance.Search", FakeSearch):
        articles = fetch_yahoo_finance_news()

    assert len(articles) == 1
    assert articles[0]["source"] == "Yahoo Finance"
    assert articles[0]["publisher"] == "Zacks"
    assert articles[0]["link"].startswith("https://finance.yahoo.com/")
