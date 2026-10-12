from pathlib import Path

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator


class SyllabusUploadForm(forms.Form):
    file = forms.FileField(
        label="Syllabus file",
        max_length=255,
        help_text="Upload a PDF or UTF-8 TXT file, up to 5 MB.",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "txt"],
                message="Please upload a PDF or TXT file.",
            ),
        ],
        widget=forms.ClearableFileInput(
            attrs={"accept": ".pdf,.txt"}
        ),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]

        if uploaded_file.size > settings.SYLLABUS_MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                "The file must be 5 MB or smaller."
            )

        extension = Path(uploaded_file.name).suffix.lower()

        try:
            uploaded_file.seek(0)

            if extension == ".pdf":
                if uploaded_file.read(5) != b"%PDF-":
                    raise forms.ValidationError(
                        "The file does not have a PDF header."
                    )
            else:
                try:
                    text = uploaded_file.read().decode("utf-8-sig")
                except UnicodeDecodeError:
                    raise forms.ValidationError(
                        "The TXT file must use UTF-8 encoding."
                    ) from None

                if "\x00" in text:
                    raise forms.ValidationError(
                        "The TXT file contains unsupported binary content."
                    )

                if not text.strip():
                    raise forms.ValidationError(
                        "The TXT file must contain text."
                    )
        finally:
            uploaded_file.seek(0)

        return uploaded_file