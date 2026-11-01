"""Decide what a listing is: a gig, an uncertain one, or something we don't want.

The rules are written for Turkish job posts (with the English words the same sites use).
Three things the brief insists on:

- the payment model is read from the text, never from "part-time" alone;
- a listing that says nothing about pay is *uncertain*, not a gig;
- full-time, monthly-only and heavy-lifting work is out.

Nothing here guesses: an amount that isn't there stays None, a unit that isn't stated stays
UNKNOWN.
"""

from __future__ import annotations

import re
from datetime import datetime

from jobradar.gig.models import (
    Effort,
    Gig,
    PaymentFrequency,
    PaymentUnit,
    Verdict,
    WorkMode,
)
from jobradar.pipeline.dedupe import sha1

# ---- payment words ----------------------------------------------------------------------------

_UNIT_WORDS: list[tuple[PaymentUnit, str]] = [
    (
        PaymentUnit.PER_TASK,
        r"görev\s+(?:başı|başına|bazlı)|task\s*(?:başı|başına|bazlı)|"
        r"adet\s+başı|iş\s+başına|sipariş\s+başı|her\s+görev|per\s+task|"
        r"tek\s+seferlik|bir\s+kerelik|/\s*görev",
    ),
    (
        PaymentUnit.PER_PROJECT,
        r"proje\s+(?:bazlı|başına|başinde)|per\s+project|projeli|"
        r"teslimata\s+göre|teslim\s+edilecek|/\s*proje",
    ),
    (
        PaymentUnit.HOURLY,
        r"saatlik|saat\s+başı|saat\s+başına|saat\s+ücreti|hourly|"
        r"per\s+hour|per\s+saat|/\s*saat|saatde|/\s*hour\b",
    ),
    (
        PaymentUnit.DAILY,
        r"günlük(?!çü)|gün\s+başı|gün\s+başına|gün\s+bazlı|günlükmü|yevmiye|"
        r"daily|per\s+day|/\s*gün",
    ),
    (PaymentUnit.WEEKLY, r"haftalık|hafta\s+başı|hafta\s+başına|weekly|per\s+week|/\s*hafta"),
    (PaymentUnit.MONTHLY, r"aylık|ay\s+başı|ay\s+bazlı|maaş|salary|per\s+month"),
]
_UNIT_RE = [(unit, re.compile(pattern, re.IGNORECASE)) for unit, pattern in _UNIT_WORDS]

# The unit has to sit near the amount, otherwise "günlük 30 kişi" would read as a daily rate.
_AMOUNT_RE = re.compile(
    r"(?P<amount>\d[\d.,]*)\s*(?P<currency>TL|TRY|₺|USD|\$|EUR|€)?",
    re.IGNORECASE,
)
_CURRENCY_NAMES = {
    "tl": "TL",
    "try": "TL",
    "₺": "TL",
    "usd": "USD",
    "$": "USD",
    "eur": "EUR",
    "€": "EUR",
}

# ---- exclusion words --------------------------------------------------------------------------

_FULL_TIME = re.compile(
    r"tam\s+zamanlı|full[\s-]?time|sürekli\s+çalış|kadrolu|permanent",
    re.IGNORECASE,
)
_HEAVY = re.compile(
    r"(\d{1,3})\s*kg|kg\s*(?:ağırlığında|taşıma|taşınacak)|ağır\s+fiziksel|ağır\s+iş|"
    r"yük\s+taşıma|vinç|şantiye|inşaat\s+işçisi|forklift",
    re.IGNORECASE,
)
_LIGHT_HINT = re.compile(
    r"ofis|bilgisayar\s+başında|müşteri\s+iletişimi|veri\s+girişi|içerik|yazı|çeviri|"
    r"etiketleme|düzenleme|montaj|denetim",
    re.IGNORECASE,
)

# ---- place, mode, duration --------------------------------------------------------------------

_ANKARA_DISTRICTS = (
    "Çankaya",
    "Keçiören",
    "Yenimahalle",
    "Etimesgut",
    "Mamak",
    "Sincan",
    "Altındağ",
    "Gölbaşı",
    "Pursaklar",
    "Akyurt",
    "Polatlı",
    "Beypazarı",
    "Şereflikoçluğlu",
    "Kızılay",
    "Ulus",
    "Balgat",
    "Dumlupınar",
    "Ostim",
    "Batıkent",
)
_OTHER_CITIES = (
    "İstanbul",
    "Istanbul",
    "İzmir",
    "Izmir",
    "Bursa",
    "Antalya",
    "Adana",
    "Konya",
    "Kocaeli",
    "Eskişehir",
    "Gaziantep",
    "Diyarbakır",
    "Samsun",
    "Denizli",
    "Kayseri",
    "Trabzon",
)
_REMOTE = re.compile(
    r"uzaktan|remote|online\s+(?:çalışma|iş|işe)|dijital\s+çalış|home\s*office|evden",
    re.IGNORECASE,
)
_ONSITE = re.compile(r"ofisten|yerinde|şirket\s+içinde|site\s+çalış", re.IGNORECASE)

