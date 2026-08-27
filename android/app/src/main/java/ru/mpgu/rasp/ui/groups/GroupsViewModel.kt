package ru.mpgu.rasp.ui.groups

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.GroupCatalog
import javax.inject.Inject

@HiltViewModel
class GroupsViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    savedState: SavedStateHandle,
) : ViewModel() {

    private val instituteId: String = checkNotNull(savedState["instituteId"])

    data class State(
        val groups: List<ManifestGroupDto> = emptyList(),
        val query: String = "",
        val loading: Boolean = true,
        val error: String? = null,
    ) {
        val filtered: List<ManifestGroupDto>
            get() = GroupCatalog.filter(groups, query)

        /** Институт → направление → профиль → группа. */
        val catalog: List<GroupCatalog.DirectionNode>
            get() = GroupCatalog.build(filtered)
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init { load() }

    fun setQuery(q: String) { _state.value = _state.value.copy(query = q) }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repo.getManifest(instituteId) }
                .onSuccess { _state.value = _state.value.copy(groups = it.groups, loading = false) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}
