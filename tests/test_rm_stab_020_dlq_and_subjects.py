"""RM-STAB-020 — DLQ consumer оркестратора и полный stream (RF-10: P1-6.b, P1-7).

Unit-часть:
* политика повторов: 7 доставок, backoff 5с/30с/2м/10м/30м/60м, env-переопределение;
* consumer: на последней доставке неуспех → DLQ + term; раньше — nak с задержкой
  по расписанию; сбой записи в DLQ → nak с максимальной задержкой, без term;
* два stream (решение владельца 2026-10-01): RMP — только campaign.>,
  RMP_EVENTS — остальные семейства outbox со своими лимитами; вместе они
  покрывают каждый event_type, который пишет код; без auto-provision воркер
  сверяет subjects обоих stream;
* envelope — JSON, но не объект → term (poison), цикл не падает;
* события не-campaign, если всё же пришли в durable, подтверждаются без генерации;
* health показывает dead_lettered.

Запись/повтор DLQ под RLS доказаны на PostgreSQL:
`tests/behavioral/test_rm_stab_020_consumer_dlq.py`.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from packages.services import health_state
from packages.services.campaign_event_handler import NatsJetStreamCampaignConsumer
from packages.services.consumer_dead_letters import (
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_MAX_DELIVERIES,
    RetryPolicy,
    retry_policy_from_env,
)
from packages.services.jetstream_provisioning import (
    CAMPAIGN_STREAM_SUBJECTS,
    EVENTS_STREAM,
    EVENTS_STREAM_CONFIG,
    EVENTS_STREAM_SUBJECTS,
    OUTBOX_STREAM_SUBJECTS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _envelope(event_type: str = "campaign.approved", aggregate_id: str = "camp-1") -> bytes:
    return json.dumps({
        "event_id": f"evt-{event_type}-{aggregate_id}",
        "event_type": event_type,
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": aggregate_id,
        "payload": {},
        "headers": {},
        "created_at": "2026-10-01T00:00:00Z",
    }).encode("utf-8")


class _Msg:
    """JetStream message double with metadata.num_delivered / sequence.stream."""

    def __init__(self, data: bytes, num_delivered: int | None = 1, stream_seq: int = 42) -> None:
        self.data = data
        if num_delivered is not None:
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


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


def _consumer(**kwargs) -> NatsJetStreamCampaignConsumer:
    return NatsJetStreamCampaignConsumer(nats_url="nats://unused:4222", engine=MagicMock(), **kwargs)


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


class TestRetryPolicy(unittest.TestCase):

    def test_defaults_match_owner_decision(self):
        self.assertEqual(DEFAULT_MAX_DELIVERIES, 7)
        self.assertEqual(DEFAULT_BACKOFF_SECONDS, (5.0, 30.0, 120.0, 600.0, 1800.0, 3600.0))

    def test_delay_follows_schedule_and_caps_at_last(self):
        policy = RetryPolicy()
        self.assertEqual(
            [policy.nak_delay(n) for n in range(1, 9)],
            [5.0, 30.0, 120.0, 600.0, 1800.0, 3600.0, 3600.0, 3600.0],
        )
        self.assertEqual(policy.nak_delay(0), 5.0)
        self.assertEqual(policy.max_delay, 3600.0)

    def test_total_wait_before_dlq_is_about_1h43m(self):
        policy = RetryPolicy()
        waited = sum(policy.nak_delay(n) for n in range(1, policy.max_deliveries))
        self.assertEqual(waited, 6155.0)  # 1 h 42 min 35 s

    def test_env_overrides(self):
        policy = retry_policy_from_env({
            "CAMPAIGN_CONSUMER_MAX_DELIVERIES": "3",
            "CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "1, 2.5",
        })
        self.assertEqual(policy.max_deliveries, 3)
        self.assertEqual(policy.backoff_seconds, (1.0, 2.5))

    def test_env_absent_gives_defaults(self):
        self.assertEqual(retry_policy_from_env({}), RetryPolicy())

    def test_invalid_env_fails_fast(self):
        for env in (
            {"CAMPAIGN_CONSUMER_MAX_DELIVERIES": "0"},
            {"CAMPAIGN_CONSUMER_MAX_DELIVERIES": "many"},
            {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": ""},
            {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "5,-1"},
            {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "5,x"},
            {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "nan,30"},
            {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "5,inf"},
        ):
            with self.subTest(env=env), self.assertRaises(ValueError):
                retry_policy_from_env(env)


# ---------------------------------------------------------------------------
# Consumer: limit, backoff, DLQ
# ---------------------------------------------------------------------------


class _HealthIsolation(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self._saved = health_state.get_health_state()

    def tearDown(self) -> None:
        with health_state._lock:
            health_state._state = self._saved


class TestConsumerRetryAndDeadLetter(_HealthIsolation):

    async def _fail(self, consumer, msg):
        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(),
        ), patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
            side_effect=RuntimeError("DB down"),
        ):
            await consumer._process_one(msg)

    async def test_failure_before_limit_naks_with_scheduled_delay(self):
        for num, delay in ((1, 5.0), (2, 30.0), (3, 120.0), (6, 3600.0)):
            consumer = _consumer()
            consumer._dead_letter = AsyncMock(return_value=True)
            msg = _Msg(_envelope(), num_delivered=num)
            await self._fail(consumer, msg)
            with self.subTest(num_delivered=num):
                self.assertEqual(msg.nak_delay, delay)
                self.assertFalse(msg.terminated)
                consumer._dead_letter.assert_not_called()

    async def test_failure_on_last_delivery_dead_letters_and_terms(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=True)
        msg = _Msg(_envelope(), num_delivered=7, stream_seq=99)
        before = health_state.get_health_state().consumer_dead_lettered

        await self._fail(consumer, msg)

        self.assertTrue(msg.terminated)
        self.assertIsNone(msg.nak_delay)
        self.assertFalse(msg.acked)
        consumer._dead_letter.assert_awaited_once()
        kwargs = consumer._dead_letter.await_args.kwargs
        self.assertEqual(kwargs["deliveries"], 7)
        self.assertEqual(kwargs["stream_sequence"], 99)
        self.assertEqual(kwargs["envelope"]["event_type"], "campaign.approved")
        self.assertEqual(kwargs["last_error"], "handler returned failure")
        self.assertEqual(consumer.dead_lettered, 1)
        self.assertEqual(health_state.get_health_state().consumer_dead_lettered, before + 1)

    async def test_dead_letter_write_failure_naks_with_max_delay(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=False)
        msg = _Msg(_envelope(), num_delivered=7)

        await self._fail(consumer, msg)

        self.assertFalse(msg.terminated)
        self.assertEqual(msg.nak_delay, 3600.0)
        self.assertEqual(consumer.dead_lettered, 0)

    async def test_exception_reason_is_class_name_only(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=True)
        setup = AsyncMock(side_effect=ConnectionResetError("password=hunter2 host=db"))
        consumer._session_setup = setup
        msg = _Msg(_envelope(), num_delivered=7)

        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(),
        ):
            await consumer._process_one(msg)

        self.assertEqual(consumer._dead_letter.await_args.kwargs["last_error"], "ConnectionResetError")
        self.assertTrue(msg.terminated)

    async def test_message_without_metadata_counts_as_first_delivery(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=True)
        msg = _Msg(_envelope(), num_delivered=None)
        await self._fail(consumer, msg)
        self.assertEqual(msg.nak_delay, 5.0)

    async def test_custom_policy_is_used(self):
        consumer = _consumer(retry_policy=RetryPolicy(max_deliveries=2, backoff_seconds=(1.0,)))
        consumer._dead_letter = AsyncMock(return_value=True)
        first, second = _Msg(_envelope(), num_delivered=1), _Msg(_envelope(), num_delivered=2)
        await self._fail(consumer, first)
        await self._fail(consumer, second)
        self.assertEqual(first.nak_delay, 1.0)
        self.assertTrue(second.terminated)

    async def test_success_on_last_delivery_is_acked_not_dead_lettered(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=True)
        msg = _Msg(_envelope(), num_delivered=7)
        with patch(
            "packages.services.campaign_event_handler.AsyncSession",
            side_effect=lambda engine: _Session(),
        ), patch("packages.domain.delivery.generate_manifests_for_campaign") as gen:
            gen.return_value = MagicMock(eligible=True, manifest_count=1)
            await consumer._process_one(msg)
        self.assertTrue(msg.acked)
        consumer._dead_letter.assert_not_called()


class TestHealthDeadLettered(_HealthIsolation):

    def test_dead_lettered_in_ready_payload(self):
        state = health_state.HealthState(consumer_dead_lettered=3)
        self.assertEqual(state.to_dict()["components"]["consumer"]["dead_lettered"], 3)

    def test_pending_dead_letters_from_db_in_ready_payload(self):
        self.assertIsNone(health_state.HealthState().to_dict()["components"]["consumer"]["dead_letters_pending"])
        health_state.set_consumer_dead_letters_pending(4)
        payload = health_state.get_health_state().to_dict()
        self.assertEqual(payload["components"]["consumer"]["dead_letters_pending"], 4)


class TestWorkerRejectsBadRetryEnv(unittest.IsolatedAsyncioTestCase):

    async def test_bad_env_fails_the_consumer_start(self):
        import os

        worker = _load_worker()
        with patch.dict(os.environ, {"CAMPAIGN_CONSUMER_BACKOFF_SECONDS": "nan"}):
            with self.assertRaises(ValueError):
                await worker._start_real_consumer("nats://unused:4222", MagicMock())


# ---------------------------------------------------------------------------
# Stream subjects (P1-7)
# ---------------------------------------------------------------------------


def _nats_match(pattern: str, subject: str) -> bool:
    p, s = pattern.split("."), subject.split(".")
    for i, token in enumerate(p):
        if token == ">":
            return len(s) > i
        if i >= len(s) or (token != "*" and token != s[i]):
            return False
    return len(p) == len(s)


_EVENT_TYPE_LITERAL = re.compile(r"""event_type\s*=\s*["']([a-z_]+(?:\.[a-z_]+)+)["']""")


def _event_types_in_code() -> set[str]:
    found: set[str] = set()
    for root in ("packages", "apps"):
        for path in (REPO_ROOT / root).rglob("*.py"):
            if "node_modules" in path.parts:
                continue
            found.update(_EVENT_TYPE_LITERAL.findall(path.read_text(encoding="utf-8")))
    return found


def _load_worker():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "worker_main_rm_stab_020",
        REPO_ROOT / "apps" / "orchestrator-worker" / "main.py",
        submodule_search_locations=[],
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


class TestStreamSubjects(unittest.TestCase):

    def test_owner_decided_topology(self):
        self.assertEqual(CAMPAIGN_STREAM_SUBJECTS, ("campaign.>",))
        self.assertEqual(EVENTS_STREAM, "RMP_EVENTS")
        self.assertEqual(EVENTS_STREAM_SUBJECTS, ("delivery.>", "pop.>", "emergency.>", "creative_asset.>"))
        self.assertEqual(OUTBOX_STREAM_SUBJECTS, CAMPAIGN_STREAM_SUBJECTS + EVENTS_STREAM_SUBJECTS)
        # Bounded buffer: PoP volume ages out instead of growing forever.
        self.assertEqual(EVENTS_STREAM_CONFIG["max_age"], 7 * 24 * 3600)
        self.assertEqual(EVENTS_STREAM_CONFIG["max_bytes"], 1024 ** 3)
        self.assertEqual(EVENTS_STREAM_CONFIG["discard"], "old")

    def test_every_outbox_event_type_is_captured_exactly_once(self):
        types = _event_types_in_code()
        # The scan must actually see the known families, or it proves nothing.
        for expected in ("campaign.approved", "delivery.manifest.failed", "pop.event.accepted",
                         "emergency.changed", "creative_asset.created"):
            self.assertIn(expected, types)
        for event_type in sorted(types):
            in_campaign = any(_nats_match(p, event_type) for p in CAMPAIGN_STREAM_SUBJECTS)
            in_events = any(_nats_match(p, event_type) for p in EVENTS_STREAM_SUBJECTS)
            with self.subTest(event_type=event_type):
                # Exactly one stream: JetStream rejects overlapping subjects.
                self.assertTrue(in_campaign != in_events)

    def test_campaign_provisioning_keeps_its_contract(self):
        import asyncio

        from packages.services import jetstream_provisioning as prov

        js = MagicMock()
        nc = AsyncMock()
        nc.jetstream = MagicMock(return_value=js)
        with patch("nats.aio.client.Client", return_value=nc), \
             patch.object(prov, "_ensure_stream", new=AsyncMock()) as ensure_stream, \
             patch.object(prov, "_ensure_consumer", new=AsyncMock()) as ensure_consumer:
            asyncio.run(prov.provision_campaign_delivery("nats://unused:4222"))

        self.assertEqual(ensure_stream.await_args.args[1:3], ("RMP", ["campaign.>"]))
        # The durable keeps its existing config (no filter) — no recreate, no replay.
        self.assertEqual(ensure_consumer.await_args.args[1:], ("RMP", "rmp-campaign-consumer"))
        self.assertNotIn("filter_subject", ensure_consumer.await_args.kwargs)

    def test_events_stream_provisioning(self):
        import asyncio

        from packages.services import jetstream_provisioning as prov

        js = MagicMock()
        nc = AsyncMock()
        nc.jetstream = MagicMock(return_value=js)
        with patch("nats.aio.client.Client", return_value=nc), \
             patch.object(prov, "_ensure_stream", new=AsyncMock()) as ensure_stream:
            asyncio.run(prov.provision_outbox_event_stream("nats://unused:4222"))

        args = ensure_stream.await_args.args
        self.assertEqual(args[1:], ("RMP_EVENTS", list(EVENTS_STREAM_SUBJECTS), EVENTS_STREAM_CONFIG))

    def test_missing_stream_subjects_reports_old_stream(self):
        import asyncio

        from packages.services import jetstream_provisioning as prov

        infos = {"RMP": ["campaign.>"]}

        async def stream_info(name):
            if name not in infos:
                raise RuntimeError("stream not found")
            return SimpleNamespace(config=SimpleNamespace(subjects=infos[name]))

        js = MagicMock()
        js.stream_info = stream_info
        nc = AsyncMock()
        nc.jetstream = MagicMock(return_value=js)
        expected = {"RMP": CAMPAIGN_STREAM_SUBJECTS, "RMP_EVENTS": EVENTS_STREAM_SUBJECTS}
        with patch("nats.aio.client.Client", return_value=nc):
            self.assertEqual(asyncio.run(prov.missing_stream_subjects("nats://x", expected)),
                             ["stream RMP_EVENTS not found"])
            infos["RMP_EVENTS"] = ["delivery.>", "pop.>"]
            self.assertEqual(asyncio.run(prov.missing_stream_subjects("nats://x", expected)), [
                "stream RMP_EVENTS does not capture emergency.>",
                "stream RMP_EVENTS does not capture creative_asset.>",
            ])
            infos["RMP_EVENTS"] = list(EVENTS_STREAM_SUBJECTS)
            self.assertEqual(asyncio.run(prov.missing_stream_subjects("nats://x", expected)), [])

    def test_worker_provisions_both_streams(self):
        import asyncio
        import os

        worker = _load_worker()
        with patch.dict(os.environ, {"NATS_AUTO_PROVISION": "true"}), patch(
            "packages.services.jetstream_provisioning.provision_campaign_delivery",
            new=AsyncMock(return_value={"stream": "RMP", "durable": "rmp-campaign-consumer"}),
        ) as provision, patch(
            "packages.services.jetstream_provisioning.provision_outbox_event_stream",
            new=AsyncMock(return_value={"stream": "RMP_EVENTS"}),
        ) as provision_events:
            asyncio.run(worker._run_provisioning("nats://unused:4222"))

        self.assertEqual(provision.await_args.kwargs["subjects"], ["campaign.>"])
        provision_events.assert_awaited_once()

    def test_worker_without_auto_provision_rejects_old_stream(self):
        import asyncio
        import os

        worker = _load_worker()
        with patch.dict(os.environ, {"NATS_AUTO_PROVISION": "false"}), patch(
            "packages.services.jetstream_provisioning.missing_stream_subjects",
            new=AsyncMock(return_value=["stream RMP_EVENTS not found"]),
        ) as check:
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(worker._run_provisioning("nats://unused:4222"))

        self.assertIn("RMP_EVENTS not found", str(ctx.exception))
        self.assertEqual(check.await_args.args[1], {
            "RMP": CAMPAIGN_STREAM_SUBJECTS, "RMP_EVENTS": EVENTS_STREAM_SUBJECTS,
        })


class TestNonObjectEnvelopeIsPoison(_HealthIsolation):

    async def test_json_array_is_termed_and_loop_safe(self):
        consumer = _consumer()
        consumer._dead_letter = AsyncMock(return_value=True)
        msg = _Msg(b"[1, 2]", num_delivered=7)
        await consumer._process_one(msg)
        self.assertTrue(msg.terminated)
        self.assertIsNone(msg.nak_delay)
        consumer._dead_letter.assert_not_called()


class TestNonCampaignEventsAreAckedWithoutGeneration(_HealthIsolation):
    """Defence in depth: RMP holds campaign.> only, but the durable has no
    server-side filter — anything else that reaches it is acked, not retried."""

    async def test_each_non_campaign_type_is_acked(self):
        types = sorted(t for t in _event_types_in_code() if not t.startswith("campaign."))
        self.assertTrue(types)
        for event_type in types:
            consumer = _consumer()
            msg = _Msg(_envelope(event_type), num_delivered=1)
            with patch(
                "packages.services.campaign_event_handler.AsyncSession",
                side_effect=lambda engine: _Session(),
            ), patch("packages.domain.delivery.generate_manifests_for_campaign") as gen:
                await consumer._process_one(msg)
            with self.subTest(event_type=event_type):
                self.assertTrue(msg.acked)
                self.assertIsNone(msg.nak_delay)
                gen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
