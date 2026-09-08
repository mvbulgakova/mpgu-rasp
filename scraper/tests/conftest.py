"""Тесты не ходят в сеть. Совсем.

Поводом послужил живой инцидент: тест обратной связи вызвал бота с
`request=None`, в окружении оказался `GITHUB_TOKEN`, и вместо подменённого
транспорта вызов ушёл в настоящий GitHub API — в публичном репозитории
появился issue. Чинить такое «внимательностью в тесте» бесполезно: нужна
защита, при которой ошибка невозможна.

Поэтому на время прогона:
  * из окружения убираются токены, по которым код решает «я в проде»;
  * `urlopen` подменяется на заглушку, которая падает с внятным текстом.
"""
import urllib.request

import pytest

PROD_ENV = ("GITHUB_TOKEN", "GH_TOKEN", "BOT_TOKEN", "ANTHROPIC_API_KEY",
            "CLOUDFLARE_API_TOKEN")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    for name in PROD_ENV:
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        target = args[0] if args else "?"
        url = getattr(target, "full_url", target)
        raise AssertionError(
            f"тест попытался выйти в сеть: {url}\n"
            "Подменяйте транспорт явно (аргумент `request=` / monkeypatch), "
            "а не полагайтесь на то, что токена не окажется.")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
