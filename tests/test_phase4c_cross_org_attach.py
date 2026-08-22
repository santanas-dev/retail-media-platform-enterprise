#!/usr/bin/env python3
"""CAMPAIGN-UX-002A — cross-org attach → 422 backend test."""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from packages.domain.exceptions import CrossOrgReferenceError


class TestCrossOrgAttach422(unittest.TestCase):
    """Repository-level: cross-org attach raises, same-org succeeds."""

    def test_cross_org_attach_raises_cross_org_reference_error(self):
        from packages.domain.models import Campaign, CreativeAsset
        from packages.domain.repository import attach_creative_to_campaign

        async def _run():
            sess = AsyncMock()
            camp = MagicMock(spec=Campaign)
            camp.status = "draft"
            camp.advertiser_organization_id = "org-1"
            asset = MagicMock(spec=CreativeAsset)
            asset.advertiser_organization_id = "org-2"
            sess.execute.side_effect = [
                MagicMock(**{"scalar_one_or_none.return_value": camp}),
                MagicMock(**{"scalar_one_or_none.return_value": asset}),
            ]
            with self.assertRaises(CrossOrgReferenceError) as ctx:
                await attach_creative_to_campaign(
                    sess, campaign_id="c1", creative_asset_id="ca-org2",
                )
            self.assertIn("does not belong", str(ctx.exception))

        asyncio.run(_run())

    def test_same_org_attach_no_cross_org_error(self):
        from packages.domain.models import Campaign, CreativeAsset
        from packages.domain.repository import attach_creative_to_campaign

        async def _run():
            sess = AsyncMock()
            camp = MagicMock(spec=Campaign)
            camp.status = "draft"
            camp.advertiser_organization_id = "org-1"
            asset = MagicMock(spec=CreativeAsset)
            asset.advertiser_organization_id = "org-1"
            sess.execute.side_effect = [
                MagicMock(**{"scalar_one_or_none.return_value": camp}),
                MagicMock(**{"scalar_one_or_none.return_value": asset}),
                MagicMock(**{"scalar_one_or_none.return_value": None}),
            ]
            sess.add = MagicMock()
            # Should not raise CrossOrgReferenceError
            try:
                await attach_creative_to_campaign(
                    sess, campaign_id="c1", creative_asset_id="ca-org1",
                )
            except CrossOrgReferenceError:
                self.fail("Same-org attach must not raise CrossOrgReferenceError")
            self.assertTrue(sess.add.called, "Expected add() to be called for same-org attach")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
