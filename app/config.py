from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for import-only checks
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")


def _csv(value: str, default: list[str]) -> list[str]:
    if not value.strip():
        return default.copy()
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    """Runtime configuration loaded from environment variables.

    The original JavaScript project contains a Telegram token and operator IDs in
    source files.  The Python port deliberately reads these values from `.env`
    or the process environment instead.
    """

    root: Path = ROOT
    port: int = int(os.getenv("PORT", "8080"))
    telegram_token: str = os.getenv("BOT_TOKEN", "")
    owner_number: str = os.getenv("OWNER_NUMBER", "93748807162")
    owner_name: str = os.getenv("OWNER_NAME", "@rais_bahram810")
    developer_ids: list[str] = field(
        default_factory=lambda: _csv(os.getenv("DEVELOPER_IDS", "8764900501"), ["8764900501"])
    )
    bot_name: str = os.getenv(
        "BOT_NAME", "༒︎⚜️ 𝐈 𝐀𝐌 𝐊𝐈𝐍𝐆 𝐀𝐌𝐀𝐍𝐈 ⚜️༒︎"
    )
    footer: str = os.getenv(
        "BOT_FOOTER", "꧁༒☬ 𝑰 𝑨𝑴 𝑲𝑰𝑵𝑮 𝑨𝑴𝑨𝑵𝑰 ☬༒꧂"
    )
    prefixes: list[str] = field(
        default_factory=lambda: _csv(os.getenv("BOT_PREFIXES", "!,.,#,&,/"), ["!", ".", "#", "&", "/"])
    )
    required_channels: list[str] = field(
        default_factory=lambda: _csv(
            os.getenv("REQUIRED_CHANNELS", "@Reyesbahram810,@FARSHAD_CHINAL"),
            ["@Reyesbahram810", "@FARSHAD_CHINAL"],
        )
    )
    pairing_root: Path = field(
        default_factory=lambda: Path(os.getenv("PAIRING_ROOT", str(ROOT / "sessions" / "pairing")))
    )
    database_root: Path = field(
        default_factory=lambda: Path(os.getenv("DATABASE_ROOT", str(ROOT / "data" / "database")))
    )
    media_root: Path = field(
        default_factory=lambda: Path(os.getenv("MEDIA_ROOT", str(ROOT / "media")))
    )
    max_pairings: int = int(os.getenv("MAX_PAIRINGS", "1000"))
    auto_presence: bool = os.getenv("AUTO_PRESENCE", "false").lower() == "true"
    auto_read: bool = os.getenv("AUTO_READ", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    green_api_url: str = os.getenv("GREEN_API_URL", "https://api.green-api.com")
    green_api_instance_id: str = os.getenv("GREEN_API_INSTANCE_ID", "")
    green_api_token: str = os.getenv("GREEN_API_TOKEN", "")
    green_api_receive_timeout: int = int(os.getenv("GREEN_API_RECEIVE_TIMEOUT", "5"))

    def ensure_directories(self) -> None:
        self.pairing_root.mkdir(parents=True, exist_ok=True)
        self.database_root.mkdir(parents=True, exist_ok=True)
        self.media_root.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
