"""The gig finder: what it reads, what it keeps, what it drops, and what it tells you."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import pytest

from jobradar.db.repo import Repo
from jobradar.gig import scan as scanner
from jobradar.gig import validate as validator
from jobradar.gig.adapters.base import Blocked, LinkAdapter, Listing, extract_links
from jobradar.gig.classify import (
    classify,
    detect_city_district,
    detect_eligibility,
    detect_employer,
    detect_published,
    extract_payment,
)
from jobradar.gig.models import PaymentUnit, Verdict
from jobradar.gig.notify import build_email, gig_line, notify
from jobradar.gig.structured import read_posting

# ---- the classifier -------------------------------------------------------------------------


def test_a_daily_wage_is_a_gig() -> None:
    gig = classify(
        title="Temizlik Personeli - Ankara",
        description="Ankara Çankaya'da günlük 1.500 TL yevmiye ile çalışacağız.",
        url="https://x.test/1",
        platform="test",
    )
    assert gig.verdict == Verdict.GIG
    assert gig.payment_unit == PaymentUnit.DAILY
    assert gig.payment_amount == 1500
    assert gig.payment_currency == "TL"
    assert gig.city == "Ankara"
    assert gig.district == "Çankaya"
    assert gig.confidence_score >= 0.9


def test_part_time_alone_is_not_a_gig() -> None:
    """The brief: "part-time" by itself says nothing about the payment."""
    gig = classify(
        title="Part-Time Kasiyer",
        description="Part-time kasiyer aranıyor, Ankara.",
        url="https://x.test/2",
        platform="test",
    )
    assert gig.verdict == Verdict.UNCERTAIN
    assert gig.payment_unit == PaymentUnit.UNKNOWN
    assert gig.payment_amount is None


def test_a_schedule_is_not_a_payment_model() -> None:
    """ "GÜNLÜK 8 SAAT" is when the work happens, not what it pays."""
    gig = classify(
        title="Temizlik",
        description="GÜNLÜK 8 SAAT temizlik personeli, Ankara.",
        url="https://x.test/3",
        platform="test",
    )
    assert gig.verdict == Verdict.UNCERTAIN


@pytest.mark.parametrize(
    ("text", "unit"),
    [
        ("Saatlik 200 TL çeviri işi", PaymentUnit.HOURLY),
        ("Görev başı 300 TL etiketleme", PaymentUnit.PER_TASK),
        ("Proje bazlı 5.000 TL web sitesi", PaymentUnit.PER_PROJECT),
        ("Haftalık 4.000 TL satış danışmanı", PaymentUnit.WEEKLY),
        ("Günlük 1.500 TL yevmiye", PaymentUnit.DAILY),
    ],
)
def test_every_payment_unit_is_read(text: str, unit: PaymentUnit) -> None:
    amount, currency, found, _ = extract_payment(text)
    assert found == unit
    assert amount and amount > 0
    assert currency == "TL"


def test_the_amount_closest_to_the_unit_word_wins() -> None:
    """ "GÜNLÜK = 1.282,09 TL" then a note about 110 TL: the first one is the wage."""
    amount, _, unit, _ = extract_payment(
        "GÜNLÜK = 1.282,09 TL. NOT: GÜNLÜK ÜCRET ÜZERİNDEN 110 TL EKİMDE BAŞLAYANLAR ALAMAZ."
    )
    assert unit == PaymentUnit.DAILY
    assert amount == 1282.09


@pytest.mark.parametrize(
    ("text", "amount"),
    [("1.500 TL", 1500.0), ("1,500 TL", 1500.0), ("45.000 TL", 45000.0), ("300 TL", 300.0)],
)
def test_thousand_separators(text: str, amount: float) -> None:
    assert extract_payment(f"günlük {text}")[0] == amount


def test_monthly_only_work_is_excluded() -> None:
    gig = classify(
        title="Muhasebeci",
        description="Aylık 45.000 TL maaşlı muhasebeci aranıyor.",
        url="https://x.test/4",
        platform="test",
    )
    assert gig.verdict == Verdict.EXCLUDED
    assert "monthly" in " ".join(gig.reasons)


def test_full_time_work_is_excluded() -> None:
    gig = classify(
        title="Satış Temsilcisi",
        description="Tam zamanlı satış temsilcisi, haftalık 30.000 TL.",
        url="https://x.test/5",
        platform="test",
    )
    assert gig.verdict == Verdict.EXCLUDED


def test_heavy_lifting_is_excluded() -> None:
    gig = classify(
        title="Depo Elemanı",
        description="Günlük 1.000 TL yevmiye, 30 kg yük taşıma.",
        url="https://x.test/6",
        platform="test",
    )
    assert gig.verdict == Verdict.EXCLUDED
    assert any("heavy" in reason for reason in gig.reasons)


def test_work_outside_ankara_is_excluded_unless_it_is_remote() -> None:
    onsite = classify(
        title="Kasiyer",
        description="Günlük 900 TL yevmiye, İstanbul Kadıköy.",
        url="https://x.test/7",
        platform="test",
    )
    assert onsite.verdict == Verdict.EXCLUDED
    remote = classify(
        title="Kasiyer",
        description="Günlük 900 TL yevmiye, uzaktan çalışma.",
        url="https://x.test/8",
        platform="test",
    )
    assert remote.verdict == Verdict.GIG
    assert remote.remote_or_onsite.value == "remote"


def test_a_listing_filed_under_ankara_keeps_that_city() -> None:
    gig = classify(
        title="Depo elemanı",
        description="Günlük 1.000 TL.",
        url="https://x.test/9",
        platform="test",
        default_city="Ankara",
    )
    assert gig.city == "Ankara"
    assert gig.verdict == Verdict.GIG


def test_the_date_is_read_in_its_forms() -> None:
    assert detect_published("İlan tarihi: 12.10.2026") == datetime(2026, 10, 12)
    assert detect_published("12 Ekim 2026") == datetime(2026, 10, 12)
    now = datetime(2026, 10, 20)
    assert detect_published("3 gün önce", now) == datetime(2026, 10, 17)
    assert detect_published("dün", now) == datetime(2026, 10, 19)
    # A number that is not a date is not a date.
    assert detect_published("2018 numaralı başvuru", now) is None


def test_the_employer_and_the_place_are_read() -> None:
    assert detect_employer("Firma: Bofor Lojistik İstanbul") == "Bofor Lojistik İstanbul"
    assert detect_city_district("Ankara Yenimahalle ilanı") == ("Ankara", "Yenimahalle")
    assert detect_city_district("İzmir ilanı") == ("İzmir", None)


def test_who_can_take_the_job_is_read() -> None:
    assert detect_eligibility("19-40 YAŞ ARASI SGK") == "19-40 yaş"
    assert detect_eligibility("Son sınıf öğrenciler bekleniyor") == "son sınıf öğrenci"
    assert detect_eligibility("En az 3 yıl deneyim şart") == "en az 3 yıl deneyim"
    assert detect_eligibility("Temizlik elemanı") is None


# ---- the adapters ----------------------------------------------------------------------------


def test_links_are_read_out_of_the_page() -> None:
    html = '<a href="/is-ilani/temizlik-i1">Temizlik Elemanı</a><a href="/x">Başka</a>'
    links = extract_links(html, "https://site.test/list")
    assert ("https://site.test/is-ilani/temizlik-i1", "Temizlik Elemanı") in links


def _page(body: str) -> str:
    """A tiny HTML page, the way a board serves an ad."""
    return f"<html><body><p>{body}</p></body></html>"


class FakeClient:
    """A client that answers from a dictionary instead of the network."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    async def html(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise Blocked(f"{url} answered 404")
        return self.pages[url]

    async def text(self, url: str) -> str:
        return self.pages.get(url, "")


