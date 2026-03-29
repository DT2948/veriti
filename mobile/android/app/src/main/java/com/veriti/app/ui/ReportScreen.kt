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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.VideoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import java.util.UUID

private data class IncidentTypeOption(
    val label: String,
    val value: String,
)

private val incidentTypes = listOf(
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

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
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
            title = { Text("Duplicate Submission Blocked") },
            text = { Text("You already submitted this image during this session.") },
            confirmButton = {
                TextButton(onClick = { showDuplicateDialog = false }) {
                    Text("OK")
                }
            },
        )
    }

    if (showFailureDialog) {
        AlertDialog(
            onDismissRequest = { showFailureDialog = false },
            title = { Text("Submission Failed") },
            text = {
                Text("Could not reach the server. Please check your connection and try again.")
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
                    Text("Retry")
                }
            },
            dismissButton = {
                TextButton(onClick = { showFailureDialog = false }) {
                    Text("Cancel")
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
            CenterAlignedTopAppBar(
                title = { Text("Veriti") },
                navigationIcon = {
                    Icon(
                        imageVector = Icons.Outlined.Shield,
                        contentDescription = null,
                        modifier = Modifier.padding(start = 16.dp),
                    )
                },
            )
        },
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Card(
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer,
                    ),
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        Text(
                            text = "Report Incident",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "Capture or select evidence. Veriti sanitizes media locally before anything leaves your device.",
                            style = MaterialTheme.typography.bodyMedium,
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
                                modifier = Modifier.weight(1f),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.PhotoCamera,
                                    contentDescription = null,
                                )
                                Text(
                                    text = "Take Photo",
                                    modifier = Modifier.padding(start = 8.dp),
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
                                modifier = Modifier.weight(1f),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.VideoLibrary,
                                    contentDescription = null,
                                )
                                Text(
                                    text = "Choose from Gallery",
                                    modifier = Modifier.padding(start = 8.dp),
                                )
                            }
                        }
                    }
                }

                previewBitmap?.let { bitmap ->
                    Card(shape = RoundedCornerShape(20.dp)) {
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

                OutlinedTextField(
                    value = noteText,
                    onValueChange = { noteText = it.take(500) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("What did you observe? (optional)") },
                    placeholder = { Text("Keep it factual. Personal details will be removed locally.") },
                    minLines = 3,
                )

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "Incident type",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        incidentTypes.forEach { type ->
                            FilterChip(
                                selected = selectedIncidentType == type,
                                onClick = { selectedIncidentType = type },
                                label = { Text(type.label) },
                            )
                        }
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
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(imageVector = Icons.Outlined.Security, contentDescription = null)
                    Text(
                        text = if (cooldownRemaining > 0) {
                            "Submit again in ${cooldownRemaining}s..."
                        } else {
                            "Submit Report Anonymously"
                        },
                        modifier = Modifier.padding(start = 8.dp),
                    )
                }

                if (isUploading) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        LinearProgressIndicator(progress = uploadProgress, modifier = Modifier.fillMaxWidth())
                        Text(
                            text = "Uploading sanitized report... ${(uploadProgress * 100).toInt()}%",
                            style = MaterialTheme.typography.bodySmall,
                        )
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
        title = { Text(prompt.title) },
        text = { Text(prompt.message) },
        confirmButton = {
            TextButton(onClick = onContinue) {
                Text("Continue")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        },
    )
}

@Composable
private fun StatusCard(
    message: String,
) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "Submission Status",
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun SuccessOverlay(onDone: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.45f)),
        contentAlignment = Alignment.Center,
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            shape = RoundedCornerShape(28.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Icon(
                    imageVector = Icons.Filled.CheckCircle,
                    contentDescription = null,
                    tint = Color(0xFF1FA25C),
                    modifier = Modifier.height(72.dp),
                )
                Text(
                    text = "Report Submitted Anonymously ✅",
                    style = MaterialTheme.typography.headlineSmall,
                    textAlign = TextAlign.Center,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "Your report has been received and will be verified against other independent reports.",
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = "All identifying metadata was stripped before upload.",
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                )
                Button(onClick = onDone, modifier = Modifier.fillMaxWidth()) {
                    Text("Done")
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
