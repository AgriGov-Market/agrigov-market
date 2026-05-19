from decimal import Decimal
from django.db import migrations


def create_official_prices(apps, schema_editor):
    OfficialPrice = apps.get_model('marketplace', 'OfficialPrice')

    prices = {
        'Vegetables': Decimal('250.00'),
        'Fruits': Decimal('450.00'),
        'Grains': Decimal('5000.00'),
        'Legumes': Decimal('900.00'),
        'Herbs': Decimal('150.00'),
        'Cattle': Decimal('450000.00'),
        'Sheep': Decimal('70000.00'),
        'Goats': Decimal('55000.00'),
        'Poultry': Decimal('2500.00'),
        'Rabbits': Decimal('5000.00'),
        'Eggs': Decimal('500.00'),
        'Milk': Decimal('150.00'),
        'Dairy Products': Decimal('1800.00'),
        'Honey': Decimal('4500.00'),
        'Wool': Decimal('2000.00'),
        'Vegetable Seeds': Decimal('250.00'),
        'Fruit Seeds': Decimal('600.00'),
        'Seedlings': Decimal('800.00'),
        'Trees': Decimal('5000.00'),
        'Flowers': Decimal('1200.00'),
        'Fertilizers': Decimal('7000.00'),
        'Pesticides': Decimal('5000.00'),
        'Soil & Compost': Decimal('2500.00'),
        'Irrigation Equipment': Decimal('20000.00'),
        'Tractors': Decimal('4500000.00'),
        'Machinery': Decimal('200000.00'),
        'Hand Tools': Decimal('5000.00'),
        'Sprayers': Decimal('15000.00'),
        'Animal Feed': Decimal('5000.00'),
        'Veterinary Products': Decimal('4000.00'),
        'Breeding Equipment': Decimal('20000.00'),
        'Farm Accessories': Decimal('8000.00'),
        'Plowing Services': Decimal('15000.00'),
        'Transport Services': Decimal('7000.00'),
        'Agricultural Consulting': Decimal('25000.00'),
        'Irrigation Installation': Decimal('80000.00'),
    }

    for commodity, value in prices.items():
        OfficialPrice.objects.update_or_create(
            commodity=commodity,
            defaults={
                'price_per_kg': value,
            },
        )


def reverse_official_prices(apps, schema_editor):
    OfficialPrice = apps.get_model('marketplace', 'OfficialPrice')
    commodities = [
        'Vegetables', 'Fruits', 'Grains', 'Legumes', 'Herbs',
        'Cattle', 'Sheep', 'Goats', 'Poultry', 'Rabbits',
        'Eggs', 'Milk', 'Dairy Products', 'Honey', 'Wool',
        'Vegetable Seeds', 'Fruit Seeds', 'Seedlings', 'Trees', 'Flowers',
        'Fertilizers', 'Pesticides', 'Soil & Compost', 'Irrigation Equipment',
        'Tractors', 'Machinery', 'Hand Tools', 'Sprayers',
        'Animal Feed', 'Veterinary Products', 'Breeding Equipment', 'Farm Accessories',
        'Plowing Services', 'Transport Services', 'Agricultural Consulting', 'Irrigation Installation',
    ]
    OfficialPrice.objects.filter(commodity__in=commodities).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0016_seed_default_categories'),
    ]

    operations = [
        migrations.RunPython(create_official_prices, reverse_official_prices),
    ]
