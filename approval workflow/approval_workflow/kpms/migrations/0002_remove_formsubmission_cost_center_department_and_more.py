# Generated by Django 4.2.18 on 2025-03-10 13:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kpms', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='formsubmission',
            name='cost_center_department',
        ),
        migrations.RemoveField(
            model_name='formsubmission',
            name='profit_center_segment',
        ),
        migrations.AddField(
            model_name='formsubmission',
            name='cost_centre_department',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='formsubmission',
            name='doc_number',
            field=models.CharField(blank=True, editable=False, max_length=7, unique=True),
        ),
        migrations.AddField(
            model_name='formsubmission',
            name='profit_centre_segment',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='accountant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accountant_forms', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='bank_voucher_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='client_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_forms', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='department_expense_code',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='expense_head',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='itc_claimed',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='itc_gst_r2b',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='itc_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='project_code',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='reference_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Reviewed', 'Reviewed'), ('Approved', 'Approved')], default='Pending', max_length=50),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='tds_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='tds_application',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='tds_section',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='terminal_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='vendor_gst_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='vendor_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='vendor_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
