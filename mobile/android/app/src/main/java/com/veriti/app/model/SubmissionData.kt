package com.veriti.app.model

import java.io.File

data class SubmissionData(
    val file: File,
    val mediaType: String,
    val textNote: String,
    val latitude: Double,
    val longitude: Double,
    val deviceTrustScore: Float,
    val integrityToken: String,
    val incidentType: String,
)
