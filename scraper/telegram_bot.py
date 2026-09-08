"""Telegram-бот расписания МПГУ на long-polling (для запуска в GitHub Actions).

Без внешнего хостинга и вебхуков: воркфлоу периодически запускает этот скрипт,
он опрашивает getUpdates и отвечает почти мгновенно, затем выходит; крон
перезапускает. Нужен только секрет BOT_TOKEN.

Данные берёт с публичного CDN jsDelivr (data-ветка) — ничего деплоить не надо.

**Обратная связь.** Под каждым расписанием висит кнопка «тут ошибка»: нажатие
заводит issue в этом же репозитории со всем контекстом (институт, группа,
день, чётность, версия данных, что именно показал бот). Ответ на сообщение
бота уходит комментарием в тот же issue — состояние живёт в самом сообщении
Telegram, поэтому бот остаётся stateless и переживает любой рестарт рана.

Локальный прогон логики (без Telegram и без GitHub):
    python -m scraper.telegram_bot --selftest ВОП40-ПФК2501
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import datetime as dt
from dataclasses import dataclass

from scraper.academic_calendar import is_odd_week
from scraper import feedback

DATA_BASE = os.environ.get(
    "DATA_BASE", "https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data")
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "3300"))  # ~55 минут
REPO = os.environ.get("GITHUB_REPOSITORY", "mvbulgakova/mpgu-rasp")

#: Сколько сообщений о проблемах принимаем от одного человека в час.
#: Инбокс должен оставаться читаемым; честному человеку этого с запасом.
REPORTS_PER_HOUR = 5

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_RU = {"monday": "Понедельник", "tuesday": "Вторник", "wednesday": "Среда",
          "thursday": "Четверг", "friday": "Пятница", "saturday": "Суббота",
          "sunday": "Воскресенье"}
TYPE_RU = {"lecture": "ЛК", "practice": "ПЗ", "lab": "ЛР", "seminar": "СЕМ", "other": ""}
_HOMO = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У"})

#: Номер issue в подтверждении — по нему ответ пользователя находит свой issue.
_ISSUE_REF_RE = re.compile(r"#(\d{1,7})\b")


@dataclass
class Reply:
    """Ответ бота: текст и, если есть, inline-кнопки."""

    text: str
    buttons: list[list[dict]] | None = None


def search_key(s: str) -> str:
    return re.sub(r"[\s\-_]", "", s.strip().upper().translate(_HOMO))


def _get_json(path: str):
    url = f"{DATA_BASE}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "MPGU-Schedule-Bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _esc(s) -> str:
    return (str("" if s is None else s)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _week_key(d: dt.date) -> str:
    """odd_week / even_week по календарю МПГУ, а не по ISO-номеру недели.

    ISO-правило инвертировано весь первый семестр — см.
    scraper/academic_calendar.
    """
    return "odd_week" if is_odd_week(d) else "even_week"


def _now_msk() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=3)))


# ── rate limit ───────────────────────────────────────────────────────────
# В памяти рана: переживать рестарт незачем — окно час, а ран длиннее часа.

_reports: dict[int, list[float]] = {}


def reset_rate_limit() -> None:
    _reports.clear()


def _allow_report(user_id: int | None, now=time.time) -> bool:
    if user_id is None:
        return True
    cutoff = now() - 3600
    recent = [t for t in _reports.get(user_id, []) if t > cutoff]
    _reports[user_id] = recent
    if len(recent) >= REPORTS_PER_HOUR:
        return False
    recent.append(now())
    return True


# ── расписание ───────────────────────────────────────────────────────────

#: Индекс групп меняется два раза в сутки, а `/oshibka` перебирает слова
#: сообщения — без кэша это был бы поход в CDN на каждое слово.
_GROUPS_TTL = 300
_groups_cache: tuple[float, list[dict]] | None = None


def reset_caches() -> None:
    global _groups_cache
    _groups_cache = None


def _all_groups() -> list[dict]:
    global _groups_cache
    if _groups_cache and time.time() - _groups_cache[0] < _GROUPS_TTL:
        return _groups_cache[1]
    groups = (_get_json("meta/groups.json") or {}).get("groups", [])
    _groups_cache = (time.time(), groups)
    return groups


def _find_groups(query: str) -> list[dict]:
    """Поиск по коду, направлению и профилю — как в Cloudflare-воркере.

    Студент помнит направление и профиль; код группы он подсматривает.
    """
    groups = _all_groups()
    code = search_key(query)
    plain = query.strip().lower()
    exact = [g for g in groups if g.get("key") == code]
    if exact:
        return exact
    return [g for g in groups
            if (len(code) >= 3 and code in (g.get("key") or ""))
            or plain in (g.get("direction") or "").lower()
            or plain in (g.get("profile") or "").lower()]


def _group_by_code(institute: str, code: str) -> dict | None:
    key = search_key(code)
    return next((g for g in _all_groups()
                 if g.get("institute") == institute and g.get("key") == key), None)


def _format_today(group: dict, meta: dict) -> str:
    now = _now_msk()
    day = DAYS[now.weekday()]
    wk = _week_key(now.date())
    lessons = ((group.get("schedule") or {}).get(wk) or {}).get(day) or []
    label = "нечётная · над чертой" if wk == "odd_week" else "чётная · под чертой"
    head = (f"📅 <b>{_esc(group.get('name') or meta['code'])}</b> · "
            f"{DAY_RU[day]} · {label}")
    if not lessons:
        return f"{head}\n\nЗанятий нет 🎉"
    lessons = sorted(lessons, key=lambda l: l.get("time_start") or "")
    parts = []
    for l in lessons:
        t = f" ({TYPE_RU[l['type']]})" if TYPE_RU.get(l.get("type")) else ""
        tm = f"{l.get('time_start') or ''}{'–' + l['time_end'] if l.get('time_end') else ''}"
        extra = ", ".join(_esc(x) for x in (l.get("teacher"), l.get("room")) if x)
        parts.append(f"🕐 <b>{tm}</b> {_esc(l.get('subject') or '')}{t}"
                     + (f"\n   {extra}" if extra else ""))
    return head + "\n\n" + "\n\n".join(parts)


def _report_button(meta: dict, day: str) -> list[list[dict]]:
    """callback_data режется Telegram'ом на 64 БАЙТАХ — кириллица по два."""
    data = f"fb|{meta['institute']}|{meta['code']}|{day}"
    if len(data.encode("utf-8")) > 64:
        data = f"fb|{meta['institute']}|{meta['code']}|-"
    return [[{"text": "⚠️ Тут ошибка в расписании", "callback_data": data}]]


