package ru.mpgu.rasp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.ui.nav.Dest
import ru.mpgu.rasp.ui.nav.RaspNavGraph
import ru.mpgu.rasp.ui.theme.RaspTheme
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var prefs: UserPrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Resolve start destination synchronously so the NavHost never flashes
        // Onboarding for a user who already has a saved selection.
        // DataStore's first read is fast (single small file); the block runs
        // once per cold start on the main thread — acceptable for MVP.
        val startRoute = runBlocking {
            val sel = prefs.selection.first()
            if (sel.instituteId != null && sel.groupFile != null && sel.groupName != null) {
                Dest.Week(sel.instituteId, sel.groupFile, sel.groupName).route
            } else {
                Dest.Onboarding.route
            }
        }

        setContent {
            RaspTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    RaspNavGraph(startDestination = startRoute)
                }
            }
        }
    }
}
