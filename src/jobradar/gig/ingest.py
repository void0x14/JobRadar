"""Ads that come from the person, not from a crawler.

Facebook groups and WhatsApp groups need an account and a membership, so nothing is
scraped from them: the ad text is pasted, forwarded or pushed by the user's own bridge,
and it comes in through this one door. The same rules apply as for the scanned ads, so a
manual ad is judged the same way.
"""

from __future__ import annotations

from jobradar.db.repo import Repo
from jobradar.gig.classify import classify, detect_employer, detect_published
from jobradar.gig.models import Gig
from jobradar.pipeline.dedupe import sha1


def add_gig(
    repo: Repo,
    text: str,
    *,
    url: str | None = None,
    platform: str = "manuel",
    source_key: str = "manuel",
) -> tuple[Gig, bool]:
    """Read an ad someone brought in and store it. Returns (the gig, is_new)."""
    link = url or f"https://manuel.local/{sha1(text)[:16]}"
    gig = classify(
        title=text.split(chr(10), 1)[0][:120],
        description=text,
        url=link,
        platform=platform,
        employer=detect_employer(text),
        published=detect_published(text),
    )
    gig.job_id = sha1(link)[:40]
    gig.source_key = source_key
    _, is_new = repo.save_gig(gig)
    return gig, is_new
