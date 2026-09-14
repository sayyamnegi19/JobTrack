from django.contrib import admin
from .models import JobApplication
# Register your models here.

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "job_title",
        "job_status",
        "job_type",
        "application_date"
    )

    list_filter = (
        "job_status",
        "job_type"
    )

    search_fields = (
        "job_title",
        "company"
    )