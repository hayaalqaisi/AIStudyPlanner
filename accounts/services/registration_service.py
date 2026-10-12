def register_user(form):
    """Create a regular account from a validated RegistrationForm."""
    if not form.is_valid():
        raise ValueError("The registration form must be valid.")

    user = form.save(commit=False)
    user.is_staff = False
    user.is_superuser = False
    user.save()

    return user