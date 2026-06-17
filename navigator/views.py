import logging
import re

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language, gettext as _, override
from django.views.decorators.http import require_http_methods

from accounts.i18n import (
    ONBOARDING_STEP_KEY,
    PREFERRED_LANGUAGE_CHOICES,
    complete_onboarding,
    get_onboarding_step,
    get_request_language,
    is_onboarding_complete,
    set_request_language,
    sync_language_on_login,
    sync_onboarding_on_login,
)

from .forms import LaunchpadForm, LoginForm, PolicyDocumentForm, SignupForm
from .models import Chat, Message
from .rate_limit import rate_limit
from .services.featherless_ai import (
    MAX_TITLE_LENGTH,
    build_gatekeeper_rejection_message,
    cache_policy_text_for_chat,
    evaluate_policy_document,
    finalize_eligibility_state,
    generate_chat_ai_response,
    generate_chat_title,
    get_ai_error_message,
    get_or_generate_reasoning_trace,
    initialize_checklist,
    is_blueprint_message,
    is_gatekeeper_message,
    is_navigation_complete,
)

User = get_user_model()
logger = logging.getLogger(__name__)

def ensure_session(request):
    if not request.session.session_key:
        request.session.create()


def get_chat_for_request(request, chat_id):
    ensure_session(request)
    chat = get_object_or_404(Chat, id=chat_id)

    if request.user.is_authenticated:
        if chat.user_id != request.user.id:
            raise Http404
    elif chat.session_key != request.session.session_key:
        raise Http404

    return chat


def get_chat_sources(chat):
    """Collect active reference sources from the initial launchpad message."""
    sources = []
    first_user_message = chat.messages.filter(role="user").order_by("timestamp").first()
    if not first_user_message:
        return sources

    if first_user_message.attached_url:
        sources.append(
            {
                "type": "link",
                "label": first_user_message.attached_url,
                "url": first_user_message.attached_url,
            }
        )

    if first_user_message.attached_file:
        sources.append(
            {
                "type": "document",
                "label": first_user_message.attached_file.name.rsplit("/", 1)[-1],
                "url": first_user_message.attached_file.url,
            }
        )

    return sources


def needs_initial_processing(chat):
    """True when launchpad created the chat but Gatekeeper has not run yet."""
    if chat.has_valid_document:
        return False
    if chat.messages.filter(role="ai").exists():
        return False
    first_user_message = chat.messages.filter(role="user").order_by("timestamp").first()
    if not first_user_message:
        return False
    return bool(first_user_message.attached_url or first_user_message.attached_file)


def needs_ai_response(chat):
    """True when the user sent a message that still needs an AI reply."""
    if needs_initial_processing(chat):
        return False
    last_message = chat.messages.order_by("-timestamp").first()
    if last_message is None or last_message.role != "user":
        return False
    if is_navigation_complete(chat):
        return True
    return chat.has_valid_document


def redirect_after_auth(request):
    if is_onboarding_complete(request):
        return redirect("navigator:launchpad")
    return redirect("navigator:onboarding")


def _chat_title_queryset(chat):
    if chat.user_id:
        return Chat.objects.filter(user_id=chat.user_id)
    if chat.session_key:
        return Chat.objects.filter(session_key=chat.session_key)
    return Chat.objects.filter(pk=chat.pk)


def ensure_unique_chat_title(chat, title):
    """Ensure the title is unique within the user's navigation history."""
    base = re.sub(r"\s+", " ", str(title or "").strip())
    if not base:
        base = "New Navigation"
    if len(base) > MAX_TITLE_LENGTH:
        base = base[: MAX_TITLE_LENGTH - 1].rstrip() + "…"

    queryset = _chat_title_queryset(chat)
    if chat.pk:
        queryset = queryset.exclude(pk=chat.pk)

    if not queryset.filter(title=base).exists():
        return base

    suffix = 2
    while suffix < 1000:
        suffix_text = f" ({suffix})"
        trimmed = base
        if len(trimmed) + len(suffix_text) > MAX_TITLE_LENGTH:
            trimmed = trimmed[: MAX_TITLE_LENGTH - len(suffix_text)].rstrip()
        candidate = f"{trimmed}{suffix_text}"
        if not queryset.filter(title=candidate).exists():
            return candidate
        suffix += 1

    return f"{base[:40].rstrip()} {str(chat.id)[:8]}"


