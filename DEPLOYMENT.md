# راهنمای استقرار Python 3.9

## وضعیت نسخهٔ فعلی

نسخهٔ فعلی پروژه دیگر از `neonize` استفاده نمی‌کند. به همین دلیل روی Python 3.9 اجرا می‌شود و خطای زیر نباید دوباره ظاهر شود:

```text
No matching distribution found for neonize
```

اتصال واتس‌اپ از طریق Green API انجام می‌شود. این روش به browser، Selenium، Playwright یا Docker سفارشی روی هاست نیاز ندارد.

## GSM Telegram Bot Hosting

1. مخزن GitHub را Clone کنید.
2. در بخش **Select Python file to run**، `main.py` را انتخاب کنید.
3. ربات را اجرا کنید.
4. متغیر `BOT_TOKEN` را در تنظیمات محرمانهٔ پلتفرم تنظیم کنید؛ اگر پلتفرم این امکان را ندارد، توکن را در GitHub عمومی قرار ندهید.
5. بعد از شروع ربات، در چت خصوصی Telegram، فرمان `/green <instance_id> <api_token>` را بفرستید.
6. QR فرستاده‌شده توسط ربات را در WhatsApp → Linked Devices اسکن کنید.

## اگر خطای قبلی باقی ماند

باید cache build را پاک کنید و مخزن را دوباره Clone کنید. لاگ نصب نباید نام `neonize` را نمایش دهد. اگر همچنان `neonize` دیده می‌شود، اپ شما از commit قدیمی استفاده می‌کند یا clone دوباره انجام نشده است.

## اجرای محلی

```bash
pip install -r requirements.txt
export BOT_TOKEN="your_telegram_token"
python main.py
```

برای اتصال واتس‌اپ، شناسه و token Green API را از طریق Telegram با فرمان `/green` وارد کنید؛ این داده‌ها در GitHub ذخیره نمی‌شوند.
