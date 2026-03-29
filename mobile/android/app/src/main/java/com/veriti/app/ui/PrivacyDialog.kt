package com.veriti.app.ui

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.compose.ui.res.stringResource
import com.veriti.app.R
import com.veriti.app.ui.theme.VeritiBlue
import com.veriti.app.ui.theme.VeritiSurface
import com.veriti.app.ui.theme.VeritiTextPrimary
import com.veriti.app.ui.theme.VeritiTextSecondary

@Composable
fun PrivacyDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = {},
        containerColor = VeritiSurface,
        titleContentColor = VeritiTextPrimary,
        textContentColor = VeritiTextSecondary,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text(
                    text = stringResource(id = R.string.privacy_dialog_button),
                    color = VeritiBlue,
                )
            }
        },
        title = {
            Text(
                text = stringResource(id = R.string.privacy_dialog_title),
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Text(
                text = stringResource(id = R.string.privacy_dialog_body),
                fontSize = 13.sp,
            )
        },
    )
}
