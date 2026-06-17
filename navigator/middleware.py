from django.utils import translation

from accounts.i18n import get_request_language


class UserLanguageMiddleware:
    """
    Activate the user's preferred language for each request.

    Authenticated users: UserProfile.preferred_language
    Guests: session language (django_language)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = get_request_language(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)

        translation.deactivate()
        return response
