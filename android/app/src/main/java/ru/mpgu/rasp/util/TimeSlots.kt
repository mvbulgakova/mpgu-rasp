package ru.mpgu.rasp.util

import java.time.LocalTime

object TimeSlots {
    // Matches TIME_SLOTS in scraper/normalizer/schedule_normalizer.py (lines 22-30).
    // Keep in sync — the scraper stamps `slot: N` based on these exact starts,
    // and Android/PWA/backend must all resolve to the same N for the same time.
    private val slotStarts = linkedMapOf(
        LocalTime.of(9, 0)   to 1,
        LocalTime.of(10, 40) to 2,
        LocalTime.of(12, 40) to 3,
        LocalTime.of(14, 20) to 4,
        LocalTime.of(16, 0)  to 5,
        LocalTime.of(17, 40) to 6,
        LocalTime.of(19, 20) to 7,
    )

    fun slotFromStart(time: LocalTime): Int? = slotStarts[time]

    data class LessonTimeRange(val start: LocalTime, val end: LocalTime)

    fun currentLessonIndex(lessons: List<LessonTimeRange>, now: LocalTime): Int? {
        lessons.forEachIndexed { i, r -> if (now >= r.start && now < r.end) return i }
        return null
    }
}
