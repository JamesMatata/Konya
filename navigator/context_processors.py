from accounts.i18n import (
    LANGUAGE_DISPLAY_NAMES,
    PREFERRED_LANGUAGE_CHOICES,
)


def i18n_context(request):
    from django.utils.translation import get_language

    current = get_language() or "en"
    return {
        "current_language": current,
        "languages": PREFERRED_LANGUAGE_CHOICES,
        "language_display_names": LANGUAGE_DISPLAY_NAMES,
        "current_language_name": LANGUAGE_DISPLAY_NAMES.get(current, "English"),
    }