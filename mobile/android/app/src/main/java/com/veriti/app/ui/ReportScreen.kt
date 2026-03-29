package com.veriti.app.ui

import android.Manifest
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.VerifiedUser
import androidx.compose.material.icons.outlined.VideoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.veriti.app.model.PipelineState
import com.veriti.app.model.PipelineStepState
import com.veriti.app.model.StepStatus
import com.veriti.app.model.SubmissionData
import com.veriti.app.network.ApiClient
import com.veriti.app.network.UploadResult
import com.veriti.app.pipeline.LocalPipeline
import com.veriti.app.pipeline.LocalProcessingResult
import com.veriti.app.pipeline.TextSanitizer
import com.veriti.app.ui.theme.VeritiBackground
import com.veriti.app.ui.theme.VeritiAccentSubtle
import com.veriti.app.ui.theme.VeritiBlue
import com.veriti.app.ui.theme.VeritiBluePressed
import com.veriti.app.ui.theme.VeritiBorder
import com.veriti.app.ui.theme.VeritiDanger
import com.veriti.app.ui.theme.VeritiPanel
import com.veriti.app.ui.theme.VeritiSuccess
import com.veriti.app.ui.theme.VeritiSurface
import com.veriti.app.ui.theme.VeritiSurfaceElevated
import com.veriti.app.ui.theme.VeritiTextMuted
import com.veriti.app.ui.theme.VeritiTextPrimary
import com.veriti.app.ui.theme.VeritiTextSecondary
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import java.util.UUID

private data class IncidentTypeOption(
    val label: String,
    val value: String,
)

private val incidentTypes = listOf(
    IncidentTypeOption("Drone-related", "drone"),
    IncidentTypeOption("Explosion", "explosion"),
    IncidentTypeOption("Debris", "debris"),
    IncidentTypeOption("Siren/Warning", "warning"),
    IncidentTypeOption("Missile-related", "missile"),
    IncidentTypeOption("Structural Damage", "unknown"),
    IncidentTypeOption("Other", "unknown"),
)

private val defaultIncidentType = incidentTypes.last()

private enum class MediaAction {
    Camera,
    Gallery,
}

