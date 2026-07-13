#!/usr/bin/env python3
"""
NATS JetStream recovery diagnostics for Retail Media Platform.

Read-only by default — inspects NATS stream/consumer state and PostgreSQL
outbox event counts to produce a recovery summary.  Never mutates data.

Usage:
    # Check NATS + outbox status
    python scripts/check/nats_recovery_check.py

    # Include outbox event breakdowns per status
    python scripts/check/nats_recovery_check.py --detailed

    # JSON output for automation
    python scripts/check/nats_recovery_check.py --json

Environment:
    DATABASE_URL      — PostgreSQL connection (required)
    NATS_URL          — NATS server (default: nats://localhost:4222)
    NATS_STREAM       — JetStream stream name (default: RMP)
    NATS_DURABLE      — Durable consumer name (default: rmp-campaign-consumer)

Never prints secrets.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_URL = os.environ.get("DATABASE_URL", "")
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
NATS_STREAM = os.environ.get("NATS_STREAM", "RMP")
NATS_DURABLE = os.environ.get("NATS_DURABLE", "rmp-campaign-consumer")


def _redact_db_url(url: str) -> str:
    """Replace password in DATABASE_URL with ***."""
    import re
    return re.sub(r"://[^:]+:[^@]+@", r"://***:***@", url)


# ---------------------------------------------------------------------------
# NATS inspection
# ---------------------------------------------------------------------------


async def _check_nats() -> dict:
    """Inspect NATS stream and consumer state."""
    result = {
        "nats_reachable": False,
        "stream_exists": False,
        "consumer_exists": False,
        "stream_state": None,
        "consumer_state": None,
        "error": None,
    }

    try:
        from nats.aio.client import Client as NATS
        nc = NATS()
        await nc.connect(
            servers=[NATS_URL],
            connect_timeout=5.0,
        )
    except Exception as exc:
        result["error"] = f"NATS unreachable at {NATS_URL}: {exc}"
        return result

    try:
        js = nc.jetstream()
        result["nats_reachable"] = True

        # Stream info
        try:
            info = await js.stream_info(NATS_STREAM)
            result["stream_exists"] = True
            result["stream_state"] = {
                "messages": info.state.messages,
                "bytes": info.state.bytes,
                "first_seq": info.state.first_seq,
                "last_seq": info.state.last_seq,
                "consumer_count": info.state.consumer_count,
            }
        except Exception:
            result["stream_exists"] = False

        # Consumer info
        if result["stream_exists"]:
            try:
                ci = await js.consumer_info(NATS_STREAM, NATS_DURABLE)
                result["consumer_exists"] = True
                result["consumer_state"] = {
                    "delivered": ci.delivered.consumer_seq if hasattr(ci, "delivered") else None,
                    "ack_floor": ci.delivered.stream_seq if hasattr(ci, "delivered") else None,
                    "num_ack_pending": ci.num_ack_pending,
                    "num_pending": ci.num_pending,
                    "num_waiting": ci.num_waiting,
                    "num_redelivered": ci.num_redelivered,
                }
            except Exception:
                result["consumer_exists"] = False
    finally:
        await nc.drain()

    return result


# ---------------------------------------------------------------------------
# PostgreSQL outbox inspection
# ---------------------------------------------------------------------------


def _check_outbox() -> dict:
    """Inspect outbox event counts by status from PostgreSQL."""
    result = {
        "db_reachable": False,
        "total_events": 0,
        "pending": 0,
        "published": 0,
        "failed": 0,
        "dead_letter": 0,
        "recent_pending": [],
        "recent_dead_letter": [],
        "error": None,
    }

    if not DB_URL:
        result["error"] = "DATABASE_URL is not set"
        return result

    try:
        import sqlalchemy as sa
        engine = sa.create_engine(
            DB_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql+psycopg2"),
            echo=False,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as conn:
            result["db_reachable"] = True

            # Total and status counts
            rows = conn.execute(sa.text(
                "SELECT status, count(*) FROM outbox_events GROUP BY status"
            )).fetchall()
            for status, count in rows:
                result["total_events"] += count
                if status in ("pending", "published", "failed", "dead_letter"):
                    result[status] = count

            # Recent pending (last 10)
            pending_rows = conn.execute(sa.text(
                "SELECT id, event_type, aggregate_type, aggregate_id, attempt_count, created_at "
                "FROM outbox_events WHERE status = 'pending' "
                "ORDER BY created_at DESC LIMIT 10"
            )).fetchall()
            result["recent_pending"] = [
                {
                    "id": r[0], "event_type": r[1], "aggregate_type": r[2],
                    "aggregate_id": r[3], "attempt_count": r[4],
                    "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
                }
                for r in pending_rows
            ]

            # Recent dead_letter (last 5)
            dl_rows = conn.execute(sa.text(
                "SELECT id, event_type, aggregate_type, aggregate_id, "
                "attempt_count, last_error, created_at "
                "FROM outbox_events WHERE status = 'dead_letter' "
                "ORDER BY created_at DESC LIMIT 5"
            )).fetchall()
            result["recent_dead_letter"] = [
                {
                    "id": r[0], "event_type": r[1], "aggregate_type": r[2],
                    "aggregate_id": r[3], "attempt_count": r[4],
                    "last_error": (r[5] or "")[:120],  # truncate long errors
                    "created_at": r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
                }
                for r in dl_rows
            ]
    except Exception as exc:
        result["error"] = f"PostgreSQL unreachable: {exc}"

    return result


# ---------------------------------------------------------------------------
# Recovery recommendation
# ---------------------------------------------------------------------------


def _recommendation(nats: dict, outbox: dict) -> str:
    """Generate a recovery recommendation based on inspection results."""
    if not nats["nats_reachable"]:
        return "NATS is unreachable. Start NATS with JetStream enabled (nats-server -js), then re-run provisioning."

    if not outbox["db_reachable"]:
        return "PostgreSQL is unreachable. Restore PostgreSQL from backup, then re-run this check."

    if not nats["stream_exists"]:
        if outbox["total_events"] > 0:
            return (
                "NATS stream does not exist. Run provisioning (provision_campaign_delivery) "
                "to recreate stream and consumer. Then run outbox relay to republish pending events. "
                "Events already published will be skipped by JetStream dedup (Nats-Msg-Id = event_id)."
            )
        return "NATS stream does not exist and outbox is empty. Run provisioning before using the system."

    if outbox["pending"] > 0:
        return (
            f"NATS stream is healthy but {outbox['pending']} outbox events are still pending. "
            "Run outbox relay to publish them."
        )

    if outbox["dead_letter"] > 0:
        return (
            f"NATS stream is healthy but {outbox['dead_letter']} events are in dead_letter. "
            "Investigate failure causes. Dead_letter events require manual intervention — "
            "they will not be retried automatically."
        )

    if outbox["failed"] > 0:
        return (
            f"NATS stream is healthy but {outbox['failed']} events have transient failures. "
            "Relay will retry them automatically (attempt_count < max_attempts)."
        )

    return "All systems healthy. No recovery action needed."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    detailed = "--detailed" in sys.argv
    json_out = "--json" in sys.argv

    if json_out and detailed:
        print("ERROR: --json and --detailed are mutually exclusive", file=sys.stderr)
        return 1

    # Gather data
    nats = asyncio.run(_check_nats())
    outbox = _check_outbox()
    recommendation = _recommendation(nats, outbox)

    if json_out:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "nats_url": NATS_URL,
            "nats_stream": NATS_STREAM,
            "nats_durable": NATS_DURABLE,
            "nats": nats,
            "outbox": {k: v for k, v in outbox.items() if k not in ("recent_pending", "recent_dead_letter")},
            "recommendation": recommendation,
        }
        if detailed:
            report["outbox"]["recent_pending"] = outbox["recent_pending"]
            report["outbox"]["recent_dead_letter"] = outbox["recent_dead_letter"]
        print(json.dumps(report, indent=2, default=str))
        return 0

    # Human-readable output
    print("=" * 60)
    print("NATS JetStream Recovery Check")
    print("=" * 60)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"  Time:        {now}")
    print(f"  NATS URL:    {NATS_URL}")
    print(f"  Stream:      {NATS_STREAM}")
    print(f"  Durable:     {NATS_DURABLE}")
    if DB_URL:
        print(f"  Database:    {_redact_db_url(DB_URL)}")
    else:
        print("  Database:    NOT CONFIGURED")
    print()

    # NATS section
    print("--- NATS Status ---")
    if nats["error"]:
        print(f"  ERROR: {nats['error']}")
    else:
        print(f"  Reachable:       {'✅ yes' if nats['nats_reachable'] else '❌ no'}")
        print(f"  Stream exists:   {'✅ yes' if nats['stream_exists'] else '❌ no'}")
        print(f"  Consumer exists: {'✅ yes' if nats['consumer_exists'] else '❌ no'}")
        if nats["stream_state"]:
            ss = nats["stream_state"]
            print(f"  Stream messages: {ss['messages']}")
            print(f"  Stream bytes:    {ss['bytes']}")
        if nats["consumer_state"]:
            cs = nats["consumer_state"]
            print(f"  Ack pending:     {cs['num_ack_pending']}")
            print(f"  Pending:         {cs['num_pending']}")
            print(f"  Redelivered:     {cs['num_redelivered']}")

    print()
    print("--- Outbox Status ---")
    if outbox["error"]:
        print(f"  ERROR: {outbox['error']}")
    else:
        print(f"  Reachable:       {'✅ yes' if outbox['db_reachable'] else '❌ no'}")
        print(f"  Total events:    {outbox['total_events']}")
        print(f"  Published:       {outbox['published']}")
        print(f"  Pending:         {outbox['pending']}")
        print(f"  Failed:          {outbox['failed']}")
        print(f"  Dead letter:     {outbox['dead_letter']}")

        if detailed and outbox["recent_pending"]:
            print()
            print("  Recent pending (last 10):")
            for e in outbox["recent_pending"]:
                print(f"    {e['event_type']} | {e['aggregate_type']}={e['aggregate_id'][:8]}... "
                      f"| attempts={e['attempt_count']}")

        if detailed and outbox["recent_dead_letter"]:
            print()
            print("  Recent dead_letter (last 5):")
            for e in outbox["recent_dead_letter"]:
                print(f"    {e['event_type']} | {e['aggregate_type']}={e['aggregate_id'][:8]}... "
                      f"| attempts={e['attempt_count']} | {e['last_error']}")

    print()
    print("--- Recommendation ---")
    print(f"  {recommendation}")
    print()

    # Overall status
    healthy = (
        nats["nats_reachable"]
        and nats["stream_exists"]
        and outbox["db_reachable"]
        and outbox["dead_letter"] == 0
    )
    if healthy and outbox["pending"] == 0:
        print("=== Status: HEALTHY ===")
    elif healthy and outbox["pending"] > 0:
        print("=== Status: DEGRADED (pending events) ===")
    else:
        print("=== Status: RECOVERY NEEDED ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
