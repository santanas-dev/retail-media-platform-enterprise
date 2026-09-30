"""RM-STAB-019 — оркестратор не маскирует сбои (RF-04: P0-4, P1-8).

Доказательство на PostgreSQL. Путь воркера идёт под ролью приложения
`retail_media_app` (NOSUPERUSER, NOBYPASSRLS) — как в orchestrator-worker:
consumer с `session_setup=set_worker_admin_context`. Подготовка и проверки
данных — под владельцем БД (`BEHAVIORAL_DB_URL`), как в соседних файлах.

* P0-4: системная ошибка генерации манифеста (конфиг безопасности, БД) —
  rollback и nak, строки failed и событие `delivery.manifest.failed` не
  появляются. Ошибка данных одного устройства — failed + событие + ack.
* P1-8: один проход воркера завершения кампаний под `retail_media_app`
  завершает активную кампанию с истёкшими флайтами. Без admin-контекста RLS
  прячет кампанию — контрольный случай показывает, что тест это видит.

Requires: RUN_BEHAVIORAL_TESTS=1, миграции, seed, роль `retail_media_app`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from tests.behavioral.dsn import sqlalchemy_dsn  # noqa: E402

OWNER_DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
)
REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
pytestmark = pytest.mark.skipif(not REQUIRE_ENV, reason="RUN_BEHAVIORAL_TESTS=1 not set.")

# Seed IDs — apps/control-api/seed.py
SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
SEED_ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"
SEED_CONTRACT_ID = "00000000-0000-0000-0000-000000000212"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _owner_exec(sql: str, params: dict | None = None) -> list:
    engine = create_async_engine(OWNER_DB_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            result = await conn.execute(text(sql), params or {})
            return result.fetchall() if result.returns_rows else []
    finally:
        await engine.dispose()


def _owner(sql: str, params: dict | None = None) -> list:
    return asyncio.run(_owner_exec(sql, params))


def _app_engine():
    return create_async_engine(sqlalchemy_dsn(), echo=False)


class _Msg:
    """JetStream message double: records ack / nak / term."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = False
        self.nakd = False
        self.terminated = False

    async def ack(self) -> None:
        self.acked = True

    async def nak(self, delay: float = 0) -> None:
        self.nakd = True

    async def term(self) -> None:
        self.terminated = True


def _envelope(campaign_id: str) -> bytes:
    return json.dumps({
        "event_id": f"evt-rm-stab-019-{uuid.uuid4().hex[:8]}",
        "event_type": "campaign.approved",
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": campaign_id,
        "payload": {},
        "headers": {},
        "created_at": "2026-09-29T00:00:00Z",
    }).encode("utf-8")


def _process_as_worker(msg: _Msg) -> None:
    """Run one message through the real JetStream consumer under the app role."""
    from packages.domain.database import set_worker_admin_context
    from packages.services.campaign_event_handler import NatsJetStreamCampaignConsumer

    async def _run():
        engine = _app_engine()
        try:
            consumer = NatsJetStreamCampaignConsumer(
                nats_url="nats://unused:4222",
                engine=engine,
                session_setup=set_worker_admin_context,
            )
            await consumer._process_one(msg)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def _seed_delivery_rows() -> dict:
    """Counts of manifests and delivery.manifest.* outbox rows for the seed campaign."""
    manifests = _owner(
        "SELECT status, COUNT(*) FROM delivery_manifests WHERE campaign_id = :cid GROUP BY status",
        {"cid": SEED_CAMPAIGN_ID},
    )
    outbox = _owner(
        "SELECT event_type, COUNT(*) FROM outbox_events "
        "WHERE aggregate_id = :cid AND event_type LIKE 'delivery.manifest.%' GROUP BY event_type",
        {"cid": SEED_CAMPAIGN_ID},
    )
    return {
        "manifests": {r[0]: r[1] for r in manifests},
        "outbox": {r[0]: r[1] for r in outbox},
    }


