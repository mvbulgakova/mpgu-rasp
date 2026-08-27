package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Alignment
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WeekScreen(
    instituteId: String,
    groupFile: String,
    groupName: String,
    onChangeGroup: () -> Unit = {},
    vm: WeekViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()
    // Tick every 30s so the «сейчас» chip and highlight stay accurate as time
    // passes — otherwise they freeze at composition time and mislead the user.
    var now by remember { mutableStateOf(LocalTime.now()) }
    var today by remember { mutableStateOf(LocalDate.now().dayOfWeek) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(30_000)
            now = LocalTime.now()
            today = LocalDate.now().dayOfWeek
        }
    }
    val isTodayInThisWeek = state.showingCurrentWeek

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
                    IconButton(onClick = onChangeGroup) {
                        Icon(Icons.Default.School, contentDescription = "Сменить группу")
                    }
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
        Column(modifier = Modifier.fillMaxWidth().padding(padding)) {
            if (state.offline) OfflineBanner()
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
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
}


@Composable
private fun OfflineBanner() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.tertiaryContainer)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Icon(
            Icons.Default.CloudOff,
            contentDescription = null,
            modifier = Modifier.size(18.dp),
            tint = MaterialTheme.colorScheme.onTertiaryContainer,
        )
        Text(
            "Показано из кэша — нет соединения",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onTertiaryContainer,
        )
    }
}
