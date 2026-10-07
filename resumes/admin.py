from django.contrib import admin
from .models import Resume, ResumeAnalysis


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "original_filename",
        "created_at",
    )

    search_fields = (
        "user__email",
        "original_filename",
    )


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "resume",
        "mode",
        "overall_score",
        "semantic_similarity",
        "ai_model",
        "created_at",
    )

    list_filter = (
        "mode",
        "ai_model",
    )

    search_fields = (
        "resume__user__email",
        "job_url",
    )
