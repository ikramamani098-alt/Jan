# گزارش تبدیل All-amani-main

## دامنهٔ تبدیل

پروژهٔ دریافت‌شده شامل ۳۳ فایل JavaScript، فایل `bot.js`، فایل بزرگ `drenox.js`، وابستگی‌های Node.js، داده‌های JSON و رسانه‌ها بود. برای همهٔ ۳۳ فایل JavaScript یک مسیر Python ساخته شد؛ `bot.js` به‌طور مشخص با نام `bot.py` حفظ شد و حذف نشد.

## معماری Python

`main.py` جایگزین `index.js` است و health server و سرویس Telegram را اجرا می‌کند. `bot.py` جریان Telegram، بررسی عضویت کانال، `/start`، `/pair`، `/green`، `/unpair` و حالت انتظار شماره را پیاده‌سازی می‌کند. `pair.py` جایگزین `pair.js` است و endpoint کد جفت‌سازی Green API را فراخوانی می‌کند. `drenox.py` و `app/commands.py` لایهٔ handler و command router واتس‌اپ را فراهم می‌کنند.

از ۶۴۴ نام فرمان استخراج‌شده از switch بزرگ `drenox.js`، فرمان‌های اصلی مستقیماً پیاده‌سازی شده‌اند و تمام نام‌ها در `legacy_command_names.txt` ثبت شده‌اند. فرمان‌هایی که به scraper، media converter، API بیرونی یا متدهای خصوصی Baileys وابسته‌اند، پیام شفاف سازگاری می‌دهند و به‌عنوان اجرای خام و دروغین معرفی نمی‌شوند.

## حل خطای Python 3.9

وابستگی `neonize` حذف شده است، زیرا روی Python 3.9 نصب نمی‌شود. `requirements.txt` اکنون فقط وابستگی‌های runtime سازگار با Python 3.9 را نصب می‌کند: `httpx`، `python-telegram-bot` و `python-dotenv`. Dockerfile نیز برای Python 3.11 باقی مانده، اما هاست Python 3.9 می‌تواند همین requirements را بدون Neonize نصب کند.

## امنیت

توکن واقعی موجود در `token.js` به `token_config.py` منتقل نشده است. نام `token.py` عمداً استفاده نشد، زیرا با ماژول استاندارد `token` در Python تداخل ایجاد می‌کند. `.env`، نشست‌ها، `pairing.json` و Green API token در Git نادیده گرفته می‌شوند. داده‌های pairing دریافت‌شده از ZIP منتشر نشده‌اند.

## اعتبارسنجی

بررسی نگاشت نشان داد هر ۳۳ فایل JavaScript یک معادل Python دارد. پروژه با lint هدف Python 3.9 و آزمون‌های آفلاین بررسی می‌شود. اتصال زنده به Green API برای آزمون نیازمند `Instance ID` و `API Token` واقعی است و بدون این اطلاعات اجرا نمی‌شود.
