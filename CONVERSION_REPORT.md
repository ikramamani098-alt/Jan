# گزارش تبدیل Jan-main به Python

## وضعیت فعلی

پروژهٔ اصلی یک ربات Node.js بود. نسخهٔ فعلی Python، لایه‌های Telegram، ذخیره‌سازی، فرمان‌های اصلی، کنترل‌های گروهی و اتصال واتس‌اپ را در فایل‌های جداگانه پیاده‌سازی می‌کند.

| بخش نسخهٔ اصلی | معادل Python |
|---|---|
| `index.js` | `main.py` |
| `bot.js` | `bot.py` |
| `pair.js` و `autoload.js` | `bot.py` و `app/storage.py` |
| `drenox.js` | `app/whatsapp.py`، `app/commands.py` و `app/moderation.py` |
| `Settings.js` و `setting/config.js` | `app/config.py` و `app/storage.py` |

## تغییر مسیر اتصال واتس‌اپ

نسخهٔ قبلی Python از Neonize استفاده می‌کرد؛ اما Neonize به Python 3.10 یا بالاتر نیاز داشت و در هاست GSM Telegram Bot Hosting که Python 3.9 دارد نصب نمی‌شد. در نسخهٔ جدید، آداپتر `app/whatsapp.py` از Green API استفاده می‌کند.

Green API امکان دریافت QR، ارسال پیام متنی و دریافت notificationهای ورودی از queue HTTP را ارائه می‌کند. بنابراین ربات به Python 3.9، مرورگر محلی یا Node.js وابسته نیست [1] [2] [3]. برای اتصال، کاربر باید یک instance Green API بسازد و شناسه و API token آن را فقط در چت خصوصی Telegram با فرمان `/green` وارد کند.

## قابلیت‌های اجراشده

نسخهٔ فعلی شامل اجرای ربات Telegram، فرمان `/green` برای تنظیم instance، فرمان `/pair` برای دریافت QR، فرمان `/unpair` برای متوقف‌کردن polling، دریافت پیام‌های ورودی WhatsApp، ارسال پاسخ، فرمان‌های اصلی و کنترل‌های ضدلینک/ضدواژه است.

## محدودیت‌ها

فرمان‌های بسیار اختصاصی نسخهٔ JavaScript که به scraping، APIهای خارجی یا متدهای داخلی Baileys متکی بودند، به شکل یک‌به‌یک منتقل نشده‌اند. ساختار `CommandRouter` برای افزودن آن‌ها به‌صورت ماژولار آماده است.

اطلاعات Green API در `sessions/green_api.json` ذخیره می‌شود و از طریق `.gitignore` از GitHub خارج است. توکن Telegram و Green API را در مخزن عمومی ثبت نکنید.

## بررسی‌های انجام‌شده

- `ruff check .` بدون خطا اجرا شد.
- آزمون‌های آفلاین command/router و Green API اجرا شدند.
- نصب runtime dependencies بدون Neonize بررسی شد.

## منابع

[1]: https://green-api.com/en/docs/api/account/QR/ "Green API — دریافت QR"
[2]: https://green-api.com/en/docs/api/sending/SendMessage/ "Green API — ارسال پیام"
[3]: https://green-api.com/en/docs/api/receiving/technology-http-api/ReceiveNotification/ "Green API — دریافت notification"
