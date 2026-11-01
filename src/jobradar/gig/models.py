"""What one gig looks like, and the words the classifier works with.

The field list is the one the brief asks for: everything a gig needs to be judged,
including what is *not* known (payment amount, unit, timing stay empty rather than guessed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PaymentUnit(StrEnum):
    """How the work is paid for. Kept apart on purpose: a daily wage is not an hourly
    rate, and "part-time" on its own says nothing about either."""

    DAILY = "daily"
    HOURLY = "hourly"
    PER_TASK = "per_task"
    PER_PROJECT = "per_project"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    UNKNOWN = "unknown"  # nothing in the text says how it is paid


class PaymentFrequency(StrEnum):
    ONCE = "once"  # one task, one delivery
    PER_DAY = "per_day"
    PER_WEEK = "per_week"
    PER_MONTH = "per_month"
    UNKNOWN = "unknown"


class Verdict(StrEnum):
    """What the classifier decided about a listing."""

    GIG = "gig"  # a real short-paid job: keep it
    UNCERTAIN = "uncertain"  # no payment information: its own bucket, never counted as a gig
    EXCLUDED = "excluded"  # full-time, monthly-only, heavy lifting: not our business


class WorkMode(StrEnum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class Effort(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"  # 15-30 kg lifting and the like: excluded
    UNKNOWN = "unknown"


@dataclass
class Gig:
    """One listing, as the finder read it."""

    job_id: str
    job_title: str
    employer: str | None
    original_url: str
    source_platform: str
    source_key: str = ""  # which adapter found it
    city: str | None = None
    district: str | None = None
    remote_or_onsite: WorkMode = WorkMode.UNKNOWN
    job_description: str = ""
    payment_amount: float | None = None
    payment_currency: str | None = None
    payment_unit: PaymentUnit = PaymentUnit.UNKNOWN
    payment_frequency: PaymentFrequency = PaymentFrequency.UNKNOWN
    payment_timing: str | None = None  # "end of the day", "weekly", "on delivery"
    work_duration: str | None = None  # "one day", "3 days", "2 weeks"
    working_hours: str | None = None
    publication_date: datetime | None = None
    application_method: str | None = None
    contact_information: str | None = None
    physical_effort: Effort = Effort.UNKNOWN
    required_skills: list[str] = field(default_factory=list)
    eligibility: str | None = None
    confidence_score: float = 0.0  # 0-1: how sure the classifier is
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    verdict: Verdict = Verdict.UNCERTAIN
    reasons: list[str] = field(default_factory=list)  # why it was kept or dropped
    fingerprint: str = ""
    seen_on: list[str] = field(default_factory=list)  # every platform it was seen on

    @property
    def is_gig(self) -> bool:
        return self.verdict == Verdict.GIG

    @property
    def payment_text(self) -> str:
        """What a human would read for the pay, or "" when it isn't stated."""
        if self.payment_amount is None or self.payment_unit == PaymentUnit.UNKNOWN:
            return ""
        amount = f"{self.payment_amount:g}"
        currency = f" {self.payment_currency}" if self.payment_currency else ""
        unit = {
            PaymentUnit.DAILY: "/gün",
            PaymentUnit.HOURLY: "/saat",
            PaymentUnit.PER_TASK: "/görev",
            PaymentUnit.PER_PROJECT: "/proje",
            PaymentUnit.WEEKLY: "/hafta",
            PaymentUnit.MONTHLY: "/ay",
        }[self.payment_unit]
        return f"{amount}{currency}{unit}"