private data class PermissionPrompt(
    val title: String,
    val message: String,
    val permissions: List<String>,
    val action: MediaAction,
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ReportScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val apiClient = remember { ApiClient() }
    val sanitizer = remember { TextSanitizer() }
    val sessionToken = remember { UUID.randomUUID().toString() }
    val sessionHashes = remember { mutableSetOf<String>() }
    val pipeline = remember(context) { LocalPipeline(context, sessionHashes) }

    var noteText by remember { mutableStateOf("") }
    var selectedIncidentType by remember { mutableStateOf(defaultIncidentType) }
    var previewBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var pipelineState by remember { mutableStateOf(PipelineState.idle()) }
    var processedMedia by remember { mutableStateOf<LocalProcessingResult?>(null) }
    var statusMessage by remember { mutableStateOf("No report has been prepared yet.") }
    var uploadProgress by remember { mutableFloatStateOf(0f) }
    var isUploading by remember { mutableStateOf(false) }
    var showPrivacyDialog by remember { mutableStateOf(true) }
    var permissionPrompt by remember { mutableStateOf<PermissionPrompt?>(null) }
    var pendingRetry by remember { mutableStateOf<SubmissionData?>(null) }
    var currentCameraUri by remember { mutableStateOf<Uri?>(null) }
    var launchGrantedAction by remember { mutableStateOf<(() -> Unit)?>(null) }
    var showSuccessOverlay by remember { mutableStateOf(false) }
    var showFailureDialog by remember { mutableStateOf(false) }
    var showDuplicateDialog by remember { mutableStateOf(false) }
    var cooldownRemaining by remember { mutableStateOf(0) }
    var pendingSubmittedHash by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(cooldownRemaining) {
        if (cooldownRemaining > 0) {
            delay(1000)
            cooldownRemaining -= 1
        }
    }

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri != null) {
            processSelectedMedia(
                uri = uri,
                pipeline = pipeline,
                onPipelineState = { pipelineState = it },
                onSuccess = {
                    processedMedia = it
                    previewBitmap = it.previewBitmap
                    pendingRetry = null
                    statusMessage = it.duplicateWarning
                        ?: "All local checks passed. Your data is sanitized."
                },
                onFailure = {
                    processedMedia = null
                    previewBitmap = null
                    pipelineState = pipelineFailureState(pipelineState, it)
                    statusMessage = it
                },
                scope = scope,
            )
        }
    }

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture(),
    ) { success ->
        if (success) {
            currentCameraUri?.let { uri ->
                processSelectedMedia(
                    uri = uri,
                    pipeline = pipeline,
                    onPipelineState = { pipelineState = it },
                    onSuccess = {
                        processedMedia = it
                        previewBitmap = it.previewBitmap
                        pendingRetry = null
                        statusMessage = it.duplicateWarning
                            ?: "All local checks passed. Your data is sanitized."
                    },
                    onFailure = {
                        processedMedia = null
                        previewBitmap = null
                        pipelineState = pipelineFailureState(pipelineState, it)
                        statusMessage = it
                    },
                    scope = scope,
                )
            }
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
    ) { permissions ->
        val granted = permissionPrompt?.permissions?.all { permissions[it] == true } == true
        if (granted) {
            launchGrantedAction?.invoke()
        } else {
            statusMessage = "Required permission was denied. Veriti only needs camera, gallery, and approximate location for this report."
        }
        permissionPrompt = null
    }

    if (showPrivacyDialog) {
        PrivacyDialog(onDismiss = { showPrivacyDialog = false })
    }

    if (showDuplicateDialog) {
        AlertDialog(
            onDismissRequest = { showDuplicateDialog = false },
            containerColor = VeritiSurface,
            titleContentColor = VeritiTextPrimary,
            textContentColor = VeritiTextSecondary,
            title = {
                Text(
                    "Duplicate Submission Blocked",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
            },
            text = {
                Text(
                    "You already submitted this image during this session.",
                    fontSize = 13.sp,
                )
            },
            confirmButton = {
                TextButton(onClick = { showDuplicateDialog = false }) {
                    Text("OK", color = VeritiBlue)
                }
            },
        )
    }

    if (showFailureDialog) {
        AlertDialog(
            onDismissRequest = { showFailureDialog = false },
            containerColor = VeritiSurface,
            titleContentColor = VeritiTextPrimary,
            textContentColor = VeritiTextSecondary,
            title = {
                Text(
                    "Submission Failed",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
            },
            text = {
                Text(
                    "Could not reach the server. Please check your connection and try again.",
                    fontSize = 13.sp,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val cached = pendingRetry
                        if (cached != null) {
                            showFailureDialog = false
                            submitPreparedData(
                                apiClient = apiClient,
                                submission = cached,
                                onProgress = {
                                    isUploading = true
                                    uploadProgress = it
                                },
                                onFinished = { result ->
                                    isUploading = false
                                    when (result) {
                                        is UploadResult.Success -> {
                                            pendingRetry = null
                                            pendingSubmittedHash?.let { pipeline.markSubmittedHash(it) }
                                            cooldownRemaining = 60
                                            showSuccessOverlay = true
                                            statusMessage = "Report submitted anonymously."
                                        }
                                        is UploadResult.Failure -> {
                                            pendingRetry = cached
                                            showFailureDialog = true
                                            statusMessage = "Submission failed."
                                        }
                                        is UploadResult.Timeout -> {
                                            pendingRetry = cached
                                            showFailureDialog = true
                                            statusMessage = result.message
                                        }
                                    }
                                },
                                scope = scope,
                            )
                        }
                    }
                ) {
                    Text("Retry", color = VeritiBlue)
                }
            },
            dismissButton = {
                TextButton(onClick = { showFailureDialog = false }) {
                    Text("Cancel", color = VeritiTextMuted)
                }
            },
        )
    }

    permissionPrompt?.let { prompt ->
        PermissionExplanationDialog(
            prompt = prompt,
            onDismiss = { permissionPrompt = null },
            onContinue = {
                launchGrantedAction = when (prompt.action) {
                    MediaAction.Camera -> {
                        {
                            val captureUri = createCameraUri(context, sessionToken)
                            currentCameraUri = captureUri
                            cameraLauncher.launch(captureUri)
                        }
                    }
                    MediaAction.Gallery -> {
                        { galleryLauncher.launch(arrayOf("image/*", "video/*")) }
                    }
                }
                permissionLauncher.launch(prompt.permissions.toTypedArray())
            },
        )
    }

    Scaffold(
        topBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(VeritiBackground)
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.Shield,
                        contentDescription = null,
                        tint = VeritiTextPrimary,
                        modifier = Modifier.size(18.dp),
                    )
                    Text(
                        text = "VERITI",
                        color = VeritiTextPrimary,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 2.sp,
                        modifier = Modifier.padding(start = 8.dp),
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(RoundedCornerShape(999.dp))
                            .background(VeritiSuccess),
                    )
                    Text(
                        text = "SECURE",
                        color = VeritiTextMuted,
                        fontSize = 12.sp,
                        letterSpacing = 1.sp,
                        modifier = Modifier.padding(start = 6.dp),
                    )
                }
            }
        },
        containerColor = VeritiBackground,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(VeritiBackground)
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .navigationBarsPadding(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (isUploading) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        LinearProgressIndicator(
                            progress = { uploadProgress },
                            modifier = Modifier.fillMaxWidth(),
                            color = VeritiBlue,
                            trackColor = VeritiBorder,
                        )
                        Text(
                            text = "Uploading sanitized report... ${(uploadProgress * 100).toInt()}%",
                            style = MaterialTheme.typography.bodySmall,
                            color = VeritiTextMuted,
                        )
                    }
                }

                Button(
                    onClick = {
                        val prepared = processedMedia ?: return@Button
                        if (pipeline.hasSubmittedHash(prepared.sha256)) {
                            showDuplicateDialog = true
                            statusMessage = "This media was already submitted during this session."
                            return@Button
                        }

                        val submission = SubmissionData(
                            file = prepared.file,
                            mediaType = prepared.mediaType,
                            textNote = sanitizer.sanitize(noteText),
                            latitude = prepared.latitude,
                            longitude = prepared.longitude,
                            deviceTrustScore = prepared.deviceTrustScore,
                            integrityToken = prepared.integrityToken,
                            incidentType = selectedIncidentType.value,
                        )
                        submitPreparedData(
                            apiClient = apiClient,
                            submission = submission,
                            onProgress = {
                                isUploading = true
                                uploadProgress = it
                            },
                            onFinished = { result ->
                                isUploading = false
                                when (result) {
                                    is UploadResult.Success -> {
                                        pendingRetry = null
                                        pipeline.markSubmittedHash(prepared.sha256)
                                        pendingSubmittedHash = null
                                        cooldownRemaining = 60
                                        showSuccessOverlay = true
                                        statusMessage = "Report submitted anonymously."
                                    }
                                    is UploadResult.Failure -> {
                                        pendingRetry = submission
                                        pendingSubmittedHash = prepared.sha256
                                        showFailureDialog = true
                                        statusMessage = "Submission failed."
                                    }
                                    is UploadResult.Timeout -> {
                                        pendingRetry = submission
                                        pendingSubmittedHash = prepared.sha256
                                        showFailureDialog = true
                                        statusMessage = result.message
                                    }
                                }
                            },
                            scope = scope,
                        )
                    },
                    enabled = pipelineState.isReadyForUpload &&
                        processedMedia != null &&
                        !isUploading &&
                        cooldownRemaining == 0,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = VeritiBlue,
                        contentColor = VeritiTextPrimary,
                        disabledContainerColor = VeritiSurface,
                        disabledContentColor = VeritiTextMuted,
                    ),
                ) {
                    if (isUploading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            color = VeritiTextPrimary,
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text(
                            text = if (cooldownRemaining > 0) {
                                "Submit again in ${cooldownRemaining}s..."
                            } else {
                                "Submit Anonymous Report"
                            },
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
        },
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 16.dp, top = 12.dp, end = 16.dp, bottom = 8.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Card(
                    shape = RoundedCornerShape(8.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color.Transparent,
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
                ) {
                    Column(
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        Text(
                            text = "CAPTURE EVIDENCE",
                            fontSize = 13.sp,
                            color = VeritiTextMuted,
                            letterSpacing = 1.5.sp,
                            fontWeight = FontWeight.Medium,
                        )
                        Text(
                            text = "Capture or select media. Sanitization happens locally before upload.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = VeritiTextSecondary,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Button(
                                onClick = {
                                    permissionPrompt = PermissionPrompt(
                                        title = "Camera access",
                                        message = "To capture incident evidence and determine your approximate area only.",
                                        permissions = cameraPermissions(),
                                        action = MediaAction.Camera,
                                    )
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .height(52.dp),
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = VeritiSurfaceElevated,
                                    contentColor = VeritiTextPrimary,
                                    disabledContainerColor = VeritiBorder,
                                    disabledContentColor = VeritiTextMuted,
                                ),
                                border = androidx.compose.foundation.BorderStroke(1.dp, VeritiBorder),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.PhotoCamera,
                                    contentDescription = null,
                                    tint = VeritiBlue,
                                    modifier = Modifier.size(18.dp),
                                )
                                Text(
                                    text = "Take Photo",
                                    modifier = Modifier.padding(start = 8.dp),
                                    color = VeritiTextPrimary,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Medium,
                                )
                            }
                            Button(
                                onClick = {
                                    permissionPrompt = PermissionPrompt(
                                        title = "Gallery access",
                                        message = "To choose incident evidence from your library and determine your approximate area only.",
                                        permissions = galleryPermissions(),
                                        action = MediaAction.Gallery,
                                    )
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .height(52.dp),
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = VeritiSurfaceElevated,
                                    contentColor = VeritiTextPrimary,
                                    disabledContainerColor = VeritiBorder,
                                    disabledContentColor = VeritiTextMuted,
                                ),
                                border = androidx.compose.foundation.BorderStroke(1.dp, VeritiBorder),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.VideoLibrary,
                                    contentDescription = null,
                                    tint = VeritiBlue,
                                    modifier = Modifier.size(18.dp),
                                )
                                Text(
                                    text = "Choose Gallery",
                                    modifier = Modifier.padding(start = 8.dp),
                                    color = VeritiTextPrimary,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Medium,
                                )
                            }
                        }
                    }
                }

                previewBitmap?.let { bitmap ->
                    Card(
                        shape = RoundedCornerShape(8.dp),
                        colors = CardDefaults.cardColors(containerColor = VeritiSurface),
                    ) {
                        Image(
                            bitmap = bitmap.asImageBitmap(),
                            contentDescription = "Selected media preview",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(220.dp),
                        )
                    }
                }

                PrivacyStatusCard(state = pipelineState)

                TextField(
                    value = noteText,
                    onValueChange = { noteText = it.take(500) },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = TextStyle(color = VeritiTextPrimary, fontSize = 14.sp),
                    placeholder = {
                        Text(
                            "What did you observe?",
                            color = VeritiTextMuted,
                            fontSize = 14.sp,
                        )
                    },
                    supportingText = {
                        Text(
                            "Optional - Personal details auto-removed",
                            color = VeritiTextMuted,
                            fontSize = 12.sp,
                        )
                    },
                    minLines = 3,
                    maxLines = 3,
                    shape = RoundedCornerShape(8.dp),
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = VeritiPanel,
                        unfocusedContainerColor = VeritiPanel,
                        disabledContainerColor = VeritiPanel,
                        focusedIndicatorColor = VeritiBlue,
                        unfocusedIndicatorColor = Color.Transparent,
                        disabledIndicatorColor = Color.Transparent,
                        focusedTextColor = VeritiTextPrimary,
                        unfocusedTextColor = VeritiTextPrimary,
                        cursorColor = VeritiBlue,
                        focusedSupportingTextColor = VeritiTextMuted,
                        unfocusedSupportingTextColor = VeritiTextMuted,
                    ),
                )

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "INCIDENT TYPE",
                        fontSize = 13.sp,
                        color = VeritiTextMuted,
                        letterSpacing = 1.5.sp,
                        fontWeight = FontWeight.Medium,
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        incidentTypes.forEach { type ->
                            FilterChip(
                                selected = selectedIncidentType == type,
                                onClick = { selectedIncidentType = type },
                                label = {
                                    Text(
                                        type.label,
                                        fontSize = 14.sp,
                                        color = if (selectedIncidentType == type) VeritiBluePressed else VeritiTextSecondary,
                                    )
                                },
                                shape = RoundedCornerShape(20.dp),
                                border = FilterChipDefaults.filterChipBorder(
                                    enabled = true,
                                    selected = selectedIncidentType == type,
                                    borderColor = VeritiBorder,
                                    selectedBorderColor = VeritiBlue,
                                ),
                                colors = FilterChipDefaults.filterChipColors(
                                    containerColor = VeritiPanel,
                                    labelColor = VeritiTextSecondary,
                                    selectedContainerColor = VeritiAccentSubtle,
                                    selectedLabelColor = VeritiBluePressed,
                                ),
                            )
                        }
                    }
                }

                StatusCard(message = statusMessage)
            }

            if (showSuccessOverlay) {
                SuccessOverlay(
                    onDone = {
                        showSuccessOverlay = false
                        processedMedia = null
                        previewBitmap = null
                        noteText = ""
                        selectedIncidentType = defaultIncidentType
                        pendingRetry = null
                        pendingSubmittedHash = null
                        uploadProgress = 0f
                        pipelineState = PipelineState.idle()
                        statusMessage = "Ready for another anonymous report."
                    }
                )
            }
        }
    }
}

