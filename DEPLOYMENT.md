# راهنمای رفع خطای استقرار Python 3.9

## علت خطا

وابستگی `neonize` فقط با Python 3.10 یا جدیدتر سازگار است. اگر در لاگ استقرار این خط را می‌بینید، پلتفرم هنوز از image قدیمی استفاده می‌کند:

```dockerfile
FROM python:3.9-slim
```

این خط از پیکربندی پلتفرم می‌آید؛ نه از `requirements.txt` پروژه. در نتیجه، تغییر نسخهٔ Neonize یا اجرای مجدد build با Python 3.9 مشکل را حل نمی‌کند.

## تنظیم لازم در پلتفرم

یکی از گزینه‌های زیر را انجام دهید:

1. اگر پلتفرم گزینهٔ **Dockerfile** دارد، حالت Build/Deploy را روی `Dockerfile` قرار دهید. Dockerfile این مخزن از `python:3.11-slim` استفاده می‌کند.
2. اگر پلتفرم انتخاب **Runtime / Python version** دارد، آن را به `3.11` یا حداقل `3.10` تغییر دهید.
3. اگر پلتفرم یک Dockerfile ثابت نشان می‌دهد، خط اول آن را به این مقدار تغییر دهید:

   ```dockerfile
   FROM python:3.11-slim
   ```

4. اگر پلتفرم از Nixpacks استفاده می‌کند، فایل `nixpacks.toml` در مخزن به‌طور خودکار Python 3.11 را درخواست می‌کند.
5. اگر پلتفرم از Buildpack استفاده می‌کند، فایل‌های `runtime.txt` و `.python-version` در مخزن Python 3.11 را مشخص می‌کنند.

پس از تغییر، گزینهٔ **Clear build cache / Rebuild without cache** را بزنید و deploy را دوباره شروع کنید.

## بررسی موفقیت

ابتدای لاگ جدید باید چیزی شبیه به این باشد:

```text
FROM python:3.11-slim
```

یا باید نصب Neonize را بدون پیام `Requires-Python >=3.10` ادامه دهد.

## دستور محلی Docker

```bash
docker build --no-cache -t jan-main-python .
docker run --rm -p 8080:8080 --env-file .env jan-main-python
```
