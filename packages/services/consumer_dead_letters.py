"""Dead letters of the orchestrator campaign consumer (RM-STAB-020, RF-10).

Retry policy: the consumer counts deliveries itself (``msg.metadata.num_delivered``)
— the server-side ``max_deliver`` stays -1, so the durable consumer config never
changes and is never recreated.  A failed delivery is nak'd with a growing
delay; the failure on the last allowed delivery stores the message in
``consumer_dead_letters`` and terminates it.  If that write fails the message is
nak'd with the longest delay instead — it is never dropped.

Operator CLI (inside the worker image, ``DATABASE_URL`` = the app role)::

    python -m packages.services.consumer_dead_letters list [--all]
    python -m packages.services.consumer_dead_letters replay <id>
    python -m packages.services.consumer_dead_letters replay --all

``replay`` re-enqueues the original event as a new outbox event (same type,
aggregate, payload, headers) and marks the row ``replayed`` in one transaction.
Manifest generation is idempotent, so a replay is safe to repeat after a fix.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_MAX_DELIVERIES = 7
DEFAULT_BACKOFF_SECONDS: tuple[float, ...] = (5.0, 30.0, 120.0, 600.0, 1800.0, 3600.0)

ENV_MAX_DELIVERIES = "CAMPAIGN_CONSUMER_MAX_DELIVERIES"
ENV_BACKOFF_SECONDS = "CAMPAIGN_CONSUMER_BACKOFF_SECONDS"


@dataclass(frozen=True)
class RetryPolicy:
    """How many deliveries a campaign event gets, and the nak delay between them."""

    max_deliveries: int = DEFAULT_MAX_DELIVERIES
    backoff_seconds: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS

    def __post_init__(self) -> None:
        if self.max_deliveries < 1:
            raise ValueError("max_deliveries must be >= 1")
        if not self.backoff_seconds or any(
            not math.isfinite(d) or d < 0 for d in self.backoff_seconds
        ):
            raise ValueError("backoff_seconds must be a non-empty list of finite, non-negative delays")

    def nak_delay(self, num_delivered: int) -> float:
        """Delay before the next delivery after delivery number ``num_delivered`` failed."""
        index = min(max(num_delivered, 1) - 1, len(self.backoff_seconds) - 1)
        return self.backoff_seconds[index]

    @property
    def max_delay(self) -> float:
        return self.backoff_seconds[-1]


def retry_policy_from_env(environ: Mapping[str, str] | None = None) -> RetryPolicy:
    """Read the policy from env; absent keys keep the defaults, bad values raise ValueError."""
    env = os.environ if environ is None else environ
    max_deliveries = DEFAULT_MAX_DELIVERIES
    backoff = DEFAULT_BACKOFF_SECONDS

    if ENV_MAX_DELIVERIES in env:
        raw = env[ENV_MAX_DELIVERIES].strip()
        try:
            max_deliveries = int(raw)
        except ValueError:
            raise ValueError(f"{ENV_MAX_DELIVERIES} must be an integer, got {raw!r}") from None
    if ENV_BACKOFF_SECONDS in env:
        raw = env[ENV_BACKOFF_SECONDS].strip()
        try:
            backoff = tuple(float(part) for part in raw.split(",")) if raw else ()
        except ValueError:
            raise ValueError(f"{ENV_BACKOFF_SECONDS} must be comma-separated seconds, got {raw!r}") from None

    return RetryPolicy(max_deliveries=max_deliveries, backoff_seconds=backoff)


# ---------------------------------------------------------------------------
# Storage — callers own the session and set the worker admin context
# ---------------------------------------------------------------------------


async def record_dead_letter(
    session: AsyncSession,
    *,
    envelope: dict,
    deliveries: int,
    stream_sequence: int | None,
    last_error: str,
) -> str:
    """Insert one dead letter; does not commit.  Returns its id.

    A message that is already dead-lettered (same event_id, not replayed) is
    not stored twice — e.g. when ``term()`` failed and it came back.  Fields
    are coerced and cut to the column sizes so a malformed envelope cannot
    make the write fail forever.
    """
    from packages.domain.models import ConsumerDeadLetter

    event_id = _text(envelope.get("event_id"), 64)
    if event_id:
        existing = (await session.execute(
            select(ConsumerDeadLetter.id).where(
                ConsumerDeadLetter.event_id == event_id, ConsumerDeadLetter.status == "dead",
            ).limit(1)
        )).scalar_one_or_none()
        if existing is not None:
            return existing
    else:
        # Without an id there is nothing to deduplicate on — store every one.
        event_id = "?"

    row = ConsumerDeadLetter(
        event_id=event_id,
        event_type=_text(envelope.get("event_type"), 128) or "?",
        aggregate_type=_text(envelope.get("aggregate_type"), 64),
        aggregate_id=_text(envelope.get("aggregate_id"), 36),
        envelope_json=envelope,
        deliveries=deliveries,
        stream_sequence=stream_sequence,
        last_error=last_error,
        status="dead",
    )
    session.add(row)
    await session.flush()
    return row.id


async def count_dead_letters(session: AsyncSession) -> int:
    """Rows still waiting for the operator (status 'dead')."""
    from sqlalchemy import func

    from packages.domain.models import ConsumerDeadLetter

    return (await session.execute(
        select(func.count()).select_from(ConsumerDeadLetter).where(ConsumerDeadLetter.status == "dead")
    )).scalar_one()


def _text(value, size: int) -> str | None:
    return None if value is None else str(value)[:size]


async def list_dead_letters(
    session: AsyncSession, *, include_replayed: bool = False, limit: int | None = 500,
) -> list:
    from packages.domain.models import ConsumerDeadLetter

    stmt = select(ConsumerDeadLetter).order_by(ConsumerDeadLetter.created_at)
    if limit is not None:
        stmt = stmt.limit(limit)
    if not include_replayed:
        stmt = stmt.where(ConsumerDeadLetter.status == "dead")
    return list((await session.execute(stmt)).scalars().all())


async def replay_dead_letter(session: AsyncSession, dead_letter_id: str) -> str | None:
    """Re-enqueue a dead letter as a new outbox event; does not commit.

    Returns the new outbox event id, or None when the row does not exist or was
    already replayed.  The row is claimed with a conditional UPDATE, so two
    concurrent replays of one row enqueue a single event.
    """
    from packages.domain.models import ConsumerDeadLetter
    from packages.domain.repository import enqueue_outbox_event

    claimed = (await session.execute(
        update(ConsumerDeadLetter)
        .where(ConsumerDeadLetter.id == dead_letter_id, ConsumerDeadLetter.status == "dead")
        .values(status="replayed", replayed_at=datetime.now(timezone.utc))
        .returning(ConsumerDeadLetter.envelope_json)
    )).first()
    if claimed is None:
        return None

    envelope = claimed[0]
    outbox_id = await enqueue_outbox_event(
        session,
        event_type=envelope["event_type"],
        event_version=envelope.get("event_version") or "1.0",
        aggregate_type=envelope["aggregate_type"],
        aggregate_id=envelope["aggregate_id"],
        payload=envelope.get("payload") or {},
        headers=envelope.get("headers") or {},
    )
    await session.execute(
        update(ConsumerDeadLetter)
        .where(ConsumerDeadLetter.id == dead_letter_id)
        .values(replay_outbox_event_id=outbox_id)
    )
    return outbox_id


# ---------------------------------------------------------------------------
# Operator CLI
# ---------------------------------------------------------------------------


async def _cli(args) -> int:
    from packages.domain.database import create_engine, set_worker_admin_context

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("DATABASE_URL is not set")
        return 2

    engine = create_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            await set_worker_admin_context(session)
            if args.command == "list":
                limit = 500
                rows = await list_dead_letters(session, include_replayed=args.all, limit=limit)
                for r in rows:
                    print(
                        f"{r.id}\t{r.status}\t{r.created_at.isoformat()}\t{r.event_type}\t"
                        f"event_id={r.event_id}\taggregate_id={r.aggregate_id}\t"
                        f"deliveries={r.deliveries}\terror={r.last_error}"
                    )
                print(f"{len(rows)} row(s)")
                if len(rows) == limit:
                    print(f"WARNING: output limited to {limit} rows")
                return 0

            if args.all:
                ids = [r.id for r in await list_dead_letters(session, limit=None)]
            elif args.id:
                ids = [args.id]
            else:
                print("replay needs <id> or --all")
                return 2
            replayed = 0
            for dead_letter_id in ids:
                # One bad row (e.g. an envelope without aggregate_type) must not
                # roll back the rows already replayed in this run.
                try:
                    async with session.begin_nested():
                        outbox_id = await replay_dead_letter(session, dead_letter_id)
                except Exception as exc:
                    print(f"{dead_letter_id}\tfailed\t{type(exc).__name__}")
                    continue
                if outbox_id is None:
                    print(f"{dead_letter_id}\tnot found or already replayed")
                else:
                    replayed += 1
                    print(f"{dead_letter_id}\treplayed\toutbox_event_id={outbox_id}")
            await session.commit()
            print(f"{replayed} replayed")
            return 0 if replayed == len(ids) else 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(prog="python -m packages.services.consumer_dead_letters")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="dead letters (default: not yet replayed)")
    p_list.add_argument("--all", action="store_true", help="include replayed rows")
    p_replay = sub.add_parser("replay", help="re-enqueue into the outbox")
    p_replay.add_argument("id", nargs="?")
    p_replay.add_argument("--all", action="store_true", help="every row not yet replayed")
    args = parser.parse_args(argv)
    return asyncio.run(_cli(args))


if __name__ == "__main__":
    raise SystemExit(main())