@Composable
private fun PermissionExplanationDialog(
    prompt: PermissionPrompt,
    onDismiss: () -> Unit,
    onContinue: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = VeritiSurface,
        titleContentColor = VeritiTextPrimary,
        textContentColor = VeritiTextSecondary,
        title = {
            Text(
                text = prompt.title,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Text(
                text = prompt.message,
                fontSize = 13.sp,
            )
        },
        confirmButton = {
            TextButton(onClick = onContinue) {
                Text("Continue", color = VeritiBlue)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = VeritiTextMuted)
            }
        },
    )
}

@Composable
private fun StatusCard(
    message: String,
) {
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = VeritiSurface,
        ),
        border = androidx.compose.foundation.BorderStroke(1.dp, VeritiBorder),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = "Submission Status",
                color = VeritiTextMuted,
                fontSize = 12.sp,
                letterSpacing = 1.5.sp,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = VeritiTextSecondary,
            )
        }
    }
}

@Composable
private fun SuccessOverlay(onDone: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(VeritiBackground.copy(alpha = 0.72f)),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            shape = RoundedCornerShape(12.dp),
            color = VeritiSurface,
            border = androidx.compose.foundation.BorderStroke(1.dp, VeritiBorder),
        ) {
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Icon(
                    imageVector = Icons.Outlined.VerifiedUser,
                    contentDescription = null,
                    tint = VeritiSuccess,
                    modifier = Modifier.size(32.dp),
                )
                Text(
                    text = "Report Submitted",
                    color = VeritiTextPrimary,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = "Your anonymous report is being verified.",
                    color = VeritiTextSecondary,
                    fontSize = 13.sp,
                    textAlign = TextAlign.Center,
                )
                TextButton(onClick = onDone) {
                    Text("Dismiss", color = VeritiBlue)
                }
            }
        }
    }
}