async def test_a_link_adapter_keeps_only_the_ad_links() -> None:
    adapter = LinkAdapter(
        key="test",
        name="Test",
        platform="test",
        list_urls=["https://site.test/list"],
        pattern=r"site\.test/is-ilani/",
    )
    client = FakeClient(
        {
            "https://site.test/list": (
                '<a href="/is-ilani/bir-i1">Bir İlan</a><a href="/kategori">Kategori</a>'
            )
        }
    )
    listings = await adapter.scan(client)  # type: ignore[arg-type]
    assert [item.url for item in listings] == ["https://site.test/is-ilani/bir-i1"]
    assert listings[0].title == "Bir İlan"


async def test_a_blocked_source_is_reported_not_hidden(repo: Repo) -> None:
    adapter = LinkAdapter(
        key="blocked",
        name="Engelli",
        platform="test",
        list_urls=["https://site.test/list"],
        pattern=r"site\.test/is-ilani/",
    )
    client = FakeClient({})
    result = await scanner.scan_source(adapter, repo, client)  # type: ignore[arg-type]
    assert result.ok is False
    assert result.error and "404" in result.error
    state = repo.gig_source("blocked")
    assert state is not None and state.error_count == 1 and state.last_ok is None


async def test_one_dead_listing_page_does_not_take_the_source_down() -> None:
    adapter = LinkAdapter(
        key="test",
        name="Test",
        platform="test",
        list_urls=["https://site.test/dead", "https://site.test/list"],
        pattern=r"site\.test/is-ilani/",
        max_pages=2,
    )
    client = FakeClient({"https://site.test/list": '<a href="/is-ilani/bir-i1">Bir İlan</a>'})
    listings = await adapter.scan(client)  # type: ignore[arg-type]
    assert [item.url for item in listings] == ["https://site.test/is-ilani/bir-i1"]


