package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class GroupScheduleDto(
    val name: String,
    val year: Int? = null,
    val form: String? = null,
    val degree: String? = null,
    val direction: String? = null,
    val profile: String? = null,
    val schedule: WeekMapDto = WeekMapDto(),
)

@Serializable
data class WeekMapDto(
    val odd_week: Map<String, List<LessonDto>> = emptyMap(),
    val even_week: Map<String, List<LessonDto>> = emptyMap(),
)
