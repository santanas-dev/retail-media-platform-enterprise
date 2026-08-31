"""RM-STAB-002 — доказательство, что strict-умолчание работает.

Раньше `conftest` открывал КАЖДЫЙ запрос с `app.rmp_is_admin='true'`. Сброс живёт
в `resolve_scope_context`, который вызывается только через `set_rls_context`,
поэтому эндпоинт, забывший контекст, в тестах видел все строки, а в проде —
ни одной. Набор структурно не мог поймать этот класс.

Здесь пиниется само свойство: в фазе `call` сессия не элевирована, и запрос без
контекста ведёт себя fail-closed — как в проде.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from tests.behavioral import conftest as _conftest
from tests.behavioral.conftest import (
    _elevation_allowed,
    set_elevation_phase,
)
from tests.behavioral.dsn import sqlalchemy_dsn


class TestElevationPhase:
    """Фаза, в которой элевация законна."""

    def test_call_phase_is_not_elevated(self):
        """В теле теста элевация выключена — это и есть strict-умолчание."""
        assert _elevation_allowed() is False, (
            "фаза `call` элевирована: маска admin вернулась, и набор снова не может "
            "поймать эндпоинт, забывший set_rls_context"
        )

    def test_setup_phase_is_elevated(self):
        """Переключатель действительно управляет флагом, а не декоративен."""
        set_elevation_phase(True)
        try:
            assert _elevation_allowed() is True
        finally:
            set_elevation_phase(False)
        assert _elevation_allowed() is False


class TestSessionIsFailClosed:
    """Сессия в фазе `call` обязана вести себя как продовая."""

    def test_no_admin_flag_on_a_plain_session(self, db_available):
        """Свежая сессия роли приложения не несёт admin-обхода."""

        async def _probe():
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy.pool import NullPool

            engine = create_async_engine(sqlalchemy_dsn(), echo=False, poolclass=NullPool)
            try:
                async with engine.connect() as conn:
                    flag = await conn.scalar(
                        text("SELECT current_setting('app.rmp_is_admin', true)")
                    )
                    rows = await conn.scalar(
                        text("SELECT count(*) FROM device_onboarding_codes")
                    )
                    return flag, rows
            finally:
                await engine.dispose()

        flag, rows = asyncio.run(_probe())
        assert flag in (None, "", "false"), (
            f"app.rmp_is_admin={flag!r} на чистой сессии — RLS обходится там, "
            f"где в проде она применяется"
        )
        assert rows == 0, (
            f"без контекста видно {rows} строк RLS-таблицы; ожидается 0 (fail-closed)"
        )


class TestNoRouteElevationRemains:
    """RM-TECH-210: allowlist элевации по маршрутам снят вместе с механизмом.

    Раньше два маршрута (device-codes, device/onboard) держались на маске admin
    в фазе `call`; оба починены в эндпоинтах (set_rls_context, bootstrap-контекст
    кода — миграция 037). Пустая заглушка не оставлена: механизма нет вовсе.
    """

    def test_allowlist_mechanism_is_gone(self):
        assert not hasattr(_conftest, "ENDPOINT_ELEVATION_ALLOWLIST"), (
            "механизм allowlist вернулся — маска admin по маршрутам запрещена; "
            "эндпоинт, которому нужен контекст, чинится, а не исключается"
        )
        assert not hasattr(_conftest, "_path_allowlisted")
