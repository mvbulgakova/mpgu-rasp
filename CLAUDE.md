# mpgu-rasp — agent guide

Приложение с расписанием МПГУ + весь pipeline вокруг него: парсер, PWA,
нативный Android, Cloudflare-воркеры, Telegram-бот. Родился как перенос из
[`mvbulgakova/mpgu-schedule`](https://github.com/mvbulgakova/mpgu-schedule)
(архивный репо с полной историей коммитов); методология парсинга и данные
переехали, дальнейшее развитие — здесь.

## Skills first

Библиотека skills в `.claude/skills/` (в стиле и частично vendored из
[obra/superpowers](https://github.com/obra/superpowers)).

**Перед любой нетривиальной задачей — проверить, есть ли подходящий skill,
и вызвать его.** Даже если шанс подходящего skill ~1% — вызывай.

Три семейства:

- **General engineering discipline** (vendored из superpowers, MIT — см.
  `.claude/skills/_vendor/ATTRIBUTION.md`): `brainstorming`, `writing-plans`,
  `executing-plans`, `test-driven-development`, `systematic-debugging`,
  `verification-before-completion`, `requesting-code-review`,
  `subagent-driven-development`, `using-git-worktrees`,
  `finishing-a-development-branch`, `using-superpowers`.
  Начинай сессию с `using-superpowers`.

- **Методология парсинга MPGU** (специфика проекта):
  - `parsing-mpgu-schedules` — entry point для любой задачи по данным.
  - `choosing-a-schedule-parser` — детерминизм в первую очередь, Surya только для скан-PDF.
  - `handling-mpgu-group-codes` — гомоглифы, регекс кода, majority voting.
  - `verifying-schedule-completeness` — аудит источника до заявления «готово».
  - `safe-schedule-data-merges` — additive-no-loss vs replace.
  - `publishing-schedule-data` — data-ветка, синк индекса, конвенции коммит/пуш.

  Для ЛЮБОЙ задачи, трогающей `institutes/*` в data-ветке, начинай с
  `parsing-mpgu-schedules`.

- **Поддержка библиотеки skills:** `maintaining-project-skills`.

## Форма проекта

- **Scraper / парсеры:** `scraper/parsers/` (`pdf_parser`, `excel_parser`,
  `gsheets_parser`, `surya_column_parser`), нормализатор в
  `scraper/normalizer/`, storage в `scraper/storage/git_storage.py`,
  VLM reparse driver `scraper/reparse_vision.py` (`--surya`).
- **Data:** ветка `data` (worktree в `.data-wt/`) хранит
  `institutes/<id>/groups/*.json`, `institutes/<id>/schedule.json` и
  `meta/index.json`. Код/конфиг — в feature-ветке; данные — в `data`.
- **PWA:** `pwa/` (React + Vite + Tailwind + Zustand + TanStack Query),
  деплой на GitHub Pages.
- **Cloudflare workers:** `cloudflare-worker/` (CDN-прокси к data-ветке),
  `cloudflare-worker-bot/` (Telegram-бот на вебхуках).
- **Native Android:** `android/` — Kotlin + Jetpack Compose (в разработке,
  см. `docs/superpowers/specs/2026-08-16-mpgu-rasp-migration-design.md`).
- **Telegram-бот на GitHub Actions long-polling:** `scraper/telegram_bot.py`
  (альтернатива вебхукам, если нет Cloudflare).

## Non-negotiables

- **Точность важнее полноты.** Приложение обязано совпадать с сайтом mpgu.su.
  Расхождение — это баг класса P0.
- **Никогда не терять данные.** Garbled group code хуже, чем missing group.
- **Никогда не верить group count** — diff parsed-unique против текущих данных
  и объяснить каждый LOSE/GAIN перед публикацией
  (`verifying-schedule-completeness`).
- **`meta/index.json` counts** = актуальным файлам на диске.

## Отношения с mpgu-schedule (архив)

- Старый репо — `mvbulgakova/mpgu-schedule`, оставлен как есть на GitHub.
- PWA/бот на старых URL продолжают работать до переключения DNS/поддоменов.
- Полная git-история проекта — в архивном репо. Здесь initial commit
  (2026-08-16) — снапшот тех наработок.

## Активный дизайн-план

`docs/superpowers/specs/2026-08-16-mpgu-rasp-migration-design.md` — три оси:
parity-check против сайта, Cloudflare Worker + D1 API, нативный Android
(Kotlin + Compose). См. этапы 0-5.
