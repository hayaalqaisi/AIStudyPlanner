from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from accounts.forms.registration_form import RegistrationForm
from accounts.services.registration_service import register_user


@sensitive_post_parameters("password1", "password2")
@require_http_methods(["GET", "POST"])
def registration_view(request):
    if request.user.is_authenticated:
        return redirect("planner:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    register_user(form)
            except IntegrityError:
                form.add_error(
                    None,
                    "Your account could not be created. "
                    "The username may already be in use.",
                )
            else:
                messages.success(
                    request,
                    "Your account was created successfully. Please log in.",
                )
                return redirect("accounts:login")
    else:
        form = RegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )