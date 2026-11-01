import json
import re
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from jobradar.config import WebConfig
from jobradar.db.models import JobStatus, Platform
from jobradar.db.repo import Repo
from jobradar.pipeline.schemas import JobPosting
from jobradar.queue.tasks import TaskQueue
from jobradar.web import server, views
from jobradar.web.app import create_app
from jobradar.web.server import NoFreePort, free_port
from tests.conftest import FakeClock
from tests.test_digest import settings

TZ = settings().config.notify.tz


def add(repo: Repo, job_id: str, company: str = "Acme", role: str = "Software Engineer",
        score: int | None = 90, status: JobStatus = JobStatus.NEW, you: bool = False,
        **posting: Any) -> None:  # fmt: skip
    repo.get_or_create_job(job_id, f"https://acme.com/jobs/{job_id}")
    data = json.dumps({"company": company, "role": role, **posting})
    repo.save_extraction(job_id, data, company, role, posting.get("deadline"), "rules-v1",
                         JobStatus.EXTRACTED)  # fmt: skip
    repo.set_match_score(job_id, score, f"Good fit · {score} · eligible ✓ · Python ✓")
    if you:
        repo.set_user_status(job_id, status)
    else:
        repo.set_job_status(job_id, status)


# ---- what each page lists ------------------------------------------------------------------


def test_today_lists_recent_good_matches_you_havent_touched(repo: Repo, clock: FakeClock) -> None:
    add(repo, "old", score=95)
    clock.advance(4 * 86400)  # "old" is now 4 days old
    add(repo, "good", score=80)
    add(repo, "best", score=99)
    add(repo, "weak", score=60)
    add(repo, "shortlisted", score=99, status=JobStatus.SHORTLISTED, you=True)
    add(repo, "hidden", score=None, status=JobStatus.HIDDEN)
    assert [c.id for c in views.today(repo, 75, clock(), TZ)] == ["best", "good"]


def test_search_and_show(repo: Repo, clock: FakeClock) -> None:
    add(repo, "r", company="Rubrik")
    add(repo, "d", company="Acme", role="Data Engineer")
    add(repo, "p", company="100% Remote Co")
    add(repo, "h", company="Rubrik", status=JobStatus.HIDDEN)
    add(repo, "n", company="Junk", status=JobStatus.DISCARDED)
    ids = lambda show="jobs", q="": {c.id for c in views.all_jobs(repo, TZ, show, q, 1).cards}  # noqa: E731
    assert ids() == {"r", "d", "p"}  # hidden and not-a-job left out
    assert ids(q="rubrik") == {"r"} and ids(q="data eng") == {"d"}
    assert ids(q="%") == ids()  # no words in it: no search
    assert ids(q='" OR *') == set()  # operators are only words here: no error, no match
    assert ids(show="hidden") == {"h"} and ids(show="everything") == {"r", "d", "p", "h", "n"}
    assert ids(show="nonsense") == ids()


def test_pages_of_fifty(repo: Repo, clock: FakeClock) -> None:
    for n in range(55):
        add(repo, f"j{n:02}")
        clock.advance(1)
    first = views.all_jobs(repo, TZ, "jobs", "", 1)
    assert (first.total, first.pages, len(first.cards), first.cards[0].id) == (55, 2, 50, "j54")
    last = views.all_jobs(repo, TZ, "jobs", "", 99)  # past the end: the last page
    assert (last.page, [c.id for c in last.cards][-1]) == (2, "j00")


def test_job_detail(repo: Repo, clock: FakeClock) -> None:
    add(repo, "j", company="Rubrik", locations=["Pune"], work_mode="hybrid",
        experience_min=0, experience_max=1, skills_required=["Python", "SQL"],
        deadline="2026-10-24", apply_url="https://apply.acme.com/1")  # fmt: skip
    source = repo.upsert_source(Platform.TELEGRAM, "-1001234", "Freshershunt")
    assert source.id is not None
    raw, _ = repo.save_raw_message(source.id, "77", "2026-10-08T08:30:00Z", "Rubrik hiring")
    repo.add_job_source("j", raw)
    repo.set_user_status("j", JobStatus.SHORTLISTED)
    d = views.job_detail(repo, "j", TZ, clock())
    assert d is not None
    assert ("Experience", "0-1 years") in d.facts and ("Closes", "24 Oct") in d.facts
    assert d.card.place == "Pune · Hybrid" and d.apply_url == "https://apply.acme.com/1"
    assert [(s.where, s.at, s.link) for s in d.seen_in] == [
        ("Telegram · Freshershunt", "8 Oct, 14:00", "https://t.me/c/1234/77")
    ]
    assert d.history == [("Shortlisted", "8 Oct, 14:30")]  # 09:00 UTC in Asia/Kolkata
    assert views.job_detail(repo, "nope", TZ, clock()) is None


def test_blip(repo: Repo, clock: FakeClock) -> None:
    add(repo, "a", company="Rubrik", role="Backend Engineer", score=92)
    add(repo, "b", status=JobStatus.SHORTLISTED, you=True)
    cards = views.today(repo, 75, clock(), TZ)
    assert (
        views.blip_says(cards, 75)
        == "One good match waiting. The best is Backend Engineer at Rubrik, a 92."
    )
    assert views.blip_says([], 75).startswith("Nothing new scored 75+")
    assert views.greeting(clock(), TZ, "Sameer") == "Good afternoon, Sameer."  # 14:30 IST

    ov = views.overview(repo, 75, clock(), TZ, "Sameer Kumar")
    assert (ov.today, ov.active, ov.name, ov.awake) == (1, 1, "Sameer", False)
    source = repo.upsert_source(Platform.TELEGRAM, "-1001", "Chat")
    assert source.id is not None
    repo.save_raw_message(source.id, "1", "2026-10-08T08:59:00.000000Z", "hi")
    ov = views.overview(repo, 75, clock(), TZ, "Your Name")  # the example profile's name
    assert ov.awake and ov.last_read == "just now" and ov.name == ""
    clock.advance(3600)
    assert not views.overview(repo, 75, clock(), TZ, "").awake  # an hour with nothing read


def test_blips_take() -> None:
    r = views.split_reason("Strong fit · 96 · eligible ✓ · Python, SQL ✓ · missing Kafka · Pune ✓",
                           JobPosting(locations=["Pune"]))  # fmt: skip
    assert views.take(r) == (
        "Strong fit. You're eligible, Pune works and you have Python, SQL. Missing: Kafka."
    )
    assert (
        views.take(views.split_reason(None, None)) == "I couldn't read enough of this job to say."
    )
    assert views.initials("Thermo Fisher Scientific") == "TF" and views.initials("rubrik") == "RU"
    assert views.hue("Rubrik") == views.hue("rubrik")


def test_when() -> None:
    assert views.when("2026-10-19T17:41:43.000000Z", TZ) == "19 Oct, 23:11"
    assert views.when("2026-10-19T00:00:00.000000Z", TZ) == "19 Oct"  # a board's bare date
    assert views.when("not a time", TZ) == "" and views.when(None, TZ) == ""


# ---- the web app ------------------------------------------------------------------------------


@pytest.fixture
def client(repo: Repo, clock: FakeClock) -> TestClient:
    return TestClient(create_app(settings(), repo, clock), base_url="http://127.0.0.1:8080")


