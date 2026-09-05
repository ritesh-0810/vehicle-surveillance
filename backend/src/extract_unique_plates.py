import os
import sys
import ssl
import cv2
import easyocr
import numpy as np
from collections import Counter
from difflib import SequenceMatcher
import re
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import traceback
import pytesseract
from Levenshtein import distance as levenshtein_distance

# Bypass SSL verification for model downloads (e.g. on macOS)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# Fix encoding issues for Windows
if sys.platform.startswith('win'):
    # Set environment variables for UTF-8 support
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Try to set console to UTF-8
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except:
        pass

# Load environment variables
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

# Connect to MongoDB
try:
    client = MongoClient(MONGODB_URI)
    db = client["number_plate_db"]
    results_collection = db["plate_detections"]
    error_collection = db["error_detections"]
    print(f"[OK] Connected to MongoDB successfully")
except Exception as e:
    print(f"[ERROR] Failed to connect to MongoDB: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Multiple regex patterns for various license plate formats
VALID_PLATE_PATTERNS = [
    re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'),  # e.g., MH12AB1234
    re.compile(r'^[A-Z]{2}[0-9]{2}[0-9]{4}$'),  # e.g., MH121234
    re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$'),  # Other variants
    re.compile(r'^[A-Z0-9]{4,10}$')  # Fallback general pattern
]

# OCR error correction mapping
OCR_CORRECTIONS = str.maketrans({
    'O': '0',
    'I': '1',
    '|': '1',
    'S': '5',
    'B': '8',
    'Z': '2',
    'l': '1',
    'G': '6',
    'D': '0',
    'Q': '0'
})

# Safe progress bar function that works with Windows encoding
def print_progress_bar(current, total, prefix='Progress', suffix='Complete', length=50):
    """Print a progress bar without Unicode characters"""
    try:
        percent = (current / total) * 100
        filled_length = int(length * current // total)
        # Use ASCII characters instead of Unicode
        bar = '#' * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix}: |{bar}| {percent:.1f}% {suffix}', end='', flush=True)
        if current == total:
            print()  # New line when complete
    except Exception as e:
        # Fallback to simple percentage display
        try:
            percent = (current / total) * 100
            print(f'{prefix}: {percent:.1f}% {suffix}')
        except:
            print(f'{prefix}: {current}/{total} {suffix}')

# Initialize EasyOCR reader with error handling
def initialize_easyocr():
    """Initialize EasyOCR with proper error handling for Windows encoding issues"""
    try:
        # Try to use GPU if available
        use_gpu = True
        try:
            import torch
            if not torch.cuda.is_available():
                use_gpu = False
                print("[INFO] CUDA not available, falling back to CPU")
        except ImportError:
            use_gpu = False
            print("[INFO] PyTorch not installed, falling back to CPU")

        # Create model cache directory
        model_cache_dir = os.path.join(os.getcwd(), 'model_cache')
        os.makedirs(model_cache_dir, exist_ok=True)

        # Initialize with verbose=False to avoid progress bar issues
        reader = easyocr.Reader(
            ['en'],
            gpu=use_gpu,
            model_storage_directory=model_cache_dir,
            download_enabled=True,
            quantize=True,
            verbose=False  # This prevents the problematic progress bar
        )
        
        print(f"[OK] Initialized EasyOCR reader with GPU={use_gpu}")
        return reader
        
    except UnicodeEncodeError as e:
        print(f"[WARNING] Unicode encoding error during EasyOCR initialization: {str(e)}")
        print("[INFO] Trying alternative initialization method...")
        
        # Try with minimal configuration
        try:
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            print("[OK] Initialized EasyOCR reader with minimal configuration")
            return reader
        except Exception as e2:
            print(f"[ERROR] Alternative EasyOCR initialization also failed: {str(e2)}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize EasyOCR: {str(e)}")
        traceback.print_exc()
        return None

# Initialize the reader
reader = initialize_easyocr()

# Configure Tesseract path if not in PATH
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "tesseract")
if TESSERACT_PATH != "tesseract":
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Similarity check using Levenshtein distance
def is_similar_plate(plate1, plate2, similarity_threshold=0.75):
    if plate1 == plate2:
        return True
    if abs(len(plate1) - len(plate2)) > 2:
        return False
    clean1 = re.sub(r'[^A-Z0-9]', '', plate1)
    clean2 = re.sub(r'[^A-Z0-9]', '', plate2)
    if clean1 in clean2 or clean2 in clean1:
        return True
    # Use Levenshtein distance for more accurate comparison
    max_len = max(len(clean1), len(clean2))
    if max_len == 0:
        return False
    lev_distance = levenshtein_distance(clean1, clean2)
    lev_similarity = 1 - (lev_distance / max_len)
    return lev_similarity >= similarity_threshold

