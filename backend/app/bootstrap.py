"""Process-level composition root (Band 13: Deployment/DevOps).

`app/main.py`'s router-level DI (`Depends(get_...)` functions inside each
module's `presentation/router.py`) is request-scoped and doesn't apply to
background work that isn't triggered by an HTTP request. The marketplace
ingestion scheduler (`app.modules.offers.infrastructure.scheduler.
AsyncIntervalScheduler`, built in Band 07/Task #5 but never started — no
call site existed until now) is exactly that case: it needs to be built
once at process startup and stopped at shutdown. This module is the one
place allowed to import concrete infrastructure from four different
modules (offers, search, notifications, users) to wire that up; nothing
inside those modules imports across module boundaries directly (Band 02
rule still holds — this file sits above all of them).
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.session import session_factory
from app.modules.notifications.application.interfaces import (
    EmailSenderProtocol,
    NotificationSenderProtocol,
)
from app.modules.notifications.application.match_notifier import SavedSearchMatchNotifier
from app.modules.notifications.application.service import NotificationService
from app.modules.notifications.infrastructure.device_token_repository import (
    SqlAlchemyDeviceTokenRepository,
)
from app.modules.notifications.infrastructure.fcm_provider import FcmNotificationSender
from app.modules.notifications.infrastructure.preference_repository import (
    SqlAlchemyNotificationPreferenceRepository,
)
from app.modules.notifications.infrastructure.repository import SqlAlchemyNotificationRepository
from app.modules.notifications.infrastructure.resend_provider import ResendEmailSender
from app.modules.offers.domain.entities import OfferCategory
from app.modules.offers.infrastructure.normalizer import OfferNormalizer
from app.modules.offers.infrastructure.providers.ebay_api import EbayApiProvider
from app.modules.offers.infrastructure.providers.kleinanzeigen import KleinanzeigenProvider
from app.modules.offers.infrastructure.repository import SqlAlchemyOfferRepository
from app.modules.offers.infrastructure.scheduler import AsyncIntervalScheduler, ScheduledJob
from app.modules.offers.infrastructure.validator import OfferValidator
from app.modules.scoring.infrastructure.repository import SqlAlchemyDealScoreRepository
from app.modules.search.application.service import SearchService
from app.modules.search.infrastructure.repository import SqlAlchemySearchProfileRepository
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository

logger = get_logger(__name__)

# Kleinanzeigen has no laptops/consoles-specific search UX worth scoping per
# category the way EbayApiProvider does (see its `_CATEGORY_QUERY`) — one
# job per category is still correct, `KleinanzeigenProvider.search` derives
# its own query text from the category.
_ALL_CATEGORIES: tuple[OfferCategory, ...] = tuple(OfferCategory)


def _build_hook_factory(
    settings: Settings,
) -> Callable[[AsyncSession], SavedSearchMatchNotifier]:
    """Returns a per-session factory for the "offer persisted" hook. Mirrors
    the DI functions in `notifications/presentation/router.py` and
    `search/presentation/router.py` (`get_notification_service`/
    `get_search_service`) — same construction, just triggered by the
    scheduler instead of a request."""

    def build(session: AsyncSession) -> SavedSearchMatchNotifier:
        sender: NotificationSenderProtocol | None = (
            FcmNotificationSender(settings)
            if settings.fcm_project_id and settings.fcm_credentials_json_path
            else None
        )
        email_sender: EmailSenderProtocol | None = (
            ResendEmailSender(settings)
            if settings.resend_api_key and settings.resend_from_email
            else None
        )
        notifications = NotificationService(
            notifications=SqlAlchemyNotificationRepository(session),
            device_tokens=SqlAlchemyDeviceTokenRepository(session),
            preferences=SqlAlchemyNotificationPreferenceRepository(session),
            sender=sender,
            email_sender=email_sender,
            users=SqlAlchemyUserRepository(session),
        )
        matcher = SearchService(
            profiles=SqlAlchemySearchProfileRepository(session),
            offers=SqlAlchemyOfferRepository(session),
            deal_scores=SqlAlchemyDealScoreRepository(session),
        )
        profiles = SqlAlchemySearchProfileRepository(session)
        return SavedSearchMatchNotifier(matcher, profiles, notifications)

    return build


def build_scheduler(settings: Settings) -> AsyncIntervalScheduler | None:
    """Builds the ingestion scheduler, or returns `None` if there's nothing
    it could usefully do yet. Called once from `app.main`'s lifespan."""
    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled", reason="SCHEDULER_ENABLED is false")
        return None

    jobs: list[ScheduledJob] = []

    if settings.ebay_client_id and settings.ebay_client_secret:
        ebay = EbayApiProvider(settings)
        jobs.extend(ScheduledJob(provider=ebay, category=c) for c in _ALL_CATEGORIES)
    else:
        logger.warning(
            "scheduler_ebay_provider_skipped",
            reason="EBAY_CLIENT_ID/EBAY_CLIENT_SECRET not set",
        )

    if settings.kleinanzeigen_provider_enabled:
        kleinanzeigen = KleinanzeigenProvider(settings)
        jobs.extend(ScheduledJob(provider=kleinanzeigen, category=c) for c in _ALL_CATEGORIES)

    if not jobs:
        logger.warning(
            "scheduler_not_started",
            reason="no provider is configured (set EBAY_CLIENT_ID/SECRET or "
            "KLEINANZEIGEN_PROVIDER_ENABLED=true)",
        )
        return None

    return AsyncIntervalScheduler(
        jobs,
        session_factory=session_factory,
        normalizer=OfferNormalizer(),
        validator=OfferValidator(),
        interval_seconds=settings.scheduler_interval_seconds,
        hook_factory=_build_hook_factory(settings),
    )
