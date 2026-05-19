#!/usr/bin/env python
"""Test the AI image search functionality."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrigov_project.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from marketplace.models import Product, ProductImage
from marketplace.views import get_product_image_path

print("\n" + "=" * 60)
print("AI IMAGE SEARCH DIAGNOSTIC TEST")
print("=" * 60)

# Check if there are any products
products = Product.objects.filter(available=True)
print(f"\n[1] Total available products: {products.count()}")

if products.count() == 0:
    print("⚠ WARNING: No products found. Add some products first!")
else:
    # Check which products have images
    products_with_images = 0
    products_without_images = 0
    
    print("\n[2] Checking product images:")
    for product in products[:5]:  # Check first 5
        image_path = get_product_image_path(product)
        has_images = product.images.exists()
        has_main = bool(product.image)
        
        print(f"\n  Product: {product.name}")
        print(f"    - Has main image: {has_main}")
        print(f"    - Has related images: {has_images} ({product.images.count()} total)")
        print(f"    - Image path found: {image_path is not None}")
        
        if image_path:
            exists = os.path.exists(image_path)
            print(f"    - Path exists: {exists}")
            if exists:
                print(f"    - File size: {os.path.getsize(image_path)} bytes")
            products_with_images += 1
        else:
            products_without_images += 1
    
    print(f"\n[3] Summary:")
    print(f"    - Products with accessible images: ~{products_with_images}")
    print(f"    - Products without images: ~{products_without_images}")

# Test AI model loading
print(f"\n[4] Testing AI model loading:")
try:
    from marketplace.views import get_image_model_and_transform, TORCH_AVAILABLE
    
    if not TORCH_AVAILABLE:
        print("    ✗ PyTorch is not available")
    else:
        print("    ✓ PyTorch is available")
        print("    Loading model...")
        model, transform = get_image_model_and_transform()
        print("    ✓ Model loaded successfully")
except Exception as e:
    print(f"    ✗ Model loading failed: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nTroubleshooting:")
print("- If no products found: Create products in Django admin")
print("- If products have no images: Upload images for products")
print("- If path not found: Check MEDIA_ROOT and MEDIA_URL settings")
print("- If model fails: Check PyTorch installation with test_pytorch.py")
