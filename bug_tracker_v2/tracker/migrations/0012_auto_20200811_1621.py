# Generated by Django 3.0.8 on 2020-08-11 20:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0011_auto_20200811_0943'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='comment',
            unique_together=set(),
        ),
    ]
