from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from applications.models import JobApplication
from django.utils import timezone
from interviews.models import Interview

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()

    applications = JobApplication.objects.filter(
        user=user
    )

    upcoming_interviews = Interview.objects.filter(
        application__user=user,
        scheduled_at__gte=now,
        status=Interview.Status.UPCOMING
    ).select_related("application").order_by("scheduled_at")[:5]

    context = {
        "total_applications": applications.count(),
        "applied_count": applications.filter(
            job_status=JobApplication.Status.APPLIED
        ).count(),
        "under_review_count": applications.filter(
            job_status=JobApplication.Status.UNDER_REVIEW
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
        "recent_applications": applications.order_by(
            "-created_at"
        )[:5],
        "upcoming_interviews": upcoming_interviews
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )