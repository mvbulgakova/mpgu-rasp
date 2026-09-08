package ru.mpgu.rasp.ui.groups

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import ru.mpgu.rasp.util.GroupCatalog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroupsScreen(
    instituteId: String,
    onSelect: (groupFile: String, groupName: String) -> Unit,
    vm: GroupsViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()
    val catalog = state.catalog
    // Свёрнутые направления: по умолчанию раскрыто, если оно одно или идёт поиск.
    val collapsed = remember { mutableStateMapOf<String, Boolean>() }

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.groups_title)) }) }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp)) {
            OutlinedTextField(
                value = state.query,
                onValueChange = vm::setQuery,
                label = { Text(stringResource(R.string.search_groups_hint)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            LazyColumn(
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                contentPadding = PaddingValues(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                catalog.forEach { dir ->
                    val expanded = collapsed[dir.direction]?.not()
                        ?: (catalog.size == 1 || state.query.isNotBlank())

                    item(key = "dir:${dir.direction}") {
                        DirectionHeader(
                            title = dir.direction,
                            groupCount = dir.profiles.sumOf { it.groups.size },
                            expanded = expanded,
                            onToggle = { collapsed[dir.direction] = expanded },
                        )
                    }

                    if (!expanded) return@forEach

                    dir.profiles.forEach { profile ->
                        if (profile.profile != GroupCatalog.NO_PROFILE ||
                            dir.profiles.size > 1
                        ) {
                            item(key = "prof:${dir.direction}/${profile.profile}") {
                                Text(
                                    profile.profile,
                                    style = MaterialTheme.typography.titleSmall,
                                    modifier = Modifier.padding(start = 8.dp, top = 4.dp),
                                )
                            }
                        }
                        items(profile.groups, key = { it.file }) { g ->
                            ElevatedCard(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onSelect(g.file, g.name) },
                            ) {
                                Column(Modifier.padding(16.dp)) {
                                    Text(g.name, style = MaterialTheme.typography.titleMedium)
                                    val sub = listOfNotNull(
                                        g.year?.let { "$it курс" },
                                        g.degree,
                                    ).joinToString(" · ")
                                    if (sub.isNotBlank()) {
                                        Text(sub, style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DirectionHeader(
    title: String,
    groupCount: Int,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onToggle),
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    groupCount.toString(),
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(end = 8.dp),
                )
                Icon(
                    if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null,
                )
            }
        }
    }
}
