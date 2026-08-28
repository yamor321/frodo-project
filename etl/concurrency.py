"""Concurrent I/O helper for the daily collection run. Downloading a
store's price file is a network wait, not CPU work, and today's run does
every download one at a time -- total runtime grows linearly with every
store *and every chain* added. ThreadPoolExecutor is the right tool for
I/O-bound waiting; multiprocessing would just add overhead for no benefit
here.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")


def fetch_concurrently(tasks: list[Callable[[], T]], max_workers: int = 6) -> list[T | None]:
    """Run each zero-arg callable in `tasks` on a bounded thread pool,
    preserving input order in the result. A single task's exception does
    not fail the whole batch -- it's printed and that slot comes back
    `None`, the same shape a per-item try/except loop would give, so one
    flaky download can't take down an entire chain's (or all chains')
    collection run.

    `max_workers` stays modest on purpose: it's basic etiquette toward the
    public portals being hit, and a hedge against tripping a self-inflicted
    rate limit -- not just a speed knob. Different chains are different
    servers, so nothing here needs coordinating across chains beyond
    sharing this one bounded pool.
    """
    if not tasks:
        return []

    def _run(task: Callable[[], T]) -> T | None:
        try:
            return task()
        except Exception as exc:  # noqa: BLE001 - one bad download must not sink the run
            print(f"  [fetch_concurrently] task failed: {exc}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_run, tasks))
