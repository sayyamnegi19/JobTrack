from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from applications.models import JobApplication

# Create your views here.
@login_required
def dashboard(request):
    user = request.user

    applications = JobApplication.objects.filter(
        user=user
    )

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
        )[:5]
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )