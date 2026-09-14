from django.db import models
from django.conf import settings

# Create your models here.
class JobApplication(models.Model):

    class JobType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full Time"
        PART_TIME = "PART_TIME", "Part Time"
        INTERNSHIP = "INTERNSHIP", "Internship"
        FREELANCE = "FREELANCE", "Freelance"
        REMOTE = "REMOTE", "Remote"

    class Status(models.TextChoices):
        SAVED = "SAVED", "Saved"
        APPLIED = "APPLIED", "Applied"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        INTERVIEW = "INTERVIEW", "Interview"
        REJECTED = "REJECTED", "Rejected"
        OFFER = "OFFER", "Offer"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        ACCEPTED = "ACCEPTED", "Accepted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications"
    )

    company = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)

    location = models.CharField(max_length=100, blank=True)
    job_type = models.CharField(
        max_length=50,
        choices=JobType.choices,
        default=JobType.FULL_TIME
    )
    application_date = models.DateField()
    job_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.APPLIED
    )
    salary = models.CharField(max_length=100, blank=True)
    job_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_title} at {self.company}"