from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .document_files import POLICY_FILE_ACCEPT, validate_policy_upload


class LaunchpadForm(forms.Form):
    content = forms.CharField(
        label=_("Your situation"),
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": _("Describe your personal situation, goals, or the guidance you need…"),
            }
        ),
    )
    attached_url = forms.URLField(
        label=_("Policy link"),
        required=False,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://www.example.gov/policy-or-program-page",
            }
        ),
    )
    attached_file = forms.FileField(
        label=_("Policy document"),
        required=False,
    )

    def clean_attached_file(self):
        return validate_policy_upload(self.cleaned_data.get("attached_file"))

    def clean(self):
        cleaned_data = super().clean()
        attached_url = cleaned_data.get("attached_url")
        attached_file = cleaned_data.get("attached_file")

        if not attached_url and not attached_file:
            raise ValidationError(
                _("Provide a policy link or upload a policy document — at least one is required.")
            )

        return cleaned_data

    @property
    def policy_file_accept(self):
        return POLICY_FILE_ACCEPT


class PolicyDocumentForm(forms.Form):
    attached_url = forms.URLField(
        label=_("Policy link"),
        required=False,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://example.gov/policy-or-program-page",
            }
        ),
    )
    attached_file = forms.FileField(
        label=_("Policy document"),
        required=False,
    )

    def clean_attached_file(self):
        return validate_policy_upload(self.cleaned_data.get("attached_file"))

    def clean(self):
        cleaned_data = super().clean()
        attached_url = cleaned_data.get("attached_url")
        attached_file = cleaned_data.get("attached_file")

        if not attached_url and not attached_file:
            raise ValidationError(_("Provide a policy link or upload a policy document."))

        return cleaned_data

    @property
    def policy_file_accept(self):
        return POLICY_FILE_ACCEPT


class LoginForm(forms.Form):
    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": _("Password"),
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email or "@" not in email:
            raise ValidationError(_("Enter a valid email address."))
        return email.lower()


class SignupForm(forms.Form):
    email = forms.CharField(
        label=_("Email"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "test@example.com",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Any password for testing"),
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email or "@" not in email:
            raise ValidationError(_("Enter a basic email address (e.g. test@example.com)."))
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password or not str(password).strip():
            raise ValidationError(_("Enter a password."))
        return password