# ── обратная связь ───────────────────────────────────────────────────────

def _github(request):
    """Транспорт к GitHub API: подставленный (тесты) или боевой по токену."""
    if request is not None:
        return request
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    return feedback.github_request(REPO, token)


_NO_TOKEN = ("Приём сообщений сейчас не настроен — напишите, пожалуйста, позже.")


def _submit(report: feedback.Report, user_id, request) -> Reply:
    gh = _github(request)
    if gh is None:
        return Reply(_NO_TOKEN)
    if not _allow_report(user_id):
        return Reply("Вы отправили слишком много сообщений за час — "
                     "остальные приму чуть позже. Спасибо, что помогаете!")
    try:
        result = feedback.submit(report, repo=REPO, request=gh)
    except Exception as e:  # noqa: BLE001 — пользователю нужен ответ, не трейс
        print(f"feedback error: {e}")
        return Reply("Не получилось записать сообщение, попробуйте позже.")
    what = "Записал" if result.created else "Добавил к уже известному"
    return Reply(
        f"{what}: обращение <b>#{result.number}</b>. Спасибо!\n\n"
        "Если хотите добавить детали — <b>ответьте на это сообщение</b>, "
        "и они попадут туда же.")


def handle_callback(data: str, user_id: int | None = None, request=None) -> Reply:
    """Нажата кнопка «тут ошибка» под расписанием."""
    parts = (data or "").split("|")
    if len(parts) != 4 or parts[0] != "fb":
        return Reply("Не понял кнопку, попробуйте ещё раз.")
    _, institute, code, day = parts
    meta = _group_by_code(institute, code)
    if meta is None:
        return Reply("Такой группы не найден — возможно, данные обновились. "
                     "Пришлите код группы заново.")
    return _submit(
        feedback.Report(institute=institute, group=meta["code"],
                        day=day if day in DAYS else None,
                        week="odd" if _week_key(_now_msk().date()) == "odd_week" else "even",
                        reporter_id=user_id),
        user_id, request)


def _handle_oshibka(text: str, user_id, request) -> Reply:
    """`/oshibka <код группы> <что не так>` — на случай, если кнопка потерялась."""
    rest = re.sub(r"^/\S+\s*", "", text).strip()
    words = rest.split()
    meta = None
    for i, word in enumerate(words):
        found = _find_groups(word)
        if len(found) == 1:
            meta = found[0]
            rest = " ".join(words[:i] + words[i + 1:]).strip()
            break
    if meta is None:
        return Reply("Чтобы это можно было починить, нужен код группы.\n"
                     "Например: <code>/oshibka ВОП40-ПФК2501 в понедельник "
                     "нет первой пары</code>")
    return _submit(
        feedback.Report(institute=meta["institute"], group=meta["code"],
                        text=rest, reporter_id=user_id),
        user_id, request)


def _handle_followup(text: str, reply_to: str, user_id, request) -> Reply | None:
    """Ответ на подтверждение бота — комментарий в тот же issue."""
    match = _ISSUE_REF_RE.search(reply_to or "")
    if not match:
        return None
    gh = _github(request)
    if gh is None:
        return Reply(_NO_TOKEN)
    if not _allow_report(user_id):
        return Reply("Слишком много сообщений за час — приму чуть позже.")
    try:
        feedback.add_comment(int(match.group(1)), text, gh)
    except Exception as e:  # noqa: BLE001
        print(f"feedback comment error: {e}")
        return Reply("Не получилось добавить, попробуйте позже.")
    return Reply(f"Спасибо, добавил к обращению <b>#{match.group(1)}</b>.")


