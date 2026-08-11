# اتصال WhatsApp روی Python 3.9

## مسیر انتخاب‌شده: Green API

این پروژه اکنون از Green API برای اتصال واتس‌اپ استفاده می‌کند. این روش برای هاست GSM Telegram Bot Hosting مناسب‌تر است، زیرا فقط به HTTP نیاز دارد و به browser، Chromium، Selenium، Node.js یا Python 3.10 وابسته نیست.

| نیاز | وضعیت |
|---|---|
| Python 3.9 | پشتیبانی می‌شود |
| QR اتصال واتس‌اپ | از طریق ربات Telegram نمایش داده می‌شود |
| دریافت پیام‌های ورودی | با HTTP polling notification queue انجام می‌شود |
| ارسال پیام‌های متنی | از طریق `sendMessage` انجام می‌شود |
| URL عمومی webhook | لازم نیست؛ notification queue استفاده می‌شود |
| حساب Green API | لازم است |

## راه‌اندازی

1. در [Green API Console](https://console.green-api.com/) یک instance بسازید.
2. `Instance ID` و `API Token Instance` را کپی کنید.
3. به ربات Telegram، در چت خصوصی و با حساب مالک بفرستید:

   ```text
   /green <instance_id> <api_token>
   ```

4. ربات QR اتصال را می‌فرستد. آن را در WhatsApp → Linked Devices اسکن کنید.
5. در واتس‌اپ `.ping` یا `.menu` بفرستید تا پاسخ ربات را امتحان کنید.

## دلیل انتخاب

Neonize برای Python 3.9 قابل نصب نیست؛ Astra به browser/Chromium نیاز دارد که در این هاست در دسترس بودنش تضمین نشده است؛ اما Green API با notification queue امکان دریافت پیام‌ها بدون webhook عمومی یا مرورگر را فراهم می‌کند [1] [2] [3].

## منابع

[1]: https://green-api.com/en/docs/api/account/QR/ "Green API — دریافت QR"
[2]: https://green-api.com/en/docs/api/sending/SendMessage/ "Green API — ارسال پیام"
[3]: https://green-api.com/en/docs/api/receiving/technology-http-api/ReceiveNotification/ "Green API — دریافت notification"
