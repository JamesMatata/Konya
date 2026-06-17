from django.db import migrations, models


def mark_existing_chats_with_documents(apps, schema_editor):
  Chat = apps.get_model("navigator", "Chat")
  Message = apps.get_model("navigator", "Message")

  for chat in Chat.objects.all():
    first_user = (
      Message.objects.filter(chat_id=chat.id, role="user")
      .order_by("timestamp")
      .first()
    )
    if first_user and (first_user.attached_url or first_user.attached_file):
      chat.has_valid_document = True
      chat.save(update_fields=["has_valid_document"])


class Migration(migrations.Migration):

  dependencies = [
    ("navigator", "0003_message_is_error"),
  ]

  operations = [
    migrations.AddField(
      model_name="chat",
      name="has_valid_document",
      field=models.BooleanField(default=False),
    ),
    migrations.AddField(
      model_name="chat",
      name="invalid_doc_attempts",
      field=models.IntegerField(default=0),
    ),
    migrations.RunPython(mark_existing_chats_with_documents, migrations.RunPython.noop),
  ]
