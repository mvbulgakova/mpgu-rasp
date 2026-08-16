package ru.mpgu.rasp.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColors = lightColorScheme(
    primary = Indigo600, onPrimary = Neutral50,
    primaryContainer = Indigo100, onPrimaryContainer = Indigo900,
    secondary = Indigo500, onSecondary = Neutral50,
    background = Neutral50, onBackground = Neutral900,
    surface = Neutral50, onSurface = Neutral900,
    surfaceVariant = Indigo50, onSurfaceVariant = Indigo900,
)

private val DarkColors = darkColorScheme(
    primary = Indigo400, onPrimary = Neutral900,
    primaryContainer = Indigo800, onPrimaryContainer = Indigo100,
    secondary = Indigo500, onSecondary = Neutral900,
    background = Neutral900, onBackground = Neutral50,
    surface = Neutral900, onSurface = Neutral50,
    surfaceVariant = Neutral800, onSurfaceVariant = Indigo200,
)

@Composable
fun RaspTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colors = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val ctx = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(ctx) else dynamicLightColorScheme(ctx)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colors.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(colorScheme = colors, typography = AppTypography, content = content)
}