def test_pages_render(client: TestClient, repo: Repo) -> None:
    add(repo, "a", company="Rubrik")
    add(repo, "b", company="Acme", status=JobStatus.SHORTLISTED, you=True)
    today = client.get("/")
    assert today.status_code == 200 and "Rubrik" in today.text and "Acme" not in today.text
    assert "Acme" in client.get("/jobs?q=acme").text
    assert "Rubrik" in client.get("/jobs?q=rub").text
    job = client.get("/jobs/a")
    assert job.status_code == 200 and "https://acme.com/jobs/a" in job.text
    assert client.get("/static/app.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert '<symbol id="blip"' in today.text and "Good afternoon" in today.text


def test_the_gigs_page_shows_the_short_paid_work(client: TestClient, repo: Repo) -> None:
    from jobradar.gig.classify import classify

    gig = classify(
        title="Günlük 1.500 TL temizlik elemanı",
        description="Ankara Çankaya'da günlük 1.500 TL yevmiye ile temizlik elemanı.",
        url="https://acme.com/ilan/gunluk",
        platform="eleman",
    )
    repo.save_gig(gig)
    page = client.get("/gigs")
    assert page.status_code == 200
    assert "Günlük 1.500 TL" in page.text
    assert "1500 TL/gün" in page.text
    assert "Ankara" in page.text
    assert "https://acme.com/ilan/gunluk" in page.text
    # A job that is not a gig is not on the page.
    add(repo, "j", company="Acme")
    assert "Software Engineer @ Acme" not in client.get("/gigs").text


def test_errors_are_pages(client: TestClient) -> None:
    missing = client.get("/jobs/nope")
    assert missing.status_code == 404 and "Not found" in missing.text
    bad = client.get("/jobs?page=abc")
    assert bad.status_code == 400 and "doesn't look right" in bad.text


def test_job_text_is_escaped(client: TestClient, repo: Repo) -> None:
    add(repo, "x", company="<script>alert(1)</script>")
    body = client.get("/jobs/x").text
    assert "<script>alert(1)" not in body and "&lt;script&gt;" in body


def test_only_this_computer(client: TestClient, repo: Repo) -> None:
    # A site that points its own name at 127.0.0.1 ("DNS rebinding") gets nothing.
    assert client.get("/", headers={"host": "evil.example:8080"}).status_code == 400
    assert client.get("/", headers={"host": "localhost:8080"}).status_code == 200
    headers = client.get("/").headers
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store" and "server" not in headers


def test_never_every_network() -> None:
    with pytest.raises(ValidationError, match="Wi-Fi"):
        WebConfig(host="0.0.0.0")  # noqa: S104


def test_busy_port_takes_the_next(monkeypatch: pytest.MonkeyPatch) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        assert free_port("127.0.0.1", port) != port
        monkeypatch.setattr(server, "PORT_TRIES", 1)
        with pytest.raises(NoFreePort, match="in use"):
            free_port("127.0.0.1", port)


# ---- charts, funnel, score parts, palette ------------------------------------------------------


def test_pulse_counts_each_day(repo: Repo, clock: FakeClock) -> None:
    add(repo, "a", score=90)
    add(repo, "b", score=50)
    add(repo, "x", score=None, status=JobStatus.DISCARDED)  # not a job: not counted
    clock.advance(86400)
    add(repo, "c", score=80)
    p = views.pulse(repo, 75, clock(), TZ)
    assert len(p.days) == views.PULSE_DAYS and p.days[-1].today
    assert [(d.found, d.good) for d in p.days[-2:]] == [(2, 1), (1, 1)]
    assert (p.found, p.good, p.peak) == (3, 2, 2)


def test_sources_group_boards(repo: Repo, clock: FakeClock) -> None:
    def seen(job_id: str, platform: Platform, chat: str, title: str) -> None:
        source = repo.upsert_source(platform, chat, title)
        assert source.id is not None
        raw, _ = repo.save_raw_message(source.id, job_id, "2026-10-08T08:00:00.000000Z", "x")
        repo.add_job_source(job_id, raw)

    for n in range(3):
        add(repo, f"t{n}", score=90)
        seen(f"t{n}", Platform.TELEGRAM, "-1001", "Freshershunt")
    add(repo, "g", score=90)
    seen("g", Platform.BOARD, "greenhouse:stripe", "Greenhouse · Stripe")
    add(repo, "l", score=85)
    seen("l", Platform.BOARD, "lever:meesho", "Lever · Meesho")
    add(repo, "weak", score=40)
    seen("weak", Platform.TELEGRAM, "-1002", "Spam jobs")
    got = [(s.name, s.jobs, s.share) for s in views.sources(repo, 75, clock())]
    assert got == [("Freshershunt", 3, 100), ("Company boards", 2, 67)]


def test_breakdown_and_skills(repo: Repo) -> None:
    weights = {"skills_coverage": 0.4, "role_alignment": 0.3, "seniority_fit": 0.15,
               "location_ok": 0.15}  # fmt: skip
    answers = json.dumps({"provider": "llm", "eligible": 0.95, "skills_coverage": 0.5,
                          "role_alignment": 1.0, "confidence": 0.8})  # fmt: skip
    b = views.breakdown(answers, weights)
    assert b is not None and (b.eligible, b.confidence, b.by) == (95, 80, "AI read the whole job")
    assert [(p.name, p.value, p.weight) for p in b.parts] == [
        ("Skills you have", 50, 40), ("Role fits what you want", 100, 30)
    ]  # fmt: skip
    assert views.breakdown(None, weights) is None and views.breakdown("{bad", weights) is None
    profile = {"skills": {"languages": ["Python", "SQL"]}}
    got = [(s.name, s.have) for s in views.skills(["Python", "Kafka"], profile)]
    assert got == [("Python", True), ("Kafka", False)]
    assert views.skills(["Go"], None)[0].have is None


def test_quick_filter_tags(repo: Repo, clock: FakeClock) -> None:
    add(repo, "i", role="SDE Intern", work_mode="remote", deadline="2026-10-10")
    c = views.today(repo, 75, clock(), TZ)[0]
    assert set(c.tags.split()) == {"eligible", "remote", "internship", "closing"}
    assert c.closes_in == 2


def test_palette_search(client: TestClient, repo: Repo) -> None:
    add(repo, "r", company="Rubrik", role="SDE")
    jobs = client.get("/api/search", params={"q": "rub"}).json()["jobs"]
    assert jobs == [{"id": "r", "role": "SDE", "company": "Rubrik", "score": 90, "status": "New"}]
    assert client.get("/api/search").json() == {"jobs": []}


def test_static_files_get_a_new_address_when_they_change(client: TestClient) -> None:
    page = client.get("/").text
    js = re.search(r'src="(/static/app\.js\?v=[0-9a-f]{10})"', page)
    css = re.search(r'href="(/static/app\.css\?v=[0-9a-f]{10})"', page)
    assert js and css  # the browser can't keep running an old app.js after an update
    assert client.get(js.group(1)).headers["cache-control"] == "no-cache"


def test_today_cards_carry_what_the_toolbar_sorts_by(
    client: TestClient, repo: Repo, clock: FakeClock
) -> None:
    add(repo, "a", company="Rubrik", role="SDE Intern", deadline="2026-10-09")
    clock.advance(7 * 3600)
    add(repo, "b", company="Acme", score=80)
    c = {x.id: x for x in views.today(repo, 75, clock(), TZ)}
    assert (c["a"].fresh, c["a"].age, c["b"].fresh, c["b"].age) == (
        False,
        "7 h ago",
        True,
        "just now",
    )
    assert c["a"].url == "https://acme.com/jobs/a"
    page = client.get("/").text
    assert 'data-filter="internship"' in page and "data-sort" in page and "data-find" in page
    assert 'data-text="sde intern rubrik' in page and 'data-closes="1"' in page  # tomorrow


# ---- the digest page and sorting by time ------------------------------------------------------


def test_digest_windows_follow_the_digest_times(clock: FakeClock) -> None:
    now = clock().astimezone(TZ)  # Thu 8 Oct, 14:30 IST; digests at 09:00 and 19:00
    w = views.windows(now, ["09:00", "19:00"])
    assert (w[0].key, w[0].label, w[0].current) == ("now", "So far", True)
    assert w[0].since.hour == 9 and w[0].until == now
    assert (w[1].key, w[1].label) == ("2026-10-08-0900", "Morning · 8 Oct")
    assert (w[1].since.day, w[1].since.hour, w[2].label) == (7, 19, "Evening · 7 Oct")
    assert len(w) == views.DIGEST_WINDOWS


def test_an_earlier_digest_leaves_out_what_came_after(
    client: TestClient, repo: Repo, clock: FakeClock
) -> None:
    clock.now = clock.now.replace(hour=2)  # 07:30 IST: in the window before the 09:00 digest
    add(repo, "early", company="Rubrik", score=90)
    clock.now = clock.now.replace(hour=5)  # 10:30 IST: after it
    add(repo, "late", company="Acme", score=95)
    morning = views.digest(repo, settings(), clock(), "", None)  # default: the latest sent
    assert morning.title == "Morning digest" and [c.id for c in morning.inbox] == ["early"]
    so_far = views.digest(repo, settings(), clock(), "now", None)
    assert so_far.title == "Next digest, so far" and [c.id for c in so_far.inbox] == ["late"]
    page = client.get("/digest")
    assert page.status_code == 200 and "Rubrik" in page.text and "Acme" not in page.text
    email = client.get("/digest/email", params={"w": "now"})
    assert "Acme" in email.text and "Rubrik" not in email.text
    assert email.headers["content-security-policy"].startswith("default-src 'none'")
    assert "script" not in email.headers["content-security-policy"]


def test_all_jobs_sort_by_time(repo: Repo, clock: FakeClock) -> None:
    add(repo, "first", score=50)
    clock.advance(60)
    add(repo, "second", score=99)
    order = lambda sort: [c.id for c in views.all_jobs(repo, TZ, "jobs", "", 1, sort=sort).cards]  # noqa: E731
    assert order("new") == ["second", "first"] and order("old") == ["first", "second"]
    assert order("score") == ["second", "first"] and order("nonsense") == order("new")


# ---- changing a status from the page -----------------------------------------------------------


def test_buttons_need_the_page_token(client: TestClient, repo: Repo) -> None:
    add(repo, "j", company="Rubrik")
    token = repo.get_setting("web_token")
    assert token and f'content="{token}"' in client.get("/").text
    assert client.post("/jobs/j/act", content="action=shortlist").status_code == 403
    bad = {"x-jobradar-token": "guess", "content-type": "application/x-www-form-urlencoded"}
    assert client.post("/jobs/j/act", content="action=shortlist", headers=bad).status_code == 403
    other_site = {"x-jobradar-token": token, "origin": "https://evil.example",
                  "content-type": "application/x-www-form-urlencoded"}  # fmt: skip
    assert (
        client.post("/jobs/j/act", content="action=shortlist", headers=other_site).status_code
        == 403
    )
    job = repo.get_job("j")
    assert job is not None and job.status == "new"


def test_a_button_click(client: TestClient, repo: Repo) -> None:
    add(repo, "j", company="Rubrik")
    token = repo.get_setting("web_token") or ""
    headers = {"x-jobradar-token": token, "content-type": "application/x-www-form-urlencoded"}
    out = client.post("/jobs/j/act", content="action=shortlist", headers=headers).json()
    assert (out["ok"], out["status"], out["undo"]) == (True, "shortlisted", "new")
    assert 'data-id="j"' in out["row"] and "Not interested" in out["row"]  # the row's next buttons
    again = client.post("/jobs/j/act", content="action=shortlist", headers=headers)
    assert again.status_code == 409 and "is Shortlisted now" in again.json()["message"]
    undo = client.post("/jobs/j/status", content="status=new", headers=headers).json()
    assert undo["ok"] and undo["status"] == "new"
    assert (
        client.post("/jobs/nope/act", content="action=shortlist", headers=headers).status_code
        == 404
    )


def test_without_javascript_a_form_post_comes_back(client: TestClient, repo: Repo) -> None:
    add(repo, "j")
    token = repo.get_setting("web_token") or ""
    form = {"content-type": "application/x-www-form-urlencoded"}
    back = client.post("/jobs/j/act", content=f"action=shortlist&token={token}&next=/jobs%3Fq%3Dx",
                       headers=form, follow_redirects=False)  # fmt: skip
    assert back.status_code == 303 and back.headers["location"] == "/jobs?q=x"
    away = client.post("/jobs/j/status", content=f"status=new&token={token}&next=//evil.com",
                       headers=form, follow_redirects=False)  # fmt: skip
    assert away.headers["location"] == "/"  # never to another site
    assert [st for st, _ in repo.status_history("j")] == ["shortlisted", "new"]


def test_cards_show_the_next_steps(repo: Repo, clock: FakeClock) -> None:
    add(repo, "n")
    add(repo, "s", status=JobStatus.SHORTLISTED, you=True)
    add(repo, "k", status=JobStatus.SKIPPED, you=True)
    add(repo, "h", status=JobStatus.HIDDEN)
    acts = lambda job_id: [a for a, _ in views.card(repo.get_job(job_id), TZ).actions]  # type: ignore[arg-type]  # noqa: E731
    assert acts("n") == ["shortlist", "skip"]
    assert acts("s") == ["skip"] and acts("k") == ["shortlist"] and acts("h") == ["shortlist"]


# ---- step 3: inside `jobradar run` --------------------------------------------------------------


def with_web(**web: Any) -> Any:
    from jobradar.config import AppConfig, Settings

    base = settings()
    config = base.config.model_dump()
    config["web"].update(web)
    return Settings(config=AppConfig.model_validate(config), secrets=base.secrets)


async def test_the_dashboard_runs_inside_jobradar_run(
    repo: Repo, queue: TaskQueue, tmp_path: Path
) -> None:
    import asyncio
    import signal

    import httpx

    from jobradar.app import start_dashboard

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    before = signal.getsignal(signal.SIGINT)
    woke: list[int] = []
    server = start_dashboard(with_web(port=port), repo, queue,
                             lambda: woke.append(1))  # fmt: skip
    assert server is not None
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.05)
    async with httpx.AsyncClient() as http:
        page = await http.get(f"http://127.0.0.1:{port}/")
    assert page.status_code == 200 and "JobRadar" in page.text
    assert signal.getsignal(signal.SIGINT) is before  # Ctrl+C stays JobRadar's
    server.should_exit = True
    await asyncio.wait_for(task, 5)
    assert start_dashboard(with_web(enabled=False), repo, queue, print) is None


