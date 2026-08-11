from __future__ import annotations

import asyncio
from pathlib import Path

from app.commands import CommandRouter
from app.storage import JsonStore, SessionManager
from app.utils import normalize_jid, parse_mentions, runtime
from app.whatsapp import IncomingMessage


class FakeClient:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, jid: str, text: str, **kwargs):
        self.sent.append((jid, text))


async def run_command(text: str):
    fake = FakeClient()
    router = CommandRouter(fake)  # type: ignore[arg-type]
    message = IncomingMessage(chat="123@g.us", sender="456@s.whatsapp.net", text=text, client=fake)  # type: ignore[arg-type]
    await router.handle(message)
    return fake.sent


def test_normalize_jid_and_mentions() -> None:
    assert normalize_jid("123:4@s.whatsapp.net") == "123"
    assert parse_mentions("hello @123456789") == ["123456789@s.whatsapp.net"]


def test_runtime_format() -> None:
    assert runtime(3661) == "0d 1h 1m 1s"


def test_json_store(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = JsonStore(path, {})
    store.save({"ok": True})
    assert store.load() == {"ok": True}


def test_session_manager(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path / "pairing")
    assert manager.normalize_jid("93748807162") == "93748807162@s.whatsapp.net"
    manager.save_pairing_code("93748807162", "ABCD-EFGH")
    assert manager.read_pairing_code()["code"] == "ABCD-EFGH"


def test_ping_command() -> None:
    sent = asyncio.run(run_command(".ping"))
    assert sent and "pong" in sent[0][1]


def test_unknown_command_is_safe() -> None:
    sent = asyncio.run(run_command(".not_a_real_command"))
    assert sent and "ثبت نشده" in sent[0][1]


def test_all_amani_pairing_number_validation() -> None:
    from bot import TelegramPairingBot

    assert TelegramPairingBot.validate_number("93748807162") == "93748807162"
    assert TelegramPairingBot.validate_number("+93748807162") == "93748807162"
    assert TelegramPairingBot.validate_number("0") is None
    assert TelegramPairingBot.validate_number("abc93748807162") is None
    assert TelegramPairingBot.validate_number("2521234567") is None
