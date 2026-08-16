# mpgu-rasp — миграция и новая архитектура

**Дата:** 2026-08-16
**Статус:** черновик, ждёт review

## Контекст

Запрос из t.me/MPGUgoodday/25708: студентам нужно приложение с расписанием
МПГУ. Ключевое требование — **точность**: данные в приложении обязаны
совпадать с расписанием на сайте mpgu.su, иначе теряется смысл.

В `mvbulgakova/mpgu-schedule` уже есть рабочий стек: Python-scraper с 5-уровневым
PDF-парсером, PWA на React, тонкий Android WebView, Cloudflare-workers, Telegram-бот,
data-ветка с ~700 групп по 16 институтам, набор skills для парсинга. Всё поднято, CI
крутится 2×/день + hot phase.

`mvbulgakova/mpgu-rasp` — пустой репо (0 коммитов), выбран как новый дом проекта.

## Цели

1. Перенести проверенные наработки из `mpgu-schedule` в `mpgu-rasp` без потери
   функциональности.
2. Ужесточить контроль **точности** данных (сверка с сайтом).
3. Заменить WebView-обёртку **нативным Android-клиентом** (Kotlin + Compose)
   с фичами, которых не даёт PWA (виджет, Wear OS, системный календарь, deep-link
   из пуша).
4. Прокачать **API-слой** (Cloudflare Worker + D1) для нативного клиента и
   сторонних интеграций.

Не-цели:
- Полный редизайн PWA (мигрирует как есть).
- iOS-клиент (не в этой итерации).
- ML/предсказание — только детерминистика и existing vision-fallback.

## Решения по scope (приняты пользователем)

- **Монорепо** `mpgu-rasp`: scraper + pwa + workers + telegram-бот + skills +
  новый нативный Android.
- **Миграция кода** — свежий initial commit из `mpgu-schedule`, история
  оригинала остаётся в архивном репо.
- **Data-ветка** наполняется свежим прогоном парсера в новом репо, не копируется
  из старого. (Сам формат данных — тот же.)
- **`mpgu-schedule`** остаётся как есть (архив на GitHub). PWA/бот на старых URL
  продолжают работать до переключения DNS.

## Что переносится (и что нет)

| Директория `mpgu-schedule` | Тащим? | Куда в `mpgu-rasp` |
|----------------------------|--------|---------------------|
| `scraper/` | да | `scraper/` |
| `pwa/` | да | `pwa/` |
| `cloudflare-worker/` | да | `cloudflare-worker/` (позже апгрейд до D1) |
| `cloudflare-worker-bot/` | да | `cloudflare-worker-bot/` |
| `.claude/skills/` | да | `.claude/skills/` |
| `.github/workflows/` | да | адаптировать URL к `mpgu-rasp` |
| `design.md`, `plan.md` | да | обновить URL-ссылки |
| `android/` (WebView) | **нет** | заменяется нативным Android |
| `app/`, `hyperbolic_sphere_app.py`, `build.gradle` в корне, `Procfile` | **нет** | легаси гиперболической сферы, чужой проект |
| `.data-wt/` | н/д | воркtree, локальный |
| `requirements.txt` в корне | нет | заменить на scraper/requirements.txt |

## Три технологические оси

### Ось 1. Точность парсинга — parity-check против сайта

**Проблема сегодня:** парсер верит источнику файлов; если МПГУ поменяет формат
или выложит битый PDF — данные тихо деградируют, никто не узнает пока студент
не пожалуется.

**Что делаем:**

1. **Golden fixtures** — для каждого института фиксируем:
   `fixtures/{id}/source.{ext}` (MD5-адресуемый снапшот), `fixtures/{id}/expected.json`
   (ожидаемые группы). Regression-тест: если парсер выдал не то — CI падает.
   Обновляем осознанно, PR отдельным.
2. **Дневной parity-diff** — параллельная workflow `parity-check.yml`:
   репарсит все институты и делает `parsed_now` vs `current data`.
   Diff кладёт в `meta/parity.json` (для UI), при отличиях > threshold →
   GitHub Issue + плашка в UI «данные разошлись с сайтом на N позиций».
