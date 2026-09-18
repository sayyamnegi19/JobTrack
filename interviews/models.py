from django.db import models
from applications.models import JobApplication

class Interview(models.Model):
    class InterviewType(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        PHONE = "PHONE", "Phone"
        IN_PERSON = "IN_PERSON", "In Person"

    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="interviews"
    )

    round_name = models.CharField(
        max_length=100
    )

    interview_type = models.CharField(
        max_length=20,
        choices=InterviewType.choices,
        default=InterviewType.ONLINE
    )

    scheduled_at = models.DateTimeField()

    location = models.CharField(
        max_length=500,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.round_name} - {self.application}"