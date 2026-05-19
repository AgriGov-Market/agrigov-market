from decimal import Decimal
from django.db import migrations


def create_categories(apps, schema_editor):
    ProductCategory = apps.get_model('marketplace', 'ProductCategory')

    category_tree = [
        {
            'name': 'Crops & Produce',
            'min_price': Decimal('50.00'),
            'max_price': Decimal('8000.00'),
            'children': [
                {'name': 'Vegetables', 'min_price': Decimal('50.00'), 'max_price': Decimal('500.00')},
                {'name': 'Fruits', 'min_price': Decimal('100.00'), 'max_price': Decimal('800.00')},
                {'name': 'Grains', 'min_price': Decimal('2000.00'), 'max_price': Decimal('8000.00')},
                {'name': 'Legumes', 'min_price': Decimal('300.00'), 'max_price': Decimal('1500.00')},
                {'name': 'Herbs', 'min_price': Decimal('50.00'), 'max_price': Decimal('300.00')},
            ],
        },
        {
            'name': 'Livestock',
            'min_price': Decimal('500.00'),
            'max_price': Decimal('800000.00'),
            'children': [
                {'name': 'Cattle', 'min_price': Decimal('200000.00'), 'max_price': Decimal('800000.00')},
                {'name': 'Sheep', 'min_price': Decimal('40000.00'), 'max_price': Decimal('120000.00')},
                {'name': 'Goats', 'min_price': Decimal('30000.00'), 'max_price': Decimal('90000.00')},
                {'name': 'Poultry', 'min_price': Decimal('500.00'), 'max_price': Decimal('5000.00')},
                {'name': 'Rabbits', 'min_price': Decimal('2000.00'), 'max_price': Decimal('8000.00')},
            ],
        },
        {
            'name': 'Animal Products',
            'min_price': Decimal('100.00'),
            'max_price': Decimal('8000.00'),
            'children': [
                {'name': 'Eggs', 'min_price': Decimal('300.00'), 'max_price': Decimal('800.00')},
                {'name': 'Milk', 'min_price': Decimal('100.00'), 'max_price': Decimal('200.00')},
                {'name': 'Dairy Products', 'min_price': Decimal('500.00'), 'max_price': Decimal('3000.00')},
                {'name': 'Honey', 'min_price': Decimal('2000.00'), 'max_price': Decimal('8000.00')},
                {'name': 'Wool', 'min_price': Decimal('500.00'), 'max_price': Decimal('3000.00')},
            ],
        },
        {
            'name': 'Seeds & Plants',
            'min_price': Decimal('100.00'),
            'max_price': Decimal('10000.00'),
            'children': [
                {'name': 'Vegetable Seeds', 'min_price': Decimal('100.00'), 'max_price': Decimal('500.00')},
                {'name': 'Fruit Seeds', 'min_price': Decimal('200.00'), 'max_price': Decimal('1000.00')},
                {'name': 'Seedlings', 'min_price': Decimal('200.00'), 'max_price': Decimal('1500.00')},
                {'name': 'Trees', 'min_price': Decimal('1000.00'), 'max_price': Decimal('10000.00')},
                {'name': 'Flowers', 'min_price': Decimal('300.00'), 'max_price': Decimal('2000.00')},
            ],
        },
        {
            'name': 'Farming Supplies',
            'min_price': Decimal('500.00'),
            'max_price': Decimal('50000.00'),
            'children': [
                {'name': 'Fertilizers', 'min_price': Decimal('2000.00'), 'max_price': Decimal('15000.00')},
                {'name': 'Pesticides', 'min_price': Decimal('1000.00'), 'max_price': Decimal('10000.00')},
                {'name': 'Soil & Compost', 'min_price': Decimal('500.00'), 'max_price': Decimal('5000.00')},
                {'name': 'Irrigation Equipment', 'min_price': Decimal('3000.00'), 'max_price': Decimal('50000.00')},
            ],
        },
        {
            'name': 'Equipment & Tools',
            'min_price': Decimal('1000.00'),
            'max_price': Decimal('10000000.00'),
            'children': [
                {'name': 'Tractors', 'min_price': Decimal('1000000.00'), 'max_price': Decimal('10000000.00')},
                {'name': 'Machinery', 'min_price': Decimal('50000.00'), 'max_price': Decimal('500000.00')},
                {'name': 'Hand Tools', 'min_price': Decimal('1000.00'), 'max_price': Decimal('10000.00')},
                {'name': 'Sprayers', 'min_price': Decimal('5000.00'), 'max_price': Decimal('30000.00')},
            ],
        },
        {
            'name': 'Animal Care',
            'min_price': Decimal('500.00'),
            'max_price': Decimal('50000.00'),
            'children': [
                {'name': 'Animal Feed', 'min_price': Decimal('2000.00'), 'max_price': Decimal('10000.00')},
                {'name': 'Veterinary Products', 'min_price': Decimal('500.00'), 'max_price': Decimal('10000.00')},
                {'name': 'Breeding Equipment', 'min_price': Decimal('5000.00'), 'max_price': Decimal('50000.00')},
                {'name': 'Farm Accessories', 'min_price': Decimal('1000.00'), 'max_price': Decimal('20000.00')},
            ],
        },
        {
            'name': 'Farm Services',
            'min_price': Decimal('2000.00'),
            'max_price': Decimal('200000.00'),
            'children': [
                {'name': 'Plowing Services', 'min_price': Decimal('5000.00'), 'max_price': Decimal('30000.00')},
                {'name': 'Transport Services', 'min_price': Decimal('2000.00'), 'max_price': Decimal('20000.00')},
                {'name': 'Agricultural Consulting', 'min_price': Decimal('5000.00'), 'max_price': Decimal('50000.00')},
                {'name': 'Irrigation Installation', 'min_price': Decimal('20000.00'), 'max_price': Decimal('200000.00')},
            ],
        },
    ]

    for category_data in category_tree:
        parent_obj, created = ProductCategory.objects.update_or_create(
            name=category_data['name'],
            defaults={
                'parent': None,
                'min_price': category_data['min_price'],
                'max_price': category_data['max_price'],
                'is_active': True,
            },
        )
        for child_data in category_data['children']:
            ProductCategory.objects.update_or_create(
                name=child_data['name'],
                defaults={
                    'parent': parent_obj,
                    'min_price': child_data['min_price'],
                    'max_price': child_data['max_price'],
                    'is_active': True,
                },
            )


