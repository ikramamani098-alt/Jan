from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from app.commands import BotState, install_router
from app.config import settings
from app.moderation import Moderation
from app.telegram_bot import TelegramPairingBot
from app.whatsapp import WhatsAppClientAdapter

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("jan-main")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = json.dumps({"status": "ok", "service": "jan-main-python"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("health: " + format, *args)


def start_health_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", settings.port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()
    log.info("Health server listening on port %s", settings.port)
    return server


async def run_whatsapp() -> None:
    try:
        client = WhatsAppClientAdapter()
        state = BotState()
        await install_router(client)
        client.add_handler(Moderation(client, state).handle)
        result = await asyncio.to_thread(client.connect)
        if asyncio.iscoroutine(result):
            await result
        log.info("WhatsApp transport started")
        await client.idle()
    except (RuntimeError, OSError, ImportError) as exc:
        log.error("WhatsApp transport unavailable: %s", exc)
        log.info("The Telegram/health services can continue without WhatsApp.")


async def run_telegram() -> None:
    if not settings.telegram_token:
        log.warning("BOT_TOKEN is empty; Telegram service is disabled.")
        return
    try:
        bot = TelegramPairingBot()
        await bot.run()
    except Exception:
        log.exception("Telegram service stopped unexpectedly")


async def main() -> None:
    server = start_health_server()
    stop_event = asyncio.Event()

    def stop() -> None:
        if not stop_event.is_set():
            log.info("Shutdown requested")
            stop_event.set()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, signame), stop)
        except (NotImplementedError, RuntimeError):
            pass

    tasks = [asyncio.create_task(run_whatsapp(), name="whatsapp")]
    if settings.telegram_token:
        tasks.append(asyncio.create_task(run_telegram(), name="telegram"))
    try:
        await stop_event.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        server.shutdown()
        server.server_close()
        log.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
