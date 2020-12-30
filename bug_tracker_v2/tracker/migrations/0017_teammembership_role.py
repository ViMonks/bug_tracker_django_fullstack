# Generated by Django 3.0.8 on 2020-08-17 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0016_auto_20200817_1253'),
    ]

    operations = [
        migrations.AddField(
            model_name='teammembership',
            name='role',
            field=models.IntegerField(choices=[(1, 'Member'), (2, 'Manager'), (3, 'Owner')], default=1),
        ),
    ]