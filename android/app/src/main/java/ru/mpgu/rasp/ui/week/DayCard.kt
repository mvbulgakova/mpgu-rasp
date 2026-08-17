package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ru.mpgu.rasp.R
import ru.mpgu.rasp.data.model.Lesson
import ru.mpgu.rasp.util.TimeSlots
import java.time.DayOfWeek
import java.time.LocalTime
import java.time.format.TextStyle
import java.util.Locale

@Composable
fun DayCard(
    day: DayOfWeek,
    lessons: List<Lesson>,
    highlightNow: Boolean,
    now: LocalTime,
) {
    val currentIdx = if (highlightNow) TimeSlots.currentLessonIndex(
        lessons.map { TimeSlots.LessonTimeRange(LocalTime.parse(it.timeStart), LocalTime.parse(it.timeEnd)) },
        now,
    ) else null

    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            day.getDisplayName(TextStyle.FULL, Locale("ru")).replaceFirstChar { it.uppercase() },
            style = MaterialTheme.typography.titleMedium,
        )
        if (lessons.isEmpty()) {
            Text(stringResource(R.string.empty_day), style = MaterialTheme.typography.bodyMedium)
        } else {
            lessons.forEachIndexed { i, l -> LessonCard(l, isNow = i == currentIdx) }
        }
    }
}
