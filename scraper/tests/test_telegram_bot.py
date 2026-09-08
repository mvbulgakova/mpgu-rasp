"""Поведение бота: поиск и обратная связь.

Сеть не трогаем — данные и GitHub API подменяются.
"""
import datetime as dt

import pytest

from scraper import telegram_bot as bot

GROUPS = {"groups": [
    {"code": "БОЖ09-ЖРН2101", "key": "БОЖ09ЖРН2101", "institute": "journalism",
     "institute_short": "ИЖиМК", "file": "БОЖ09-ЖРН2101",
     "direction": "42.03.02 ЖУРНАЛИСТИКА", "profile": "Телевидение"},
    {"code": "БОЖ09-МХК2101", "key": "БОЖ09МХК2101", "institute": "journalism",
     "institute_short": "ИЖиМК", "file": "БОЖ09-МХК2101",
     "direction": "44.03.01 ПЕДАГОГИЧЕСКОЕ ОБРАЗОВАНИЕ", "profile": "МХК"},
    {"code": "ВОП40-ПФК2501", "key": "ВОП40ПФК2501", "institute": "pedagogy",
     "institute_short": "ИПиП", "file": "ВОП40-ПФК2501",
     "direction": "44.03.02 Психолого-педагогическое образование",
     "profile": "Профессиональное консультирование"},
]}

SCHEDULE = {"name": "БОЖ09-ЖРН2101", "schedule": {
    "odd_week": {"monday": [{"time_start": "10:40", "time_end": "12:10",
                             "subject": "История", "type": "lecture",
                             "teacher": "доц. И.И. Иванов", "room": "204"}]},
    "even_week": {"monday": []},
}}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fake_get(path):
        if path.endswith("groups.json"):
            return GROUPS
        return SCHEDULE
    monkeypatch.setattr(bot, "_get_json", fake_get)
    # Часы замораживаем: тест, который проходит только по понедельникам, —
    # это не тест. 31.08.2026 — понедельник недели НАД чертой.
    monkeypatch.setattr(bot, "_now_msk", lambda: dt.datetime(
        2026, 8, 31, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=3))))
    bot.reset_rate_limit()
    bot.reset_caches()


class FakeGitHub:
    def __init__(self):
        self.calls = []

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET":
            return []
        if path == "/issues":
            return {"number": 17, "html_url": "https://github.com/o/r/issues/17"}
        return {"id": 1}


# ── поиск ────────────────────────────────────────────────────────────────

def test_search_by_direction_matches_the_worker():
    """Бот на Actions и воркер на Cloudflare обязаны отвечать одинаково."""
    reply = bot.handle("журналистика")
    assert "БОЖ09-ЖРН2101" in reply.text


def test_search_by_profile():
    reply = bot.handle("телевидение")
    assert "БОЖ09-ЖРН2101" in reply.text


def test_search_by_code_still_works():
    reply = bot.handle("БОЖ09-ЖРН2101")
    assert "История" in reply.text
    assert "над чертой" in reply.text, "неделя должна называться словами из расписания"


def test_a_resolved_group_carries_a_report_button():
    """Кнопка «тут ошибка» должна быть там, где ошибку и видно."""
    reply = bot.handle("БОЖ09-ЖРН2101")
    assert reply.buttons, "под расписанием нет кнопки обратной связи"
    data = reply.buttons[0][0]["callback_data"]
    assert data.startswith("fb|")
    assert len(data.encode("utf-8")) <= 64, "Telegram режет callback_data на 64 байтах"


def test_ambiguous_search_has_no_report_button():
    reply = bot.handle("БОЖ09")
    assert reply.buttons is None


# ── обратная связь ───────────────────────────────────────────────────────

def test_button_press_opens_an_issue_and_tells_the_user_its_number():
    gh = FakeGitHub()
    reply = bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                                user_id=1, request=gh)
    assert ("POST", "/issues") == gh.calls[-1][:2]
    assert "#17" in reply.text, "номер нужен, чтобы к нему можно было ответить"


def test_replying_to_the_ack_adds_a_comment_instead_of_a_new_issue():
    """Состояние живёт в самом сообщении Telegram — бот остаётся stateless."""
    gh = FakeGitHub()
    ack = bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                              user_id=1, request=gh).text
    gh.calls.clear()

    reply = bot.handle("на самом деле пара в 12:40", reply_to=ack,
                       user_id=1, request=gh)

    assert gh.calls, "комментарий не отправлен"
    method, path, payload = gh.calls[-1]
    assert (method, path) == ("POST", "/issues/17/comments")
    assert "12:40" in payload["body"]
    assert "спасибо" in reply.text.lower()


