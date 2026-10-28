import xml.etree.ElementTree as ET

import pytest

from src.news import NEWS_SOURCES, parse_feed


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

    articles = parse_feed(feed, NEWS_SOURCES[2])

    assert len(articles) == 1
    assert articles[0]["summary"] == "Official update"
    assert articles[0]["published"] == "2026-10-28T01:00:00+00:00"


def test_parse_feed_reports_invalid_xml():
    with pytest.raises(ET.ParseError):
        parse_feed(b"<rss>", NEWS_SOURCES[0])
