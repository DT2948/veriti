package com.veriti.app.ui

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.veriti.app.R

@Composable
fun PrivacyDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = {},
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text(text = stringResource(id = R.string.privacy_dialog_button))
            }
        },
        title = { Text(text = stringResource(id = R.string.privacy_dialog_title)) },
        text = { Text(text = stringResource(id = R.string.privacy_dialog_body)) },
    )
}
