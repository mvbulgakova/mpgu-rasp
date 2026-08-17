package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import ru.mpgu.rasp.util.WeekParity
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WeekScreen(
    instituteId: String,
    groupFile: String,
    groupName: String,
    vm: WeekViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()
    val today = LocalDate.now().dayOfWeek
    val now = LocalTime.now()
    val isTodayInThisWeek = (WeekParity.forDate(LocalDate.now()) == WeekParity.EVEN) == state.showEven

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(groupName)
                        Text(
                            if (state.showEven) stringResource(R.string.week_title_even) else stringResource(R.string.week_title_odd),
                            style = androidx.compose.material3.MaterialTheme.typography.labelSmall,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = vm::toggleWeek) {
                        Icon(Icons.Default.SwapHoriz, contentDescription = "Сменить неделю")
                    }
                },
            )
        },
    ) { padding ->
        val week = state.group?.schedule?.let { if (state.showEven) it.evenWeek else it.oddWeek } ?: emptyMap()
        val days = listOf(
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY, DayOfWeek.SATURDAY,
        )
        LazyColumn(
            modifier = Modifier.fillMaxWidth().padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(days, key = { it.name }) { day ->
                DayCard(
                    day = day,
                    lessons = week[day] ?: emptyList(),
                    highlightNow = isTodayInThisWeek && day == today,
                    now = now,
                )
            }
        }
    }
}
