package ru.mpgu.rasp.data.model

data class Lesson(
    val slot: Int?,
    val timeStart: String,
    val timeEnd: String,
    val subject: String,
    val type: String?,      // lecture / practice / lab / seminar / other
    val teacher: String?,
    val room: String?,
    val subgroup: Int?,     // 1 or 2 (podgruppa), null if lesson covers full group
    val notes: String?,
)
