package ru.mpgu.rasp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import dagger.hilt.android.AndroidEntryPoint
import ru.mpgu.rasp.ui.theme.RaspTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RaspTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Text("МПГУ Расписание — MVP")
                }
            }
        }
    }
}
