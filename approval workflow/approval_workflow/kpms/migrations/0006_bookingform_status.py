# Generated by Django 4.2.18 on 2025-03-18 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kpms', '0005_bookingform_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingform',
            name='status',
            field=models.CharField(choices=[('In Progress', 'In Progress'), ('Raise Query', 'Raise Query'), ('Closed', 'Closed')], default='In Progress', max_length=20),
        ),
    ]
