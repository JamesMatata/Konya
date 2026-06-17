DEFAULT_LANGUAGE = "en"
LANGUAGE_SESSION_KEY = "django_language"
LANGUAGE_CONFIRMED_SESSION_KEY = "language_confirmed"
ONBOARDING_COMPLETE_KEY = "onboarding_complete"
ONBOARDING_STEP_KEY = "onboarding_step"

PREFERRED_LANGUAGE_CHOICES = [
    (DEFAULT_LANGUAGE, "English"),
    ("sw", "Kiswahili"),
    ("sheng", "Sheng"),
]

VALID_LANGUAGE_CODES = {code for code, _ in PREFERRED_LANGUAGE_CHOICES}

LANGUAGE_DISPLAY_NAMES = {
    "en": "English",
    "sw": "Kiswahili",
    "sheng": "Sheng",
}


def normalize_language_code(language_code):
    if language_code in VALID_LANGUAGE_CODES:
        return language_code
    return DEFAULT_LANGUAGE


def get_request_language(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            return normalize_language_code(profile.preferred_language)

    session_language = request.session.get(LANGUAGE_SESSION_KEY)
    if session_language:
        return normalize_language_code(session_language)

    return DEFAULT_LANGUAGE


def set_request_language(request, language_code):
    from accounts.models import UserProfile

    language_code = normalize_language_code(language_code)
    request.session[LANGUAGE_SESSION_KEY] = language_code
    request.session[LANGUAGE_CONFIRMED_SESSION_KEY] = True

    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.preferred_language != language_code:
            profile.preferred_language = language_code
            profile.save(update_fields=["preferred_language"])

    return language_code


def sync_language_on_login(request, user):
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user)
    session_language = request.session.get(LANGUAGE_SESSION_KEY)

    if session_language and session_language in VALID_LANGUAGE_CODES:
        if profile.preferred_language != session_language:
            profile.preferred_language = session_language
            profile.save(update_fields=["preferred_language"])
    else:
        request.session[LANGUAGE_SESSION_KEY] = profile.preferred_language
        request.session[LANGUAGE_CONFIRMED_SESSION_KEY] = True


def sync_onboarding_on_login(request, user):
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.session.get(ONBOARDING_COMPLETE_KEY) and not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed"])
    elif profile.onboarding_completed:
        request.session[ONBOARDING_COMPLETE_KEY] = True


def should_show_language_modal(request):
    """Deprecated: language is chosen in onboarding step 2."""
    return False


def complete_onboarding(request):
    request.session[ONBOARDING_COMPLETE_KEY] = True

    if request.user.is_authenticated:
        from accounts.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.save(update_fields=["onboarding_completed"])


def is_onboarding_complete(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.onboarding_completed:
            return True

    return bool(request.session.get(ONBOARDING_COMPLETE_KEY))


def get_onboarding_step(request):
    return int(request.session.get(ONBOARDING_STEP_KEY, 1))
