from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("navigator", "0004_chat_byop_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chat",
            name="cached_policy_text",
            field=models.TextField(blank=True, default=""),
        ),
    ]
