package ru.mpgu.rasp.data.prefs

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore("rasp-prefs")

@Singleton
class UserPrefs @Inject constructor(@ApplicationContext private val context: Context) {

    private object Keys {
        val INSTITUTE_ID = stringPreferencesKey("institute_id")
        val GROUP_FILE = stringPreferencesKey("group_file")
        val GROUP_NAME = stringPreferencesKey("group_name")
    }

    data class Selection(val instituteId: String?, val groupFile: String?, val groupName: String?)

    val selection: Flow<Selection> = context.dataStore.data.map { p ->
        Selection(
            instituteId = p[Keys.INSTITUTE_ID],
            groupFile = p[Keys.GROUP_FILE],
            groupName = p[Keys.GROUP_NAME],
        )
    }

    suspend fun setSelection(instituteId: String, groupFile: String, groupName: String) {
        context.dataStore.edit {
            it[Keys.INSTITUTE_ID] = instituteId
            it[Keys.GROUP_FILE] = groupFile
            it[Keys.GROUP_NAME] = groupName
        }
    }

    suspend fun clear() { context.dataStore.edit { it.clear() } }
}
