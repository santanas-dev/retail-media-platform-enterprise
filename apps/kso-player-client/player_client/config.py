"""KSO Player Client — environment configuration."""

import os
import sys
from dataclasses import dataclass


@dataclass
class PlayerConfig:
    gateway_url: str = ""
    control_url: str = ""
    signing_key: str = ""
    device_code: str = ""
    device_secret: str = ""
    device_jwt: str = ""
    retailer_id: str = ""
    max_retries: int = 3


def load_config() -> PlayerConfig:
    gateway_url = os.environ.get("PLAYER_GATEWAY_URL", "http://localhost:8001")
    cfg = PlayerConfig(
        gateway_url=gateway_url,
        control_url=os.environ.get("PLAYER_CONTROL_URL", "http://localhost:8000"),
        signing_key=os.environ.get("PLAYER_SIGNING_KEY", ""),
        device_code=os.environ.get("PLAYER_DEVICE_CODE", ""),
        device_secret=os.environ.get("PLAYER_DEVICE_SECRET", ""),
        device_jwt=os.environ.get("PLAYER_DEVICE_JWT", ""),
        retailer_id=os.environ.get("PLAYER_RETAILER_ID", ""),
        max_retries=int(os.environ.get("PLAYER_MAX_RETRIES", "3")),
    )
    if not cfg.gateway_url:
        _die("PLAYER_GATEWAY_URL is required")
    return cfg


def _die(msg: str) -> None:
    print(f"CONFIG ERROR: {msg}", file=sys.stderr)
    sys.exit(2)
