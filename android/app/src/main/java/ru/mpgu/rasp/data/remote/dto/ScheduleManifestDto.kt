package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class ScheduleManifestDto(
    val institute_id: String,
    val institute_name: String,
    val short_name: String? = null,
    val academic_year: String? = null,
    val updated_at: String? = null,
    val groups: List<ManifestGroupDto> = emptyList(),
)

@Serializable
data class ManifestGroupDto(
    val name: String,
    val file: String,
    val year: Int? = null,
    val form: String? = null,
    val degree: String? = null,
)
