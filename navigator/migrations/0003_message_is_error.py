from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("navigator", "0002_chat_eligibility_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="is_error",
            field=models.BooleanField(default=False),
        ),
    ]
