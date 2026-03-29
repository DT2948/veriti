package com.veriti.app.network

import com.veriti.app.BuildConfig
import com.veriti.app.model.SubmissionData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

class ApiClient(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build(),
) {
    suspend fun uploadSubmission(
        submissionData: SubmissionData,
        onProgress: (Float) -> Unit,
    ): UploadResult = withContext(Dispatchers.IO) {
        try {
            val multipartBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart(
                    "file",
                    submissionData.file.name,
                    ProgressRequestBody(
                        file = submissionData.file,
                        contentType = submissionData.file.guessContentType().toMediaTypeOrNull(),
                        onProgress = onProgress,
                    ),
                )
                .addFormDataPart("text_note", submissionData.textNote)
                .addFormDataPart("latitude", submissionData.latitude.toString())
                .addFormDataPart("longitude", submissionData.longitude.toString())
                .addFormDataPart("device_trust_score", submissionData.deviceTrustScore.toString())
                .addFormDataPart("integrity_token", submissionData.integrityToken)
                .addFormDataPart("incident_type", submissionData.incidentType)
                .build()

            val request = Request.Builder()
                .url(UPLOAD_URL)
                .post(multipartBody)
                .build()

            client.newCall(request).execute().use { response ->
                val body = response.body?.string().orEmpty()
                return@withContext if (response.isSuccessful) {
                    UploadResult.Success(body.ifBlank { "Report submitted anonymously." })
                } else {
                    UploadResult.Failure("Submission failed (${response.code}). $body")
                }
            }
        } catch (exception: IOException) {
            return@withContext UploadResult.Timeout(
                "Could not reach server. Your report is saved locally and will retry."
            )
        } catch (exception: Exception) {
            return@withContext UploadResult.Failure(
                exception.message ?: "Submission failed. Tap to retry."
            )
        }
    }

    companion object {
        private const val BASE_URL = BuildConfig.API_BASE_URL
        const val UPLOAD_URL = "$BASE_URL/api/v1/submissions/upload"
    }
}

sealed class UploadResult {
    data class Success(val message: String) : UploadResult()
    data class Failure(val message: String) : UploadResult()
    data class Timeout(val message: String) : UploadResult()
}

private fun File.guessContentType(): String = when (extension.lowercase()) {
    "jpg", "jpeg" -> "image/jpeg"
    "png" -> "image/png"
    "webp" -> "image/webp"
    "bmp" -> "image/bmp"
    "gif" -> "image/gif"
    "mp4" -> "video/mp4"
    "mov" -> "video/quicktime"
    "avi" -> "video/x-msvideo"
    "webm" -> "video/webm"
    "mkv" -> "video/x-matroska"
    else -> "application/octet-stream"
}

private class ProgressRequestBody(
    private val file: File,
    private val contentType: okhttp3.MediaType?,
    private val onProgress: (Float) -> Unit,
) : RequestBody() {
    override fun contentType() = contentType

    override fun contentLength(): Long = file.length()

    override fun writeTo(sink: okio.BufferedSink) {
        val total = contentLength().toFloat().coerceAtLeast(1f)
        file.inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var uploaded = 0L
            var read = input.read(buffer)
            while (read >= 0) {
                sink.write(buffer, 0, read)
                uploaded += read
                onProgress((uploaded / total).coerceIn(0f, 1f))
                read = input.read(buffer)
            }
        }
    }
}