# ---- full-text search and filters -----------------------------------------------------------


def test_search_reads_the_whole_job(repo: Repo, clock: FakeClock) -> None:
    add(repo, "k", company="Acme", role="Backend Engineer", locations=["Pune"], work_mode="hybrid",
        skills_required=["Kafka"])  # fmt: skip
    repo.save_page("k", "https://acme.com/k", "Backend", "You will build event pipelines on Kafka.")
    add(repo, "g", company="Globex", role="Frontend Developer", locations=["Bangalore"])
    repo.save_page("g", "https://acme.com/g", "Frontend", "React and TypeScript, onsite.")
    found = lambda q="", **f: views.all_jobs(repo, TZ, "jobs", q, 1, clock(),  # noqa: E731
                                             filters=views.Filters(**f))  # fmt: skip
    hit = found("kafka pipelines")
    assert [c.id for c in hit.cards] == ["k"]
    assert "<mark>pipelines</mark>" in str(hit.snippets["k"])
    assert [c.id for c in found("typescr").cards] == ["g"]  # a prefix finds the word
    assert [c.id for c in found(place="pune").cards] == ["k"]
    assert [c.id for c in found(remote=True).cards] == ["k"]  # hybrid counts
    assert {c.id for c in found().cards} == {"k", "g"}
    # A page fetched later gets into the index on the next search.
    clock.advance(60)
    repo.save_page("g", "https://acme.com/g", "Frontend", "React, TypeScript and some Kafka.")
    assert {c.id for c in found("kafka").cards} == {"k", "g"}


