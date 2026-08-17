package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class LessonDto(
    val slot: Int? = null,
    val time_start: String,
    val time_end: String,
    val subject: String,
    val type: String? = null,
    val teacher: String? = null,
    val room: String? = null,
    val subgroup: Int? = null,
    val notes: String? = null,
)
