package ru.mpgu.rasp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.map
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
        setContent {
            RaspTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val start by prefs.selection
                        .map { if (it.instituteId != null && it.groupFile != null) Dest.Institutes.route else Dest.Onboarding.route }
                        .collectAsState(initial = Dest.Onboarding.route)
                    RaspNavGraph(startDestination = start)
                }
            }
        }
    }
}
