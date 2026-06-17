from django.urls import path

from . import views

app_name = "navigator"

urlpatterns = [
    path("", views.onboarding_wizard, name="onboarding"),
    path("launchpad/", views.launchpad, name="launchpad"),
    path("about/", views.about_view, name="about"),
    path("chat/<uuid:chat_id>/reasoning/", views.reasoning_trace, name="reasoning_trace"),
    path("chat/<uuid:chat_id>/process/", views.process_launch_navigation, name="process_launch_navigation"),
    path("chat/<uuid:chat_id>/", views.chat_detail, name="chat_detail"),
    path("chat/<uuid:chat_id>/submit-policy/", views.submit_policy_document, name="submit_policy_document"),
    path("chat/<uuid:chat_id>/delete/", views.delete_chat, name="delete_chat"),
    path("set-language/", views.set_language_view, name="set_language"),
]
