from app.config import settings

# Python hosts should execute main.py directly; this metadata mirrors the old PM2 entry.
APP_NAME = "all-amani-python"
SCRIPT = "main.py"
PORT = settings.port
