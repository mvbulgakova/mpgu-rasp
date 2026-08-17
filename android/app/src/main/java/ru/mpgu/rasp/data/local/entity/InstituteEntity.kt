package ru.mpgu.rasp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "institute")
data class InstituteEntity(
    @PrimaryKey val id: String,
    val name: String,
    val shortName: String?,
    val groupsCount: Int,
    val updatedAt: String?,
    val cachedAt: Long,
)