def group_similar_plates(plates):
    if not plates:
        return []
    groups = []
    plates_sorted = sorted(plates, key=len)
    for plate in plates_sorted:
        matched = False
        for group in groups:
            if is_similar_plate(plate, group[0]):
                group.append(plate)
                matched = True
                break
        if not matched:
            groups.append([plate])
    return groups

def correct_common_ocr_errors(text):
    """Apply common OCR error corrections."""
    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
    corrected = cleaned.translate(OCR_CORRECTIONS)
    return corrected

def validate_plate_format(plate):
    """Check if the plate matches any valid format."""
    for pattern in VALID_PLATE_PATTERNS:
        if pattern.match(plate):
            return True
    return False

def detect_plate_region(image):
    """Detect potential license plate regions using contours."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        # Edge detection
        edges = cv2.Canny(blur, 50, 150)
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # Filter contours by area and aspect ratio
        candidate_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / float(h)
            # License plates typically have aspect ratio between 2-5
            if area > 1000 and 1.5 < aspect_ratio < 7:
                candidate_regions.append((x, y, w, h))
        # Return regions sorted by area (largest first)
        return sorted(candidate_regions, key=lambda r: r[2] * r[3], reverse=True)
    except Exception as e:
        print(f"[ERROR] Error in plate region detection: {str(e)}")
        return []

def preprocess_image(image):
    """Enhanced image preprocessing for better OCR accuracy."""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10, templateWindowSize=7, searchWindowSize=21)
        # Apply adaptive thresholding for better text extraction
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        # Dilate to connect broken characters
        kernel = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=1)
        # Convert back to regular polarity
        binary_normal = cv2.bitwise_not(dilated)
        # Create versions of the image
        return {
            "gray": gray,
            "enhanced": enhanced,
            "denoised": denoised,
            "binary": binary_normal,
            "original": image
        }
    except Exception as e:
        print(f"[ERROR] Error in image preprocessing: {str(e)}")
        return {"original": image, "gray": cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)}

def process_image_with_tesseract(image_dict):
    """Use Tesseract OCR as a fallback method."""
    try:
        results = []
        # Try different image versions
        for img_type, img in image_dict.items():
            if img_type == "original":  # Skip color image
                continue
            # Configure Tesseract for license plates
            config = '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            # Enlarge image for better recognition
            scaled = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # Run OCR
            text = pytesseract.image_to_string(scaled, config=config).strip()
            if text:
                # Clean and validate
                cleaned = correct_common_ocr_errors(text)
                if cleaned and len(cleaned) >= 4:
                    results.append(cleaned)
        return results
    except Exception as e:
        print(f"[WARNING] Tesseract OCR failed: {str(e)}")
        return []

def combine_ocr_results(image_dict, confidence_threshold=0.5):
    """Combine results from multiple OCR methods for better accuracy."""
    all_results = []
    
    # Method 1: EasyOCR (if available)
    if reader is not None:
        try:
            # For preprocessed binary image
            binary_results = reader.readtext(
                image_dict["binary"],
                detail=1,  # Get confidence scores
                paragraph=False
            )
            for detection in binary_results:
                bbox, text, confidence = detection
                if confidence >= confidence_threshold:
                    cleaned = correct_common_ocr_errors(text)
                    if cleaned:
                        all_results.append((cleaned, confidence, "easyocr_binary"))
        except Exception as e:
            print(f"[WARNING] EasyOCR on binary failed: {str(e)}")

        try:
            # For enhanced image
            enhanced_results = reader.readtext(
                image_dict["enhanced"],
                detail=1,  # Get confidence scores
                paragraph=False
            )
            for detection in enhanced_results:
                bbox, text, confidence = detection
                if confidence >= confidence_threshold:
                    cleaned = correct_common_ocr_errors(text)
                    if cleaned:
                        all_results.append((cleaned, confidence, "easyocr_enhanced"))
        except Exception as e:
            print(f"[WARNING] EasyOCR on enhanced failed: {str(e)}")
    else:
        print("[WARNING] EasyOCR not available, using Tesseract only")

    # Method 2: Try Tesseract as fallback
    tesseract_results = process_image_with_tesseract(image_dict)
    for text in tesseract_results:
        # Assign a default confidence to tesseract results
        all_results.append((text, 0.6, "tesseract"))

    # Deduplicate and sort by confidence
    unique_results = {}
    for text, confidence, method in all_results:
        if text not in unique_results or confidence > unique_results[text][0]:
            unique_results[text] = (confidence, method)

    # Return sorted by confidence
    return sorted([(text, conf, method) for text, (conf, method) in unique_results.items()],
                  key=lambda x: x[1], reverse=True)

def process_image_file(image_path):
    """Process a single image file to detect number plates."""
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"[WARNING] Could not read image: {os.path.basename(image_path)}")
            return None

        valid_plates = []
        confidence_scores = {}
        methods_used = {}

        # The image is already a cropped plate from step 1 (YOLOv5)
        # Preprocess directly for OCR
        scaled_image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        image_versions = preprocess_image(scaled_image)

        # Run OCR methods on full cropped image
        results = combine_ocr_results(image_versions)
        for plate, confidence, method in results:
            if validate_plate_format(plate):
                valid_plates.append(plate)
                confidence_scores[plate] = confidence
                methods_used[plate] = method

        # If no valid plates found directly, try region contours as secondary pass
        if not valid_plates:
            regions = detect_plate_region(image)
            if regions:
                for i, (x, y, w, h) in enumerate(regions[:3]):
                    margin = 5
                    x_start = max(0, x - margin)
                    y_start = max(0, y - margin)
                    x_end = min(image.shape[1], x + w + margin)
                    y_end = min(image.shape[0], y + h + margin)
                    crop = image[y_start:y_end, x_start:x_end]

                    if crop.shape[0] < 10 or crop.shape[1] < 10:
                        continue

                    scaled = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    region_versions = preprocess_image(scaled)
                    region_results = combine_ocr_results(region_versions)
                    for plate, confidence, method in region_results:
                        if validate_plate_format(plate):
                            valid_plates.append(plate)
                            confidence_scores[plate] = confidence
                            methods_used[plate] = f"region_{method}"

        # Fallback: Parse plate text from filename (saved by step 1 YOLO+EasyOCR)
        if not valid_plates:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            clean_name = re.sub(r'[^A-Z0-9]', '', base_name.split("_")[0].upper())
            if validate_plate_format(clean_name):
                valid_plates.append(clean_name)
                confidence_scores[clean_name] = 0.75
                methods_used[clean_name] = "filename_fallback"

        return {
            "plates": valid_plates,
            "confidence": confidence_scores,
            "methods": methods_used
        }
    except Exception as e:
        print(f"[ERROR] Error processing {os.path.basename(image_path)}: {str(e)}")
        traceback.print_exc()
        return None

def store_results_in_mongodb(results_data, session_id):
    try:
        # Fetch session metadata
        session_meta = db["sessions"].find_one({"session_id": session_id})
        if not session_meta:
            print(f"[ERROR] No session metadata found for session_id: {session_id}")
            return

        # Extract fields
        location = session_meta.get("location")
        latitude = session_meta.get("latitude")
        longitude = session_meta.get("longitude")

        # Use os.path.join with normpath to handle Windows paths correctly
        plates_folder = os.path.normpath(os.path.join("processed_data", session_id, "plates")).replace("\\", "/")
        video_output = os.path.normpath(os.path.join("processed_data", session_id, "video_output")).replace("\\", "/")
        video_filename = f"{session_id}_traffic.mp4"
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")

        inserted_count = 0
        for plate_entry in results_data["all_plates"]:
            plate = plate_entry["plate"]
            count = plate_entry["count"]
            confidence = plate_entry.get("avg_confidence", 0.0)
            methods = plate_entry.get("methods", [])

            image_path = os.path.normpath(os.path.join(plates_folder, f"{plate}.jpg")).replace("\\", "/")

            document = {
                "session_id": session_id,
                "plate_number": plate,
                "image_path": image_path,
                "timestamp": now_iso,
                "video_filename": video_filename,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "status": "Processing complete",
                "progress": 100,
                "plates_folder": plates_folder,
                "video_output": video_output,
                "confidence": confidence,
                "detection_methods": methods,
                "detection_count": count
            }

            results_collection.insert_one(document)
            inserted_count += 1

        print(f"[OK] Inserted {inserted_count} plate records into MongoDB")
    except Exception as e:
        print(f"[ERROR] Failed to store results in MongoDB: {str(e)}")
        traceback.print_exc()

def store_error_plate(plate, image_path, session_id):
    """Store plates that failed validation for further analysis."""
    try:
        document = {
            "session_id": session_id,
            "plate_candidate": plate,
            "image_path": image_path,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "error"
        }
        error_collection.insert_one(document)
        print(f"[INFO] Stored error plate for analysis: {plate}")
    except Exception as e:
        print(f"[WARNING] Failed to store error plate: {str(e)}")

def main():
    print("=" * 50)
    print("ENHANCED NUMBER PLATE EXTRACTION SCRIPT STARTING")
    print("=" * 50)
    
    try:
        if len(sys.argv) < 2:
            print("Usage: python extract_unique_plates.py <session_id> [plates_dir]")
            sys.exit(1)

        session_id = sys.argv[1]
        print(f"[INFO] Session ID: {session_id}")

        # Check explicit CLI argument, otherwise try relative and absolute paths
        if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]):
            plates_dir = os.path.normpath(sys.argv[2])
        else:
            candidates = [
                os.path.normpath(os.path.join("processed_data", session_id, "plates")),
                os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_data", session_id, "plates")),
                os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "processed_data", session_id, "plates"))
            ]
            plates_dir = candidates[0]
            for cand in candidates:
                if os.path.isdir(cand):
                    plates_dir = cand
                    break

        print(f"[INFO] Starting extraction for session: {session_id}")
        print(f"[INFO] Looking for plates in directory: {plates_dir}")
        print(f"[INFO] Current working directory: {os.getcwd()}")

        if not os.path.isdir(plates_dir):
            print(f"[ERROR] Plates directory not found for session ID: {session_id}")
            print(f"[INFO] Checking if parent directory exists: {os.path.dirname(plates_dir)}")
            if os.path.exists(os.path.dirname(plates_dir)):
                print(f"[INFO] Parent directory exists, contents: {os.listdir(os.path.dirname(plates_dir))}")
            sys.exit(1)

        print(f"[OK] Found plates directory with contents: {os.listdir(plates_dir)}")

        start_time = datetime.now()
        print(f"[INFO] Starting plate detection for session: {session_id}")

        plate_counts = Counter()
        plate_confidences = {}
        plate_methods = {}

        image_files = [f for f in os.listdir(plates_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        total_files = len(image_files)
        print(f"[INFO] Found {total_files} image files to process")

        for i, filename in enumerate(sorted(image_files), 1):
            image_path = os.path.join(plates_dir, filename)
            result = process_image_file(image_path)
            
            if result and result["plates"]:
                for plate in result["plates"]:
                    plate_counts[plate] += 1
                    # Track confidence and methods
                    if plate not in plate_confidences:
                        plate_confidences[plate] = []
                    plate_confidences[plate].append(result["confidence"].get(plate, 0.0))
                    
                    if plate not in plate_methods:
                        plate_methods[plate] = set()
                    plate_methods[plate].add(result["methods"].get(plate, "unknown"))
            else:
                print(f"[WARNING] No valid plates found in {filename}")

            # Show progress every 10 files using safe progress bar
            if i % 10 == 0 or i == total_files:
                print_progress_bar(i, total_files, prefix='Progress', suffix='Complete')

        print("\n" + "=" * 50)
        
        if not plate_counts:
            print("[ERROR] No valid plates detected in any images")
            # Update MongoDB to indicate completion even with no plates
            db["sessions"].update_one(
                {"session_id": session_id},
                {"$set": {"status": "Completed - No valid plates detected", "progress": 100}}
            )
            return

        # Group similar plates using improved algorithm
        plate_groups = group_similar_plates(list(plate_counts.elements()))
        most_frequent_plates = []
        
        for group in plate_groups:
            group_counter = Counter(group)
            most_common = group_counter.most_common(1)[0]
            # Retain all detected plate groups (frequency >= 1)
            most_frequent_plates.append(most_common)

        if not most_frequent_plates:
            print("[ERROR] No plates detected")
            # Update MongoDB to indicate completion even with no frequent plates
            db["sessions"].update_one(
                {"session_id": session_id},
                {"$set": {"status": "Completed - No plates", "progress": 100}}
            )
            return

        # Sort by frequency and confidence
        most_frequent_plates.sort(key=lambda x: (-x[1], len(x[0])))

        processing_time = (datetime.now() - start_time).total_seconds()

        # Calculate average confidence for each plate
        avg_confidences = {}
        for plate in plate_confidences:
            if plate_confidences[plate]:
                avg_confidences[plate] = sum(plate_confidences[plate]) / len(plate_confidences[plate])
            else:
                avg_confidences[plate] = 0.0

        # Prepare enhanced results data
        results_data = {
            "directory": plates_dir,
            "timestamp": datetime.now().isoformat(),
            "processing_time": processing_time,
            "images_processed": total_files,
            "unique_plates": len(plate_counts),
            "total_detections": sum(plate_counts.values()),
            "top_plates": [
                {
                    "plate": plate,
                    "count": count,
                    "avg_confidence": avg_confidences.get(plate, 0.0),
                    "methods": list(plate_methods.get(plate, ["unknown"]))
                }
                for plate, count in most_frequent_plates[:10]
            ],
            "all_plates": [
                {
                    "plate": plate,
                    "count": count,
                    "avg_confidence": avg_confidences.get(plate, 0.0),
                    "methods": list(plate_methods.get(plate, ["unknown"]))
                }
                for plate, count in plate_counts.items()
            ]
        }

        # Store results in MongoDB with enhanced metadata
        store_results_in_mongodb(results_data, session_id)

        # Save detailed results file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(plates_dir, f"plate_results_{timestamp}.txt")
        
        with open(output_file, "w", encoding='utf-8') as f:
            f.write("ENHANCED NUMBER PLATE DETECTION RESULTS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Images processed: {total_files}\n")
            f.write(f"Valid detections: {sum(plate_counts.values())}\n")
            f.write(f"Unique plates: {len(plate_counts)}\n")
            f.write(f"Processing time: {processing_time:.2f} seconds\n\n")
            f.write("TOP DETECTED PLATES:\n")
            f.write("Rank | Plate      | Count | Confidence | Methods\n")
            f.write("---- | ---------- | ----- | ---------- | -------\n")
            
            for rank, (plate, count) in enumerate(most_frequent_plates, 1):
                confidence = avg_confidences.get(plate, 0.0)
                methods = ", ".join(plate_methods.get(plate, ["unknown"]))
                f.write(f"{rank:4} | {plate:10} | {count:5} | {confidence:.2f}      | {methods}\n")

        print("\n[RESULTS] ENHANCED DETECTION RESULTS:")
        print(f"[INFO] Directory: {plates_dir}")
        print(f"[INFO] Images processed: {total_files}")
        print(f"[INFO] Unique plates found: {len(plate_counts)}")
        print(f"[INFO] Total detections: {sum(plate_counts.values())}")
        print(f"[INFO] Processing time: {processing_time:.2f} seconds\n")

        print("[RESULTS] TOP PLATES:")
        for rank, (plate, count) in enumerate(most_frequent_plates[:10], 1):
            confidence = avg_confidences.get(plate, 0.0)
            methods = ", ".join(plate_methods.get(plate, ["unknown"]))
            print(f"{rank:2}. {plate} ({count} detections, {confidence:.2f} confidence, methods: {methods})")

        print(f"\n[INFO] Full results saved to: {output_file}")

        # Update MongoDB to indicate successful completion
        db["sessions"].update_one(
            {"session_id": session_id},
            {"$set": {"status": "Processing complete", "progress": 100}}
        )

        print("=" * 50)
        print("ENHANCED NUMBER PLATE EXTRACTION SCRIPT COMPLETED SUCCESSFULLY")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] Unhandled exception in main: {str(e)}")
        traceback.print_exc()
        # Update MongoDB to indicate error
        try:
            db["sessions"].update_one(
                {"session_id": session_id},
                {"$set": {"status": f"Error: {str(e)}", "progress": 75}}
            )
        except Exception as db_error:
            print(f"[ERROR] Failed to update error status in MongoDB: {str(db_error)}")
        sys.exit(1)

if __name__ == "__main__":
    main()