def test_filters_by_score_age_and_source(repo: Repo, clock: FakeClock) -> None:
    source = repo.upsert_source(Platform.TELEGRAM, "-1009", "Freshershunt")
    assert source.id is not None
    add(repo, "old", score=95)
    clock.advance(5 * 86400)
    add(repo, "weak", score=55)
    add(repo, "tg", score=92)
    raw, _ = repo.save_raw_message(source.id, "5", "2026-10-13T08:00:00.000000Z", "post")
    repo.add_job_source("tg", raw)
    ids = lambda **f: {c.id for c in views.all_jobs(repo, TZ, "jobs", "", 1, clock(),  # noqa: E731
                                                    filters=views.Filters(**f)).cards}  # fmt: skip
    assert ids(min_score=90) == {"old", "tg"} and ids(within=3) == {"weak", "tg"}
    assert ids(source=source.id) == {"tg"} and ids(min_score=90, within=3) == {"tg"}
    assert repo.sources() == [(source.id, "telegram", "Freshershunt")]


def test_all_jobs_page_with_filters(client: TestClient, repo: Repo) -> None:
    add(repo, "k", company="Acme", role="Kafka Engineer", score=91)
    page = client.get("/jobs", params={"q": "kafka", "min": 90, "remote": "", "sort": "relevance"})
    assert page.status_code == 200 and "Kafka Engineer" in page.text and "1 filter" in page.text
    assert client.get("/jobs", params={"min": 37}).status_code == 200  # an odd value: ignored


