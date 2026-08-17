package ru.mpgu.rasp.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import ru.mpgu.rasp.data.remote.ScheduleApi
import javax.inject.Singleton

private const val DEFAULT_BASE = "https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data"

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    @Provides @Singleton
    fun provideHttp(json: Json): HttpClient = HttpClient(CIO) {
        install(ContentNegotiation) { json(json) }
        install(Logging) { level = LogLevel.INFO }
    }

    @Provides @Singleton
    fun provideApi(http: HttpClient): ScheduleApi = ScheduleApi(http, DEFAULT_BASE)
}
