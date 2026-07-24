from django.db import migrations


def seed_master_data(apps, schema_editor):
    FraudType = apps.get_model('investigator', 'FraudType')
    PoliceStation = apps.get_model('investigator', 'PoliceStation')

    fraud_types = [
        'Financial Fraud',
        'Mobile Fraud',
        'Mobile & Financial',
        'UPI Fraud',
        'Bank Fraud',
        'Job Fraud',
        'Investment Fraud',
        'Other',
    ]
    police_stations = [
        'Bhiwandi City Police Station',
        'Nijampura Police Station',
        'Narpoli Police Station',
        'Shantinagar Police Station',
    ]

    for name in fraud_types:
        FraudType.objects.get_or_create(name=name, defaults={'is_active': True})
    for name in police_stations:
        PoliceStation.objects.get_or_create(name=name, defaults={'is_active': True})


def unseed_master_data(apps, schema_editor):
    FraudType = apps.get_model('investigator', 'FraudType')
    PoliceStation = apps.get_model('investigator', 'PoliceStation')

    FraudType.objects.filter(name__in=[
        'Financial Fraud',
        'Mobile Fraud',
        'Mobile & Financial',
        'UPI Fraud',
        'Bank Fraud',
        'Job Fraud',
        'Investment Fraud',
        'Other',
    ]).delete()
    PoliceStation.objects.filter(name__in=[
        'Bhiwandi City Police Station',
        'Nijampura Police Station',
        'Narpoli Police Station',
        'Shantinagar Police Station',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('investigator', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_master_data, unseed_master_data),
    ]
