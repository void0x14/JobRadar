"""Every source the finder knows, in the order the brief asks for them.

The order is the development and validation order, not a filter: every source stays in the
list, and each one reports its own access status instead of pretending to work.
"""

from __future__ import annotations

from jobradar.gig.adapters import ai_data, boards_tr, digital_tr, manual, telegram_web
from jobradar.gig.adapters.base import Adapter, LinkAdapter, Listing, WebClient

_ADAPTERS: list[Adapter] = [
    boards_tr.ELEMAN,
    boards_tr.ELEMAN_GUNLUK,
    boards_tr.ISIN_OLSUN,
    telegram_web.ADAPTERS[0],
    digital_tr.R10_ILAN,
    digital_tr.UPWORK,
    ai_data.DATAFORCE,
    ai_data.ONEFORMA,
    ai_data.RWS,
    ai_data.OPENTRAIN,
    digital_tr.BIONLUK,
    digital_tr.ARMUT,
    manual.ADAPTERS[0],
    manual.ADAPTERS[1],
    boards_tr.SAHIBINDEN,
    boards_tr.KARIYER,
    boards_tr.SECRETCV,
    boards_tr.INDEED,
    boards_tr.LINKEDIN,
    boards_tr.ANKARA_BBS,
    digital_tr.R10_ARAYAN,
    digital_tr.CONTRA,
    ai_data.MINDRIFT,
    ai_data.CORPSHORE,
    ai_data.RISE,
    ai_data.TELUS,
    telegram_web.ADAPTERS[1],
    telegram_web.ADAPTERS[2],
]

ADAPTERS: list[Adapter] = list(_ADAPTERS)

__all__ = ["ADAPTERS", "Adapter", "LinkAdapter", "Listing", "WebClient"]
