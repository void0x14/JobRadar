"""Public Telegram channels, read the way a visitor sees them.

t.me/s/<channel> is the channel's public web preview: no account, no API key, only what
anyone can read. The message text sits in a div and the link to the message in an anchor,
so this adapter reads those two instead of the links alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from jobradar.gig.adapters.base import Blocked, Listing, WebClient


class _ChannelParser(HTMLParser):
    """Collects (message link, message text, posted at) from a channel preview page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.messages: list[tuple[str, str, str | None]] = []
        self._text_parts: list[str] = []
        self._in_text = False
        self._date: str | None = None
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        classes = (attrs_map.get("class") or "").split()
        if tag == "div" and "tgme_widget_message_text" in classes:
            self._in_text = True
            self._text_parts = []
        elif tag == "a" and "tgme_widget_message_date" in classes:
            self._href = attrs_map.get("href")
            self._date = None
        elif tag == "time" and self._href is not None:
            self._date = attrs_map.get("datetime")

    def handle_data(self, data: str) -> None:
        if self._in_text:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_text:
            self._in_text = False
        elif tag == "a" and self._href is not None:
            text = " ".join("".join(self._text_parts).split())
            if text:
                self.messages.append((self._href, text, self._date))
            self._href = None
            self._date = None


@dataclass
class TelegramChannelAdapter:
    """One public channel."""

    key: str
    name: str
    platform: str = "telegram"
    channel: str = ""
    manual: bool = False
    note: str = ""

    async def scan(self, client: WebClient) -> list[Listing]:
        url = f"https://t.me/s/{self.channel}"
        body = await client.html(url)
        parser = _ChannelParser()
        parser.feed(body)
        if not parser.messages:
            raise Blocked(f"{self.channel} has no public preview")
        out: list[Listing] = []
        for href, text, posted in parser.messages:
            title = text.split("\n", 1)[0].strip()[:200]
            out.append(
                Listing(
                    url=href,
                    title=title or text[:200],
                    platform=self.platform,
                    source_key=self.key,
                    published=posted,
                    summary=text[:4000],
                )
            )
        return out


def _channel_adapter(key: str, name: str, channel: str) -> TelegramChannelAdapter:
    return TelegramChannelAdapter(key=key, name=name, channel=channel)


ADAPTERS = [
    _channel_adapter("telegram_ilanlar06", "Telegram: Ankara İş İlanları", "ilanlar06"),
    _channel_adapter("telegram_eleman_arayanlar", "Telegram: Eleman Arayanlar", "eleman_arayanlar"),
    _channel_adapter("telegram_rasyokariyer", "Telegram: Rasyonel Kariyer", "rasyokariyer"),
]
