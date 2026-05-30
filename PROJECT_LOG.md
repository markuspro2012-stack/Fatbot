# PROJECT_LOG — CalBot (FatBot)

> Лог создан: 2026-05-30 | Последнее обновление: 2026-05-30

---

<!-- RESUME HERE — переписывать ПОЛНОСТЬЮ после каждого шага, коммита, деплоя, проблемы -->
## ⚡ RESUME HERE

**Project**: CalBot (FatBot)
**Folder**: `g:\VS CODE\calbot\`
**Stack**: Python 3.11, aiogram v3, Gemini Vision API, OpenFoodFacts API, PostgreSQL (Supabase), APScheduler, matplotlib, Railway.app
**Status**: Active
**Last session**: 2026-05-30

### Где мы сейчас
**Шаг**: 9 из 9 — Тестирование и доработка на Render
**Статус шага**: In progress

### Что было сделано последним
Бот задеплоен на Render. Доработан food_photo.py: добавлены кнопки "Изменить название", "Искать вручную" (поиск OpenFoodFacts), "⭐ Сохранить как избранное" после добавления. Исправлен render.yaml — добавлен GEMINI_API_KEY. Gemini API ключ добавлен пользователем в api keys.md.

### Следующее действие
Протестировать фото-распознавание — отправить фото еды в Telegram и проверить что бот распознаёт и предлагает все кнопки.

### Блокеры
None

### Ключевые данные
**Последний коммит**: "Step 9: Food photo improvements — edit name, manual search, save favorite; fix render.yaml GEMINI_API_KEY"
**Deploy URL**: на Render (запрос URL у пользователя)
**Открытые решения**: нет
**Непроверенные допущения**: нет — GEMINI_API_KEY добавлен через Render API, редеплой запущен

### Предупреждение о сессии

<!-- END RESUME HERE -->

---

## Overview

CalBot — умный Telegram-бот для трекинга питания. Распознаёт еду по фото через Gemini Vision, считает КБЖУ, ведёт дневник питания, отправляет умные уведомления. Помогает пользователю достигать целей по весу через персональные лимиты.

## Stack

- **Bot framework:** Python 3.11 + aiogram v3 (async)
- **AI Vision:** Google Gemini Vision API
- **Nutrition DB:** OpenFoodFacts API (free, 500k+ продуктов)
- **Database:** PostgreSQL (Supabase free tier) + SQLAlchemy async
- **Scheduler:** APScheduler (уведомления)
- **Charts:** matplotlib
- **Hosting:** Railway.app (free tier)

## Links

- **Git:** [markuspro2012-stack/Fatbot](https://github.com/markuspro2012-stack/Fatbot)
- **Deploy:** — (заполнить после деплоя)
- **Local:** `g:\VS CODE\calbot\`
- **API Keys:** `g:\VS CODE\api keys.md`

---

## Implementation Plan

- [x] Step 1: Основа — структура проекта, БД, модели, /start /help ✅ 2026-05-30
- [x] Step 2: Онбординг — FSM-форма профиля, BMR/TDEE расчёт, /profile /setup ✅ 2026-05-30
- [x] Step 3: Ручной ввод еды — поиск OpenFoodFacts, выбор порции, /add текстом ✅ 2026-05-30
- [x] Step 4: AI распознавание фото — Gemini Vision, подтверждение, сохранение ✅ 2026-05-30
- [x] Step 5: Дашборд и аналитика — /today /week /left, графики matplotlib ✅ 2026-05-30
- [x] Step 6: Уведомления — APScheduler, утро/вечер/еда/вода, /notifications ✅ 2026-05-30
- [x] Step 7: Умные фичи — сохранённые блюда, лог веса, стрики, водный баланс ✅ 2026-05-30
- [x] Step 8: Деплой — Railway.app конфиги готовы ✅ 2026-05-30 (ожидает ручного деплоя)

---

## Problems Log

> Записывать сразу при возникновении. Статусы: 🔴 Open | 🟡 In Progress | ✅ Resolved

| ID | Дата | Проблема | Статус | Решение | Причина | Дата решения |
|----|------|----------|--------|---------|---------|--------------|
| — | — | Проблем не зафиксировано | — | — | — | — |

---

## Deploy History

| Дата | Коммит | Окружение | URL | Проверен | Заметки |
|------|--------|-----------|-----|----------|---------|
| — | — | — | — | — | Ожидает первого деплоя |

---

## Decisions

| ID | Дата | Решение | Причина | Альтернативы | Влияет на |
|----|------|---------|---------|--------------|-----------|
| DEC-1 | 2026-05-30 | aiogram v3 | Современный async, FSM из коробки, активная поддержка | python-telegram-bot | Вся архитектура бота |
| DEC-2 | 2026-05-30 | OpenFoodFacts вместо платных API | Бесплатно, 500k+ продуктов, открытый | Nutritionix, Edamam | Step 3 (ручной ввод еды) |
| DEC-3 | 2026-05-30 | Railway.app для хостинга | Free tier, поддержка Python + PostgreSQL addon | Heroku, Render | Step 8 (деплой) |
| DEC-4 | 2026-05-30 | Supabase для PostgreSQL | Free tier 500MB, простое подключение | PlanetScale, Neon | Все шаги с БД |
| DEC-5 | 2026-05-30 | Gemini Vision вместо GPT-4o | Бесплатный tier, аналогичное качество распознавания | OpenAI GPT-4o Vision | Step 4 (AI фото) |

---

## Session History

<!-- Новые сессии добавлять СВЕРХУ -->

### Session 2026-05-30 — Полная разработка бота (шаги 1–8)

**Статус при старте**: Шаг 1/8 — новый проект
**Резюм с**: нет коммитов
**Цель сессии**: Разработать полный Telegram-бот для трекинга калорий с AI-распознаванием

**Выполнено:**
- Шаг 1: Структура проекта, модели БД (User, FoodLog, WeightLog, WaterLog, SavedMeal), /start, /help, config.py, database.py
- Шаг 2: FSM онбординг (пол→возраст→рост→вес→активность→цель), BMR/TDEE по Mifflin-St Jeor, /profile, /setup
- Шаг 3: Поиск еды через OpenFoodFacts API, выбор порции inline-кнопками, /add, сохранение в FoodLog
- Шаг 4: AI распознавание фото через Gemini Vision, подтверждение результата, сохранение в дневник
- Шаг 5: Дашборд (/today, /week, /left), графики matplotlib по дням/неделям, статистика КБЖУ
- Шаг 6: APScheduler уведомления (утро, вечер, напоминания о еде и воде), /notifications управление
- Шаг 7: Сохранённые блюда (/saved), лог веса (/weight), стрики активности, водный баланс (/water)
- Шаг 8: Конфиги деплоя — Procfile, railway.json, runtime.txt, render.yaml; health endpoint в main.py

**Проблемы:** None

**Файлы созданы:**
- `main.py` — точка входа, polling, health server (aiohttp)
- `config.py` — константы, уровни активности, цели
- `database.py` — engine + AsyncSessionLocal
- `models/user.py`, `models/food_log.py`, `models/weight_log.py`, `models/water_log.py`, `models/saved_meal.py`
- `handlers/start.py`, `handlers/onboarding.py`, `handlers/profile.py`
- `handlers/food_add.py`, `handlers/food_photo.py`
- `handlers/dashboard.py`, `handlers/notifications.py`, `handlers/extras.py`
- `services/calculator.py`, `services/food_api.py`, `services/vision.py`, `services/stats.py`, `services/scheduler.py`
- `utils/charts.py`
- `Procfile`, `railway.json`, `runtime.txt`, `render.yaml`, `.env.example`, `.gitignore`, `requirements.txt`

**Коммиты:**
- `3787a30` — "Step 1: Project foundation — models, handlers, config, database"
- `29d1d08` — "Step 2: Onboarding FSM, profile setup, BMR/TDEE calculator"
- (шаги 3–8 — см. GitHub репозиторий markuspro2012-stack/Fatbot)

**Деплои:** —

**Решения:** DEC-1 через DEC-5 (см. Decisions выше)

### Session End — 2026-05-30
**Завершено в сессии**: Шаги 1–8 полностью разработаны и закоммичены
**Шаг при закрытии**: 8/8 — Деплой (ожидает ручных действий)
**Следующее действие**: Задеплоить на Railway.app — открыть railway.app, создать проект, подключить GitHub repo markuspro2012-stack/Fatbot, добавить env vars (TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, DATABASE_URL), добавить PostgreSQL addon
**Открытые проблемы**: нет
**Предупреждение**: нет

---
