"""
Identity API Router — backward-compatible aggregator.

Prefixed router that includes all decomposed domain routers.
The original 2097-line single file has been split by bounded context
into packages/api/identity_routes/.

Import compatibility: ``from packages.api.identity import router``
continues to work unchanged.

Test compatibility: module-level re-exports for ``@patch("packages.api.identity.XXX")``
targets used by existing tests.
"""

from fastapi import APIRouter

from packages.api.identity_routes.users import router as users_router
from packages.api.identity_routes.ad_settings import router as ad_settings_router
from packages.api.identity_routes.advertisers import router as advertisers_router
from packages.api.identity_routes.campaigns import router as campaigns_router
from packages.api.identity_routes.creatives import router as creatives_router
from packages.api.identity_routes.reporting import router as reporting_router
from packages.api.identity_routes.inventory import router as inventory_router
from packages.api.identity_routes.devices import router as devices_router
from packages.api.identity_routes.emergency import router as emergency_router
from packages.api.identity_routes.advertiser_applications import router as advertiser_applications_router

# Backward-compatible re-exports for test patches.
# Tests patch ``packages.api.identity.repository.XXX`` — ``repository`` must be
# available as a module attribute.  All sub-routers use ``repository.XXX()``
# style (consistent with creatives.py / users.py), so patching through the
# module works regardless of which sub-router handles the request.
from packages.domain import repository  # noqa: F401 — patched by tests

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])

router.include_router(users_router)
router.include_router(ad_settings_router)
router.include_router(advertisers_router)
router.include_router(campaigns_router)
router.include_router(creatives_router)
router.include_router(reporting_router)
router.include_router(inventory_router)
router.include_router(devices_router)
router.include_router(emergency_router)
router.include_router(advertiser_applications_router)
