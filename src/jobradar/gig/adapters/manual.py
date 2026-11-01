"""Facebook groups and WhatsApp: the ads come from the person, not from a crawler.

Both need an account and a membership, and neither offers a public listing API. The brief
says to support "user-provided or permitted message flows" for them, so these adapters
never scrape: they point at the two ways a person can bring an ad in.

- forward or paste the ad text:  jobradar gig add --text "..." --url "..."
- WhatsApp: the repo's wa-bridge sends incoming messages over HTTP, and the same
  "jobradar gig add" path takes them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jobradar.gig.adapters.base import Listing, WebClient


@dataclass
class ManualAdapter:
    """A source that only a person can read, with the way to bring its ads in."""

    key: str
    name: str
    platform: str
    manual: bool = True
    note: str = ""
    entry_points: list[str] = field(default_factory=list)

    async def scan(self, client: WebClient) -> list[Listing]:
        return []


ADAPTERS = [
    ManualAdapter(
        key="facebook",
        name="Facebook grupları (iş ilanı)",
        platform="facebook",
        note="Facebook has no public listing API and groups need an account; nothing is scraped.",
        entry_points=[
            "Facebook: İş Arayan İş Veren Ankara grubundaki ilanı kopyalayıp "
            "jobradar gig add --text ile ekle",
            "veya ilanın bağlantısını jobradar gig add --url ile ver",
        ],
    ),
    ManualAdapter(
        key="whatsapp",
        name="WhatsApp grupları (iş ilanı)",
        platform="whatsapp",
        note="Groups need a membership and the messages are not public; nothing is scraped.",
        entry_points=[
            "WhatsApp: grubundaki ilanı ilet veya kopyalayıp jobradar gig add --text ile ekle",
            "wa-bridge (Node) gelen mesajı aynı komuta yollar",
        ],
    ),
]
