package ru.mpgu.rasp.ui.groups

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroupsScreen(
    instituteId: String,
    onSelect: (groupFile: String, groupName: String) -> Unit,
    vm: GroupsViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()

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
                items(state.filtered, key = { it.file }) { g ->
                    ElevatedCard(
                        modifier = Modifier.fillMaxWidth().clickable { onSelect(g.file, g.name) },
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text(g.name, style = MaterialTheme.typography.titleMedium)
                            g.degree?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                        }
                    }
                }
            }
        }
    }
}