def test_oshibka_command_with_a_group_code():
    gh = FakeGitHub()
    reply = bot.handle("/oshibka БОЖ09-ЖРН2101 в понедельник нет первой пары",
                       user_id=1, request=gh)
    method, path, payload = gh.calls[-1]
    assert (method, path) == ("POST", "/issues")
    assert "БОЖ09-ЖРН2101" in payload["title"]
    assert "нет первой пары" in payload["body"]
    assert "#17" in reply.text


def test_oshibka_without_a_group_asks_for_one_and_writes_nothing():
    gh = FakeGitHub()
    reply = bot.handle("/oshibka всё сломалось", user_id=1, request=gh)
    assert not gh.calls, "нельзя заводить issue без группы — его некому чинить"
    assert "код группы" in reply.text.lower()


def test_rate_limit_stops_a_flood_but_says_so():
    gh = FakeGitHub()
    for _ in range(bot.REPORTS_PER_HOUR):
        bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                            user_id=7, request=gh)
    before = len(gh.calls)

    reply = bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                                user_id=7, request=gh)

    assert len(gh.calls) == before, "лимит не сработал"
    assert "слишком" in reply.text.lower()


def test_rate_limit_is_per_user():
    gh = FakeGitHub()
    for _ in range(bot.REPORTS_PER_HOUR):
        bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                            user_id=7, request=gh)
    before = len(gh.calls)
    bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                        user_id=8, request=gh)
    assert len(gh.calls) > before, "чужой лимит не должен затыкать другого"


def test_feedback_degrades_politely_without_a_token():
    """Токена нет (локальный прогон) — бот не молчит и не падает."""
    reply = bot.handle_callback("fb|journalism|БОЖ09-ЖРН2101|monday",
                                user_id=1, request=None)
    assert reply.text
    assert "не настроен" in reply.text.lower() or "позже" in reply.text.lower()


def test_callback_for_an_unknown_group_is_refused():
    gh = FakeGitHub()
    reply = bot.handle_callback("fb|journalism|НЕТ-ТАКОЙ0000|monday",
                                user_id=1, request=gh)
    assert not gh.calls
    assert "не наш" in reply.text.lower() or "не найден" in reply.text.lower()


# ── запуск: почему «бот не реагирует» должно быть видно из лога ───────────

class FakeTelegram:
    """Подменяет вызовы Telegram API."""

    def __init__(self, webhook_url="", me=None, fail=None):
        self.webhook_url = webhook_url
        self.me = me or {"ok": True, "result": {"username": "mpgu_rasp_bot"}}
        self.fail = fail
        self.calls = []

    def __call__(self, token, method, **params):
        self.calls.append(method)
        if self.fail and method in self.fail:
            raise self.fail[method]
        if method == "getMe":
            return self.me
        if method == "getWebhookInfo":
            return {"ok": True, "result": {"url": self.webhook_url}}
        if method == "deleteWebhook":
            self.webhook_url = ""
            return {"ok": True}
        raise AssertionError(method)


def test_preflight_names_the_bot_it_actually_started_as():
    """В логе должно быть видно, КАКОЙ бот запущен, а не просто «запущен»."""
    tg = FakeTelegram()
    ok, note = bot.preflight("token", api=tg)
    assert ok is True
    assert "mpgu_rasp_bot" in note


def test_preflight_removes_a_conflicting_webhook():
    """Вебхук и long-polling взаимно исключают друг друга.

    Если на боте висит вебхук, getUpdates отдаёт 409 и бот молчит вечно.
    Раз этот воркфлоу владеет токеном — он и снимает вебхук.
    """
    tg = FakeTelegram(webhook_url="https://worker.example/tg")
    ok, note = bot.preflight("token", api=tg)
    assert ok is True
    assert "deleteWebhook" in tg.calls
    assert "вебхук" in note.lower()


def test_preflight_reports_a_bad_token_instead_of_polling_into_the_void():
    tg = FakeTelegram(fail={"getMe": RuntimeError("401 Unauthorized")})
    ok, note = bot.preflight("token", api=tg)
    assert ok is False
    assert "401" in note or "токен" in note.lower()


def test_missing_token_is_reported_as_an_error_not_a_quiet_success():
    """Зелёный ран без токена — ложь: она и породила «бот не реагирует»."""
    assert "::error::" in bot.NO_TOKEN_MESSAGE
    assert "BOT_TOKEN" in bot.NO_TOKEN_MESSAGE
