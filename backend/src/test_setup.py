# Create a test script: test_setup.py
import sys
import torch
import cv2
import numpy as np

print("Testing installation...")
print(f"Python version: {sys.version}")
print(f"OpenCV version: {cv2.__version__}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

try:
    import easyocr
    print("✓ EasyOCR installed")
except ImportError:
    print("✗ EasyOCR not installed")

try:
    from paddleocr import PaddleOCR
    print("✓ PaddleOCR installed")
except ImportError:
    print("✗ PaddleOCR not installed")

try:
    from transformers import TrOCRProcessor
    print("✓ Transformers installed")
except ImportError:
    print("✗ Transformers not installed")

try:
    import pytesseract
    print("✓ Pytesseract installed")
except ImportError:
    print("✗ Pytesseract not installed")

try:
    import albumentations
    print("✓ Albumentations installed")
except ImportError:
    print("✗ Albumentations not installed")

print("Setup test complete!")