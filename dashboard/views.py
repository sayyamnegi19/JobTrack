from calendar import month_abbr

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from applications.models import JobApplication
from interviews.models import Interview
from resumes.models import ResumeAnalysis

# Chart colors: mid-tones that stay readable on both light and dark themes.
STATUS_COLORS = {
    "SAVED": "#94a3b8",
    "APPLIED": "#6366f1",
    "UNDER_REVIEW": "#38bdf8",
    "INTERVIEW": "#4ade80",
    "REJECTED": "#f87171",
    "OFFER": "#fbbf24",
    "WITHDRAWN": "#9ca3af",
    "ACCEPTED": "#34d399",
}

TREND_MONTHS = 6


@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()

    applications = JobApplication.objects.filter(user=user)

    upcoming_interviews = Interview.objects.filter(
        application__user=user,
        scheduled_at__gte=now,
        status=Interview.Status.UPCOMING
    ).select_related("application").order_by("scheduled_at")[:5]

    # --- Chart data ---------------------------------------------------------

    status_display = dict(JobApplication.Status.choices)
    status_breakdown = [
        {
            "label": status_display.get(row["job_status"], row["job_status"]),
            "value": row["count"],
            "color": STATUS_COLORS.get(row["job_status"], "#6366f1"),
        }
        for row in applications.values("job_status")
        .annotate(count=Count("id"))
        .order_by("-count")
    ]

    counts_by_month = {
        (row["month"].year, row["month"].month): row["count"]
        for row in applications.annotate(month=TruncMonth("application_date"))
        .values("month")
        .annotate(count=Count("id"))
        if row["month"]
    }

    today = timezone.localdate()
    months = []
    year, month = today.year, today.month
    for _ in range(TREND_MONTHS):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    context = {
        "total_applications": applications.count(),
        "applied_count": applications.filter(
            job_status=JobApplication.Status.APPLIED
        ).count(),
        "interview_count": applications.filter(
            job_status=JobApplication.Status.INTERVIEW
        ).count(),
        "rejected_count": applications.filter(
            job_status=JobApplication.Status.REJECTED
        ).count(),
        "offer_count": applications.filter(
            job_status=JobApplication.Status.OFFER
        ).count(),
        "saved_count": applications.filter(
            job_status=JobApplication.Status.SAVED
        ).count(),
        "withdrawn_count": applications.filter(
            job_status=JobApplication.Status.WITHDRAWN
        ).count(),
        "accepted_count": applications.filter(
            job_status=JobApplication.Status.ACCEPTED
        ).count(),
        "recent_applications": applications.order_by(
            "-application_date", "-created_at"
        )[:5],
        "upcoming_interviews": upcoming_interviews,
        "latest_analysis": ResumeAnalysis.objects.filter(
            resume__user=user
        ).select_related("resume").order_by("-created_at").first(),
        "status_breakdown": status_breakdown,
        "trend_labels": [f"{month_abbr[m]} {str(y)[2:]}" for y, m in months],
        "trend_values": [
            counts_by_month.get((y, m), 0) for y, m in months
        ],
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )
