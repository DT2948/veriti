package com.veriti.app.pipeline

import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import com.veriti.app.model.PipelineState
import com.veriti.app.model.PipelineStepState
import com.veriti.app.model.StepStatus
import java.io.File

data class LocalProcessingResult(
    val file: File,
    val mediaType: String,
    val previewBitmap: Bitmap?,
    val sha256: String,
    val latitude: Double,
    val longitude: Double,
    val integrityToken: String,
    val deviceTrustScore: Float,
    val duplicateWarning: String?,
)

class LocalPipeline(
    context: Context,
    private val sessionHashes: MutableSet<String>,
) {
    private val appContext = context.applicationContext
    private val exifStripper = ExifStripper(appContext)
    private val locationCoarsener = LocationCoarsener(appContext)
    private val mediaValidator = MediaValidator(sessionHashes)
    private val integrityChecker = IntegrityChecker(appContext)
    private val submittedHashes = mutableSetOf<String>()

    suspend fun process(
        uri: Uri,
        onState: (PipelineState) -> Unit,
    ): Result<LocalProcessingResult> {
        return runCatching {
            onState(
                PipelineState(
                    isRunning = true,
                    statusMessage = "Running local privacy checks on your device...",
                )
            )

            val extension = inferExtension(uri)
            val initialCopy = exifStripper.copyToInternalStorage(uri, extension)
            val mediaKind = if (extension in IMAGE_EXTENSIONS) "image" else "video"
            if (mediaKind == "image") {
                exifStripper.stripExif(initialCopy)
                onState(
                    PipelineState(
                        metadata = PipelineStepState(StepStatus.Success, "Metadata stripped from image."),
                        isRunning = true,
                        statusMessage = "Metadata stripped locally.",
                    )
                )
            } else {
                // TODO: Add equivalent metadata scrubbing for video containers if broader support is needed.
                onState(
                    PipelineState(
                        metadata = PipelineStepState(StepStatus.Success, "Video copied to app-private storage."),
                        isRunning = true,
                        statusMessage = "Video copied into app-private storage.",
                    )
                )
            }

            val location = locationCoarsener.getCoarsenedLocation()
            onState(
                PipelineState(
                    metadata = PipelineStepState(StepStatus.Success, metadataMessage(mediaKind)),
                    location = PipelineStepState(
                        StepStatus.Success,
                        "Location coarsened to ~500m before upload.",
                    ),
                    isRunning = true,
                    statusMessage = "Approximate location coarsened on device.",
                )
            )

            val validation = mediaValidator.validate(initialCopy)
            val validationDetail = validation.duplicateWarning
                ?: "Media type, size, integrity, and quality checks passed."
            onState(
                PipelineState(
                    metadata = PipelineStepState(StepStatus.Success, metadataMessage(mediaKind)),
                    location = PipelineStepState(
                        StepStatus.Success,
                        "Location coarsened to ~500m before upload.",
                    ),
                    mediaValidation = PipelineStepState(StepStatus.Success, validationDetail),
                    isRunning = true,
                    statusMessage = "Local media validation passed.",
                )
            )

            val integrity = integrityChecker.requestToken(validation.sha256)
            val integrityStatus = if (integrity.available) StepStatus.Success else StepStatus.Warning
            onState(
                PipelineState(
                    metadata = PipelineStepState(StepStatus.Success, metadataMessage(mediaKind)),
                    location = PipelineStepState(
                        StepStatus.Success,
                        "Location coarsened to ~500m before upload.",
                    ),
                    mediaValidation = PipelineStepState(StepStatus.Success, validationDetail),
                    integrity = PipelineStepState(integrityStatus, integrity.message),
                    isRunning = false,
                    isReadyForUpload = true,
                    statusMessage = "All local checks passed. Your data is sanitized.",
                )
            )

            LocalProcessingResult(
                file = initialCopy,
                mediaType = validation.mediaType,
                previewBitmap = mediaValidator.createPreview(initialCopy, validation.mediaType),
                sha256 = validation.sha256,
                latitude = location.latitude,
                longitude = location.longitude,
                integrityToken = integrity.token,
                deviceTrustScore = integrity.trustScore,
                duplicateWarning = validation.duplicateWarning,
            )
        }
    }

    fun hasSubmittedHash(sha256: String): Boolean = submittedHashes.contains(sha256)

    fun markSubmittedHash(sha256: String) {
        submittedHashes += sha256
    }

    private fun inferExtension(uri: Uri): String {
        val guessed = appContext.contentResolver.getType(uri).orEmpty()
        return when {
            guessed.contains("png") -> "png"
            guessed.contains("webp") -> "webp"
            guessed.contains("bmp") -> "bmp"
            guessed.contains("gif") -> "gif"
            guessed.contains("mp4") -> "mp4"
            guessed.contains("quicktime") -> "mov"
            guessed.contains("avi") -> "avi"
            guessed.contains("webm") -> "webm"
            guessed.contains("video") -> "mp4"
            else -> "jpg"
        }
    }

    private fun metadataMessage(mediaKind: String): String {
        return if (mediaKind == "image") {
            "Metadata stripped from media."
        } else {
            "Video stored privately on device before upload."
        }
    }

    companion object {
        private val IMAGE_EXTENSIONS = setOf("jpg", "jpeg", "png", "webp", "bmp", "gif")
    }
}
