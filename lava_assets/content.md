# Тексты для карточек Lava.top (Квадрат Пифагора)

Универсальный вариант: один текст на все 3 пакета в каждом языке (RU/EN) —
конкретное число разборов и цену покупатель и так видит в названии товара
и в цене карточки, а сколько кредитов начислить бэкенд определяет сам по
`offerId` (см. `LAVA_OFFERS`/`PACKS` в `backend/main.py`) — в самих текстах
это дублировать не нужно.

Поля идут в порядке формы «Создание продукта» на Lava.top: **Название
продукта → Описание продукта → После оплаты → Письмо покупателю**.

**Картинки** — в `covers/`:
- `cover_ru.png` / `cover_en.png` — обложка (1160×464), одна на все 3 RU-пакета и одна на все 3 EN-пакета.
- `icon.png` — квадратная иконка (512×512, универсальная для RU и EN), на случай если где-то в интерфейсе Lava.top потребуется отдельно от обложки (в их документации по цифровым продуктам такого поля не нашлось, но раз просили — сделал про запас).

**Цена** вводится вручную в поле цены на Lava.top:
- RU: 399 ₽ / 999 ₽ / 1399 ₽ (pack3 / pack10 / pack15)
- EN: $5.99 / $11.99 / $15.99 (pack3 / pack10 / pack15— цену pack3
  подняли с $4.99 до $5.99, у Lava.top минимум $5 за товар)

Переключатель **«Цена по запросу через API»** — выключить: наш бэкенд
передаёт при создании счёта только `offerId`, `currency` и email, без
суммы, значит сумма должна браться из цены самой карточки.

---

## RU — названия трёх товаров (различаются только этим полем)

> Квадрат Пифагора — 3 разбора (399 ₽)
> Квадрат Пифагора — 10 разборов (999 ₽)
> Квадрат Пифагора — 15 разборов (1399 ₽)

## RU — Описание продукта (одинаковое для всех трёх)

> Доступ к вкладке «Графики» калькулятора «Квадрат Пифагора»: график жизненных сил и периоды жизни по дате рождения и ФИО. Разборы не сгорают и остаются на балансе до использования — доступ через вход по Telegram.

## RU — После оплаты (одинаковое для всех трёх)

> Оплата прошла успешно! Оплаченные разборы уже зачисляются на ваш баланс — обычно это занимает несколько минут. Откройте бот @AstroNumeros_bot, войдите через кнопку «Войти через Telegram» (тем же аккаунтом, что указывали при оплате) и откройте вкладку «Графики». Чек за покупку придёт отдельным письмом на указанный email.

## RU — Письмо покупателю — тема (одинаковое для всех трёх)

> Ваша покупка — Квадрат Пифагора

## RU — Письмо покупателю — текст (одинаковое для всех трёх)

> Здравствуйте!
>
> Спасибо за покупку — оплаченные разборы для калькулятора «Квадрат Пифагора» уже добавляются на ваш баланс (обычно автоматически, в течение нескольких минут после оплаты).
>
> Как получить доступ:
> 1. Откройте бот @AstroNumeros_bot в Telegram (или сайт, когда он заработает по постоянному адресу).
> 2. Войдите через кнопку «Войти через Telegram» — важно использовать тот же аккаунт, что и при оплате.
> 3. Введите дату рождения и ФИО, рассчитайте разбор и откройте вкладку «Графики» — теперь она доступна.
>
> Разборы не сгорают и остаются на балансе до использования.
>
> Если баланс не обновился в течение 15–20 минут после оплаты, или возникли вопросы — просто ответьте на это письмо или напишите на mvbern8@gmail.com.
>
> Спасибо, что выбрали «Квадрат Пифагора»!

---

## EN — three product names (only field that differs)

> Pythagorean Square — 3 readings ($5.99)
> Pythagorean Square — 10 readings ($11.99)
> Pythagorean Square — 15 readings ($15.99)

## EN — Product description (same for all three)

> Unlocks the "Charts" tab in the Pythagorean Square calculator: your life-force chart and life-period breakdown, based on your birth date and full name. Credits never expire — access via Telegram login.

## EN — After payment (same for all three)

> Payment successful! Your purchased readings are being added to your balance — this usually takes a few minutes. Open the @AstroNumeros_bot bot, sign in with "Log in with Telegram" (use the same account you paid with), and open the "Charts" tab. A receipt will be emailed to you separately.

## EN — Buyer email — subject (same for all three)

> Your purchase — Pythagorean Square

## EN — Buyer email — body (same for all three)

> Hello!
>
> Thank you for your purchase — your readings for the Pythagorean Square calculator are being added to your balance (usually automatically, within a few minutes of payment).
>
> How to access them:
> 1. Open the @AstroNumeros_bot bot in Telegram (or the website once it's live at a permanent address).
> 2. Sign in with "Log in with Telegram" — make sure to use the same account you paid with.
> 3. Enter a birth date and full name to run a reading, then open the "Charts" tab — it's now unlocked.
>
> Credits never expire and stay on your balance until used.
>
> If your balance hasn't updated within 15–20 minutes of payment, or you have any questions, just reply to this email or write to mvbern8@gmail.com.
>
> Thank you for choosing Pythagorean Square!