# ---- the scan --------------------------------------------------------------------------------


class FakeAdapter:
    """One source with two ads, one of them a daily wage."""

    key = "fake"
    name = "Sahte Kaynak"
    platform = "fake"
    manual = False
    note = ""

    def __init__(self) -> None:
        self.list_urls = ["https://fake.test/list"]

    async def scan(self, client: FakeClient) -> list[Listing]:
        return [
            Listing(
                url="https://fake.test/is-ilani/gunluk-i1",
                title="Günlük 1.500 TL yevmiye elemanı",
                platform="fake",
                source_key="fake",
            ),
            Listing(
                url="https://fake.test/is-ilani/part-time-i2",
                title="Part-Time Kasiyer",
                platform="fake",
                source_key="fake",
            ),
        ]


async def test_a_scan_stores_the_gigs_and_leaves_the_rest_uncertain(
    repo: Repo,
) -> None:
    client = FakeClient(
        {
            "https://fake.test/is-ilani/gunluk-i1": _page(
                "Ankara Çankaya günlük 1.500 TL yevmiye."
            ),
            "https://fake.test/is-ilani/part-time-i2": _page("Part-time kasiyer, Ankara."),
        }
    )
    adapter = FakeAdapter()
    result = await scanner.scan_source(adapter, repo, client)  # type: ignore[arg-type]
    assert result.ok is True
    assert result.listings == 2 and result.new == 2
    assert result.gigs == 1
    assert repo.count_gigs("gig") == 1
    assert repo.count_gigs("uncertain") == 1


async def test_a_second_scan_finds_nothing_new(repo: Repo) -> None:
    client = FakeClient(
        {
            "https://fake.test/is-ilani/gunluk-i1": _page(
                "Ankara Çankaya günlük 1.500 TL yevmiye."
            ),
            "https://fake.test/is-ilani/part-time-i2": _page("Part-time kasiyer, Ankara."),
        }
    )
    adapter = FakeAdapter()
    await scanner.scan_source(adapter, repo, client)  # type: ignore[arg-type]
    again = await scanner.scan_source(adapter, repo, client)  # type: ignore[arg-type]
    assert again.new == 0
    assert repo.count_gigs("gig") == 1


async def test_the_same_ad_on_two_sites_is_one_row(repo: Repo) -> None:
    one = classify(
        title="Temizlik elemanı",
        description="Ankara günlük 1.500 TL",
        url="https://a.test/ilan",
        platform="a",
    )
    two = classify(
        title="Temizlik elemanı",
        description="Ankara günlük 1.500 TL",
        url="https://b.test/ilan",
        platform="b",
    )
    assert one.fingerprint == two.fingerprint
    job_id, is_new = repo.save_gig(one)
    assert is_new is True
    job_id_again, is_new_again = repo.save_gig(two)
    assert is_new_again is False
    assert job_id_again == job_id
    assert repo.count_gigs() == 1
    row = repo.gig_by_url("https://a.test/ilan")
    assert row is not None
    assert json.loads(row.seen_on) == ["a", "b"]


