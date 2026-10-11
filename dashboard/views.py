from calendar import month_abbr
import random

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


# ---------------------------------------------------------------------------
# Landing page preview
# ---------------------------------------------------------------------------

# Same tones as JobApplication.status_tone, for the sample rows.
STATUS_TONES = {
    "SAVED": "secondary",
    "APPLIED": "primary",
    "UNDER_REVIEW": "info",
    "INTERVIEW": "success",
    "REJECTED": "danger",
    "OFFER": "warning",
    "WITHDRAWN": "secondary",
    "ACCEPTED": "success",
}

# Weighted status split for the anonymous sample; always sums to the total.
SAMPLE_SPLIT_WEIGHTS = [
    ("APPLIED", 0.40),
    ("UNDER_REVIEW", 0.15),
    ("INTERVIEW", 0.20),
    ("OFFER", 0.08),
    ("REJECTED", 0.17),
]

SAMPLE_ROLES = [
    ("Senior Frontend Developer", "Northwind Labs", "INTERVIEW"),
    ("Backend Engineer", "DataFlow", "APPLIED"),
    ("Full Stack Engineer", "InnoSoft", "OFFER"),
    ("Python Developer", "BrightPath", "UNDER_REVIEW"),
    ("Platform Engineer", "CloudNest", "APPLIED"),
    ("API Engineer", "Quantify", "REJECTED"),
    ("Backend Developer", "Fabrikam", "INTERVIEW"),
    ("Software Engineer", "Lumen Works", "SAVED"),
    ("Data Engineer", "Statline", "APPLIED"),
    ("DevOps Engineer", "Orbit Systems", "APPLIED"),
    ("Machine Learning Engineer", "Vectra AI", "UNDER_REVIEW"),
    ("QA Engineer", "Trellis", "APPLIED"),
]


def _last_six_month_keys():
    today = timezone.localdate()
    keys = []
    year, month = today.year, today.month
    for _ in range(6):
        keys.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    keys.reverse()
    return keys


def _trend_payload(keys, values):
    """
    Bars for the landing preview.

    Heights are emitted in *pixels* (against a fixed plot height) because
    percentage heights inside nested flex containers resolve unreliably
    across browsers; pixel heights always render.
    """
    peak = max(values) if values else 0
    plot_height = 150  # px of drawing area

    bars = []
    for (year, month), value in zip(keys, values):
        if peak and value:
            percent = max(6, round(value * 100 / peak))
            px = max(6, round(value * plot_height / peak))
        else:
            percent = 0
            px = 0
        bars.append(
            {
                "label": month_abbr[month],
                "count": value,
                "percent": percent,
                "px": px,
            }
        )
    return bars


