"""Import hub that registers every SQLAlchemy model on `Base.metadata`.

Alembic's `env.py` imports this module before diffing, and anything needing
the full schema (`Base.metadata.create_all`, test fixtures) should import
it too rather than relying on import order elsewhere.
"""

from __future__ import annotations

from app.modules.analytics.infrastructure.models import AnalyticsEventModel
from app.modules.auth.infrastructure.models import RefreshTokenModel
from app.modules.notifications.infrastructure.models import NotificationModel
from app.modules.offers.infrastructure.models import (
    CategoryModel,
    FavoriteModel,
    OfferModel,
    PriceHistoryModel,
    ProductModel,
    SellerScoreModel,
)
from app.modules.repair.infrastructure.models import RepairReportModel
from app.modules.scoring.infrastructure.models import DealScoreModel
from app.modules.search.infrastructure.models import SearchProfileModel
from app.modules.users.infrastructure.models import UserModel

__all__ = [
    "AnalyticsEventModel",
    "CategoryModel",
    "DealScoreModel",
    "FavoriteModel",
    "NotificationModel",
    "OfferModel",
    "PriceHistoryModel",
    "ProductModel",
    "RefreshTokenModel",
    "RepairReportModel",
    "SearchProfileModel",
    "SellerScoreModel",
    "UserModel",
]
