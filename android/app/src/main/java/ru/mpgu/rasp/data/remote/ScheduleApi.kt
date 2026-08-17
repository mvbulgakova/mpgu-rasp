package ru.mpgu.rasp.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.dto.IndexDto
import ru.mpgu.rasp.data.remote.dto.ScheduleManifestDto
import javax.inject.Singleton

@Singleton
class ScheduleApi(
    private val http: HttpClient,
    private val baseUrl: String,
) {
    suspend fun index(): List<Institute> =
        http.get("$baseUrl/meta/index.json").body<IndexDto>().institutes.map { it.toDomain() }

    suspend fun manifest(instituteId: String): ScheduleManifestDto =
        http.get("$baseUrl/institutes/$instituteId/schedule.json").body()

    suspend fun group(instituteId: String, groupFile: String): Group =
        http.get("$baseUrl/institutes/$instituteId/groups/$groupFile.json")
            .body<GroupScheduleDto>().toDomain()
}