def _pipeline_segments(applications):
    """[{label, count, percent, color}] for the doughnut and its legend."""
    total = applications.count()
    if not total:
        return []

    status_display = dict(JobApplication.Status.choices)
    rows = list(
        applications.values("job_status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    segments = []
    running_percent = 0
    for index, row in enumerate(rows):
        if index == len(rows) - 1:
            # Give the last slice the remainder so percentages sum to 100.
            percent = max(0, 100 - running_percent)
        else:
            percent = round(row["count"] * 100 / total)
            running_percent += percent

        segments.append(
            {
                "label": status_display.get(row["job_status"], row["job_status"]),
                "count": row["count"],
                "percent": percent,
                "color": STATUS_COLORS.get(row["job_status"], "#6366f1"),
            }
        )

    return segments


def _donut_gradient(segments):
    """A CSS conic-gradient string for the preview doughnut."""
    if not segments:
        return "conic-gradient(var(--bs-secondary-bg) 0% 100%)"

    stops = []
    cursor = 0
    for index, item in enumerate(segments):
        end = 100 if index == len(segments) - 1 else cursor + item["percent"]
        stops.append(f"{item['color']} {cursor}% {end}%")
        cursor = end

    return "conic-gradient(" + ", ".join(stops) + ")"


def _sample_preview():
    """A coherent random sample for anonymous (and new) visitors."""
    total = random.randint(12, 36)

    counts = {}
    fractions = []
    for status, weight in SAMPLE_SPLIT_WEIGHTS:
        exact = weight * total
        counts[status] = int(exact)
        fractions.append((exact - int(exact), status))

    remainder = total - sum(counts.values())
    fractions.sort(reverse=True)
    for index in range(remainder):
        counts[fractions[index % len(fractions)][1]] += 1

    # Keep the sample flattering: at least 2 interviews and 1 offer.
    for key, minimum in (("INTERVIEW", 2), ("OFFER", 1)):
        if counts[key] < minimum:
            donor = max(counts, key=counts.get)
            if donor != key:
                moved = min(minimum - counts[key], max(0, counts[donor] - 1))
                counts[donor] -= moved
                counts[key] += moved

    status_display = dict(JobApplication.Status.choices)
    ordered = [status for status, _ in SAMPLE_SPLIT_WEIGHTS]

    segments = []
    running_percent = 0
    for index, status in enumerate(ordered):
        if index == len(ordered) - 1:
            percent = max(0, 100 - running_percent)
        else:
            percent = round(counts[status] * 100 / total)
            running_percent += percent

        segments.append(
            {
                "label": status_display[status],
                "count": counts[status],
                "percent": percent,
                "color": STATUS_COLORS.get(status, "#6366f1"),
            }
        )

    recent = [
        {
            "job_title": role,
            "company": company,
            "status_label": status_display[status],
            "status_tone": STATUS_TONES[status],
        }
        for role, company, status in random.sample(SAMPLE_ROLES, 3)
    ]

    month_values = [random.randint(1, max(2, total // 5)) for _ in range(6)]
    trend = _trend_payload(_last_six_month_keys(), month_values)

    interviews = counts["INTERVIEW"]

    return {
        "preview_is_sample": True,
        "preview_has_data": False,
        "preview_zero_data": False,
        "preview_total": total,
        "preview_interviews": interviews,
        "preview_upcoming": random.randint(1, min(4, interviews)),
        "preview_rejected": counts["REJECTED"],
        "preview_recent": recent,
        "preview_breakdown": segments,
        "preview_trend": trend,
    }


def landing_page(request):
    """
    Marketing home page.

    Logged-in users with data see their real stats; anonymous visitors (and
    users who haven't added anything yet) see a coherent random sample that
    is clearly labelled as a preview.
    """
    context = None

    if request.user.is_authenticated:
        applications = JobApplication.objects.filter(user=request.user)
        total = applications.count()

        if total:
            keys = _last_six_month_keys()
            counts_by_month = {
                (row["month"].year, row["month"].month): row["count"]
                for row in applications.annotate(month=TruncMonth("application_date"))
                .values("month")
                .annotate(count=Count("id"))
                if row["month"]
            }

            context = {
                "preview_is_sample": False,
                "preview_has_data": True,
                "preview_zero_data": False,
                "preview_total": total,
                "preview_interviews": applications.filter(
                    job_status=JobApplication.Status.INTERVIEW
                ).count(),
                "preview_upcoming": Interview.objects.filter(
                    application__user=request.user,
                    scheduled_at__gte=timezone.now(),
                    status=Interview.Status.UPCOMING,
                ).count(),
                "preview_rejected": applications.filter(
                    job_status=JobApplication.Status.REJECTED
                ).count(),
                "preview_recent": [
                    {
                        "job_title": application.job_title,
                        "company": application.company,
                        "status_label": application.get_job_status_display(),
                        "status_tone": application.status_tone,
                    }
                    for application in applications.order_by(
                        "-application_date", "-created_at"
                    )[:3]
                ],
                "preview_breakdown": _pipeline_segments(applications),
                "preview_trend": _trend_payload(
                    keys, [counts_by_month.get(key, 0) for key in keys]
                ),
            }
        else:
            context = _sample_preview()
            context["preview_zero_data"] = True

    if context is None:
        context = _sample_preview()

    context["preview_donut"] = _donut_gradient(context["preview_breakdown"])

    return render(request, "home.html", context)
