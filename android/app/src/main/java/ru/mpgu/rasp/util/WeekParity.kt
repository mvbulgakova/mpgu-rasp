package ru.mpgu.rasp.util

import java.time.LocalDate
import java.time.temporal.WeekFields
import java.util.Locale

enum class WeekParity { ODD, EVEN;

    companion object {
        private val ISO = WeekFields.of(Locale.forLanguageTag("ru-RU-u-fw-mon"))

        fun forDate(date: LocalDate): WeekParity {
            val week = date.get(WeekFields.ISO.weekOfWeekBasedYear())
            return if (week % 2 == 0) EVEN else ODD
        }
    }
}
