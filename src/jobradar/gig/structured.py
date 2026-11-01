"""Read a job posting's own structured data (schema.org JobPosting) when the page has it.

Many boards put the ad's facts in a JSON-LD block: when it was posted, who is hiring, where,
the employment type and the salary. That is far more reliable than reading them out of the
prose, so the classifier uses it first and falls back to the text.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jobradar.pipeline.structured import description_text, find_job_posting

_TAG = re.compile(r"<[^>]+>")


@dataclass
class Posting:
    """What the page says about the ad, in its own words."""

    title: str | None = None
    employer: str | None = None
    city: str | None = None
    district: str | None = None
    description: str | None = None
    date_posted: datetime | None = None
    valid_through: datetime | None = None
    employment_type: str | None = None
    salary_text: str | None = None


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, (str, int, float)):
        text = " ".join(html_lib.unescape(str(value)).split())
        return text or None
    return None


def _when(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(fmt) + 2].rstrip(), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _place(value: Any) -> tuple[str | None, str | None]:
    """(city, district) out of a schema.org jobLocation."""
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, dict):
        return _text(value), None
    address = value.get("address")
    if not isinstance(address, dict):
        return _text(value.get("addressLocality")), None
    city = _text(address.get("addressLocality"))
    district = _text(address.get("addressRegion")) or _text(address.get("streetAddress"))
    return city, district


def read_posting(html: str) -> Posting | None:
    """The page's JobPosting, or None when it has none."""
    posting = find_job_posting(html)
    if not posting:
        return None
    city, district = _place(posting.get("jobLocation"))
    return Posting(
        title=_text(posting.get("title")),
        employer=_text(posting.get("hiringOrganization")),
        city=city,
        district=district,
        description=description_text(posting),
        date_posted=_when(posting.get("datePosted")),
        valid_through=_when(posting.get("validThrough")),
        employment_type=_text(posting.get("employmentType")),
        salary_text=_salary(posting.get("baseSalary")),
    )


def _salary(value: Any) -> str | None:
    """The salary as a phrase, when the page states one."""
    if not isinstance(value, dict):
        return _text(value)
    currency = _text(value.get("currency")) or ""
    value_obj = value.get("value")
    if isinstance(value_obj, dict):
        amount = _text(value_obj.get("value"))
        unit = _text(value_obj.get("unitText")) or ""
    else:
        amount = _text(value_obj)
        unit = ""
    if not amount:
        return None
    return " ".join(part for part in (amount, currency, unit) if part).strip() or None
