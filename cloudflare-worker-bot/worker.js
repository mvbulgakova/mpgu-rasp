/**
 * Telegram-бот расписания МПГУ (Cloudflare Worker).
 *
 * Пользователь присылает код группы (или его часть) — бот ищет в
 * meta/groups.json, тянет расписание группы и отвечает парами на сегодня.
 *
 * Развёртывание:
 *   cd cloudflare-worker-bot && wrangler deploy
 *   wrangler secret put BOT_TOKEN          # токен от @BotFather
 *   wrangler secret put WEBHOOK_SECRET      # произвольная строка
 * Регистрация вебхука (один раз):
 *   curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<worker>.workers.dev&secret_token=<WEBHOOK_SECRET>"
 *
 * Данные берутся через прокси-воркер (DATA_BASE), который уже кэширует data-ветку.
 */

// Источник данных: публичный CDN jsDelivr отдаёт data-ветку с кэшем — никакой
// дополнительной инфраструктуры не требуется. Можно переопределить через env.DATA_BASE.
const DEFAULT_DATA_BASE = "https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data";

const DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const DAY_RU = {
  monday: "Понедельник", tuesday: "Вторник", wednesday: "Среда",
  thursday: "Четверг", friday: "Пятница", saturday: "Суббота", sunday: "Воскресенье",
};
const TYPE_RU = { lecture: "ЛК", practice: "ПЗ", lab: "ЛР", seminar: "СЕМ", other: "" };

const HOMO = { A: "А", B: "В", C: "С", E: "Е", H: "Н", K: "К", M: "М", O: "О", P: "Р", T: "Т", X: "Х", Y: "У" };
function searchKey(s) {
  return s.trim().toUpperCase().replace(/[A-Z]/g, (c) => HOMO[c] || c).replace(/[\s\-_]/g, "");
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("ok"); // health check
    if (env.WEBHOOK_SECRET &&
        request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }
    let update;
    try { update = await request.json(); } catch { return new Response("ok"); }

    const msg = update.message || update.edited_message;
    const text = (msg && msg.text || "").trim();
    const chatId = msg && msg.chat && msg.chat.id;
    if (!chatId || !text) return new Response("ok");

    try {
      const reply = await handle(text, env.DATA_BASE || DEFAULT_DATA_BASE);
      await send(env, chatId, reply);
    } catch (e) {
      await send(env, chatId, "Что-то пошло не так. Попробуйте позже.");
    }
    return new Response("ok");
  },
};

async function handle(text, base) {
  if (text.startsWith("/start") || text.startsWith("/help")) {
    return "👋 Бот расписания МПГУ.\n\nПришлите код группы (<b>ВОП40-ПФК2501</b>), " +
      "направление или профиль (<b>журналистика</b>) — и я покажу пары на сегодня.";
  }
  const raw = text.replace(/^\/\S+\s*/, "").trim();
  const q = searchKey(raw);
  if (q.length < 3) return "Пришлите код группы, направление или профиль (минимум 3 символа) — например ВОП40-ПФК2501 или «журналистика».";

  const index = await getJson(`${base}/meta/groups.json`);
  const all = (index.groups || []);
  const exact = all.filter((g) => g.key === q);
  // Студент чаще помнит направление и профиль, чем код группы, — ищем и по ним.
  const plain = raw.toLowerCase();
  const matches = exact.length
    ? exact
    : all.filter((g) =>
        g.key.includes(q) ||
        (g.direction || "").toLowerCase().includes(plain) ||
        (g.profile || "").toLowerCase().includes(plain));

  if (matches.length === 0) return `Ничего не нашёл по запросу «${escapeHtml(text)}». Попробуйте код группы, направление или профиль.`;
  if (matches.length > 1 && exact.length !== 1) {
    const list = matches.slice(0, 12).map((g) => {
      const where = [g.profile || g.direction, g.institute_short].filter(Boolean).map(escapeHtml).join(" — ");
      return `• <b>${escapeHtml(g.code)}</b> — ${where}`;
    }).join("\n");
    const more = matches.length > 12 ? `\n…и ещё ${matches.length - 12}` : "";
    return `Нашёл несколько групп — уточните:\n${list}${more}`;
  }

  const g = matches[0];
  const group = await getJson(`${base}/institutes/${g.institute}/groups/${encodeURIComponent(g.file)}.json`);
  // Календарь НАД/ПОД чертой публикуется вместе с данными: новый учебный
  // год не требует передеплоя воркера.
  const calendar = await getJson(`${base}/meta/week_parity.json`)
    .catch(() => BUILT_IN_WEEK_CALENDAR);
  return formatToday(group, g, calendar);
}

