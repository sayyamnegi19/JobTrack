from django import forms
from django.contrib.auth import get_user_model, password_validation

User = get_user_model()

class RegisterationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Enter Password"
    )

    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name"
        ]

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match!")

        return cleaned_data

    def _post_clean(self):
        super()._post_clean()

        password = self.cleaned_data.get("password")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit = True):
        user = super().save(commit=False)

        user.set_password(self.cleaned_data.get("password"))

        if commit:
            user.save()

        return user