_DURATION = re.compile(
    r"(?P<text>(?:tek\s+gün|1\s+gün|bir\s+gün|birkaç\s+gün|\d{1,2}\s+g(?:ün|ecek)?|"
    r"\d{1,2}\s+hafta|\d{1,2}\s+ay|yarı\s+gün))",
    re.IGNORECASE,
)
_HOURS = re.compile(r"(?P<text>\d{1,2}\s*(?:saat|hours?))", re.IGNORECASE)

_TIMING = re.compile(
    r"(?P<text>gün\s+sonunda|hafta\s+sonunda|ay\s+sonunda|iş\s+bitince|teslim(?:at|atta|"
    r"attan)\s*(?:sonra)?|ödeme\s+\w+)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+90|0)?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}(?!\d)")

_SKILLS = (
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "vue",
    "angular",
    "node",
    "php",
    "c#",
    "c++",
    "go",
    "rust",
    "kotlin",
    "swift",
    "sql",
    "excel",
    "word",
    "powerpoint",
    "photoshop",
    "illustrator",
    "figma",
    "canva",
    "video",
    "youtube",
    "sosyal medya",
    "muhasebe",
    "nakliye",
    "e-irsaliye",
    "iletişim",
    "telefon",
    "pazarlama",
    "satış",
    "müşteri",
    "ehliyet",
    "kaynak",
    "montaj",
    "paketleme",
    "depo",
    "temizlik",
    "garson",
    "kasiyer",
    "reception",
    "üretim",
    "inşaat",
    "makine",
    "çeviri",
    "translasyon",
    "veri",
    "etiketleme",
    "test",
    "yazılım",
    "tasarım",
)

_ANCHOR_HINTS = (
    "başvur",
    "başvuru",
    "iş başvurusu",
    "başvur formu",
    "apply",
    "whatsapp",
    "linkedin",
    "e-posta gönder",
    "mesaj at",
    "iletişime geç",
)

# "GÜNLÜK 8 SAAT" or "haftada 3 gün" is a work schedule, not a payment model. When the unit
# word sits next to hours or days, it says when the work happens, not what it pays.
_SCHEDULE = re.compile(r"\d{1,2}\s*saat|haftada\s*\d|günde\s*\d|çalışma\s+saat", re.IGNORECASE)

# The ad body ends where the site's own text starts. These markers are the boilerplate the
# job boards print under every ad; keeping it would feed the classifier words that are not
# about the job.
_BOILERPLATE = (
    "İlana başvuru yapabilmeniz için",
    "İlana başvurabilmeniz için",
    "Eleman arıyorsanız iş ilanı ver",
    "Bu ilana benzer ilan araması",
    "Aradığınız ",
    "Hemen Başvur",
    "İlan detayları",
    "Başvur formu",
    "İş ilanı ver",
    "Şirket ilanları",
)


def clean_ad_text(text: str) -> str:
    """The ad's own text, without the site's boilerplate under it."""
    cut = len(text)
    for marker in _BOILERPLATE:
        at = text.find(marker)
        if 0 <= at < cut:
            cut = at
    return text[:cut].strip()


def _number(text: str) -> float | None:
    """ "1.500" and "1,500" are fifteen hundred; "500,50" is five hundred and a half."""
    raw = text.replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")  # 1.500,50
    elif raw.count(",") == 1 and len(raw.split(",")[1]) == 3:
        raw = raw.replace(",", "")  # 1,500
    elif raw.count(".") == 1 and len(raw.split(".")[1]) == 3:
        raw = raw.replace(".", "")  # 1.500
    try:
        return float(raw)
    except ValueError:
        return None


