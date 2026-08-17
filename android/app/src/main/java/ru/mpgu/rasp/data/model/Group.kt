package ru.mpgu.rasp.data.model

data class Group(
    val name: String,
    val year: Int?,
    val form: String?,       // full_time, part_time, ...
    val degree: String?,     // bachelor, master, specialist, ...
    val schedule: WeekSchedule,
)
