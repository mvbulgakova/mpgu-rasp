package ru.mpgu.rasp.data.remote

import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.model.Lesson
import ru.mpgu.rasp.data.model.WeekSchedule
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.dto.IndexInstituteDto
import ru.mpgu.rasp.data.remote.dto.LessonDto
import ru.mpgu.rasp.data.remote.dto.WeekMapDto
import java.time.DayOfWeek

private val DAY_MAP = mapOf(
    "monday" to DayOfWeek.MONDAY,
    "tuesday" to DayOfWeek.TUESDAY,
    "wednesday" to DayOfWeek.WEDNESDAY,
    "thursday" to DayOfWeek.THURSDAY,
    "friday" to DayOfWeek.FRIDAY,
    "saturday" to DayOfWeek.SATURDAY,
    "sunday" to DayOfWeek.SUNDAY,
)

fun IndexInstituteDto.toDomain(): Institute = Institute(
    id = id, name = name, shortName = short_name,
    groupsCount = groups_count, updatedAt = updated_at,
)

fun LessonDto.toDomain(): Lesson = Lesson(
    slot = slot, timeStart = time_start, timeEnd = time_end,
    subject = subject, type = type, teacher = teacher,
    room = room, subgroup = subgroup, notes = notes,
)

private fun WeekMapDto.toWeekMap(daysMap: Map<String, List<LessonDto>>): Map<DayOfWeek, List<Lesson>> {
    val out = mutableMapOf<DayOfWeek, List<Lesson>>()
    for ((key, list) in daysMap) {
        val day = DAY_MAP[key.lowercase()] ?: continue
        out[day] = list.map { it.toDomain() }
    }
    return out
}

fun GroupScheduleDto.toDomain(): Group = Group(
    name = name, year = year, form = form, degree = degree,
    direction = direction, profile = profile,
    schedule = WeekSchedule(
        oddWeek = schedule.toWeekMap(schedule.odd_week),
        evenWeek = schedule.toWeekMap(schedule.even_week),
    ),
)
