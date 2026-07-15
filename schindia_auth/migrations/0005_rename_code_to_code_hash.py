from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schindia_auth', '0004_user_email_verified_user_notification_preference'),
    ]

    operations = [
        migrations.RenameField(
            model_name='otptoken',
            old_name='code',
            new_name='code_hash',
        ),
        migrations.AlterField(
            model_name='otptoken',
            name='code_hash',
            field=models.CharField(max_length=128),
        ),
    ]
