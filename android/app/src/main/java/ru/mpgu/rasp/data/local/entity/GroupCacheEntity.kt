package ru.mpgu.rasp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "group_cache")
data class GroupCacheEntity(
    @PrimaryKey val cacheKey: String,   // instituteId + "/" + groupFile
    val instituteId: String,
    val groupFile: String,
    val name: String,
    val json: String,                   // raw domain JSON to keep the schema flat
    val cachedAt: Long,
)
