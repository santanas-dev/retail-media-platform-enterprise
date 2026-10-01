"""RM-STAB-020 — DLQ consumer оркестратора на PostgreSQL (RF-10: P1-6.b).

Путь воркера идёт под ролью приложения `retail_media_app` (NOSUPERUSER,
NOBYPASSRLS): consumer с `session_setup=set_worker_admin_context`, как в
orchestrator-worker. Проверки данных — под владельцем БД с admin-контекстом
(таблица под FORCE RLS, владелец тоже подчиняется политикам).

* последняя (7-я) неудачная доставка → строка DLQ + term; раньше → nak с
  задержкой по расписанию, строки нет;
* сбой записи в DLQ → nak с максимальной задержкой, сообщение не теряется;
* повтор: новое outbox-событие с тем же типом и aggregate, строка `replayed`;
  повторный replay ничего не делает;
* CLI `python -m packages.services.consumer_dead_letters list / replay`;
* без admin-контекста роль приложения не видит и не пишет DLQ.

Requires: RUN_BEHAVIORAL_TESTS=1, миграции (038), seed, роль `retail_media_app`.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from tests.behavioral.dsn import sqlalchemy_dsn  # noqa: E402

OWNER_DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
)
REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
pytestmark = pytest.mark.skipif(not REQUIRE_ENV, reason="RUN_BEHAVIORAL_TESTS=1 not set.")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# A campaign id that does not exist: the handler path runs, generation is patched to fail.
GHOST_CAMPAIGN_ID = "00000000-0000-0000-0000-0000000f0020"


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
    def __init__(self, data: bytes, num_delivered: int, stream_seq: int = 1234) -> None:
        self.data = data
        self.metadata = SimpleNamespace(
            num_delivered=num_delivered,
            sequence=SimpleNamespace(stream=stream_seq, consumer=num_delivered),
        )
        self.acked = False
        self.nak_delay: float | None = None
        self.terminated = False

    async def ack(self) -> None:
        self.acked = True

    async def nak(self, delay: float = 0) -> None:
        self.nak_delay = delay

    async def term(self) -> None:
        self.terminated = True


def _envelope(event_id: str) -> bytes:
    return json.dumps({
        "event_id": event_id,
        "event_type": "campaign.approved",
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": GHOST_CAMPAIGN_ID,
        "payload": {"campaign_id": GHOST_CAMPAIGN_ID},
        "headers": {"x-rf10": "1"},
        "created_at": "2026-10-01T00:00:00Z",
    }).encode("utf-8")


def _process_failing(msg: _Msg) -> None:
    """One message through the real consumer under the app role; generation fails."""
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
            with patch(
                "packages.domain.delivery.generate_manifests_for_campaign",
                side_effect=RuntimeError("config broken"),
            ):
                await consumer._process_one(msg)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def _dlq_rows(event_id: str) -> list:
    return _owner(
        "SELECT id, status, deliveries, stream_sequence, last_error, event_type, aggregate_id, "
        "envelope_json, replay_outbox_event_id FROM consumer_dead_letters WHERE event_id = :e",
        {"e": event_id},
    )


@pytest.fixture
def event_id():
    eid = f"evt-rf10-{uuid.uuid4().hex[:12]}"
    try:
        yield eid
    finally:
        rows = _owner("SELECT replay_outbox_event_id FROM consumer_dead_letters WHERE event_id = :e", {"e": eid})
        for (outbox_id,) in rows:
            if outbox_id:
                _owner("DELETE FROM outbox_events WHERE id = :i", {"i": outbox_id})
        _owner("DELETE FROM consumer_dead_letters WHERE event_id = :e", {"e": eid})


def test_app_role_is_nobypassrls():
    async def _run():
        engine = _app_engine()
        try:
            async with engine.connect() as conn:
                return (await conn.execute(text(
                    "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                ))).one()
        finally:
            await engine.dispose()

    assert tuple(asyncio.run(_run())) == ("retail_media_app", False, False)


def test_failure_before_limit_naks_with_backoff_and_no_row(event_id):
    msg = _Msg(_envelope(event_id), num_delivered=3)
    _process_failing(msg)

    assert msg.nak_delay == 120.0
    assert msg.terminated is False
    assert _dlq_rows(event_id) == []


def test_last_delivery_failure_is_dead_lettered_and_termed(event_id):
    msg = _Msg(_envelope(event_id), num_delivered=7, stream_seq=777)
    _process_failing(msg)

    assert msg.terminated is True
    assert msg.nak_delay is None
    assert msg.acked is False
    rows = _dlq_rows(event_id)
    assert len(rows) == 1
    _, status, deliveries, seq, last_error, event_type, aggregate_id, envelope, replay_id = rows[0]
    assert (status, deliveries, seq) == ("dead", 7, 777)
    assert last_error == "handler returned failure"
    assert (event_type, aggregate_id) == ("campaign.approved", GHOST_CAMPAIGN_ID)
    assert envelope["event_id"] == event_id and envelope["headers"] == {"x-rf10": "1"}
    assert replay_id is None


def test_dead_letter_write_failure_keeps_message(event_id):
    msg = _Msg(_envelope(event_id), num_delivered=7)
    with patch(
        "packages.services.consumer_dead_letters.record_dead_letter",
        side_effect=RuntimeError("DB down"),
    ):
        _process_failing(msg)

    assert msg.terminated is False
    assert msg.nak_delay == 3600.0
    assert _dlq_rows(event_id) == []


def _replay(dead_letter_id: str):
    from packages.domain.database import set_worker_admin_context
    from packages.services.consumer_dead_letters import replay_dead_letter

    async def _run():
        engine = _app_engine()
        try:
            async with AsyncSession(engine) as session:
                await set_worker_admin_context(session)
                outbox_id = await replay_dead_letter(session, dead_letter_id)
                await session.commit()
                return outbox_id
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_replay_enqueues_outbox_event_once(event_id):
    _process_failing(_Msg(_envelope(event_id), num_delivered=7))
    dead_letter_id = _dlq_rows(event_id)[0][0]

    outbox_id = _replay(dead_letter_id)

    assert outbox_id
    outbox = _owner(
        "SELECT event_type, aggregate_type, aggregate_id, payload_json, headers_json, status "
        "FROM outbox_events WHERE id = :i",
        {"i": outbox_id},
    )
    assert len(outbox) == 1
    assert tuple(outbox[0][:3]) == ("campaign.approved", "campaign", GHOST_CAMPAIGN_ID)
    assert outbox[0][3] == {"campaign_id": GHOST_CAMPAIGN_ID}
    assert outbox[0][5] == "pending"
    row = _dlq_rows(event_id)[0]
    assert row[1] == "replayed" and row[8] == outbox_id

    # A second replay of the same row does nothing.
    assert _replay(dead_letter_id) is None
    count = _owner(
        "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id = :a AND event_type = 'campaign.approved' "
        "AND headers_json ->> 'x-rf10' = '1'",
        {"a": GHOST_CAMPAIGN_ID},
    )
    assert count[0][0] == 1


def test_cli_lists_and_replays(event_id):
    _process_failing(_Msg(_envelope(event_id), num_delivered=7))
    dead_letter_id = _dlq_rows(event_id)[0][0]
    env = {**os.environ, "DATABASE_URL": sqlalchemy_dsn(), "PYTHONPATH": REPO_ROOT}

    listed = subprocess.run(
        [sys.executable, "-m", "packages.services.consumer_dead_letters", "list"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert listed.returncode == 0, listed.stderr
    assert dead_letter_id in listed.stdout and event_id in listed.stdout

    replayed = subprocess.run(
        [sys.executable, "-m", "packages.services.consumer_dead_letters", "replay", dead_letter_id],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert replayed.returncode == 0, replayed.stderr
    assert _dlq_rows(event_id)[0][1] == "replayed"

    again = subprocess.run(
        [sys.executable, "-m", "packages.services.consumer_dead_letters", "replay", dead_letter_id],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert again.returncode == 1


def test_app_role_without_admin_context_cannot_see_or_write(event_id):
    _process_failing(_Msg(_envelope(event_id), num_delivered=7))
    assert len(_dlq_rows(event_id)) == 1

    async def _run():
        engine = _app_engine()
        try:
            async with engine.connect() as conn:
                visible = (await conn.execute(
                    text("SELECT COUNT(*) FROM consumer_dead_letters WHERE event_id = :e"), {"e": event_id},
                )).scalar_one()
                denied = False
                try:
                    await conn.execute(text(
                        "INSERT INTO consumer_dead_letters (id, event_id, event_type, envelope_json, deliveries, "
                        "last_error, status, created_at) VALUES (:id, :e, 'campaign.approved', '{}'::jsonb, 7, "
                        "'x', 'dead', now())"
                    ), {"id": str(uuid.uuid4()), "e": event_id})
                except Exception as exc:  # RLS WITH CHECK violation
                    denied = "row-level security" in str(exc)
                return visible, denied
        finally:
            await engine.dispose()

    visible, denied = asyncio.run(_run())
    assert visible == 0
    assert denied is True


def test_table_has_forced_rls():
    rows = _owner(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'consumer_dead_letters'"
    )
    assert tuple(rows[0]) == (True, True)


def test_redelivered_dead_message_is_not_stored_twice(event_id):
    """term() lost → message comes back on the last delivery: still one row."""
    _process_failing(_Msg(_envelope(event_id), num_delivered=7))
    second = _Msg(_envelope(event_id), num_delivered=8)
    _process_failing(second)

    assert second.terminated is True
    assert len(_dlq_rows(event_id)) == 1


def test_oversized_aggregate_fields_do_not_block_the_write(event_id):
    raw = json.loads(_envelope(event_id))
    raw["aggregate_id"] = "x" * 80
    raw["aggregate_type"] = 12345
    msg = _Msg(json.dumps(raw).encode("utf-8"), num_delivered=7)
    _process_failing(msg)

    assert msg.terminated is True
    rows = _dlq_rows(event_id)
    assert len(rows) == 1 and rows[0][6] == "x" * 36


def test_cli_replay_all_skips_a_broken_row_and_keeps_the_rest(event_id):
    good_id = f"{event_id}-good"
    try:
        _process_failing(_Msg(_envelope(event_id), num_delivered=7))
        _process_failing(_Msg(_envelope(good_id), num_delivered=7))
        broken_row = _dlq_rows(event_id)[0][0]
        # An envelope that cannot be replayed (no aggregate_type).
        _owner(
            "UPDATE consumer_dead_letters SET envelope_json = envelope_json - 'aggregate_type' WHERE id = :i",
            {"i": broken_row},
        )
        env = {**os.environ, "DATABASE_URL": sqlalchemy_dsn(), "PYTHONPATH": REPO_ROOT}
        result = subprocess.run(
            [sys.executable, "-m", "packages.services.consumer_dead_letters", "replay", "--all"],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
        )

        assert result.returncode == 1, result.stdout + result.stderr
        assert f"{broken_row}\tfailed\tKeyError" in result.stdout
        assert _dlq_rows(event_id)[0][1] == "dead"
        assert _dlq_rows(good_id)[0][1] == "replayed"
    finally:
        rows = _owner("SELECT replay_outbox_event_id FROM consumer_dead_letters WHERE event_id = :e", {"e": good_id})
        for (outbox_id,) in rows:
            if outbox_id:
                _owner("DELETE FROM outbox_events WHERE id = :i", {"i": outbox_id})
        _owner("DELETE FROM consumer_dead_letters WHERE event_id = :e", {"e": good_id})


def test_messages_without_event_id_are_each_kept(event_id):
    raw = json.loads(_envelope(event_id))
    raw.pop("event_id")
    raw["headers"] = {"x-rf10": event_id}
    for _ in range(2):
        msg = _Msg(json.dumps(raw).encode("utf-8"), num_delivered=7)
        _process_failing(msg)
        assert msg.terminated is True
    rows = _owner(
        "SELECT event_id FROM consumer_dead_letters WHERE envelope_json -> 'headers' ->> 'x-rf10' = :e",
        {"e": event_id},
    )
    try:
        assert [r[0] for r in rows] == ["?", "?"]
    finally:
        _owner(
            "DELETE FROM consumer_dead_letters WHERE envelope_json -> 'headers' ->> 'x-rf10' = :e",
            {"e": event_id},
        )


def test_worker_dead_letter_check_counts_pending_under_app_role(event_id):
    import importlib.util

    from packages.services import health_state

    spec = importlib.util.spec_from_file_location(
        "orchestrator_worker_main_rm_stab_020",
        os.path.join(REPO_ROOT, "apps", "orchestrator-worker", "main.py"),
        submodule_search_locations=[],
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    async def _count():
        engine = _app_engine()
        try:
            return await worker._dead_letter_check(engine)
        finally:
            await engine.dispose()

    before = asyncio.run(_count())
    _process_failing(_Msg(_envelope(event_id), num_delivered=7))
    after = asyncio.run(_count())

    assert after == before + 1
    assert health_state.get_health_state().consumer_dead_letters_pending == after