# ---- Skills ------------------------------------------------------------------------------------

PROFILE_YAML = """basics:
  name: Sameer Kumar   # me
skills:
  languages: [Python, SQL]
  additional: ["Machine Learning (feature engineering, model training)", Agile]  # keep this
experience: []
"""


def test_add_skill_touches_one_line(tmp_path: Path) -> None:
    from jobradar.config import ConfigError
    from jobradar.profile import add_skill, load_profile

    path = tmp_path / "profile.yaml"
    path.write_text(PROFILE_YAML)
    backup = add_skill(path, "AWS", "20261020-1300")
    assert (
        backup == "profile.yaml.bak-20261020-1300"
        and (tmp_path / backup).read_text() == PROFILE_YAML
    )
    after = path.read_text()
    assert "Agile, AWS]  # keep this" in after and "# me" in after  # comments stay
    assert after.count("\n") == PROFILE_YAML.count("\n")
    assert "AWS" in load_profile(path)["skills"]["additional"]
    add_skill(path, "Node.js: backend", "x")  # needs quotes in YAML
    assert load_profile(path)["skills"]["additional"][-1] == "Node.js: backend"
    with pytest.raises(ConfigError, match="already"):
        add_skill(path, "aws", "y")
    flat = tmp_path / "flat.yaml"
    flat.write_text("skills:\n  - Python\n")
    with pytest.raises(ConfigError, match="yourself"):
        add_skill(flat, "AWS", "z")
    assert flat.read_text() == "skills:\n  - Python\n"


