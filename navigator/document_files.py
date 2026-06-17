from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

POLICY_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".docx",
    ".doc",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}

POLICY_FILE_ACCEPT = (
    "application/pdf,.pdf,"
    "text/plain,.txt,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,"
    "application/msword,.doc,"
    "image/jpeg,.jpg,.jpeg,image/png,.png,image/gif,.gif,image/webp,.webp"
)


def policy_file_extension(filename):
    if not filename or "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


def validate_policy_upload(uploaded_file):
    if not uploaded_file:
        return uploaded_file

    extension = policy_file_extension(uploaded_file.name)
    if extension not in POLICY_ALLOWED_EXTENSIONS:
        raise ValidationError(
            _("Upload a supported policy document (PDF, Word, text, or image).")
        )

    return uploaded_file
