"""Unit tests for NotificationTemplateRenderer — pure, no I/O."""

from __future__ import annotations

from app.modules.notifications.domain.entities import NotificationEvent
from app.modules.notifications.domain.templates import NotificationTemplateRenderer


def test_saved_search_match_includes_offer_and_profile_name() -> None:
    renderer = NotificationTemplateRenderer()
    rendered = renderer.render(
        NotificationEvent.SAVED_SEARCH_MATCH,
        {"offer_title": "MacBook Pro 14", "profile_name": "Cheap MacBooks", "price_amount": 799.0},
    )
    assert "MacBook Pro 14" in rendered.body
    assert "Cheap MacBooks" in rendered.body
    assert "799.00" in rendered.body


def test_saved_search_match_handles_missing_data_gracefully() -> None:
    renderer = NotificationTemplateRenderer()
    rendered = renderer.render(NotificationEvent.SAVED_SEARCH_MATCH, {})
    assert rendered.title
    assert rendered.body


def test_price_drop_shows_old_and_new_price() -> None:
    renderer = NotificationTemplateRenderer()
    rendered = renderer.render(
        NotificationEvent.PRICE_DROP,
        {"offer_title": "iPhone 13", "old_price": 500.0, "new_price": 450.0},
    )
    assert "500.00" in rendered.body
    assert "450.00" in rendered.body


def test_deal_score_ready_includes_score() -> None:
    renderer = NotificationTemplateRenderer()
    rendered = renderer.render(
        NotificationEvent.DEAL_SCORE_READY, {"offer_title": "PS5", "score": 87}
    )
    assert "87" in rendered.body


def test_generic_fallback_uses_the_message_field() -> None:
    # Exercises the same fallback `render()` uses for any event without a
    # dedicated renderer, without needing a non-existent enum member.
    rendered = NotificationTemplateRenderer._render_generic({"message": "custom text"})
    assert rendered.body == "custom text"
