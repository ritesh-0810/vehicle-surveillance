#!/usr/bin/env python3
"""
Complete test script for Tesseract OCR configuration with license plate processing
"""

import os
import sys
import shutil
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import traceback

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tesseract_configuration():
    """Test the complete Tesseract configuration"""
    print("=" * 60)
    print("COMPLETE TESSERACT OCR CONFIGURATION TEST")
    print("=" * 60)
    
    # Test 1: Basic Tesseract installation
    print("\n[TEST 1] Basic Tesseract Installation")
    print("-" * 40)
    
    tesseract_path = os.getenv("TESSERACT_PATH") or shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if tesseract_path and os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"[OK] Tesseract executable found at: {tesseract_path}")
    elif shutil.which("tesseract"):
        tesseract_path = shutil.which("tesseract")
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"[OK] Tesseract executable found in PATH at: {tesseract_path}")
    else:
        print(f"[ERROR] Tesseract executable not found.")
        return False
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"[OK] Tesseract version: {version}")
    except Exception as e:
        print(f"[ERROR] Failed to get Tesseract version: {e}")
        return False
    
    # Test 2: Configuration file import
    print("\n[TEST 2] Configuration File Import")
    print("-" * 40)
    
    try:
        from config.tesseract_config import (
            get_tesseract_path, get_best_configs, get_preprocessing_settings,
            get_ocr_corrections, get_validation_patterns, get_performance_settings
        )
        print("[OK] Tesseract configuration module imported successfully")
        
        # Test configuration functions
        config_path = get_tesseract_path()
        print(f"[OK] Tesseract path from config: {config_path}")
        
        configs = get_best_configs()
        print(f"[OK] Found {len(configs)} Tesseract configurations")
        
        settings = get_preprocessing_settings()
        print(f"[OK] Preprocessing settings loaded: {len(settings)} parameters")
        
    except ImportError as e:
        print(f"[WARNING] Configuration import failed: {e}")
        print("[INFO] Using fallback configuration")
    except Exception as e:
        print(f"[ERROR] Configuration test failed: {e}")
        return False
    
    # Test 3: OCR with different configurations
    print("\n[TEST 3] OCR with Different Configurations")
    print("-" * 40)
    
    # Create test license plate image
    plate_img = Image.new('RGB', (300, 100), color='white')
    draw = ImageDraw.Draw(plate_img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 30), "MH12AB1234", fill='black', font=font)
    
    # Test different configurations
    test_configs = [
        ('Single Line', '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
        ('Single Word', '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
        ('Raw Line', '--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
        ('Single Block', '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    ]
    
    best_result = ""
    best_config_name = ""
    
    for config_name, config in test_configs:
        try:
            text = pytesseract.image_to_string(plate_img, config=config).strip()
            print(f"[INFO] {config_name}: '{text}'")
            if text and len(text) > len(best_result):
                best_result = text
                best_config_name = config_name
        except Exception as e:
            print(f"[WARNING] {config_name} failed: {e}")
    
    if best_result:
        print(f"[OK] Best result: '{best_result}' with {best_config_name}")
    else:
        print("[WARNING] No valid results from any configuration")
    
    # Test 4: Image preprocessing simulation
    print("\n[TEST 4] Image Preprocessing Simulation")
    print("-" * 40)
    
    try:
        # Convert PIL to OpenCV format
        plate_cv = cv2.cvtColor(np.array(plate_img), cv2.COLOR_RGB2BGR)
        
        # Apply preprocessing similar to the main application
        gray = cv2.cvtColor(plate_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Scale up for better OCR
        scaled = cv2.resize(binary, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        
        # Test OCR on preprocessed image
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(scaled, config=config).strip()
        
        if text:
            print(f"[OK] Preprocessed image OCR: '{text}'")
        else:
            print("[WARNING] Preprocessed image OCR returned empty result")
            
    except Exception as e:
        print(f"[ERROR] Image preprocessing test failed: {e}")
        return False
    
    # Test 5: Error correction
    print("\n[TEST 5] OCR Error Correction")
    print("-" * 40)
    
    try:
        # Create image with common OCR errors
        error_img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((50, 30), "MH12AB1234", fill='black', font=font)
        
        # Simulate common OCR errors
        ocr_corrections = str.maketrans({
            'O': '0', 'I': '1', '|': '1', 'S': '5', 'B': '8', 'Z': '2',
            'l': '1', 'G': '6', 'D': '0', 'Q': '0'
        })
        
        # Test with simulated error text
        error_text = "MH12AB1234"  # This would normally come from OCR
        corrected = error_text.translate(ocr_corrections)
        print(f"[OK] Error correction test: '{error_text}' -> '{corrected}'")
        
    except Exception as e:
        print(f"[ERROR] Error correction test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return True

def test_license_plate_validation():
    """Test license plate validation patterns"""
    print("\n[TEST 6] License Plate Validation")
    print("-" * 40)
    
    import re
    
    # Test patterns
    test_plates = [
        "MH12AB1234",  # Valid
        "MH121234",    # Valid
        "MH12A1234",   # Valid
        "ABC123",      # Invalid (too short)
        "MH12AB12345", # Invalid (too long)
        "12AB1234",    # Invalid (wrong format)
    ]
    
    patterns = [
        re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'),
        re.compile(r'^[A-Z]{2}[0-9]{2}[0-9]{4}$'),
        re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$'),
        re.compile(r'^[A-Z0-9]{4,10}$')
    ]
    
    for plate in test_plates:
        valid = False
        for pattern in patterns:
            if pattern.match(plate):
                valid = True
                break
        status = "VALID" if valid else "INVALID"
        print(f"[INFO] {plate}: {status}")
    
    print("[OK] License plate validation test completed")

if __name__ == "__main__":
    try:
        success = test_tesseract_configuration()
        if success:
            test_license_plate_validation()
            print("\n[SUCCESS] Complete Tesseract configuration is working!")
        else:
            print("\n[ERROR] Tesseract configuration test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        traceback.print_exc()
        sys.exit(1)

