from django.urls import path
from . import views

app_name = "interviews"

urlpatterns = [
    path("", views.interview_list, name="list"),
    path("add/", views.add_interview, name="add"),
    path("details/<int:pk>/", views.interview_details, name="details"),
    path("edit/<int:pk>", views.update_interview, name="edit"),
    path("delete/<int:pk>/", views.delete_interview, name="delete")
]