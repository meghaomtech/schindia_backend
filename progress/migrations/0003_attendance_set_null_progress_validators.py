import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0002_courseprogress_attendance'),
    ]

    operations = [
        # Attendance: slot and session → SET_NULL instead of CASCADE
        migrations.AlterField(
            model_name='attendance',
            name='slot',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendances',
                to='sessions_app.sessionslot',
            ),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='session',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendances',
                to='sessions_app.session',
            ),
        ),
        # Attendance: ordering tiebreaker
        migrations.AlterModelOptions(
            name='attendance',
            options={'ordering': ['-date', '-created_at']},
        ),
        # JourneyEntry: ordering tiebreaker
        migrations.AlterModelOptions(
            name='journeyentry',
            options={'ordering': ['-date', '-created_at'], 'verbose_name_plural': 'journey entries'},
        ),
        # ChildNote: ordering tiebreaker
        migrations.AlterModelOptions(
            name='childnote',
            options={'ordering': ['-date', '-created_at']},
        ),
        # CourseProgress: add created_at
        migrations.AddField(
            model_name='courseprogress',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # CourseProgress: add validators to current_month
        migrations.AlterField(
            model_name='courseprogress',
            name='current_month',
            field=models.PositiveIntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
        # CourseProgress: add validators to current_week
        migrations.AlterField(
            model_name='courseprogress',
            name='current_week',
            field=models.PositiveIntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(4),
                ],
            ),
        ),
    ]
