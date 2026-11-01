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
    groups: list[str] = field(default_factory=list)  # where the ads are, for the person

    async def scan(self, client: WebClient) -> list[Listing]:
        return []


ADAPTERS = [
    ManualAdapter(
        key="facebook",
        name="Facebook grupları (iş ilanı)",
        platform="facebook",
        note=(
            "Facebook has no public listing API: robots.txt disallows the group pages and the "
            "posts need an account, so nothing is scraped."
        ),
        groups=[
            "https://www.facebook.com/groups/1533399140233390",
            "https://www.facebook.com/search/groups/?q=ankara%20g%C3%BCnl%C3%BCk%20i%C5%9F%20ilanlar%C4%B1",
        ],
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
        note=(
            "The directories are public and carry the invitation links, the member counts and "
            "whether a group is private; the messages themselves need a membership, so nothing "
            "is scraped."
        ),
        groups=[
            "https://whatsappgruplari.com/grup/ankara-is-ilanlari",
            "https://whatsappgruplari.com/kategori/is-ilanlari",
            "https://whatsappkanali.com/sehir/ankara/is-ilanlari",
        ],
        entry_points=[
            "WhatsApp: grubundaki ilanı ilet veya kopyalayıp jobradar gig add --text ile ekle",
            "wa-bridge (Node) gelen mesajı aynı komuta yollar",
        ],
    ),
]
