package ru.mpgu.rasp.util

import java.time.LocalDate
import java.time.temporal.WeekFields

enum class WeekParity { ODD, EVEN;

    companion object {
        fun forDate(date: LocalDate): WeekParity {
            val week = date.get(WeekFields.ISO.weekOfWeekBasedYear())
            return if (week % 2 == 0) EVEN else ODD
        }
    }
}
