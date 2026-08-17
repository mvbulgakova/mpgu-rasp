package ru.mpgu.rasp.ui.institutes

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
import ru.mpgu.rasp.data.model.Institute

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InstitutesScreen(
    onSelect: (String) -> Unit,
    vm: InstitutesViewModel = hiltViewModel(),
) {
    val items by vm.institutes.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.institutes_title)) }) }) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxWidth().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(items, key = { it.id }) { inst -> InstituteRow(inst, onClick = { onSelect(inst.id) }) }
        }
    }
}

@Composable
private fun InstituteRow(inst: Institute, onClick: () -> Unit) {
    ElevatedCard(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp)) {
            Text(inst.name, style = MaterialTheme.typography.titleMedium)
            Text("Групп: ${inst.groupsCount}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
