import cv2
import yolov5
import os
import easyocr
import torch
import torch.serialization
from yolov5.models.yolo import DetectionModel
from datetime import datetime
import warnings
import time
import numpy as np
warnings.filterwarnings("ignore", category=FutureWarning)

# --------------------------
# Fix for PyTorch >= 2.6
# --------------------------
torch.serialization.add_safe_globals([DetectionModel])

# --------------------------
# Configuration
# --------------------------
video_path = "traffic_feed.mp4"   # change to "0" for webcam
plates_output_folder = "plates_output"

# Create output folder and verify it works
try:
    os.makedirs(plates_output_folder, exist_ok=True)
    # Test write permissions
    test_file = os.path.join(plates_output_folder, "test_write.tmp")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print(f"[INFO] Output folder ready: {os.path.abspath(plates_output_folder)}")
except Exception as e:
    print(f"[ERROR] Cannot create/write to output folder: {e}")
    exit(1)

# Performance settings
SKIP_FRAMES = 1          # Process every 2nd frame
RESIZE_FACTOR = 0.8      # Moderate resize
USE_GPU = True           # Use GPU if available
CONFIDENCE_THRESHOLD = 0.4

# --------------------------
# Setup GPU if available
# --------------------------
device = 'cuda' if torch.cuda.is_available() and USE_GPU else 'cpu'
print(f"[INFO] Using device: {device}")

# --------------------------
# Load Models
# --------------------------
print("[INFO] Loading YOLOv5 model...")
model = yolov5.load('keremberke/yolov5m-license-plate')
model.conf = CONFIDENCE_THRESHOLD
model.iou = 0.45
model.to(device)
model.eval()

print("[INFO] Initializing EasyOCR...")
reader = easyocr.Reader(['en'], gpu=USE_GPU)

# --------------------------
# Open video
# --------------------------
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("[ERROR] Could not open video file or camera.")
    exit(1)

# Webcam optimizations
if video_path == "0" or video_path == 0:
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

frame_count = 0
processed_count = 0
plate_memory = {}  # Simple dictionary to track saved plates
frame_gap = 30     # Minimum frames between saving same plate
saved_count = 0    # Counter for saved plates

# Performance monitoring
start_time = time.time()
fps_counter = 0
last_fps_time = start_time

# --------------------------
# Get video dimensions and setup window
# --------------------------
original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[INFO] Original video size: {original_width}x{original_height}")

process_width = int(original_width * RESIZE_FACTOR)
process_height = int(original_height * RESIZE_FACTOR)
print(f"[INFO] Processing size: {process_width}x{process_height}")

cv2.namedWindow("Number Plate Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Number Plate Detection", original_width, original_height)

max_display_width = 1200
max_display_height = 800

if original_width > max_display_width or original_height > max_display_height:
    scale_w = max_display_width / original_width
    scale_h = max_display_height / original_height
    scale = min(scale_w, scale_h)
    
    display_width = int(original_width * scale)
    display_height = int(original_height * scale)
    cv2.resizeWindow("Number Plate Detection", display_width, display_height)

fullscreen = False

