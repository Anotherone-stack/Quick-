"""News and official updates from a small allow-list of trusted sources."""

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.request import Request, urlopen
import re
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class NewsSource:
    name: str
    feed_url: str
    allowed_hosts: tuple[str, ...]


NEWS_SOURCES = (
    NewsSource(
        name="BBC Business",
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        allowed_hosts=("bbc.co.uk", "bbc.com"),
    ),
    NewsSource(
        name="U.S. Securities and Exchange Commission",
        feed_url="https://www.sec.gov/news/pressreleases.rss",
        allowed_hosts=("sec.gov",),
    ),
    NewsSource(
        name="Federal Reserve",
        feed_url="https://www.federalreserve.gov/feeds/press_all.xml",
        allowed_hosts=("federalreserve.gov",),
    ),
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(value)
    text = re.sub(r"\s+", " ", " ".join(extractor.parts)).strip()
    return re.sub(r"\s+([.,!?;:])", r"\1", text)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, *names: str) -> str:
    accepted = {name.lower() for name in names}
    for child in element:
        if _local_name(child.tag) in accepted:
            return "".join(child.itertext()).strip()
    return ""


def _is_trusted_link(link: str, source: NewsSource) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(link)
    return parsed.scheme == "https" and any(
        parsed.hostname == host or (parsed.hostname or "").endswith(f".{host}")
        for host in source.allowed_hosts
    )


def _parse_published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def parse_feed(xml_data: bytes, source: NewsSource) -> list[dict[str, str]]:
    """Parse RSS or Atom entries, keeping links on the source's own domain."""
    root = ET.fromstring(xml_data)
    entries = [
        element for element in root.iter()
        if _local_name(element.tag) in {"item", "entry"}
    ]
    articles = []
    for entry in entries:
        title = _plain_text(_child_text(entry, "title"))
        summary = _plain_text(
            _child_text(entry, "description", "summary", "content")
        )
        link = _child_text(entry, "link")
        if not link:
            for child in entry:
                if _local_name(child.tag) == "link":
                    link = child.attrib.get("href", "")
                    if link:
                        break
        if not title or not _is_trusted_link(link, source):
            continue

        published_text = _child_text(
            entry, "pubDate", "published", "updated", "date"
        )
        published = _parse_published(published_text)
        articles.append({
            "title": title,
            "summary": summary,
            "link": link,
            "source": source.name,
            "published": published.isoformat() if published else "",
        })
    return articles


def fetch_source(source: NewsSource) -> list[dict[str, str]]:
    request = Request(
        source.feed_url,
        headers={"User-Agent": "StockyMarketDashboard/1.0", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
    )
    with urlopen(request, timeout=15) as response:
        xml_data = response.read(2_000_001)
    if len(xml_data) > 2_000_000:
        raise ValueError(f"{source.name} feed exceeded the 2 MB size limit.")
    return parse_feed(xml_data, source)


def load_news() -> tuple[list[dict[str, str]], dict[str, str]]:
    """Fetch all configured sources, isolating failures by publisher."""
    articles: list[dict[str, str]] = []
    errors: dict[str, str] = {}
    seen_links: set[str] = set()
    for source in NEWS_SOURCES:
        try:
            for article in fetch_source(source):
                if article["link"] not in seen_links:
                    seen_links.add(article["link"])
                    articles.append(article)
        except (URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors[source.name] = str(exc)
    articles.sort(key=lambda article: article["published"], reverse=True)
    return articles[:100], errors
