from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from marketplace.models import UserProfile, Product


class ProductCrudTest(TestCase):
    def setUp(self):
        # create farmer user
        self.farmer = User.objects.create_user(username='farmer1', password='pass')
        UserProfile.objects.create(user=self.farmer, user_type='farmer', is_validated=True)

        # login client as farmer
        self.client.login(username='farmer1', password='pass')

        # create a product owned by farmer
        self.product = Product.objects.create(
            farmer=self.farmer,
            name='Test Product',
            description='Sample',
            quantity=Decimal('10.00'),
            unit='kg',
            price_per_unit=Decimal('100.00'),
            available=True,
        )

    def test_edit_product_get_and_post(self):
        url = reverse('edit_product', args=[self.product.id])
        # GET should return 200
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # POST updated data
        data = {
            'name': 'Test Product Updated',
            'category': '',
            'farm': '',
            'description': 'Updated',
            'quantity': '8.00',
            'unit': 'kg',
            'price_per_unit': '120.00',
        }
        resp = self.client.post(url, data, follow=True)
        # should redirect to farmer_dashboard
        self.assertEqual(resp.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(str(self.product.price_per_unit), '120.00')
        self.assertEqual(self.product.name, 'Test Product Updated')

    def test_delete_product_post(self):
        url = reverse('delete_product', args=[self.product.id])
        # non-POST should redirect to farmer_dashboard
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)

        # POST delete should remove product
        resp = self.client.post(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        exists = Product.objects.filter(id=self.product.id).exists()
        self.assertFalse(exists)

    def test_products_dashboard_uses_database_product_cards(self):
        url = reverse('products_dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Product')
        self.assertContains(resp, reverse('product_detail', args=[self.product.id]))
        self.assertContains(resp, reverse('edit_product', args=[self.product.id]))
