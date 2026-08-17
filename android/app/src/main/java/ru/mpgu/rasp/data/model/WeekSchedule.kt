package ru.mpgu.rasp.data.model

/** Both weeks of a group's schedule. Days are Monday..Sunday keyed by DayOfWeek. */
data class WeekSchedule(
    val oddWeek: Map<java.time.DayOfWeek, List<Lesson>>,
    val evenWeek: Map<java.time.DayOfWeek, List<Lesson>>,
)
