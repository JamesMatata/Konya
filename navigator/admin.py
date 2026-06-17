from django.contrib import admin

from .models import Chat, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "content", "is_error", "is_gatekeeper", "attached_url", "timestamp")
    readonly_fields = ("timestamp",)
    ordering = ("timestamp",)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "session_key",
        "has_valid_document",
        "invalid_doc_attempts",
        "created_at",
    )
    list_filter = ("has_valid_document", "created_at")
    search_fields = ("title", "user__email", "session_key")
    readonly_fields = ("id", "created_at")
    inlines = (MessageInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("chat", "role", "short_content", "is_error", "is_gatekeeper", "timestamp")
    list_filter = ("role", "is_error", "is_gatekeeper")
    search_fields = ("content", "chat__title")
    readonly_fields = ("timestamp",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:80]
