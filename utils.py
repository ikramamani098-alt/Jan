from __future__ import annotations

import asyncio
from typing import Any

from app.utils import get_buffer, get_size_media, is_url, normalize_jid, parse_mentions, runtime


async def sleep(milliseconds: int) -> None:
    await asyncio.sleep(max(0, milliseconds) / 1000)


async def fetch(url: str, **kwargs: Any) -> bytes:
    return await get_buffer(url, **kwargs)


__all__ = [
    "fetch",
    "get_buffer",
    "get_size_media",
    "is_url",
    "normalize_jid",
    "parse_mentions",
    "runtime",
    "sleep",
]
