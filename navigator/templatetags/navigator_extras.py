import markdown
from django import template
from django.utils.safestring import mark_safe

from navigator.document_files import POLICY_FILE_ACCEPT
from navigator.services.featherless_ai import is_blueprint_message, is_gatekeeper_message

register = template.Library()

MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "nl2br", "sane_lists"]


def markdown_to_html(value):
    if not value:
        return ""
    return markdown.markdown(value, extensions=MARKDOWN_EXTENSIONS)


@register.simple_tag
def policy_file_accept():
    return POLICY_FILE_ACCEPT


@register.filter
def render_markdown(value):
    return mark_safe(markdown_to_html(value))


@register.filter
def filename(value):
    if not value:
        return ""
    name = str(value)
    return name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]


@register.filter
def is_gatekeeper(message):
    return is_gatekeeper_message(message)


@register.filter
def is_blueprint(message, chat):
    return is_blueprint_message(message, chat)