def fallback_chat_title(chat, content):
    words = re.sub(r"\s+", " ", (content or "").strip()).split()[:4]
    if words:
        base = " ".join(words).title()
    else:
        base = f"Navigation {chat.created_at:%b %d}"
    return ensure_unique_chat_title(chat, base)


def assign_chat_title(chat, *, language_code="en", first_message_content=None, overwrite=False):
    """Generate and persist a unique sidebar/header title for the chat."""
    chat.refresh_from_db()
    if not overwrite and chat.title != "New Navigation":
        return chat.title

    content = first_message_content
    if content is None:
        first_message = chat.messages.filter(role="user").order_by("timestamp").first()
        content = first_message.content if first_message else ""

    generated = None
    try:
        generated = generate_chat_title(content, language_code=language_code)
    except Exception:
        logger.exception("Chat title generation failed for chat %s", chat.id)

    title = ensure_unique_chat_title(chat, generated) if generated else fallback_chat_title(chat, content)
    Chat.objects.filter(pk=chat.pk).update(title=title)
    chat.title = title
    return title


def create_ai_response(chat, *, assign_title=True, user_message=None, is_first_turn=None):
    language_code = get_language() or "en"
    fallback_state = chat.eligibility_state or {}

    result = generate_chat_ai_response(
        chat,
        user_message=user_message or "",
        is_first_turn=is_first_turn,
        language_code=language_code,
    )

    if result.get("skip"):
        return None, chat.title

    is_error = result.get("error", False)
    content = result["response"] if not is_error else get_ai_error_message(language_code)

    if not is_error and result.get("eligibility_state") is not None:
        chat.eligibility_state = result["eligibility_state"]
        chat.save(update_fields=["eligibility_state"])
    elif is_error:
        chat.eligibility_state = fallback_state

    message = Message.objects.create(
        chat=chat,
        role="ai",
        content=content,
        is_error=is_error,
    )

    chat_title = chat.title
    if assign_title:
        chat_title = assign_chat_title(chat, language_code=language_code)

    return message, chat_title


def get_eligibility_progress_payload(chat):
    """Serialize eligibility checklist progress for the chat header UI."""
    hidden = {
        "visible": False,
        "confirmed": 0,
        "total": 0,
        "percent": 0,
        "next_label": "",
        "use_groups": False,
        "criteria": [],
        "counts": {"missing": 0, "known": 0, "disqualified": 0, "skipped": 0},
    }

    if not chat.has_valid_document or is_navigation_complete(chat):
        return hidden

    state = finalize_eligibility_state(chat.eligibility_state or {})
    criteria = state.get("criteria") or []

    if not criteria:
        checklist = state.get("checklist") or {}
        criteria_meta = state.get("criteria_meta") or {}
        if not checklist:
            return hidden
        for key, value in checklist.items():
            meta = criteria_meta.get(key) or {}
            if value is None:
                status = "missing"
            elif value is True:
                status = "known"
            elif value is False:
                status = "disqualified"
            else:
                status = "missing"
            criteria.append(
                {
                    "key": key,
                    "label": meta.get("label") or key.replace("_", " ").capitalize(),
                    "status": status,
                }
            )

    total = len(criteria)
    if total == 0:
        return hidden

    next_key = (state.get("next_target_variable") or "").strip()
    next_label = ""
    items = []
    counts = {"missing": 0, "known": 0, "disqualified": 0, "skipped": 0}

    for item in criteria:
        status = item.get("status", "missing")
        key = str(item.get("key", ""))
        label = str(item.get("label", key)).strip() or key.replace("_", " ").capitalize()
        is_next = key == next_key and status == "missing"
        if is_next:
            next_label = label
        if status not in counts:
            status = "missing"
        counts[status] += 1
        items.append(
            {
                "key": key,
                "label": label,
                "status": status,
                "is_next": is_next,
            }
        )

    resolved = counts["known"] + counts["disqualified"] + counts["skipped"]
    percent = round((resolved / total) * 100) if total else 0

    with override(get_language() or "en"):
        summary = _("Checking eligibility · %(confirmed)s of %(total)s confirmed") % {
            "confirmed": resolved,
            "total": total,
        }
        if next_label:
            panel_summary = _("%(summary)s — Next up: %(label)s") % {
                "summary": summary,
                "label": next_label,
            }
        else:
            panel_summary = summary

    return {
        "visible": True,
        "confirmed": resolved,
        "total": total,
        "percent": percent,
        "next_label": next_label,
        "summary": summary,
        "panel_summary": panel_summary,
        "use_groups": total >= 11,
        "criteria": items,
        "counts": counts,
        "group_labels": {
            "missing": str(_("Still needed")),
            "known": str(_("Confirmed")),
            "disqualified": str(_("May not qualify")),
            "skipped": str(_("Not applicable")),
        },
        "next_up_label": str(_("Next up")),
    }


