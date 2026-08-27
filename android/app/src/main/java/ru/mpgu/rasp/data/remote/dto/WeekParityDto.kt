package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

/** `meta/week_parity.json` — какие недели НАД чертой, какие ПОД. */
@Serializable
data class WeekParityDto(
    val anchor: String = "",
    /** По букве на неделю: «o» = НАД чертой, «e» = ПОД чертой. */
    val weeks: String = "",
    val academic_year: String? = null,
    val source: String? = null,
)
