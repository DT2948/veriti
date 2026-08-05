package com.veriti.app.pipeline

import android.graphics.BitmapFactory
import android.media.ExifInterface
import android.net.Uri
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest
import kotlin.math.ceil
import kotlin.math.sqrt


@RunWith(AndroidJUnit4::class)
class PrivacyBenchmarkTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val appContext = instrumentation.targetContext
    private val testContext = instrumentation.context
    private val args = InstrumentationRegistry.getArguments()
    private val fixtureAssetDir get() = args.getString("fixtureDirectory") ?: "privacy"

    @Test
    fun benchmarkPrivacyPipeline() = runBlocking {
        val manifest = JSONObject(readAsset(fixtureAssetDir + "/manifest.json"))
        val fixtures = manifest.getJSONArray("fixtures").objects()
        val validFixtures = fixtures.filter { !it.getBoolean("intentionally_invalid") }
        val warmups = args.getString("warmups")?.toIntOrNull() ?: 5
        val repetitions = args.getString("repetitions")?.toIntOrNull()
            ?: ceil(100.0 / fixtures.size).toInt()

        repeat(warmups) { runSample(validFixtures[it % validFixtures.size], false) }
        val samples = mutableListOf<JSONObject>()
        repeat(repetitions) { pass ->
            fixtures.indices.forEach { offset ->
                val fixture = fixtures[(offset + pass) % fixtures.size]
                val started = SystemClock.elapsedRealtimeNanos()
                samples += runCatching { runSample(fixture, true) }.getOrElse {
                    failedSample(fixture, elapsedMs(started))
                }
            }
        }

        val outputRoot = args.getString("outputDirectory")?.let(::File)
            ?: appContext.getExternalFilesDir("benchmark_results")
            ?: error("External benchmark output directory is unavailable.")
        outputRoot.mkdirs()
        File(outputRoot, "android-privacy-raw.jsonl").bufferedWriter().use { writer ->
            samples.forEach { writer.appendLine(it.toString()) }
        }
        val summary = buildSummary(samples, manifest)
        File(outputRoot, "android-privacy-summary.json").writeText(summary.toString(2))

        assertTrue(samples.size >= 100)
        assertEquals(samples.size, summary.getInt("sample_count"))
    }

    @Test
    fun privacyPipelineCorrectness() = runBlocking {
        val manifest = JSONObject(readAsset(fixtureAssetDir + "/manifest.json"))
        manifest.getJSONArray("fixtures").objects().forEach { fixture ->
            val invalid = fixture.getBoolean("intentionally_invalid")
            val result = runCatching { runSample(fixture, false) }
            if (invalid) {
                assertTrue(result.isFailure)
            } else {
                val row = result.getOrThrow()
                assertTrue(row.getBoolean("readable_output"))
                assertTrue(row.getBoolean("original_unchanged"))
                if (fixture.getBoolean("exif")) assertTrue(row.getBoolean("metadata_removed"))
                if (fixture.getBoolean("gps")) assertTrue(row.getBoolean("gps_removed"))
            }
        }
        val sanitized = TextSanitizer().sanitize(
            "My name is Jordan Example, email jordan@example.test or call +1 555 010 1234."
        )
        assertFalse(sanitized.contains("jordan@example.test"))
        assertFalse(sanitized.contains("555 010 1234"))
        assertFalse(sanitized.contains("Jordan Example", ignoreCase = true))
    }

    private suspend fun runSample(fixture: JSONObject, measured: Boolean): JSONObject {
        val filename = fixture.getString("filename")
        val input = copyAsset(fixtureAssetDir + "/" + filename)
        val inputHash = input.sha256()
        val pipeline = LocalPipeline(appContext, mutableSetOf()) {
            CoarsenedLocation(25.2045, 55.269)
        }
        val totalStarted = SystemClock.elapsedRealtimeNanos()
        val result = pipeline.process(Uri.fromFile(input)) {}.getOrThrow()
        val totalMs = elapsedMs(totalStarted)

        val stripper = ExifStripper(appContext)
        val encodingStarted = SystemClock.elapsedRealtimeNanos()
        val stageCopy = stripper.copyToInternalStorage(
            Uri.fromFile(input),
            filename.substringAfterLast('.', "jpg"),
        )
        val encodingMs = elapsedMs(encodingStarted)
        val exifStarted = SystemClock.elapsedRealtimeNanos()
        stripper.stripExif(stageCopy)
        val exifMs = elapsedMs(exifStarted)
        val locationStarted = SystemClock.elapsedRealtimeNanos()
        LocationCoarsener(appContext).coarsen(25.2048, 55.2708)
        val locationMs = elapsedMs(locationStarted)
        val validationStarted = SystemClock.elapsedRealtimeNanos()
        MediaValidator(mutableSetOf()).validate(stageCopy)
        val validationMs = elapsedMs(validationStarted)
        val integrityStarted = SystemClock.elapsedRealtimeNanos()
        IntegrityChecker(appContext).requestToken("benchmark")
        val integrityMs = elapsedMs(integrityStarted)
        val redactionStarted = SystemClock.elapsedRealtimeNanos()
        val sanitizedCaption = TextSanitizer().sanitize(
            "My name is Jordan Example, jordan@example.test, +1 555 010 1234"
        )
        val redactionMs = elapsedMs(redactionStarted)
        val supportedPiiRemoved = !sanitizedCaption.contains("Jordan Example", ignoreCase = true) &&
            !sanitizedCaption.contains("jordan@example.test") &&
            !sanitizedCaption.contains("555 010 1234")

        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(result.file.absolutePath, bounds)
        val exif = ExifInterface(result.file.absolutePath)
        val metadataRemoved = exif.getAttribute(ExifInterface.TAG_MAKE) == null &&
            exif.getAttribute(ExifInterface.TAG_MODEL) == null &&
            exif.getAttribute(ExifInterface.TAG_DATETIME_ORIGINAL) == null
        val gpsRemoved = exif.getAttribute(ExifInterface.TAG_GPS_LATITUDE) == null &&
            exif.getAttribute(ExifInterface.TAG_GPS_LONGITUDE) == null
        val row = JSONObject()
            .put("fixture_id", fixture.getString("fixture_id"))
            .put("intentionally_invalid", fixture.getBoolean("intentionally_invalid"))
            .put("format", fixture.getString("format"))
            .put("size_category", fixture.getString("size_category"))
            .put("input_bytes", input.length())
            .put("output_bytes", result.file.length())
            .put("total_ms", totalMs)
            .put("operation", "android.privacy.total")
            .put("exif_ms", exifMs)
            .put("location_ms", locationMs)
            .put("validation_ms", validationMs)
            .put("integrity_ms", integrityMs)
            .put("redaction_ms", redactionMs)
            .put("encoding_ms", encodingMs)
            .put("success", true)
            .put("failure_category", JSONObject.NULL)
            .put("readable_output", bounds.outWidth > 0 && bounds.outHeight > 0)
            .put("metadata_removed", metadataRemoved)
            .put("gps_removed", gpsRemoved)
            .put("supported_pii_removed", supportedPiiRemoved)
            .put("original_unchanged", input.sha256() == inputHash)
            .put("stages", JSONObject()
                .put("android.privacy.exif", exifMs)
                .put("android.privacy.location", locationMs)
                .put("android.privacy.validation", validationMs)
                .put("android.privacy.integrity", integrityMs)
                .put("android.privacy.redaction", redactionMs)
                .put("android.privacy.encoding", encodingMs)
            )

        result.previewBitmap?.recycle()
        result.file.delete()
        stageCopy.delete()
        input.delete()
        check(!result.file.exists() && !stageCopy.exists() && !input.exists())
        if (!measured) return row
        return row
    }

    private fun failedSample(fixture: JSONObject, totalMs: Double): JSONObject {
        val filename = fixture.getString("filename")
        appContext.cacheDir.listFiles()
            ?.filter { it.name.startsWith("benchmark-") && it.name.endsWith(filename) }
            ?.forEach { it.delete() }
        return JSONObject()
            .put("fixture_id", fixture.getString("fixture_id"))
            .put("intentionally_invalid", fixture.getBoolean("intentionally_invalid"))
            .put("format", fixture.getString("format"))
            .put("size_category", fixture.getString("size_category"))
            .put("input_bytes", fixture.getLong("file_size"))
            .put("output_bytes", 0)
            .put("total_ms", totalMs)
            .put("operation", "android.privacy.total")
            .put("exif_ms", JSONObject.NULL)
            .put("location_ms", JSONObject.NULL)
            .put("validation_ms", JSONObject.NULL)
            .put("integrity_ms", JSONObject.NULL)
            .put("redaction_ms", JSONObject.NULL)
            .put("encoding_ms", JSONObject.NULL)
            .put("success", false)
            .put(
                "failure_category",
                if (fixture.getBoolean("intentionally_invalid")) "invalid_input" else "processing_error",
            )
            .put("readable_output", false)
            .put("metadata_removed", false)
            .put("gps_removed", false)
            .put("supported_pii_removed", false)
            .put("original_unchanged", true)
            .put("stages", JSONObject.NULL)
    }

    private fun buildSummary(samples: List<JSONObject>, manifest: JSONObject): JSONObject {
        val durations = samples.map { it.getDouble("total_ms") }
        val groups = JSONObject()
        samples.groupBy { it.getString("size_category") + ":" + it.getString("format") }
            .forEach { (key, rows) ->
                groups.put(key, stats(rows.map { it.getDouble("total_ms") }))
            }
        return stats(durations)
            .put("sample_count", samples.size)
            .put("success_rate", samples.count { it.getBoolean("success") }.toDouble() / samples.size)
            .put("failure_rate", samples.count { !it.getBoolean("success") }.toDouble() / samples.size)
            .put("fixture_manifest_version", manifest.getInt("manifest_version"))
            .put("warmups", args.getString("warmups")?.toIntOrNull() ?: 5)
            .put("groups", groups)
            .put("device", android.os.Build.MODEL)
            .put("api_level", android.os.Build.VERSION.SDK_INT)
    }

    private fun stats(values: List<Double>): JSONObject {
        val sorted = values.sorted()
        val mean = sorted.average()
        val variance = sorted.sumOf { (it - mean) * (it - mean) } / sorted.size
        return JSONObject()
            .put("mean_ms", mean)
            .put("median_ms", percentile(sorted, 0.5))
            .put("p95_ms", percentile(sorted, 0.95))
            .put("min_ms", sorted.first())
            .put("max_ms", sorted.last())
            .put("stddev_ms", sqrt(variance))
            .put("percentile_method", "linear interpolation at rank (n - 1) * p")
    }

    private fun percentile(sorted: List<Double>, probability: Double): Double {
        if (sorted.size == 1) return sorted.first()
        val rank = (sorted.size - 1) * probability
        val lower = rank.toInt()
        val upper = ceil(rank).toInt()
        if (lower == upper) return sorted[lower]
        return sorted[lower] + (sorted[upper] - sorted[lower]) * (rank - lower)
    }

    private fun readAsset(path: String): String =
        testContext.assets.open(path).bufferedReader().use { it.readText() }

    private fun copyAsset(path: String): File {
        val destination = File(appContext.cacheDir, "benchmark-" + System.nanoTime() + "-" + path.substringAfterLast('/'))
        testContext.assets.open(path).use { input ->
            destination.outputStream().use { output -> input.copyTo(output) }
        }
        return destination
    }

    private fun elapsedMs(startedNanos: Long): Double =
        (SystemClock.elapsedRealtimeNanos() - startedNanos) / 1_000_000.0

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).map { getJSONObject(it) }

    private fun File.sha256(): String {
        val digest = MessageDigest.getInstance("SHA-256")
        inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
