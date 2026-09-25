from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Interview
from .forms import InterviewForm

@login_required
def interview_list(request):
    interviews = Interview.objects.filter(
        application__user=request.user
    ).select_related("application").order_by("scheduled_at")

    return render(
        request,
        "interviews/interviews_list.html",
        {
            "interviews": interviews
        }
    )

@login_required
def add_interview(request):
    if request.method == "POST":
        form = InterviewForm(request.POST)
        form.fields["application"].queryset = form.fields["application"].queryset.filter(
            user=request.user
        )

        if form.is_valid():
            interview = form.save()

            messages.success(
                request,
                "Interview added successfully."
            )

            return redirect(
                "interviews:details",
                pk=interview.pk
                )
    else:
        form = InterviewForm()

        form.fields["application"].queryset = form.fields["application"].queryset.filter(
            user=request.user
        )

    return render(
        request,
        "interviews/interview_form.html",
        {
            "form": form,
            "page_title": "Add Interview"
        }
    )

@login_required
def interview_details(request, pk):
    interview = get_object_or_404(
        Interview,
        application__user=request.user,
        pk=pk
    )

    return render(
        request,
        "interviews/interview_details.html",
        {
            "interview": interview
        }
    )

@login_required
def update_interview(request, pk):
    interview = get_object_or_404(
        Interview,
        pk=pk,
        application__user=request.user
    )

    if request.method == "POST":
        form = InterviewForm(
            request.POST,
            instance=interview
        )

        form.fields["application"].queryset = form.fields["application"].queryset.filter(
            user=request.user
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Interview updated succesfully."
            )

            return redirect(
                "interviews:details",
                pk=interview.pk
            )
    else:
        form = InterviewForm(
            instance=interview
        )

        form.fields["application"].queryset = form.fields["application"].queryset.filter(
            user=request.user
        )

    return render(
        request,
        "interviews/interview_form.html",
        {
            "form": form,
            "page_title": "Edit Interview"
        }
    )

@login_required
def delete_interview(request, pk):
    interview = get_object_or_404(
        Interview,
        pk=pk,
        application__user=request.user
    )

    if request.method == "POST":
        interview.delete()

        messages.success(
            request,
            "Interview deleted successfully."
        )

        return redirect("interviews:list")

    return render(
        request,
        "interviews/interview_confirm_delete.html",
        {
            "interview": interview
        }
    )