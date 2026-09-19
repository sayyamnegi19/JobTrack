from django.contrib import admin
from .models import Interview

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        "round_name",
        "application",
        "interview_type",
        "scheduled_at",
        "status",
    )

    list_filter = (
        "status",
        "interview_type",
    )

    search_fields = (
        "round_name",
        "application__company",
        "application__job_title",
    )

    ordering = (
        "scheduled_at",
    )