def test_skills_page_and_i_know_this(repo: Repo, tmp_path: Path, clock: FakeClock) -> None:
    from jobradar.config import AppConfig, Settings

    path = tmp_path / "profile.yaml"
    path.write_text(PROFILE_YAML)
    base = settings().config.model_dump()
    base["matching"]["profile_path"] = str(path)
    s = Settings(config=AppConfig.model_validate(base), secrets=settings().secrets)
    for n in range(3):
        add(repo, f"j{n}", company=f"Co{n}", score=90)
        repo.save_page(f"j{n}", f"https://acme.com/j{n}", "Role", "Python, AWS and Kubernetes.")
    add(repo, "j3", company="Co3", score=80)
    repo.save_page("j3", "https://acme.com/j3", "Role", "Good knowledge of Python or C++.")
    page = views.skills_page(repo, s, views_profile(path), clock(), 30)
    assert page.looked_at == 4  # C++ isn't missing: that job takes Python instead
    assert [(r.name, r.jobs, r.trend) for r in page.missing] == [
        ("AWS", 3, None),
        ("Kubernetes", 3, None),
    ]
    assert [r.name for r in page.have] == ["Python"] and len(page.missing[0].samples) == 3
    client = TestClient(create_app(s, repo, clock), base_url="http://127.0.0.1:8080")
    listing = client.get("/skills").text
    assert "Skills you keep missing" in listing and '<span class="gh-name">AWS</span>' in listing
    assert (
        page.missing[0].dots == ["must"] * 3 and "3 of 3 jobs ask for AWS outright" in page.verdict
    )
    aws = client.get("/skills/aws")
    assert aws.status_code == 200 and '<h1 class="sk-name">AWS</h1>' in aws.text
    assert aws.text.count('class="tile k-must"') == 3 and "<b>3</b> must have" in aws.text
    assert "3 of 3 jobs ask for AWS outright" in aws.text and "<mark>AWS</mark>" in aws.text
    cpp = client.get("/skills/c%2B%2B").text
    assert "The one job naming C++ takes Python instead, which you have." in cpp
    assert client.get("/skills/cobol").status_code == 404
    form = {"content-type": "application/x-www-form-urlencoded"}
    assert client.post("/skills/know", content="skill=AWS", headers=form).status_code == 403
    token = repo.get_setting("web_token") or ""
    out = client.post(
        "/skills/know", content="skill=AWS", headers=form | {"x-jobradar-token": token}
    )
    assert out.json()["ok"] and "AWS" in path.read_text()
    assert "AWS" not in [
        r.name for r in views.skills_page(repo, s, views_profile(path), clock(), 30).missing
    ]
    again = client.post(
        "/skills/know", content="skill=AWS", headers=form | {"x-jobradar-token": token}
    )
    assert again.status_code == 409 and "already" in again.json()["message"]


def views_profile(path: Path) -> dict[str, Any]:
    from jobradar.profile import load_profile

    return load_profile(path)


