package ru.mpgu.rasp.util

import java.time.DayOfWeek
import java.time.LocalDate
import java.time.temporal.ChronoUnit
import java.time.temporal.TemporalAdjusters

/**
 * НАД чертой = [ODD] (`odd_week`), ПОД чертой = [EVEN] (`even_week`).
 *
 * Чётность задаёт официальное «Расписание недель НАД / ПОД чертой», а не
 * арифметика. Два очевидных правила — оба неверны:
 *
 *  * **ISO-номер недели % 2** совпадает с календарём МПГУ только со второго
 *    семестра: в 2026 году 53 ISO-недели, и на переходе через Новый год
 *    чётность ISO переворачивается. Правило ошибается 18 недель подряд.
 *  * **Строгое чередование от начала года** ломается на стыке семестров:
 *    22.02–28.02 и 01.03–07.03 обе ПОД чертой.
 *
 * Поэтому здесь таблица из документа. Свежую таблицу приложение забирает
 * из `meta/week_parity.json`, встроенная — запасной вариант.
 */
/** Таблица чётности: [weeks] — по букве на неделю от [anchor] («o»/«e»). */
data class WeekCalendar(val anchor: LocalDate, val weeks: String)

enum class WeekParity { ODD, EVEN;

    companion object {
        /**
         * Скан «Расписание недель НАД / ПОД чертой на 2026-2027 уч.г.»
         * (институт педагогики и психологии):
         * 31.08.2026–28.02.2027 — 26 недель ровного чередования с НАД,
         * 01.03.2027–11.07.2027 — 19 недель, чередование снова с ПОД.
         */
        val BUILT_IN = WeekCalendar(
            anchor = LocalDate.of(2026, 8, 31),
            weeks = "oeoeoeoeoeoeoeoeoeoeoeoeoe" + "eoeoeoeoeoeoeoeoeoe",
        )

        fun forDate(date: LocalDate, calendar: WeekCalendar = BUILT_IN): WeekParity =
            if (isOdd(date, calendar)) ODD else EVEN

        private fun isOdd(date: LocalDate, calendar: WeekCalendar): Boolean {
            val table = calendar.weeks
            val monday = date.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
            val anchorMonday =
                calendar.anchor.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
            val index = ChronoUnit.WEEKS.between(anchorMonday, monday).toInt()
            if (table.isEmpty()) return Math.floorMod(index, 2) == 0
            if (index in table.indices) return table[index] == 'o'
            // За пределами опубликованного года — чередование от ближайшего
            // известного края. Это догадка до выхода нового документа.
            val (known, distance) = if (index < 0) {
                table.first() to -index
            } else {
                table.last() to index - (table.length - 1)
            }
            return (known == 'o') != (distance % 2 == 1)
        }
    }
}