def extract_payment(text: str) -> tuple[float | None, str | None, PaymentUnit, PaymentFrequency]:
    """(amount, currency, unit, frequency) from a listing's text. Amount and currency stay
    None when the text doesn't state them; the unit stays UNKNOWN when it doesn't say."""
    unit = PaymentUnit.UNKNOWN
    unit_at = -1
    unit_end = -1
    for candidate, pattern in _UNIT_RE:
        found = pattern.search(text)
        if found and (unit_at < 0 or found.start() < unit_at):
            unit, unit_at, unit_end = candidate, found.start(), found.end()
    if unit_at >= 0 and _SCHEDULE.search(text[max(0, unit_at - 30) : unit_end + 40]):
        unit, unit_at, unit_end = PaymentUnit.UNKNOWN, -1, -1

    amount: float | None = None
    currency: str | None = None
    if unit_at >= 0:
        # The amount has to be near the unit word: "3 kişi" is not a rate. The closest
        # number wins, and one that carries a currency beats one that doesn't.
        start = max(0, unit_at - 60)
        window = text[start : unit_at + 60]
        best: tuple[tuple[int, float], float, str | None] | None = None
        for found in _AMOUNT_RE.finditer(window):
            value = _number(found.group("amount"))
            if value is None or value <= 0 or value > 1_000_000:
                continue
            money = _CURRENCY_NAMES.get((found.group("currency") or "").lower())
            distance = abs(found.start() - (unit_end - start))
            score = (0 if money else 1, distance)
            if best is None or score < best[0]:
                best = (score, value, money)
        if best is not None:
            amount, currency = best[1], best[2]

    frequency = {
        PaymentUnit.DAILY: PaymentFrequency.PER_DAY,
        PaymentUnit.HOURLY: PaymentFrequency.PER_DAY,
        PaymentUnit.WEEKLY: PaymentFrequency.PER_WEEK,
        PaymentUnit.MONTHLY: PaymentFrequency.PER_MONTH,
        PaymentUnit.PER_TASK: PaymentFrequency.ONCE,
        PaymentUnit.PER_PROJECT: PaymentFrequency.ONCE,
    }.get(unit, PaymentFrequency.UNKNOWN)
    return amount, currency, unit, frequency


def detect_effort(text: str) -> Effort:
    if _HEAVY.search(text):
        return Effort.HEAVY
    if _LIGHT_HINT.search(text):
        return Effort.LIGHT
    return Effort.UNKNOWN


def detect_work_mode(text: str) -> WorkMode:
    if _REMOTE.search(text):
        return WorkMode.ONSITE if _ONSITE.search(text) else WorkMode.REMOTE
    if _ONSITE.search(text):
        return WorkMode.ONSITE
    return WorkMode.UNKNOWN


def detect_city_district(text: str) -> tuple[str | None, str | None]:
    district = next(
        (d for d in _ANKARA_DISTRICTS if re.search(rf"\b{re.escape(d)}\b", text, re.I)), None
    )
    if re.search(r"\bAnkara\b", text, re.I):
        return "Ankara", district
    if district:
        return "Ankara", district
    other = next((c for c in _OTHER_CITIES if re.search(rf"\b{re.escape(c)}\b", text, re.I)), None)
    return other, None


def detect_duration(text: str) -> str | None:
    found = _DURATION.search(text)
    return found.group("text").strip() if found else None


def detect_hours(text: str) -> str | None:
    found = _HOURS.search(text)
    return found.group("text").strip() if found else None


def detect_timing(text: str) -> str | None:
    found = _TIMING.search(text)
    return found.group("text").strip() if found else None


def detect_contact(text: str) -> str | None:
    mail = _EMAIL.search(text)
    if mail:
        return mail.group(0)
    phone = _PHONE.search(text)
    return phone.group(0).strip() if phone else None


def detect_application_method(text: str) -> str | None:
    low = text.casefold()
    for hint in _ANCHOR_HINTS:
        if hint in low:
            return hint
    return None


def detect_skills(text: str) -> list[str]:
    low = text.casefold()
    return [skill for skill in _SKILLS if skill in low]


def fingerprint(gig: Gig) -> str:
    """The same gig seen twice, on two sites, has one row: title, employer, pay and place."""
    parts = [
        gig.job_title.casefold().strip(),
        (gig.employer or "").casefold().strip(),
        gig.city or "",
        gig.district or "",
        f"{gig.payment_amount or 0:g}",
        str(gig.payment_unit),
    ]
    return sha1("|".join(parts))[:32]