# ---- the source health -----------------------------------------------------------------------


async def test_the_source_health_is_kept(repo: Repo) -> None:
    adapter = FakeAdapter()
    client = FakeClient(
        {
            "https://fake.test/is-ilani/gunluk-i1": _page("Ankara günlük 1.500 TL"),
            "https://fake.test/is-ilani/part-time-i2": _page("Part-time, Ankara."),
        }
    )
    await scanner.scan_source(adapter, repo, client)  # type: ignore[arg-type]
    state = repo.gig_source("fake")
    assert state is not None
    assert state.last_ok is not None
    assert state.listings_total == 2
    assert state.error_count == 0


async def test_an_ad_that_is_gone_is_marked_closed(repo: Repo) -> None:
    """The ad page answered 404: the ad is closed and must not be offered again."""
    gig = classify(
        title="Günlük 1.500 TL temizlik elemanı",
        description="Ankara günlük 1.500 TL yevmiye",
        url="https://fake.test/is-ilani/kapandi-i1",
        platform="fake",
    )
    repo.save_gig(gig)
    row = repo.gig_by_url("https://fake.test/is-ilani/kapandi-i1")
    assert row is not None
    repo.mark_gig_closed(row.job_id)
    assert repo.list_gigs(verdict="gig") == []
    assert [g.job_id for g in repo.list_gigs(include_closed=True)] == [row.job_id]


async def test_an_old_ad_is_not_a_gig(repo: Repo) -> None:
    """Posted more than a month ago: old, not new."""
    page = (
        '<html><body><script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Günlük 1.500 TL temizlik elemanı",
                "datePosted": "2026-08-01 09:00:00",
                "description": "Ankara günlük 1.500 TL yevmiye",
            }
        )
        + "</script></body></html>"
    )
    client = FakeClient({"https://fake.test/is-ilani/eski-i1": page})

    class OneAdapter:
        key = "fake"
        name = "Sahte Kaynak"
        platform = "fake"
        manual = False
        note = ""
        list_urls: ClassVar[list[str]] = ["https://fake.test/list"]

        async def scan(self, client: FakeClient) -> list[Listing]:
            return [
                Listing(
                    url="https://fake.test/is-ilani/eski-i1",
                    title="Günlük 1.500 TL temizlik elemanı",
                    platform="fake",
                    source_key="fake",
                )
            ]

    result = await scanner.scan_source(OneAdapter(), repo, client)  # type: ignore[arg-type]
    assert result.gigs == 0
    row = repo.gig_by_url("https://fake.test/is-ilani/eski-i1")
    assert row is not None and row.verdict == "excluded"
    assert "old ad" in row.reasons


# ---- the structured data ---------------------------------------------------------------------


def test_the_pages_own_job_posting_is_used() -> None:
    html = (
        """<script type="application/ld+json">"""
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Günlük Depo Elemanı",
                "datePosted": "2026-10-30 13:03:25",
                "validThrough": "2026-11-27",
                "employmentType": "Part Time",
                "hiringOrganization": {"@type": "Organization", "name": "Bofor Lojistik"},
                "jobLocation": {
                    "@type": "Place",
                    "address": {"addressLocality": "Ankara", "addressRegion": "Çankaya"},
                },
                "description": "<p>GÜNLÜK = 1.282,09 TL</p>",
                "baseSalary": {"@type": "MonetaryAmount", "currency": "TRY", "value": 1282.09},
            }
        )
        + """</script>"""
    )
    posting = read_posting(html)
    assert posting is not None
    assert posting.employer == "Bofor Lojistik"
    assert posting.city == "Ankara" and posting.district == "Çankaya"
    assert posting.date_posted == datetime(2026, 10, 30, 13, 3, 25)
    assert posting.employment_type == "Part Time"
    assert posting.salary_text and "1282.09" in posting.salary_text
    assert posting.description and "GÜNLÜK" in posting.description


