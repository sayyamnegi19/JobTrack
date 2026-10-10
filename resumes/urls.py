from django.urls import path

from . import views

app_name = "resumes"

urlpatterns = [
    path("", views.analysis_list, name="list"),
    path("analyze/", views.analyze, name="analyze"),
    path("analysis/<int:pk>/", views.analysis_detail, name="analysis_detail"),
    path(
        "analysis/<int:pk>/delete/",
        views.analysis_delete,
        name="analysis_delete",
    ),
    path(
        "resume/<int:pk>/download/",
        views.resume_download,
        name="resume_download",
    ),
    path("resume/<int:pk>/delete/", views.resume_delete, name="resume_delete"),
]