def _clear_seed_delivery_rows() -> None:
    _owner(
        "DELETE FROM delivery_attempts WHERE manifest_id IN "
        "(SELECT manifest_id FROM delivery_manifests WHERE campaign_id = :cid)",
        {"cid": SEED_CAMPAIGN_ID},
    )
    for table in ("delivery_manifest_assets", "delivery_manifest_surfaces"):
        _owner(
            f"DELETE FROM {table} WHERE manifest_id IN "
            "(SELECT id FROM delivery_manifests WHERE campaign_id = :cid)",
            {"cid": SEED_CAMPAIGN_ID},
        )
    _owner("DELETE FROM delivery_manifests WHERE campaign_id = :cid", {"cid": SEED_CAMPAIGN_ID})
    _owner("DELETE FROM delivery_plans WHERE campaign_id = :cid", {"cid": SEED_CAMPAIGN_ID})
    _owner(
        "DELETE FROM outbox_events WHERE aggregate_id = :cid AND event_type LIKE 'delivery.manifest.%'",
        {"cid": SEED_CAMPAIGN_ID},
    )


@pytest.fixture
def approved_seed_campaign():
    """Seed campaign approved, device active, flight window current; restored afterwards."""
    campaign = _owner("SELECT status FROM campaigns WHERE id = :cid", {"cid": SEED_CAMPAIGN_ID})
    device = _owner("SELECT status FROM physical_devices WHERE id = :did", {"did": SEED_DEVICE_ID})
    flights = _owner(
        "SELECT id, start_at, end_at FROM campaign_flights WHERE campaign_id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    assert campaign and device and flights, "seed campaign/device/flights missing"

    now = datetime.now(timezone.utc)
    _owner("UPDATE campaigns SET status = 'approved' WHERE id = :cid", {"cid": SEED_CAMPAIGN_ID})
    _owner("UPDATE physical_devices SET status = 'active' WHERE id = :did", {"did": SEED_DEVICE_ID})
    _owner(
        "UPDATE campaign_flights SET start_at = :s, end_at = :e WHERE campaign_id = :cid",
        {"s": now - timedelta(days=1), "e": now + timedelta(days=7), "cid": SEED_CAMPAIGN_ID},
    )
    _clear_seed_delivery_rows()
    try:
        yield
    finally:
        _clear_seed_delivery_rows()
        _owner("UPDATE campaigns SET status = :st WHERE id = :cid",
               {"st": campaign[0][0], "cid": SEED_CAMPAIGN_ID})
        _owner("UPDATE physical_devices SET status = :st WHERE id = :did",
               {"st": device[0][0], "did": SEED_DEVICE_ID})
        for fid, start_at, end_at in flights:
            _owner("UPDATE campaign_flights SET start_at = :s, end_at = :e WHERE id = :fid",
                   {"s": start_at, "e": end_at, "fid": fid})


def test_app_role_is_nobypassrls():
    """The worker path in this file really runs under a NOBYPASSRLS non-owner role."""
    async def _run():
        engine = _app_engine()
        try:
            async with engine.connect() as conn:
                return (await conn.execute(text(
                    "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                ))).one()
        finally:
            await engine.dispose()

    user, is_super, bypass = asyncio.run(_run())
    assert user == "retail_media_app"
    assert is_super is False
    assert bypass is False


# ---------------------------------------------------------------------------
# P0-4 — системный сбой генерации не ack'ается
# ---------------------------------------------------------------------------


def test_security_config_failure_is_nakd_without_failed_rows(approved_seed_campaign):
    """Broken security config: nak, no failed manifest, no delivery.manifest.failed."""
    msg = _Msg(_envelope(SEED_CAMPAIGN_ID))
    with patch(
        "packages.security.config.get_security_config",
        side_effect=ValueError("METRICS_AUTH_TOKEN is required outside dev"),
    ):
        _process_as_worker(msg)

    assert msg.nakd is True
    assert msg.acked is False
    rows = _seed_delivery_rows()
    assert rows["manifests"] == {}
    assert rows["outbox"] == {}


def test_database_error_is_nakd_without_failed_rows(approved_seed_campaign):
    """DB error while persisting a manifest: nak, nothing recorded as failed."""
    msg = _Msg(_envelope(SEED_CAMPAIGN_ID))
    with patch(
        "packages.domain.repository.create_delivery_manifest_record",
        side_effect=OperationalError("INSERT INTO delivery_manifests", {}, Exception("connection lost")),
    ):
        _process_as_worker(msg)

    assert msg.nakd is True
    assert msg.acked is False
    rows = _seed_delivery_rows()
    assert rows["manifests"] == {}
    assert rows["outbox"] == {}


def test_device_data_error_is_recorded_failed_and_acked(approved_seed_campaign):
    """A per-device data error keeps the old contract: failed event + ack."""
    msg = _Msg(_envelope(SEED_CAMPAIGN_ID))
    with patch(
        "packages.domain.delivery.generate_manifest_json",
        side_effect=ValueError("bad playlist item"),
    ):
        _process_as_worker(msg)

    assert msg.acked is True
    assert msg.nakd is False
    rows = _seed_delivery_rows()
    assert rows["outbox"].get("delivery.manifest.failed", 0) >= 1
    assert rows["outbox"].get("delivery.manifest.generated", 0) == 0


def test_healthy_generation_is_acked(approved_seed_campaign):
    """Control: the same worker path with a working config generates and acks."""
    msg = _Msg(_envelope(SEED_CAMPAIGN_ID))
    _process_as_worker(msg)

    assert msg.acked is True
    rows = _seed_delivery_rows()
    assert rows["manifests"].get("generated", 0) >= 1
    assert rows["outbox"].get("delivery.manifest.generated", 0) >= 1
    assert rows["outbox"].get("delivery.manifest.failed", 0) == 0


# ---------------------------------------------------------------------------
# P1-8 — воркер завершения кампаний под RLS
# ---------------------------------------------------------------------------


def _load_worker_main():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_worker_main_rm_stab_019",
        os.path.join(os.path.dirname(__file__), "..", "..", "apps", "orchestrator-worker", "main.py"),
        submodule_search_locations=[],
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def expired_active_campaign():
    """An active campaign whose only flight ended yesterday (created as owner)."""
    from packages.domain.models import Campaign, CampaignFlight

    cid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async def _create():
        engine = create_async_engine(OWNER_DB_URL, echo=False)
        try:
            async with AsyncSession(engine) as session:
                await session.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
                session.add(Campaign(
                    id=cid, code=f"RMSTAB019-{cid[:8]}", name="RM-STAB-019 completion",
                    advertiser_organization_id=SEED_ADV_ORG_ID, advertiser_contract_id=SEED_CONTRACT_ID,
                    status="active", budget_limit_amount=100000, budget_limit_currency="RUB",
                ))
                await session.flush()
                session.add(CampaignFlight(
                    id=str(uuid.uuid4()), campaign_id=cid, name="expired",
                    start_at=now - timedelta(days=10), end_at=now - timedelta(days=1),
                ))
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_create())
    try:
        yield cid
    finally:
        _owner("DELETE FROM outbox_events WHERE aggregate_id = :cid", {"cid": cid})
        _owner("DELETE FROM campaign_status_history WHERE campaign_id = :cid", {"cid": cid})
        _owner("DELETE FROM campaign_flights WHERE campaign_id = :cid", {"cid": cid})
        _owner("DELETE FROM campaigns WHERE id = :cid", {"cid": cid})


def test_completion_without_admin_context_sees_nothing(expired_active_campaign):
    """Control: under the app role without worker context RLS hides the campaign."""
    from packages.domain.repository import complete_expired_campaigns

    async def _run():
        engine = _app_engine()
        try:
            async with AsyncSession(engine) as session:
                completed = await complete_expired_campaigns(session)
                await session.commit()
                return completed
        finally:
            await engine.dispose()

    assert expired_active_campaign not in asyncio.run(_run())
    status = _owner("SELECT status FROM campaigns WHERE id = :cid", {"cid": expired_active_campaign})
    assert status[0][0] == "active"


def test_completion_worker_pass_completes_under_app_role(expired_active_campaign):
    """The worker's completion pass (app role, NOBYPASSRLS) completes the campaign."""
    worker = _load_worker_main()

    async def _run():
        engine = _app_engine()
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            return await worker._campaign_completion_pass(factory)
        finally:
            await engine.dispose()

    completed = asyncio.run(_run())

    assert expired_active_campaign in completed
    status = _owner("SELECT status FROM campaigns WHERE id = :cid", {"cid": expired_active_campaign})
    assert status[0][0] == "completed"
    history = _owner(
        "SELECT new_status FROM campaign_status_history WHERE campaign_id = :cid",
        {"cid": expired_active_campaign},
    )
    assert ("completed",) in [tuple(r) for r in history]
