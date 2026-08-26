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

from tests.behavioral.conftest import (
    ENDPOINT_ELEVATION_ALLOWLIST,
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


class TestAllowlistIsAccountable:
    """Каждая запись allowlist — названный дефект, а не удобство."""

    def test_every_entry_names_a_defect_and_a_proof(self):
        assert ENDPOINT_ELEVATION_ALLOWLIST, (
            "allowlist пуст — если дефекты починены, удалите и этот тест вместе с "
            "механизмом, а не оставляйте пустую заглушку"
        )
        for route, reason in ENDPOINT_ELEVATION_ALLOWLIST.items():
            assert route.startswith("/"), f"{route}: маршрут должен начинаться со слэша"
            assert len(reason) > 120, (
                f"{route}: причина слишком короткая — запись обязана называть дефект, "
                f"доказательство и то, чем она снимается"
            )
            assert "RLS-CONTEXT-" in reason, (
                f"{route}: причина не называет идентификатор дефекта"
            )
            assert "починк" in reason, (
                f"{route}: причина не говорит, что запись снимается починкой эндпоинта"
            )

    def test_allowlist_is_not_a_blanket(self):
        """Список не должен подменять собой отключение strict-режима."""
        assert len(ENDPOINT_ELEVATION_ALLOWLIST) <= 5, (
            f"в allowlist {len(ENDPOINT_ELEVATION_ALLOWLIST)} записей — это уже не "
            f"исключение, а возврат маски другим способом"
        )
