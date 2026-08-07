"""Delete analytics events older than a retention window (Band 15:
retention). Not wired into the scheduler or any request path — deleting
analytics history is an operational decision, run deliberately, not an
automatic background job. See docs/analytics.md's "Retention" section for
the default (180 days) and how to run this on a schedule if that's wanted
later (e.g. a cron entry calling this, or a second job alongside the
Band 13 scheduler once one is actually needed).

Usage:
    python -m scripts.purge_analytics_events [--days N]
"""

from __future__ import annotations

import argparse
import asyncio

from app.db.session import session_factory
from app.modules.analytics.application.service import AnalyticsService
from app.modules.analytics.infrastructure.repository import SqlAlchemyAnalyticsEventRepository

DEFAULT_RETENTION_DAYS = 180


async def purge(days: int) -> int:
    async with session_factory() as session:
        service = AnalyticsService(SqlAlchemyAnalyticsEventRepository(session))
        deleted = await service.purge_events_older_than(days)
        await session.commit()
        return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"delete events older than this many days (default: {DEFAULT_RETENTION_DAYS})",
    )
    args = parser.parse_args()

    deleted = asyncio.run(purge(args.days))
    print(f"purge_analytics_events: deleted {deleted} event(s) older than {args.days} days")


if __name__ == "__main__":
    main()
