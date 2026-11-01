"""Tell the moment a new gig appears: one email with the new jobs in it.

Same manners as the rest of JobRadar: it goes to one address (NOTIFY_TO or EMAIL_ADDRESS),
nothing is sent in dry run (the email is saved as a preview instead), and it never carries
more than the title, the employer, the pay, the place and the link.
"""

from __future__ import annotations

import logging
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from jobradar.config import Settings
from jobradar.db.models import GigRow
from jobradar.sinks.email_notify import PREVIEW_DIR, save_preview, smtp_send
from jobradar.sinks.email_template import esc, layout

log = logging.getLogger(__name__)

PREVIEW_PREFIX = "gigs-"


def gig_line(gig: GigRow) -> str:
    """One line about a gig: what it is, what it pays, where, and when."""
    bits = [gig.job_title.strip()[:120]]
    if gig.employer:
        bits.append(gig.employer.strip()[:60])
    if gig.payment_amount is not None:
        unit = {
            "daily": "/gün",
            "hourly": "/saat",
            "per_task": "/görev",
            "per_project": "/proje",
            "weekly": "/hafta",
            "monthly": "/ay",
        }.get(gig.payment_unit, "")
        money = f"{gig.payment_amount:g} {gig.payment_currency or ''}".strip()
        bits.append(f"{money}{unit}".strip())
    place = " · ".join(p for p in (gig.city, gig.district) if p)
    if place:
        bits.append(place)
    if gig.remote_or_onsite == "remote":
        bits.append("uzaktan")
    if gig.work_duration:
        bits.append(gig.work_duration)
    if gig.publication_date:
        bits.append(gig.publication_date[:10])
    return " · ".join(b for b in bits if b)


def build_email(gigs: list[GigRow], sender: str, to: str) -> EmailMessage:
    """The email: the new gigs, one per line, with the link."""
    lines = [gig_line(g) for g in gigs]
    links = [g.original_url for g in gigs]
    subject = (
        f"[JobRadar] {len(gigs)} yeni kısa süreli iş"
        if len(gigs) > 1
        else f"[JobRadar] Yeni kısa süreli iş: {gigs[0].job_title.strip()[:60]}"
    )
    rows = "".join(
        f"<tr><td style='padding:10px 0;border-top:1px solid #e3e6ea;font-size:14px'>"
        f"<a href='{esc(url)}' style='color:#1a56db;font-weight:700'>{esc(line)}</a>"
        f"<div style='color:#59636e;font-size:12px;margin-top:2px'>{esc(url)}</div></td></tr>"
        for line, url in zip(lines, links, strict=True)
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(
        f"{len(gigs)} yeni kısa süreli iş bulundu:\n\n"
        + "\n".join(f"{line}\n{url}" for line, url in zip(lines, links, strict=True))
        + "\n\n— JobRadar\n"
    )
    footer = (
        "JobRadar yalnızca günlük, saatlik, görev ve proje başına ödeme yapan işleri "
        "bildirir. İlanı gönderen senin; başvurmak senin işin."
    )
    msg.add_alternative(
        layout(
            "JobRadar",
            f"{len(gigs)} yeni kısa süreli iş",
            "Hemen açılabilir, günlük veya görev bazlı ödemeyle.",
            subject.removeprefix("[JobRadar] "),
            rows,
            footer,
        ),
        subtype="html",
    )
    return msg


def notify(
    settings: Settings,
    gigs: list[GigRow],
    *,
    preview_dir: Path = PREVIEW_DIR,
    now: datetime | None = None,
) -> str:
    """Send (or preview) the new gigs. Returns what happened."""
    if not gigs:
        return "nothing new"
    secrets = settings.secrets
    sender = secrets.email_address or "jobradar@localhost"
    to = secrets.notify_address or sender
    msg = build_email(gigs, sender, to)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    if settings.config.notify.dry_run:
        path = save_preview(msg, preview_dir / f"{PREVIEW_PREFIX}{stamp}.html")
        log.info("dry run: gig alert saved", extra={"preview": str(path)})
        return f"dry run: saved {path}"
    smtp_send(settings, msg)
    log.info("gig alert sent", extra={"gigs": len(gigs)})
    return f"sent {len(gigs)} gig(s)"
