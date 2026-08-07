"""Search scheduler foundation (Band 02: SearchScheduler, Band 07 deliverable).

An in-process asyncio interval runner. Deliberately simple — the point of
the `SearchSchedulerProtocol` abstraction is that this can be swapped for
Celery beat, a cron-triggered job, or a cloud scheduler later (Band 20:
scalability milestones) without any other module noticing.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.modules.offers.application.ingestion import IngestionService
from app.modules.offers.application.interfaces import (
    MarketplaceProviderProtocol,
    OfferNormalizerProtocol,
    OfferPersistedHookProtocol,
    OfferValidatorProtocol,
)
from app.modules.offers.domain.entities import OfferCategory
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    provider: MarketplaceProviderProtocol
    category: OfferCategory
    query: str | None = None
    limit: int = 20


class AsyncIntervalScheduler:
    """Implements `SearchSchedulerProtocol`. Each tick runs every configured
    job in its own database transaction, so one job's failure can't roll
    back another's persisted offers."""

    def __init__(
        self,
        jobs: list[ScheduledJob],
        *,
        session_factory: async_sessionmaker[AsyncSession],
        normalizer: OfferNormalizerProtocol,
        validator: OfferValidatorProtocol,
        interval_seconds: float = 900.0,
        hook_factory: Callable[[AsyncSession], OfferPersistedHookProtocol] | None = None,
    ) -> None:
        """`hook_factory` builds a fresh `OfferPersistedHookProtocol` bound to
        the *current job's* session, not a session-less singleton — a real
        hook (e.g. `SavedSearchMatchNotifier`) reads back the just-persisted
        offer to match it against saved searches, which only works if it
        shares the same not-yet-committed transaction (see
        `IngestionService._persist`: the hook runs before `run_once` below
        commits). A hook built once at scheduler-construction time, before
        any session exists, could not satisfy that."""
        self._jobs = jobs
        self._session_factory = session_factory
        self._normalizer = normalizer
        self._validator = validator
        self._interval = interval_seconds
        self._hook_factory = hook_factory
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def run_once(self) -> None:
        for job in self._jobs:
            async with self._session_factory() as session:
                try:
                    repo = SqlAlchemyOfferRepository(session)
                    hook = self._hook_factory(session) if self._hook_factory is not None else None
                    service = IngestionService(
                        job.provider,
                        self._normalizer,
                        self._validator,
                        repo,
                        on_offer_persisted=hook,
                    )
                    result = await service.ingest(
                        category=job.category, query=job.query, limit=job.limit
                    )
                    await session.commit()
                    logger.info(
                        "scheduled_ingestion_ok",
                        provider=job.provider.source,
                        category=job.category.value,
                        persisted=result.persisted,
                        rejected=result.rejected,
                    )
                except Exception as exc:  # noqa: BLE001 — one job's failure must not stop the rest
                    await session.rollback()
                    logger.error(
                        "scheduled_ingestion_failed",
                        provider=job.provider.source,
                        category=job.category.value,
                        error=str(exc),
                    )

    def start(self) -> None:
        if self._task is not None:
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _loop(self) -> None:
        while not self._stopped.is_set():
            await self.run_once()
            # TimeoutError here is normal: it means the interval elapsed
            # without being stopped, so we run another tick.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopped.wait(), timeout=self._interval)
