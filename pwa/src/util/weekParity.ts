/**
 * НАД чертой = нечётная неделя (`odd_week`), ПОД чертой = чётная (`even_week`).
 *
 * Чётность задаёт официальное «Расписание недель НАД / ПОД чертой», а не
 * арифметика. Оба очевидных правила неверны:
 *
 *  - **ISO-номер недели % 2** совпадает с календарём МПГУ только со второго
 *    семестра: в 2026 году 53 ISO-недели, и на переходе через Новый год
 *    чётность ISO переворачивается. Правило ошибается 18 недель подряд —
 *    весь первый семестр.
 *  - **Строгое чередование от начала года** ломается на стыке семестров:
 *    22.02–28.02 и 01.03–07.03 обе ПОД чертой.
 *
 * Поэтому здесь таблица из документа. Свежую таблицу PWA забирает из
 * `meta/week_parity.json`, встроенная — запасной вариант.
 */
export interface WeekCalendar {
  /** Понедельник первой недели таблицы, ISO-дата. */
  anchor: string;
  /** По букве на неделю: «o» = НАД чертой, «e» = ПОД чертой. */
  weeks: string;
  academic_year?: string;
  source?: string;
}

/**
 * Скан «Расписание недель НАД / ПОД чертой на 2026-2027 уч.г.»:
 * 31.08.2026–28.02.2027 — 26 недель ровного чередования с НАД,
 * 01.03.2027–11.07.2027 — 19 недель, чередование снова с ПОД.
 */
export const BUILT_IN_CALENDAR: WeekCalendar = {
  anchor: "2026-08-31",
  weeks: "oeoeoeoeoeoeoeoeoeoeoeoeoe" + "eoeoeoeoeoeoeoeoeoe",
  academic_year: "2026/2027",
};

const DAY_MS = 86_400_000;

function mondayOfUTC(utcMidnight: number): number {
  const weekday = (new Date(utcMidnight).getUTCDay() + 6) % 7; // 0 = понедельник
  return utcMidnight - weekday * DAY_MS;
}

function mondayOfDate(date: Date): number {
  return mondayOfUTC(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
}

function mondayOfISO(iso: string): number {
  const [y, m, day] = iso.split("-").map(Number);
  return mondayOfUTC(Date.UTC(y, m - 1, day));
}

/** True, если неделя этой даты — НАД чертой (нечётная). */
export function isOddWeek(date: Date, calendar: WeekCalendar = BUILT_IN_CALENDAR): boolean {
  const table = calendar.weeks ?? "";
  const index = Math.round((mondayOfDate(date) - mondayOfISO(calendar.anchor)) / (7 * DAY_MS));
  if (!table) return ((index % 2) + 2) % 2 === 0;
  if (index >= 0 && index < table.length) return table[index] === "o";
  // За пределами опубликованного года — чередование от ближайшего
  // известного края. Это догадка до выхода нового документа.
  const known = index < 0 ? table[0] : table[table.length - 1];
  const distance = index < 0 ? -index : index - (table.length - 1);
  return (known === "o") !== (distance % 2 === 1);
}

export function isEvenWeek(date: Date, calendar: WeekCalendar = BUILT_IN_CALENDAR): boolean {
  return !isOddWeek(date, calendar);
}
