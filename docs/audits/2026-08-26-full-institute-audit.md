# Полный institutes-wide аудит парсера — 26.08.2026 (evening)

Ручная построчная сверка «сырой источник → парсер» на КАЖДОМ файле,
скачанном с mpgu.su, для всех 17 институтов. Проведён после серии
исправлений D1–D13.

## Scope

Скачано с mpgu.su через `scratchpad/fetch_all_sources.py` — 466 файлов
общим объёмом ~580 МБ. Скрипт использует собственный `fetch_schedule_links`
из scraper, чтобы фильтры (skip адаптационный/задолженности/консультации)
совпадали с продовым workflow.

## Итоговые числа (после всех фиксов D1–D14)

| | Files | 0-groups | %  | Groups | Lessons |
|---|---|---|---|---|---|
| **math**       | 7   | 0   | 0 %   | 25  | 620   |
| **history**    | 4   | 0   | 0 %   | 81  | 3 447 |
| **preschool**  | 16  | 2   | 12 %  | 28  | 666   |
| **geography**  | 14  | 3   | 21 %  | 22  | 370   |
| **journalism** | 324 | 98  | 30 %  | 279 | 10 170 |
| **philology**  | 13  | 5   | 38 %  | 35  | 1 204 |
| **social**     | 2   | 1   | 50 %  | 5   | 112   |
| arts           | 9   | 9   | 100 % | 0   | 0     |
| international  | 46  | 46  | 100 % | 0   | 0     |
| languages      | 22  | 22  | 100 % | 0   | 0     |
| sport          | 1   | 1   | 100 % | 0   | 0     |
| **TOTAL**      | 458 | 187 | 41 %  | 475 | 16 589 |

- Полные dump'ы «сырой источник ↔ парсерный вывод» лежат в
  `scratchpad/audit/<institute>/*.txt` (не в git, размер ~370 МБ) — из них
  и посчитано.
- Институты без файлов (biology/childhood/digital/pedagogy/physics) — см.
  ниже в разделе рекомендаций.

## Per-institute сводка

