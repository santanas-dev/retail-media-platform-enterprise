"""
T1 — Behavioural Test Data Builder.

Minimal, explicit builder for behavioural test fixtures.
No magic — every method is a single-purpose INSERT with a generated ID.
cleanup() deletes all rows matching the builder's prefix in reverse FK order.

Usage:
    from tests.behavioral.builder import BehBuilder

    b = BehBuilder("beh-t1")
    rid = b.retailer()
    chain = b.store_chain()
    cd = b.channel_device_type()
    org = b.advertiser(rid)
    camp = b.campaign(org["org_id"], org["contract_id"], rid)
    dev = b.device(chain["store_id"], cd["device_type_id"], rid)
    man = b.manifest(camp, dev, rid)
    # … test …
    b.cleanup()
"""

from __future__ import annotations

import asyncio

from tests.behavioral.conftest import _run_sql


# ── FK-safe table order for cleanup (children before parents) ──

_CLEANUP_TABLES = [
    "pop_events_raw",
    "pop_dedup_index",
    "delivery_manifest_surfaces",
    "delivery_manifest_assets",
    "delivery_manifests",
    "creative_assets",
    "display_surfaces",
    "logical_carriers",
    "physical_devices",
    "campaigns",
    "advertiser_contracts",
    "advertiser_organizations",
    "device_types",
    "channels",
    "stores",
    "clusters",
    "branches",
    "retailers",
    "emergency_overrides",
]


def _run(sql: str) -> None:
    asyncio.run(_run_sql(sql))


