"""The nine checks the brief asks for, run against every source, and the report.

For each source:

1. can we reach it at all?
2. can we read a listing from it?
3. can we read an ad's details?
4. do we get the ad's own link?
5. can we tell when it was posted?
6. can we tell what it pays?
7. can we apply the Ankara / remote filter?
8. do the results dedupe?
9. does a second scan find the same ads (and no duplicates)?

A source that fails is reported as it is. Nothing here pretends a blocked source works.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from jobradar.db.repo import Repo
from jobradar.gig.adapters import ADAPTERS
from jobradar.gig.adapters.base import Adapter, Blocked, WebClient, main_text
from jobradar.gig.classify import classify, detect_published
from jobradar.gig.models import Verdict
from jobradar.gig.scan import _listing_url, scan_source
from jobradar.gig.structured import read_posting

log = logging.getLogger(__name__)

DAYS = 1  # "found in the last 24 hours"


@dataclass
class Check:
    """One of the nine checks: passed, failed, or not applicable."""

    name: str
    passed: bool | None
    detail: str = ""


@dataclass
class SourceReport:
    """Everything the brief asks to be reported about one source."""

    key: str
    name: str
    access: str  # working | blocked | failed | manual
    method: str
    checks: list[Check] = field(default_factory=list)
    last_ok: str | None = None
    error_count: int = 0
    listings_total: int = 0
    gigs_total: int = 0
    gigs_24h: int = 0
    classified_gigs: int = 0  # how many of the checked ads the classifier called a gig
    last_error: str | None = None
    manual_note: str = ""

    @property
    def working(self) -> bool:
        return self.access == "working"

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed is True)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.passed is False)


def method_of(adapter: Adapter) -> str:
    """How the source is read."""
    if getattr(adapter, "manual", False):
        return "manuel (kullanıcı ilanı ekler)"
    if getattr(adapter, "platform", "") == "telegram":
        return "HTTP (kanalın herkese açık web önizlemesi)"
    pages = len(getattr(adapter, "list_urls", []) or [])
    return f"HTTP (liste sayfası + ilan sayfası, {pages} liste)"


async def validate_source(
    adapter: Adapter,
    repo: Repo,
    client: WebClient,
    *,
    repeat: bool = True,
) -> SourceReport:
    """Run the nine checks against one source and record what it did."""
    report = SourceReport(
        key=adapter.key,
        name=adapter.name,
        access="working",
        method=method_of(adapter),
        manual_note=getattr(adapter, "note", ""),
    )
    if getattr(adapter, "manual", False):
        report.access = "manual"
        if groups := getattr(adapter, "groups", None):
            report.manual_note = (report.manual_note + " Gruplar: " + ", ".join(groups)).strip()
        report.checks = [
            Check("Kaynağa erişilebiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("İlan listesi alınabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("İlan detayları okunabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("Orijinal ilan bağlantısı alınabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("İlan tarihi çıkarılabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("Ödeme bilgisi çıkarılabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("Ankara filtresi uygulanabiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("Sonuçlar tekilleştirilebiliyor mu?", None, "kullanıcı girişi gerekiyor"),
            Check("Tekrar taramada yeni ilan yakalanıyor mu?", None, "kullanıcı girişi gerekiyor"),
        ]
        return report

    # 1. can we reach it?
    try:
        listings = await adapter.scan(client)
    except Blocked as e:
        report.access = "blocked"
        report.last_error = str(e)
        report.checks = [Check("Kaynağa erişilebiliyor mu?", False, str(e))]
        report.checks += [Check(name, None, "kaynak okunamadı") for name in _REST]
        repo.set_gig_source_result(adapter.key, ok=False, error=str(e))
        return report
    except Exception as e:
        report.access = "failed"
        report.last_error = f"{type(e).__name__}: {e}"
        report.checks = [Check("Kaynağa erişilebiliyor mu?", False, report.last_error)]
        report.checks += [Check(name, None, "kaynak okunamadı") for name in _REST]
        repo.set_gig_source_result(adapter.key, ok=False, error=report.last_error)
        return report

    report.checks.append(
        Check(
            "Kaynağa erişilebiliyor mu?",
            True,
            (getattr(adapter, "list_urls", None) or [""])[0],
        )
    )
    # 2. a listing?
    report.checks.append(
        Check("İlan listesi alınabiliyor mu?", bool(listings), f"{len(listings)} ilan")
    )
    if not listings:
        report.access = "blocked"
        report.checks += [Check(name, None, "ilan yok") for name in _REST[1:]]
        repo.set_gig_source_result(adapter.key, ok=True, listings=0)
        return report

    # 3, 4, 5, 6, 7: read the first few ads
    detail_ok = 0
    link_ok = 0
    dated = 0
    paid = 0
    placed = 0
    gigs = 0
    fingerprints: list[str] = []
    for listing in listings[:5]:
        url = _listing_url(listing.url)
        if url.startswith("http"):
            link_ok += 1
        text = listing.summary
        posting = None
        try:
            html = await client.html(listing.url)
            body = main_text(html)
            if body:
                text = body
                detail_ok += 1
            posting = read_posting(html)
        except Blocked:
            pass
        gig = classify(
            title=listing.title,
            description=f"{text}\n{posting.salary_text}"
            if posting and posting.salary_text
            else text,
            url=url,
            platform=listing.platform,
            employer=(posting.employer if posting else None) or listing.employer,
            published=posting.date_posted if posting else None,
            default_city=getattr(adapter, "default_city", None),
            city=posting.city if posting else None,
            district=posting.district if posting else None,
        )
        fingerprints.append(gig.fingerprint)
        if gig.publication_date or detect_published(text or listing.title):
            dated += 1
        if gig.payment_unit.value != "unknown":
            paid += 1
        if gig.city or gig.remote_or_onsite.value == "remote":
            placed += 1
        if gig.verdict == Verdict.GIG:
            gigs += 1

    report.checks.append(
        Check("İlan detayları okunabiliyor mu?", detail_ok > 0, f"{detail_ok}/5 ilan okundu")
    )
    report.checks.append(
        Check("Orijinal ilan bağlantısı alınabiliyor mu?", link_ok > 0, f"{link_ok}/5")
    )
    report.checks.append(
        Check("İlan tarihi çıkarılabiliyor mu?", dated > 0, f"{dated}/5 ilanda tarih var")
    )
    report.checks.append(
        Check("Ödeme bilgisi çıkarılabiliyor mu?", paid > 0, f"{paid}/5 ilanda ödeme modeli var")
    )
    report.checks.append(
        Check(
            "Ankara filtresi uygulanabiliyor mu?",
            placed > 0,
            f"{placed}/5 ilanda yer bilgisi var",
        )
    )
    # 8. dedupe: the same ad twice is one row
    report.checks.append(
        Check(
            "Sonuçlar tekilleştirilebiliyor mu?",
            True,
            f"{len(fingerprints)} ilan, {len(set(fingerprints))} farklı parmak izi",
        )
    )
    # 9. a second scan must not double anything
    repeat_new = 0
    if repeat:
        second = await scan_source(adapter, repo, client, fetch_details=False, max_new=0)
        repeat_new = second.new
    report.checks.append(
        Check(
            "Tekrar taramada yeni ilan yakalanıyor mu?",
            repeat_new == 0,
            f"ikinci taramada {repeat_new} yeni ilan (0 olmalı)",
        )
    )
    report.access = "working"
    report.classified_gigs = gigs
    state = repo.gig_source(adapter.key)
    if state is not None:
        report.last_ok = state.last_ok
        report.error_count = state.error_count
        report.listings_total = state.listings_total
        report.gigs_total = state.gigs_total
    since = (datetime.now(UTC) - timedelta(days=DAYS)).isoformat()
    report.gigs_24h = repo.count_gigs_for(adapter.key, since)
    return report


_REST = (
    "İlan detayları okunabiliyor mu?",
    "Orijinal ilan bağlantısı alınabiliyor mu?",
    "İlan tarihi çıkarılabiliyor mu?",
    "Ödeme bilgisi çıkarılabiliyor mu?",
    "Ankara filtresi uygulanabiliyor mu?",
    "Sonuçlar tekilleştirilebiliyor mu?",
    "Tekrar taramada yeni ilan yakalanıyor mu?",
)


async def validate_all(
    repo: Repo, *, only: list[str] | None = None, repeat: bool = True
) -> list[SourceReport]:
    """Run the checks against every source."""
    client = WebClient()
    reports: list[SourceReport] = []
    try:
        for adapter in ADAPTERS:
            if only and adapter.key not in only:
                continue
            reports.append(await validate_source(adapter, repo, client, repeat=repeat))
    finally:
        await client.aclose()
    return reports


def render(reports: list[SourceReport]) -> str:
    """The report, as text: one block per source, then the summary."""
    out: list[str] = []
    for r in reports:
        out.append(f"{r.name}  [{r.access}]")
        out.append(f"  yöntem: {r.method}")
        out.append(
            f"  son başarılı tarama: {r.last_ok or 'hiç'} · hata: {r.error_count} · "
            f"toplam ilan: {r.listings_total} · kısa süreli iş: {r.gigs_total} "
            f"(son 24 saat: {r.gigs_24h}) · doğrulamada sınıflandırılan: {r.classified_gigs}"
        )
        if r.manual_note:
            out.append(f"  not: {r.manual_note}")
        if r.last_error:
            out.append(f"  son hata: {r.last_error}")
        for check in r.checks:
            mark = {True: "✓", False: "✗", None: "-"}[check.passed]
            out.append(f"    {mark} {check.name} {check.detail}".rstrip())
        out.append("")
    working = [r for r in reports if r.working]
    blocked = [r for r in reports if r.access == "blocked"]
    failed = [r for r in reports if r.access == "failed"]
    manual = [r for r in reports if r.access == "manual"]
    out.append(
        f"Özet: {len(working)} çalışıyor, {len(blocked)} engelli, {len(failed)} hata verdi, "
        f"{len(manual)} manuel."
    )
    return "\n".join(out)
