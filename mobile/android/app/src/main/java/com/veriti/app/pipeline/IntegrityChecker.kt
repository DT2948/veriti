package com.veriti.app.pipeline

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Debug
import android.provider.Settings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.round

data class IntegrityResult(
    val token: String,
    val trustScore: Float,
    val available: Boolean,
    val message: String,
)

class IntegrityChecker(private val context: Context) {
    suspend fun requestToken(_requestHash: String): IntegrityResult = withContext(Dispatchers.IO) {
        val emulatorDetected = runCatching { isEmulator() }.getOrDefault(false)
        val rooted = runCatching { isRooted() }.getOrDefault(false)
        val debuggerState = runCatching { debuggerScore() }.getOrDefault(0.5f)
        val installSource = runCatching { installSourceScore() }.getOrDefault(0.3f to "side")
        val overlaysDetected = runCatching { hasOverlayRisk() }.getOrDefault(false)
        val mockLocationDetected = runCatching { hasMockLocationRisk() }.getOrDefault(false)

        val emulatorScore = if (emulatorDetected) 0.0f else 1.0f
        val rootScore = if (rooted) 0.0f else 1.0f
        val overlayScore = if (overlaysDetected) 0.7f else 1.0f
        val mockLocationScore = if (mockLocationDetected) 0.0f else 1.0f
        val installScore = installSource.first
        val installLabel = installSource.second

        val rawScore =
            (emulatorScore * 0.25f) +
                (rootScore * 0.20f) +
                (debuggerState * 0.15f) +
                (installScore * 0.15f) +
                (overlayScore * 0.10f) +
                (mockLocationScore * 0.15f)
        val trustScore = round(rawScore * 100f) / 100f

        val message = when {
            trustScore >= 0.8f -> "Device integrity: Strong"
            trustScore >= 0.5f -> "Device integrity: Moderate"
            else -> "Device integrity: Weak"
        }

        val token = buildString {
            append("local-v1")
            append("|em:").append(if (emulatorDetected) 1 else 0)
            append("|rt:").append(if (rooted) 1 else 0)
            append("|db:").append(if (debuggerState < 1.0f) 1 else 0)
            append("|is:").append(installLabel)
            append("|ol:").append(if (overlaysDetected) 1 else 0)
            append("|ml:").append(if (mockLocationDetected) 1 else 0)
            append("|ts:").append("%.2f".format(trustScore))
        }

        IntegrityResult(
            token = token,
            trustScore = trustScore,
            available = true,
            message = message,
        )
    }

    private fun isEmulator(): Boolean {
        val fingerprint = Build.FINGERPRINT.orEmpty()
        val model = Build.MODEL.orEmpty()
        val manufacturer = Build.MANUFACTURER.orEmpty()
        val hardware = Build.HARDWARE.orEmpty()
        val product = Build.PRODUCT.orEmpty()

        return fingerprint.contains("generic", ignoreCase = true) ||
            fingerprint.contains("unknown", ignoreCase = true) ||
            model.contains("google_sdk", ignoreCase = true) ||
            model.contains("Emulator", ignoreCase = true) ||
            model.contains("Android SDK", ignoreCase = true) ||
            manufacturer.contains("Genymotion", ignoreCase = true) ||
            hardware.contains("goldfish", ignoreCase = true) ||
            hardware.contains("ranchu", ignoreCase = true) ||
            product.contains("sdk", ignoreCase = true) ||
            product.contains("google_sdk", ignoreCase = true) ||
            product.contains("sdk_x86", ignoreCase = true)
    }

    private fun isRooted(): Boolean {
        val commonPaths = listOf(
            "/system/app/Superuser.apk",
            "/system/xbin/su",
            "/sbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
        )
        if (commonPaths.any { File(it).exists() }) {
            return true
        }

        return try {
            val process = Runtime.getRuntime().exec(arrayOf("which", "su"))
            process.inputStream.bufferedReader().use { it.readLine() != null }
        } catch (_: Exception) {
            false
        }
    }

    private fun debuggerScore(): Float {
        return when {
            Debug.isDebuggerConnected() -> 0.0f
            (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0 -> 0.5f
            else -> 1.0f
        }
    }

    private fun installSourceScore(): Pair<Float, String> {
        val installer = try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getInstallerPackageName(context.packageName)
            }
        } catch (_: Exception) {
            null
        }

        return when (installer) {
            "com.android.vending",
            "com.amazon.venezia",
            -> 1.0f to "store"

            null,
            "com.android.shell",
            -> 0.3f to "side"

            else -> 0.3f to "side"
        }
    }

    private fun hasOverlayRisk(): Boolean {
        if (Settings.canDrawOverlays(context)) {
            return true
        }

        val packages = runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.getInstalledPackages(
                    PackageManager.PackageInfoFlags.of(PackageManager.GET_PERMISSIONS.toLong())
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getInstalledPackages(PackageManager.GET_PERMISSIONS)
            }
        }.getOrDefault(emptyList())

        return packages.any { packageInfo ->
            packageInfo.packageName != context.packageName &&
                (packageInfo.requestedPermissions?.contains("android.permission.SYSTEM_ALERT_WINDOW") == true)
        }
    }

    private fun hasMockLocationRisk(): Boolean {
        val mockSettingEnabled = runCatching {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ALLOW_MOCK_LOCATION) == "1"
        }.getOrDefault(false)

        val packages = runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.packageManager.getInstalledPackages(
                    PackageManager.PackageInfoFlags.of(PackageManager.GET_PERMISSIONS.toLong())
                )
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getInstalledPackages(PackageManager.GET_PERMISSIONS)
            }
        }.getOrDefault(emptyList())

        val mockPermissionInstalled = packages.any { packageInfo ->
            packageInfo.packageName != context.packageName &&
                (packageInfo.requestedPermissions?.contains("android.permission.ACCESS_MOCK_LOCATION") == true)
        }

        return mockSettingEnabled || mockPermissionInstalled
    }
}