private fun processSelectedMedia(
    uri: Uri,
    pipeline: LocalPipeline,
    onPipelineState: (PipelineState) -> Unit,
    onSuccess: (LocalProcessingResult) -> Unit,
    onFailure: (String) -> Unit,
    scope: kotlinx.coroutines.CoroutineScope,
) {
    scope.launch {
        pipeline.process(uri, onPipelineState)
            .onSuccess(onSuccess)
            .onFailure { exception ->
                onFailure(exception.message ?: "Local processing failed.")
            }
    }
}

private fun submitPreparedData(
    apiClient: ApiClient,
    submission: SubmissionData,
    onProgress: (Float) -> Unit,
    onFinished: (UploadResult) -> Unit,
    scope: kotlinx.coroutines.CoroutineScope,
) {
    scope.launch {
        onFinished(apiClient.uploadSubmission(submission, onProgress))
    }
}

private fun pipelineFailureState(
    current: PipelineState,
    message: String,
): PipelineState {
    return when {
        current.metadata.status == StepStatus.Pending -> {
            current.copy(
                metadata = PipelineStepState(StepStatus.Error, message),
                isRunning = false,
                isReadyForUpload = false,
                statusMessage = message,
            )
        }
        current.location.status == StepStatus.Pending -> {
            current.copy(
                location = PipelineStepState(StepStatus.Error, message),
                isRunning = false,
                isReadyForUpload = false,
                statusMessage = message,
            )
        }
        current.mediaValidation.status == StepStatus.Pending -> {
            current.copy(
                mediaValidation = PipelineStepState(StepStatus.Error, message),
                isRunning = false,
                isReadyForUpload = false,
                statusMessage = message,
            )
        }
        else -> {
            current.copy(
                integrity = PipelineStepState(StepStatus.Warning, message),
                isRunning = false,
                isReadyForUpload = false,
                statusMessage = message,
            )
        }
    }
}

private fun createCameraUri(context: Context, sessionToken: String): Uri {
    val cameraDir = File(context.cacheDir, "camera").apply { mkdirs() }
    val file = File(cameraDir, "veriti_${sessionToken.take(8)}_${System.currentTimeMillis()}.jpg")
    return FileProvider.getUriForFile(
        context,
        "${context.packageName}.fileprovider",
        file,
    )
}

private fun cameraPermissions(): List<String> = buildList {
    add(Manifest.permission.CAMERA)
    add(Manifest.permission.ACCESS_COARSE_LOCATION)
}

private fun galleryPermissions(): List<String> = buildList {
    add(Manifest.permission.ACCESS_COARSE_LOCATION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        add(Manifest.permission.READ_MEDIA_IMAGES)
        add(Manifest.permission.READ_MEDIA_VIDEO)
    } else {
        add(Manifest.permission.READ_EXTERNAL_STORAGE)
    }
}
