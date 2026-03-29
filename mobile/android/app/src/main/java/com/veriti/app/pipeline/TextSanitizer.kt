package com.veriti.app.pipeline

class TextSanitizer {
    private val emailRegex =
        Regex("""\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b""")
    private val phoneRegex =
        Regex("""(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\d[\s-]?){8,14}\d""")
    private val nameRegex =
        Regex("""(?i)\bmy name is\s+[a-z]+(?:\s+[a-z]+){0,2}\b""")

    fun sanitize(input: String): String {
        return input
            .replace(emailRegex, "[redacted-email]")
            .replace(phoneRegex, "[redacted-phone]")
            .replace(nameRegex, "my name is [redacted]")
            .trim()
            .take(500)
    }
}
