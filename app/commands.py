from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from .config import settings
from .storage import settings_store
from .utils import runtime
from .whatsapp import IncomingMessage, WhatsAppClientAdapter

log = logging.getLogger(__name__)


@dataclass(slots=True)
class BotState:
    started_at: float = field(default_factory=time.monotonic)
    flags: dict[str, bool] = field(
        default_factory=lambda: {
            "autoread": False,
            "autotyping": False,
            "autorecording": False,
            "autoviewstatus": True,
            "autolikestatus": True,
            "autobio": True,
            "autoreply": False,
            "antilink": False,
            "antibadword": False,
            "antibot": False,
            "antidelete": False,
            "chatbot": False,
        }
    )


class CommandRouter:
    """Port of the command-dispatch layer from `drenox.js`.

    The original file contains many third-party media/scraper commands. This
    router keeps the stable core commands and exposes an extension registry so
    additional command modules can be added without touching the transport.
    """

    def __init__(self, client: WhatsAppClientAdapter, state: BotState | None = None) -> None:
        self.client = client
        self.state = state or BotState()
        self.commands: dict[str, Callable[[IncomingMessage, list[str]], Awaitable[None]]] = {}
        self._register_core()
        self._register_aliases()

    def add(self, *names: str) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
        def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
            for name in names:
                self.commands[name.lower()] = func
            return func

        return decorator

    def _register_core(self) -> None:
        self.add("ping", "alive", "status")(self._cmd_ping)
        self.add("menu", "allmenu", "help")(self._cmd_menu)
        self.add("runtime")(self._cmd_runtime)
        self.add("owner", "creator")(self._cmd_owner)
        self.add("id", "chatid", "checkid")(self._cmd_id)
        self.add("echo", "say")(self._cmd_echo)
        self.add("settings", "botsettings")(self._cmd_settings)
        self.add("on", "enable")(self._cmd_enable)
        self.add("off", "disable")(self._cmd_disable)
        self.add("antilink", "antibadword", "antibot", "antibill", "antidelete", "autoreply", "autotyping", "autorecord", "autorecording", "autoread", "autoviewstatus", "autolikestatus", "autobio", "chatbot")(self._cmd_toggle)
        self.add("admincheck", "checkadmin", "amiadmin")(self._cmd_admincheck)
        self.add("broadcast")(self._cmd_broadcast)

    def _register_aliases(self) -> None:
        # Common aliases seen in the original command switch.
        aliases = {
            "runtime": ["uptime"],
            "menu": ["men", "listmenu", "downloadmenu", "aimenu", "animemenu", "emojimenu"],
            "ping": ["p"],
        }
        for target, names in aliases.items():
            for name in names:
                self.commands[name] = self.commands[target]

    async def handle(self, message: IncomingMessage) -> None:
        text = message.text.strip()
        if not text:
            return
        prefix = next((p for p in settings.prefixes if text.startswith(p)), None)
        if prefix is None:
            if self.state.flags.get("autoreply"):
                await message.reply("پیام شما دریافت شد. برای دیدن فرمان‌ها /menu را بفرستید.")
            return

        content = text[len(prefix) :].strip()
        if not content:
            await self._cmd_menu(message, [])
            return
        parts = content.split()
        name = parts.pop(0).lower()
        command = self.commands.get(name)
        if command is None:
            await message.reply(
                f"فرمان `{name}` در نسخهٔ Python ثبت نشده است. برای فهرست فرمان‌های اصلی `{prefix}menu` را بفرستید."
            )
            return
        try:
            await command(message, parts)
        except Exception:
            log.exception("Command failed: %s", name)
            await message.reply("❌ اجرای این فرمان با خطا مواجه شد. گزارش خطا در لاگ ثبت گردید.")

    async def _cmd_ping(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply("🏓 pong — ربات فعال است.")

    async def _cmd_menu(self, message: IncomingMessage, _args: list[str]) -> None:
        core = ", ".join(f"{settings.prefixes[0]}{name}" for name in ["ping", "runtime", "owner", "id", "settings", "on", "off", "admincheck"])
        moderation = ", ".join(f"{settings.prefixes[0]}{name}" for name in ["antilink", "antibadword", "antibot", "antidelete", "autoreply", "autoread"])
        await message.reply(
            f"{settings.bot_name}\n\n"
            f"فرمان‌های اصلی:\n{core}\n\n"
            f"مدیریت و حالت‌ها:\n{moderation}\n\n"
            f"برای فعال/غیرفعال‌کردن حالت‌ها از `{settings.prefixes[0]}on <name>` و `{settings.prefixes[0]}off <name>` استفاده کنید."
        )

    async def _cmd_runtime(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"⏱️ مدت فعالیت: {runtime(time.monotonic() - self.state.started_at)}")

    async def _cmd_owner(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"👑 مالک: {settings.owner_name}\n📞 شماره: +{settings.owner_number}")

    async def _cmd_id(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"Chat: {message.chat}\nSender: {message.sender}")

    async def _cmd_echo(self, message: IncomingMessage, args: list[str]) -> None:
        await message.reply(" ".join(args) or "متنی برای بازتاب ارسال نشده است.")

    async def _cmd_settings(self, message: IncomingMessage, _args: list[str]) -> None:
        enabled = [name for name, value in self.state.flags.items() if value]
        await message.reply("حالت‌های فعال:\n" + ("\n".join(f"• {name}" for name in enabled) if enabled else "هیچ حالتی فعال نیست."))

    async def _cmd_enable(self, message: IncomingMessage, args: list[str]) -> None:
        await self._set_flags(message, args, True)

    async def _cmd_disable(self, message: IncomingMessage, args: list[str]) -> None:
        await self._set_flags(message, args, False)

    async def _cmd_toggle(self, message: IncomingMessage, args: list[str]) -> None:
        name = next((n for n in self.state.flags if message.text.lower().find(n) >= 0), None)
        if not args and name:
            self.state.flags[name] = not self.state.flags[name]
            await self._persist_flag(message, name)
            await message.reply(f"{name}: {'فعال' if self.state.flags[name] else 'غیرفعال'}")
            return
        await self._set_flags(message, args, not self.state.flags.get(name or "", False))

    async def _set_flags(self, message: IncomingMessage, args: list[str], value: bool) -> None:
        names = [arg.lower().lstrip("-") for arg in args] or []
        valid = [name for name in names if name in self.state.flags]
        if not valid:
            await message.reply("نام حالت را مشخص کنید؛ مانند: `.on autoread` یا `.off antilink`")
            return
        for name in valid:
            self.state.flags[name] = value
            await self._persist_flag(message, name)
        await message.reply("✅ " + ", ".join(valid) + (" فعال شد." if value else " غیرفعال شد."))

    async def _persist_flag(self, message: IncomingMessage, name: str) -> None:
        settings_store.set(message.chat, name, self.state.flags[name])

    async def _cmd_admincheck(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply("ℹ️ بررسی مدیر در نسخهٔ Python به اطلاعات گروه Neonize وابسته است و در این نشست فعال می‌شود.")

    async def _cmd_broadcast(self, message: IncomingMessage, args: list[str]) -> None:
        if not args:
            await message.reply("متن اعلان را بعد از فرمان بنویسید.")
            return
        await message.reply("⚠️ برای جلوگیری از ارسال ناخواسته، broadcast در این پورت به‌صورت محافظت‌شده غیرفعال است.")


async def install_router(client: WhatsAppClientAdapter) -> CommandRouter:
    router = CommandRouter(client)
    client.add_handler(router.handle)
    return router
