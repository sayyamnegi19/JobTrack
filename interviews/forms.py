from django import forms
from .models import Interview

class InterviewForm(forms.ModelForm):

    class Meta:
        model = Interview

        fields = [
            "application",
            "round_name",
            "interview_type",
            "scheduled_at",
            "location",
            "status",
            "notes",
        ]

        widgets = {
            "scheduled_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 5,
                }
            ),
        }