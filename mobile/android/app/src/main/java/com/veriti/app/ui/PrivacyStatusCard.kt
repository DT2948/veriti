package com.veriti.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.GppGood
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.veriti.app.model.PipelineState
import com.veriti.app.model.PipelineStepState
import com.veriti.app.model.StepStatus

@Composable
fun PrivacyStatusCard(
    state: PipelineState,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Outlined.GppGood,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = "Privacy Verification",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(start = 10.dp),
                )
            }

            PrivacyStepLine(
                label = "Metadata stripped from media",
                step = state.metadata,
            )
            PrivacyStepLine(
                label = "Location coarsened (~500m)",
                step = state.location,
            )
            PrivacyStepLine(
                label = "Media validated locally",
                step = state.mediaValidation,
            )
            PrivacyStepLine(
                label = if (state.integrity.status == StepStatus.Warning) {
                    "Device integrity unavailable"
                } else {
                    "Device integrity verified"
                },
                step = state.integrity,
            )

            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Your identity is not collected.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                text = "Only sanitized data is uploaded.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun PrivacyStepLine(
    label: String,
    step: PipelineStepState,
) {
    AnimatedVisibility(
        visible = step.status != StepStatus.Pending,
        enter = fadeIn(),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Text(
                text = when (step.status) {
                    StepStatus.Success -> "✅"
                    StepStatus.Warning -> "⚠️"
                    StepStatus.Error -> "❌"
                    StepStatus.Pending -> ""
                },
                modifier = Modifier.padding(end = 8.dp),
            )
            Column {
                Text(text = label, style = MaterialTheme.typography.bodyMedium)
                if (step.detail.isNotBlank()) {
                    Text(
                        text = step.detail,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.75f),
                    )
                }
            }
        }
    }
}
