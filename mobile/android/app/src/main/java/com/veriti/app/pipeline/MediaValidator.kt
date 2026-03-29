package com.veriti.app.pipeline

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import java.io.File
import java.security.MessageDigest
import kotlin.random.Random

data class MediaValidationResult(
    val mediaType: String,
    val sha256: String,
    val duplicateWarning: String?,
)

class MediaValidator(private val sessionHashes: MutableSet<String>) {
    fun validate(file: File): MediaValidationResult {
        require(file.exists()) { "Selected media no longer exists." }
        require(file.length() <= MAX_FILE_SIZE_BYTES) { "Files larger than 50MB are rejected." }

        val mediaType = detectMediaType(file) ?: error("Selected file is not a valid image or video.")
        val sha256 = file.sha256()
        val duplicateWarning = if (!sessionHashes.add(sha256)) {
            "You already selected this exact media once in this session."
        } else {
            null
        }

        when (mediaType) {
            "image" -> validateImage(file)
            "video" -> validateVideo(file)
        }

        return MediaValidationResult(
            mediaType = mediaType,
            sha256 = sha256,
            duplicateWarning = duplicateWarning,
        )
    }

    fun createPreview(file: File, mediaType: String): Bitmap? {
        return if (mediaType == "image") {
            BitmapFactory.decodeFile(file.absolutePath)
        } else {
            val retriever = MediaMetadataRetriever()
            try {
                retriever.setDataSource(file.absolutePath)
                retriever.frameAtTime
            } finally {
                retriever.release()
            }
        }
    }

    private fun validateImage(file: File) {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.absolutePath, bounds)
        require(bounds.outWidth >= 100 && bounds.outHeight >= 100) {
            "Images smaller than 100x100 pixels are not useful evidence."
        }

        val bitmap = BitmapFactory.decodeFile(file.absolutePath)
            ?: error("Image could not be decoded and appears corrupted.")
        require(hasReasonableEntropy(bitmap)) {
            "Image appears blank or solid-color and is not useful evidence."
        }
    }

    private fun validateVideo(file: File) {
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(file.absolutePath)
            val width = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)
                ?.toIntOrNull() ?: 0
            val height = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)
                ?.toIntOrNull() ?: 0
            require(width >= 100 && height >= 100) {
                "Videos smaller than 100x100 pixels are not useful evidence."
            }
        } finally {
            retriever.release()
        }
    }

    private fun detectMediaType(file: File): String? {
        val header = file.inputStream().use { input ->
            ByteArray(16).also { input.read(it) }
        }
        return when {
            header.startsWith(byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte())) -> "image"
            header.startsWith(byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47)) -> "image"
            header.copyOfRange(0, 4).contentEquals("RIFF".encodeToByteArray()) &&
                header.copyOfRange(8, 12).contentEquals("WEBP".encodeToByteArray()) -> "image"
            header.copyOfRange(0, 2).contentEquals("BM".encodeToByteArray()) -> "image"
            header.copyOfRange(4, 8).contentEquals("ftyp".encodeToByteArray()) -> "video"
            header.startsWith(byteArrayOf(0x1A, 0x45, 0xDF.toByte(), 0xA3.toByte())) -> "video"
            header.copyOfRange(0, 4).contentEquals("RIFF".encodeToByteArray()) &&
                header.copyOfRange(8, 11).contentEquals("AVI".encodeToByteArray()) -> "video"
            else -> null
        }
    }

    private fun hasReasonableEntropy(bitmap: Bitmap): Boolean {
        val sampleCount = 100
        val random = Random(bitmap.width * 31 + bitmap.height)
        val uniqueColors = mutableSetOf<Int>()
        repeat(sampleCount.coerceAtMost(bitmap.width * bitmap.height)) {
            val x = random.nextInt(bitmap.width)
            val y = random.nextInt(bitmap.height)
            uniqueColors += bitmap.getPixel(x, y)
        }
        return uniqueColors.size > 1
    }

    private fun ByteArray.startsWith(prefix: ByteArray): Boolean {
        if (size < prefix.size) return false
        return prefix.indices.all { this[it] == prefix[it] }
    }

    private fun File.sha256(): String {
        val digest = MessageDigest.getInstance("SHA-256")
        inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var read = input.read(buffer)
            while (read != -1) {
                digest.update(buffer, 0, read)
                read = input.read(buffer)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val MAX_FILE_SIZE_BYTES = 50L * 1024L * 1024L
    }
}
