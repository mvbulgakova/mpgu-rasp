package ru.mpgu.rasp.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.GroupSearch
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    private val prefs: UserPrefs,
) : ViewModel() {

    val institutes: StateFlow<List<Institute>> =
        repo.observeInstitutes().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _picked = MutableStateFlow<Institute?>(null)
    val picked: StateFlow<Institute?> = _picked.asStateFlow()

    private val _groups = MutableStateFlow<List<ManifestGroupDto>>(emptyList())
    val groups: StateFlow<List<ManifestGroupDto>> = _groups.asStateFlow()

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    val filteredGroups: List<ManifestGroupDto>
        get() = if (_query.value.isBlank()) _groups.value
                else _groups.value.filter { GroupSearch.searchKey(it.name).contains(GroupSearch.searchKey(_query.value)) }

    init { viewModelScope.launch { repo.refreshInstitutes() } }

    fun pickInstitute(inst: Institute) {
        _picked.value = inst
        viewModelScope.launch {
            runCatching { repo.getManifest(inst.id) }.onSuccess { _groups.value = it.groups }
        }
    }

    fun setQuery(q: String) { _query.value = q }

    fun pickGroup(g: ManifestGroupDto, then: (String, String, String) -> Unit) {
        val inst = _picked.value ?: return
        viewModelScope.launch {
            prefs.setSelection(inst.id, g.file, g.name)
            then(inst.id, g.file, g.name)
        }
    }
}
