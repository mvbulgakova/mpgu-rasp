package ru.mpgu.rasp.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity

@Dao
interface GroupCacheDao {
    @Query("SELECT * FROM group_cache WHERE cacheKey = :key LIMIT 1")
    suspend fun get(key: String): GroupCacheEntity?

    @Upsert
    suspend fun upsert(entity: GroupCacheEntity)
}
