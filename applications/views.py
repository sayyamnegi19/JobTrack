from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import JobApplication
from .forms import JobApplicationForm

# Create your views here.
@login_required
def application_list(request):
    applications = JobApplication.objects.filter(
        user=request.user
    ).order_by("-application_date")

    return render(
        request,
        "applications/application_list.html",
        {
            "applications": applications
        }
    )

@login_required
def create_application(request):
    if request.method == "POST":
        form = JobApplicationForm(request.POST)

        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()

            messages.success(
                request,
                "Job Application added successfully."
            )

            return redirect(
                "applications:details",
                pk=application.pk
            )
    else:
        form = JobApplicationForm()

    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
            "page_title": "Add Application"
        }
    )

@login_required
def application_details(request, pk):
    application = get_object_or_404(
        JobApplication,
        pk=pk,
        user=request.user
    )

    return render(
        request,
        "applications/application_details.html",
        {
            "application": application
        }
    )

@login_required
def update_application(request, pk):
    application = get_object_or_404(
        JobApplication,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        form = JobApplicationForm(
            request.POST,
            instance=application
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Job Application Updated."
            )

            return redirect(
                "applications:details",
                pk=application.pk
            )
    else:
        form = JobApplicationForm(instance=application)

    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
            "page_title": "Edit Application"
        }
    )

@login_required
def delete_application(request, pk):
    application = get_object_or_404(
        JobApplication,
        user=request.user,
        pk=pk
    )

    if request.method == "POST":
        application.delete()

        messages.success(
            request,
            "Job Application Deleted."
        )

        return redirect(
            "applications:list"
        )

    return render(
        request,
        "applications/application_confirm_delete.html",
        {
            "application": application
        }
    )    