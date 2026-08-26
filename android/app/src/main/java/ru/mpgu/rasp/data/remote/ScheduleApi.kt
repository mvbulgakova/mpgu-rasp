package ru.mpgu.rasp.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.http.encodeURLPath
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

    // Group file names contain Cyrillic (e.g. «БОГ35-ГЭК2101») — CDN and
    // browsers accept percent-encoded UTF-8; encode explicitly rather than
    // relying on Ktor's implicit normalization, which varies by engine.
    suspend fun group(instituteId: String, groupFile: String): Group =
        http.get("$baseUrl/institutes/$instituteId/groups/${groupFile.encodeURLPath()}.json")
            .body<GroupScheduleDto>().toDomain()
}
