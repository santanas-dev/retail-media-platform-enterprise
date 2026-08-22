"""Regression: server-generated user code is unique and collision-safe.

Locks the product fix for `create_local_advertiser`: the previous
``username.upper().replace(" ", "_")[:8]`` truncated the code to 8 chars, so
any two usernames sharing a prefix (e.g. every ``smoke_adv_*``) collided on the
``ix_users_code`` unique constraint and the endpoint returned a raw HTTP 500.
"""
import re

from packages.api.identity_routes.users import _generate_user_code
from packages.domain.schemas import CreateLocalAdvertiserRequest


def test_user_code_fits_schema_constraints():
    """Generated code stays under users.code String(64) and has the right shape."""
    code = _generate_user_code("a b c")
    assert len(code) <= 64
    # prefix (uppercased, spaces→_) + '-' + 8-hex uuid suffix
    assert re.fullmatch(r"[A-Z0-9_]{1,32}-[0-9a-f]{8}", code), code


def test_user_code_uniqueness_100_identical_prefixes():
    """100 users sharing a long prefix all get distinct codes."""
    shared = "very_long_common_prefix_shared_by_all_users_1234567890"
    codes = {_generate_user_code(shared) for _ in range(100)}
    assert len(codes) == 100, "collision: identical prefixes produced duplicate codes"
    for c in codes:
        assert len(c) <= 64
        # truncated to 32 chars, so the shared prefix dominates deterministically
        assert c.startswith("VERY_LONG_COMMON_PREFIX_SHARED_B"), c


def test_user_code_prefix_bounded_to_32():
    """Extremely long usernames still produce a bounded, unique code."""
    long_username = "x" * 300
    code = _generate_user_code(long_username)
    assert len(code) == 32 + 1 + 8  # 32 prefix + '-' + 8 suffix
    assert code.startswith("X" * 32)


def test_user_code_not_accepted_from_ui():
    """The code is server-generated: the create request has no `code` field."""
    assert "code" not in CreateLocalAdvertiserRequest.model_fields
