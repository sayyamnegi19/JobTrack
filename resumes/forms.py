from django import forms

from applications.models import JobApplication

from . import parsers
from .models import Resume


class ResumeAnalysisForm(forms.Form):
    """
    One-stop form for a resume analysis attempt.

    The user provides exactly one resume source (saved, uploaded, or pasted)
    and any combination of optional job context. A pasted job description
    takes priority over a link; a link is only fetched when no description
    was pasted.
    """

    resume_choice = forms.ModelChoiceField(
        queryset=Resume.objects.none(),
        required=False,
        label="Use a saved resume",
        empty_label="— Upload or paste a new resume —",
    )

    resume_file = forms.FileField(
        required=False,
        label="Upload a file",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.docx,.txt"}),
        help_text="PDF, DOCX or TXT, up to 5 MB.",
    )

    resume_text = forms.CharField(
        required=False,
        label="Paste resume text",
        widget=forms.Textarea(
            attrs={"rows": 6, "placeholder": "Paste your resume here…"}
        ),
    )

    job_application = forms.ModelChoiceField(
        queryset=JobApplication.objects.none(),
        required=False,
        label="Link a tracked application",
        empty_label="— Not linked —",
    )

    job_url = forms.URLField(
        required=False,
        label="Job link",
        widget=forms.URLInput(attrs={"placeholder": "https://…"}),
        help_text=(
            "We fetch and read this page. Ignored when a description is "
            "pasted below."
        ),
    )

    job_description = forms.CharField(
        required=False,
        label="Paste the job description",
        widget=forms.Textarea(
            attrs={"rows": 6, "placeholder": "Paste the job description here…"}
        ),
        help_text="Takes priority over the link — use this when a site blocks fetching.",
    )

    def __init__(self, user, *args, **kwargs):
        # Querysets are scoped per request so one user can never select
        # another user's resume or application.
        super().__init__(*args, **kwargs)
        self.fields["resume_choice"].queryset = Resume.objects.filter(user=user)
        self.fields["job_application"].queryset = JobApplication.objects.filter(
            user=user
        )

    def clean_resume_file(self):
        """Cheap file checks (extension, size) attach errors to the field."""
        uploaded = self.cleaned_data.get("resume_file")

        if uploaded:
            try:
                parsers.validate_upload(uploaded)
            except parsers.ResumeParseError as exc:
                raise forms.ValidationError(str(exc))

        return uploaded

    def clean(self):
        cleaned = super().clean()

        sources = [
            bool(cleaned.get("resume_choice")),
            bool(cleaned.get("resume_file")),
            bool((cleaned.get("resume_text") or "").strip()),
        ]

        if not any(sources):
            raise forms.ValidationError(
                "Provide a resume — choose an existing one, upload a file, "
                "or paste the text."
            )

        if sum(sources) > 1:
            raise forms.ValidationError(
                "Choose only one resume source: existing, upload, or pasted text."
            )

        text = (cleaned.get("resume_text") or "").strip()
        if text and len(text) < parsers.MIN_TEXT_LENGTH:
            self.add_error(
                "resume_text",
                "This text is too short to analyze. Please paste your full resume.",
            )

        return cleaned
