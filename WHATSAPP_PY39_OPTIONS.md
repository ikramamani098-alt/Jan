# اتصال WhatsApp روی Python 3.9 با کد جفت‌سازی

## مسیر انتخاب‌شده: Green API + Phone Number Authorization

پروژه از Green API استفاده می‌کند و روی Python 3.9 اجرا می‌شود. اتصال واتس‌اپ با **کد جفت‌سازی شماره‌ای** انجام می‌شود؛ QR لازم نیست.

| نیاز | وضعیت |
|---|---|
| Python 3.9 | پشتیبانی می‌شود |
| QR | لازم نیست |
| کد جفت‌سازی | از endpoint رسمی `getAuthorizationCode` دریافت می‌شود |
| دریافت پیام‌های ورودی | با HTTP polling notification queue انجام می‌شود |
| URL عمومی webhook | لازم نیست |
| حساب Green API | لازم است |

## جریان اتصال

1. در Green API Console یک instance ایجاد کنید و `Instance ID` و `API Token Instance` را دریافت کنید.
2. در چت خصوصی ربات Telegram بفرستید:

   ```text
   /green <instance_id> <api_token>
   ```

3. سپس شمارهٔ واتس‌اپ را با کد کشور و بدون `+` بفرستید:

   ```text
   /pair 937xxxxxxxxx
   ```

4. ربات با درخواست زیر به Green API کد واقعی را می‌گیرد:

   ```text
   POST /waInstance{idInstance}/getAuthorizationCode/{apiTokenInstance}
   {"phoneNumber": 937xxxxxxxxx}
   ```

5. در WhatsApp بروید: `Linked devices → Link a device → Link with phone number instead` و کد را وارد کنید.

کد معمولاً ۸ کاراکتر دارد و حدود ۲.۵ دقیقه اعتبار دارد. instance باید پیش از درخواست کد در حالت `notAuthorized` باشد؛ اگر قبلاً وصل است، ابتدا آن را logout کنید.

## منابع

[1]: https://green-api.com/en/docs/api/account/GetAuthorizationCode/ "Green API — GetAuthorizationCode"
[2]: https://green-api.com/en/docs/api/recommendations/connecting-a-phone-number-to-the-Green-API/ "Green API — اتصال با شماره تلفن"
[3]: https://green-api.com/en/docs/api/receiving/technology-http-api/ReceiveNotification/ "Green API — دریافت notification"
