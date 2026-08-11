# All-amani Python Bot

این پروژه نسخهٔ Python پروژهٔ `All-amani-main` است. تمام **۳۳ فایل JavaScript** پروژه دارای معادل Python هستند؛ مهم‌ترین فایل‌ها از این قرارند:

| JavaScript اصلی | معادل Python |
|---|---|
| `index.js` | `index.py` و `main.py` |
| `bot.js` | `bot.py` |
| `pair.js` | `pair.py` |
| `autoload.js` | `autoload.py` |
| `drenox.js` | `drenox.py` و `app/commands.py` |
| `setting/config.js` | `setting/config.py` و `app/config.py` |
| `utils.js` | `utils.py` و `app/utils.py` |
| `token.js` | `token_config.py`؛ بدون نگه‌داری توکن واقعی |
| `allfunc/*.js` | `allfunc/*.py` |
| `commands/*.js` و `handlers/*.js` | معادل‌های Python همان مسیرها |

## تغییر مهم در اتصال واتس‌اپ

نسخهٔ Node.js به Baileys و Node 18 وابسته بود. در نسخهٔ Python، برای اینکه پروژه روی هاست دارای **Python 3.9** هم نصب شود، اتصال واتس‌اپ با Green API انجام می‌شود. این مسیر از endpoint رسمی `getAuthorizationCode` برای کد جفت‌سازی شماره‌ای استفاده می‌کند و نیازمند نصب Neonize، Node.js یا QR محلی نیست.

> توجه: یک Green API instance فقط یک حساب واتس‌اپ را هم‌زمان مدیریت می‌کند. برای چند حساب مستقل باید برای هر حساب instance جداگانه یا یک gateway چندنشسته روی هاست مناسب تهیه شود.

## نصب

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

توکن Telegram را فقط در متغیر محیطی یا بخش Secrets پنل استقرار قرار دهید:

```text
BOT_TOKEN=توکن_ربات_تلگرام
DEVELOPER_IDS=8764900501
```

توکن واقعی پروژهٔ قدیمی عمداً وارد این نسخه نشده است؛ اگر آن توکن قبلاً عمومی شده، آن را در BotFather لغو و توکن تازه بسازید.

## اجرای پروژه

```bash
python main.py
```

در اپ GSM Telegram Bot Hosting، فایل `main.py` را انتخاب کنید. وابستگی‌های `requirements.txt` با Python 3.9 سازگارند و دیگر `neonize` یا پکیج‌های Node.js را نصب نمی‌کنند.

## اتصال با کد جفت‌سازی

ابتدا در [Green API Console](https://console.green-api.com/) یک instance بسازید. سپس مالک ربات در چت خصوصی Telegram این فرمان را وارد کند:

```text
/green <instance_id> <api_token>
```

بعد برای دریافت کد شماره‌ای:

```text
/pair 937xxxxxxxxx
```

یا کافی است `/start` بزنید و شماره را در پیام بعدی بفرستید. ربات کد واقعی را فقط برای همان چت Telegram می‌فرستد. در WhatsApp بروید:

```text
Linked devices → Link a device → Link with phone number instead
```

و کد را وارد کنید. کد معمولاً ۸ کاراکتر دارد و زمان اعتبار محدودی دارد.

## فرمان‌های واتس‌اپ

فرمان‌های اصلی مانند `.ping`، `.menu`، `.runtime`، `.owner`، `.id`، `.calc`، `.settings`، `.on`، `.off`، `.antilink`، `.antibadword`، `.autoreply`، `.autoread` و `broadcast` پیاده‌سازی شده‌اند. تمام ۶۴۴ نام فرمان استخراج‌شده از `drenox.js` در `legacy_command_names.txt` ثبت شده‌اند؛ فرمان‌هایی که به scraper یا API اختصاصی Node.js نیاز دارند، به‌صورت شفاف پیام سازگاری می‌دهند تا بدون خطای خاموش مشخص باشد کدام سرویس باید جداگانه اضافه شود.

## امنیت و داده‌ها

فایل `.env`، نشست‌ها، `pairing.json` و tokenهای Green API در `.gitignore` قرار دارند. فایل‌های pairing قدیمی از ZIP به نسخهٔ Python منتقل نشده‌اند تا کد جفت‌سازی یا نشست خصوصی منتشر نشود. رسانه‌ها و داده‌های غیرمحرمانهٔ پروژه در ساختار خود نگه داشته شده‌اند.

## منابع

راهنمای رسمی Green API برای [دریافت کد جفت‌سازی](https://green-api.com/en/docs/api/account/GetAuthorizationCode/) و [اتصال شماره تلفن](https://green-api.com/en/docs/api/recommendations/connecting-a-phone-number-to-the-Green-API/) در دسترس است.
