package ru.mpgu.rasp.util

import java.time.LocalTime
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class TimeSlotsTest {

    @Test fun `slot 1 starts at 9 00`() {
        assertEquals(1, TimeSlots.slotFromStart(LocalTime.of(9, 0)))
    }

    @Test fun `slot 5 starts at 16 00`() {
        assertEquals(5, TimeSlots.slotFromStart(LocalTime.of(16, 0)))
    }

    @Test fun `unknown start returns null`() {
        assertNull(TimeSlots.slotFromStart(LocalTime.of(3, 33)))
    }

    @Test fun `15 20 is between slots and returns null`() {
        // 15:20 falls in the gap between slot 4 (14:20-15:50) and slot 5 (16:00-17:30)
        // relative to slot-START-only mapping. It IS inside slot 4's range for
        // currentLessonIndex, but slotFromStart is exact-start match only.
        assertNull(TimeSlots.slotFromStart(LocalTime.of(15, 20)))
    }

    @Test fun `current lesson is the one containing now`() {
        val lessons = listOf(
            fake("09:00", "10:30"),
            fake("10:40", "12:10"),
            fake("12:40", "14:10"),
        )
        assertEquals(1, TimeSlots.currentLessonIndex(lessons, LocalTime.of(11, 45)))
    }

    @Test fun `no current lesson between blocks`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("12:40", "14:10"))
        assertNull(TimeSlots.currentLessonIndex(lessons, LocalTime.of(11, 30)))
    }

    @Test fun `all seven slot starts map to their index`() {
        // Full coverage of Python TIME_SLOTS (schedule_normalizer.py:22-30) — any
        // mistranscription of a slot start would show up here even for the slots
        // not explicitly covered by other tests.
        val expected = mapOf(
            LocalTime.of(9, 0)   to 1,
            LocalTime.of(10, 40) to 2,
            LocalTime.of(12, 40) to 3,
            LocalTime.of(14, 20) to 4,
            LocalTime.of(16, 0)  to 5,
            LocalTime.of(17, 40) to 6,
            LocalTime.of(19, 20) to 7,
        )
        for ((time, slot) in expected) {
            assertEquals(slot, TimeSlots.slotFromStart(time), "slot for $time")
        }
    }

    @Test fun `currentLessonIndex includes lesson start (inclusive lower bound)`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("10:40", "12:10"))
        assertEquals(1, TimeSlots.currentLessonIndex(lessons, LocalTime.of(10, 40)))
    }

    @Test fun `currentLessonIndex excludes lesson end (exclusive upper bound)`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("10:40", "12:10"))
        assertNull(TimeSlots.currentLessonIndex(lessons, LocalTime.of(10, 30)))
    }

    private fun fake(start: String, end: String) = TimeSlots.LessonTimeRange(
        start = LocalTime.parse(start),
        end = LocalTime.parse(end),
    )
}