# --------------------------
# Main processing loop
# --------------------------
print("[INFO] Starting processing... Press 'q' to quit")
print(f"[INFO] Saving plates to: {os.path.abspath(plates_output_folder)}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[INFO] End of video reached")
        break
    
    frame_count += 1
    
    # Frame skipping for performance
    if SKIP_FRAMES > 0 and frame_count % (SKIP_FRAMES + 1) != 0:
        cv2.imshow("Number Plate Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue
    
    processed_count += 1
    
    # Resize frame for faster processing
    if RESIZE_FACTOR != 1.0:
        small_frame = cv2.resize(frame, (process_width, process_height))
        scale_x = original_width / process_width
        scale_y = original_height / process_height
    else:
        small_frame = frame
        scale_x = scale_y = 1.0

    # Run YOLO detection
    with torch.no_grad():
        results = model(small_frame)
    predictions = results.pred[0]

    # Process each detection
    for i in range(len(predictions)):
        x1, y1, x2, y2, conf, cls = predictions[i].tolist()
        
        if conf < CONFIDENCE_THRESHOLD:
            continue

        # Scale coordinates back to original frame size
        x1 = int(x1 * scale_x)
        y1 = int(y1 * scale_y)
        x2 = int(x2 * scale_x)
        y2 = int(y2 * scale_y)
        
        # Ensure coordinates are within frame bounds
        x1 = max(0, min(x1, original_width - 1))
        y1 = max(0, min(y1, original_height - 1))
        x2 = max(x1 + 1, min(x2, original_width))
        y2 = max(y1 + 1, min(y2, original_height))
        
        # Skip if bounding box is too small
        if (x2 - x1) < 30 or (y2 - y1) < 15:
            continue
            
        # Extract plate region
        cropped_plate = frame[y1:y2, x1:x2]
        
        if cropped_plate.size == 0:
            continue
        
        # OCR processing with error handling
        try:
            # Enhance image for better OCR
            gray_plate = cv2.cvtColor(cropped_plate, cv2.COLOR_BGR2GRAY)
            enhanced_plate = cv2.equalizeHist(gray_plate)
            
            # Run OCR
            plate_text = reader.readtext(enhanced_plate, detail=0, paragraph=False)
            
            if plate_text and len(plate_text) > 0:
                plate_number = plate_text[0].strip()
                # Clean the plate number - keep only alphanumeric
                plate_number = ''.join(c for c in plate_number if c.isalnum() or c.isspace()).strip()
                plate_number = ' '.join(plate_number.split())  # Clean whitespace
            else:
                plate_number = "Unknown"
                
        except Exception as e:
            print(f"[WARNING] OCR error: {e}")
            plate_number = "Unknown"
            continue

        # Skip if plate number is invalid
        if not plate_number or plate_number == "Unknown" or len(plate_number) < 3:
            continue
        
        # Check if we should save this plate
        should_save = True
        if plate_number in plate_memory:
            frames_since_last_save = processed_count - plate_memory[plate_number]
            if frames_since_last_save < frame_gap:
                should_save = False
        
        # Save the plate image
        if should_save:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
                # Clean filename - remove invalid characters
                clean_plate_name = ''.join(c for c in plate_number if c.isalnum() or c in (' ', '-', '_')).strip()
                clean_plate_name = clean_plate_name.replace(' ', '_')
                
                plate_filename = f"{clean_plate_name}_{timestamp}.jpg"
                full_path = os.path.join(plates_output_folder, plate_filename)
                
                # Save the cropped plate image
                success = cv2.imwrite(full_path, cropped_plate)
                
                if success:
                    plate_memory[plate_number] = processed_count
                    saved_count += 1
                    print(f"[SAVED] Plate #{saved_count}: '{plate_number}' -> {plate_filename}")
                else:
                    print(f"[ERROR] Failed to save: {plate_filename}")
                    
            except Exception as e:
                print(f"[ERROR] Save error: {e}")
        
        # Draw detection on frame
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
        
        # Add text background for better visibility
        display_text = f"{plate_number} ({conf:.2f})"
        text_size = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        
        cv2.rectangle(frame, (x1, y1 - 35), 
                     (x1 + text_size[0] + 10, y1), (0, 255, 0), -1)
        cv2.putText(frame, display_text, (x1 + 5, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Add status overlay to frame
    status_text = f"Processed: {processed_count} | Saved: {saved_count} | Frame: {frame_count}"
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

    # FPS counter
    fps_counter += 1
    current_time = time.time()
    if current_time - last_fps_time >= 3.0:  # Update every 3 seconds
        fps = fps_counter / (current_time - last_fps_time)
        print(f"[PERF] Processing FPS: {fps:.1f} | Frames: {processed_count}/{frame_count} | Plates saved: {saved_count}")
        fps_counter = 0
        last_fps_time = current_time

    # Display frame
    cv2.imshow("Number Plate Detection", frame)

    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # quit
        break
    elif key == ord('f'):  # toggle fullscreen
        fullscreen = not fullscreen
        if fullscreen:
            cv2.setWindowProperty("Number Plate Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty("Number Plate Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Number Plate Detection", original_width, original_height)
    elif key == ord('r'):  # reset window size
        cv2.resizeWindow("Number Plate Detection", original_width, original_height)
    elif key == ord('s'):  # toggle frame skipping
        SKIP_FRAMES = 0 if SKIP_FRAMES > 0 else 1
        print(f"[INFO] Frame skipping: {'OFF (every frame)' if SKIP_FRAMES == 0 else f'Every {SKIP_FRAMES+1}th frame'}")
    elif key == ord('c'):  # cycle confidence threshold
        if CONFIDENCE_THRESHOLD >= 0.5:
            CONFIDENCE_THRESHOLD = 0.3
        elif CONFIDENCE_THRESHOLD >= 0.4:
            CONFIDENCE_THRESHOLD = 0.5
        else:
            CONFIDENCE_THRESHOLD = 0.4
        model.conf = CONFIDENCE_THRESHOLD
        print(f"[INFO] Confidence threshold: {CONFIDENCE_THRESHOLD}")

# --------------------------
# Cleanup and final stats
# --------------------------
cap.release()
cv2.destroyAllWindows()

total_time = time.time() - start_time
avg_fps = processed_count / total_time if total_time > 0 else 0

print(f"\n{'='*50}")
print(f"[COMPLETED] License Plate Detection")
print(f"{'='*50}")
print(f"Total frames in video: {frame_count}")
print(f"Frames processed: {processed_count}")
print(f"Average processing FPS: {avg_fps:.1f}")
print(f"Plates saved: {saved_count}")
print(f"Output folder: {os.path.abspath(plates_output_folder)}")
print(f"Processing time: {total_time:.1f} seconds")

# List saved files
try:
    saved_files = [f for f in os.listdir(plates_output_folder) if f.endswith('.jpg')]
    print(f"\nSaved files ({len(saved_files)}):")
    for i, filename in enumerate(sorted(saved_files), 1):
        print(f"  {i:2d}. {filename}")
except Exception as e:
    print(f"[WARNING] Could not list saved files: {e}")

print(f"\n[DONE] Check the '{plates_output_folder}' folder for saved plate images!")