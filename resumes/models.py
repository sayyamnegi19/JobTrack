from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Resume(models.Model):
    """
    A stored resume: either an uploaded file (PDF/DOCX) or pasted plain text.

    The raw file is kept so the user can re-analyze the same resume against
    different jobs without uploading it again. `text` is the extracted content
    that is actually sent to the AI.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
    )

    file = models.FileField(
        upload_to="resumes/%Y/%m/",
        blank=True,
        help_text="Original uploaded file (empty when the resume was pasted).",
    )

    text = models.TextField(
        help_text="Extracted resume text used for analysis.",
    )

    original_filename = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename or f"Resume #{self.pk}"


class ResumeAnalysis(models.Model):
    """
    One AI evaluation of a resume, optionally matched against a job description.

    `overall_score` is denormalized out of `result` so history lists and
    future charts can sort/aggregate cheaply; everything else the AI returns
    lives in the `result` JSON field.
    """

    class Mode(models.TextChoices):
        GENERAL = "GENERAL", "General"
        JOB_MATCH = "JOB_MATCH", "Job Match"

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="analyses",
    )

    # Optional link to a tracked application ("score for this job").
    job_application = models.ForeignKey(
        "applications.JobApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resume_analyses",
    )

    job_url = models.URLField(blank=True)

    job_description = models.TextField(
        blank=True,
        help_text="Job description fetched from the link or pasted by the user.",
    )

    mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
        default=Mode.GENERAL,
    )

    overall_score = models.PositiveSmallIntegerField(
        help_text="0-100 score shown in history and dashboards.",
    )

    semantic_similarity = models.FloatField(
        null=True,
        blank=True,
        help_text="Cosine similarity between resume and JD embeddings (0-1).",
    )

    result = models.JSONField(
        default=dict,
        help_text="Full structured AI response (categories, keywords, etc.).",
    )

    ai_model = models.CharField(max_length=100, blank=True)

    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resume", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.resume} - {self.get_mode_display()} ({self.overall_score})"


@receiver(post_delete, sender=Resume)
def delete_resume_file(sender, instance, **kwargs):
    """Remove the stored file when its Resume row is deleted.

    Django does not delete files on model deletion, so without this hook
    deleted resumes would leave orphaned personal documents on disk.
    """
    if instance.file:
        instance.file.delete(save=False)
