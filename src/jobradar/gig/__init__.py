"""Türkiye daily gig finder: find real, short-paid work and say so the moment it appears.

One adapter per source, one SQLite table, one classifier that decides what is a gig
(daily, hourly, per task, per project) and what is not, one dedupe across sources and
one notification path. Nothing here writes a CV or tracks an application.
"""

from __future__ import annotations

from jobradar.gig.models import Gig, PaymentUnit, Verdict

__all__ = ["Gig", "PaymentUnit", "Verdict"]
