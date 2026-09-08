package ru.mpgu.rasp.ui.onboarding

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import ru.mpgu.rasp.util.GroupCatalog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(
    onPicked: (instituteId: String, groupFile: String, groupName: String) -> Unit,
    vm: OnboardingViewModel = hiltViewModel(),
) {
    val institutes by vm.institutes.collectAsState()
    val picked by vm.picked.collectAsState()
    val query by vm.query.collectAsState()
    val groups by vm.groups.collectAsState()
    // Compute the filter here (not vm.filteredGroups, which reads _groups.value
    // via a plain getter Compose can't track). remember(query, groups) keeps the
    // recomposition dependency chain explicit — updates as either changes.
    // Ищем и по коду, и по направлению с профилем — студент чаще помнит их.
    val filteredGroups = remember(query, groups) { GroupCatalog.filter(groups, query) }

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.onboarding_title)) }) }) { padding ->
        if (picked == null) {
            LazyColumn(
                modifier = Modifier.fillMaxWidth().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(institutes, key = { it.id }) { inst ->
                    ElevatedCard(modifier = Modifier.fillMaxWidth().clickable { vm.pickInstitute(inst) }) {
                        Column(Modifier.padding(16.dp)) {
                            Text(inst.name, style = MaterialTheme.typography.titleMedium)
                            Text("Групп: ${inst.groupsCount}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        } else {
            Column(Modifier.padding(padding).padding(16.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = vm::setQuery,
                    label = { Text(stringResource(R.string.search_groups_hint)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                LazyColumn(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(filteredGroups, key = { it.file }) { g ->
                        ElevatedCard(modifier = Modifier.fillMaxWidth().clickable { vm.pickGroup(g) { a, b, c -> onPicked(a, b, c) } }) {
                            Column(Modifier.padding(16.dp)) {
                                Text(g.name, style = MaterialTheme.typography.titleMedium)
                                val sub = listOfNotNull(g.profile, g.direction, g.degree)
                                    .firstOrNull()
                                sub?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                            }
                        }
                    }
                }
            }
        }
    }
}
