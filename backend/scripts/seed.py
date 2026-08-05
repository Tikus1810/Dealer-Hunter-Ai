"""Seed baseline reference data (Band 09 deliverable: "Seed data").

Idempotent: safe to run multiple times (uses `ON CONFLICT DO NOTHING` via
`code`'s unique constraint). Seeds the four primary device categories named
in Band 01 (Master PRD -> Primary categories).

Usage:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_factory
from app.modules.offers.domain.entities import OfferCategory
from app.modules.offers.infrastructure.models import CategoryModel

CATEGORY_NAMES: dict[OfferCategory, str] = {
    OfferCategory.WINDOWS_LAPTOP: "Windows Laptops",
    OfferCategory.MACBOOK: "MacBooks",
    OfferCategory.IPHONE: "iPhones",
    OfferCategory.GAME_CONSOLE: "Game Consoles",
}


async def seed_categories(session: AsyncSession) -> None:
    existing = set((await session.execute(select(CategoryModel.code))).scalars().all())
    created = 0
    for category, name in CATEGORY_NAMES.items():
        if category.value in existing:
            continue
        session.add(CategoryModel(code=category.value, name=name))
        created += 1
    await session.commit()
    print(f"seed_categories: {created} created, {len(existing)} already present")


async def main() -> None:
    async with session_factory() as session:
        await seed_categories(session)


if __name__ == "__main__":
    asyncio.run(main())