async function getJson(url) {
  const r = await fetch(url, { headers: { "User-Agent": "MPGU-Schedule-Bot" } });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// НАД чертой = нечётная неделя (odd_week), ПОД чертой = чётная (even_week).
// Чётность задаёт официальный документ «Расписание недель НАД / ПОД чертой»,
// а не арифметика: ISO-номер недели инвертирован весь первый семестр (2026
// год содержит 53 ISO-недели), а строгое чередование рвётся на стыке
// семестров — 22.02–28.02 и 01.03–07.03 обе ПОД чертой.
// Свежая таблица лежит в meta/week_parity.json; эта — запасная.
const BUILT_IN_WEEK_CALENDAR = {
  anchor: "2026-08-31",
  weeks: "oeoeoeoeoeoeoeoeoeoeoeoeoe" + "eoeoeoeoeoeoeoeoeoe",
};
const DAY_MS = 86400000;

function mondayOf(utcMidnight) {
  const weekday = (new Date(utcMidnight).getUTCDay() + 6) % 7; // 0 = понедельник
  return utcMidnight - weekday * DAY_MS;
}

function isEvenWeek(date, calendar = BUILT_IN_WEEK_CALENDAR) {
  const table = calendar.weeks || "";
  const [y, m, d] = calendar.anchor.split("-").map(Number);
  const anchorMonday = mondayOf(Date.UTC(y, m - 1, d));
  const monday = mondayOf(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const index = Math.round((monday - anchorMonday) / (7 * DAY_MS));
  if (!table) return (((index % 2) + 2) % 2) !== 0;
  if (index >= 0 && index < table.length) return table[index] !== "o";
  // За пределами опубликованного года — чередование от известного края.
  const known = index < 0 ? table[0] : table[table.length - 1];
  const distance = index < 0 ? -index : index - (table.length - 1);
  return !((known === "o") !== (distance % 2 === 1));
}

function formatToday(group, meta, calendar = BUILT_IN_WEEK_CALENDAR) {
  // Москва = UTC+3
  const now = new Date(Date.now() + 3 * 3600 * 1000);
  const day = DAYS[now.getUTCDay()];
  const even = isEvenWeek(now, calendar);
  const wk = even ? "even_week" : "odd_week";
  const lessons = ((group.schedule || {})[wk] || {})[day] || [];
  const header = `📅 <b>${escapeHtml(group.name || meta.code)}</b> · ${DAY_RU[day]} · ${even ? "под чертой" : "над чертой"}`;
  if (!lessons.length) return `${header}\n\nЗанятий нет 🎉`;
  const body = lessons
    .sort((a, b) => (a.time_start || "").localeCompare(b.time_start || ""))
    .map((l) => {
      const t = TYPE_RU[l.type] ? ` (${TYPE_RU[l.type]})` : "";
      const time = `${l.time_start || ""}${l.time_end ? "–" + l.time_end : ""}`;
      const extra = [l.teacher, l.room].filter(Boolean).map(escapeHtml).join(", ");
      return `🕐 <b>${time}</b> ${escapeHtml(l.subject || "")}${t}${extra ? "\n   " + extra : ""}`;
    })
    .join("\n\n");
  return `${header}\n\n${body}`;
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function send(env, chatId, text) {
  await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
}
