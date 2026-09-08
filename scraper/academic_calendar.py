"""Чётность учебной недели МПГУ.

МПГУ печатает расписание двумя строками в одной ячейке: НАД чертой —
нечётная неделя (`odd_week`), ПОД чертой — чётная (`even_week`). Какая
календарная неделя какая — задаёт официальный документ «Расписание недель
НАД / ПОД чертой», а не арифметика.

Два правила, которые кажутся очевидными, и оба неверны:

1. **ISO-номер недели % 2.** Совпадает с календарём МПГУ только со второго
   семестра: 2026 год содержит 53 ISO-недели, поэтому на переходе через
   Новый год чётность ISO переворачивается. Правило ошибается на всём
   первом семестре — 18 недель подряд. Именно оно стояло в PWA, в Android
   и в обоих ботах.

2. **Строгое чередование от начала года.** Тоже ломается: в 2026/2027
   чередование рвётся ровно один раз, на стыке семестров — 22.02–28.02
   ПОД чертой и 01.03–07.03 снова ПОД чертой.

Поэтому здесь лежит таблица из документа, а не формула. Она же уезжает в
`meta/week_parity.json`, чтобы клиентам не требовался релиз на новый
учебный год.
"""
import datetime as dt

# Понедельник первой недели учебного года.
WEEK_PARITY_ANCHOR = dt.date(2026, 8, 31)

# Одна буква на неделю, начиная с WEEK_PARITY_ANCHOR:
# «o» = НАД чертой (odd_week), «e» = ПОД чертой (even_week).
# Источник: скан «Расписание недель НАД / ПОД чертой на 2026-2027 уч.г.»
# (институт педагогики и психологии), 2 страницы.
#
#   31.08.2026 – 28.02.2027 — 26 недель, ровное чередование с НАД
#   01.03.2027 – 11.07.2027 — 19 недель, чередование начинается СНОВА с ПОД
WEEK_PARITY_2026_2027 = (
    "oeoeoeoeoeoeoeoeoeoeoeoeoe"
    "eoeoeoeoeoeoeoeoeoe"
)

ACADEMIC_YEAR = "2026/2027"


def _week_index(day: dt.date, anchor: dt.date) -> int:
    monday = day - dt.timedelta(days=day.weekday())
    anchor_monday = anchor - dt.timedelta(days=anchor.weekday())
    return (monday - anchor_monday).days // 7


def is_odd_week(day: dt.date, anchor: dt.date = WEEK_PARITY_ANCHOR,
                table: str = WEEK_PARITY_2026_2027) -> bool:
    """True, если неделя этой даты — НАД чертой (нечётная, `odd_week`).

    За пределами таблицы (до начала года и после его конца) чётность
    достраивается чередованием от ближайшего известного края. Это
    ДОГАДКА: настоящий ответ появится только с новым документом.
    """
    index = _week_index(day, anchor)
    if not table:
        return index % 2 == 0
    if 0 <= index < len(table):
        return table[index] == "o"
    if index < 0:
        known, distance = table[0], -index
    else:
        known, distance = table[-1], index - (len(table) - 1)
    flipped = distance % 2 == 1
    return (known == "o") != flipped


def week_type(day: dt.date, anchor: dt.date = WEEK_PARITY_ANCHOR,
              table: str = WEEK_PARITY_2026_2027) -> str:
    """Ключ расписания для этой даты: `odd_week` или `even_week`."""
    return "odd_week" if is_odd_week(day, anchor, table) else "even_week"


def week_parity_doc() -> dict:
    """Содержимое `meta/week_parity.json` для data-ветки."""
    return {
        "academic_year": ACADEMIC_YEAR,
        "anchor": WEEK_PARITY_ANCHOR.isoformat(),
        # o = НАД чертой (odd_week), e = ПОД чертой (even_week)
        "weeks": WEEK_PARITY_2026_2027,
        "source": "Расписание недель НАД / ПОД чертой на 2026-2027 уч.г.",
    }
