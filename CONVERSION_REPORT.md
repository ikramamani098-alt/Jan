# گزارش تبدیل Jan-main به Python

## وضعیت کلی

پروژهٔ پیوست‌شده یک آرشیو ZIP از یک ربات Node.js بود. نسخهٔ Python در این پوشه از صفر با ساختار ماژولار ساخته شده و داده‌ها و رسانه‌های قابل‌استفادهٔ نسخهٔ اصلی را نگه می‌دارد.

| بخش نسخهٔ اصلی | معادل Python |
|---|---|
| `index.js` | `main.py` |
| `bot.js` | `bot.py` |
| `pair.js` و `autoload.js` | `PairingService` در `bot.py` و `SessionManager` در `app/storage.py` |
| `drenox.js` | `app/whatsapp.py`، `app/commands.py` و `app/moderation.py` |
| `Settings.js` و `setting/config.js` | `app/config.py` و `app/storage.py` |
| JSONهای `database/` | `data/database/` |
| پوشهٔ `media/` | `media/` |

## قابلیت‌های منتقل‌شده

نسخهٔ Python سرور سلامت، اجرای هم‌زمان سرویس‌ها، راه‌اندازی ربات Telegram، بررسی عضویت کانال‌ها، `/start`، `/pair`، `/unpair`، بارگذاری نشست‌های معتبر، حذف نشست، نگه‌داری تنظیمات JSON، مدل پیام نرمال‌شده، ارسال متن، فرمان‌های پایه و کنترل‌های ضدلینک/ضدواژهٔ نامناسب را پیاده‌سازی می‌کند.

## تفاوت اتصال واتس‌اپ

نسخهٔ JavaScript با Baileys کار می‌کرد. چون Baileys کتابخانهٔ Node.js است، نسخهٔ Python از Neonize استفاده می‌کند. Neonize یک کلاینت event-driven برای WhatsApp بر پایهٔ Whatsmeow است و APIهای `NewClient`، رویدادهای اتصال/پیام و ارسال پیام دارد [1].

کد جفت‌سازی متنی در Baileys با `requestPairingCode` قابل فراخوانی بود؛ Neonize بسته به نسخه ممکن است QR/device-login ارائه کند. آداپتر Python در صورت نبودن متد pairing code، این محدودیت را گزارش می‌کند و برنامه را با ادعای نادرست ادامه نمی‌دهد.

## محدودیت‌های شناخته‌شده

بخش بزرگی از `drenox.js` به سرویس‌های scraping، APIهای بیرونی، تبدیل رسانه، متدهای خصوصی Baileys، newsletter queryهای داخلی و صدها فرمان اختصاصی متکی است. ترجمهٔ نحوی این کدها بدون بازطراحی APIها، یک برنامهٔ قابل‌اعتماد تولید نمی‌کند. برای همین فرمان‌های پایدار و زیرساخت اصلی منتقل شده‌اند و `CommandRouter` به‌عنوان نقطهٔ توسعه برای افزودن فرمان‌های APIمحور آماده است.

توکن Telegram و سایر مقدارهای حساس از کد خارج و به `.env` منتقل شده‌اند. فایل `.env.example` فقط قالب پیکربندی است و نباید با توکن واقعی عمومی شود.

## بررسی‌های انجام‌شده

- `python3 -m compileall -q .` با موفقیت اجرا شد.
- `ruff check .` با موفقیت اجرا شد.
- `pytest -q` با موفقیت اجرا شد: **۶ آزمون موفق**.
- اجرای آفلاین `main.py` بدون `BOT_TOKEN` بررسی شد؛ سرور سلامت بالا می‌آید و نبودن Neonize/توکن باعث توقف کل برنامه نمی‌شود.

## منابع

[1]: https://github.com/krypton-byte/neonize "Neonize official GitHub repository"
[2]: https://pypi.org/project/neonize/ "Neonize on PyPI"