def is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def serialize_message(message, chat=None):
    data = {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "is_error": message.is_error,
        "is_gatekeeper": message.is_gatekeeper or is_gatekeeper_message(message),
    }
    if chat and is_blueprint_message(message, chat):
        data["is_blueprint"] = True
    if message.attached_url:
        data["attached_url"] = message.attached_url
    if message.attached_file:
        name = message.attached_file.name.replace("\\", "/")
        data["attached_file_name"] = name.rsplit("/", 1)[-1]
        data["attached_file_url"] = message.attached_file.url
    return data


def get_active_gatekeeper_message(chat):
    if chat.has_valid_document:
        return None
    for message in chat.messages.filter(role="ai").order_by("-timestamp"):
        if message.is_gatekeeper or (is_gatekeeper_message(message) and not message.is_error):
            return message
    return None


def get_user_chats(request):
    """Return all chats owned by the current user or session."""
    ensure_session(request)
    if request.user.is_authenticated:
        return Chat.objects.filter(user=request.user).order_by("-created_at")
    return Chat.objects.filter(session_key=request.session.session_key).order_by("-created_at")


def migrate_session_chats(session_key, user):
    """Reassign anonymous chats from a session key to an authenticated user."""
    if not session_key:
        return 0

    return Chat.objects.filter(
        session_key=session_key,
        user__isnull=True,
    ).update(user=user, session_key=None)


def complete_authentication(request, user, backend="django.contrib.auth.backends.ModelBackend"):
    """Log in the user and migrate any anonymous session chats."""
    if not request.session.session_key:
        request.session.create()

    anonymous_session_key = request.session.session_key
    login(request, user, backend=backend)
    migrate_session_chats(anonymous_session_key, user)
    sync_language_on_login(request, user)
    sync_onboarding_on_login(request, user)


def index(request):
    return redirect("navigator:onboarding")


@require_http_methods(["GET", "POST"])
def onboarding_wizard(request):
    ensure_session(request)

    if request.GET.get("action") == "skip":
        complete_onboarding(request)
        return redirect("navigator:launchpad")

    if is_onboarding_complete(request):
        return redirect("navigator:launchpad")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "skip":
            complete_onboarding(request)
            return redirect("navigator:launchpad")

        if action == "next":
            step = get_onboarding_step(request)
            if step == 1:
                request.session[ONBOARDING_STEP_KEY] = 2
            return redirect("navigator:onboarding")

        if action == "back":
            step = get_onboarding_step(request)
            if step > 1:
                request.session[ONBOARDING_STEP_KEY] = step - 1
            return redirect("navigator:onboarding")

        if action == "set_language":
            language = request.POST.get("language", "en")
            set_request_language(request, language)
            request.session[ONBOARDING_STEP_KEY] = 3
            return redirect("navigator:onboarding")

        if action == "create_account":
            complete_onboarding(request)
            return redirect("accounts:signup")

        if action == "continue_guest":
            complete_onboarding(request)
            return redirect("navigator:launchpad")

    current_step = get_onboarding_step(request)
    saved_language = get_request_language(request)

    return render(
        request,
        "navigator/onboarding.html",
        {
            "onboarding_step": current_step,
            "languages": PREFERRED_LANGUAGE_CHOICES,
            "saved_language": saved_language,
        },
    )


@require_http_methods(["GET"])
def about_view(request):
    ensure_session(request)

    if not is_onboarding_complete(request):
        return redirect("navigator:onboarding")

    return render(
        request,
        "navigator/about.html",
        {
            "chat_history": get_user_chats(request),
            "active_chat": None,
            "active_page": "about",
        },
    )


