# The demand time fence moves from whole months to days from the plant's today
# (user decision 2026-11-02). Each tenant's months setting carries over as 30 days a
# month (0 stays off), before the months field goes.

import django.core.validators
from django.db import migrations, models


def months_to_days(apps, schema_editor):
    OptimizationConfig = apps.get_model('Tracker', 'OptimizationConfig')
    for cfg in OptimizationConfig._default_manager.all():
        cfg.demand_time_fence_days = min(365, cfg.demand_time_fence_months * 30)
        cfg.save(update_fields=['demand_time_fence_days'])


def days_to_months(apps, schema_editor):
    OptimizationConfig = apps.get_model('Tracker', 'OptimizationConfig')
    for cfg in OptimizationConfig._default_manager.all():
        cfg.demand_time_fence_months = min(12, -(-cfg.demand_time_fence_days // 30))
        cfg.save(update_fields=['demand_time_fence_months'])


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0281_demand_settings_upper_bound'),
    ]

    operations = [
        migrations.AddField(
            model_name='optimizationconfig',
            name='demand_time_fence_days',
            field=models.PositiveIntegerField(default=30, help_text="Days from the plant's today in which forecast is not planned — only orders count, since unsold forecast that close in won't arrive. A forecast month straddling the fence is planned only for its days past it. 0 = off.", validators=[django.core.validators.MaxValueValidator(365)]),
        ),
        migrations.RunPython(months_to_days, days_to_months),
        migrations.RemoveField(
            model_name='optimizationconfig',
            name='demand_time_fence_months',
        ),
    ]
