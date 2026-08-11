from __future__ import annotations

import logging
from typing import Any

from app.commands import BotState, CommandRouter
from app.moderation import Moderation
from app.whatsapp import IncomingMessage, WhatsAppClientAdapter

log = logging.getLogger(__name__)


async def handle_message(
    client: WhatsAppClientAdapter,
    message: IncomingMessage,
    chat_update: Any = None,
    store: Any = None,
) -> None:
    """Compatibility entry point corresponding to drenox.js's handleMessage."""
    router = CommandRouter(client)
    moderation = Moderation(client, router.state)
    await moderation.handle(message)
    if message.text:
        await router.handle(message)


async def setup_event_listeners(client: WhatsAppClientAdapter, store: Any = None) -> None:
    """Install the stable event-layer handlers preserved from drenox.js."""
    state = BotState()
    client.add_handler(Moderation(client, state).handle)
    client.add_handler(CommandRouter(client, state).handle)
    log.info("Converted drenox event listeners installed")


def group_metadata_cache() -> dict[str, Any]:
    return {}


async def refresh_group_metadata(*_args: Any, **_kwargs: Any) -> None:
    return None


async def check_admin_status(*_args: Any, **_kwargs: Any) -> bool:
    return False
