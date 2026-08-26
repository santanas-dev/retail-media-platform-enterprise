"""RM-STAB-001 — единый контракт `BEHAVIORAL_APP_DB_URL`.

До этого модуля переменная была перегружена двумя НЕСОВМЕСТИМЫМИ формами, и ни
одно значение не удовлетворяло обеим:

* потребители SQLAlchemy (`conftest`, `test_commerce_rls`, `test_license_*`)
  требуют драйверную форму `postgresql+asyncpg://`;
* два новейших доказательства безопасности
  (`test_authz_cross_portal_001_derived_rls`, `test_campaign_permission_split_001`)
  зовут `asyncpg.connect` напрямую и требуют голую форму `postgresql://`.

Задать одно значение так, чтобы прошли обе группы, было невозможно:
драйверная форма даёт `ClientConfigurationError: invalid DSN ... got
'postgresql+asyncpg'`, голая — `InvalidRequestError: The asyncio extension
requires an async driver ... 'psycopg2' is not async`.

В CI дефект не виден, потому что CI переменную не задаёт вовсе и каждый файл
падает на собственный корректный дефолт. Ловушка достаётся оператору, которому
раздел «Environment» в `PROJECT_STATE.md` велит переменную выставить.

Контракт теперь один: **значение задаётся в любой из двух форм**, а потребитель
берёт ту, которая нужна ему, через `sqlalchemy_dsn()` или `raw_dsn()`.
"""

from __future__ import annotations

import os

ENV_VAR = "BEHAVIORAL_APP_DB_URL"
FALLBACK_ENV_VAR = "DATABASE_URL"

# Роль приложения: NOSUPERUSER, NOBYPASSRLS. RLS обязана применяться.
DEFAULT_BARE = (
    "postgresql://retail_media_app:retail_media_app"
    "@localhost:5432/retail_media_platform"
)

_ASYNC_DRIVER = "postgresql+asyncpg://"
_BARE = "postgresql://"
# Синхронный драйвер сюда попасть не должен: behavioral-стек асинхронный.
_SYNC_DRIVERS = ("postgresql+psycopg2://", "postgresql+psycopg://")


def _configured() -> str:
    value = os.environ.get(ENV_VAR, "").strip()
    if not value:
        value = os.environ.get(FALLBACK_ENV_VAR, "").strip()
    return value or DEFAULT_BARE


def raw_dsn() -> str:
    """DSN для `asyncpg.connect` — без имени драйвера."""
    value = _configured()
    for sync in _SYNC_DRIVERS:
        if value.startswith(sync):
            raise ValueError(
                f"{ENV_VAR} задан синхронным драйвером ({sync}); behavioral-стек "
                f"асинхронный. Используйте {_BARE} или {_ASYNC_DRIVER}."
            )
    if value.startswith(_ASYNC_DRIVER):
        return _BARE + value[len(_ASYNC_DRIVER):]
    return value


def sqlalchemy_dsn() -> str:
    """DSN для `create_async_engine` — с явным асинхронным драйвером."""
    value = _configured()
    for sync in _SYNC_DRIVERS:
        if value.startswith(sync):
            raise ValueError(
                f"{ENV_VAR} задан синхронным драйвером ({sync}); behavioral-стек "
                f"асинхронный. Используйте {_BARE} или {_ASYNC_DRIVER}."
            )
    if value.startswith(_ASYNC_DRIVER):
        return value
    if value.startswith(_BARE):
        return _ASYNC_DRIVER + value[len(_BARE):]
    return value