@require_http_methods(["GET", "POST"])
def launchpad(request):
    ensure_session(request)

    if not is_onboarding_complete(request):
        return redirect("navigator:onboarding")

    if request.method == "POST":
        form = LaunchpadForm(request.POST, request.FILES)
        if form.is_valid():
            chat = Chat()
            if request.user.is_authenticated:
                chat.user = request.user
            else:
                chat.session_key = request.session.session_key

            chat.title = "New Navigation"
            chat.save()

            attached_url = form.cleaned_data.get("attached_url") or None
            attached_file = form.cleaned_data.get("attached_file")

            Message.objects.create(
                chat=chat,
                role="user",
                content=form.cleaned_data["content"],
                attached_url=attached_url,
                attached_file=attached_file,
            )

            chat.title = fallback_chat_title(chat, form.cleaned_data["content"])
            chat.save(update_fields=["title"])

            return redirect("navigator:chat_detail", chat_id=chat.id)
    else:
        form = LaunchpadForm()

    return render(
        request,
        "navigator/launchpad.html",
        {
            "form": form,
            "chat_history": get_user_chats(request),
            "active_chat": None,
            "active_page": "launchpad",
        },
    )


def run_launch_processing(chat, language_code):
    """Gatekeeper + planner + first navigator response for a new launchpad chat."""
    first_user_message = chat.messages.filter(role="user").order_by("timestamp").first()
    if not first_user_message:
        return {"error": "No opening message found."}

    attached_url = first_user_message.attached_url
    attached_file = first_user_message.attached_file
    ai_messages = []

    chat_title = assign_chat_title(
        chat,
        language_code=language_code,
        first_message_content=first_user_message.content,
        overwrite=True,
    )

    evaluation = evaluate_policy_document(
        chat,
        attached_url=attached_url,
        attached_file=attached_file,
        language_code=language_code,
    )

    if evaluation.get("error"):
        ai_message = Message.objects.create(
            chat=chat,
            role="ai",
            content=get_ai_error_message(language_code),
            is_error=True,
        )
        ai_messages.append(serialize_message(ai_message, chat))
    elif evaluation["is_relevant"]:
        chat.has_valid_document = True
        chat.invalid_doc_attempts = 0
        chat.save(update_fields=["has_valid_document", "invalid_doc_attempts"])
        cache_policy_text_for_chat(
            chat,
            attached_url=attached_url,
            attached_file=attached_file,
        )
        try:
            initialize_checklist(chat, language_code=language_code)
        except (ValueError, RuntimeError):
            logger.exception("Planner failed for chat %s at launch", chat.id)

        chat.refresh_from_db()
        ai_message, chat_title = create_ai_response(
            chat,
            is_first_turn=True,
            assign_title=False,
        )
        if ai_message:
            ai_messages.append(serialize_message(ai_message, chat))
    else:
        chat.invalid_doc_attempts = 1
        chat.save(update_fields=["invalid_doc_attempts"])
        rejection_text = build_gatekeeper_rejection_message(
            1,
            evaluation.get("reason", ""),
            language_code=language_code,
        )
        ai_message = Message.objects.create(
            chat=chat,
            role="ai",
            content=rejection_text,
            is_gatekeeper=True,
        )
        ai_messages.append(serialize_message(ai_message, chat))

    chat.refresh_from_db()
    return {
        "complete": True,
        "has_valid_document": chat.has_valid_document,
        "chat_title": chat_title,
        "ai_messages": ai_messages,
        "navigation_complete": is_navigation_complete(chat),
        "eligibility_progress": get_eligibility_progress_payload(chat),
    }


@require_http_methods(["POST"])
@rate_limit("process_launch", limit=10, period=60)
def process_launch_navigation(request, chat_id):
    chat = get_chat_for_request(request, chat_id)

    if not needs_initial_processing(chat):
        return JsonResponse(
            {
                "complete": True,
                "has_valid_document": chat.has_valid_document,
                "chat_title": chat.title,
                "ai_messages": [],
                "navigation_complete": is_navigation_complete(chat),
                "eligibility_progress": get_eligibility_progress_payload(chat),
            }
        )

    language_code = get_language() or "en"
    result = run_launch_processing(chat, language_code)

    if result.get("error"):
        return JsonResponse({"error": result["error"]}, status=400)

    return JsonResponse(result)


