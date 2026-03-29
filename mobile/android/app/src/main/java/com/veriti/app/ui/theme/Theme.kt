package com.veriti.app.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val VeritiColors = darkColorScheme(
    primary = VeritiBlue,
    onPrimary = VeritiTextPrimary,
    primaryContainer = VeritiSurfaceElevated,
    onPrimaryContainer = VeritiTextPrimary,
    secondary = VeritiTextSecondary,
    onSecondary = VeritiTextPrimary,
    secondaryContainer = VeritiSurface,
    onSecondaryContainer = VeritiTextSecondary,
    tertiary = VeritiWarning,
    onTertiary = VeritiBackground,
    background = VeritiBackground,
    onBackground = VeritiTextPrimary,
    surface = VeritiSurface,
    onSurface = VeritiTextPrimary,
    surfaceVariant = VeritiSurfaceElevated,
    onSurfaceVariant = VeritiTextSecondary,
    outline = VeritiBorder,
    error = VeritiDanger,
    onError = VeritiTextPrimary,
)

private val VeritiTypography = Typography(
    headlineSmall = TextStyle(
        fontSize = 19.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 0.sp,
    ),
    titleMedium = TextStyle(
        fontSize = 15.sp,
        fontWeight = FontWeight.Medium,
        letterSpacing = 0.sp,
    ),
    bodyMedium = TextStyle(
        fontSize = 14.sp,
        fontWeight = FontWeight.Normal,
        letterSpacing = 0.sp,
    ),
    bodySmall = TextStyle(
        fontSize = 12.sp,
        fontWeight = FontWeight.Normal,
        letterSpacing = 0.sp,
    ),
    labelLarge = TextStyle(
        fontSize = 17.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 0.sp,
    ),
)

@Composable
fun VeritiTheme(
    darkTheme: Boolean = true,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colors = VeritiColors

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colors.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = colors,
        typography = VeritiTypography,
        content = content,
    )
}
