# Generated by Django 4.2.18 on 2025-03-20 13:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kpms', '0010_alter_bookingform_reference_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='document',
            old_name='form',
            new_name='booking',
        ),
    ]