# ---- the report and the notification ---------------------------------------------------------


async def test_the_validation_report_says_what_each_source_can_do(repo: Repo) -> None:
    adapter = FakeAdapter()
    client = FakeClient(
        {
            "https://fake.test/is-ilani/gunluk-i1": _page("Ankara günlük 1.500 TL yevmiye."),
            "https://fake.test/is-ilani/part-time-i2": _page("Part-time kasiyer, Ankara."),
        }
    )
    report = await validator.validate_source(adapter, repo, client)  # type: ignore[arg-type]
    assert report.access == "working"
    assert report.passed >= 6
    # The only thing these fake ads do not say is when they were posted.
    assert [c.name for c in report.checks if c.passed is False] == [
        "İlan tarihi çıkarılabiliyor mu?"
    ]
    text = validator.render([report])
    assert "Sahte Kaynak" in text and "çalışıyor" in text


async def test_a_manual_source_is_reported_as_manual(repo: Repo) -> None:
    from jobradar.gig.adapters.manual import ManualAdapter

    adapter = ManualAdapter(key="facebook", name="Facebook", platform="facebook")
    report = await validator.validate_source(adapter, repo, FakeClient({}))  # type: ignore[arg-type]
    assert report.access == "manual"
    assert all(check.passed is None for check in report.checks)


def test_the_notification_carries_the_pay_and_the_link(repo: Repo) -> None:
    gig = classify(
        title="Günlük 1.500 TL temizlik elemanı",
        description="Ankara Çankaya günlük 1.500 TL yevmiye",
        url="https://x.test/ilan",
        platform="test",
    )
    repo.save_gig(gig)
    row = repo.gig_by_url("https://x.test/ilan")
    assert row is not None
    line = gig_line(row)
    assert "1500" in line and "Ankara" in line
    msg = build_email([row], "me@x.com", "me@x.com")
    plain = str(msg.get_body(("plain",)).get_content())
    assert "https://x.test/ilan" in plain
    assert "1500" in plain


def test_the_notification_is_saved_in_dry_run(repo: Repo, tmp_path: Path) -> None:
    from jobradar.config import AppConfig, Secrets, Settings

    gig = classify(
        title="Günlük 1.500 TL temizlik elemanı",
        description="Ankara günlük 1.500 TL yevmiye",
        url="https://x.test/ilan",
        platform="test",
    )
    repo.save_gig(gig)
    row = repo.gig_by_url("https://x.test/ilan")
    assert row is not None
    settings = Settings(
        config=AppConfig.model_validate({"sources": {"telegram": {"enabled": False}}}),
        secrets=Secrets(),
    )
    outcome = notify(settings, [row], preview_dir=tmp_path)
    assert "dry run" in outcome
    assert list(tmp_path.glob("gigs-*.html"))


def test_an_ad_brought_in_by_hand_is_judged_the_same_way(repo: Repo) -> None:
    """Facebook and WhatsApp groups are not scraped: their ads come in by hand."""
    from jobradar.gig.ingest import add_gig

    gig, is_new = add_gig(
        repo,
        "Günlük 1.500 TL yevmiye ile Ankara Çankaya'da temizlik personeli aranıyor.",
        platform="facebook",
        source_key="facebook",
    )
    assert is_new is True
    assert gig.verdict == Verdict.GIG
    assert gig.payment_amount == 1500 and gig.payment_unit == PaymentUnit.DAILY
    assert gig.city == "Ankara"
    row = repo.gig_by_url(gig.original_url)
    assert row is not None and row.source_key == "facebook"
    # The same ad pasted twice is one row.
    again, is_new_again = add_gig(
        repo,
        "Günlük 1.500 TL yevmiye ile Ankara Çankaya'da temizlik personeli aranıyor.",
        platform="facebook",
        source_key="facebook",
    )
    assert is_new_again is False
    assert again.job_id == gig.job_id
    assert repo.count_gigs() == 1
