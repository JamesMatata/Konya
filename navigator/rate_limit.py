from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse


def _client_identifier(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    if request.session.session_key:
        return f"session:{request.session.session_key}"
    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def rate_limit(key_prefix, *, limit=30, period=60):
    """Simple cache-backed rate limiter for sensitive POST endpoints."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            cache_key = f"ratelimit:{key_prefix}:{_client_identifier(request)}"
            count = cache.get(cache_key, 0)
            if count >= limit:
                message = "Too many requests. Please wait a moment and try again."
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"error": message}, status=429)
                return HttpResponse(message, status=429)

            cache.set(cache_key, count + 1, period)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
