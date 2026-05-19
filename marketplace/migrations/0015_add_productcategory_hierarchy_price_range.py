from decimal import Decimal
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0014_productimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcategory',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='marketplace.productcategory'),
        ),
        migrations.AddField(
            model_name='productcategory',
            name='min_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                verbose_name='Minimum price range (DA/kg)',
                help_text='Minimum allowed price range for this category in DA per kg.',
            ),
        ),
        migrations.AddField(
            model_name='productcategory',
            name='max_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                verbose_name='Maximum price range (DA/kg)',
                help_text='Maximum allowed price range for this category in DA per kg.',
            ),
        ),
        migrations.AlterModelOptions(
            name='productcategory',
            options={'ordering': ['parent__name', 'name'], 'verbose_name_plural': 'product categories'},
        ),
    ]
