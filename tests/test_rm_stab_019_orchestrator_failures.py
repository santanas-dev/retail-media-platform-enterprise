"""RM-STAB-019 — consumer оркестратора переживает сбой сообщения (RF-04: P1-6.a, T11).

* Сбой `session_setup` или rollback одного сообщения — nak и счётчик ошибок,
  исключение не уходит в цикл `run()`, следующие сообщения обрабатываются.
* Если цикл подключённого consumer всё же завершился, health это видит:
  `consumer_running=False`, `/health/ready` — не `ok` (503).

Системный сбой генерации манифеста (P0-4) доказан на PostgreSQL:
`tests/behavioral/test_rm_stab_019_orchestrator_rls.py`.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.services import health_state
from packages.services.campaign_event_handler import NatsJetStreamCampaignConsumer


def _envelope(campaign_id: str = "camp-1") -> bytes:
    return json.dumps({
        "event_id": f"evt-{campaign_id}",
        "event_type": "campaign.approved",
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": campaign_id,
        "payload": {},
        "headers": {},
        "created_at": "2026-09-29T00:00:00Z",
    }).encode("utf-8")


class _Msg:
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


class _Session:
    """AsyncSession double whose commit / rollback can be made to fail."""

    def __init__(self, *, rollback_error: Exception | None = None) -> None:
        self.rollback_error = rollback_error
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        if self.rollback_error is not None:
            raise self.rollback_error


def _consumer(session_setup=None) -> NatsJetStreamCampaignConsumer:
    return NatsJetStreamCampaignConsumer(
        nats_url="nats://unused:4222",
        engine=MagicMock(),
        session_setup=session_setup,
    )


class _HealthStateIsolation(unittest.IsolatedAsyncioTestCase):
    """Snapshot / restore the process-wide health singleton around each test."""

    def setUp(self) -> None:
        self._saved = health_state.get_health_state()

    def tearDown(self) -> None:
        with health_state._lock:
            health_state._state = self._saved


class TestProcessOneSurvivesSessionFailures(_HealthStateIsolation):

    async def test_session_setup_failure_naks_and_does_not_raise(self):
        setup = AsyncMock(side_effect=RuntimeError("SET LOCAL failed: connection reset"))
        consumer = _consumer(session_setup=setup)
        msg = _Msg(_envelope())
        before = health_state.get_health_state().consumer_errors

        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(),
        ), patch("packages.domain.delivery.generate_manifests_for_campaign") as gen:
            await consumer._process_one(msg)

        self.assertTrue(msg.nakd)
        self.assertFalse(msg.acked)
        gen.assert_not_called()
        self.assertEqual(consumer.nakd, 1)
        self.assertEqual(consumer.errors, 1)
        self.assertEqual(health_state.get_health_state().consumer_errors, before + 1)

    async def test_rollback_failure_naks_and_does_not_raise(self):
        consumer = _consumer()
        msg = _Msg(_envelope())

        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(rollback_error=RuntimeError("rollback on dead connection")),
        ), patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
            side_effect=RuntimeError("DB down"),
        ):
            await consumer._process_one(msg)

        self.assertTrue(msg.nakd)
        self.assertFalse(msg.acked)
        self.assertEqual(consumer.nakd, 1)
        self.assertEqual(consumer.errors, 1)

    async def test_commit_failure_is_not_acked(self):
        consumer = _consumer()
        msg = _Msg(_envelope())
        session = _Session()
        session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))

        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: session,
        ), patch("packages.domain.delivery.generate_manifests_for_campaign") as gen:
            gen.return_value = MagicMock(eligible=True, manifest_count=1)
            await consumer._process_one(msg)

        self.assertFalse(msg.acked)
        self.assertTrue(msg.nakd)


class TestRunLoopSurvivesMessageFailure(_HealthStateIsolation):

    async def test_loop_continues_after_session_setup_failure(self):
        calls = {"n": 0}

        async def flaky_setup(session):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("SET LOCAL failed")

        consumer = _consumer(session_setup=flaky_setup)
        bad, good = _Msg(_envelope("camp-bad")), _Msg(_envelope("camp-good"))
        processed = asyncio.Event()
        fetches = {"n": 0}

        async def fetch(batch, timeout):
            fetches["n"] += 1
            if fetches["n"] == 1:
                return [bad, good]
            processed.set()
            await asyncio.sleep(0.01)  # idle fetch: yield like a real timeout
            raise TimeoutError()

        consumer._sub = MagicMock()
        consumer._sub.fetch = fetch

        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(),
        ), patch("packages.domain.delivery.generate_manifests_for_campaign") as gen:
            gen.return_value = MagicMock(eligible=True, manifest_count=1)
            task = asyncio.create_task(consumer.run())
            await asyncio.wait_for(processed.wait(), timeout=5)
            still_running = consumer._running
            await consumer.stop()
            await asyncio.wait_for(task, timeout=5)

        self.assertTrue(still_running)
        self.assertTrue(bad.nakd)
        self.assertTrue(good.acked)
        self.assertGreaterEqual(fetches["n"], 2)


class TestReadinessSeesStoppedConsumer(_HealthStateIsolation):

    def test_connected_consumer_not_running_is_not_ready(self):
        state = health_state.HealthState(
            db_ok=True, nats_connected=True, consumer_ready=True, consumer_running=False,
        )
        self.assertEqual(state.to_dict()["status"], "degraded")

    def test_connected_running_consumer_is_ready(self):
        state = health_state.HealthState(
            db_ok=True, nats_connected=True, consumer_ready=True, consumer_running=True,
        )
        self.assertEqual(state.to_dict()["status"], "ok")

    def test_consumer_disabled_does_not_affect_readiness(self):
        state = health_state.HealthState(db_ok=True, nats_connected=True)
        self.assertEqual(state.to_dict()["status"], "ok")

    def test_shutting_down_wins(self):
        state = health_state.HealthState(
            db_ok=True, nats_connected=True, consumer_ready=True, consumer_running=False,
            shutting_down=True,
        )
        self.assertEqual(state.to_dict()["status"], "shutting_down")


class TestLoopExitClearsRunningFlag(_HealthStateIsolation):

    async def test_crashed_loop_marks_consumer_not_running(self):
        health_state.set_db_ok(True)
        health_state.set_nats_connected(True)
        health_state.set_consumer_ready(True)
        health_state.set_consumer_running(True)

        consumer = _consumer()
        consumer._sub = MagicMock()
        consumer._sub.fetch = AsyncMock(return_value=[_Msg(_envelope())])
        consumer._process_one = AsyncMock(side_effect=RuntimeError("unexpected"))

        await asyncio.wait_for(consumer.run(), timeout=5)

        state = health_state.get_health_state()
        self.assertFalse(state.consumer_running)
        self.assertEqual(state.to_dict()["status"], "degraded")

    async def test_loop_reports_running_while_it_runs(self):
        health_state.set_consumer_running(False)
        consumer = _consumer()
        seen = asyncio.Event()

        async def fetch(batch, timeout):
            seen.set()
            await asyncio.sleep(0.01)
            raise TimeoutError()

        consumer._sub = MagicMock()
        consumer._sub.fetch = fetch
        task = asyncio.create_task(consumer.run())
        await asyncio.wait_for(seen.wait(), timeout=5)
        running_inside = health_state.get_health_state().consumer_running
        await consumer.stop()
        await asyncio.wait_for(task, timeout=5)

        self.assertTrue(running_inside)
        self.assertFalse(health_state.get_health_state().consumer_running)

    async def test_run_without_subscription_reports_not_running(self):
        health_state.set_consumer_running(True)
        await _consumer().run()
        self.assertFalse(health_state.get_health_state().consumer_running)


if __name__ == "__main__":
    unittest.main()
