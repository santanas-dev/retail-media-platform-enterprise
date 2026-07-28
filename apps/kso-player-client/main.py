#!/usr/bin/env python3
"""KSO Player Client — first runnable enterprise KSO client.

Usage:
  python -m apps.kso-player-client.main --once

Environment:
  PLAYER_GATEWAY_URL   — device-gateway base URL (default: http://localhost:8001)
  PLAYER_SIGNING_KEY   — MANIFEST_SIGNING_KEY for signature verification
  PLAYER_DEVICE_JWT    — pre-configured device JWT (skip auth)
  PLAYER_DEVICE_CODE   — device code for auth
  PLAYER_DEVICE_SECRET — device secret for auth
  PLAYER_RETAILER_ID   — retailer UUID (optional)
  PLAYER_MAX_RETRIES   — max HTTP retries (default: 3)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from player_client.config import load_config
from player_client.http import PlayerHttpClient
from player_client.auth import authenticate
from player_client.manifest import fetch_manifest
from player_client.heartbeat import send_heartbeat
from player_client.pop import send_pop_batch
from player_client.retry_backoff import PlayerHttpError


def run_once(config) -> int:
    max_retries = config.max_retries
    http = PlayerHttpClient(config.base_url)

    # 1. Auth
    if config.device_jwt:
        http.token = config.device_jwt
        print(f"[AUTH] using configured JWT")
    else:
        try:
            token = authenticate(http, max_retries)
            http.token = token.access_token
            print(f"[AUTH] ok (valid until {token.expires_at:.0f})")
        except (ValueError, PlayerHttpError) as e:
            print(f"[AUTH] FAILED: {e}")
            return 3

    # 2. Manifest
    try:
        manifest = fetch_manifest(http, config.signing_key, max_retries)
        print(f"[MANIFEST] {manifest.manifest_id} (verified={manifest.verified}, emergency={manifest.emergency_active})")
    except (ValueError, PlayerHttpError) as e:
        print(f"[MANIFEST] FAILED: {e}")
        return 4

    if manifest.emergency_active:
        print("[EMERGENCY] active — skipping PoP")
    else:
        # 3. Heartbeat
        try:
            hb = send_heartbeat(http, max_retries=max_retries)
            print(f"[HEARTBEAT] accepted={hb.accepted} server_time={hb.server_time}")
        except (ValueError, PlayerHttpError) as e:
            print(f"[HEARTBEAT] FAILED: {e}")
            return 5

        # 4. PoP
        playlist = manifest.playlist
        if not playlist:
            print("[POP] no playlist items — skipping")
        else:
            slot = playlist[0]
            try:
                pop = send_pop_batch(
                    http,
                    manifest_id=manifest.manifest_id,
                    device_id=manifest.device_id,
                    campaign_id=slot.get("campaign_id", ""),
                    surface_id=slot.get("surface_id", ""),
                    creative_asset_id=slot.get("creative_asset_id", slot.get("id", "")),
                    duration_ms=slot.get("duration_ms", 10000),
                    max_retries=max_retries,
                )
                print(f"[POP] accepted={pop.accepted_count} rejected={pop.rejected_count} quarantined={pop.quarantined_count}")
                if not pop.accepted:
                    print("[POP] WARNING: no events accepted")
                    return 6
            except (ValueError, PlayerHttpError) as e:
                print(f"[POP] FAILED: {e}")
                return 6

    print("[DONE] client loop complete")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="KSO Player Client")
    parser.add_argument("--once", action="store_true", help="Run one client loop")
    args = parser.parse_args()

    if not args.once:
        parser.print_help()
        sys.exit(1)

    cfg = load_config()
    sys.exit(run_once(cfg))


if __name__ == "__main__":
    main()
