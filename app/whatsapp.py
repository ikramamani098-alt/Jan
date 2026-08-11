from __future__ import annotations

import asyncio
import base64
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Optional, Union

import httpx

from .config import settings
from .storage import green_api_store
from .utils import parse_mentions

log = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    """Transport-neutral WhatsApp message used by commands and moderation."""

    chat: str
    sender: str
    text: str = ""
    message_id: str = ""
    from_me: bool = False
    is_group: bool = False
    raw: Any = None
    mentions: list[str] = field(default_factory=list)
    client: Optional["WhatsAppClientAdapter"] = None

    async def reply(self, text: str) -> Any:
        if self.client is None:
            raise RuntimeError("Message is not attached to a WhatsApp client")
        return await self.client.send_text(self.chat, text)


MessageHandler = Callable[[IncomingMessage], Union[Awaitable[None], None]]


def _green_chat_id(jid: str) -> str:
    """Convert Baileys-style personal JIDs to Green API chat IDs."""
    value = str(jid or "").strip()
    if not value:
        raise ValueError("A WhatsApp chat ID is required")
    if "@" not in value:
        return f"{value}@c.us"
    if value.endswith("@s.whatsapp.net"):
        return "{}@c.us".format(value.split("@", 1)[0])
    return value


def _text_from_green(body: dict[str, Any]) -> str:
    data = body.get("messageData") or {}
    message_type = data.get("typeMessage") or ""
    candidates = (
        ("textMessageData", "textMessage"),
        ("extendedTextMessageData", "text"),
        ("quotedMessage", "textMessage"),
    )
    for outer, inner in candidates:
        payload = data.get(outer) or {}
        value = payload.get(inner)
        if isinstance(value, str):
            return value
    if message_type in {"textMessage", "extendedTextMessage"}:
        return str(data.get("text") or "")
    return ""


def normalize_green_notification(payload: dict[str, Any], client: "WhatsAppClientAdapter") -> Optional[IncomingMessage]:
    """Map a Green API incoming notification into the existing command model."""
    body = payload.get("body") or payload
    if body.get("typeWebhook") != "incomingMessageReceived":
        return None
    sender_data = body.get("senderData") or {}
    chat = str(sender_data.get("chatId") or sender_data.get("sender") or "")
    sender = str(sender_data.get("sender") or chat)
    if not chat:
        return None
    text = _text_from_green(body)
    return IncomingMessage(
        chat=chat,
        sender=sender,
        text=text,
        message_id=str(body.get("idMessage") or ""),
        from_me=False,
        is_group=chat.endswith("@g.us"),
        raw=body,
        mentions=parse_mentions(text),
        client=client,
    )


class WhatsAppClientAdapter:
    """Green API transport for WhatsApp on Python 3.9.

    Green API maintains the linked WhatsApp device. This process uses HTTP polling
    rather than a local Chromium browser or the Python-3.10-only Neonize package.
    """

    def __init__(self, device_name: Optional[str] = None) -> None:
        self.device_name = device_name or settings.green_api_instance_id or "green-api"
        self.handlers: list[MessageHandler] = []
        self.connected = False
        self._http: Optional[httpx.AsyncClient] = None
        self._stopping = False

    def _credentials(self) -> tuple[str, str, str]:
        saved = green_api_store.load()
        instance_id = settings.green_api_instance_id or str(saved.get("instance_id") or "")
        token = settings.green_api_token or str(saved.get("token") or "")
        api_url = settings.green_api_url or str(saved.get("api_url") or "https://api.green-api.com")
        if not instance_id or not token:
            raise RuntimeError(
                "Green API is not configured. In Telegram, the owner must use "
                "/green <instance_id> <api_token>, then scan the QR code with WhatsApp."
            )
        return api_url.rstrip("/"), instance_id, token

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(70.0, connect=20.0))
        return self._http

    def _endpoint(self, method: str, extra: str = "") -> str:
        api_url, instance_id, token = self._credentials()
        suffix = f"/{extra}" if extra else ""
        return f"{api_url}/waInstance{instance_id}/{method}/{token}{suffix}"

    def add_handler(self, handler: MessageHandler) -> None:
        self.handlers.append(handler)

    def connect(self) -> None:
        self._credentials()
        self.connected = True
        self._stopping = False
        log.info("Green API WhatsApp transport started (%s)", self.device_name)

    async def send_text(self, jid: str, text: str, **kwargs: Any) -> Any:
        payload = {"chatId": _green_chat_id(jid), "message": text}
        if kwargs.get("typing_time"):
            payload["typingTime"] = int(kwargs["typing_time"])
        response = await (await self._client()).post(self._endpoint("sendMessage"), json=payload)
        response.raise_for_status()
        return response.json()

    async def reply(self, message: IncomingMessage, text: str, **kwargs: Any) -> Any:
        return await self.send_text(message.chat, text, **kwargs)

    async def send_media(self, jid: str, path: str, caption: str = "", **kwargs: Any) -> Any:
        """Send a local file through Green API's upload endpoint."""
        target = _green_chat_id(jid)
        with open(path, "rb") as file_handle:
            response = await (await self._client()).post(
                self._endpoint("sendFileByUpload"),
                data={"chatId": target, "caption": caption},
                files={"file": (path.rsplit("/", 1)[-1], file_handle)},
            )
        response.raise_for_status()
        return response.json()

    async def get_qr_image(self) -> Optional[bytes]:
        response = await (await self._client()).get(self._endpoint("qr"))
        response.raise_for_status()
        payload = response.json()
        if payload.get("type") == "qrCode" and payload.get("message"):
            return base64.b64decode(payload["message"])
        if payload.get("type") == "alreadyLogged":
            self.connected = True
            return None
        raise RuntimeError(str(payload.get("message") or "Green API could not produce a QR code"))

    async def get_instance_state(self) -> str:
        response = await (await self._client()).get(self._endpoint("getStateInstance"))
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("stateInstance") or payload.get("state") or "unknown")

    async def _dispatch(self, message: IncomingMessage) -> None:
        for handler in tuple(self.handlers):
            try:
                result = handler(message)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                log.exception("WhatsApp message handler failed")

    async def _poll_once(self) -> None:
        response = await (await self._client()).get(
            self._endpoint("receiveNotification"),
            params={"receiveTimeout": settings.green_api_receive_timeout},
        )
        response.raise_for_status()
        if not response.content:
            return
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("receiptId"):
            return
        receipt_id = payload["receiptId"]
        try:
            message = normalize_green_notification(payload, self)
            if message is not None:
                await self._dispatch(message)
        finally:
            delete_response = await (await self._client()).delete(
                self._endpoint("deleteNotification", str(receipt_id))
            )
            delete_response.raise_for_status()

    async def idle(self) -> None:
        if not self.connected:
            self.connect()
        while self.connected and not self._stopping:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                log.warning("Green API polling failed: %s", exc)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._stopping = True
        self.connected = False
        if self._http is not None:
            await self._http.aclose()
            self._http = None
