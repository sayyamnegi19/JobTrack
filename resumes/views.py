from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import parsers
from .ai_client import AIAnalysisError
from .analyzer import analyze_resume
from .forms import ResumeAnalysisForm
from .models import Resume, ResumeAnalysis
from .scraper import JobFetchError, fetch_job_description

PAGE_SIZE = 12


def _score_tone(score):
    """Map a 0-100 score to a Bootstrap contextual color."""
    if score >= 80:
        return "success"
    if score >= 60:
        return "primary"
    if score >= 40:
        return "warning"
    return "danger"


@login_required
def analysis_list(request):
    resumes = (
        Resume.objects.filter(user=request.user)
        .annotate(analysis_count=Count("analyses"))
        .order_by("-created_at")
    )

    analyses = (
        ResumeAnalysis.objects.filter(resume__user=request.user)
        .select_related("resume", "job_application")
        .order_by("-created_at")
    )

    page_obj = Paginator(analyses, PAGE_SIZE).get_page(request.GET.get("page"))

    today_count = analyses.filter(created_at__date=timezone.localdate()).count()

    return render(
        request,
        "resumes/analysis_list.html",
        {
            "resumes": resumes,
            "page_obj": page_obj,
            "latest_analysis": analyses.first(),
            "total_analyses": analyses.count(),
            "today_count": today_count,
            "daily_limit": settings.ATS_DAILY_LIMIT,
        },
    )


def _run_analysis(request, form):
    """
    Orchestrate one analysis attempt.

    Adds form errors and returns None on failure, or the saved
    ResumeAnalysis instance on success. Order matters: local parsing first,
    quota guard before any network work, then fetch, then AI, then persist.
    """
    cleaned = form.cleaned_data
    user = request.user

    # 1. Resolve the resume source (exactly one is guaranteed by the form).
    resume = cleaned.get("resume_choice")
    uploaded_file = cleaned.get("resume_file")

    if not resume and uploaded_file:
        try:
            extracted_text = parsers.extract_text_from_file(uploaded_file)
        except parsers.ResumeParseError as exc:
            form.add_error("resume_file", str(exc))
            return None
    else:
        extracted_text = (cleaned.get("resume_text") or "").strip()

    # 2. Daily quota guard — before any network call.
    today_count = ResumeAnalysis.objects.filter(
        resume__user=user,
        created_at__date=timezone.localdate(),
    ).count()

    if today_count >= settings.ATS_DAILY_LIMIT:
        form.add_error(
            None,
            f"Daily limit reached ({settings.ATS_DAILY_LIMIT} analyses). "
            "Please try again tomorrow.",
        )
        return None

    # 3. Resolve job context. Pasted description wins; the link is fetched
    #    only when no description was pasted.
    application = cleaned.get("job_application")
    job_description = (cleaned.get("job_description") or "").strip()
    job_url = cleaned.get("job_url") or (
        application.job_url if application else ""
    )

    if not job_description and job_url:
        try:
            job_description = fetch_job_description(job_url)
        except JobFetchError as exc:
            form.add_error("job_url", str(exc))
            return None

    # 4. Persist a new Resume row if the user supplied a fresh source.
    if not resume:
        if uploaded_file:
            resume = Resume.objects.create(
                user=user,
                file=uploaded_file,
                text=extracted_text,
                original_filename=uploaded_file.name[:255],
            )
        else:
            resume = Resume.objects.create(
                user=user,
                text=extracted_text,
                original_filename="Pasted text",
            )

    # 5. Score with the AI (single call).
    try:
        analysis_result = analyze_resume(resume.text, job_description or None)
    except AIAnalysisError as exc:
        form.add_error(None, str(exc))
        return None

    # 6. Persist the analysis.
    return ResumeAnalysis.objects.create(
        resume=resume,
        job_application=application,
        job_url=job_url or "",
        job_description=job_description or "",
        mode=analysis_result["mode"],
        overall_score=analysis_result["overall_score"],
        semantic_similarity=analysis_result["semantic_similarity"],
        result=analysis_result["result"],
        ai_model=analysis_result["ai_model"],
        prompt_tokens=analysis_result["prompt_tokens"],
        output_tokens=analysis_result["output_tokens"],
    )


@login_required
def analyze(request):
    initial = {}

    # "Re-analyze" button passes ?resume=<id>; ownership is verified.
    preselect = request.GET.get("resume")
    if preselect:
        resume = Resume.objects.filter(pk=preselect, user=request.user).first()
        if resume:
            initial["resume_choice"] = resume.pk

    if request.method == "POST":
        form = ResumeAnalysisForm(request.user, request.POST, request.FILES)

        if form.is_valid():
            analysis = _run_analysis(request, form)

            if analysis is not None:
                messages.success(
                    request,
                    f"Analysis complete — ATS score "
                    f"{analysis.overall_score}/100.",
                )
                return redirect("resumes:analysis_detail", pk=analysis.pk)
    else:
        form = ResumeAnalysisForm(request.user, initial=initial)

    return render(request, "resumes/analyze_form.html", {"form": form})


@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(
        ResumeAnalysis.objects.select_related("resume", "job_application"),
        pk=pk,
        resume__user=request.user,
    )

    return render(
        request,
        "resumes/analysis_detail.html",
        {
            "analysis": analysis,
            "score_tone": _score_tone(analysis.overall_score),
        },
    )


@login_required
def analysis_delete(request, pk):
    analysis = get_object_or_404(
        ResumeAnalysis,
        pk=pk,
        resume__user=request.user,
    )

    if request.method == "POST":
        analysis.delete()
        messages.success(request, "Analysis deleted.")
        return redirect("resumes:list")

    return render(
        request,
        "resumes/analysis_confirm_delete.html",
        {"analysis": analysis},
    )


@login_required
def resume_delete(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)

    if request.method == "POST":
        resume.delete()
        messages.success(request, "Resume and its analyses were deleted.")
        return redirect("resumes:list")

    return render(
        request,
        "resumes/resume_confirm_delete.html",
        {"resume": resume},
    )


@login_required
def resume_download(request, pk):
    """Owner-only download; files are never served from a public media URL."""
    resume = get_object_or_404(Resume, pk=pk, user=request.user)

    if not resume.file:
        messages.error(
            request,
            "This resume was pasted as text — there is no file to download.",
        )
        return redirect("resumes:list")

    return FileResponse(
        resume.file.open("rb"),
        as_attachment=True,
        filename=resume.original_filename or "resume",
    )
