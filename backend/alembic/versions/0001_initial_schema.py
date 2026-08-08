"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-05

Creates all 13 tables from Band 09 (Database Design): users, refresh_tokens
(auth module), categories, products, seller_scores, offers, price_history,
favorites (offers module), search_profiles, deal_scores, repair_reports,
notifications, analytics_events.

Table and index definitions here were verified by compiling each SQLAlchemy
model's DDL against the PostgreSQL dialect (see app/db/models.py for the
source of truth) before being transcribed into this migration.

Revision id kept short ("0001", not the full filename) — found in a later
review pass, the first time `alembic upgrade head` ever ran against real
Postgres: Alembic's `alembic_version.version_num` column defaults to
VARCHAR(32), and 0002's original full-filename revision id ("0002_
notification_device_tokens_and_preferences", 49 chars) overflowed it.
Fixed for both migrations here, before any real deployment ever depended
on the old ids — the descriptive name still lives in the filename and
this docstring, just not in the id Alembic stores in the database.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "seller_scores",
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_seller_id", sa.String(120), nullable=False),
        sa.Column("seller_name", sa.String(120), nullable=True),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False),
        sa.Column("trust_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_seller_id", name="uq_seller_scores_source_seller"),
    )

    op.create_table(
        "users",
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("roles", postgresql.ARRAY(sa.String(32)), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "analytics_events",
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "notifications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "products",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(80), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("variant", sa.String(120), nullable=True),
        sa.Column("specs", postgresql.JSONB(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand", "model", "variant", name="uq_products_brand_model_variant"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_jti", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "search_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("keywords", sa.String(300), nullable=True),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_deal_score", sa.Integer(), nullable=True),
        sa.Column("notify_on_match", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "offers",
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_listing_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_currency", sa.String(3), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("seller_score_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("images", postgresql.ARRAY(sa.String(500)), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_listing_id", name="uq_offers_source_listing"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_score_id"], ["seller_scores.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "deal_scores",
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("estimated_market_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("estimated_total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("recommendation", sa.String(60), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        sa.Column("scoring_version", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "favorites",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "offer_id", name="uq_favorites_user_offer"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "price_history",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_currency", sa.String(3), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "repair_reports",
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repair_score", sa.Integer(), nullable=False),
        sa.Column("estimated_repair_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("estimated_repair_time_hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("required_tools", postgresql.ARRAY(sa.String(120)), nullable=False),
        sa.Column("compatible_parts", postgresql.JSONB(), nullable=False),
        sa.Column("risk_notes", postgresql.ARRAY(sa.String(300)), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column("report_version", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
    )

    # Indexes (beyond those implied by PRIMARY KEY / UNIQUE constraints above)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    op.create_index("ix_analytics_events_occurred_at", "analytics_events", ["occurred_at"])
    op.create_index("ix_analytics_events_name", "analytics_events", ["name"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_refresh_tokens_token_jti", "refresh_tokens", ["token_jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_search_profiles_is_active", "search_profiles", ["is_active"])
    op.create_index("ix_search_profiles_category_id", "search_profiles", ["category_id"])
    op.create_index("ix_search_profiles_user_id", "search_profiles", ["user_id"])
    op.create_index("ix_offers_source", "offers", ["source"])
    op.create_index("ix_offers_product_id", "offers", ["product_id"])
    op.create_index("ix_offers_category_price", "offers", ["category_id", "price_amount"])
    op.create_index("ix_offers_category_id", "offers", ["category_id"])
    op.create_index("ix_deal_scores_created_at", "deal_scores", ["created_at"])
    op.create_index("ix_deal_scores_offer_id", "deal_scores", ["offer_id"])
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorites_offer_id", "favorites", ["offer_id"])
    op.create_index("ix_price_history_offer_id", "price_history", ["offer_id"])
    op.create_index("ix_price_history_recorded_at", "price_history", ["recorded_at"])
    op.create_index("ix_price_history_product_id", "price_history", ["product_id"])
    op.create_index("ix_repair_reports_offer_id", "repair_reports", ["offer_id"])
    op.create_index("ix_repair_reports_created_at", "repair_reports", ["created_at"])


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_table("repair_reports")
    op.drop_table("price_history")
    op.drop_table("favorites")
    op.drop_table("deal_scores")
    op.drop_table("offers")
    op.drop_table("search_profiles")
    op.drop_table("refresh_tokens")
    op.drop_table("products")
    op.drop_table("notifications")
    op.drop_table("analytics_events")
    op.drop_table("users")
    op.drop_table("seller_scores")
    op.drop_table("categories")
