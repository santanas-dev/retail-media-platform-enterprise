"""RM-STAB-021 — надёжность NATS (RF-11).

* JetStream хранит данные в смонтированном томе: у сервиса nats в pilot- и
  phase1-compose `-sd <путь>`, и этот путь — точка монтирования тома. Без `-sd`
  nats-server пишет в `/tmp/nats/jetstream` контейнера, и streams с сообщениями
  теряются при каждом пересоздании контейнера (подтверждено на стенде).
* Провижининг streams обязателен перед relay: выполняется при любом NATS_URL
  (relay публикует и без consumer), сбой завершает старт воркера; только
  явный dev/test-режим OUTBOX_RELAY_ALLOW_STUB=true его логирует.

Живое доказательство сохранности (пересоздание контейнера nats) — локальный
прогон pilot-стека, журнал RF-11.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILES = (
    REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml",
    REPO_ROOT / "infra" / "compose" / "docker-compose.phase1.yml",
)
WORKER_MAIN = REPO_ROOT / "apps" / "orchestrator-worker" / "main.py"


def _load_worker():
    spec = importlib.util.spec_from_file_location(
        "worker_main_rm_stab_021", WORKER_MAIN, submodule_search_locations=[],
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


class TestJetStreamStoreIsOnTheVolume(unittest.TestCase):

    def test_store_dir_is_the_mounted_volume(self):
        for path in COMPOSE_FILES:
            nats = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]["nats"]
            command = list(nats["command"])
            with self.subTest(compose=path.name):
                self.assertIn("-js", command)
                self.assertIn("-sd", command, "JetStream would store in /tmp inside the container")
                store_dir = command[command.index("-sd") + 1]
                mounts = {}
                for volume in nats.get("volumes", []):
                    source, target = str(volume).split(":")[:2]
                    mounts[target] = source
                self.assertIn(store_dir, mounts, f"-sd {store_dir} is not a mounted volume")
                # A named volume (not a bind into the repo) — survives recreate.
                self.assertFalse(mounts[store_dir].startswith((".", "/")))


class TestStartupProvisioning(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.worker = _load_worker()

    async def test_runs_when_consumer_disabled(self):
        with patch.dict(os.environ, {"CAMPAIGN_CONSUMER_ENABLED": "false"}), \
             patch.object(self.worker, "_run_provisioning", new=AsyncMock(return_value=True)) as run:
            await self.worker._startup_provisioning("nats://nats:4222")
        run.assert_awaited_once_with("nats://nats:4222")

    async def test_skipped_without_nats_url(self):
        with patch.object(self.worker, "_run_provisioning", new=AsyncMock()) as run:
            await self.worker._startup_provisioning("")
        run.assert_not_awaited()

    async def test_failure_stops_the_start(self):
        with patch.dict(os.environ, {"OUTBOX_RELAY_ALLOW_STUB": ""}), patch.object(
            self.worker, "_run_provisioning",
            new=AsyncMock(side_effect=RuntimeError("stream RMP_EVENTS not found")),
        ):
            with self.assertRaises(RuntimeError):
                await self.worker._startup_provisioning("nats://nats:4222")

    async def test_stub_mode_only_logs(self):
        with patch.dict(os.environ, {"OUTBOX_RELAY_ALLOW_STUB": "true"}), patch.object(
            self.worker, "_run_provisioning", new=AsyncMock(side_effect=RuntimeError("NATS down")),
        ), self.assertLogs("orchestrator-worker", level="ERROR") as logs:
            await self.worker._startup_provisioning("nats://nats:4222")
        self.assertIn("OUTBOX_RELAY_ALLOW_STUB", "\n".join(logs.output))

    async def test_stream_check_errors_surface_as_runtime_error(self):
        # Without auto-provision the stream check may fail with anything (e.g.
        # nats-py missing → ImportError); it must reach _startup_provisioning
        # as RuntimeError so the stub mode can log it and the start can stop.
        with patch.dict(os.environ, {"NATS_AUTO_PROVISION": ""}), patch(
            "packages.services.jetstream_provisioning.missing_stream_subjects",
            new=AsyncMock(side_effect=ModuleNotFoundError("No module named 'nats'")),
        ):
            with self.assertRaises(RuntimeError):
                await self.worker._run_provisioning("nats://nats:4222")
            with patch.dict(os.environ, {"OUTBOX_RELAY_ALLOW_STUB": "true"}), \
                 self.assertLogs("orchestrator-worker", level="ERROR"):
                await self.worker._startup_provisioning("nats://nats:4222")

    async def test_main_stops_before_relay_when_provisioning_fails(self):
        env = {
            "NATS_URL": "nats://nats:4222",
            "CAMPAIGN_CONSUMER_ENABLED": "false",
            "OUTBOX_RELAY_ALLOW_STUB": "",
        }
        with patch.dict(os.environ, env), \
             patch.object(self.worker, "health_http_server", new=AsyncMock()), \
             patch.object(self.worker, "_run_provisioning",
                          new=AsyncMock(side_effect=RuntimeError("stream RMP not found"))), \
             patch.object(self.worker, "_start_relay", new=AsyncMock()) as relay, \
             patch.object(self.worker, "_start_consumer", new=AsyncMock()) as consumer:
            # A main() that swallows the failure would start the relay and wait
            # for a shutdown signal forever — the timeout turns that into a failure.
            with self.assertRaises(RuntimeError):
                await asyncio.wait_for(self.worker.main(), timeout=5)
        relay.assert_not_awaited()
        consumer.assert_not_awaited()

    def test_main_provisions_before_relay_without_swallowing(self):
        tree = ast.parse(WORKER_MAIN.read_text(encoding="utf-8"))
        main = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
        calls = sorted(
            (n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)),
            key=lambda n: (n.lineno, n.col_offset),
        )
        names = [n.func.id for n in calls]
        self.assertIn("_startup_provisioning", names)
        self.assertNotIn("_run_provisioning", names, "main() must not call (and swallow) provisioning directly")
        # Source order, and both at the top level of main() (not inside an if).
        order = [c for c in names if c in ("_startup_provisioning", "_start_relay")]
        self.assertEqual(order[:2], ["_startup_provisioning", "_start_relay"])
        top_level = {
            n.value.value.func.id for n in main.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Await)
            and isinstance(n.value.value, ast.Call) and isinstance(n.value.value.func, ast.Name)
        }
        self.assertLessEqual({"_startup_provisioning", "_start_relay"}, top_level)
        # Not wrapped in try/except inside main().
        for node in ast.walk(main):
            if isinstance(node, ast.Try):
                inner = [n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
                self.assertNotIn("_startup_provisioning", inner)


if __name__ == "__main__":
    unittest.main()
