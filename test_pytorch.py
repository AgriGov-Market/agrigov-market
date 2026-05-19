#!/usr/bin/env python
"""Test if PyTorch and required packages are properly installed."""

import sys
import os

# Add the project to the path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("Testing PyTorch and AI dependencies...")
print("=" * 60)

# Test 1: numpy
print("\n[1/6] Testing numpy...")
try:
    import numpy as np
    print(f"✓ numpy {np.__version__} is installed")
except Exception as e:
    print(f"✗ numpy failed: {e}")
    sys.exit(1)

# Test 2: PIL
print("\n[2/6] Testing PIL (Pillow)...")
try:
    from PIL import Image
    print(f"✓ PIL is installed")
except Exception as e:
    print(f"✗ PIL failed: {e}")
    sys.exit(1)

# Test 3: scikit-learn
print("\n[3/6] Testing scikit-learn...")
try:
    from sklearn.metrics.pairwise import cosine_similarity
    print(f"✓ scikit-learn is installed")
except Exception as e:
    print(f"✗ scikit-learn failed: {e}")
    sys.exit(1)

# Test 4: torch
print("\n[4/6] Testing torch (this may take a moment)...")
try:
    import torch
    print(f"✓ torch {torch.__version__} is installed")
except Exception as e:
    print(f"✗ torch failed: {e}")
    sys.exit(1)

# Test 5: torchvision
print("\n[5/6] Testing torchvision (this may take a moment)...")
try:
    import torchvision
    print(f"✓ torchvision {torchvision.__version__} is installed")
except Exception as e:
    print(f"✗ torchvision failed: {e}")
    sys.exit(1)

# Test 6: ResNet50 model
print("\n[6/6] Loading ResNet50 model (this may take a moment)...")
try:
    from torchvision import models
    print("  Loading model weights...")
    try:
        weights = models.ResNet50_Weights.DEFAULT
        model = models.resnet50(weights=weights)
    except:
        model = models.resnet50(pretrained=True)
    print(f"✓ ResNet50 model loaded successfully")
except Exception as e:
    print(f"✗ ResNet50 failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All dependencies are properly installed!")
print("=" * 60)
print("\nYour AI image search should now work correctly.")
