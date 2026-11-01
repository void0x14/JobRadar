from jobradar.db.models import JobStatus
from jobradar.db.repo import Repo
from jobradar.pipeline import status_rules as rules
from jobradar.pipeline.task_types import NOTION_STATUS
from jobradar.queue.tasks import TaskQueue
from tests.test_web import add


def job(repo: Repo, job_id: str = "j") -> object:
    found = repo.get_job(job_id)
    assert found is not None
    return found


def queued(queue: TaskQueue, kind: str) -> list[dict[str, object]]:
    out = []
    while (task := queue.claim([kind])) is not None:
        out.append(task.payload)
        queue.complete(task)
    return out


def test_buttons_move_forward_only(repo: Repo, queue: TaskQueue) -> None:
    add(repo, "j")
    done = rules.act(repo, queue, job(repo), "shortlist")  # type: ignore[arg-type]
    assert (done.ok, done.before, done.after) == (True, "new", "shortlisted")
    assert done.message == "Shortlisted: Software Engineer @ Acme."
    assert queued(queue, NOTION_STATUS) == [{"status": "Shortlisted"}]
    late = rules.act(repo, queue, job(repo), "shortlist")  # type: ignore[arg-type]
    assert not late.ok and "is Shortlisted now" in late.message and "Change status" in late.message
    assert job(repo).status == "shortlisted"  # type: ignore[attr-defined]
    assert not rules.act(repo, queue, job(repo), "dance").ok  # type: ignore[arg-type]


def test_skip_marks_the_job_skipped(repo: Repo, queue: TaskQueue) -> None:
    add(repo, "j")
    done = rules.act(repo, queue, job(repo), "skip")  # type: ignore[arg-type]
    assert (done.ok, done.after) == (True, "skipped")
    assert done.message == "Skipped: Software Engineer @ Acme."
    assert queued(queue, NOTION_STATUS) == [{"status": "Skipped"}]
    # A skipped job can come back as a shortlist, but not be skipped twice.
    assert rules.act(repo, queue, job(repo), "skip").ok is False  # type: ignore[arg-type]
    assert rules.act(repo, queue, job(repo), "shortlist").ok is True  # type: ignore[arg-type]


def test_change_status_goes_anywhere_of_yours(repo: Repo, queue: TaskQueue) -> None:
    add(repo, "j", status=JobStatus.SHORTLISTED, you=True)
    back = rules.set_status(repo, queue, job(repo), "skipped")  # type: ignore[arg-type]
    assert (back.ok, back.after, back.message) == (
        True,
        "skipped",
        "Now Skipped: Software Engineer @ Acme.",
    )
    assert queued(queue, NOTION_STATUS) == [{"status": "Skipped"}]
    assert repo.status_history("j")[-1][0] == "skipped"
    assert not rules.set_status(repo, queue, job(repo), "discarded").ok  # JobRadar's, not yours
    assert rules.set_status(repo, queue, job(repo), "skipped").message == "Already Skipped."
    assert rules.notion_option(JobStatus.SHORTLISTED) == "Shortlisted"
