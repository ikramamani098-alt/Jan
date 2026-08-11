from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .config import settings
from .utils import parse_mentions

log = logging.getLogger(__name__)

try:  # Neonize is optional at import time so health checks and Telegram can still run.
    from neonize.client import NewClient
    from neonize.events import ConnectedEv, MessageEv, event
except ImportError:  # pragma: no cover - depends on deployment environment
    NewClient = None  # type: ignore[assignment]
    ConnectedEv = MessageEv = event = None  # type: ignore[assignment]


@dataclass(slots=True)
class IncomingMessage:
    chat: str
    sender: str
    text: str = ""
    message_id: str = ""
    from_me: bool = False
    is_group: bool = False
    raw: Any = None
    mentions: list[str] = field(default_factory=list)
    client: WhatsAppClientAdapter | None = None

    async def reply(self, text: str) -> Any:
        if self.client is None:
            raise RuntimeError("Message is not attached to a WhatsApp client")
        return await self.client.send_text(self.chat, text)


MessageHandler = Callable[[IncomingMessage], Awaitable[None] | None]


def _read_value(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        try:
            value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name)
        except (AttributeError, KeyError, TypeError):
            continue
        if value is not None:
            return value
    return default


def normalize_event(event_obj: Any, client: WhatsAppClientAdapter) -> IncomingMessage:
    message = _read_value(event_obj, "message", "Message", default=event_obj)
    info = _read_value(event_obj, "info", "Info", default=None)
    conversation = _read_value(message, "conversation", "text", "body", default="")
    if not isinstance(conversation, str):
        conversation = _read_value(message, "caption", default="") or ""

    chat = _read_value(info, "MessageSource", "chat", "remote_jid", default=None)
    sender = _read_value(info, "Sender", "sender", "participant", default=None)
    message_id = _read_value(info, "ID", "id", "message_id", default="")
    from_me = bool(_read_value(info, "IsFromMe", "from_me", default=False))

    # Neonize versions expose source fields slightly differently. Keep the
    # fallback conservative rather than guessing a private or group chat.
    if not chat:
        chat = _read_value(message, "chat", "remoteJid", default="")
    if not sender:
        sender = _read_value(message, "sender", "participant", default=chat)
    chat = str(chat or "")
    sender = str(sender or chat)
    is_group = chat.endswith("@g.us") or bool(_read_value(info, "IsGroup", "is_group", default=False))

    return IncomingMessage(
        chat=chat,
        sender=sender,
        text=str(conversation or ""),
        message_id=str(message_id or ""),
        from_me=from_me,
        is_group=is_group,
        raw=event_obj,
        mentions=parse_mentions(str(conversation or "")),
        client=client,
    )


class WhatsAppClientAdapter:
    """Small compatibility surface for the old `bad` Baileys socket object.

    Neonize owns the actual WhatsApp Web transport. The adapter gives the
    converted command layer stable methods such as `send_text`, `reply`, and
    `send_media`, while keeping library-specific event parsing in one place.
    """

    def __init__(self, device_name: str | None = None) -> None:
        if NewClient is None:
            raise RuntimeError(
                "Neonize is not installed. Install dependencies with `pip install -r requirements.txt`."
            )
        self.device_name = device_name or settings.neonize_device_name
        self.client = NewClient(self.device_name)
        self.handlers: list[MessageHandler] = []
        self.connected = False
        self._install_events()

    def _install_events(self) -> None:
        if event is None:
            return

        @self.client.event(ConnectedEv)
        def _connected(_client: Any, _event: Any) -> None:
            self.connected = True
            log.info("WhatsApp connected (%s)", self.device_name)

        @self.client.event(MessageEv)
        def _message(_client: Any, event_obj: Any) -> None:
            message = normalize_event(event_obj, self)
            for handler in tuple(self.handlers):
                try:
                    result = handler(message)
                    if inspect.isawaitable(result):
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            asyncio.run(result)
                        else:
                            loop.create_task(result)
                except Exception:
                    log.exception("WhatsApp message handler failed")

    def add_handler(self, handler: MessageHandler) -> None:
        self.handlers.append(handler)

    async def send_text(self, jid: str, text: str, **kwargs: Any) -> Any:
        target = jid if "@" in jid else f"{jid}@s.whatsapp.net"
        send = getattr(self.client, "send_message", None)
        if send is None:
            raise RuntimeError("The installed Neonize version does not expose send_message")
        result = send(target, text=text, **kwargs)
        return await result if inspect.isawaitable(result) else result

    async def reply(self, message: IncomingMessage, text: str, **kwargs: Any) -> Any:
        return await self.send_text(message.chat, text, **kwargs)

    async def send_media(self, jid: str, path: str, caption: str = "", **kwargs: Any) -> Any:
        """Send common media types when supported by the installed Neonize build."""
        target = jid if "@" in jid else f"{jid}@s.whatsapp.net"
        suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
        builder_name = {
            "jpg": "build_image_message",
            "jpeg": "build_image_message",
            "png": "build_image_message",
            "webp": "build_image_message",
            "mp4": "build_video_message",
            "mp3": "build_audio_message",
            "ogg": "build_audio_message",
            "pdf": "build_document_message",
        }.get(suffix, "build_document_message")
        builder = getattr(self.client, builder_name, None)
        if builder is None:
            raise RuntimeError(f"Neonize does not expose {builder_name}")
        result = builder(path, caption=caption, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        send = self.client.send_message
        result = send(target, result)
        return await result if inspect.isawaitable(result) else result

    def request_pairing_code(self, phone_number: str) -> str:
        """Return a code if the installed Neonize version supports one.

        Baileys exposes `requestPairingCode`; Neonize releases commonly use a
        QR/device-login flow instead. We fail explicitly rather than claiming a
        code was generated when the transport cannot provide one.
        """
        for name in ("request_pairing_code", "request_pairing_code_sync"):
            method = getattr(self.client, name, None)
            if method is not None:
                value = method(phone_number)
                if inspect.isawaitable(value):
                    raise RuntimeError(
                        "This Neonize build exposes an asynchronous pairing API; use the async startup path."
                    )
                return str(value)
        raise RuntimeError(
            "The installed Neonize build does not expose WhatsApp pairing codes. "
            "Use its QR/device-login flow, or keep the original Node/Baileys pairing service."
        )

    def connect(self) -> Any:
        result = self.client.connect()
        return result

    async def idle(self) -> None:
        idle = getattr(self.client, "idle", None)
        if idle is not None:
            result = idle()
            if inspect.isawaitable(result):
                await result
            return
        await asyncio.Event().wait()

    async def stop(self) -> None:
        for method_name in ("disconnect", "close", "logout"):
            method = getattr(self.client, method_name, None)
            if method is not None:
                result = method()
                if inspect.isawaitable(result):
                    await result
                break
        self.connected = False
