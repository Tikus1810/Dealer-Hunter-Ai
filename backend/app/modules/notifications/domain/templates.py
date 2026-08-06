"""Notification templates (Band 11: templates). Pure, deterministic string
formatting — no I/O.

Single locale (German) for now, matching this product's actual market
(eBay.de / eBay Kleinanzeigen — same choice reflected in the example offer
listings used elsewhere in this codebase). Per-user locale selection is a
natural Future Extension Point (Band 11 lists localization explicitly) once
there's a second locale to switch to.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.domain.entities import NotificationEvent


@dataclass(frozen=True, slots=True)
class RenderedNotification:
    title: str
    body: str


class NotificationTemplateRenderer:
    """Renders (title, body) for each `NotificationEvent` from event-specific
    data. Missing/wrong-typed keys fall back to generic phrasing rather than
    raising — a template hiccup should never block a real event from being
    delivered (same "never silently fail the caller" spirit as the rest of
    this codebase's fallback handling, e.g. Vision AI's cosmetic analyzer)."""

    def render(self, event: NotificationEvent, data: dict[str, object]) -> RenderedNotification:
        if event == NotificationEvent.SAVED_SEARCH_MATCH:
            return self._render_saved_search_match(data)
        if event == NotificationEvent.PRICE_DROP:
            return self._render_price_drop(data)
        if event == NotificationEvent.DEAL_SCORE_READY:
            return self._render_deal_score_ready(data)
        return self._render_generic(data)

    @staticmethod
    def _render_saved_search_match(data: dict[str, object]) -> RenderedNotification:
        offer_title = str(data.get("offer_title") or "Ein Angebot")
        profile_name = str(data.get("profile_name") or "deine gespeicherte Suche")
        price = data.get("price_amount")
        price_note = f" für {price:.2f} €" if isinstance(price, int | float) else ""
        return RenderedNotification(
            title="Neuer Treffer für deine Suche",
            body=f'{offer_title}{price_note} passt zu "{profile_name}".',
        )

    @staticmethod
    def _render_price_drop(data: dict[str, object]) -> RenderedNotification:
        offer_title = str(data.get("offer_title") or "Ein Angebot")
        old_price = data.get("old_price")
        new_price = data.get("new_price")
        if isinstance(old_price, int | float) and isinstance(new_price, int | float):
            price_note = f" von {old_price:.2f} € auf {new_price:.2f} €"
        else:
            price_note = ""
        return RenderedNotification(
            title="Preis gesenkt", body=f"{offer_title} ist{price_note} günstiger geworden."
        )

    @staticmethod
    def _render_deal_score_ready(data: dict[str, object]) -> RenderedNotification:
        offer_title = str(data.get("offer_title") or "Ein Angebot")
        score = data.get("score")
        score_note = f" (Score: {score})" if isinstance(score, int) else ""
        return RenderedNotification(
            title="Deal Score verfügbar", body=f"{offer_title} wurde bewertet{score_note}."
        )

    @staticmethod
    def _render_generic(data: dict[str, object]) -> RenderedNotification:
        return RenderedNotification(
            title="Neue Benachrichtigung", body=str(data.get("message") or "")
        )
