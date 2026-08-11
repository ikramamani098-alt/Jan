from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

log = logging.getLogger(__name__)


class JsonStore:
    """Small atomic JSON store matching the original JSON-backed files."""

    def __init__(self, path: Path, default: Any) -> None:
        self.path = path
        self.default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Any:
        if not self.path.exists():
            self.save(self.default)
            return self.default
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not read %s: %s; restoring default", self.path, exc)
            self.save(self.default)
            return self.default

    def save(self, value: Any) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.store = JsonStore(path or settings.database_root / "settings.json", {})

    def get(self, jid: str, key: str, default: Any = False) -> Any:
        data = self.store.load()
        return data.get(jid, {}).get(key, default)

    def set(self, jid: str, key: str, value: Any) -> None:
        data = self.store.load()
        data.setdefault(jid, {})[key] = value
        self.store.save(data)


@dataclass
class PairingSession:
    jid: str
    path: Path

    @property
    def creds_path(self) -> Path:
        return self.path / "creds.json"

    @property
    def pairing_path(self) -> Path:
        return self.path.parent / "pairing.json"

    def exists(self) -> bool:
        return self.path.exists()

    def valid(self) -> bool:
        if not self.creds_path.exists():
            return False
        try:
            creds = json.loads(self.creds_path.read_text(encoding="utf-8"))
            return bool(creds.get("me", {}).get("id") or creds.get("registrationId"))
        except (OSError, json.JSONDecodeError):
            return False

    def delete(self) -> None:
        if self.path.exists():
            shutil.rmtree(self.path)


class SessionManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.pairing_root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_jid(value: str) -> str:
        value = value.strip()
        if "@" not in value:
            return f"{value}@s.whatsapp.net"
        return value

    def session(self, jid_or_number: str) -> PairingSession:
        jid = self.normalize_jid(jid_or_number)
        return PairingSession(jid=jid, path=self.root / jid)

    def list_sessions(self) -> list[PairingSession]:
        return [
            PairingSession(entry.name, entry)
            for entry in sorted(self.root.iterdir())
            if entry.is_dir() and entry.name.endswith("@s.whatsapp.net")
        ]

    def count(self) -> int:
        return len(self.list_sessions())

    def save_pairing_code(self, jid: str, code: str) -> Path:
        path = self.root / "pairing.json"
        payload = {
            "number": jid,
            "code": code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        JsonStore(path, {}).save(payload)
        return path

    def read_pairing_code(self) -> dict[str, Any] | None:
        path = self.root / "pairing.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def remove(self, jid_or_number: str) -> bool:
        session = self.session(jid_or_number)
        if not session.path.exists():
            # The legacy bot sometimes stores a folder with a suffix; support it.
            suffix = self.normalize_jid(jid_or_number)
            matches = [p for p in self.root.iterdir() if p.is_dir() and p.name.endswith(suffix)]
            if not matches:
                return False
            for match in matches:
                shutil.rmtree(match)
            return True
        session.delete()
        return True


admins_store = JsonStore(settings.database_root / "admintele.json", settings.developer_ids)
settings_store = SettingsStore()
sessions = SessionManager()
# This file is excluded from Git; it stores the credentials of the linked Green API instance.
green_api_store = JsonStore(settings.root / "kingbadboitimewisher" / "green_api.json", {})
