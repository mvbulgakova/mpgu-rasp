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
