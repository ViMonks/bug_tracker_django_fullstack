# Generated by Django 3.0.8 on 2020-08-12 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_is_manager'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_viewed_project_pk',
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
    ]
