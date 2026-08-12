from __future__ import annotations

import asyncio
import logging
import re
import shutil
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
except ImportError:  # pragma: no cover - optional until dependencies are installed
    Application = None  # type: ignore[assignment]
    Update = Any  # type: ignore[misc,assignment]
    ContextTypes = Any  # type: ignore[assignment]
    InlineKeyboardButton = InlineKeyboardMarkup = ChatType = None  # type: ignore[assignment]
    CallbackQueryHandler = CommandHandler = MessageHandler = filters = None  # type: ignore[assignment]
    TelegramError = RuntimeError  # type: ignore[assignment]

PHONE_RE = re.compile(r"^\d{7,15}$")
BLOCKED_COUNTRY_CODES = {"252", "201"}
HARDCODED_TELEGRAM_TOKEN = "8820323516:AAFy8rl9MWaQviXNa-N6BT2_-GzvFyFnSEg"


class PairingService:
    """Manage the Green API transport used by the converted Baileys pairing flow.

    Green API authorizes one WhatsApp account per instance. A deployment that must
    host independent accounts for many users needs one Green API instance per user
    or a separate multi-session gateway; this class never pretends one instance can
    safely own several accounts.
    """

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
            self.polling_task = asyncio.create_task(self.client.idle(), name="whatsapp-green-api")
            return self.client

    async def stop(self) -> None:
        if self.polling_task is not None:
            self.polling_task.cancel()
            await asyncio.gather(self.polling_task, return_exceptions=True)
            self.polling_task = None
        if self.client is not None:
            await self.client.stop()
            self.client = None

    async def request_code(self, phone_number: str) -> str:
        client = await self.start()
        return await client.get_authorization_code(phone_number)

    async def autoload(self) -> None:
        if green_api_store.load().get("instance_id") or settings.green_api_instance_id:
            try:
                await self.start()
            except (RuntimeError, OSError, ValueError):
                log.exception("Could not start saved Green API instance")


