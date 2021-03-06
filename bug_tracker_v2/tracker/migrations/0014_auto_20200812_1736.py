# Generated by Django 3.0.8 on 2020-08-12 21:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0013_teaminvitation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teaminvitation',
            name='invitee',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='teaminvitation',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tracker.Team'),
        ),
    ]
