"""Keep checking: the gig scan on a timer, so a new ad is found within minutes.

The scan is one task on the same durable queue as everything else, so a restart loses
nothing and a source that fails is simply tried again next time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jobradar.config import Settings
from jobradar.db.repo import Repo, TaskRecord
from jobradar.gig import notify as gig_notify
from jobradar.gig import scan as gig_scan
from jobradar.gig.adapters.base import WebClient
from jobradar.pipeline.task_types import GIG_SCAN
from jobradar.queue.tasks import TaskQueue

log = logging.getLogger(__name__)


@dataclass
class GigWatcher:
    """Scans the gig sources on a timer and tells you what is new."""

    settings: Settings
    repo: Repo
    queue: TaskQueue

    @property
    def every_minutes(self) -> int:
        return self.settings.config.gig.every_minutes

    def schedule(self, delay: float = 0, key: str = "a") -> None:
        self.queue.enqueue(GIG_SCAN, key, delay=delay)

    async def tick(self, task: TaskRecord) -> None:
        """One round: scan every source, notify what is new, and queue the next round."""
        try:
            await self.run_once()
        finally:
            self.schedule(self.every_minutes * 60, key="b" if task.key == "a" else "a")

    async def run_once(self) -> str:
        """Scan every source now; returns what happened."""
        client = WebClient()
        try:
            results = await gig_scan.scan_all(self.repo, client=client)
        finally:
            await client.aclose()
        new_gigs = [gig for result in results for gig in result.new_gigs]
        if not new_gigs:
            return "nothing new"
        if not self.settings.config.gig.notify:
            return f"{len(new_gigs)} new gig(s), not sent"
        wanted = {gig.original_url for gig in new_gigs}
        rows = [
            row
            for row in self.repo.list_gigs(verdict="gig", limit=200)
            if row.original_url in wanted
        ]
        return gig_notify.notify(self.settings, rows)
