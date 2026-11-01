"""What every source adapter has in common: an HTTP client with manners, a listing, and a
generic adapter that reads a listing page and keeps the links that look like ads.

Manners are the ones the rest of JobRadar uses: robots.txt is obeyed, one request per
second per host, and a real user agent. A source that answers 403 or a challenge page is
reported as blocked, never worked around.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

from jobradar.gig.structured import read_item_list

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) JobRadar/0.3 (+https://github.com/ThePlator/JobRadar)"
TIMEOUT = 20.0
BLOCK_MARKERS = (
    "just a moment",
    "attention required",
    "security check",
    "challenge -",
    "enable javascript and cookies to continue",
    "are you a robot",
    "access denied",
    "forbidden",
)


class Blocked(Exception):
    """The source refused us (403, a WAF challenge, a login wall). Not worked around."""


_JUNK_TITLES = {
    "apply now",
    "apply",
    "skip to content",
    "details",
    "more",
    "read more",
    "devam",
    "ilani ac",
    "basvur",
    "basvur formu",
    "incele",
    "view",
    "open",
    "jobs",
    "is ilanlari",
}


def _junk_title(title: str) -> bool:
    """A link text that says nothing about the ad ("Apply now", "Skip to content")."""
    return title.strip().casefold() in _JUNK_TITLES or len(title.strip()) < 3


class WebClient:
    """Raw HTML and main text, with robots.txt obeyed and one request per second per host."""

    def __init__(self, user_agent: str = USER_AGENT, interval: float = 1.0) -> None:
        self.client = httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"},
        )
        self.interval = interval
        self._next_at: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _pace(self, host: str) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            wait = self._next_at.get(host, 0.0) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_at[host] = time.monotonic() + self.interval

    async def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = None
            try:
                await self._pace(parts.hostname or "")
                resp = await self.client.get(origin + "/robots.txt")
                if resp.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(resp.text.splitlines())
            except httpx.HTTPError:
                parser = None  # no robots.txt reachable: allowed
            self._robots[origin] = parser
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    async def html(self, url: str) -> str:
        """The page's HTML. Raises Blocked when the source refuses us or robots says no."""
        if not await self._allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        host = urlsplit(url).hostname or ""
        await self._pace(host)
        try:
            resp = await self.client.get(url)
        except httpx.HTTPError as e:
            raise Blocked(f"{host} could not be reached: {type(e).__name__}") from e
        if resp.status_code in (401, 403, 404, 429) or resp.status_code >= 500:
            raise Blocked(f"{host} answered {resp.status_code}")
        body = resp.text
        head = body[:4000].casefold()
        if any(marker in head for marker in BLOCK_MARKERS):
            raise Blocked(f"{host} answered a challenge or block page")
        return body

    async def text(self, url: str) -> str:
        """The page's main text (the ad body), empty when there is none."""
        body = await self.html(url)
        return main_text(body)


def main_text(html: str) -> str:
    """The readable text of a page (the ad body), empty when there is none."""
    return trafilatura.extract(html) or ""


class _LinkParser(HTMLParser):
    """Every anchor on the page: its absolute URL and its text."""

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            label = " ".join("".join(self._text).split())
            self.links.append((urljoin(self.base, self._href), label))
            self._href = None
            self._text = []


def extract_links(html: str, base: str) -> list[tuple[str, str]]:
    """(absolute URL, anchor text) for every link on the page."""
    parser = _LinkParser(base)
    try:
        parser.feed(html)
    except Exception:  # a broken page is still worth the links we got
        log.debug("could not parse all of %s", base)
    return parser.links


@dataclass
class Listing:
    """One ad found on a listing page: where it is and what it is called."""

    url: str
    title: str
    platform: str
    source_key: str
    employer: str | None = None
    published: str | None = None
    summary: str = ""


class Adapter(Protocol):
    """What every source implements."""

    key: str
    name: str
    platform: str
    manual: bool  # True when a person has to bring the ads in

    async def scan(self, client: WebClient) -> list[Listing]: ...


@dataclass
class LinkAdapter:
    """The generic adapter: read these listing pages, keep the links that look like ads.

    Most job boards are the same shape: a list page whose anchors point at the ads. The
    pattern decides what an ad link looks like; the anchor text is the ad's title.
    """

    key: str
    name: str
    platform: str
    list_urls: list[str]
    pattern: str
    manual: bool = False
    max_pages: int = 1
    note: str = ""
    default_city: str | None = None  # the list is filed under this city
    _compiled: re.Pattern[str] = field(
        init=False, repr=False, compare=False, default=re.compile("$")
    )

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    async def scan(self, client: WebClient) -> list[Listing]:
        found: dict[str, Listing] = {}
        errors: list[str] = []
        for url in self.list_urls[: self.max_pages]:
            try:
                body = await client.html(url)
            except Blocked as e:
                # One dead listing page must not take the whole source down: the source is
                # blocked only when every one of its pages is refused.
                errors.append(str(e))
                continue
            names = read_item_list(body)
            for href, text in extract_links(body, url):
                if not self._compiled.search(href):
                    continue
                key = href.split("#", 1)[0].split("?", 1)[0].rstrip("/")
                title = names.get(key, "").strip() or text.strip()
                if not title:
                    continue
                if key in found:
                    # The same ad twice (a card link and an 'Apply now' link): keep the
                    # title that says what the ad is.
                    if len(title) > len(found[key].title) and not _junk_title(found[key].title):
                        found[key] = Listing(
                            url=href, title=title, platform=self.platform, source_key=self.key
                        )
                    continue
                found[key] = Listing(
                    url=href, title=title, platform=self.platform, source_key=self.key
                )
        if not found and errors:
            raise Blocked(errors[0])
        return list(found.values())
