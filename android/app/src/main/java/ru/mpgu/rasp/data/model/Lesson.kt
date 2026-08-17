package ru.mpgu.rasp.data.model

data class Lesson(
    val slot: Int?,
    val timeStart: String,
    val timeEnd: String,
    val subject: String,
    val type: String?,      // lecture / practice / lab / seminar / other
    val teacher: String?,
    val room: String?,
    val subgroup: String?,
    val notes: String?,
)
