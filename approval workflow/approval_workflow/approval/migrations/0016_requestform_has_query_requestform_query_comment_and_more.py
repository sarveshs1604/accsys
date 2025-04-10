# Generated by Django 4.2.18 on 2025-02-23 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('approval', '0015_userprofile_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestform',
            name='has_query',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='requestform',
            name='query_comment',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='requestform',
            name='update_history',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
