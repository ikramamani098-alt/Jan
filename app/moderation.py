from __future__ import annotations

import re
from dataclasses import dataclass, field

from .commands import BotState
from .whatsapp import IncomingMessage, WhatsAppClientAdapter


@dataclass
class Moderation:
    client: WhatsAppClientAdapter
    state: BotState
    bad_words: set[str] = field(
        default_factory=lambda: {
            "fuck", "shit", "bitch", "asshole", "motherfucker", "bullshit",
            "کونی", "کس", "فحش", "احمق", "حرامزاده",
        }
    )

    async def handle(self, message: IncomingMessage) -> None:
        if not message.text:
            return
        text = message.text.lower()
        if message.is_group and self.state.flags.get("antilink") and re.search(
            r"(?:https?://|www\.|chat\.whatsapp\.com/|t\.me/)", text
        ):
            await message.reply("🚫 ارسال لینک در این گروه مجاز نیست.")
            return
        if self.state.flags.get("antibadword") and any(word in text for word in self.bad_words):
            await message.reply("⚠️ لطفاً از واژه‌های توهین‌آمیز استفاده نکنید.")
            return