3. **LLM-judge (не парсер, судья)** — при confidence < 0.8 или diff > N ячеек:
   Playwright снимает скриншот страницы МПГУ, Claude-vision сравнивает
   с распарсенным JSON, голосует «данные верны / нет». Judge-ответ логируется
   отдельным файлом (`meta/judge_log.jsonl`).
4. **Site screenshots** — Playwright снимает страницы источника с интервалом
   раз в неделю, храним в data-ветке `meta/snapshots/{institute}/{date}.png`
   для аудита при жалобе.

### Ось 2. Бэкенд-API — Cloudflare Worker + D1

**Сейчас:** тонкий Worker-прокси к `raw.githubusercontent.com/…/data`, простой
кеш по TTL.

**Апгрейд:**

- **D1 (SQLite на edge)** как индекс. Таблицы: `groups`, `lessons`, `institutes`,
  `teachers`, `exams`, `updates_log`.
- Наполнение через GitHub webhook: push в data-ветку → Worker берёт diff и
  инкрементально апдейтит D1.
- Эндпоинты:
  - `GET /institutes` — список
  - `GET /groups/search?q={q}` — поиск по коду с учётом гомоглифов
  - `GET /schedule/{group}?week=current|even|odd` — расписание
  - `GET /next-lesson/{group}` — быстрый ответ для виджета/пуша
  - `GET /diff?since={ts}` — инкрементальные апдейты для клиента
  - `GET /ical/{group}.ics` — на лету собираем iCal
  - `GET /exams/{group}` — сессия
  - `GET /parity` — статус сверки с сайтом (для клиента)
- **ETag + `If-None-Match`** — экономия трафика мобильного клиента.
- **CORS открыт** — сторонние (боты, виджеты) могут интегрировать.
- **Rate-limit** — 60 req/min с IP (бесплатный tier Cloudflare это тянет).

Старый прокси-Worker остаётся как fallback (raw GH → CDN).

### Ось 3. Нативный Android (Kotlin + Compose)

**Стек:**
- Kotlin 2.0, Coroutines + Flow
- Jetpack Compose, Material 3, Compose Navigation
- Ktor client + kotlinx.serialization
- Room 2 для offline-кеша
- WorkManager для фоновых апдейтов и пуш-обвязки
- DataStore для настроек (выбранная группа, тема, etc)
- Hilt для DI
- Glance для домашнего виджета
- Wear Compose для watch companion (позже)
- Firebase Cloud Messaging для пушей

**Package:** `ru.mpgu.rasp` (`android/` в mpgu-schedule был `ru.mpgu.schedule`).

**Экраны:**
1. Onboarding: выбор института и группы (skippable, потом настраивается)
2. Institutes: список 16 институтов (с индикатором свежести данных)
3. Groups: поиск, pinned наверху, группировка по степени
4. Week: pager по дням, чётная/нечётная, автопрыжок на сегодня, «сейчас»-плашка
5. Lesson details: полный формат, кнопки «в календарь», «поделиться»
6. Teacher: поиск преподавателя и его расписание
7. Exams: сессия
8. Settings: тема, чётность вручную, push, виджет-конфиг

**Фичи, которых нет в PWA:**
- **Glance-виджет** «сегодня / ближайшая пара» — самое востребованное
- **Wear OS** мини-приложение «что сейчас» (следующая итерация)
- **FCM-пуши**: «пара через N минут», «изменения в расписании» (после `/diff`)
- **CalendarContract** — вставка пары в системный календарь одной кнопкой
- **Deep-link** из пуша/виджета сразу в конкретную пару
- **Monet + Material You** (Android 12+): динамические цвета из обоев
- **Adaptive icon**

**Не делаем в первой итерации:** offline-first sync (кеш есть, но не полный
graceful merge с апдейтами), collaboration (заметки к парам общие), AR-виджет,
голосовой ассистент.

