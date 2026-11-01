"""AI, data and micro-task platforms: the ones that pay per task or per project."""

from __future__ import annotations

from jobradar.gig.adapters.base import LinkAdapter

ONEFORMA = LinkAdapter(
    key="oneforma",
    name="OneForma (open projects)",
    platform="oneforma",
    list_urls=["https://www.oneforma.com/projects/"],
    pattern=r"oneforma\.com/projects/[^/]+/",
)

DATAFORCE = LinkAdapter(
    key="dataforce",
    name="DataForce Community (projects)",
    platform="dataforce",
    list_urls=["https://dataforcecommunity.transperfect.com/projects"],
    pattern=r"dataforcecommunity\.transperfect\.com/project/[^/]+",
)

OPENTRAIN = LinkAdapter(
    key="opentrain",
    name="OpenTrain AI (Türkiye jobs)",
    platform="opentrain",
    list_urls=["https://www.opentrain.ai/jobs/country/turkiye/"],
    pattern=r"opentrain\.ai/jobs/[^/]+/",
)

MINDRIFT = LinkAdapter(
    key="mindrift",
    name="Mindrift (annotation projects)",
    platform="mindrift",
    list_urls=["https://mindrift.ai/project/annotation"],
    pattern=r"mindrift\.ai/project/[^/]+",
)

CORPSHORE = LinkAdapter(
    key="corpshore",
    name="Corpshore (Türkiye)",
    platform="corpshore",
    list_urls=["https://platform.corpshore.ai/turkiye"],
    pattern=r"corpshore\.ai/(?:project|job|task)/[^/]+",
    note="The list is rendered with JavaScript.",
)

RISE = LinkAdapter(
    key="rise",
    name="Rise Data Labs (remote AI jobs)",
    platform="rise",
    list_urls=["https://experts.risedatalabs.com/jobs"],
    pattern=r"risedatalabs\.com/(?:jobs|job)/[^/]+",
    note="The list is rendered with JavaScript.",
)

TELUS = LinkAdapter(
    key="telus",
    name="TELUS Digital (careers)",
    platform="telus",
    list_urls=["https://www.telusdigital.com/careers"],
    pattern=r"telusdigital\.com/careers/",
    note="Answers a Cloudflare block page.",
)

RWS = LinkAdapter(
    key="rws",
    name="RWS TrainAI",
    platform="rws",
    list_urls=["https://www.rws.com/artificial-intelligence/train-ai/"],
    pattern=r"rws\.com/artificial-intelligence/[^/]+",
    note="The page answers 404; RWS moved the programme.",
)

ADAPTERS = [
    ONEFORMA,
    DATAFORCE,
    OPENTRAIN,
    MINDRIFT,
    CORPSHORE,
    RISE,
    TELUS,
    RWS,
]
