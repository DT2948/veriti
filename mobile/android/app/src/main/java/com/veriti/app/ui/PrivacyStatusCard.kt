package com.veriti.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.GppGood
import androidx.compose.material.icons.outlined.HourglassEmpty
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.veriti.app.model.PipelineState
import com.veriti.app.model.PipelineStepState
import com.veriti.app.model.StepStatus
import com.veriti.app.ui.theme.VeritiBorder
import com.veriti.app.ui.theme.VeritiDanger
import com.veriti.app.ui.theme.VeritiSuccess
import com.veriti.app.ui.theme.VeritiSurfaceElevated
import com.veriti.app.ui.theme.VeritiTextMuted
import com.veriti.app.ui.theme.VeritiTextPrimary
import com.veriti.app.ui.theme.VeritiTextSecondary
import com.veriti.app.ui.theme.VeritiWarning

@Composable
fun PrivacyStatusCard(
    state: PipelineState,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Outlined.GppGood,
                contentDescription = null,
                tint = VeritiSuccess,
                modifier = Modifier.padding(end = 8.dp),
            )
            Text(
                text = "Identity protected - Data sanitized locally",
                color = VeritiTextMuted,
                fontSize = 12.sp,
                fontWeight = FontWeight.Normal,
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(VeritiSurfaceElevated)
                .padding(horizontal = 10.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            PrivacyStepLine("Metadata stripped from media", state.metadata)
            PrivacyStepLine("Location coarsened (~500m)", state.location)
            PrivacyStepLine("Media validated locally", state.mediaValidation)
            PrivacyStepLine(
                if (state.integrity.status == StepStatus.Warning) {
                    "Device integrity unavailable"
                } else {
                    "Device integrity verified"
                },
                state.integrity,
            )
        }
    }
}

@Composable
private fun PrivacyStepLine(
    label: String,
    step: PipelineStepState,
) {
    val (icon, tint) = when (step.status) {
        StepStatus.Success -> Icons.Outlined.GppGood to VeritiSuccess
        StepStatus.Warning -> Icons.Outlined.WarningAmber to VeritiWarning
        StepStatus.Error -> Icons.Outlined.ErrorOutline to VeritiDanger
        StepStatus.Pending -> Icons.Outlined.HourglassEmpty to VeritiTextMuted
    }

    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
    ) {
        StatusGlyph(icon = icon, tint = tint, pending = step.status == StepStatus.Pending)
        Column(
            modifier = Modifier
                .padding(start = 10.dp)
                .weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text(
                text = label,
                color = VeritiTextPrimary,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
            if (step.detail.isNotBlank()) {
                Text(
                    text = step.detail,
                    color = VeritiTextSecondary,
                    fontSize = 12.sp,
                )
            }
        }
    }
}

@Composable
private fun StatusGlyph(
    icon: ImageVector,
    tint: Color,
    pending: Boolean,
) {
    Row(
        modifier = Modifier
            .size(20.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(if (pending) VeritiBorder else tint.copy(alpha = 0.15f)),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = tint,
            modifier = Modifier.size(12.dp),
        )
    }
}
