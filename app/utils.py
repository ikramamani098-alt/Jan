from __future__ import annotations

import asyncio
import json
import mimetypes
import random
import re
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx


def normalize_jid(jid: str | None) -> str:
    if not jid:
        return ""
    return jid.split("@")[0].split(":")[0]


def is_same_user(first: str | None, second: str | None) -> bool:
    return bool(first and second and normalize_jid(first) == normalize_jid(second))


def is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value or "", re.IGNORECASE))


def parse_mentions(text: str = "") -> list[str]:
    return [f"{number}@s.whatsapp.net" for number in re.findall(r"@([0-9]{5,16}|0)", text)]


def get_group_admins(participants: Iterable[dict[str, Any]]) -> list[str]:
    admins: list[str] = []
    for participant in participants:
        if participant.get("admin") in {"admin", "superadmin"}:
            jid = participant.get("id") or participant.get("jid")
            if jid:
                admins.append(jid)
    return admins


def pick_random(items: list[Any]) -> Any:
    return random.choice(items) if items else None


def runtime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def clock_string(milliseconds: int) -> str:
    return runtime(milliseconds / 1000)


def bytes_to_size(value: int, decimals: int = 2) -> str:
    if value <= 0:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    index = min(int(__import__("math").floor(__import__("math").log(value, 1024))), len(units) - 1)
    size = round(value / 1024**index, max(decimals, 0))
    return f"{size} {units[index]}"


def get_file_mime(path: Path) -> tuple[str, str]:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    ext = path.suffix.lstrip(".") or "bin"
    return mime, ext


async def sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def fetch_json(url: str, **kwargs: Any) -> Any:
    timeout = kwargs.pop("timeout", 30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()


async def get_buffer(source: str | Path, **kwargs: Any) -> bytes:
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        return Path(source).read_bytes()
    async with httpx.AsyncClient(timeout=kwargs.pop("timeout", 30.0), follow_redirects=True) as client:
        response = await client.get(str(source), **kwargs)
        response.raise_for_status()
        return response.content


def json_format(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def now_ms() -> int:
    return int(time.time() * 1000)
