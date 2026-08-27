package ru.mpgu.rasp.data.repo

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import ru.mpgu.rasp.data.local.RaspDatabase
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity
import ru.mpgu.rasp.data.local.entity.InstituteEntity
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.remote.ScheduleApi
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.toDomain
import ru.mpgu.rasp.util.WeekCalendar
import ru.mpgu.rasp.util.WeekParity
import java.io.IOException
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScheduleRepository @Inject constructor(
    private val api: ScheduleApi,
    private val db: RaspDatabase,
    private val json: Json,
) {
    fun observeInstitutes(): Flow<List<Institute>> =
        db.instituteDao().observeAll().map { rows ->
            rows.map { Institute(it.id, it.name, it.shortName, it.groupsCount, it.updatedAt) }
        }

    suspend fun refreshInstitutes(): Result<Unit> = runCatching {
        val fresh = api.index()
        db.instituteDao().upsert(fresh.map {
            InstituteEntity(
                id = it.id, name = it.name, shortName = it.shortName,
                groupsCount = it.groupsCount, updatedAt = it.updatedAt,
                cachedAt = System.currentTimeMillis(),
            )
        })
    }

    suspend fun getManifest(instituteId: String) = api.manifest(instituteId)

    /**
     * Календарь НАД/ПОД чертой из data-ветки. Если он недоступен (нет сети,
     * старая data-ветка) — встроенная таблица: показать неделю всё равно
     * надо, а без сети она не «неизвестна», а просто прошлогодняя.
     */
    suspend fun getWeekCalendar(): WeekCalendar = runCatching {
        val dto = api.weekParity()
        if (dto.anchor.isBlank() || dto.weeks.isBlank()) WeekParity.BUILT_IN
        else WeekCalendar(LocalDate.parse(dto.anchor), dto.weeks)
    }.getOrDefault(WeekParity.BUILT_IN)

    data class GroupResult(val group: Group, val fromCache: Boolean)

    suspend fun getGroupSchedule(instituteId: String, groupFile: String): Result<GroupResult> {
        val key = "$instituteId/$groupFile"
        return runCatching { api.group(instituteId, groupFile) }
            .map { fresh ->
                // Cache-write MUST NOT propagate — a full disk or a Room error should
                // not eat a valid network response and drop the user to «offline».
                runCatching {
                    db.groupCacheDao().upsert(
                        GroupCacheEntity(
                            cacheKey = key, instituteId = instituteId, groupFile = groupFile,
                            name = fresh.name,
                            json = json.encodeToString(GroupScheduleDto.serializer(), fresh.toDto()),
                            cachedAt = System.currentTimeMillis(),
                        )
                    )
                }
                GroupResult(fresh, fromCache = false)
            }
            .recoverCatching { err ->
                if (err !is IOException) throw err
                val cached = db.groupCacheDao().get(key) ?: throw err
                val group = json.decodeFromString(GroupScheduleDto.serializer(), cached.json).toDomain()
                GroupResult(group, fromCache = true)
            }
    }

    // Round-trip helper: domain Group → DTO for cache serialization.
    private fun Group.toDto(): GroupScheduleDto {
        val weekMap = ru.mpgu.rasp.data.remote.dto.WeekMapDto(
            odd_week = schedule.oddWeek.mapKeys { it.key.name.lowercase() }
                .mapValues { entry -> entry.value.map { it.toDto() } },
            even_week = schedule.evenWeek.mapKeys { it.key.name.lowercase() }
                .mapValues { entry -> entry.value.map { it.toDto() } },
        )
        return GroupScheduleDto(name = name, year = year, form = form, degree = degree, schedule = weekMap)
    }

    private fun ru.mpgu.rasp.data.model.Lesson.toDto() = ru.mpgu.rasp.data.remote.dto.LessonDto(
        slot = slot, time_start = timeStart, time_end = timeEnd, subject = subject,
        type = type, teacher = teacher, room = room, subgroup = subgroup, notes = notes,
    )
}
