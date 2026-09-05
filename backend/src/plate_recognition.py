# FOR CPU
import cv2
import yolov5
import os
import sys
import ssl
from pymongo import MongoClient
from dotenv import load_dotenv
import uuid
from datetime import datetime
import easyocr
import torch
import io
import contextlib

# Bypass SSL verification for model downloads (e.g. on macOS)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import codecs
    import logging
    
    # Reconfigure stdout/stderr with UTF-8 encoding
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    
    # Fix logging to use the new stdout/stderr
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# --------------------------
# Validate arguments
# --------------------------
if len(sys.argv) < 4:
    print("[ERROR] Missing required arguments.", file=sys.stderr)
    sys.exit(1)

video_path = os.path.normpath(sys.argv[1])
plates_output_folder = os.path.normpath(sys.argv[2])
session_id = sys.argv[3]

# --------------------------
# Load environment and connect to MongoDB
# --------------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client["number_plate_db"]
sessions_collection = db["sessions"]
plates_collection = db["plates"]

def update_progress(status, percentage):
    sessions_collection.update_one(
        {"session_id": session_id},
        {"$set": {"status": status, "progress": percentage}}
    )

update_progress("Processing started", 0)

# --------------------------
# Check video existence
# --------------------------
if not os.path.exists(video_path):
    update_progress("Error: Video file not found", 0)
    sys.exit(1)

# --------------------------
# Fetch full session metadata
# --------------------------
session_doc = sessions_collection.find_one({"session_id": session_id})
if not session_doc:
    update_progress("Error: Session not found in database", 0)
    sys.exit(1)

# Remove MongoDB ObjectId for clean insert
session_doc.pop("_id", None)

# --------------------------
# Create output directories
# --------------------------
os.makedirs(plates_output_folder, exist_ok=True)
video_output_folder = os.path.join(os.path.dirname(plates_output_folder), "video_output")
os.makedirs(video_output_folder, exist_ok=True)

# --------------------------
# Load Models
# --------------------------
# Load YOLOv5 License Plate Model
print("[INFO] Loading YOLOv5 license plate detection model...")
try:
    model = yolov5.load('keremberke/yolov5m-license-plate')
    model.conf = 0.5
    model.iou = 0.45
    print("[OK] YOLOv5 model loaded successfully")
except Exception as e:
    print(f"[ERROR] Failed to load YOLOv5 model: {e}")
    update_progress("Error: Failed to load detection model", 0)
    sys.exit(1)

# Initialize OCR with suppressed output to avoid Unicode encoding issues
print("[INFO] Initializing EasyOCR reader...")
try:
    # Suppress EasyOCR's verbose output during initialization
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        reader = easyocr.Reader(['en'], verbose=False)
    print("[OK] EasyOCR reader initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize EasyOCR: {e}")
    update_progress("Error: Failed to initialize OCR", 0)
    sys.exit(1)

# --------------------------
# Open video
# --------------------------
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    update_progress("Error: Could not open video file", 0)
    sys.exit(1)

fps = int(cap.get(cv2.CAP_PROP_FPS))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# --------------------------
# Output video
# --------------------------
output_video_path = os.path.join(video_output_folder, "output.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

# --------------------------
# Process each frame
# --------------------------
frame_count = 0
plate_memory = {}  # Dictionary to track seen plates and frame timestamps
frame_gap = 30  # Minimum frames before re-saving the same plate

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1

    # Update progress every 10 frames
    if frame_count % 10 == 0:
        percent = int((frame_count / total_frames) * 100)
        update_progress("Processing...", percent)

    # Run YOLOv5 License Plate Detection
    results = model(frame)
    predictions = results.pred[0]

    detected_plates = []

    for i in range(len(predictions)):
        x1, y1, x2, y2, conf, cls = predictions[i].tolist()
        if conf < 0.5:  # Confidence filter
            continue

        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        cropped_plate = frame[y1:y2, x1:x2]

        # Perform OCR
        plate_text = reader.readtext(cropped_plate, detail=0)
        plate_number = plate_text[0] if plate_text else "Unknown"

        # Avoid saving plates with unclear text
        if plate_number == "Unknown" or len(plate_number) < 4:
            continue

        detected_plates.append({
            'plate_image': cropped_plate,
            'plate_number': plate_number,
            'confidence': conf,
            'bbox': (x1, y1, x2, y2)
        })

    # Process detected plates
    if detected_plates:
        detected_plates.sort(key=lambda x: x['confidence'], reverse=True)
        best_plate = detected_plates[0]
        plate_number = best_plate['plate_number']
        best_plate_image = best_plate['plate_image']
        best_bbox = best_plate['bbox']

        # Check if the plate was recently saved
        if plate_number not in plate_memory or (frame_count - plate_memory[plate_number]) > frame_gap:
            # Save image
            plate_filename = f"{plate_number}.jpg"
            full_path = os.path.join(plates_output_folder, plate_filename)
            cv2.imwrite(full_path, best_plate_image)
            plate_memory[plate_number] = frame_count

            # Relative image path
            image_path_relative = os.path.relpath(full_path, start=os.getcwd()).replace("\\", "/")

            # Insert into plates collection
            plates_collection.insert_one({
                "plate_number": plate_number,
                "image_path": image_path_relative,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **session_doc  # Includes session_id, video_filename, location, eloc, etc.
            })

            print(f"[OK] Saved plate: {plate_number}")

        # Draw bounding box
        x1, y1, x2, y2 = best_bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, plate_number, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    out.write(frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --------------------------
# Cleanup and finalize
# --------------------------
cap.release()
out.release()
cv2.destroyAllWindows()

# Update final status
update_progress("Processing completed", 100)
print(f"[OK] Processing completed. Processed {frame_count} frames.")
print(f"[OK] Found {len(plate_memory)} unique license plates.")