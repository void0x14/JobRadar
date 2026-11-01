"""One scan: every source, one after the other, then classify, dedupe and store.

The rules the brief asks for:

- new ads are read (the ad page carries the pay, the date and the place);
- an ad we already know is only touched, not read again;
- the same ad on two sites keeps one row;
- a source that fails is recorded as failed, and the scan carries on.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jobradar.db.repo import Repo
from jobradar.gig.adapters import ADAPTERS
from jobradar.gig.adapters.base import Adapter, Blocked, WebClient, _junk_title, main_text
from jobradar.gig.classify import classify, detect_employer, detect_published
from jobradar.gig.models import Gig, Verdict
from jobradar.gig.structured import page_title, read_posting
from jobradar.pipeline.dedupe import sha1

log = logging.getLogger(__name__)

MAX_NEW_PER_SOURCE = 20  # how many new ads one source may cost per scan
RECHECK_AFTER_HOURS = 24  # when to look at an old ad again: it may be closed by now
MAX_AGE_DAYS = 30  # an ad older than this is old, not new


@dataclass
class ScanResult:
    """What one source did in this scan."""

    source_key: str
    name: str
    ok: bool
    error: str | None = None
    listings: int = 0
    new: int = 0
    gigs: int = 0
    seconds: float = 0.0
    new_gigs: list[Gig] = field(default_factory=list)


def _listing_url(listing_url: str) -> str:
    """The same ad on two pages of the same site is one ad: drop the query and the fragment."""
    base = listing_url.split("#", 1)[0].rstrip("/")
    return base.split("?", 1)[0]


async def scan_source(
    adapter: Adapter,
    repo: Repo,
    client: WebClient,
    *,
    fetch_details: bool = True,
    max_new: int = MAX_NEW_PER_SOURCE,
) -> ScanResult:
    """Read one source: its listing page, then the ad pages it points at."""
    started = time.monotonic()
    now = datetime.now(UTC)
    repo.upsert_gig_source(
        adapter.key,
        adapter.name,
        getattr(adapter, "platform", adapter.key),
        url=(getattr(adapter, "list_urls", None) or [None])[0],
        manual=bool(getattr(adapter, "manual", False)),
        note=getattr(adapter, "note", ""),
    )
    result = ScanResult(source_key=adapter.key, name=adapter.name, ok=True)
    try:
        listings = await adapter.scan(client)
    except Blocked as e:
        result.ok = False
        result.error = str(e)
        result.seconds = time.monotonic() - started
        repo.set_gig_source_result(adapter.key, ok=False, error=str(e))
        log.info("source blocked", extra={"source": adapter.key, "error": str(e)})
        return result
    except Exception as e:  # a broken adapter must not stop the others
        result.ok = False
        result.error = f"{type(e).__name__}: {e}"
        result.seconds = time.monotonic() - started
        repo.set_gig_source_result(adapter.key, ok=False, error=result.error)
        log.warning("source failed", extra={"source": adapter.key, "error": result.error})
        return result

    result.listings = len(listings)
    new_gigs = 0
    for listing in listings:
        url = _listing_url(listing.url)
        if repo.gig_by_url(url) is not None:
            continue
        if new_gigs >= max_new:
            break
        description = listing.summary
        employer = listing.employer
        published = None
        city = None
        district = None
        title = listing.title
        page_html = None
        if fetch_details and getattr(adapter, "fetch_details", True):
            try:
                html = await client.html(
                    listing.url, ignore_robots=getattr(adapter, "ignore_robots", False)
                )
                page_html = html
                posting = read_posting(html)
                if posting is not None:
                    # The listing page may say how the job is paid (Upwork: "Hourly"), the
                    # ad page says what the job is. Keep both.
                    body = posting.description or ""
                    description = f"{description}\n{body}" if body else description
                    employer = employer or posting.employer
                    published = posting.date_posted
                    city = posting.city
                    district = posting.district
                    title = posting.title or title
                    if posting.salary_text:
                        description = f"{description}\n{posting.salary_text}"
                else:
                    body = main_text(html)
                    # The listing page may say how the job is paid (Upwork: "Hourly"), the
                    # ad page says what the job is. Keep both.
                    description = f"{description}\n{body}" if body else description
            except Blocked as e:
                log.info("ad page not readable", extra={"source": adapter.key, "error": str(e)})
        if _junk_title(title) and page_html is not None:
            # The link text said nothing ("Apply now", "Preview Job"): the page knows.
            title = page_title(page_html) or title
        if not description:
            description = listing.title
        gig = classify(
            title=title,
            description=description,
            url=url,
            platform=listing.platform,
            employer=employer or detect_employer(description),
            published=published or detect_published(description or listing.title),
            default_city=getattr(adapter, "default_city", None),
            city=city,
            district=district,
            physical=getattr(adapter, "physical", True),
        )
        gig.job_id = sha1(url)[:40]
        gig.source_key = adapter.key
        published = gig.publication_date
        if published is not None and published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        if published is not None and (now - published).days > MAX_AGE_DAYS:
            gig.verdict = Verdict.EXCLUDED
            gig.reasons = [*gig.reasons, "old ad"]
            gig.confidence_score = min(gig.confidence_score, 0.5)
        _, is_new = repo.save_gig(gig)
        if is_new:
            result.new += 1
            if gig.verdict == Verdict.GIG:
                result.gigs += 1
                result.new_gigs.append(gig)
                new_gigs += 1
    # Old ads: a page that has gone tells us the ad is closed.
    for known in repo.gigs_to_recheck(
        adapter.key, (now - timedelta(hours=RECHECK_AFTER_HOURS)).isoformat(), limit=5
    ):
        try:
            await client.html(known.original_url)
        except Blocked as e:
            if "404" in str(e):
                repo.mark_gig_closed(known.job_id)
                log.info(
                    "ad closed", extra={"job_id": known.job_id[:10], "url": known.original_url}
                )
    result.seconds = time.monotonic() - started
    repo.set_gig_source_result(adapter.key, ok=True, listings=result.listings, gigs=result.gigs)
    log.info(
        "source scanned",
        extra={
            "source": adapter.key,
            "listings": result.listings,
            "new": result.new,
            "gigs": result.gigs,
            "seconds": round(result.seconds, 1),
        },
    )
    return result


async def scan_all(
    repo: Repo,
    *,
    only: list[str] | None = None,
    fetch_details: bool = True,
    client: WebClient | None = None,
) -> list[ScanResult]:
    """Scan every source (or only the named ones) and return what each one did."""
    owns_client = client is None
    http = client or WebClient()
    results: list[ScanResult] = []
    try:
        for adapter in ADAPTERS:
            if only and adapter.key not in only:
                continue
            results.append(await scan_source(adapter, repo, http, fetch_details=fetch_details))
    finally:
        if owns_client:
            await http.aclose()
    return results
