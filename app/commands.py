from __future__ import annotations

import ast
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings
from .storage import settings_store
from .utils import runtime
from .whatsapp import IncomingMessage, WhatsAppClientAdapter

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


@dataclass
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


def _load_legacy_commands() -> set[str]:
    path = ROOT / "legacy_command_names.txt"
    if not path.exists():
        return set()
    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


LEGACY_COMMANDS = _load_legacy_commands()


class CommandRouter:
    """Python command surface corresponding to the large `drenox.js` switch.

    Stable local commands are implemented directly. All names extracted from the
    original switch remain registered so users receive a clear compatibility
    response instead of an unknown-command error. Scrapers, media providers and
    Node-only Baileys operations require an explicit Python/API implementation and
    are intentionally not claimed to work silently.
    """

    def __init__(self, client: WhatsAppClientAdapter, state: BotState | None = None) -> None:
        self.client = client
        self.state = state or BotState()
        self.commands: dict[str, Callable[[IncomingMessage, list[str]], Awaitable[None]]] = {}
        self._register_core()
        self._register_legacy_names()
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
        self.add("runtime", "uptime")(self._cmd_runtime)
        self.add("owner", "creator")(self._cmd_owner)
        self.add("id", "chatid", "checkid")(self._cmd_id)
        self.add("echo", "say")(self._cmd_echo)
        self.add("calc", "calculate")(self._cmd_calc)
        self.add("settings", "botsettings")(self._cmd_settings)
        self.add("on", "enable")(self._cmd_enable)
        self.add("off", "disable")(self._cmd_disable)
        self.add(
            "antilink", "antibadword", "antibot", "antibill", "antidelete",
            "autoreply", "autotyping", "autorecord", "autorecording", "autoread",
            "autoviewstatus", "autolikestatus", "autobio", "chatbot",
        )(self._cmd_toggle)
        self.add("admincheck", "checkadmin", "amiadmin")(self._cmd_admincheck)
        self.add("broadcast")(self._cmd_broadcast)

    def _register_legacy_names(self) -> None:
        for name in LEGACY_COMMANDS:
            if name not in self.commands:
                self.commands[name] = self._cmd_legacy_not_ported

    def _register_aliases(self) -> None:
        aliases = {
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
        content = text[len(prefix):].strip()
        if not content:
            await self._cmd_menu(message, [])
            return
        parts = content.split()
        name = parts.pop(0).lower()
        command = self.commands.get(name)
        if command is None:
            await message.reply(
                f"فرمان `{name}` ثبت نشده است. برای فهرست فرمان‌های اصلی `{prefix}menu` را بفرستید."
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
        core = ", ".join(f"{settings.prefixes[0]}{name}" for name in ["ping", "runtime", "owner", "id", "calc", "settings", "on", "off"])
        moderation = ", ".join(f"{settings.prefixes[0]}{name}" for name in ["antilink", "antibadword", "antibot", "antidelete", "autoreply", "autoread"])
        await message.reply(
            f"{settings.bot_name}\n\n"
            f"فرمان‌های اصلی:\n{core}\n\n"
            f"مدیریت و حالت‌ها:\n{moderation}\n\n"
            f"۶۴۴ نام فرمان legacy ثبت شده است؛ فرمان‌های وابسته به scraper/API در این پورت نیاز به تنظیم سرویس دارند."
        )

    async def _cmd_runtime(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"⏱️ مدت فعالیت: {runtime(time.monotonic() - self.state.started_at)}")

    async def _cmd_owner(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"👑 مالک: {settings.owner_name}\n📞 شماره: +{settings.owner_number}")

    async def _cmd_id(self, message: IncomingMessage, _args: list[str]) -> None:
        await message.reply(f"Chat: {message.chat}\nSender: {message.sender}")

    async def _cmd_echo(self, message: IncomingMessage, args: list[str]) -> None:
        await message.reply(" ".join(args) or "متنی برای بازتاب ارسال نشده است.")

    async def _cmd_calc(self, message: IncomingMessage, args: list[str]) -> None:
        expression = " ".join(args).strip()
        if not expression:
            await message.reply("استفاده: `.calc 2 + 2`")
            return
        try:
            tree = ast.parse(expression, mode="eval")
            allowed = (ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd)
            if not all(isinstance(node, allowed) for node in ast.walk(tree)):
                raise ValueError("unsupported expression")
            result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {})
            await message.reply(str(result))
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError):
            await message.reply("❌ عبارت ریاضی معتبر نیست.")

    async def _cmd_settings(self, message: IncomingMessage, _args: list[str]) -> None:
        enabled = [name for name, value in self.state.flags.items() if value]
        await message.reply("حالت‌های فعال:\n" + ("\n".join(f"• {name}" for name in enabled) if enabled else "هیچ حالتی فعال نیست."))

    async def _cmd_enable(self, message: IncomingMessage, args: list[str]) -> None:
        await self._set_flags(message, args, True)

    async def _cmd_disable(self, message: IncomingMessage, args: list[str]) -> None:
        await self._set_flags(message, args, False)

    async def _cmd_toggle(self, message: IncomingMessage, args: list[str]) -> None:
        name = next((n for n in self.state.flags if n in message.text.lower()), None)
        if not args and name:
            self.state.flags[name] = not self.state.flags[name]
            await self._persist_flag(message, name)
            await message.reply(f"{name}: {'فعال' if self.state.flags[name] else 'غیرفعال'}")
            return
        await self._set_flags(message, args, not self.state.flags.get(name or "", False))

    async def _set_flags(self, message: IncomingMessage, args: list[str], value: bool) -> None:
        names = [arg.lower().lstrip("-") for arg in args]
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
        await message.reply("ℹ️ بررسی مدیر گروه در Green API به مجوزهای گروه وابسته است.")

    async def _cmd_broadcast(self, message: IncomingMessage, args: list[str]) -> None:
        if not args:
            await message.reply("متن اعلان را بعد از فرمان بنویسید.")
            return
        await message.reply("⚠️ broadcast برای جلوگیری از ارسال ناخواسته در این پورت محدود است.")

    async def _cmd_legacy_not_ported(self, message: IncomingMessage, _args: list[str]) -> None:
        command_name = message.text.lstrip("".join(settings.prefixes)).split()[0]
        await message.reply(
            f"ℹ️ فرمان `{command_name}` از drenox.js ثبت شده است، اما اجرای آن به API یا scraper اختصاصی Node.js وابسته است."
        )


async def install_router(client: WhatsAppClientAdapter) -> CommandRouter:
    router = CommandRouter(client)
    client.add_handler(router.handle)
    return router
