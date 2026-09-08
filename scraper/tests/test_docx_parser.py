"""DOCX parser tests.

D36: журналистика публикует обычную MPGU-сетку (день / время / колонки-групп)
в .docx, но парсер знал только «дни-колонками» и «плоский» форматы, поэтому
возвращал 0 групп на 37 файлах.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.parsers.docx_parser import _parse_mpgu_grid, _collapse_merged


def _journalism_docx_rows():
    """Как python-docx отдаёт journalism/226: объединённые ячейки
    ПОВТОРЯЮТСЯ в каждой колонке своего диапазона, время — с en-dash."""
    return [
        ["Код, наименование направления/", "Код, наименование направления/",
         "42.03.02 ЖУРНАЛИСТИКА", "42.03.02 ЖУРНАЛИСТИКА"],
        ["День недели", "  Группа \n Время", "БОЖ09-ЖРН2101\nГр. 101",
         "БОЖ09-ЖРН2102\nГр. 102"],
        ["ПОНЕДЕЛЬНИК", "09:00 – 10:30",
         "ИНТЕРНЕТ-ЖУРНАЛИСТИКА (ПЗ)\nСт. преп. А.А. Мостовая\nауд. 204", ""],
        ["ПОНЕДЕЛЬНИК", "10:40 – 12:10",
         "ИСТОРИЯ (ЛК)\nдоц. И.И. Иванов\nауд. 205",
         "ИСТОРИЯ (ЛК)\nдоц. И.И. Иванов\nауд. 205"],
    ]


def test_collapse_merged_blanks_repeated_span_cells():
    """Повтор текста объединённой ячейки в соседних колонках гасится —
    применяется ТОЛЬКО к строкам с кодами групп (в строках занятий такой
    повтор означает, что пара общая для нескольких групп)."""
    row = ["A", "A", "B", "B", "B", "C"]
    assert _collapse_merged(row) == ["A", "", "B", "", "", "C"]
    # Одинаковый текст в НЕсоседних колонках не трогаем
    assert _collapse_merged(["A", "B", "A"]) == ["A", "B", "A"]


def test_mpgu_grid_in_docx_is_parsed():
    groups = _parse_mpgu_grid(_journalism_docx_rows())
    names = sorted(g["name"] for g in groups)
    assert names == ["БОЖ09-ЖРН2101", "БОЖ09-ЖРН2102"], names

    by = {g["name"]: g["schedule"]["odd_week"]["monday"] for g in groups}
    g1 = {l["time_start"]: l["subject"] for l in by["БОЖ09-ЖРН2101"]}
    assert g1.get("09:00") == "ИНТЕРНЕТ-ЖУРНАЛИСТИКА", g1
    assert g1.get("10:40") == "ИСТОРИЯ", g1
    # У второй группы в 09:00 пары нет
    g2 = {l["time_start"]: l["subject"] for l in by["БОЖ09-ЖРН2102"]}
    assert "09:00" not in g2, g2
    assert g2.get("10:40") == "ИСТОРИЯ", g2