class TelegramPairingBot:
    def __init__(self, pairing: Optional[PairingService] = None) -> None:
        if Application is None:
            raise RuntimeError("python-telegram-bot is not installed")
        self.telegram_token = settings.telegram_token or HARDCODED_TELEGRAM_TOKEN
        if not self.telegram_token:
            raise RuntimeError("BOT_TOKEN is empty; set it in bot.py or the hosting-panel environment")
        self.pairing = pairing or PairingService()
        self.user_states: dict[int, str] = {}
        self.admin_store = JsonStore(settings.root / "kingbadboitimewisher" / "admin.json", settings.developer_ids)
        self.admin_ids = self._load_admin_ids()
        self.application = Application.builder().token(self.telegram_token).build()
        self._register_handlers()

    def _load_admin_ids(self) -> list[str]:
        value = self.admin_store.load()
        if not isinstance(value, list) or not value:
            value = settings.developer_ids
            self.admin_store.save(value)
        return [str(item) for item in value]

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("pair", self.pair_command))
        self.application.add_handler(CommandHandler("green", self.green_command))
        self.application.add_handler(CommandHandler("unpair", self.unpair_command))
        self.application.add_handler(CallbackQueryHandler(self.callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))
        self.application.add_error_handler(self.error_handler)

    @staticmethod
    def _args(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
        return list(context.args) if context.args else []

    def is_owner(self, update: Update) -> bool:
        user_id = str(update.effective_user.id) if update.effective_user else ""
        return user_id in set(self.admin_ids) or user_id in {str(item) for item in settings.developer_ids}

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
        rows = [
            [InlineKeyboardButton(f"📢 {channel}", url="https://t.me/{}".format(channel.lstrip("@")))]
            for channel in settings.required_channels
        ]
        rows.append([InlineKeyboardButton("✅ من عضو شدم", callback_data="check_join")])
        return InlineKeyboardMarkup(rows)

    async def send_channels_required(self, update: Update) -> None:
        await update.effective_message.reply_text(
            "🚨 در قدم نخست در کانال‌های ما عضو شوید؛ بعد شمارهٔ واتس‌اپ را بفرستید.",
            reply_markup=self.channels_keyboard(),
        )

    async def send_group_message(self, update: Update) -> None:
        message = update.effective_message
        if message is None:
            return
        username = ""
        try:
            me = await self.application.bot.get_me()
            username = f"@{me.username}" if me.username else ""
        except TelegramError:
            pass
        text = (
            "╭━━〔 🛡️ سلام، برای جفت‌سازی به چت خصوصی ربات بروید 〕━━╮\n"
            "➤ در چت خصوصی /start را بفرستید\n"
            f"╰━━〔 🚀 START NOW {username} 〕━━╯"
        )
        await message.reply_text(text)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await self.send_group_message(update)
            return
        user_id = update.effective_user.id if update.effective_user else 0
        if not await self.check_user_joined_channels(user_id, context):
            await self.send_channels_required(update)
            return
        self.user_states[user_id] = "awaiting_number"
        await message.reply_text(
            f"🪀 {settings.bot_name}\n\n"
            "🔐 شمارهٔ واتس‌اپ خود را با کد کشور بفرستید.\n"
            "نمونه: `937xxxxxxxxx`\n\n"
            "بعد از دریافت شماره، کد جفت‌سازی برای خودتان ارسال می‌شود.",
            parse_mode="Markdown",
        )

    async def green_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if not self.is_owner(update):
            await message.reply_text("❌ این فرمان فقط برای مالک ربات است.")
            return
        args = self._args(context)
        if len(args) < 2:
            await message.reply_text(
                "استفاده: `/green <instance_id> <api_token>`\n"
                "این تنظیم فقط توسط مالک انجام می‌شود و در GitHub ذخیره نمی‌گردد.",
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
            "✅ اتصال Green API ذخیره شد. اکنون `/start` را بزنید یا شمارهٔ واتس‌اپ را بفرستید.",
            parse_mode="Markdown",
        )

    @staticmethod
    def validate_number(value: str) -> Optional[str]:
        number = str(value or "").strip().replace("+", "")
        if not PHONE_RE.fullmatch(number):
            return None
        if number.startswith("0") or number[:3] in BLOCKED_COUNTRY_CODES:
            return None
        return number

    async def _process_number(self, update: Update, number: str) -> None:
        message = update.effective_message
        user_id = update.effective_user.id if update.effective_user else 0
        valid = self.validate_number(number)
        if valid is None:
            await message.reply_text(
                "❌ شماره نادرست است. فقط ۷ تا ۱۵ رقم، با کد کشور و بدون + بفرستید؛ مانند `937xxxxxxxxx`.",
                parse_mode="Markdown",
            )
            self.user_states[user_id] = "awaiting_number"
            return
        self.user_states.pop(user_id, None)
        await message.reply_text("⏳ کد جفت‌سازی در حال ساختن است؛ چند لحظه منتظر بمانید…")
        try:
            code = await self.pairing.request_code(valid)
            display_code = f"{code[:4]}-{code[4:]}" if len(code) == 8 else code
            await message.reply_text(
                "🔗 کد جفت‌سازی واتس‌اپ برای شمارهٔ شما:\n\n"
                f"`{display_code}`\n\n"
                "در WhatsApp بروید:\n"
                "Linked devices → Link a device → Link with phone number instead\n\n"
                "کد حدود ۲ تا ۳ دقیقه اعتبار دارد.",
                parse_mode="Markdown",
            )
        except (RuntimeError, OSError, ValueError) as exc:
            log.exception("Pairing failed for %s", valid)
            self.user_states[user_id] = "awaiting_number"
            await message.reply_text(f"❌ جفت‌سازی انجام نشد: {exc}\nدوباره شماره را بفرستید.")

    async def pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await self.send_group_message(update)
            return
        user_id = update.effective_user.id if update.effective_user else 0
        if not await self.check_user_joined_channels(user_id, context):
            await self.send_channels_required(update)
            return
        args = self._args(context)
        if not args:
            self.user_states[user_id] = "awaiting_number"
            await update.effective_message.reply_text(
                "🔐 لطفاً شمارهٔ واتس‌اپ را با کد کشور بفرستید؛ نمونه: `937xxxxxxxxx`.",
                parse_mode="Markdown",
            )
            return
        await self._process_number(update, args[0])

    async def unpair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat and update.effective_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await update.effective_message.reply_text("لطفاً این فرمان را در چت خصوصی بفرستید.")
            return
        args = self._args(context)
        if not args:
            await self.pairing.stop()
            await update.effective_message.reply_text("✅ اتصال فعال واتس‌اپ متوقف شد.")
            return
        number = self.validate_number(args[0])
        if number is None:
            await update.effective_message.reply_text("استفاده: `/unpair 937xxxxxxxxx`", parse_mode="Markdown")
            return
        folder = settings.pairing_root / f"{number}@s.whatsapp.net"
        if folder.exists():
            shutil.rmtree(folder)
        await self.pairing.stop()
        await update.effective_message.reply_text(f"✅ نشست جفت‌سازی برای {number} حذف شد.")

    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is None or update.effective_chat.type != ChatType.PRIVATE:
            return
        user_id = update.effective_user.id if update.effective_user else 0
        text = (update.effective_message.text or "").strip()
        if self.user_states.get(user_id) != "awaiting_number" or text.startswith("/"):
            return
        if not await self.check_user_joined_channels(user_id, context):
            await self.send_channels_required(update)
            return
        await self._process_number(update, text)

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if query.data == "check_join":
            if await self.check_user_joined_channels(query.from_user.id, context):
                self.user_states[query.from_user.id] = "awaiting_number"
                await query.message.reply_text("✅ عضویت تأیید شد. اکنون شمارهٔ واتس‌اپ خود را بفرستید.")
            else:
                await query.answer("ابتدا در همهٔ کانال‌های لازم عضو شوید.", show_alert=True)

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


if __name__ == "__main__":
    asyncio.run(TelegramPairingBot().run())
