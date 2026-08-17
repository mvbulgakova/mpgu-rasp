package ru.mpgu.rasp.data.local.dao

import androidx.room.Dao
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow
import ru.mpgu.rasp.data.local.entity.InstituteEntity

@Dao
interface InstituteDao {
    @Query("SELECT * FROM institute ORDER BY name")
    fun observeAll(): Flow<List<InstituteEntity>>

    @Upsert(entity = InstituteEntity::class)
    suspend fun upsert(items: List<InstituteEntity>)

    @Query("DELETE FROM institute")
    suspend fun clear()
}
