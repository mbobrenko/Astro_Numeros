# Тексты для карточек Lava.top (Нумерологический разбор судьбы)

Маркетплейс-название специально без термина «Квадрат Пифагора» — на
Lava.top товар называется и описывается как «Нумерологический разбор
судьбы» (EN: «Numerology Destiny Reading»); на самом сайте/в боте
название сервиса не меняется, это только витрина на Lava.top.

Универсальный вариант: один текст на оба пакета в каждом языке (RU/EN) —
конкретное число разборов и цену покупатель и так видит в названии товара
и в цене карточки, а сколько кредитов начислить бэкенд определяет сам по
`offerId` (см. `LAVA_OFFERS`/`PACKS` в `backend/main.py`) — в самих текстах
это дублировать не нужно.

Поля идут в порядке формы «Создание продукта» на Lava.top: **Название
продукта → Описание продукта → После оплаты → Письмо покупателю**.

**Картинки** — в `covers/`:
- `cover_ru.png` / `cover_en.png` — обложка (1160×464), одна на оба RU-пакета и одна на оба EN-пакета. Короткое описание проекта уже встроено в саму картинку текстом (заголовок + два предложения), как и просили.
- `icon.png` — квадратная иконка (512×512, универсальная для RU и EN), на случай если где-то в интерфейсе Lava.top потребуется отдельно от обложки.

**Цена** вводится вручную в поле цены на Lava.top:
- RU: 999 ₽ / 2499 ₽ (pack3 / pack10)
- EN: $14.99 / $34.99 (pack3 / pack10 — в том же соотношении к рублю, что
  вы задали; это моё предложение по курсу, проверьте и поправьте если нужно)

Пакетов теперь два (было три) — тариф на 15 разборов убрали по вашему решению,
после окончания любого пакета можно докупить ещё.

Переключатель **«Цена по запросу через API»** — выключить: наш бэкенд
передаёт при создании счёта только `offerId`, `currency` и email, без
суммы, значит сумма должна браться из цены самой карточки.

---

## RU — названия двух товаров (различаются только этим полем)

> Нумерологический разбор судьбы — 3 разбора (999 ₽)
> Нумерологический разбор судьбы — 10 разборов (2499 ₽)

## RU — Описание продукта (одинаковое для обоих)

> Персональный нумерологический разбор судьбы: график жизненных сил и периоды жизни по дате рождения и ФИО. Доступ открывается сразу после оплаты, разборы не сгорают и остаются на балансе до использования — вход через Telegram.

## RU — После оплаты (одинаковое для обоих)

> Оплата прошла успешно! Оплаченные разборы уже зачисляются на ваш баланс — обычно это занимает несколько минут. Откройте бот @AstroNumeros_bot, войдите через кнопку «Войти через Telegram» (тем же аккаунтом, что указывали при оплате) и откройте вкладку «Графики». Чек за покупку придёт отдельным письмом на указанный email.

## RU — Письмо покупателю — тема (одинаковое для обоих)

> Ваша покупка — нумерологический разбор судьбы

## RU — Письмо покупателю — текст (одинаковое для обоих, сокращено)

> Здравствуйте!
>
> Спасибо за покупку — разборы уже добавляются на баланс автоматически, обычно в течение нескольких минут.
>
> Как получить доступ:
> 1. Откройте бот @AstroNumeros_bot в Telegram (или сайт, когда заработает постоянный адрес) и войдите тем же аккаунтом Telegram, что и при оплате.
> 2. Введите дату рождения и ФИО и откройте вкладку «Графики» — теперь она доступна.
>
> Разборы не сгорают.
>
> Если баланс не обновился за 15–20 минут после оплаты, или есть вопросы — ответьте на это письмо или напишите на mvbern8@gmail.com.

---

## EN — two product names (only field that differs)

> Numerology Destiny Reading — 3 readings ($14.99)
> Numerology Destiny Reading — 10 readings ($34.99)

## EN — Product description (same for both)

> A personal numerology destiny reading: your life-force chart and life-period breakdown, based on your birth date and full name. Unlocked instantly after payment, credits never expire — access via Telegram login.

## EN — After payment (same for both)

> Payment successful! Your purchased readings are being added to your balance — this usually takes a few minutes. Open the @AstroNumeros_bot bot, sign in with "Log in with Telegram" (use the same account you paid with), and open the "Charts" tab. A receipt will be emailed to you separately.

## EN — Buyer email — subject (same for both)

> Your purchase — numerology destiny reading

## EN — Buyer email — body (same for both, shortened)

> Hello!
>
> Thanks for your purchase — your readings are added to your balance automatically, usually within a few minutes.
>
> How to access:
> 1. Open @AstroNumeros_bot in Telegram (or the website once it's live) and sign in with the same Telegram account you paid with.
> 2. Enter your birth date and full name, then open the "Charts" tab — it's unlocked.
>
> Credits never expire.
>
> Balance not updated within 15–20 minutes, or questions? Reply here or write to mvbern8@gmail.com.
