from django import forms
from .models import JobApplication

class JobApplicationForm(forms.ModelForm):

    class Meta:
        model = JobApplication

        fields = [
            "company",
            "job_title",
            "location",
            "job_type",
            "application_date",
            "job_status",
            "salary",
            "job_url",
            "notes",
        ]

        widgets = {
            "application_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 5}
            ),
        }