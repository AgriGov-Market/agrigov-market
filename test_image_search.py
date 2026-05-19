#!/usr/bin/env python
"""Test AI image search with actual product images."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrigov_project.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from marketplace.models import Product, ProductImage
from marketplace.views import (
    get_image_features, get_product_image_path, 
    TORCH_AVAILABLE, find_similar_products_from_image
)
from django.core.files.base import ContentFile
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

print("\n" + "=" * 60)
print("AI IMAGE SEARCH FUNCTION TEST")
print("=" * 60)

if not TORCH_AVAILABLE:
    print("✗ PyTorch not available")
    sys.exit(1)

# Get products with images
products = Product.objects.filter(available=True)
products_with_images = []

for product in products:
    image_path = get_product_image_path(product)
    if image_path and os.path.exists(image_path):
        products_with_images.append((product, image_path))

if not products_with_images:
    print("✗ No products with valid images found")
    sys.exit(1)

print(f"\nFound {len(products_with_images)} products with images")

# Test: Use first product's image as query
test_product, test_image_path = products_with_images[0]

print(f"\n[TEST] Using '{test_product.name}' image as search query")
print(f"Image path: {test_image_path}")

try:
    # Get query features
    query_features = get_image_features(test_image_path)
    print(f"✓ Query features extracted: {query_features.shape}")
    
    # Test all products
    print(f"\n[RESULTS] Similarity scores for all products:")
    print(f"{'Product':<30} {'Similarity':<15} {'Image Found'}")
    print("-" * 60)
    
    scores = []
    for product in Product.objects.filter(available=True):
        image_path = get_product_image_path(product)
        
        if not image_path or not os.path.exists(image_path):
            print(f"{product.name:<30} {'N/A':<15} No")
            continue
        
        try:
            product_features = get_image_features(image_path)
            score = float(cosine_similarity([query_features], [product_features])[0][0])
            scores.append((product.name, score, True))
            print(f"{product.name:<30} {score:<15.6f} Yes")
        except Exception as e:
            print(f"{product.name:<30} {'ERROR':<15} (Error: {str(e)[:20]})")
            scores.append((product.name, 0, False))
    
    # Show top matches
    valid_scores = [(name, score) for name, score, success in scores if success]
    if valid_scores:
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        print(f"\n[TOP MATCHES]")
        for i, (name, score) in enumerate(valid_scores[:5], 1):
            print(f"  {i}. {name}: {score:.6f}")
    
    # Now test the actual find_similar_products_from_image function
    print(f"\n[FUNCTION TEST] Testing find_similar_products_from_image()...")
    
    # Open the test image as a file
    with open(test_image_path, 'rb') as f:
        results = find_similar_products_from_image(f, top_n=10)
    
    print(f"✓ Function returned {len(results)} results")
    if results:
        print(f"  Top result: {results[0].name}")
        for i, result in enumerate(results[:5], 1):
            print(f"    {i}. {result.name}")
    else:
        print("  ⚠ WARNING: Function returned empty results!")
    
except Exception as e:
    import traceback
    print(f"✗ Error during test: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
