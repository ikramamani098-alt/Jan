from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from .config import settings
from .storage import JsonStore, sessions
from .whatsapp import WhatsAppClientAdapter

log = logging.getLogger(__name__)

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ChatType
    from telegram.error import TelegramError
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except ImportError:  # pragma: no cover - depends on deployment environment
    Application = None  # type: ignore[assignment]
    Update = Any  # type: ignore[misc,assignment]
    ContextTypes = Any  # type: ignore[assignment]
    InlineKeyboardButton = InlineKeyboardMarkup = ChatType = None  # type: ignore[assignment]
    CallbackQueryHandler = CommandHandler = MessageHandler = filters = None  # type: ignore[assignment]
    TelegramError = RuntimeError  # type: ignore[assignment]


PHONE_RE = re.compile(r"^\d{7,15}$")


class PairingService:
    """Manage WhatsApp client instances used by Telegram pairing requests."""

    def __init__(self) -> None:
        self.clients: dict[str, WhatsAppClientAdapter] = {}
        self.lock = asyncio.Lock()

    async def start(self, number: str) -> dict[str, Any]:
        jid = sessions.normalize_jid(number)
        async with self.lock:
            if jid in self.clients and self.clients[jid].connected:
                return {"status": "connected", "jid": jid}
            client = WhatsAppClientAdapter(device_name=jid.replace("@", "-"))
            self.clients[jid] = client
            result = client.connect()
            if asyncio.iscoroutine(result):
                await result
            # Baileys exposes a pairing-code API; Neonize may instead initiate
            # QR/device login. Keep the distinction explicit for the user.
            try:
                code = client.request_pairing_code(number)
            except (RuntimeError, OSError) as exc:
                log.info("Pairing code unavailable for %s: %s", jid, exc)
                return {"status": "qr_required", "jid": jid, "detail": str(exc)}
            sessions.save_pairing_code(jid, code)
            return {"status": "pairing_code", "jid": jid, "code": code}

    async def stop(self, number: str) -> bool:
        jid = sessions.normalize_jid(number)
        client = self.clients.pop(jid, None)
        if client is not None:
            await client.stop()
        return sessions.remove(jid)

    async def autoload(self) -> None:
        for session in sessions.list_sessions():
            if not session.valid():
                continue
            try:
                await self.start(session.jid)
                await asyncio.sleep(4)
            except Exception:
                log.exception("Could not autoload %s", session.jid)


