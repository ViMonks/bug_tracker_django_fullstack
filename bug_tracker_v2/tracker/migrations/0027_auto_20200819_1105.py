# Generated by Django 3.0.8 on 2020-08-19 15:05

import bug_tracker_v2.tracker.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0026_ticketfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketfile',
            name='file',
            field=models.FileField(upload_to=bug_tracker_v2.tracker.models.ticket_file_upload_path, validators=[]),
        ),
    ]