class BehBuilder:
    """Explicit test-data builder with prefix-scoped IDs and cleanup."""

    def __init__(self, prefix: str) -> None:
        assert prefix, "prefix must be non-empty"
        # Normalise: strip trailing hyphen, add one back
        self.prefix = prefix.rstrip("-") + "-"
        self._n = 0

    # ── internal helpers ──────────────────────────────────────────────

    def _uid(self, entity: str) -> str:
        """Generate a prefix-scoped, entity-tagged, unique ID."""
        self._n += 1
        return f"{self.prefix}{entity}-{self._n:04d}"

    def _exec(self, sql: str) -> None:
        _run(sql)

    # ── public builders ───────────────────────────────────────────────

    def retailer(
        self,
        code: str | None = None,
        legal_name: str = "T1 Retailer",
        display_name: str = "T1",
        status: str = "active",
    ) -> str:
        """Create retailer → return id."""
        rid = self._uid("ret")
        self._exec(f"""
        INSERT INTO retailers (id, code, legal_name, display_name, status)
        VALUES ('{rid}', '{code or rid}', '{legal_name}', '{display_name}', '{status}')
        ON CONFLICT (id) DO NOTHING;
        """)
        return rid

    def store_chain(
        self,
        timezone: str = "Europe/Moscow",
    ) -> dict[str, str]:
        """Create branch → cluster → store. Returns {branch_id, cluster_id, store_id}."""
        bid = self._uid("br")
        cid = self._uid("cl")
        sid = self._uid("st")
        self._exec(f"""
        INSERT INTO branches (id, code, name, timezone, is_active)
        VALUES ('{bid}', '{bid}', 'Branch {bid[-4:]}', '{timezone}', true)
        ON CONFLICT (code) DO NOTHING;
        """)
        self._exec(f"""
        INSERT INTO clusters (id, branch_id, code, name, is_active)
        VALUES ('{cid}', '{bid}', '{cid}', 'Cluster {cid[-4:]}', true)
        ON CONFLICT (code) DO NOTHING;
        """)
        self._exec(f"""
        INSERT INTO stores (id, cluster_id, code, name, is_active)
        VALUES ('{sid}', '{cid}', '{sid}', 'Store {sid[-4:]}', true)
        ON CONFLICT (code) DO NOTHING;
        """)
        return {"branch_id": bid, "cluster_id": cid, "store_id": sid}

    def channel_device_type(
        self,
        player_runtime: str = "chromium",
    ) -> dict[str, str]:
        """Create channel → device_type. Returns {channel_id, device_type_id}."""
        chid = self._uid("ch")
        dtid = self._uid("dt")
        self._exec(f"""
        INSERT INTO channels (id, code, name, is_active)
        VALUES ('{chid}', '{chid}', 'Channel {chid[-4:]}', true)
        ON CONFLICT (code) DO NOTHING;
        """)
        self._exec(f"""
        INSERT INTO device_types (id, channel_id, code, name, player_runtime)
        VALUES ('{dtid}', '{chid}', '{dtid}', 'DeviceType {dtid[-4:]}', '{player_runtime}')
        ON CONFLICT (code) DO NOTHING;
        """)
        return {"channel_id": chid, "device_type_id": dtid}

    def advertiser(
        self,
        retailer_id: str,
        org_code: str | None = None,
        contract_code: str | None = None,
    ) -> dict[str, str]:
        """Create advertiser_org → advertiser_contract. Returns {org_id, contract_id}."""
        oid = self._uid("org")
        cid = self._uid("cont")
        self._exec(f"""
        INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
        VALUES ('{oid}', '{org_code or oid}', 'Org {oid[-4:]}', 'Org {oid[-4:]}', 'active', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)
        self._exec(f"""
        INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status, retailer_id)
        VALUES ('{cid}', '{oid}', '{contract_code or cid}', 'Contract {cid[-4:]}', 'active', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)
        return {"org_id": oid, "contract_id": cid}

    def campaign(
        self,
        org_id: str,
        contract_id: str,
        retailer_id: str,
        code: str | None = None,
        status: str = "active",
    ) -> str:
        """Create campaign → return id."""
        cid = self._uid("camp")
        self._exec(f"""
        INSERT INTO campaigns (id, code, name, advertiser_organization_id,
            advertiser_contract_id, status, start_at, end_at, retailer_id)
        VALUES ('{cid}', '{code or cid}', 'Campaign {cid[-4:]}',
            '{org_id}', '{contract_id}',
            '{status}', '2026-01-01T00:00:00Z', '2027-12-31T23:59:59Z', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)
        return cid

    def device(
        self,
        store_id: str,
        device_type_id: str,
        retailer_id: str,
        fingerprint: str | None = None,
        status: str = "active",
    ) -> str:
        """Create physical_device → return id."""
        did = self._uid("dev")
        fp = fingerprint or f"fp-{did[-4:]}"
        self._exec(f"""
        INSERT INTO physical_devices (id, store_id, device_type_id, code,
            hardware_fingerprint, status, retailer_id)
        VALUES ('{did}', '{store_id}', '{device_type_id}', '{did}',
            '{fp}', '{status}', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)
        return did

    def manifest(
        self,
        campaign_id: str,
        device_id: str,
        retailer_id: str,
        manifest_version: int = 1,
    ) -> str:
        """Create delivery_manifest → return id."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        mid = self._uid("dm")
        mfid = f"sha256:{mid}"
        self._exec(f"""
        INSERT INTO delivery_manifests (id, manifest_id, campaign_id,
            physical_device_id, manifest_version, status,
            content_hash, generated_at, created_at, retailer_id)
        VALUES ('{mid}', '{mfid}', '{campaign_id}',
            '{device_id}', {manifest_version}, 'generated',
            '{mfid}-hash', '{now}', '{now}', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)
        return mid

    def surface(
        self,
        store_id: str,
        device_id: str,
        retailer_id: str,
    ) -> str:
        """Create logical_carrier → display_surface. Returns surface_id."""
        lcid = self._uid("lc")
        sid = self._uid("surf")
        self._exec(f"""
        INSERT INTO logical_carriers (id, physical_device_id, code, carrier_type)
        VALUES ('{lcid}', '{device_id}', '{lcid}', 'direct')
        ON CONFLICT (code) DO NOTHING;
        """)
        self._exec(f"""
        INSERT INTO display_surfaces (id, logical_carrier_id, store_id, code,
            resolution_w, resolution_h, retailer_id)
        VALUES ('{sid}', '{lcid}', '{store_id}', '{sid}', 1440, 1080, '{retailer_id}')
        ON CONFLICT (code) DO NOTHING;
        """)
        return sid

    def creative_asset(
        self,
        advertiser_organization_id: str,
        status: str = "ready",
    ) -> str:
        """Create creative_asset. Returns asset_id."""
        aid = self._uid("asset")
        key = f"assets/{aid}.png"
        self._exec(f"""
        INSERT INTO creative_assets (id, advertiser_organization_id, code, name,
            media_type, storage_bucket, storage_key, sha256_checksum,
            file_size_bytes, status, moderation_status)
        VALUES ('{aid}', '{advertiser_organization_id}', '{aid}', 'Asset {aid[-4:]}',
            'image/png', 'beh-bucket', '{key}', 'sha256:deadbeef0000000000000000', 1024,
            '{status}', 'approved')
        ON CONFLICT (id) DO NOTHING;
        """)
        return aid

    def manifest_surface(
        self,
        manifest_id: str,
        surface_id: str,
        retailer_id: str,
    ) -> None:
        """Link manifest → display_surface via delivery_manifest_surfaces."""
        jid = self._uid("dms")
        self._exec(f"""
        INSERT INTO delivery_manifest_surfaces (id, manifest_id, display_surface_id,
            retailer_id)
        VALUES ('{jid}', '{manifest_id}', '{surface_id}', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)

    def manifest_asset(
        self,
        manifest_id: str,
        asset_id: str,
        retailer_id: str,
    ) -> None:
        """Link manifest → creative_asset via delivery_manifest_assets."""
        jid = self._uid("dma")
        self._exec(f"""
        INSERT INTO delivery_manifest_assets (id, manifest_id, creative_asset_id,
            sha256_checksum, media_type, retailer_id)
        VALUES ('{jid}', '{manifest_id}', '{asset_id}', 'sha256:deadbeef0000000000000000',
            'image/png', '{retailer_id}')
        ON CONFLICT (id) DO NOTHING;
        """)

    def emergency_override(
        self,
        reason: str = "T1 test emergency",
        active: bool = True,
    ) -> str:
        """Create emergency_override → return id."""
        eid = self._uid("em")
        self._exec(f"""
        DELETE FROM emergency_overrides WHERE id LIKE '{self.prefix}%';
        INSERT INTO emergency_overrides (id, level, active, reason, activated_at)
        VALUES ('{eid}', 'global', {'true' if active else 'false'}, '{reason}', NOW())
        ON CONFLICT (id) DO NOTHING;
        """)
        return eid

    def deactivate_emergency(self) -> None:
        """Delete all emergency_overrides matching this prefix."""
        self._exec(f"DELETE FROM emergency_overrides WHERE id LIKE '{self.prefix}%';")

    def cleanup(self) -> None:
        """Delete all rows matching this builder's prefix, in FK-safe order."""
        for tbl in _CLEANUP_TABLES:
            self._exec(f"DELETE FROM {tbl} WHERE id LIKE '{self.prefix}%';")