# ---- Phone (Tailscale) and Notion off ----------------------------------------------------------


def test_web_url_is_the_phone_address(repo: Repo, clock: FakeClock) -> None:
    from jobradar.config import AppConfig, NotionConfig
    from jobradar.sinks.email_actions import dashboard_url

    assert WebConfig(url="https://laptop.tail1234.ts.net/").url == "https://laptop.tail1234.ts.net"
    assert WebConfig(url="").url is None
    with pytest.raises(ValidationError, match="whole address"):
        WebConfig(url="laptop.tail1234.ts.net")
    base = settings()
    web = WebConfig(url="https://laptop.tail1234.ts.net")
    config = base.config.model_copy(update={"web": web, "notion": NotionConfig(enabled=False)})
    s = base.model_copy(update={"config": config})
    assert dashboard_url(s) == "https://laptop.tail1234.ts.net"  # email links work on the phone
    client = TestClient(create_app(s, repo, clock), base_url="http://127.0.0.1:8080")
    page = client.get("/", headers={"host": "laptop.tail1234.ts.net"})
    assert page.status_code == 200 and "saved in JobRadar right away" in page.text
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400
    add(repo, "a", company="Acme")
    token = repo.get_setting("web_token") or ""
    from_phone = client.post(
        "/jobs/a/act", content=f"action=shortlist&token={token}",
        headers={"content-type": "application/x-www-form-urlencoded",
                 "origin": "https://laptop.tail1234.ts.net", "host": "laptop.tail1234.ts.net"},
        follow_redirects=False,
    )  # fmt: skip
    assert from_phone.status_code == 303 and repo.get_job("a").status == "shortlisted"
    assert AppConfig.model_validate({"sources": {"telegram": {"enabled": False}}}).notion.enabled


async def test_the_gig_scan_is_queued_while_jobradar_runs(repo: Repo, queue: TaskQueue) -> None:
    """The gig sources are read on a timer, so a new ad is found without asking."""
    from jobradar.app import Pipeline
    from jobradar.config import GigConfig
    from jobradar.pipeline.task_types import GIG_SCAN

    base = settings()
    config = base.config.model_copy(update={"gig": GigConfig(enabled=True, every_minutes=15)})
    pipeline = Pipeline(base.model_copy(update={"config": config}), repo, queue, None)
    try:
        assert pipeline.gigs is not None
        assert GIG_SCAN in pipeline.worker.handlers
        pipeline.gigs.schedule()
        task = queue.claim([GIG_SCAN])
        assert task is not None and task.type == GIG_SCAN
    finally:
        await pipeline.aclose()


async def test_pipeline_without_notion_drops_notion_tasks(repo: Repo, queue: TaskQueue) -> None:
    from jobradar.app import Pipeline, connect_notion
    from jobradar.config import NotionConfig
    from jobradar.pipeline.task_types import NOTION_POLL, NOTION_STATUS, NOTION_UPSERT

    base = settings()
    config = base.config.model_copy(update={"notion": NotionConfig(enabled=False)})
    s = base.model_copy(update={"config": config})
    assert await connect_notion(s) is None  # no Notion key needed
    pipeline = Pipeline(s, repo, queue, None)
    try:
        assert pipeline.status_sync is None
        queue.enqueue(NOTION_UPSERT, "a")
        queue.enqueue(NOTION_STATUS, "a", {"status": "Applied"})
        for _ in range(2):
            task = queue.claim([NOTION_UPSERT, NOTION_STATUS, NOTION_POLL])
            assert task is not None
            await pipeline.worker.handlers[task.type](task)
            queue.complete(task)
        assert queue.claim() is None
    finally:
        await pipeline.aclose()


async def test_run_keeps_going_without_telegram_and_notion(
    repo: Repo, queue: TaskQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from jobradar import app as application
    from jobradar.config import NotionConfig

    base = settings()
    config = base.config.model_copy(
        update={"notion": NotionConfig(enabled=False), "web": WebConfig(enabled=False)}
    )
    monkeypatch.setattr(application, "open_store", lambda: (repo, queue))
    task = asyncio.create_task(application.run(base.model_copy(update={"config": config})))
    await asyncio.sleep(0.5)
    assert not task.done()  # it used to stop as soon as the (switched off) Telegram source did
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
