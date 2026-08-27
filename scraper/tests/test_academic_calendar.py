"""Чётность недели МПГУ привязана к календарю, а не к ISO-номеру недели.

Эталон — официальное «Расписание недель НАД / ПОД чертой на 2026-2027 уч.г.»
(скан, институт педагогики и психологии). Учебный год начинается неделей
31.08.2026 — она НАД чертой, дальше строгое чередование до 11.07.2027.
"""
import datetime as dt

import pytest

from scraper.academic_calendar import (
    WEEK_PARITY_2026_2027, WEEK_PARITY_ANCHOR, is_odd_week, week_type,
)


@pytest.mark.parametrize("day,odd", [
    # ── страница 1 скана ──
    (dt.date(2026, 8, 31), True),    # 31.08–06.09  НАД
    (dt.date(2026, 9, 6), True),     # воскресенье той же недели
    (dt.date(2026, 9, 7), False),    # 07.09–13.09  ПОД
    (dt.date(2026, 9, 14), True),    # 14.09–20.09  НАД
    (dt.date(2026, 10, 26), True),   # 26.10–01.11  НАД
    (dt.date(2026, 12, 21), True),   # 21.12–27.12  НАД
    (dt.date(2026, 12, 28), False),  # 28.12–03.01  ПОД
    (dt.date(2027, 1, 4), True),     # 04.01–10.01  НАД
    (dt.date(2027, 2, 22), False),   # 22.02–28.02  ПОД
    # ── страница 2 скана ──
    (dt.date(2027, 3, 1), False),    # 01.03–07.03  ПОД
    (dt.date(2027, 3, 8), True),     # 08.03–14.03  НАД
    (dt.date(2027, 5, 31), True),    # 31.05–06.06  НАД
    (dt.date(2027, 6, 28), True),    # 28.06–04.07  НАД
    (dt.date(2027, 7, 5), False),    # 05.07–11.07  ПОД — последняя строка
])
def test_parity_matches_the_official_calendar(day, odd):
    assert is_odd_week(day) is odd, day


def test_iso_week_number_would_have_been_wrong_all_autumn():
    """Регрессия: старое правило «ISO-номер % 2» инвертировано весь 1 семестр.

    14.09.2026 — ISO-неделя 38 (чётная), но по календарю МПГУ это НАД
    чертой, то есть нечётная. Именно это правило стояло в PWA, Android
    и в боте.
    """
    day = dt.date(2026, 9, 14)
    assert day.isocalendar()[1] % 2 == 0     # ISO говорит «чётная»
    assert is_odd_week(day) is True          # МПГУ говорит «НАД чертой»


def test_alternation_breaks_once_between_the_semesters():
    """22.02–28.02 и 01.03–07.03 — ОБЕ ПОД чертой. Так в документе.

    Именно поэтому чётность лежит таблицей, а не считается формулой
    «чередование от начала года».
    """
    assert is_odd_week(dt.date(2027, 2, 22)) is False
    assert is_odd_week(dt.date(2027, 3, 1)) is False


def test_table_covers_the_whole_published_year():
    # 31.08.2026 – 11.07.2027 включительно.
    assert len(WEEK_PARITY_2026_2027) == 45
    last_monday = WEEK_PARITY_ANCHOR + dt.timedelta(weeks=44)
    assert last_monday == dt.date(2027, 7, 5)


def test_outside_the_table_parity_falls_back_to_alternation():
    """До и после опубликованного года — чередование от известного края."""
    assert is_odd_week(WEEK_PARITY_ANCHOR - dt.timedelta(days=7)) is False
    assert is_odd_week(WEEK_PARITY_ANCHOR - dt.timedelta(days=14)) is True
    # Последняя неделя таблицы ПОД чертой → следующая НАД.
    assert is_odd_week(dt.date(2027, 7, 12)) is True


def test_week_type_returns_the_schedule_key():
    assert week_type(dt.date(2026, 8, 31)) == "odd_week"
    assert week_type(dt.date(2026, 9, 7)) == "even_week"
