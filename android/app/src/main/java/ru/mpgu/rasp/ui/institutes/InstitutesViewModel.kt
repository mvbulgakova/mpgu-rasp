package ru.mpgu.rasp.ui.institutes

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.repo.ScheduleRepository
import javax.inject.Inject

@HiltViewModel
class InstitutesViewModel @Inject constructor(
    private val repo: ScheduleRepository,
) : ViewModel() {

    val institutes: StateFlow<List<Institute>> =
        repo.observeInstitutes().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    init { refresh() }

    fun refresh() { viewModelScope.launch { repo.refreshInstitutes() } }
}
