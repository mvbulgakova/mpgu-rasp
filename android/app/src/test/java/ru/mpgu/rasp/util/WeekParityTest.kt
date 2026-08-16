package ru.mpgu.rasp.util

import java.time.LocalDate
import kotlin.test.Test
import kotlin.test.assertEquals

class WeekParityTest {

    @Test fun `ISO week 1 is odd`() {
        // 2026-01-01 is a Thursday, ISO week 1 of 2026
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 1, 1)))
    }

    @Test fun `ISO week 2 is even`() {
        // 2026-01-08 is Thursday of ISO week 2
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 1, 8)))
    }

    @Test fun `known monday of even week`() {
        // 2026-08-17 is Monday, ISO week 34 (even)
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 8, 17)))
    }

    @Test fun `known monday of odd week`() {
        // 2026-08-24 is Monday, ISO week 35 (odd)
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 8, 24)))
    }
}
