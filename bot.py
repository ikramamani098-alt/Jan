from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.commands import BotState, install_router
from app.config import settings
from app.moderation import Moderation
from app.storage import JsonStore, green_api_store
from app.whatsapp import WhatsAppClientAdapter

log = logging.getLogger(__name__)

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ChatType
    from telegram.error import TelegramError
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
except ImportError:  # pragma: no cover - depends on deployment environment
    Application = None  # type: ignore[assignment]
    Update = Any  # type: ignore[misc,assignment]
    ContextTypes = Any  # type: ignore[assignment]
    InlineKeyboardButton = InlineKeyboardMarkup = ChatType = None  # type: ignore[assignment]
    CallbackQueryHandler = CommandHandler = MessageHandler = filters = None  # type: ignore[assignment]
    TelegramError = RuntimeError  # type: ignore[assignment]


class PairingService:
    """Own the single Green API WhatsApp instance used by this bot process."""

    def __init__(self) -> None:
        self.client: Optional[WhatsAppClientAdapter] = None
        self.polling_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    async def start(self) -> WhatsAppClientAdapter:
        async with self.lock:
            if self.client is not None and self.client.connected:
                return self.client
            self.client = WhatsAppClientAdapter()
            state = BotState()
            await install_router(self.client)
            self.client.add_handler(Moderation(self.client, state).handle)
            self.client.connect()
            self.polling_task = asyncio.create_task(self.client.idle(), name="green-api-whatsapp")
            return self.client

    async def stop(self) -> None:
        if self.polling_task is not None:
            self.polling_task.cancel()
            await asyncio.gather(self.polling_task, return_exceptions=True)
            self.polling_task = None
        if self.client is not None:
            await self.client.stop()
            self.client = None

    async def autoload(self) -> None:
        if green_api_store.load().get("instance_id") or settings.green_api_instance_id:
            try:
                await self.start()
            except (RuntimeError, OSError, ValueError):
                log.exception("Could not start saved Green API WhatsApp instance")


class TelegramPairingBot:
    def __init__(self, pairing: Optional[PairingService] = None) -> None:
        if Application is None:
            raise RuntimeError("python-telegram-bot is not installed")
        if not settings.telegram_token:
            raise RuntimeError("BOT_TOKEN is empty; set it in the hosting-panel environment before starting Telegram")
        self.pairing = pairing or PairingService()
        self.admin_store = JsonStore(settings.root / "data" / "admins.json", settings.developer_ids)
        self.application = Application.builder().token(settings.telegram_token).build()
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("green", self.green_command))
        self.application.add_handler(CommandHandler("pair", self.pair_command))
        self.application.add_handler(CommandHandler("unpair", self.unpair_command))
        self.application.add_handler(CallbackQueryHandler(self.callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))
        self.application.add_error_handler(self.error_handler)

    @staticmethod
    def _args(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
        return list(context.args) if context.args else []

    def is_owner(self, update: Update) -> bool:
        user_id = str(update.effective_user.id) if update.effective_user else ""
        return user_id in {str(value) for value in settings.developer_ids}

    async def check_user_joined_channels(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        for channel in settings.required_channels:
            try:
                member = await context.bot.get_chat_member(channel, user_id)
                if getattr(member, "status", "left") in {"left", "kicked"}:
                    return False
            except (TelegramError, RuntimeError, OSError):
                return False
        return True

    def channels_keyboard(self) -> InlineKeyboardMarkup:
        rows = [[InlineKeyboardButton(f"📢 {channel}", url="https://t.me/{}".format(channel.lstrip("@")))] for channel in settings.required_channels]
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
            await message.reply_text("برای راه‌اندازی واتس‌اپ، در گفت‌وگوی خصوصی ربات از `/pair` استفاده کنید.")
            return
        text = (
            f"🪀 {settings.bot_name}\n\n"
            "فرمان‌های اتصال:\n"
            "/pair <wa_number> — دریافت کد جفت‌سازی واتس‌اپ\n"
            "/unpair — قطع اجرای اتصال در ربات\n\n"
            "تنظیم Green API فقط برای مالک:\n"
            "/green <instance_id> <api_token>\n\n"
            "ابتدا یک instance در Green API بسازید؛ سپس شناسه و token آن را در چت خصوصی ربات بفرستید."
        )
        await message.reply_text(text)

    async def green_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if not self.is_owner(update):
            await message.reply_text("❌ این فرمان فقط برای مالک ربات است.")
            return
        args = self._args(context)
        if len(args) < 2:
            await message.reply_text(
                "استفاده: `/green <instance_id> <api_token>`\n\n"
                "شناسه و token را از Green API Console بردارید. این اطلاعات فقط محلی ذخیره می‌شوند و در GitHub ثبت نمی‌گردند.",
                parse_mode="Markdown",
            )
            return
        await self.pairing.stop()
        green_api_store.save({
            "instance_id": args[0],
            "token": args[1],
            "api_url": settings.green_api_url,
        })
        await message.reply_text(
            "✅ Green API ذخیره شد. اکنون شمارهٔ واتس‌اپ را بفرستید:\n\n"
            "`/pair 937xxxxxxxxx`",
            parse_mode="Markdown",
        )

    async def _send_pairing_code(self, update: Update, number: str) -> None:
        message = update.effective_message
        try:
            client = await self.pairing.start()
            code = await client.get_authorization_code(number)
            display_code = f"{code[:4]}-{code[4:]}" if len(code) == 8 else code
            await message.reply_text(
                "🔗 کد جفت‌سازی واتس‌اپ:\n\n"
                f"`{display_code}`\n\n"
                "در WhatsApp بروید: Linked devices → Link a device → Link with phone number instead\n"
                "سپس این کد را وارد کنید. کد حدود ۲ تا ۳ دقیقه اعتبار دارد.",
                parse_mode="Markdown",
            )
        except (RuntimeError, OSError, ValueError) as exc:
            log.exception("WhatsApp phone pairing failed")
            await message.reply_text(f"❌ کد جفت‌سازی آماده نشد: {exc}")

    async def pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await update.effective_message.reply_text("لطفاً `/pair` را در چت خصوصی با ربات استفاده کنید.")
            return
        user_id = update.effective_user.id if update.effective_user else 0
        if not await self.check_user_joined_channels(user_id, context):
            await self.send_channels_required(update)
            return
        if not self.is_owner(update):
            await update.effective_message.reply_text("❌ کد اتصال فقط برای مالک ربات نمایش داده می‌شود.")
            return
        args = self._args(context)
        if len(args) != 1 or not args[0].isdigit() or not 7 <= len(args[0]) <= 15:
            await update.effective_message.reply_text(
                "استفاده: `/pair 937xxxxxxxxx`\nشماره را با کد کشور، بدون + و فقط با رقم بفرستید.",
                parse_mode="Markdown",
            )
            return
        await self._send_pairing_code(update, args[0])

    async def unpair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.is_owner(update):
            await update.effective_message.reply_text("❌ این فرمان فقط برای مالک ربات است.")
            return
        await self.pairing.stop()
        await update.effective_message.reply_text("✅ polling واتس‌اپ در ربات متوقف شد. برای دریافت کد دوباره `/pair <شماره>` را بفرستید.")

    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if query.data == "check_join":
            if await self.check_user_joined_channels(query.from_user.id, context):
                await query.message.reply_text("✅ عضویت تأیید شد. مالک ربات می‌تواند `/pair <شماره>` را بفرستد.")
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
            await self.pairing.stop()
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
