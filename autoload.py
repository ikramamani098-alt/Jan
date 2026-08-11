from __future__ import annotations

import asyncio
import logging
from typing import Any

from pair import autoload_pairs

log = logging.getLogger(__name__)


async def auto_load_pairs() -> list[dict[str, Any]]:
    sessions = await autoload_pairs()
    for session in sessions:
        if session["valid"]:
            log.info("Stored pairing session available: %s", session["jid"])
        else:
            log.warning("Stored pairing session is incomplete: %s", session["jid"])
    return sessions


def auto_load_pairs_sync() -> list[dict[str, Any]]:
    return asyncio.run(auto_load_pairs())