@require_http_methods(["GET", "POST"])
@rate_limit("chat_detail", limit=45, period=60)
def chat_detail(request, chat_id):
    chat = get_chat_for_request(request, chat_id)

    if request.method == "POST":
        action = request.POST.get("action")
        ajax = is_ajax_request(request)

        if action == "regenerate":
            last_message = chat.messages.order_by("-timestamp").first()
            if last_message and last_message.role == "ai" and last_message.is_error:
                last_message.delete()
                ai_message, chat_title = create_ai_response(chat, assign_title=False)
                if ajax:
                    payload = {"chat_title": chat_title}
                    if ai_message:
                        payload["ai_message"] = serialize_message(ai_message, chat)
                    chat.refresh_from_db()
                    payload["eligibility_progress"] = get_eligibility_progress_payload(chat)
                    payload["navigation_complete"] = is_navigation_complete(chat)
                    return JsonResponse(payload)
            if ajax:
                return JsonResponse({"error": "Nothing to regenerate."}, status=400)
            return redirect("navigator:chat_detail", chat_id=chat.id)

        content = request.POST.get("content", "").strip()
        if content:
            if not chat.has_valid_document and not is_navigation_complete(chat):
                if ajax:
                    return JsonResponse(
                        {"error": "Submit a valid policy document before continuing."},
                        status=403,
                    )
                return redirect("navigator:chat_detail", chat_id=chat.id)

            user_message = Message.objects.create(chat=chat, role="user", content=content)
            ai_message, chat_title = create_ai_response(
                chat,
                user_message=content,
                assign_title=False,
            )
            if ajax:
                chat.refresh_from_db()
                payload = {
                    "eligibility_summary": chat.eligibility_state.get("summary", ""),
                    "navigation_complete": is_navigation_complete(chat),
                    "eligibility_progress": get_eligibility_progress_payload(chat),
                    "chat_title": chat_title,
                    "user_message": serialize_message(user_message),
                }
                if ai_message:
                    payload["ai_message"] = serialize_message(ai_message, chat)
                return JsonResponse(payload)
        elif ajax:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        return redirect("navigator:chat_detail", chat_id=chat.id)

    if needs_ai_response(chat):
        last_user_message = chat.messages.filter(role="user").order_by("-timestamp").first()
        create_ai_response(
            chat,
            user_message=last_user_message.content if last_user_message else "",
            assign_title=False,
        )
        chat.refresh_from_db()

    messages = chat.messages.all()
    chat_history = get_user_chats(request)
    initial_processing = needs_initial_processing(chat)
    active_gatekeeper_message = get_active_gatekeeper_message(chat)

    return render(
        request,
        "navigator/chat_detail.html",
        {
            "chat": chat,
            "messages": messages,
            "chat_history": chat_history,
            "active_chat": chat,
            "active_page": "chat",
            "sources": get_chat_sources(chat),
            "navigation_complete": is_navigation_complete(chat),
            "needs_initial_processing": initial_processing,
            "active_gatekeeper_message": active_gatekeeper_message,
            "reasoning_url": reverse("navigator:reasoning_trace", kwargs={"chat_id": chat.id}),
            "eligibility_progress": get_eligibility_progress_payload(chat),
        },
    )


@require_http_methods(["POST"])
@rate_limit("reasoning_trace", limit=20, period=60)
def reasoning_trace(request, chat_id):
    chat = get_chat_for_request(request, chat_id)

    if not is_navigation_complete(chat):
        return JsonResponse({"error": "Navigation is not complete yet."}, status=400)

    language_code = get_language() or "en"
    trace, error_message = get_or_generate_reasoning_trace(chat, language_code=language_code)
    if error_message:
        return JsonResponse({"error": error_message}, status=400)

    return JsonResponse({"reasoning_trace": trace})


