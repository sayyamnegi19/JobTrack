from django.shortcuts import render
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from .forms import RegisterationForm

# Create your views here.
def register(request):
    if request.method == "POST":
        form = RegisterationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            return redirect("dashboard")
    else:
        form = RegisterationForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )

def logout_view(request):
    logout(request)
    return redirect("accounts:login")