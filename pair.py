from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.whatsapp import WhatsAppClientAdapter

log = logging.getLogger(__name__)


async def start_pairing(phone_number: str) -> dict[str, Any]:
    """Return a Green API phone-linking code and persist it locally.

    The original pair.js created a Baileys multi-file session. Neonize/Baileys
    cannot be installed on the target Python 3.9 host, so this compatible port
    uses Green API's official getAuthorizationCode endpoint instead.
    """
    client = WhatsAppClientAdapter(device_name=phone_number)
    client.connect()
    try:
        code = await client.get_authorization_code(phone_number)
        settings.pairing_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "number": phone_number,
            "code": code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        path = settings.pairing_root / "pairing.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    finally:
        await client.stop()


def start_pairing_sync(phone_number: str) -> dict[str, Any]:
    return asyncio.run(start_pairing(phone_number))


def list_paired_sessions() -> list[Path]:
    root = settings.pairing_root
    if not root.exists():
        return []
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and path.name.endswith("@s.whatsapp.net")
    )


def validate_session(phone_number: str) -> bool:
    folder = settings.pairing_root / f"{phone_number}@s.whatsapp.net"
    return (folder / "creds.json").exists()


def force_cleanup_session(phone_number: str) -> bool:
    folder = settings.pairing_root / f"{phone_number}@s.whatsapp.net"
    if not folder.exists():
        return False
    import shutil

    shutil.rmtree(folder)
    return True


async def autoload_pairs() -> list[dict[str, Any]]:
    """Validate stored pairing folders without exposing credentials."""
    results: list[dict[str, Any]] = []
    for folder in list_paired_sessions():
        results.append({"jid": folder.name, "valid": (folder / "creds.json").exists()})
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python pair.py <international_phone_number>")
    print(json.dumps(start_pairing_sync(sys.argv[1]), ensure_ascii=False))