def reverse_create_categories(apps, schema_editor):
    ProductCategory = apps.get_model('marketplace', 'ProductCategory')
    category_names = [
        'Crops & Produce', 'Livestock', 'Animal Products', 'Seeds & Plants',
        'Farming Supplies', 'Equipment & Tools', 'Animal Care', 'Farm Services',
        'Vegetables', 'Fruits', 'Grains', 'Legumes', 'Herbs',
        'Cattle', 'Sheep', 'Goats', 'Poultry', 'Rabbits',
        'Eggs', 'Milk', 'Dairy Products', 'Honey', 'Wool',
        'Vegetable Seeds', 'Fruit Seeds', 'Seedlings', 'Trees', 'Flowers',
        'Fertilizers', 'Pesticides', 'Soil & Compost', 'Irrigation Equipment',
        'Tractors', 'Machinery', 'Hand Tools', 'Sprayers',
        'Animal Feed', 'Veterinary Products', 'Breeding Equipment', 'Farm Accessories',
        'Plowing Services', 'Transport Services', 'Agricultural Consulting', 'Irrigation Installation',
    ]
    ProductCategory.objects.filter(name__in=category_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0015_add_productcategory_hierarchy_price_range'),
    ]

    operations = [
        migrations.RunPython(create_categories, reverse_create_categories),
    ]
