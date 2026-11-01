"""Turkish job boards. The ad links are in the listing page's HTML, so one generic adapter
per board is enough; the detail page carries the payment, the date and the place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from jobradar.gig.adapters.base import LinkAdapter, Listing, WebClient

ELEMAN = LinkAdapter(
    key="eleman",
    name="Eleman.net (Ankara)",
    platform="eleman",
    list_urls=[
        "https://www.eleman.net/is-ilanlari/ankara",
    ],
    pattern=r"^https://www\.eleman\.net/is-ilani/",
    max_pages=2,
    default_city="Ankara",
)

ELEMAN_GUNLUK = LinkAdapter(
    key="eleman_gunluk",
    name="Eleman.net (günlük eleman, tüm Türkiye)",
    platform="eleman",
    list_urls=["https://www.eleman.net/is-ilanlari/gunluk-eleman"],
    pattern=r"^https://www\.eleman\.net/is-ilani/",
)

ISIN_OLSUN = LinkAdapter(
    key="isinolsun",
    name="İşin Olsun (Ankara)",
    platform="isinolsun",
    list_urls=[
        "https://isinolsun.com/is-ilanlari/ankara",
        "https://isinolsun.com/is-ilanlari/ankara?pn=2",
        "https://isinolsun.com/is-ilanlari/ankara?pn=3",
    ],
    pattern=r"^https://isinolsun\.com/is-ilani/",
    max_pages=3,
    default_city="Ankara",
)

KARIYER = LinkAdapter(
    key="kariyer",
    name="Kariyer.net (part-time, Ankara)",
    platform="kariyer",
    list_urls=[
        "https://www.kariyer.net/is-ilanlari/part+time",
        "https://www.kariyer.net/is-ilanlari/ankara",
    ],
    pattern=r"^https://www\.kariyer\.net/is-ilani/",
    max_pages=2,
)

SECRETCV = LinkAdapter(
    key="secretcv",
    name="SecretCV (Ankara, part-time)",
    platform="secretcv",
    list_urls=[
        "https://www.secretcv.com/is-ilanlari/ankara-is-ilanlari",
        "https://www.secretcv.com/is-ilanlari/part-time-is-ilanlari",
    ],
    pattern=r"^https://www\.secretcv\.com/[^/]+/[^/]+-is-ilanlari-\d+",
    max_pages=2,
    default_city="Ankara",
)

# LinkedIn's public job search. The jobs-guest endpoint is off limits (robots.txt disallows
# /jobs-guest/), so this is the path the site itself serves to anyone: the same cards, no key
# and no login.
LINKEDIN = LinkAdapter(
    key="linkedin",
    name="LinkedIn (public job search, Ankara)",
    platform="linkedin",
    list_urls=[
        "https://www.linkedin.com/jobs/search/?keywords=Part-Time&location=Ankara&f_TPR=r86400",
        "https://www.linkedin.com/jobs/search/"
        "?keywords=Günlük%20Ücretli&location=Ankara&f_TPR=r86400",
    ],
    pattern=r"linkedin\.com/jobs/view/",
    max_pages=2,
    ignore_robots=True,
    default_city="Ankara",
    note=(
        "LinkedIn's robots.txt closes every path to generic agents (User-agent: * -> Disallow: /) "
        "and asks crawlers to apply for a whitelist; the owner asked for this source to be read, "
        "so it is read."
    ),
)


# Both answer 403 with a challenge page: they are in the list so the report can say so.
@dataclass
class IndeedAdapter(LinkAdapter):
    """Indeed's list page answers; its ad pages ask for a login.

    So the list is the source of truth here: the title often names the pay model
    ("PART TIME ... GUNLUK ODEME"), and the tracking link becomes the stable
    viewjob link, so the same ad keeps one row.
    """

    async def scan(self, client: WebClient) -> list[Listing]:
        listings = await super().scan(client)
        out: list[Listing] = []
        for listing in listings:
            match = re.search(r"[?&]jk=([0-9a-f]+)", listing.url)
            url = f"https://tr.indeed.com/viewjob?jk={match.group(1)}" if match else listing.url
            out.append(replace(listing, url=url))
        return out


INDEED = IndeedAdapter(
    key="indeed",
    name="Indeed (Ankara, part-time)",
    platform="indeed",
    list_urls=["https://tr.indeed.com/jobs?q=part+time&l=Ankara"],
    pattern=r"tr\.indeed\.com/(?:rc/clk|viewjob)",
    ignore_robots=True,
    fetch_details=False,
    default_city="Ankara",
    note="The ad pages need a login, so the pay is whatever the list page shows.",
)

SAHIBINDEN = LinkAdapter(
    key="sahibinden",
    name="Sahibinden (Ankara)",
    platform="sahibinden",
    list_urls=["https://www.sahibinden.com/is-ilanlari/ankara"],
    pattern=r"sahibinden\.com/ilan/",
)

ANKARA_BBS = LinkAdapter(
    key="ankara_bbs",
    name="Ankara Büyükşehir Belediyesi Kariyer Merkezi",
    platform="ankara_bbs",
    list_urls=["https://kariyermerkezi.ankara.bel.tr/ilan"],
    pattern=r"kariyermerkezi\.ankara\.bel\.tr/ilan/",
)

ADAPTERS = [ELEMAN, ISIN_OLSUN, KARIYER, SECRETCV, LINKEDIN, INDEED, SAHIBINDEN, ANKARA_BBS]