def classify(
    *,
    title: str,
    description: str,
    url: str,
    platform: str,
    employer: str | None = None,
    published: datetime | None = None,
    job_id: str | None = None,
    default_city: str | None = None,
    city: str | None = None,
    district: str | None = None,
) -> Gig:
    """Read one listing and decide what it is. The text is the ad's title plus its body."""
    text = clean_ad_text(f"{title}\n{description}".strip())
    amount, currency, unit, frequency = extract_payment(text)
    effort = detect_effort(text)
    mode = detect_work_mode(text)
    found_city, found_district = detect_city_district(text)
    # What the page states about itself wins over what the prose seems to say.
    city = city or found_city
    district = district or found_district

    reasons: list[str] = []
    confidence = 0.0
    if unit == PaymentUnit.UNKNOWN:
        verdict = Verdict.UNCERTAIN
        reasons.append("no payment model in the text")
        confidence = 0.2
    elif unit == PaymentUnit.MONTHLY:
        verdict = Verdict.EXCLUDED
        reasons.append("monthly pay only")
        confidence = 0.7
    elif _FULL_TIME.search(text) and unit != PaymentUnit.DAILY:
        verdict = Verdict.EXCLUDED
        reasons.append("full-time")
        confidence = 0.6
    elif effort == Effort.HEAVY:
        verdict = Verdict.EXCLUDED
        reasons.append("heavy physical work")
        confidence = 0.6
    elif mode != WorkMode.REMOTE and city and city != "Ankara":
        verdict = Verdict.EXCLUDED
        reasons.append(f"on site in {city}, not Ankara and not remote")
        confidence = 0.5
    else:
        verdict = Verdict.GIG
        confidence = 0.9 if amount is not None else 0.7
        reasons.append(f"paid {unit}" + (f": {amount:g} {currency}" if amount else ""))
        if mode == WorkMode.REMOTE:
            reasons.append("remote")
        else:
            reasons.append(city or default_city or "place not stated")

    if city is None and default_city:
        # The listing itself is filed under a city (Ankara), so that is where the ad is
        # unless its text says somewhere else.
        city = default_city

    if _FULL_TIME.search(text) and verdict == Verdict.GIG:
        reasons.append("says full-time but a gig unit was found")
        confidence = min(confidence, 0.6)

    gig = Gig(
        job_id=job_id or sha1(url)[:40],
        job_title=title.strip()[:200] or "(başlıksız ilan)",
        employer=employer,
        original_url=url,
        source_platform=platform,
        city=city,
        district=district,
        remote_or_onsite=mode,
        job_description=description.strip()[:6000],
        payment_amount=amount,
        payment_currency=currency,
        payment_unit=unit,
        payment_frequency=frequency,
        payment_timing=detect_timing(text),
        work_duration=detect_duration(text),
        working_hours=detect_hours(text),
        publication_date=published,
        application_method=detect_application_method(text),
        contact_information=detect_contact(text),
        physical_effort=effort,
        required_skills=detect_skills(text),
        eligibility=None,
        confidence_score=round(confidence, 2),
        verdict=verdict,
        reasons=reasons,
        seen_on=[platform],
    )
    gig.fingerprint = fingerprint(gig)
    return gig


_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_DATE_NUM = re.compile(r"(?P<day>\d{1,2})[./\s](?P<month>\d{1,2})[./\s](?P<year>20\d{2})")
_DATE_WORDS = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>" + "|".join(_MONTHS) + r")\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)
_AGO = re.compile(r"(?P<amount>\d{1,3})\s*(?P<unit>dakika|saat|gün|hafta|ay)\s*önce", re.IGNORECASE)
_EMPLOYER = re.compile(
    r"(?:firma|şirket|company|isveren|iş\s+veren)\s*:?\s*(?P<name>[\w\d .&'()-]{2,60})",
    re.IGNORECASE,
)


def detect_published(text: str, now: datetime | None = None) -> datetime | None:
    """When the ad says it was posted: a date, a date with a month name, or "3 gün önce"."""
    base = now or datetime.now()
    found = _DATE_NUM.search(text)
    if found:
        try:
            when = datetime(
                int(found.group("year")), int(found.group("month")), int(found.group("day"))
            )
            return when if _plausible(when, base) else None
        except ValueError:
            return None
    found = _DATE_WORDS.search(text)
    if found:
        month = _MONTHS.get(found.group("month").casefold())
        if month:
            try:
                when = datetime(int(found.group("year")), month, int(found.group("day")))
                return when if _plausible(when, base) else None
            except ValueError:
                return None
    found = _AGO.search(text)
    if found:
        from datetime import timedelta

        amount = int(found.group("amount"))
        unit = found.group("unit").casefold()
        days = {"dakika": 0, "saat": 0, "gün": 1, "hafta": 7, "ay": 30}[unit]
        if unit == "dakika":
            return base - timedelta(minutes=amount)
        if unit == "saat":
            return base - timedelta(hours=amount)
        return base - timedelta(days=amount * days)
    if re.search(r"\bdün\b", text, re.IGNORECASE):
        from datetime import timedelta

        return base - timedelta(days=1)
    return None


def _plausible(when: datetime, now: datetime) -> bool:
    """A date an ad could really carry: the last two years, or next year at the latest."""
    return now.year - 2 <= when.year <= now.year + 1


def detect_employer(text: str) -> str | None:
    """The company name, when the ad states one."""
    found = _EMPLOYER.search(text)
    if found:
        name = found.group("name").strip(" .,:;-")
        if 2 < len(name) < 60:
            return name
    return None
