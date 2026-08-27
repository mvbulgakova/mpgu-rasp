"""Excel parser regression tests.

Focus: `_strip_to_code` — the module-level helper responsible for D10
(«ВОИ18-ИПЛ2601 (101)» → «ВОИ18-ИПЛ2601»).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.parsers.excel_parser import _strip_to_code, _CODE_RE


def test_strip_to_code_removes_trailing_room_number_suffix():
    """D10 audit case: xlsx headers like 'ВОИ18-ИПЛ2601 (101)' — «(101)» is
    the assigned classroom, not part of the code."""
    assert _strip_to_code("ВОИ18-ИПЛ2601 (101)") == "ВОИ18-ИПЛ2601"
    assert _strip_to_code("ВОИ34-ИОВ2603 (302А)") == "ВОИ34-ИОВ2603"


def test_strip_to_code_leaves_bare_code_intact():
    assert _strip_to_code("ВОИ18-ИПЛ2601") == "ВОИ18-ИПЛ2601"


def test_strip_to_code_returns_input_stripped_when_no_code_found():
    assert _strip_to_code("  какой-то текст без кода  ") == "какой-то текст без кода"


def test_code_regex_matches_common_mpgu_shapes():
    assert _CODE_RE.search("ВОИ18-ИПЛ2601")
    assert _CODE_RE.search("БОП40-ПФК2501")
    assert _CODE_RE.search("МОГ18-ГЕО2601")
    assert _CODE_RE.search("something ВОФ34-ФПТ2501 else")
    # Doesn't match plain words
    assert not _CODE_RE.search("hello world")
    assert not _CODE_RE.search("2601")


# ── D31: инлайновая ячейка в многострочной ячейке excel ──────────────────────


def test_inline_split_runs_on_every_line_not_just_single_line_cells():
    """D31: тот же дефект, что D13 в pdf_parser — разбиение стояло под
    `len(lines) == 1`, поэтому в многострочной ячейке (а таких в history
    большинство) преподаватель и аудитория оставались внутри названия.
    """
    from scraper.parsers.excel_parser import _parse_lesson_cell

    cell = (
        "Историография истории России, доц. Сергованцев Д.Н. (ауд. 313)\n"
        "09.09, 23.09"
    )
    lesson = _parse_lesson_cell(cell, "09:00", "10:30")
    assert lesson is not None
    assert lesson["subject"] == "Историография истории России", lesson["subject"]
    assert "Сергованцев" in (lesson["teacher"] or ""), lesson["teacher"]
    assert lesson["room"] == "313", lesson["room"]


def test_multirow_path_uses_the_same_markers():
    """D38: `_parse_multirow_lines` (ветка ЗФО/многострочных данных) несла
    старые regex: не знала «ст. пр.» и требовала, чтобы строка НАЧИНАЛАСЬ
    с «ауд.». Из-за этого преподаватель и аудитория оставались в названии.
    """
    from scraper.parsers.excel_parser import _parse_multirow_lines

    lesson = _parse_multirow_lines(
        ["Методы математической обработки данных, ст. пр. Истомина Е.И. (ауд. 324) до 06.11"],
        "09:00", "10:30",
    )
    assert lesson is not None
    assert lesson["subject"] == "Методы математической обработки данных", lesson["subject"]
    assert "Истомина" in (lesson["teacher"] or ""), lesson["teacher"]
    assert lesson["room"] == "324", lesson["room"]

    lesson2 = _parse_multirow_lines(
        ["РЦОС*", "ст. пр. Тарабукин И.М. (ауд. 322)"], "09:00", "10:30")
    assert lesson2 is not None
    assert lesson2["subject"] == "РЦОС*", lesson2["subject"]
    assert "Тарабукин" in (lesson2["teacher"] or "")


def test_direction_and_profile_from_excel_header():
    """Excel-сетка истории несёт направление и профиль в шапке по колонкам.

    NB: в источнике опечатка «наименвание» — экстрактор обязан её переживать.
    """
    from scraper.parsers.excel_parser import _try_mpgu_format

    rows = [
        ["", "Код, наименвание направления:", "", "46.03.01 История", "",
         "44.03.01 Педагогическое образование", ""],
        ["", "Направленность (профиль)", "", "Историческая политология", "",
         "История и Обществознание", ""],
        ["", "День недели", "Группа / Время", "ВОИ18-ИПЛ2601 (101)",
         "ВОИ18-ИПЛ2602 (102)", "ВОИ34-ИОВ2603 (103)", ""],
        ["", "Понедельник", "09.00-10.30",
         "Иностранный язык (ПЗ)\nдоц. Кандаурова О.И.\nауд. 311",
         "Физическая культура (ПЗ)\nдоц. Петров П.П.\nауд. 12",
         "История России (ЛК)\nпроф. Сидоров С.С.\nауд. 305", ""],
    ]
    groups = {g["name"]: g for g in _try_mpgu_format(rows)}
    assert set(groups) >= {"ВОИ18-ИПЛ2601", "ВОИ18-ИПЛ2602", "ВОИ34-ИОВ2603"}, list(groups)

    assert groups["ВОИ18-ИПЛ2601"]["direction"] == "46.03.01 История"
    assert groups["ВОИ18-ИПЛ2601"]["profile"] == "Историческая политология"
    # Объединённая ячейка направления накрывает и вторую колонку.
    assert groups["ВОИ18-ИПЛ2602"]["direction"] == "46.03.01 История"
    assert groups["ВОИ34-ИОВ2603"]["direction"] == "44.03.01 Педагогическое образование"
    assert groups["ВОИ34-ИОВ2603"]["profile"] == "История и Обществознание"