@require_http_methods(["POST"])
@rate_limit("submit_policy", limit=15, period=60)
def submit_policy_document(request, chat_id):
    chat = get_chat_for_request(request, chat_id)
    ajax = is_ajax_request(request)

    if chat.has_valid_document:
        if ajax:
            return JsonResponse({"error": "A valid policy document is already on file."}, status=400)
        return redirect("navigator:chat_detail", chat_id=chat.id)

    form = PolicyDocumentForm(request.POST, request.FILES)
    if not form.is_valid():
        if ajax:
            return JsonResponse({"errors": form.errors}, status=400)
        return redirect("navigator:chat_detail", chat_id=chat.id)

    attached_url = form.cleaned_data.get("attached_url") or None
    attached_file = form.cleaned_data.get("attached_file")
    language_code = get_language() or "en"

    submission_message = Message.objects.create(
        chat=chat,
        role="user",
        content="",
        attached_url=attached_url,
        attached_file=attached_file,
    )
    submission_payload = serialize_message(submission_message)

    evaluation = evaluate_policy_document(
        chat,
        attached_url=attached_url,
        attached_file=attached_file,
        language_code=language_code,
    )

    if evaluation.get("error"):
        ai_message = Message.objects.create(
            chat=chat,
            role="ai",
            content=get_ai_error_message(language_code),
            is_error=True,
        )
        if ajax:
            return JsonResponse(
                {
                    "is_relevant": False,
                    "valid": False,
                    "has_valid_document": False,
                    "invalid_doc_attempts": chat.invalid_doc_attempts,
                    "ai_message": serialize_message(ai_message, chat),
                    "submission_message": submission_payload,
                }
            )
        return redirect("navigator:chat_detail", chat_id=chat.id)

    if evaluation["is_relevant"]:
        first_user_message = chat.messages.filter(role="user").order_by("timestamp").first()
        if first_user_message:
            first_user_message.attached_url = attached_url
            if attached_file:
                first_user_message.attached_file = attached_file
            first_user_message.save()

        chat.has_valid_document = True
        chat.invalid_doc_attempts = 0
        chat.save(update_fields=["has_valid_document", "invalid_doc_attempts"])
        cache_policy_text_for_chat(
            chat,
            attached_url=attached_url,
            attached_file=attached_file,
        )

        try:
            initialize_checklist(chat, language_code=language_code)
            chat.refresh_from_db()
        except (ValueError, RuntimeError):
            logger.exception("Planner failed for chat %s after document validation", chat.id)

        ai_message, chat_title = create_ai_response(chat, is_first_turn=True, assign_title=False)
        chat.refresh_from_db()
        if ajax:
            payload = {
                "is_relevant": True,
                "valid": True,
                "has_valid_document": True,
                "chat_title": chat_title,
                "navigation_complete": is_navigation_complete(chat),
                "eligibility_progress": get_eligibility_progress_payload(chat),
                "submission_message": submission_payload,
            }
            if ai_message:
                payload["ai_message"] = serialize_message(ai_message, chat)
            return JsonResponse(payload)
        return redirect("navigator:chat_detail", chat_id=chat.id)

    chat.invalid_doc_attempts += 1
    chat.save(update_fields=["invalid_doc_attempts"])

    rejection_text = build_gatekeeper_rejection_message(
        chat.invalid_doc_attempts,
        evaluation.get("reason", ""),
        language_code=language_code,
    )
    ai_message = Message.objects.create(
        chat=chat,
        role="ai",
        content=rejection_text,
        is_error=False,
        is_gatekeeper=True,
    )

    if ajax:
        return JsonResponse(
            {
                "is_relevant": False,
                "valid": False,
                "has_valid_document": False,
                "invalid_doc_attempts": chat.invalid_doc_attempts,
                "ai_message": serialize_message(ai_message, chat),
                "submission_message": submission_payload,
            }
        )
    return redirect("navigator:chat_detail", chat_id=chat.id)


@require_http_methods(["POST"])
def delete_chat(request, chat_id):
    chat = get_chat_for_request(request, chat_id)
    chat.delete()
    return redirect("navigator:launchpad")


@require_http_methods(["POST"])
def set_language_view(request):
    language = request.POST.get("language")
    set_request_language(request, language)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/launchpad/"
    return redirect(next_url)


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect_after_auth(request)

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            complete_authentication(request, user, backend=user.backend)
            return redirect_after_auth(request)

        form.add_error(None, _("Invalid email or password."))

    return render(request, "navigator/login.html", {"form": form})


@require_http_methods(["GET"])
def terms_view(request):
    return render(request, "navigator/legal/terms.html")


@require_http_methods(["GET"])
def privacy_view(request):
    return render(request, "navigator/legal/privacy.html")


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect_after_auth(request)

    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.create_user(
            username=email,
            email=email,
            password=form.cleaned_data["password"],
        )
        complete_authentication(request, user)
        return redirect_after_auth(request)

    return render(request, "navigator/signup.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("accounts:login")
