package com.veriti.app.pipeline

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.tasks.await
import kotlin.math.round

data class CoarsenedLocation(
    val latitude: Double,
    val longitude: Double,
)

class LocationCoarsener(private val context: Context) {
    suspend fun getCoarsenedLocation(): CoarsenedLocation {
        val permissionState = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        require(permissionState == PackageManager.PERMISSION_GRANTED) {
            "Approximate location permission is required."
        }

        val location = LocationServices.getFusedLocationProviderClient(context)
            .getCurrentLocation(Priority.PRIORITY_BALANCED_POWER_ACCURACY, null)
            .await()
            ?: throw IllegalStateException("Could not obtain approximate location.")

        val coarsenedLat = round(location.latitude / 0.0045) * 0.0045
        val coarsenedLng = round(location.longitude / 0.0045) * 0.0045
        return CoarsenedLocation(
            latitude = coarsenedLat,
            longitude = coarsenedLng,
        )
    }
}
