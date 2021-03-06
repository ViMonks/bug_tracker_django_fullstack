# Generated by Django 3.0.8 on 2020-08-18 19:59

import bug_tracker_v2.tracker.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0025_project_subscribers'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('file', models.FileField(upload_to=bug_tracker_v2.tracker.models.ticket_file_upload_path)),
                ('uploaded_on', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='tracker.Ticket')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploads', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
