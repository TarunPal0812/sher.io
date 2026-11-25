"""Safety-net sweeper: removes files whose Redis key has expired.

Correctness never depends on this: downloads re-check Redis first. The sweeper
only reclaims disk. Ordering (reserve key, then commit file) guarantees a live
file always has a live key, so the sweeper can't delete something in use.
"""

import asyncio
import logging

from .files import FileStorage
from .store import ShareStore

log = logging.getLogger("sher.cleanup")


async def sweep(store: ShareStore, files: FileStorage) -> int:
    removed = 0
    for share_id in await asyncio.to_thread(files.stored_ids):
        if not await store.exists(share_id):
            files.delete(share_id)
            removed += 1
    removed += await asyncio.to_thread(files.purge_stale_tmp)
    return removed


async def cleanup_loop(app) -> None:  # noqa: ANN001
    interval = app.state.settings.cleanup_interval_seconds
    files = FileStorage(app.state.settings.storage_dir)
    while True:
        try:
            n = await sweep(ShareStore(app.state.redis), files)
            if n:
                log.info("cleanup removed=%d", n)
        except asyncio.CancelledError:
            raise
        except Exception:  # keep the loop alive
            log.exception("cleanup failed")
        await asyncio.sleep(interval)
