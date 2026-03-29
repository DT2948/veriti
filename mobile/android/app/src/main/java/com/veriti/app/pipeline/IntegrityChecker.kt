package com.veriti.app.pipeline

import android.content.Context
import com.google.android.gms.tasks.Tasks
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.StandardIntegrityManager
import com.veriti.app.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class IntegrityResult(
    val token: String,
    val trustScore: Float,
    val available: Boolean,
    val message: String,
)

class IntegrityChecker(private val context: Context) {
    suspend fun requestToken(requestHash: String): IntegrityResult = withContext(Dispatchers.IO) {
        val projectNumber = BuildConfig.INTEGRITY_CLOUD_PROJECT_NUMBER
        if (projectNumber <= 0L) {
            return@withContext IntegrityResult(
                token = "",
                trustScore = 0.0f,
                available = false,
                message = "Device integrity unavailable in this build.",
            )
        }

        return@withContext try {
            val manager = IntegrityManagerFactory.createStandard(context)
            val provider = Tasks.await(
                manager.prepareIntegrityToken(
                    StandardIntegrityManager.PrepareIntegrityTokenRequest.builder()
                        .setCloudProjectNumber(projectNumber)
                        .build()
                )
            )

            val token = Tasks.await(
                provider.request(
                    StandardIntegrityManager.StandardIntegrityTokenRequest.builder()
                        .setRequestHash(requestHash.take(500))
                        .build()
                )
            ).token()

            IntegrityResult(
                token = token,
                trustScore = 1.0f,
                available = true,
                message = "Device integrity verified.",
            )
        } catch (exception: Exception) {
            IntegrityResult(
                token = "",
                trustScore = 0.0f,
                available = false,
                message = "Device integrity unavailable on this device.",
            )
        }
    }
}
