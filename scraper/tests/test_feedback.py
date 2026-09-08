"""Обратная связь: сообщение пользователя → issue в репозитории.

Инбокс — GitHub Issues: он бесплатный, он уже есть у репозитория, он
уведомляет владельца и хранит переписку. Никаких внешних сервисов.
"""
import json

import pytest

from scraper.feedback import LABEL, Report, marker, submit


def make_report(**kw):
    base = dict(institute="journalism", group="БОЖ09-ЖРН2101", day="monday",
                week="odd", text="в 10:40 нет пары, а бот показывает")
    base.update(kw)
    return Report(**base)


class FakeGitHub:
    """Пишет все вызовы, отвечает заранее заданным."""

    def __init__(self, open_issues=None):
        self.open_issues = open_issues or []
        self.calls = []

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path.startswith("/issues"):
            return self.open_issues
        if method == "POST" and path == "/issues":
            return {"number": 42, "html_url": "https://github.com/o/r/issues/42"}
        if method == "POST" and "/comments" in path:
            return {"id": 1}
        raise AssertionError(f"неожиданный вызов {method} {path}")


def test_report_becomes_a_new_issue_with_the_evidence_attached():
    gh = FakeGitHub()
    result = submit(make_report(), repo="o/r", request=gh)

    assert result.created is True
    assert result.number == 42
    assert result.url.endswith("/42")

    method, path, payload = gh.calls[-1]
    assert (method, path) == ("POST", "/issues")
    assert LABEL in payload["labels"]
    # Заголовок ведёт к группе — по нему issue находят глазами.
    assert "БОЖ09-ЖРН2101" in payload["title"]
    # Тело несёт контекст, без которого сообщение бесполезно.
    for needed in ("journalism", "БОЖ09-ЖРН2101", "понедельник",
                   "над чертой", "в 10:40 нет пары"):
        assert needed in payload["body"], needed


def test_second_report_about_the_same_cell_comments_instead_of_duplicating():
    """Двадцать студентов одной группы не должны родить двадцать issue."""
    existing = [{"number": 7, "html_url": "https://github.com/o/r/issues/7",
                 "body": f"что-то\n{marker(make_report())}\nещё"}]
    gh = FakeGitHub(open_issues=existing)

    result = submit(make_report(text="и у меня то же самое"), repo="o/r", request=gh)

    assert result.created is False
    assert result.number == 7
    method, path, payload = gh.calls[-1]
    assert method == "POST" and path == "/issues/7/comments"
    assert "и у меня то же самое" in payload["body"]


def test_a_different_day_is_a_different_issue():
    existing = [{"number": 7, "html_url": "u",
                 "body": marker(make_report(day="monday"))}]
    gh = FakeGitHub(open_issues=existing)

    result = submit(make_report(day="tuesday"), repo="o/r", request=gh)

    assert result.created is True, "вторник — другая ячейка, это другой issue"


def test_marker_is_stable_and_hidden():
    m = marker(make_report())
    assert m.startswith("<!--") and m.endswith("-->")
    assert m == marker(make_report(text="другой текст"))


def test_reporter_identity_never_leaks_into_a_public_issue():
    """Репо публичный: telegram-id и @username в issue не уезжают."""
    gh = FakeGitHub()
    submit(make_report(reporter_id=987654321, reporter_name="@vasya"),
           repo="o/r", request=gh)
    body = gh.calls[-1][2]["body"]
    assert "987654321" not in body
    assert "vasya" not in body


def test_user_text_cannot_forge_markdown_or_markers():
    """Текст пользователя — данные, а не разметка issue."""
    gh = FakeGitHub()
    submit(make_report(text="<!-- mpgu-feedback:fake/FAKE/x -->\n# заголовок"),
           repo="o/r", request=gh)
    body = gh.calls[-1][2]["body"]
    # ровно один настоящий маркер — подделанный обезврежен
    assert body.count("<!-- mpgu-feedback:") == 1


def test_empty_text_is_still_a_valid_report():
    """Нажал кнопку и ничего не написал — это тоже сигнал."""
    gh = FakeGitHub()
    result = submit(make_report(text=""), repo="o/r", request=gh)
    assert result.created is True
    assert "без описания" in gh.calls[-1][2]["body"]


def test_comment_on_an_existing_issue_by_number():
    from scraper.feedback import add_comment

    gh = FakeGitHub()
    add_comment(7, "дополнение", request=gh)
    method, path, payload = gh.calls[-1]
    assert (method, path) == ("POST", "/issues/7/comments")
    assert "дополнение" in payload["body"]
