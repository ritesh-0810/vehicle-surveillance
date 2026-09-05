"""
Tesseract OCR Configuration for License Plate Recognition
"""

import os

# Tesseract executable path
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Optimized Tesseract configurations for license plate recognition
TESSERACT_CONFIGS = [
    # Single text line (best for most license plates)
    {
        'name': 'single_line',
        'config': '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'description': 'Single text line recognition'
    },
    # Single word (alternative for clear plates)
    {
        'name': 'single_word',
        'config': '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'description': 'Single word recognition'
    },
    # Raw line (no specific shape assumptions)
    {
        'name': 'raw_line',
        'config': '--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'description': 'Raw line recognition'
    },
    # Single character (for very clear images)
    {
        'name': 'single_char',
        'config': '--oem 3 --psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'description': 'Single character recognition'
    },
    # Treat image as single text block
    {
        'name': 'single_block',
        'config': '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'description': 'Single text block recognition'
    }
]

# Image preprocessing settings
IMAGE_PREPROCESSING = {
    'scale_factor': 3.0,  # Scale factor for image enlargement
    'clahe_clip_limit': 3.0,  # CLAHE clip limit
    'clahe_tile_size': (8, 8),  # CLAHE tile size
    'gaussian_blur_kernel': (3, 3),  # Gaussian blur kernel size
    'morphology_kernel_size': (2, 2),  # Morphology kernel size
    'denoise_h': 10,  # Denoising parameter
    'denoise_template_window': 7,  # Denoising template window
    'denoise_search_window': 21,  # Denoising search window
    'high_contrast_alpha': 1.5,  # High contrast alpha
    'high_contrast_beta': 30,  # High contrast beta
}

# OCR error correction mapping
OCR_CORRECTIONS = str.maketrans({
    'O': '0',  # Letter O to number 0
    'I': '1',  # Letter I to number 1
    '|': '1',  # Pipe to number 1
    'S': '5',  # Letter S to number 5
    'B': '8',  # Letter B to number 8
    'Z': '2',  # Letter Z to number 2
    'l': '1',  # Lowercase l to number 1
    'G': '6',  # Letter G to number 6
    'D': '0',  # Letter D to number 0
    'Q': '0',  # Letter Q to number 0
    'T': '7',  # Letter T to number 7 (sometimes)
    'A': '4',  # Letter A to number 4 (sometimes)
})

# License plate validation patterns
VALID_PLATE_PATTERNS = [
    r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$',  # e.g., MH12AB1234
    r'^[A-Z]{2}[0-9]{2}[0-9]{4}$',  # e.g., MH121234
    r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$',  # Other variants
    r'^[A-Z0-9]{4,10}$'  # Fallback general pattern
]

# Performance settings
PERFORMANCE_SETTINGS = {
    'max_image_versions': 5,  # Maximum number of image versions to process
    'confidence_threshold': 0.5,  # Minimum confidence threshold
    'min_plate_length': 4,  # Minimum plate length
    'max_plate_length': 12,  # Maximum plate length
    'early_break_length': 6,  # Break early if plate length >= this
}

import shutil

def get_tesseract_path():
    """Get the configured Tesseract path"""
    return os.getenv("TESSERACT_PATH") or shutil.which("tesseract") or TESSERACT_PATH

def get_best_configs():
    """Get the best Tesseract configurations for license plates"""
    return TESSERACT_CONFIGS[:3]  # Return top 3 configurations

def get_all_configs():
    """Get all available Tesseract configurations"""
    return TESSERACT_CONFIGS

def get_preprocessing_settings():
    """Get image preprocessing settings"""
    return IMAGE_PREPROCESSING

def get_ocr_corrections():
    """Get OCR error correction mapping"""
    return OCR_CORRECTIONS

def get_validation_patterns():
    """Get license plate validation patterns"""
    return VALID_PLATE_PATTERNS

def get_performance_settings():
    """Get performance settings"""
    return PERFORMANCE_SETTINGS

