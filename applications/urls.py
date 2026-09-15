from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="list"),
    path("add/", views.create_application, name="add"),
    path("<int:pk>", views.application_details, name="details"),
    path("<int:pk>/edit/", views.update_application, name="edit"),
    path("<int:pk>/delete/", views.delete_application, name="delete")
]