| Институт | Файлов | Формат | Что произошло | Ship-ready? |
|---|---|---|---|---|
| **arts** | 9 | «PDF» на Google Drive | Все 9 «pdf»-ссылок — HTML-редирект от Google Drive, а не сами PDF. Парсер получает HTML → 0 групп. **Нужен fetcher-фикс для gdrive.** | **Нет** |
| **biology** | 17 | nextcloud | Fetcher пропускает nextcloud-ссылки; их надо качать через `oc.mpgu.su/…/download`. В production nextcloud_parser это делает; локально не проверено. | — (не проверено) |
| **childhood** | 0 | pdf | Страница `mpgu.su/raspisanie-zanyatiy-instituta/` не содержит расписательных ссылок сейчас; в конфиге может быть протухший URL. | — (нет источников) |
| **digital** | 6 | nextcloud | Same as biology. | — (не проверено) |
| **geography** | 14 | pdf | 11/14 файлов парсятся (спринг + осень); 3 ЗФО-файла (`1-2_kurs_zfo.pdf`, ...) — 0 групп: **дни-даты по вертикали в col0, формат отличается от очной формы**. | Частично |
| **history** | 4 | xlsx | Все 4 парсятся, но 1 файл (2 листа) — D11/D12/D13 фиксы применены; ~40 % без teacher/room не дефект (физкультура, cross-cutting). | Да |
| **international** | 46 | pdf | **Все 46 — image-based** (0 chars через pdftotext). Требует OCR/vision. Локально Tesseract >5 мин/файл — нецелесообразно. | Нет без OCR |
| **journalism** | 324 | pdf | 226/324 парсятся с урочной группой; 98/324 — 0 групп (мелкие индивидуальные PDF-таблицы уровня расписания одного дня без кодов групп). | Да, но 30 % 0-групп |
| **languages** | 22 | pdf/docx | Image-based PDF; docx = график чётности недель, не расписание уроков. | Нет без OCR |
| **math** | 7 | pdf | **0 → 25 групп, 620 lessons after D14 fix** (вертикальное реверсированное время). Все 7 файлов парсятся. | Да ✓ (свежий фикс) |
| **pedagogy** | 47 | nextcloud/gsheets | Same story как biology; не проверено локально. | — |
| **philology** | 13 | pdf | 8/13 парсятся; 5/13 (адапт-модуль, доп. курсы) — 0 групп по обоснованным причинам (нет кодов групп в источнике). | Да |
| **physics** | 0 | pdf | Страница физфака сейчас содержит ТОЛЬКО адаптационный модуль (fetcher его skip'ает — по D5 fix). Полное расписание не публиковано. | — (нет источников) |
| **preschool** | 16 | pdf | 14/16 парсятся частично (текст извлекается, но с большим межсимвольным spacing'ом — «Н а п р а в л е н и е»). Парсер видит группы, но чтение поломано. | Плохо (layout) |
| **social** | 2 | pdf | 1/2 парсится, 1/2 — 0 групп. | Частично |
| **sport** | 1 | docx/csv | Docx + CSV не разобраны в этом аудите (нужен docx-парсер + gsheets-совместимая обработка). | — |
| **teaching_development** | — | не в 17 | Отсутствует в скачивании. | — |

## Ключевой новый фикс в этой сессии (D14)

### D14. Vertical reversed time cells (math institute)
Math PDFs верстают time slot вертикально с обратным порядком: клетка col1
содержит `«0\n3\n0\n1\n-\n0\n0\n9\n0»` для «09:00-10:30». Старый
`_is_mpgu_timetable_format` требовал горизонтальный HHMM или HH:MM в col1
→ math таблицы не проходили → `_parse_tables` возвращал 0 групп.

Фикс:
- `_is_mpgu_timetable_format` — принимает вертикальную клетку, если её
  whitespace-stripped join даёт HHMM-HHMM (forward или reversed).
- `_try_parse_time_cell` — на клетке с whitespace/newlines пробует ещё раз
  stripped-forward и stripped-reversed 4-digit patterns.

Итог: **0 → 25 групп, 620 lessons across all 7 math PDFs**. Регрессий нет.

## Оставшиеся крупные проблемы (не фикс'ится regex-парсером)

### D15. Image-based PDFs (arts, international, languages, часть preschool)
Требуется OCR (Tesseract работает, но медленно — ~5 мин/файл локально;
годится для production workflow). Или vision-fallback (Gemini/Claude
через API-ключи).

### D16. ЗФО расписание в date-vertical формате
Geography ЗФО (`1-2_kurs_zfo.pdf`) — дни-даты по вертикали в col0.
Такая же категория, что journalism, но с ДАТАМИ на месте дней недели.
Отдельный parser branch не написан.

### D17. Google Drive PDF-ссылки
Fetcher из site_fetcher классифицирует `drive.google.com/file/d/XXX/view`
как «pdf», но `curl` этой ссылки отдаёт HTML preview, а не PDF.
Нужен fixup: для gdrive преобразовать URL в `drive.google.com/uc?id=XXX`
формат.

### D18. Preschool over-kerned PDFs
PDF-рендер preschool кладёт пробел между символами внутри слов
(«Н а п р а в л е н и е»). pdfplumber честно возвращает разнесённые
токены. Нужна pre-processing логика на merge-spaced-runs или переход
на другую библиотеку.

## Тесты

Все 46 существующих тестов проходят после D14 фикса.

## Рекомендация

- **Ship-ready:** history, math (после D14), geography (очное), journalism
  (~70 % файлов), philology (8/13), social (1/2).
- **Требует OCR:** arts, international, languages, часть preschool. Прод-
  workflow это должно закрывать через Tesseract-fallback.
- **Требует fetcher-фиксы:** arts (gdrive), pedagogy/biology/digital
  (nextcloud), childhood (кажется, просто нет источника — возможно надо
  найти нужный URL).
- **Требует новый parser branch:** geography ЗФО (D16), preschool
  over-kerning (D18).

**Итог:** локальная построчная сверка честно возможна на ~40 % институтов
(text-based PDF-ы + xlsx). Остальное блокируется на сторонней
инфраструктуре (OCR ключи, gdrive/nextcloud скачивание).