# ── роутер ───────────────────────────────────────────────────────────────

HELP = ("👋 Бот расписания МПГУ.\n\n"
        "Пришлите <b>код группы</b> (<code>ВОП40-ПФК2501</code>), "
        "<b>направление</b> или <b>профиль</b> (<i>журналистика</i>) — "
        "покажу пары на сегодня.\n\n"
        "Заметили ошибку? Нажмите кнопку под расписанием или напишите "
        "<code>/oshibka ВОП40-ПФК2501 что не так</code>. "
        "Мы читаем каждое сообщение — расписание должно совпадать с деканатом.")


def handle(text: str, reply_to: str = "", user_id: int | None = None,
           request=None) -> Reply:
    text = (text or "").strip()
    if text.startswith("/start") or text.startswith("/help"):
        return Reply(HELP)
    if text.startswith("/oshibka") or text.startswith("/error"):
        return _handle_oshibka(text, user_id, request)

    followup = _handle_followup(text, reply_to, user_id, request)
    if followup is not None:
        return followup

    query = re.sub(r"^/\S+\s*", "", text)
    if len(query.strip()) < 3:
        return Reply("Пришлите код группы, направление или профиль "
                     "(минимум 3 символа) — например ВОП40-ПФК2501.")
    matches = _find_groups(query)
    if not matches:
        return Reply(f"Ничего не нашёл по запросу «{_esc(text)}». "
                     "Попробуйте код группы, направление или профиль.")
    if len(matches) > 1:
        lst = "\n".join(
            "• <b>{}</b> — {}".format(
                _esc(g["code"]),
                _esc(g.get("profile") or g.get("direction") or g.get("institute_short")))
            for g in matches[:12])
        more = f"\n…и ещё {len(matches) - 12}" if len(matches) > 12 else ""
        return Reply(f"Нашёл несколько групп — уточните:\n{lst}{more}")

    meta = matches[0]
    group = _get_json(f"institutes/{meta['institute']}/groups/"
                      f"{urllib.parse.quote(meta['file'])}.json")
    day = DAYS[_now_msk().weekday()]
    return Reply(_format_today(group, meta), _report_button(meta, day))


# ── транспорт Telegram ───────────────────────────────────────────────────

def _api(token: str, method: str, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _send(token: str, chat: int, reply: Reply) -> None:
    params = dict(chat_id=chat, text=reply.text, parse_mode="HTML",
                  disable_web_page_preview="true")
    if reply.buttons:
        params["reply_markup"] = json.dumps({"inline_keyboard": reply.buttons})
    _api(token, "sendMessage", **params)


def _dispatch(upd: dict) -> tuple[int, Reply] | None:
    """Одно обновление Telegram → куда и что отвечать."""
    if "callback_query" in upd:
        cq = upd["callback_query"]
        chat = ((cq.get("message") or {}).get("chat") or {}).get("id")
        user = (cq.get("from") or {}).get("id")
        if not chat:
            return None
        return chat, handle_callback(cq.get("data") or "", user_id=user)

    msg = upd.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat = (msg.get("chat") or {}).get("id")
    if not chat or not text:
        return None
    replied = ((msg.get("reply_to_message") or {}).get("text") or "")
    user = (msg.get("from") or {}).get("id")
    return chat, handle(text, reply_to=replied, user_id=user)


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        print(handle(sys.argv[2]).text)
        return 0
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN не задан — пропускаю (добавь секрет репозитория). Выход.")
        return 0
    if not os.environ.get("GITHUB_TOKEN"):
        print("⚠ GITHUB_TOKEN не задан — обратная связь будет отвечать отказом")
    deadline = time.time() + RUN_SECONDS
    offset = None
    print(f"Бот запущен на {RUN_SECONDS}s")
    while time.time() < deadline:
        try:
            resp = _api(token, "getUpdates", offset=offset or "", timeout=30,
                        allowed_updates='["message","callback_query"]')
        except Exception as e:
            print(f"getUpdates error: {e}"); time.sleep(3); continue
        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1
            if "callback_query" in upd:
                # Убираем «часики» на кнопке, даже если дальше всё упадёт.
                try:
                    _api(token, "answerCallbackQuery",
                         callback_query_id=upd["callback_query"]["id"])
                except Exception as e:
                    print(f"answerCallbackQuery error: {e}")
            try:
                routed = _dispatch(upd)
            except Exception as e:
                print(f"handle error: {e}")
                routed = None
            if routed is None:
                continue
            chat, reply = routed
            try:
                _send(token, chat, reply)
            except Exception as e:
                print(f"sendMessage error: {e}")
    print("Время вышло, выход")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
