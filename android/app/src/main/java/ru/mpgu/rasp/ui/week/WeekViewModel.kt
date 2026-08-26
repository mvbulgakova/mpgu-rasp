package ru.mpgu.rasp.ui.week

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.WeekParity
import java.net.URLDecoder
import java.time.LocalDate
import javax.inject.Inject

@HiltViewModel
class WeekViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    private val prefs: UserPrefs,
    savedState: SavedStateHandle,
) : ViewModel() {

    private val instituteId: String = checkNotNull(savedState["instituteId"])
    private val groupFile: String = checkNotNull(savedState["groupFile"])
    private val groupName: String = URLDecoder.decode(checkNotNull(savedState["groupName"]), "UTF-8")

    data class State(
        val group: Group? = null,
        val showEven: Boolean = WeekParity.forDate(LocalDate.now()) == WeekParity.EVEN,
        val loading: Boolean = true,
        val error: String? = null,
        val offline: Boolean = false,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        load()
        viewModelScope.launch { prefs.setSelection(instituteId, groupFile, groupName) }
    }

    fun toggleWeek() { _state.value = _state.value.copy(showEven = !_state.value.showEven) }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            repo.getGroupSchedule(instituteId, groupFile)
                .onSuccess {
                    _state.value = _state.value.copy(
                        group = it.group,
                        loading = false,
                        offline = it.fromCache,
                    )
                }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}