class TelegramPairingBot:
    def __init__(self, pairing: PairingService | None = None) -> None:
        if Application is None:
            raise RuntimeError("python-telegram-bot is not installed")
        if not settings.telegram_token:
            raise RuntimeError("BOT_TOKEN is empty; set it in .env before starting Telegram")
        self.pairing = pairing or PairingService()
        self.admin_store = JsonStore(settings.root / "data" / "admins.json", settings.developer_ids)
        self.user_states: dict[int, str] = {}
        self.application = Application.builder().token(settings.telegram_token).build()
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("pair", self.pair_command))
        self.application.add_handler(CommandHandler("unpair", self.unpair_command))
        self.application.add_handler(CallbackQueryHandler(self.callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))
        self.application.add_error_handler(self.error_handler)

    async def check_user_joined_channels(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        for channel in settings.required_channels:
            try:
                member = await context.bot.get_chat_member(channel, user_id)
                if getattr(member, "status", "left") in {"left", "kicked"}:
                    return False
            except (TelegramError, RuntimeError, OSError):
                # A channel that cannot be checked is treated as not verified.
                return False
        return True

    def channels_keyboard(self) -> InlineKeyboardMarkup:
        rows = [[InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{channel.lstrip('@')}")] for channel in settings.required_channels]
        rows.append([InlineKeyboardButton("✅ من عضو شدم", callback_data="check_join")])
        return InlineKeyboardMarkup(rows)

    async def send_channels_required(self, update: Update) -> None:
        await update.effective_message.reply_text(
            "🚨 ابتدا در کانال‌های ما عضو شوید و سپس جفت‌سازی را شروع کنید.",
            reply_markup=self.channels_keyboard(),
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await message.reply_text("برای شروع جفت‌سازی، در گفت‌وگوی خصوصی ربات از `/pair` استفاده کنید.")
            return
        await message.reply_text(
            f"🪀 {settings.bot_name}\n\n"
            "فرمان‌ها:\n"
            "/pair <wa_number>\n"
            "/unpair <wa_number>\n\n"
            "شماره را با کد کشور و بدون علامت + بفرستید."
        )

    @staticmethod
    def _number_from_context(context: ContextTypes.DEFAULT_TYPE) -> str:
        return " ".join(context.args).strip() if context.args else ""

    async def pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await update.effective_message.reply_text("لطفاً `/pair` را در چت خصوصی با ربات استفاده کنید.")
            return
        user_id = update.effective_user.id if update.effective_user else 0
        if not await self.check_user_joined_channels(user_id, context):
            await self.send_channels_required(update)
            return
        number = self._number_from_context(context)
        if not number:
            self.user_states[user_id] = "awaiting_number"
            await update.effective_message.reply_text("شمارهٔ واتس‌اپ را با کد کشور بفرستید؛ نمونه: `937xxxxxxxxx`", parse_mode="Markdown")
            return
        await self._process_pair(update, number)

    async def _process_pair(self, update: Update, number: str) -> None:
        message = update.effective_message
        if not PHONE_RE.fullmatch(number) or number.startswith("0"):
            await message.reply_text("❌ شماره باید فقط شامل ۷ تا ۱۵ رقم باشد و با صفر شروع نشود.")
            return
        if sessions.count() >= settings.max_pairings:
            await message.reply_text("❌ ظرفیت جفت‌سازی کامل شده است.")
            return
        await message.reply_text("⏳ در حال آماده‌سازی اتصال واتس‌اپ؛ چند لحظه صبر کنید…")
        try:
            result = await self.pairing.start(number)
            if result["status"] == "pairing_code":
                await message.reply_text(
                    f"🔗 کد جفت‌سازی واتس‌اپ:\n\n`{result['code']}`\n\n"
                    "WhatsApp → Linked Devices → Link a Device → واردکردن کد",
                    parse_mode="Markdown",
                )
            elif result["status"] == "connected":
                await message.reply_text("✅ این شماره از قبل متصل است.")
            else:
                await message.reply_text(
                    "⚠️ این نسخهٔ Python از Neonize کد جفت‌سازی متنی ارائه نمی‌کند و اتصال QR/دستگاه را آغاز کرده است. "
                    "لطفاً QR نمایش‌داده‌شده در ترمینال/محیط اجرا را با WhatsApp اسکن کنید."
                )
        except Exception:
            log.exception("Pairing failed for %s", number)
            await message.reply_text("❌ جفت‌سازی انجام نشد. لاگ اجرای برنامه را بررسی کنید.")

    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if self.user_states.get(user_id) != "awaiting_number":
            return
        self.user_states.pop(user_id, None)
        await self._process_pair(update, update.effective_message.text.strip())

    async def unpair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        number = self._number_from_context(context)
        if not PHONE_RE.fullmatch(number or "") or number.startswith("0"):
            await update.effective_message.reply_text("استفاده: `/unpair 937xxxxxxxxx`", parse_mode="Markdown")
            return
        if await self.pairing.stop(number):
            await update.effective_message.reply_text(f"✅ نشست واتس‌اپ برای {number} حذف شد.")
        else:
            await update.effective_message.reply_text("❌ نشست پیدا نشد.")

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if query.data == "check_join":
            if await self.check_user_joined_channels(query.from_user.id, context):
                await query.message.reply_text("✅ عضویت تأیید شد. اکنون `/pair` را بفرستید.")
            else:
                await query.answer("ابتدا در کانال‌های لازم عضو شوید.", show_alert=True)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("Telegram update error: %s", context.error, exc_info=context.error)

    async def run(self) -> None:
        await self.pairing.autoload()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        try:
            await asyncio.Event().wait()
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
