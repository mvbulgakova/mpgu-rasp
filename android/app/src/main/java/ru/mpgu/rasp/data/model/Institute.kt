package ru.mpgu.rasp.data.model

data class Institute(
    val id: String,
    val name: String,
    val shortName: String?,
    val groupsCount: Int,
    val updatedAt: String?,
)
