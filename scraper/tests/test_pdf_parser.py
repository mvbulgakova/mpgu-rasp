"""PDF parser regression tests.

Focus: cell-level extraction. `_parse_timetable_cell` is the single point where
a raw multi-line cell string from pdfplumber turns into a lesson dict. Every
audit defect around subject text (D1 wrap-truncation) lives here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.parsers.pdf_parser import _parse_timetable_cell


def test_multiline_subject_wrap_is_joined_geography_style():
    """Cell whose subject wraps across 3 lines before metadata (D1 defect).

    Source PDF (geography 5-курс): «Практика устной и\\nписьменной речи\\n
    английского языка (ПЗ),\\nдоц. Ю.С. Кузин,\\nауд. 206». Old code took only
    the first line («Практика устной и»); reader had no idea what the lesson
    actually was.
    """
    cell = (
        "Практика устной и\n"
        "письменной речи\n"
        "английского языка (ПЗ),\n"
        "доц. Ю.С. Кузин,\n"
        "ауд. 206"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == (
        "Практика устной и письменной речи английского языка"
    )
    assert lesson["type"] == "practice"
    assert lesson["teacher"] == "доц. Ю.С. Кузин"
    assert lesson["room"] == "ауд. 206"


def test_multiline_subject_wrap_is_joined_physics_style():
    """Physics 1-курс defect: «Общая» instead of «Общая и неорганическая химия»."""
    cell = (
        "Общая\n"
        "и неорганическая химия\n"
        "(ПЗ)\n"
        "Асс. А.И. Ломакин\n"
        "(ауд. 55)"
    )
    lesson = _parse_timetable_cell(cell, "11:00", "12:35", None)
    assert lesson is not None
    assert lesson["subject"] == "Общая и неорганическая химия"
    assert lesson["type"] == "practice"
    assert "Ломакин" in (lesson["teacher"] or "")


def test_singleline_subject_with_inline_type_marker():
    """Single-line cell with type marker in body — unchanged behaviour."""
    cell = "Экологический мониторинг (ПЗ),\nдоц. Э.Г. Рябова,\nауд. 502"
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == "Экологический мониторинг"
    assert lesson["type"] == "practice"


def test_lecture_marker_after_wrapped_subject():
    cell = (
        "Основы российской\n"
        "государственности\n"
        "(ЛК)\n"
        "проф. Асонов Н. В\n"
        "ауд. 314"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert lesson["subject"] == "Основы российской государственности"
    assert lesson["type"] == "lecture"


def test_single_word_subject_survives():
    """A genuine one-word subject like «Психология» must NOT be flagged/dropped."""
    cell = "Психология\n(ЛК)\nдоц. Иванов И.И.\nауд. 100"
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "Психология"
    assert lesson["type"] == "lecture"


def test_empty_cell_returns_none():
    assert _parse_timetable_cell("", "09:00", "10:30", None) is None
    assert _parse_timetable_cell("   \n\n  ", "09:00", "10:30", None) is None


# ── D9: journalism "temporary" schedule with dates instead of week parity ─────


def test_journalism_full_title_teacher_and_date_line():
    """journalism cell: полные звания и дата вместо чёт/нечёт (D9).

    Раньше «Доцент П.В. Макарова» не распознавался как teacher (regex ловил
    только abbrev'ы), а «14.09» съедалось subject'ом. Проверяем правильную
    сборку.
    """
    cell = (
        "ОСНОВЫ ДЕЯТЕЛЬНОСТИ ЖУРНАЛИСТА (ЛК)\n"
        "14.09\n"
        "Доцент П.В. Макарова\n"
        "Аудитория 204"
    )
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "ОСНОВЫ ДЕЯТЕЛЬНОСТИ ЖУРНАЛИСТА"
    assert lesson["type"] == "lecture"
    assert lesson["teacher"] == "Доцент П.В. Макарова"
    assert lesson["room"] == "Аудитория 204"


def test_journalism_professor_and_multi_date():
    cell = (
        "ХУДОЖЕСТВЕННО-ПУБЛИЦИСТИЧЕСКАЯ ЖУРНАЛИСТИКА (ЛК)\n"
        "07.09, 21.09\n"
        "Профессор Т.Н. Владимирова\n"
        "Аудитория 204"
    )
    lesson = _parse_timetable_cell(cell, "09:00", "10:30", None)
    assert lesson is not None
    assert lesson["subject"] == "ХУДОЖЕСТВЕННО-ПУБЛИЦИСТИЧЕСКАЯ ЖУРНАЛИСТИКА"
    assert lesson["teacher"] == "Профессор Т.Н. Владимирова"
    assert lesson["room"] == "Аудитория 204"


def test_journalism_senior_lecturer_and_sports_hall():
    cell = (
        "ЭЛЕКТИВНЫЕ КУРСЫ ПО ФИЗИЧЕСКОЙ КУЛЬТУРЕ И СПОРТУ (ПЗ)\n"
        "10.09, 24.09\n"
        "Старший преподаватель С.С. Волхов\n"
        "Спортивный зал"
    )
    lesson = _parse_timetable_cell(cell, "10:40", "12:10", None)
    assert lesson is not None
    assert (
        lesson["subject"]
        == "ЭЛЕКТИВНЫЕ КУРСЫ ПО ФИЗИЧЕСКОЙ КУЛЬТУРЕ И СПОРТУ"
    )
    assert lesson["type"] == "practice"
    assert "Волхов" in (lesson["teacher"] or "")
    assert lesson["room"] == "Спортивный зал"
