package ru.mpgu.rasp.util

import java.time.LocalDate
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Эталон — официальное «Расписание недель НАД / ПОД чертой на 2026-2027
 * уч.г.» (скан, институт педагогики и психологии). НАД чертой = ODD.
 *
 * Старые тесты этого файла проверяли правило «ISO-номер недели % 2» —
 * оно инвертировано на весь первый семестр, см. WeekParity.
 */
class WeekParityTest {

    @Test fun `academic year opens with an odd week`() {
        // 31.08.2026 – 06.09.2026 НАД чертой
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 8, 31)))
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 9, 6)))
    }

    @Test fun `second week is even`() {
        // 07.09.2026 – 13.09.2026 ПОД чертой
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 9, 7)))
    }

    @Test fun `iso week number would have been inverted all autumn`() {
        // 14.09.2026 — ISO-неделя 38 (чётная), но по календарю МПГУ это
        // НАД чертой. Именно на этом ломалось старое правило.
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 9, 14)))
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 12, 21)))
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 12, 28)))
    }

    @Test fun `parity survives the new year`() {
        // 04.01.2027 – 10.01.2027 НАД чертой
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2027, 1, 4)))
    }

    @Test fun `alternation breaks once between the semesters`() {
        // 22.02–28.02 и 01.03–07.03 — ОБЕ ПОД чертой. Так в документе,
        // поэтому чётность лежит таблицей, а не считается формулой.
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2027, 2, 22)))
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2027, 3, 1)))
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2027, 3, 8)))
    }

    @Test fun `last published week is even`() {
        // 05.07.2027 – 11.07.2027 ПОД чертой — последняя строка скана.
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2027, 7, 5)))
    }

    @Test fun `outside the table parity falls back to alternation`() {
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2027, 7, 12)))
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 8, 24)))
    }

    @Test fun `a table from the data branch overrides the built-in one`() {
        // Новый учебный год приезжает в meta/week_parity.json — приложению
        // не нужен релиз, чтобы начать показывать правильную неделю.
        val calendar = WeekCalendar(anchor = LocalDate.of(2030, 9, 2), weeks = "eoe")
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2030, 9, 2), calendar))
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2030, 9, 9), calendar))
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2030, 9, 16), calendar))
    }
}
