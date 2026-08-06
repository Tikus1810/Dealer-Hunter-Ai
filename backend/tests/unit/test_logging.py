"""Unit tests for app.core.logging. `logging.basicConfig` only has an
effect the first time it's called per process (unless the root logger has
no handlers yet), so each test clears `logging.root.handlers` first to
force `configure_logging` to actually re-apply — otherwise the second test
to run would silently observe the first test's level.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from app.core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _restore_root_logger_state() -> Iterator[None]:
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    yield
    logging.root.handlers = original_handlers
    logging.root.level = original_level


def test_configure_logging_sets_debug_level_when_debug_true() -> None:
    logging.root.handlers = []
    configure_logging(debug=True)
    assert logging.root.level == logging.DEBUG


def test_configure_logging_sets_info_level_when_debug_false() -> None:
    logging.root.handlers = []
    configure_logging(debug=False)
    assert logging.root.level == logging.INFO


def test_get_logger_returns_a_usable_bound_logger() -> None:
    logger = get_logger("test.module")
    # A bound logger exposes the standard level methods regardless of
    # structlog configuration state — this just proves construction works.
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
