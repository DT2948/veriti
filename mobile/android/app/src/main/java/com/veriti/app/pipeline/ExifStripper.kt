package com.veriti.app.pipeline

import android.content.Context
import android.media.ExifInterface
import android.net.Uri
import java.io.File
import java.util.UUID

class ExifStripper(private val context: Context) {
    private val exifTags = listOf(
        ExifInterface.TAG_GPS_LATITUDE,
        ExifInterface.TAG_GPS_LONGITUDE,
        ExifInterface.TAG_GPS_ALTITUDE,
        ExifInterface.TAG_GPS_LATITUDE_REF,
        ExifInterface.TAG_GPS_LONGITUDE_REF,
        ExifInterface.TAG_MAKE,
        ExifInterface.TAG_MODEL,
        ExifInterface.TAG_DATETIME,
        ExifInterface.TAG_DATETIME_ORIGINAL,
        ExifInterface.TAG_DATETIME_DIGITIZED,
        ExifInterface.TAG_SOFTWARE,
        ExifInterface.TAG_IMAGE_UNIQUE_ID,
    )

    fun copyToInternalStorage(uri: Uri, extension: String): File {
        val file = File(context.filesDir, "${UUID.randomUUID()}.$extension")
        context.contentResolver.openInputStream(uri)?.use { input ->
            file.outputStream().use { output -> input.copyTo(output) }
        } ?: error("Unable to read selected media.")
        return file
    }

    fun stripExif(file: File) {
        val exif = ExifInterface(file.absolutePath)
        exifTags.forEach { tag -> exif.setAttribute(tag, null) }
        exif.saveAttributes()
    }
}
