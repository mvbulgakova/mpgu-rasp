package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class IndexDto(
    val institutes: List<IndexInstituteDto> = emptyList(),
)

@Serializable
data class IndexInstituteDto(
    val id: String,
    val name: String,
    val short_name: String? = null,
    val groups_count: Int = 0,
    val updated_at: String? = null,
)
