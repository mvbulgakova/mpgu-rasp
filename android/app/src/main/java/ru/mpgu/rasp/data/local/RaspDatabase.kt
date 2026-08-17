package ru.mpgu.rasp.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import ru.mpgu.rasp.data.local.dao.GroupCacheDao
import ru.mpgu.rasp.data.local.dao.InstituteDao
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity
import ru.mpgu.rasp.data.local.entity.InstituteEntity

@Database(
    entities = [InstituteEntity::class, GroupCacheEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class RaspDatabase : RoomDatabase() {
    abstract fun instituteDao(): InstituteDao
    abstract fun groupCacheDao(): GroupCacheDao
}