## Архитектурная диаграмма

```
┌──────────────────┐     GH Actions cron     ┌──────────────────┐
│  МПГУ sources    │  ─── scrape.yml (2/day)  →│  data branch     │
│  (сайт, nextcloud)│  ─── parity-check.yml     │  (JSON per group)│
└──────────────────┘        (daily)             └────────┬─────────┘
        ▲                                                │
        │ Playwright screenshots                         │ webhook push
        │ (weekly + on-demand)                           ▼
        │                                       ┌──────────────────┐
        │                                       │  Cloudflare      │
        └── LLM-judge on low-confidence ────────│  Worker + D1     │
                                                │  API + iCal      │
                                                └────────┬─────────┘
                                                         │
                       ┌─────────────────────────────────┼────────────────┐
                       │                                 │                │
                       ▼                                 ▼                ▼
              ┌──────────────┐              ┌──────────────────┐  ┌─────────────┐
              │  PWA         │              │  Native Android  │  │  Telegram   │
              │  (React)     │              │  (Kotlin+Compose)│  │  bot        │
              │  GH Pages    │              │  Play/APK        │  │  (Worker)   │
              └──────────────┘              └──────────────────┘  └─────────────┘
```

## План работ (высокоуровневый — writing-plans развернёт)

**Этап 0. Миграция исходников (≈ 1 сессия)**
- Скопировать выбранные директории из `mpgu-schedule` в `mpgu-rasp`.
- Обновить абсолютные ссылки на репо в конфигах и workflow'ах.
- Обновить `CLAUDE.md` для нового имени, оставить ссылку на архив.
- Первый прогон парсера — заполнить data-ветку в новом репо.
- Убедиться, что PWA собирается и деплоится (GitHub Pages).

**Этап 1. Parity-check (≈ 2-3 сессии)**
- Golden fixtures для 3 «сложных» институтов (childhood, international, languages).
- `parity-check.yml` workflow с diff и Issue.
- Playwright site-screenshots (weekly).
- LLM-judge на low-confidence.
- Badge «расхождение» в PWA.

**Этап 2. API + D1 (≈ 2 сессии)**
- Схема D1, миграции.
- Webhook data-branch → D1 apply.
- Эндпоинты + ETag + iCal generator.
- Rate-limit, CORS.

**Этап 3. Нативный Android — минимум (≈ 3-4 сессии)**
- Проект, Compose, навигация, тема Material 3.
- Экраны 1-4 (Onboarding, Institutes, Groups, Week).
- Room-кеш, Ktor-клиент к нашему API.
- Первый релиз APK через `build-android.yml`.

**Этап 4. Android фичи (≈ 3 сессии)**
- Glance-виджет.
- FCM-пуши (с сервером-триггером).
- CalendarContract, deep-link, share.
- Экраны Teacher, Exams, Settings.

**Этап 5. Wear OS + бонусы** — после релиза первой версии.

## Риски и открытые вопросы

- **Play Store подпись** — если публиковать в Play, нужен keystore + `.aab`.
  До Play — раздача APK через GitHub Releases (уже есть в build-webview.yml).
- **FCM** — требует Firebase project и `google-services.json`. Backend-триггер
  живёт на том же Worker'е.
- **Rate-limit на МПГУ** — parity-check каждый день = +16 запросов. Не проблема,
  но добавим `User-Agent: mpgu-rasp parity-check` для честности.
- **D1 quota** — бесплатный tier: 100k чтений/день. С 700 групп и push-нотификаций
  должно хватить, при росте — SQL-in-object storage fallback.
- **История парсера** — все аккумулированные хеши в `meta/hashes.json` теряются
  при свежем прогоне; первый прогон в новом репо будет тяжёлым (все PDF
  считаются «изменившимися»). Один раз, потом инкрементально.

## Что дальше

После apruv этого дизайна вызываю `writing-plans` и разворачиваю Этап 0
(миграция) в конкретный implementation plan с задачами.
