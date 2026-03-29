package com.veriti.app.model

enum class StepStatus {
    Pending,
    Success,
    Warning,
    Error,
}

data class PipelineStepState(
    val status: StepStatus = StepStatus.Pending,
    val detail: String = "",
)

data class PipelineState(
    val metadata: PipelineStepState = PipelineStepState(),
    val location: PipelineStepState = PipelineStepState(),
    val mediaValidation: PipelineStepState = PipelineStepState(),
    val integrity: PipelineStepState = PipelineStepState(),
    val isRunning: Boolean = false,
    val isReadyForUpload: Boolean = false,
    val statusMessage: String = "",
) {
    companion object {
        fun idle() = PipelineState(
            statusMessage = "Choose media to begin local privacy verification."
        )
    }
}
