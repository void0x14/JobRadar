"""Digital and freelance work: forums, marketplaces and the two big freelance boards."""

from __future__ import annotations

from jobradar.gig.adapters.base import LinkAdapter

R10_ILAN = LinkAdapter(
    key="r10_ilanlari",
    name="R10 (iş ilanları forumu)",
    platform="r10",
    list_urls=[
        "https://www.r10.net/yazilim-kodlama-is-ilanlari/",
        "https://blog.r10.net/is-ilanlari",
    ],
    pattern=r"r10\.net/[a-z0-9-]+-is-ilanlari/\d+-.*\.html",
    max_pages=2,
    note="The forum carries the ads; the blog page lists articles, not ads.",
)

R10_ARAYAN = LinkAdapter(
    key="r10_is_arayanlar",
    name="R10 (iş arayanlar)",
    platform="r10",
    list_urls=["https://www.r10.net/is-arayanlar/"],
    pattern=r"r10\.net/is-arayanlar/\d+-.*\.html",
)

BIONLUK = LinkAdapter(
    key="bionluk",
    name="Bionluk (iş arayan)",
    platform="bionluk",
    list_urls=["https://bionluk.com/freelancer-bul"],
    pattern=r"^https://bionluk\.com/(?!freelancer-bul/|blog|pages|destek|login|register)[a-z0-9_-]+/",
    note="The job board itself is behind a login; this page lists the open briefs.",
)

ARMUT = LinkAdapter(
    key="armut",
    name="Armut (hizmet verenler)",
    platform="armut",
    list_urls=["https://armut.com/hizmetveren"],
    pattern=r"armut\.com/hizmetveren/",
    note="No public job list over HTTP; the site renders it with JavaScript.",
)

UPWORK = LinkAdapter(
    key="upwork",
    name="Upwork (Turkish jobs)",
    platform="upwork",
    list_urls=[
        "https://www.upwork.com/freelance-jobs/turkish/",
        "https://www.upwork.com/freelance-jobs/software-testing/",
    ],
    pattern=r"upwork\.com/freelance-jobs/apply/",
    context_chars=900,
    note=(
        "Answers the first request with 403 and sets a cookie on it; the retry goes through. "
        "The listing page says whether the job is hourly or fixed-price."
    ),
)

CONTRA = LinkAdapter(
    key="contra",
    name="Contra (freelance jobs)",
    platform="contra",
    list_urls=["https://contra.com/features/find-freelance-jobs"],
    pattern=r"contra\.com/(?:jobs|opportunities)/",
    note="The list is rendered with JavaScript.",
)

ADAPTERS = [R10_ILAN, R10_ARAYAN, BIONLUK, ARMUT, UPWORK, CONTRA]
