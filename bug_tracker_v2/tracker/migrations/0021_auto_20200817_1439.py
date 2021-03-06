# Generated by Django 3.0.8 on 2020-08-17 18:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0020_auto_20200817_1400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammembership',
            name='user',
            field=models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.DO_NOTHING, related_name='memberships', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='teammembership',
            unique_together={('user', 'team')},
        ),
    ]
