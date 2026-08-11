# Jan Main Python Bot

این پروژه نسخهٔ Python ربات Jan است و برای اجرا روی هاست‌های محدود به **Python 3.9** آماده شده است. اتصال واتس‌اپ اکنون از طریق **Green API** انجام می‌شود؛ بنابراین پروژه به Neonize، Node.js، Chrome یا Python 3.10 نیاز ندارد.

> Green API یک instance متصل به حساب واتس‌اپ را مدیریت می‌کند. ربات با HTTP polling پیام‌های ورودی را دریافت و با همان حساب واتس‌اپ پاسخ می‌دهد. مستندات رسمی API، دریافت QR، ارسال پیام و دریافت notification از queue را پوشش می‌دهد [1] [2] [3].

## ساختار پروژه

| مسیر | نقش |
|---|---|
| `main.py` | نقطهٔ ورود و سرور سلامت |
| `bot.py` | ربات تلگرام و فرمان‌های اتصال Green API |
| `app/whatsapp.py` | آداپتر Green API برای ارسال، دریافت و polling پیام‌های واتس‌اپ |
| `app/commands.py` | فرمان‌های اصلی واتس‌اپ |
| `app/moderation.py` | کنترل ضدلینک و واژه‌های نامناسب |
| `app/storage.py` | ذخیره‌سازی JSON و اطلاعات اتصال محلی |
| `.env.example` | قالب متغیرهای محیطی |
| `DEPLOYMENT.md` | راهنمای استقرار |

## استقرار روی GSM Telegram Bot Hosting

در همان صفحه‌ای که تصویرش را فرستادید، `main.py` را انتخاب کنید و سپس **Watch Ad / Run Selected File** را بزنید. وابستگی‌های runtime اکنون با Python 3.9 سازگارند و دیگر `neonize` نصب نمی‌شود.

برای اجرای Telegram باید متغیر `BOT_TOKEN` را به‌صورت خصوصی در تنظیمات پلتفرم قرار دهید. اگر پلتفرم متغیر محیطی ندارد، این هاست برای نگه‌داشتن امن توکن مناسب نیست؛ توکن را هرگز در GitHub عمومی قرار ندهید.

## اتصال واقعی واتس‌اپ

ابتدا در [Green API Console](https://console.green-api.com/) یک instance بسازید. پس از آماده‌شدن instance، `Instance ID` و `API Token Instance` را بردارید. سپس در چت خصوصی ربات تلگرام خود بفرستید:

```text
/green <instance_id> <api_token>
```

این فرمان فقط برای شناسه‌های `DEVELOPER_IDS` مجاز است. ربات QR را به همان چت Telegram می‌فرستد. در گوشی خود باز کنید:

```text
WhatsApp → Linked devices → Link a device
```

و QR را اسکن کنید. بعد از اتصال، هر پیام متنی واتس‌اپ با پیشوندهایی مانند `.`, `!`, `/` یا `#` به ربات می‌رسد؛ برای نمونه `.ping` یا `.menu` را در واتس‌اپ ارسال کنید.

برای گرفتن دوباره QR، در چت Telegram این فرمان را بفرستید:

```text
/pair
```

برای متوقف‌کردن polling محلی:

```text
/unpair
```

فایل حاوی شناسه و token Green API در `sessions/green_api.json` ذخیره می‌شود و طبق `.gitignore` در GitHub ثبت نمی‌گردد.

## فرمان‌های اصلی واتس‌اپ

فرمان‌های پایه شامل `ping`، `alive`، `menu`، `runtime`، `owner`، `id`، `settings`، `on`، `off`، `antilink`، `antibadword`، `antibot`، `antidelete`، `autoreply`، `autoread`، `autotyping`، `autorecording`، `autoviewstatus`، `autolikestatus`، `autobio` و `admincheck` است.

## نکات مهم

Green API یک سرویس مستقل از این پروژه است و برای اتصال باید instance خود را در Console آن ایجاد کنید. QR یا token را در گروه Telegram یا GitHub عمومی نفرستید. همچنین استفاده از اتوماسیون واتس‌اپ باید با قوانین سرویس و حساب شما سازگار باشد.

## منابع

[1]: https://green-api.com/en/docs/api/account/QR/ "Green API — دریافت QR"
[2]: https://green-api.com/en/docs/api/sending/SendMessage/ "Green API — ارسال پیام"
[3]: https://green-api.com/en/docs/api/receiving/technology-http-api/ReceiveNotification/ "Green API — دریافت notification"
